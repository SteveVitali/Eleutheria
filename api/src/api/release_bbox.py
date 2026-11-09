# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Release-pinned bbox site list (P37.20 / K1 MAP-06 — the "R-tree in the
per-release SQLite" row).

The read API answers two release-namespaced routes over the verified
``sig.release-search-index/2`` record index — whose ``site_points`` R*Tree
(P37.20) is the release's own spatial index:

* ``GET /v1/releases/{pub or latest}/compartments/{comp}/sites?bbox=&page=``
  — the per-compartment JSON list (≤ 100 rows per page, derived labels).
* ``GET /v1/releases/{pub or latest}/sites?bbox=&page=&format=html`` — the
  cross-compartment grouped list; ``format=html`` (or a browser
  ``Accept: text/html``) serves the P37.20 no-JS representation
  (``exports.site_list_page``), the default ``format=json`` the grouped
  JSON twin. This is the map's "Show all N in this area" target and the
  no-JS equivalent of a bounded ``at=`` view.

Serving rules (the same contract the v1/v2 search surfaces carry):

* **``latest`` via the conf-gen pointer** (REL-05): resolves through the
  registry's ``latest.json`` — no pointer answers 503 ``no_current_release``.
  ``{pub}`` must be ``p-<sha>`` shaped and staged, else 404.
* **Verify and copy, never read whole** (K3 §5.5): on first use per
  publication each compartment index file streams from the staged release
  mount to a local copy in 1 MiB chunks while hashing; the digest and byte
  size are compared against the release's integrity manifest before any
  ``mode=ro`` open. A drifted artifact fails 503 — never silently served.
  A release whose index carries no ``site_points`` table (a pre-P37.20
  publication) answers 404 ``spatial_index_not_published`` — the honest
  absence, never a fabricated list.
* **A bounded set of verified copies** (``max_publications``, default 2):
  evicting a publication drops its local copies.
* **The withdrawal barrier is re-evaluated per request** (the same one
  P32.5 policy): a compartment-namespace deny on the per-compartment route
  answers 410; on the grouped route the denied group is dropped and named
  in ``scope.withdrawn_compartments`` (a deny covering every group answers
  410 whole). Entity- and claim-level denials drop the record before
  pagination and are counted into ``scope.excluded_records_by_reason``
  (DR-C4-09); claim denials resolve through the compartment ``claim_ref``
  index once per request.
* **No query logging** (SIG-SRCH-012 / D-K3-4): this module never logs —
  the bbox leaves no record. Per-client rate limits are the app-wide token
  bucket (P36.13).
* **Cache headers**: a ``p-<sha>``-pinned answer is immutable —
  ``Cache-Control: public, max-age=31536000, immutable``; a ``latest``
  answer follows the mutable pointer — ``max-age=300``.
* **Dark-ship posture** (OM-20): the routes mount only under
  ``SIG_API_BBOX=on``; default ``off`` mounts nothing — the public response
  is identical to before this code landed. The deploy flip (the API roll)
  is the operator's explicit verbatim go, never pre-authorised — queued
  ``prepared_not_executed`` as D-P37.20-1.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import tempfile
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from exports.release import NON_RECORD_COMPARTMENTS, ReleaseRegistry, route_access
from exports.search_index import QUERY_TIMEOUT_SECONDS
from exports.search_index_v2 import (
    CLAIM_REF_FILE,
    RECORD_INDEX_V2_DESCRIPTOR_FILE,
    RECORD_INDEX_V2_FILE,
    STREAM_CHUNK_BYTES,
    _claim_blob,
)
from policy.eligibility import TargetKind, access_decision, latest_disposition

from exports import site_list_page as slp

from .release_search import PUBLICATION_RE
from .release_serving import ReleaseServingStore

#: The response envelope schema.
SITES_BBOX_SCHEMA = "sig.sites-bbox/1"

#: The page bound the contract pins — ≤ 100 rows per page (K1 MAP-06).
SITE_PAGE_SIZE = 100

