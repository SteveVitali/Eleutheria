# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Released-corpus search serving (P32.14 / ADR-133 — SIG-FIND-003).

The read API answers ``/v1/releases/<pub>/compartments/<comp>/search`` from the
**verified immutable per-compartment SQLite FTS5 index** the release build
emits under ``r/<pub>/c/<comp>/search_index.sqlite`` — staged into the
release registry like every other artifact. There is deliberately **no**
current-only PostgreSQL fallback beneath released pages: an index that is
absent, unverified or cold answers an explicit 503 readiness state, and a
withdrawn release answers 410.

Serving rules (the same one P32.5 policy, evaluated at access time):

* The file's sha256 is checked against the staged ``sig.release-integrity/1``
  manifest before the first ``mode=ro`` open; afterwards the verified mark is
  cached (bytes under a namespace can never change).
* Every request gets its OWN read-only connection — a shared sqlite
  connection cannot be iterated by concurrent request threads safely, and
  per-request ``mode=ro`` opens are cheap while giving real read concurrency
  across compartments.
* The CURRENT withdrawal registry is re-evaluated per request: a release
  deny → 410 whole; an entity/claim deny drops the record from every result
  page *before* pagination, so nothing withheld leaks and pages stay dense.
* Every query runs under the 2 s progress-handler budget; exhaustion answers
  503 + Retry-After, never a partial page presented as complete.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from exports.release import ReleaseRegistry, route_access
from exports.release_pages import search_page
from policy.eligibility import TargetKind, access_decision, latest_disposition

from exports import search_index as si

PUBLICATION_RE = re.compile(r"^p-[0-9a-f]{64}$")

#: The route path under /v1 — also the no-JS form action target.
SEARCH_PATH = "/v1/releases/{publication_id}/compartments/{compartment}/search"

#: Query parameters the contract recognizes; anything else is an explicit 422.
KNOWN_PARAMS = frozenset(
    {
        "q",
        "kind",
        "jurisdiction",
        "source",
        "location",
        "technology",
        "limit",
        "cursor",
        "format",
    }
)

_MANIFEST_CACHE_CAP = 8


