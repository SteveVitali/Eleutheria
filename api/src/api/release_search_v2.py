# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Release-pinned federated search serving v2 (P36.38 / K3 SRCH-03 — SIG-UI-076,
SIG-SRCH-001, SIG-SRCH-003, SIG-SRCH-012).

The read API answers ``GET /v1/releases/{publication_id or latest}/search`` —
ONE request federated across every licence compartment (SIG-SRCH-001) — over
the verified ``sig.release-search-index/2`` artifacts P36.31 emits and the
``sig.search-results/2`` engine P36.32 builds. The v1 per-compartment route
(``/v1/releases/{pub}/compartments/{comp}/search``) is kept untouched.

Serving rules (K3 §5.4/§5.5 — the v1 withdrawal/deadline contract carried over):

* **``latest`` via the conf-gen pointer** (REL-05): ``latest`` resolves through
  the registry's ``latest.json`` — no pointer answers 503
  ``no_current_release``. ``{pub}`` must be ``p-<sha>`` shaped, else 404.
* **Verify and copy, never read whole** (K3 §5.5 / NEW-2): on first use per
  publication each index file streams from the staged release mount to a
  local copy in 1 MiB chunks while hashing; the digest and byte size are
  compared against the release's integrity manifest before any ``mode=ro``
  open. A drifted artifact fails 503 — never silently served. A release with
  no v2 entries at all (a v1-era publication) answers 404
  ``v2_indexes_not_published``.
* **An LRU bounds the open engines** (``max_engines``, default 2 — two
  releases ≈ 200 MB at the K3 §5.5 sizing inside the 1 GiB service shape,
  D-K3-5): evicting a publication closes its connections and drops its
  verified local copies.
* **The withdrawal barrier is re-evaluated per request** (the same one P32.5
  policy): a route/namespace deny answers 410; entity- and claim-level
  denials drop the record before pagination and are counted into
  ``scope.excluded_records_by_reason`` under the same deadline (DR-C4-09).
  Claim denials resolve through the compartment ``claim_ref`` index — the
  denied claim id maps to its record keys once per request, never per row.
* **No query logging** (SIG-SRCH-012 / D-K3-4): this module never logs — the
  query string leaves no record. Per-client rate limits are the app-wide
  token bucket (P36.13, keyed on the LB-reported client address).
* **Cache headers** (K3 §5.4): a ``p-<sha>``-pinned answer is immutable —
  ``Cache-Control: public, max-age=31536000, immutable``; a ``latest`` answer
  follows the mutable pointer — ``max-age=300``.
* **``format`` is a known parameter**: ``json`` (or absent) serves the
  ``sig.search-results/2`` body; ``format=html`` answers a typed 501 — the
  no-JS HTML representation is P36.39's (SRCH-04), never silently JSON to a
  browser that asked for HTML.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from exports.release import NON_RECORD_COMPARTMENTS, ReleaseRegistry, route_access
from exports.search_index import QUERY_TIMEOUT_SECONDS
from exports.search_index_v2 import (
    CATALOG_V2_DESCRIPTOR_FILE,
    CATALOG_V2_FILE,
    CLAIM_REF_FILE,
    RECORD_INDEX_V2_FILE,
    STREAM_CHUNK_BYTES,
    _claim_blob,
)
from exports.search_query_v2 import (
    SearchEngineV2,
    SearchParamsV2,
    SearchQueryV2Error,
)
from policy.eligibility import TargetKind, access_decision, latest_disposition

from .release_search import PUBLICATION_RE

#: Query parameters the v2 route recognizes; anything else is an explicit 422.
KNOWN_PARAMS_V2 = frozenset(
    {
        "q",
        "type",
        "kind",
        "jurisdiction",
        "source",
        "technology",
        "collection",
        "location",  # recognized but unsupported by the v2 engine → typed 422
        "within",  # recognized but unsupported by the v2 engine → typed 422
        "cursor",
        "expand",
        "limit",
        "format",
    }
)

#: The posture env (OM-20 dark-ship): ``off`` (default — the route is not
#: mounted at all, identical public response to before the code landed) ·
#: ``on`` (the federated route serves). The deploy flip sets it; code
#: defaults keep v1 serving until then.
ENV_SEARCH_V2_POSTURE = "SIG_API_SEARCH_V2"
POSTURES_V2 = ("off", "on")

#: Cache-Control values (K3 §5.4): pub-pinned bytes are immutable; ``latest``
#: follows the mutable pointer.
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_LATEST = "public, max-age=300"

_MANIFEST_CACHE_CAP = 8
#: Default bound on simultaneously open engines (latest + one pinned release,
#: K3 §5.5 sizing inside the 1 GiB D-K3-5 shape).
DEFAULT_MAX_ENGINES = 2