#: Query parameters the routes recognize; anything else is an explicit 422.
KNOWN_PARAMS_BBOX = frozenset({"bbox", "page", "format"})

#: The posture env (OM-20 dark-ship): ``off`` (default — the routes are not
#: mounted at all, identical public response to before the code landed) ·
#: ``on`` (the routes serve). The deploy flip sets it — the roll is the
#: operator's verbatim go (D-P37.20-1), never pre-authorised.
ENV_BBOX_POSTURE = "SIG_API_BBOX"
POSTURES_BBOX = ("off", "on")

#: Cache-Control values: pub-pinned bytes are immutable; ``latest`` follows
#: the mutable pointer.
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_LATEST = "public, max-age=300"

_MANIFEST_CACHE_CAP = 8
#: Default bound on simultaneously verified publications (the same K3 §5.5
#: sizing posture the v2 store runs).
DEFAULT_MAX_PUBLICATIONS = 2


def bbox_posture(env: Mapping[str, str]) -> str:
    """Read the serving posture — fail closed on an unknown value (a typo
    must never silently un-serve or silently expose the routes)."""
    raw = (env.get(ENV_BBOX_POSTURE) or "off").strip().lower()
    if raw not in POSTURES_BBOX:
        raise ValueError(
            f"{ENV_BBOX_POSTURE}={raw!r} is not one of {POSTURES_BBOX} — "
            "the public read API refuses to boot under an unknown bbox posture"
        )
    return raw


def cache_control(was_latest: bool) -> str:
    return CACHE_LATEST if was_latest else CACHE_IMMUTABLE