class ReleaseSearchStore:
    """The staged-release search store: verified read-only index access.

    ``registry_root`` is the release registry the activation tooling writes —
    ``staged/`` holds the served bytes, ``withdrawals.json`` the current
    registry, ``catalog.json`` the activated publications.
    """

    def __init__(self, registry_root: Path | str) -> None:
        self.registry_root = Path(registry_root)
        self.staged = self.registry_root / "staged"
        #: (pub, comp) indexes that passed manifest verification — bytes under
        #: a namespace can never change, so re-hashing per request is wasted.
        self._verified: set[tuple[str, str]] = set()
        self._manifests: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    # -- verification ------------------------------------------------------ #

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
            raise si.SearchIndexError(
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

    def _verify(self, pub: str, comp: str, path: Path) -> None:
        manifest = self._integrity_manifest(pub)
        rel = f"r/{pub}/c/{comp}/{si.INDEX_FILE}"
        entry = next((a for a in manifest.get("artifacts") or [] if a.get("path") == rel), None)
        if entry is None:
            raise si.SearchIndexError(503, "index_not_staged", f"no integrity entry for {rel}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise si.SearchIndexError(
                503,
                "index_not_staged",
                f"search index for {comp} is not staged under {pub}",
            ) from exc
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.get("sha256") or len(data) != entry.get("byte_size"):
            raise si.SearchIndexError(
                503,
                "index_verification_failed",
                "search index bytes do not match the release integrity manifest",
            )

    def _index_path(self, pub: str, comp: str) -> Path:
        return self.staged / f"r/{pub}/c/{comp}/{si.INDEX_FILE}"

    def _ensure_verified(self, pub: str, comp: str) -> None:
        key = (pub, comp)
        with self._lock:
            if key in self._verified:
                return
        self._verify(pub, comp, self._index_path(pub, comp))
        with self._lock:
            self._verified.add(key)

    @contextmanager
    def _conn(self, pub: str, comp: str) -> Iterator[tuple[sqlite3.Connection, dict[str, Any]]]:
        """One fresh ``mode=ro`` connection per request — a shared connection
        cannot be iterated by concurrent request threads safely; per-request
        opens are cheap and give real read concurrency across compartments."""
        self._ensure_verified(pub, comp)
        conn = sqlite3.connect(f"file:{self._index_path(pub, comp)}?mode=ro", uri=True)
        try:
            meta = si.check_index_contract(conn)
            if str(meta.get("publication_id")) != pub or str(meta.get("compartment")) != comp:
                raise si.SearchIndexError(
                    503,
                    "index_verification_failed",
                    "search index identity does not match the requested namespace",
                )
            yield conn, meta
        finally:
            conn.close()

    # -- the withdrawal barrier ------------------------------------------- #

    def _denied_sets(self) -> tuple[set[str], set[str]]:
        """(denied entity ids, denied claim ids) under the CURRENT registry —
        evaluated at access time so a withhold recorded in a later release
        still denies under this one (ADR-124/132)."""
        registry = ReleaseRegistry(self.registry_root)
        entities: dict[str, list] = {}
        claims: dict[str, list] = {}
        for rec in registry.withdrawals():
            if rec.target_kind is TargetKind.ENTITY:
                entities.setdefault(rec.target_id, []).append(rec)
            elif rec.target_kind is TargetKind.CLAIM:
                claims.setdefault(rec.target_id, []).append(rec)
        denied_entities = {
            tid
            for tid, rs in entities.items()
            if not access_decision(latest_disposition(rs)).permitted
        }
        denied_claims = {
            tid
            for tid, rs in claims.items()
            if not access_decision(latest_disposition(rs)).permitted
        }
        return denied_entities, denied_claims

    # -- the query --------------------------------------------------------- #

    def search(self, pub: str, comp: str, params: si.SearchParams) -> dict[str, Any]:
        """One bounded page over the verified index — the same one P32.5
        withdrawal rule applied per request."""
        if not PUBLICATION_RE.match(pub):
            raise si.SearchIndexError(404, "unknown_publication", f"unknown publication {pub!r}")
        if not (self.staged / f"releases/{pub}").is_dir():
            raise si.SearchIndexError(
                404, "unknown_publication", f"publication {pub} is not staged"
            )
        # The withdrawal barrier dominates: a denied namespace answers 410 —
        # never stale hits.
        access = route_access(self.registry_root, f"r/{pub}/c/{comp}/{si.INDEX_DESCRIPTOR_FILE}")
        if not access.get("permitted"):
            tomb = access.get("tombstone") or {}
            raise si.SearchIndexError(
                410,
                "withdrawn",
                "withdrawn under the current publication-disposition policy",
                extra={"tombstone": tomb},
            )
        comp_dir = self.staged / f"r/{pub}/c/{comp}"
        if not comp_dir.is_dir():
            raise si.SearchIndexError(
                404, "unknown_compartment", f"compartment {comp} is not part of {pub}"
            )
        denied_entities, denied_claims = self._denied_sets()

        def denied(row: tuple) -> bool:
            if row[1] in denied_entities:
                return True
            if denied_claims:
                claims = json.loads(row[7])
                return bool(denied_claims.intersection(claims))
            return False

        has_denies = bool(denied_entities or denied_claims)
        with self._conn(pub, comp) as (conn, meta):
            return si.search(
                conn,
                meta,
                params,
                denied=denied if has_denies else None,
                deadline_seconds=si.QUERY_TIMEOUT_SECONDS,
            )

    def facet_options(self, pub: str, comp: str) -> dict[str, list[tuple[str, int]]]:
        """Facet value lists for the no-JS form (jurisdiction/source/kind/
        technology)."""
        out: dict[str, list[tuple[str, int]]] = {}
        with self._conn(pub, comp) as (conn, _meta):
            for facet in ("kind", "jurisdiction", "source", "technology"):
                vals = si.facet_values(conn, facet)
                if vals:
                    out[facet] = vals
        return out

    def readiness(self) -> dict[str, Any]:
        """How many compartment indexes have passed verification (aggregate)."""
        with self._lock:
            return {"verified_indexes": len(self._verified)}


def render_search_html(
    store: ReleaseSearchStore,
    pub: str,
    comp: str,
    params: si.SearchParams,
    result: Mapping[str, Any],
) -> bytes:
    """The no-JS representation — same verified index, same bounds."""
    facets = store.facet_options(pub, comp)
    licence = str(result.get("license") or "")
    return search_page(
        action=SEARCH_PATH.format(publication_id=pub, compartment=comp),
        publication_id=pub,
        compartment=comp,
        licence=licence,
        params={
            "q": params.q_raw or "",
            "filters": params.filters,
            "limit": params.limit,
        },
        facet_options=facets,
        result=result,
    )