def search_v2_posture(env: Mapping[str, str]) -> str:
    """Read the serving posture — fail closed on an unknown value (a typo
    must never silently un-serve or silently expose the route)."""
    raw = (env.get(ENV_SEARCH_V2_POSTURE) or "off").strip().lower()
    if raw not in POSTURES_V2:
        raise ValueError(
            f"{ENV_SEARCH_V2_POSTURE}={raw!r} is not one of {POSTURES_V2} — "
            "the public read API refuses to boot under an unknown v2-search posture"
        )
    return raw


class ReleaseSearchV2Store:
    """The staged-release v2 search store: verify-and-copy + a bounded LRU of
    open engines.

    ``registry_root`` is the release registry the activation tooling writes —
    ``staged/`` holds the served bytes, ``withdrawals.json`` the current
    registry, ``catalog.json``/``latest.json`` the promoted pointer set.
    ``cache_dir`` holds the verified local copies (Cloud Run local disk is
    memory — K3 §5.5); ``max_engines`` bounds the LRU.
    """

    def __init__(
        self,
        registry_root: Path | str,
        *,
        cache_dir: Path | str | None = None,
        max_engines: int = DEFAULT_MAX_ENGINES,
    ) -> None:
        self.registry_root = Path(registry_root)
        self.staged = self.registry_root / "staged"
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir is not None
            else Path(tempfile.mkdtemp(prefix="sig-search-v2-"))
        )
        self._max_engines = max(1, int(max_engines))
        #: pub → open SearchEngineV2 (verified local copies, mode=ro).
        self._engines: OrderedDict[str, SearchEngineV2] = OrderedDict()
        self._manifests: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

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
            raise SearchQueryV2Error(
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
            raise SearchQueryV2Error(
                503,
                "index_not_staged",
                f"{rel} is not staged under {pub}",
            ) from exc
        if digest.hexdigest() != entry.get("sha256") or size != entry.get("byte_size"):
            tmp.unlink(missing_ok=True)
            raise SearchQueryV2Error(
                503,
                "index_verification_failed",
                f"{rel} bytes do not match the release integrity manifest",
            )
        tmp.replace(dest)
        return dest

    def _open_engine(self, pub: str) -> SearchEngineV2:
        """Verify-and-copy every v2 artifact for ``pub``, then open the
        engine over the local ``mode=ro`` copies (contract-pinned by
        ``SearchEngineV2.open``)."""
        manifest = self._integrity_manifest(pub)
        arts = {str(a.get("path")): a for a in manifest.get("artifacts") or []}
        cat_rel = f"releases/{pub}/search/{CATALOG_V2_FILE}"
        v2_any = cat_rel in arts or any(
            f"r/{pub}/c/{cid}/{RECORD_INDEX_V2_FILE}" in arts
            for cid in self._manifest_compartments(manifest)
        )
        if not v2_any:
            raise SearchQueryV2Error(
                404,
                "v2_indexes_not_published",
                f"release {pub} carries no sig.release-search-index/2 artifacts — "
                "its v1 per-compartment route keeps working",
            )
        cat = self._copy_verified(pub, cat_rel, arts[cat_rel])
        members: list[tuple[Path, Path | None]] = []
        for cid in self._manifest_compartments(manifest):
            if cid in NON_RECORD_COMPARTMENTS:
                continue
            rec_rel = f"r/{pub}/c/{cid}/{RECORD_INDEX_V2_FILE}"
            entry = arts.get(rec_rel)
            if entry is None:
                raise SearchQueryV2Error(
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
            members.append((rec, cref))
        if not members:
            raise SearchQueryV2Error(
                404,
                "v2_indexes_not_published",
                f"release {pub} carries no searchable v2 record indexes",
            )
        try:
            return SearchEngineV2.open(cat, members)
        except SearchQueryV2Error:
            raise
        except Exception as exc:
            raise SearchQueryV2Error(
                503,
                "index_verification_failed",
                f"v2 search index for {pub} fails its contract pin",
            ) from exc

    @staticmethod
    def _manifest_compartments(manifest: Mapping[str, Any]) -> list[str]:
        return [
            str(c.get("compartment"))
            for c in manifest.get("compartments") or []
            if c.get("compartment")
        ]

    def _engine_for(self, pub: str) -> SearchEngineV2:
        """The open engine for ``pub`` — LRU hit, else verify-and-copy + open;
        an eviction closes connections and drops the local copies."""
        with self._lock:
            eng = self._engines.get(pub)
            if eng is not None:
                self._engines.move_to_end(pub)
                return eng
        eng = self._open_engine(pub)
        with self._lock:
            self._engines[pub] = eng
            self._engines.move_to_end(pub)
            while len(self._engines) > self._max_engines:
                evicted_pub, old = self._engines.popitem(last=False)
                old.close()
                shutil.rmtree(self.cache_dir / evicted_pub, ignore_errors=True)
        return eng

    # -- publication resolution ---------------------------------------------- #

    def resolve(self, requested: str) -> tuple[str, bool]:
        """``{pub or latest}`` → (publication_id, was_latest). ``latest``
        resolves through the conf-gen pointer (REL-05); an ill-formed or
        unstaged pub refuses 404, an absent pointer 503."""
        if requested == "latest":
            latest = ReleaseRegistry(self.registry_root).latest() or {}
            pub = latest.get("publication_id")
            if not pub:
                raise SearchQueryV2Error(
                    503,
                    "no_current_release",
                    "no promoted release is current — the registry carries no latest pointer",
                )
            return str(pub), True
        if not PUBLICATION_RE.match(requested):
            raise SearchQueryV2Error(
                404, "unknown_publication", f"unknown publication {requested!r}"
            )
        if not (self.staged / f"releases/{requested}").is_dir():
            raise SearchQueryV2Error(
                404,
                "unknown_publication",
                f"publication {requested} is not staged",
            )
        return requested, False

    # -- the withdrawal barrier ---------------------------------------------- #

    def _denied_targets(self) -> tuple[dict[str, str], dict[str, str]]:
        """({entity id → reason}, {claim id → reason}) under the CURRENT
        registry — evaluated at access time (the same P32.5 policy v1 runs)."""
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
    def _denied_records(engine: SearchEngineV2, denied_claims: Mapping[str, str]) -> dict[str, str]:
        """Denied claim ids → the record keys that carry them, resolved once
        per request through each compartment's ``claim_ref`` index (never a
        per-row lookup)."""
        out: dict[str, str] = {}
        if not denied_claims:
            return out
        for comp in engine.compartments:
            if comp.claim_ref is None:
                continue
            for claim_id, reason in denied_claims.items():
                for (rk,) in comp.claim_ref.execute(
                    "SELECT record_key FROM claim_ref WHERE claim = ?",
                    (_claim_blob(claim_id),),
                ):
                    out.setdefault(str(rk), reason)
        return out

    # -- the query ------------------------------------------------------------ #

    def search(self, requested: str, params: SearchParamsV2) -> tuple[dict[str, Any], str, bool]:
        """One federated ``sig.search-results/2`` page → (payload, pub,
        was_latest). The withdrawal barrier dominates and the per-request
        denial set is counted into the scope (DR-C4-09)."""
        pub, was_latest = self.resolve(requested)
        access = route_access(
            self.registry_root, f"releases/{pub}/search/{CATALOG_V2_DESCRIPTOR_FILE}"
        )
        if not access.get("permitted"):
            tomb = access.get("tombstone") or {}
            raise SearchQueryV2Error(
                410,
                "withdrawn",
                "withdrawn under the current publication-disposition policy",
                extra={"tombstone": tomb},
            )
        engine = self._engine_for(pub)
        denied_entities, denied_claims = self._denied_targets()
        denied_records = self._denied_records(engine, denied_claims) if denied_claims else {}

        def denied(row: tuple) -> str | None:
            reason = denied_entities.get(row[1])
            if reason is not None:
                return reason
            return denied_records.get(row[0])

        has_denies = bool(denied_entities or denied_records)
        # The engine's connections are check_same_thread=False (the LRU may
        # serve them on a different request thread than the opener) — but a
        # single engine's `search` is not reentrant: two concurrent calls
        # interleave cursors on the shared connections (the
        # `test_engine_survives_cross_thread_use` pin caught a `_doc_row`
        # interleave). Serving serializes the call — each is bounded by the
        # 2 s deadline and the rate limiter bounds the fan-in anyway.
        with self._lock:
            result = engine.search(
                params,
                denied=denied if has_denies else None,
                deadline_seconds=QUERY_TIMEOUT_SECONDS,
            )
        return result, pub, was_latest

    def readiness(self) -> dict[str, Any]:
        with self._lock:
            return {"open_engines": len(self._engines)}


def wants_html_v2(request: Any) -> bool:
    """``format=html`` or a browser ``Accept: text/html`` — the no-JS
    negotiation signal (handled by the route's 501 until P36.39 lands the
    representation)."""
    fmt = request.query_params.get("format")
    accept = request.headers.get("accept", "")
    return fmt == "html" or (fmt is None and "text/html" in accept)


def cache_control(was_latest: bool) -> str:
    return CACHE_LATEST if was_latest else CACHE_IMMUTABLE


__all__ = [
    "KNOWN_PARAMS_V2",
    "ReleaseSearchV2Store",
    "cache_control",
    "search_v2_posture",
    "wants_html_v2",
]