class ReleaseBboxError(Exception):
    """One typed bbox-list failure — machine code + public detail (the same
    ``{detail, code, **extra}`` shape every release-namespaced refusal
    carries)."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.extra = extra or {}


def parse_bbox(raw: str | None) -> list[tuple[float, float, float, float]]:
    """``bbox=w,s,e,n`` → one or two ``(w, s, e, n)`` spans.

    Longitudes bound to ``[-180, 180]``, latitudes to ``[-90, 90]``;
    ``s < n`` always. ``w > e`` crosses the antimeridian and splits into
    ``[w, 180]`` + ``[-180, e]`` — a real geographic case (the Pacific,
    the Aleutians), never silently clamped. Anything else is a typed 422 —
    never a guess, never a reorder.
    """
    if raw is None or not str(raw).strip():
        raise ReleaseBboxError(
            422,
            "missing_bbox",
            "the bbox parameter is required: bbox=west,south,east,north in decimal degrees",
        )
    parts = [p.strip() for p in str(raw).split(",")]
    if len(parts) != 4:
        raise ReleaseBboxError(
            422,
            "invalid_bbox",
            f"bbox must be four comma-separated numbers (west,south,east,north); got {raw!r}",
        )
    try:
        w, s, e, n = (float(p) for p in parts)
    except ValueError as exc:
        raise ReleaseBboxError(
            422,
            "invalid_bbox",
            f"bbox must be four comma-separated numbers (west,south,east,north); got {raw!r}",
        ) from exc
    if not all(math.isfinite(v) for v in (w, s, e, n)):
        raise ReleaseBboxError(422, "invalid_bbox", f"bbox values must be finite; got {raw!r}")
    if not (-180.0 <= w <= 180.0 and -180.0 <= e <= 180.0):
        raise ReleaseBboxError(
            422,
            "invalid_bbox",
            f"bbox longitudes must lie in [-180, 180]; got {raw!r}",
        )
    if not (-90.0 <= s <= 90.0 and -90.0 <= n <= 90.0):
        raise ReleaseBboxError(
            422,
            "invalid_bbox",
            f"bbox latitudes must lie in [-90, 90]; got {raw!r}",
        )
    if not s < n:
        raise ReleaseBboxError(
            422,
            "invalid_bbox",
            f"bbox south must be less than north; got {raw!r}",
        )
    if w <= e:
        return [(w, s, e, n)]
    return [(w, s, 180.0, n), (-180.0, s, e, n)]


def parse_page(raw: str | None) -> int:
    """``page=N`` — 1-based, ≥ 1. Absent answers page 1; anything else is a
    typed 422 (never a silent clamp)."""
    if raw is None or str(raw).strip() == "":
        return 1
    try:
        page = int(str(raw), 10)
    except ValueError as exc:
        raise ReleaseBboxError(
            422, "invalid_page", f"page must be a positive integer; got {raw!r}"
        ) from exc
    if page < 1:
        raise ReleaseBboxError(422, "invalid_page", f"page must be a positive integer; got {raw!r}")
    return page


def _progress_deadline(conn: sqlite3.Connection, deadline: float) -> None:
    """The 2 s execution budget (the v1/v2 search contract): the progress
    handler interrupts a runaway scan — exhaustion surfaces as an
    interrupted query, mapped to 503, never a partial page."""

    def _tick() -> int:
        return 1 if time.monotonic() > deadline else 0

    conn.set_progress_handler(_tick, 10_000)


class ReleaseBboxStore:
    """The staged-release bbox store: verify-and-copy of each compartment's
    v2 record index, then per-request ``mode=ro`` reads of ``site_points``.

    ``registry_root`` is the activated release registry — ``staged/`` holds
    the served bytes, ``withdrawals.json`` the current registry,
    ``catalog.json``/``latest.json`` the promoted pointer set. ``cache_dir``
    holds the verified local copies; ``max_publications`` bounds the set.
    """

    def __init__(
        self,
        registry_root: Path | str,
        *,
        cache_dir: Path | str | None = None,
        max_publications: int = DEFAULT_MAX_PUBLICATIONS,
    ) -> None:
        self.registry_root = Path(registry_root)
        self.staged = self.registry_root / "staged"
        self.cache_dir = (
            Path(cache_dir) if cache_dir is not None else Path(tempfile.mkdtemp(prefix="sig-bbox-"))
        )
        self._max_publications = max(1, int(max_publications))
        #: pub → {compartment: (index_path, claim_ref_path|None)} of verified
        #: local copies (bytes under a namespace can never change).
        self._verified: OrderedDict[str, dict[str, tuple[Path, Path | None]]] = OrderedDict()
        self._manifests: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._serving = ReleaseServingStore(registry_root)

    # -- verification / verify-and-copy ------------------------------------- #

    def _integrity_manifest(self, pub: str) -> dict[str, Any]:
        with self._lock:
            cached = self._manifests.get(pub)
            if cached is not None:
                self._manifests.move_to_end(pub)
                return cached
        path = self.staged / f"releases/{pub}/integrity_manifest.json"
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ReleaseBboxError(
                503,
                "index_not_staged",
                f"release {pub} has no staged integrity manifest",
            ) from exc
        with self._lock:
            self._manifests[pub] = manifest
            self._manifests.move_to_end(pub)
            while len(self._manifests) > _MANIFEST_CACHE_CAP:
                self._manifests.popitem(last=False)
        return manifest

    def _copy_verified(self, pub: str, rel: str, entry: Mapping[str, Any]) -> Path:
        """Stream ``staged/<rel>`` to the local cache in 1 MiB chunks while
        hashing (K3 §5.5 — never a whole-file read over the release mount);
        the digest AND byte size must match the integrity manifest entry."""
        src = self.staged / rel
        dest_dir = self.cache_dir / pub
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / rel.replace("/", "__")
        tmp = dest.with_suffix(dest.suffix + ".part")
        digest = hashlib.sha256()
        size = 0
        try:
            with open(src, "rb") as fin, open(tmp, "wb") as fout:
                while True:
                    chunk = fin.read(STREAM_CHUNK_BYTES)
                    if not chunk:
                        break
                    digest.update(chunk)
                    fout.write(chunk)
                    size += len(chunk)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise ReleaseBboxError(
                503,
                "index_not_staged",
                f"{rel} is not staged under {pub}",
            ) from exc
        if digest.hexdigest() != entry.get("sha256") or size != entry.get("byte_size"):
            tmp.unlink(missing_ok=True)
            raise ReleaseBboxError(
                503,
                "index_verification_failed",
                f"{rel} bytes do not match the release integrity manifest",
            )
        tmp.replace(dest)
        return dest

    @staticmethod
    def _manifest_compartments(manifest: Mapping[str, Any]) -> dict[str, str]:
        """{compartment: license} — record compartments only."""
        out: dict[str, str] = {}
        for c in manifest.get("compartments") or []:
            cid = str(c.get("compartment") or "")
            if cid and cid not in NON_RECORD_COMPARTMENTS:
                out[cid] = str(c.get("license") or "")
        return out

    def _publication_files(self, pub: str) -> dict[str, tuple[Path, Path | None]]:
        """{compartment: (index copy, claim_ref copy|None)} — verified once
        per publication, evicted past ``max_publications``."""
        with self._lock:
            cached = self._verified.get(pub)
            if cached is not None:
                self._verified.move_to_end(pub)
                return cached
        manifest = self._integrity_manifest(pub)
        arts = {str(a.get("path")): a for a in manifest.get("artifacts") or []}
        comps = self._manifest_compartments(manifest)
        if not any(f"r/{pub}/c/{cid}/{RECORD_INDEX_V2_FILE}" in arts for cid in comps):
            raise ReleaseBboxError(
                404,
                "spatial_index_not_published",
                f"release {pub} carries no sig.release-search-index/2 record index — "
                "its bbox list is not published (a pre-v2 publication)",
            )
        files: dict[str, tuple[Path, Path | None]] = {}
        for cid in sorted(comps):
            rec_rel = f"r/{pub}/c/{cid}/{RECORD_INDEX_V2_FILE}"
            entry = arts.get(rec_rel)
            if entry is None:
                raise ReleaseBboxError(
                    503,
                    "index_not_staged",
                    f"{rec_rel} is not in the integrity manifest",
                )
            rec = self._copy_verified(pub, rec_rel, entry)
            cref: Path | None = None
            cr_rel = f"r/{pub}/c/{cid}/{CLAIM_REF_FILE}"
            cr_entry = arts.get(cr_rel)
            if cr_entry is not None and (self.staged / cr_rel).is_file():
                cref = self._copy_verified(pub, cr_rel, cr_entry)
            files[cid] = (rec, cref)
        with self._lock:
            self._verified[pub] = files
            self._verified.move_to_end(pub)
            while len(self._verified) > self._max_publications:
                evicted_pub, _ = self._verified.popitem(last=False)
                shutil.rmtree(self.cache_dir / evicted_pub, ignore_errors=True)
        return files

    # -- publication resolution ---------------------------------------------- #

    def resolve(self, requested: str) -> tuple[str, bool]:
        """``{pub or latest}`` → (publication_id, was_latest). ``latest``
        resolves through the conf-gen pointer (REL-05); an ill-formed or
        unstaged pub refuses 404, an absent pointer 503."""
        if requested == "latest":
            latest = ReleaseRegistry(self.registry_root).latest() or {}
            pub = latest.get("publication_id")
            if not pub:
                raise ReleaseBboxError(
                    503,
                    "no_current_release",
                    "no promoted release is current — the registry carries no latest pointer",
                )
            return str(pub), True
        if not PUBLICATION_RE.match(requested):
            raise ReleaseBboxError(404, "unknown_publication", f"unknown publication {requested!r}")
        if not (self.staged / f"releases/{requested}").is_dir():
            raise ReleaseBboxError(
                404,
                "unknown_publication",
                f"publication {requested} is not staged",
            )
        return requested, False

    # -- the withdrawal barrier ---------------------------------------------- #

    def _denied_targets(self) -> tuple[dict[str, str], dict[str, str]]:
        """({entity id → reason}, {claim id → reason}) under the CURRENT
        registry — evaluated at access time (the same P32.5 policy the
        search surfaces run)."""
        registry = ReleaseRegistry(self.registry_root)
        grouped: dict[tuple[TargetKind, str], list] = {}
        for rec in registry.withdrawals():
            grouped.setdefault((rec.target_kind, rec.target_id), []).append(rec)
        denied: dict[TargetKind, dict[str, str]] = {
            TargetKind.ENTITY: {},
            TargetKind.CLAIM: {},
        }
        for (kind, tid), rs in grouped.items():
            decision = access_decision(latest_disposition(rs))
            if not decision.permitted and kind in denied:
                denied[kind][tid] = str(
                    decision.reason_category.value if decision.reason_category else "denied"
                )
        return denied[TargetKind.ENTITY], denied[TargetKind.CLAIM]

    @staticmethod
    def _denied_records(claim_ref: Path | None, denied_claims: Mapping[str, str]) -> dict[str, str]:
        """Denied claim ids → the record keys that carry them, resolved once
        per request through the compartment's ``claim_ref`` index (never a
        per-row lookup)."""
        out: dict[str, str] = {}
        if not denied_claims or claim_ref is None:
            return out
        conn = sqlite3.connect(f"file:{claim_ref}?mode=ro", uri=True)
        try:
            for claim_id, reason in denied_claims.items():
                for (rk,) in conn.execute(
                    "SELECT record_key FROM claim_ref WHERE claim = ?",
                    (_claim_blob(claim_id),),
                ):
                    out.setdefault(str(rk), reason)
        finally:
            conn.close()
        return out

    @contextmanager
    def _conn(self, index: Path) -> Iterator[sqlite3.Connection]:
        """One fresh ``mode=ro`` connection per compartment read — a shared
        connection cannot be iterated by concurrent request threads safely;
        per-request opens are cheap and give real read concurrency."""
        conn = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
        try:
            yield conn
        finally:
            conn.close()

    # -- the query ------------------------------------------------------------ #

    def _group_rows(
        self,
        pub: str,
        compartments: Mapping[str, str],
        files: Mapping[str, tuple[Path, Path | None]],
        spans: list[tuple[float, float, float, float]],
        page: int,
    ) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
        """One group's matched+page slice per compartment; returns
        ``(groups, excluded_by_reason, withdrawn_compartments)``."""
        denied_entities, denied_claims = self._denied_targets()
        groups: list[dict[str, Any]] = []
        excluded: dict[str, int] = {}
        withdrawn: list[str] = []
        for comp in sorted(compartments):
            index, cref = files[comp]
            access = route_access(
                self.registry_root,
                f"r/{pub}/c/{comp}/{RECORD_INDEX_V2_DESCRIPTOR_FILE}",
            )
            if not access.get("permitted"):
                withdrawn.append(comp)
                continue
            denied_records = self._denied_records(cref, denied_claims)

            def denied(
                t: tuple,
                _de: Mapping[str, str] = denied_entities,
                _dr: Mapping[str, str] = denied_records,
            ) -> str | None:
                reason = _de.get(t[1])
                if reason is not None:
                    return reason
                return _dr.get(t[0])

            excluded_here: dict[str, int] = {}
            with self._conn(index) as conn:
                _assert_spatial(conn, pub, comp)
                deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
                _progress_deadline(conn, deadline)
                try:
                    cur = conn.execute(*_bbox_sql(spans))
                    kept: list[tuple] = []
                    for t in cur:
                        reason = denied(t)
                        if reason is not None:
                            excluded_here[reason] = excluded_here.get(reason, 0) + 1
                            continue
                        kept.append(t)
                except sqlite3.OperationalError as exc:
                    if "interrupted" in str(exc).lower():
                        raise ReleaseBboxError(
                            503,
                            "query_timeout",
                            f"query exceeded the {QUERY_TIMEOUT_SECONDS:.0f}s execution budget",
                        ) from exc
                    raise
            for k, v in excluded_here.items():
                excluded[k] = excluded.get(k, 0) + v
            matched = len(kept)
            start = (page - 1) * SITE_PAGE_SIZE
            rows = [_site_row(t, pub=pub, comp=comp) for t in kept[start : start + SITE_PAGE_SIZE]]
            groups.append(
                {
                    "compartment": comp,
                    "license": compartments[comp],
                    "matched": matched,
                    "results": rows,
                }
            )
        return groups, excluded, withdrawn

    def sites(
        self,
        requested: str,
        compartment: str | None,
        spans: list[tuple[float, float, float, float]],
        page: int,
        bbox_raw: str,
    ) -> tuple[dict[str, Any], str, bool]:
        """One ``sig.sites-bbox/1`` page → (payload, pub, was_latest)."""
        pub, was_latest = self.resolve(requested)
        files = self._publication_files(pub)
        manifest = self._integrity_manifest(pub)
        comps = self._manifest_compartments(manifest)
        ident = self._serving.identity(pub)
        scope: dict[str, Any] = {}
        if compartment is not None:
            if compartment in NON_RECORD_COMPARTMENTS:
                raise ReleaseBboxError(
                    404,
                    "compartment_not_listable",
                    f"{compartment} is not a record compartment — it carries "
                    "pages and metadata only",
                )
            if compartment not in comps:
                raise ReleaseBboxError(
                    404,
                    "unknown_compartment",
                    f"compartment {compartment} is not part of {pub}",
                )
            access = route_access(
                self.registry_root,
                f"r/{pub}/c/{compartment}/{RECORD_INDEX_V2_DESCRIPTOR_FILE}",
            )
            if not access.get("permitted"):
                raise ReleaseBboxError(
                    410,
                    "withdrawn",
                    "withdrawn under the current publication-disposition policy",
                    extra={"tombstone": access.get("tombstone") or {}},
                )
            groups, excluded, _withdrawn = self._group_rows(
                pub, {compartment: comps[compartment]}, files, spans, page
            )
            group = groups[0]
            scope = {
                "matched": group["matched"],
                "excluded_records_by_reason": excluded,
            }
            payload = {
                "schema": SITES_BBOX_SCHEMA,
                "release": ident.block(),
                "query": {"bbox": bbox_raw, "page": page, "page_size": SITE_PAGE_SIZE},
                "scope": scope,
                "compartment": compartment,
                "license": group["license"],
                "results": group["results"],
                "page": {
                    "page": page,
                    "has_more": group["matched"] > page * SITE_PAGE_SIZE,
                },
            }
            return payload, pub, was_latest
        groups, excluded, withdrawn = self._group_rows(pub, comps, files, spans, page)
        if withdrawn and not groups:
            # Every record compartment is denied — the release-level
            # withdrawal dominates: a whole-route 410, never an empty list
            # presented as "no sites".
            raise ReleaseBboxError(
                410,
                "withdrawn",
                "withdrawn under the current publication-disposition policy",
            )
        matched = sum(g["matched"] for g in groups)
        scope = {
            "matched": matched,
            "excluded_records_by_reason": excluded,
        }
        if withdrawn:
            scope["withdrawn_compartments"] = withdrawn
        payload = {
            "schema": SITES_BBOX_SCHEMA,
            "release": ident.block(),
            "query": {"bbox": bbox_raw, "page": page, "page_size": SITE_PAGE_SIZE},
            "scope": scope,
            "groups": groups,
            "page": {
                "page": page,
                "has_more": any(g["matched"] > page * SITE_PAGE_SIZE for g in groups),
            },
        }
        return payload, pub, was_latest

    def readiness(self) -> dict[str, Any]:
        with self._lock:
            return {"verified_publications": len(self._verified)}

    def site_release(self, pub: str) -> dict[str, Any] | None:
        """The staged ``sig.site-release/1`` document for the stamp
        (P35.13 / REL-02). ``None`` when the release carries none — the
        page then renders unstamped, honestly."""
        path = self.staged / f"releases/{pub}/release.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return doc if isinstance(doc, dict) else None


@contextmanager
def _bbox_conn(index: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


def _assert_spatial(conn: sqlite3.Connection, pub: str, comp: str) -> None:
    """A release whose record index predates P37.20 carries no
    ``site_points`` table — the honest typed absence, never an empty list
    presented as "no sites in the box"."""
    found = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='site_points'"
    ).fetchone()
    if found is None:
        raise ReleaseBboxError(
            404,
            "spatial_index_not_published",
            f"release {pub} carries no site_points spatial index for {comp} — "
            "its bbox list is not published (a pre-P37.20 publication)",
        )


def _bbox_sql(spans: list[tuple[float, float, float, float]]) -> tuple[str, dict[str, float]]:
    where = " OR ".join(
        f"(sp.minX >= :w{i} AND sp.maxX <= :e{i} AND sp.minY >= :s{i} AND sp.maxY <= :n{i})"
        for i in range(len(spans))
    )
    binds: dict[str, float] = {}
    for i, (w, s, e, n) in enumerate(spans):
        binds[f"w{i}"], binds[f"s{i}"], binds[f"e{i}"], binds[f"n{i}"] = w, s, e, n
    sql = (
        "SELECT r.record_key, r.entity_id, r.entity_type, r.name, r.name_basis,"
        " r.place_key, r.place_text, r.source_id, r.source_name, r.technology,"
        " r.lat, r.lon, r.point_precision"
        " FROM site_points sp JOIN records r ON r.record_seq = sp.id"
        f" WHERE {where} ORDER BY r.name, r.record_key"
    )
    return sql, binds


def _site_row(t: tuple, *, pub: str, comp: str) -> dict[str, Any]:
    """One answer row — the derived label (K2's basis carried), the place,
    source and technology facets, the point at its published precision and
    the record's release-namespace hrefs."""
    (
        record_key,
        entity_id,
        entity_type,
        name,
        name_basis,
        place_key,
        place_text,
        source_id,
        source_name,
        technology,
        lat,
        lon,
        point_precision,
    ) = t
    base = f"/r/{pub}/c/{comp}/entity/{entity_type}/{entity_id}"
    location: dict[str, Any] = {"kind": "point", "lat": lat, "lon": lon}
    if point_precision:
        location["precision"] = point_precision
    return {
        "record_key": record_key,
        "entity": {"id": entity_id, "type": entity_type},
        "name": name,
        "name_basis": name_basis,
        "place": {"key": place_key, "text": place_text},
        "source": {"id": source_id, "name": source_name},
        "technology": technology,
        "location": location,
        "href": f"{base}/",
        "json_href": f"{base}.json",
    }


def wants_html(request: Any) -> bool:
    """``format=html`` or a browser ``Accept: text/html`` — the no-JS
    negotiation signal (the same rule as the search routes)."""
    fmt = request.query_params.get("format")
    accept = request.headers.get("accept", "")
    return fmt == "html" or (fmt is None and "text/html" in accept)


def render_sites_html(
    store: ReleaseBboxStore,
    requested: str,
    bbox: str,
    page: int,
    result: Mapping[str, Any],
    pub: str,
    was_latest: bool,
) -> bytes:
    """The no-JS HTML representation — the same verified page as grouped
    compartment tables under the archive chrome + release stamp."""
    return slp.sites_bbox_page(
        requested=requested,
        bbox=bbox,
        page=page,
        result=result,
        site_release=store.site_release(pub),
        was_latest=was_latest,
    )


def render_sites_error_html(requested: str, exc: ReleaseBboxError) -> bytes:
    """The no-JS error representation (DR-C4-10) — an HTML page for every
    error status, carrying the same code/detail the JSON body has plus the
    public-safe tombstone fields on a 410."""
    return slp.sites_bbox_error_page(
        requested=requested,
        status=exc.status,
        code=exc.code,
        detail=exc.detail,
        tombstone=exc.extra.get("tombstone"),
    )
