# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The search query engine v2 (P36.32 / K3 SRCH-02 — ``sig.search-results/2``).

The serving half of the §4.2 pipeline over the ``sig.release-search-index/2``
artifacts P36.31 builds: ONE release catalog (places, sources, technology
concepts, entities, documents, pages) plus ONE compact record index per
licence compartment. Every result is a typed card carrying its match reason;
order is by match quality — never by popularity, evidence counts or
confidence (the SIG-SRCH-003 posture surfaced here; that id's owner row is
P36.38).

Stages (K3 §4.2 — ``tier`` travels on every card):

* **0 identifier** — a UUID / record key / source id / claim id resolves the
  exact thing and stops.
* **1 alias** — case-sensitive acronyms compare the RAW query token (never a
  normalized lookup: a word-match for "ice" must never present as ICE —
  SIG-SRCH-005); case-insensitive technical terms join exact-name
  resolution under an ``alias`` basis. The card states the expansion and
  its cited source; when the alias names a SIG id its target follows.
  Word-hits of the same letters are *collapsed*, never hidden — each
  licence group reports its word-hit count under ``collapsed_reason``.
* **1 exact name** — the normalized query equal to a catalog official /
  alternate / identifier name resolves first (SIG-SRCH-004); every place
  homonym is shown with its parent, ordered by records held then level.
* **2 catalog text** — weighted FTS ``bm25(name 10, alternates 6,
  context 1)`` x the type prior; types merge on adjusted score.
* **2–4 records** — per compartment, weighted FTS ``bm25(name 10, place 2,
  source 1)``; per-hit tier = phrase in name (2) · all words in name (3) ·
  words only in place/source (4). Groups merge by tier, never by cross-
  compartment bm25 (the idfs are not comparable — K3 §4.2). When stage 3
  resolved exactly one place or source and the query is only that name,
  records arrive as a FILTER — the card carries the exact count and the
  scoped-search link — not as text hits.
* **5 suggestion** — only when stages 0–4 found nothing strong: the
  corrected query (the nearest vocabulary term per word, edit distance 1
  at <= 8 letters else 2, sharing a first or last letter) is kept ONLY if
  it finds strong results; ``query.suggestion`` always says so — a
  suggestion is stated, never a silent rewrite.

The bounds and the withdrawal barrier carry over verbatim from the v1
contract (P32.14 → DR-C4-09): a 200-code-point ``q`` ceiling, <= 50 rows
per group page, a 2 s execution deadline with a row-granular check, a
100 KiB serialized-response ceiling (tail rows drop, re-minting the
cursor, never exceeding it), and the access-time denial barrier —
``denied`` is evaluated per candidate row before pagination (denied rows
never return) and counted into ``excluded_records_by_reason`` under the
same deadline. With no barrier given no count pass runs at all.

Deterministic per release: identical index bytes + identical query →
identical response bytes (every ordering ends on a unique id key).
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .manifest import canonical_json
from .search_index import (
    DEFAULT_LIMIT,
    MAX_BODY_BYTES,
    MAX_LIMIT,
    MIN_TEXT_QUERY,
    QUERY_TIMEOUT_SECONDS,
    SearchIndexError,
    normalize_id,
    normalize_query,
    normalize_sort_key,
)
from .search_index_v2 import (
    CATALOG_BM25_WEIGHTS,
    CATALOG_DOC_TYPES,
    CATALOG_TYPE_PRIOR,
    CATALOG_V2_FILE,
    CLAIM_REF_FILE,
    RECORD_INDEX_V2_FILE,
    SearchIndexV2Error,
    _claim_blob,
    check_index_contract_v2,
    verify_search_index,
)

#: The results contract this engine emits (K3 §7).
SEARCH_RESULTS_SCHEMA = "sig.search-results/2"
#: The per-group cursor format version (recorded in every minted cursor).
GROUP_CURSOR_VERSION = 2
#: Result types a ``type=`` filter may name (SIG-SRCH-002's typed results
#: plus the catalog's entity type and the alias card).
RESULT_TYPES = (*CATALOG_DOC_TYPES, "record", "alias")
#: Facets emitted with counts (K3 §5.3/§7): result type, licence group,
#: jurisdiction, source, technology.
RECORD_FACETS = ("jurisdiction", "source", "technology")
#: The fetch window for catalog-text candidates before the prior merge.
CATALOG_CANDIDATE_CAP = 300
#: Bounded suggestion vocabulary (K3 §4.2 stage 6).
SUGGEST_MIN_LEN = 3


class SearchQueryV2Error(SearchIndexV2Error):
    """A serving-shaped v2 query failure — status + machine code + detail."""

    def __init__(
        self, status: int, code: str, detail: str, extra: dict[str, Any] | None = None
    ) -> None:
        super().__init__(code, detail, extra)
        self.status = status


# --------------------------------------------------------------------------- #
# Parameters                                                                  #
# --------------------------------------------------------------------------- #


@dataclass
class SearchParamsV2:
    """The normalized v2 search request (post-validation)."""

    q_raw: str | None
    q_tokens: list[str]
    types: set[str] | None
    filters: dict[str, str]
    limit: int
    group: str | None
    cursor: str | None
    expand_collapsed: bool = False
    unsupported: list[str] = field(default_factory=list)

    def with_q(self, q: str) -> SearchParamsV2:
        """The same request carrying a different query string (stage 6 —
        the suggestion re-run keeps the filters but drops any cursor:
        a cursor never survives a rewritten query)."""
        try:
            tokens = normalize_query(q)
        except SearchIndexError:
            tokens = []
        return replace(
            self,
            q_raw=q,
            q_tokens=tokens,
            cursor=None,
        )


def parse_params_v2(
    *,
    q: str | None,
    types: Iterable[str] | None = None,
    kind: str | None = None,
    jurisdiction: str | None = None,
    source: str | None = None,
    technology: str | None = None,
    collection: str | None = None,
    cursor: str | None = None,
    expand: str | None = None,
    limit: int | None,
    extra: Iterable[str] = (),
) -> SearchParamsV2:
    """Validate the request params; every failure is explicit, never guessed.

    ``type`` is the result type (place/organization/entity/technology/
    source/document/page/record/alias); ``kind`` stays the record's entity
    type (UXR-A04's split over SIG-UI-059's registry). ``cursor`` carries
    ``<group>:<token>`` — per-group paging, never a global page number
    mixing licences (K3 §6.5). ``expand=1`` re-opens collapsed word-hit
    groups (the acronym-alias "show them" affordance).
    """
    unsupported = sorted(str(e) for e in extra)
    if unsupported:
        raise SearchQueryV2Error(
            422, "unsupported_query", f"unsupported parameters: {', '.join(unsupported)}"
        )
    type_set: set[str] | None = None
    if types:
        type_set = {str(t).strip() for t in types if str(t).strip()}
        bad = type_set - set(RESULT_TYPES)
        if bad:
            raise SearchQueryV2Error(
                422,
                "unsupported_query",
                f"type must be one of {', '.join(RESULT_TYPES)}; got {', '.join(sorted(bad))}",
            )
    filters: dict[str, str] = {}
    for name, raw in (
        ("kind", kind),
        ("jurisdiction", jurisdiction),
        ("source", source),
        ("technology", technology),
        ("collection", collection),
    ):
        if raw is None or str(raw).strip() == "":
            continue
        v = str(raw).strip()
        if len(v) > 200:
            raise SearchQueryV2Error(422, "unsupported_query", f"{name} filter is too long")
        filters[name] = v
    lim = DEFAULT_LIMIT if limit is None else limit
    if not (1 <= lim <= MAX_LIMIT):
        raise SearchQueryV2Error(
            422, "unsupported_query", f"limit must be between 1 and {MAX_LIMIT}"
        )
    group = None
    token = None
    if cursor:
        if ":" not in cursor:
            raise SearchQueryV2Error(
                422,
                "malformed_cursor",
                "cursor must be <group>:<token> — per-group paging only",
            )
        group, token = cursor.split(":", 1)
        if not group or not token:
            raise SearchQueryV2Error(422, "malformed_cursor", "cursor is not decodable")
    expand_collapsed = expand in ("1", "true", "records", "all")
    try:
        tokens = normalize_query(q) if q is not None and q.strip() else []
    except SearchIndexError as exc:
        raise SearchQueryV2Error(exc.status, exc.code, exc.detail, exc.extra) from exc
    return SearchParamsV2(
        q_raw=q if q is not None and q.strip() else None,
        q_tokens=tokens,
        types=type_set,
        filters=filters,
        limit=lim,
        group=group,
        cursor=token,
        expand_collapsed=expand_collapsed,
    )


# --------------------------------------------------------------------------- #
# Per-group cursors (K3 §6.5 — "More records in this licence group")          #
# --------------------------------------------------------------------------- #


def _filter_hash(q_norm: str | None, params: SearchParamsV2) -> str:
    payload = canonical_json(
        {
            "f": dict(sorted(params.filters.items())),
            "t": sorted(params.types) if params.types else [],
            "q": q_norm,
        }
    )
    return hashlib.sha256(payload).hexdigest()[:16]


def encode_group_cursor(
    publication_id: str,
    compartment: str,
    filter_hash: str,
    last_key: tuple[int, str, str],
) -> str:
    payload = {
        "v": GROUP_CURSOR_VERSION,
        "p": publication_id,
        "c": compartment,
        "fh": filter_hash,
        "k": list(last_key),
    }
    return urlsafe_b64encode(canonical_json(payload)).rstrip(b"=").decode()


def decode_group_cursor(
    token: str,
    *,
    publication_id: str,
    compartment: str,
    filter_hash: str,
) -> tuple[int, float, str]:
    """Validate + decode → (tier, bm25 score, record_key). Malformed → 422;
    a cursor minted for another release/group/filter → 409."""
    try:
        pad = "=" * (-len(token) % 4)
        raw = json.loads(urlsafe_b64decode(token + pad))
    except Exception as exc:  # noqa: BLE001 - every decode failure is malformed
        raise SearchQueryV2Error(422, "malformed_cursor", "cursor is not decodable") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("k"), list) or len(raw["k"]) != 3:
        raise SearchQueryV2Error(422, "malformed_cursor", "cursor payload has the wrong shape")
    if (
        raw.get("v") != GROUP_CURSOR_VERSION
        or raw.get("p") != publication_id
        or raw.get("c") != compartment
        or raw.get("fh") != filter_hash
    ):
        raise SearchQueryV2Error(
            409,
            "cursor_context_mismatch",
            "cursor was minted for a different release, group or filter set",
        )
    try:
        return (int(raw["k"][0]), float(raw["k"][1]), str(raw["k"][2]))
    except (TypeError, ValueError) as exc:
        raise SearchQueryV2Error(
            422, "malformed_cursor", "cursor key is not (tier, score, record_key)"
        ) from exc


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _progress_deadline(conn: sqlite3.Connection, deadline: float) -> None:
    def _tick() -> int:
        return 1 if time.monotonic() > deadline else 0

    conn.set_progress_handler(_tick, 10_000)


def _fts_quote(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _fts_all(tokens: list[str]) -> str:
    """Tokens ANDed over every column — no grammar is ever exposed."""
    return " ".join(_fts_quote(t) for t in tokens)


def _fts_phrase(tokens: list[str]) -> str:
    return '"' + " ".join(t.replace('"', '""') for t in tokens) + '"'


def _fts_name_all(tokens: list[str]) -> str:
    """Every token present in the ``name`` column (column-scoped AND)."""
    return "name : " + " ".join(_fts_quote(t) for t in tokens)


def _deadline_raise(deadline_seconds: float) -> SearchQueryV2Error:
    return SearchQueryV2Error(
        503,
        "query_timeout",
        f"query exceeded the {deadline_seconds:.0f}s execution budget",
    )


def _edit_distance(a: str, b: str, limit: int) -> int:
    """Bounded Levenshtein — returns limit+1 once the bound is passed."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            row_min = min(row_min, cur[j])
        if row_min > limit:
            return limit + 1
        prev = cur
    return prev[-1]


#: Display order for place levels inside homonym lists (K3 §4.2 stage 3 —
#: records held first, level breaks the tie).
_LEVEL_ORDER = {
    "country": 0,
    "state_province": 1,
    "county": 2,
    "place": 3,
    "city": 3,
}


@dataclass
class CompartmentIndex:
    """One open, contract-checked per-compartment record index."""

    compartment: str
    license: str
    conn: sqlite3.Connection
    meta: dict[str, Any]
    claim_ref: sqlite3.Connection | None = None


# --------------------------------------------------------------------------- #
# The engine                                                                  #
# --------------------------------------------------------------------------- #


class SearchEngineV2:
    """The release-pinned query engine over ``sig.release-search-index/2``.

    One catalog connection + one record-index connection per licence
    compartment, every file opened ``mode=ro`` after its contract pin —
    integrity verification against the manifest is the opener's job
    (``open_release`` runs the streaming-hash ``verify_search_index``
    before any open; a drifted artifact fails, it is never served).
    """

    def __init__(
        self,
        catalog_conn: sqlite3.Connection,
        catalog_meta: Mapping[str, Any],
        compartments: Iterable[CompartmentIndex],
        *,
        release_label: str | None = None,
        as_of_world: str | None = None,
    ) -> None:
        self.catalog = catalog_conn
        self.catalog_meta = dict(catalog_meta)
        self.compartments = list(compartments)
        self.publication_id = str(self.catalog_meta["publication_id"])
        self.release_label = release_label or self.catalog_meta.get("release_label")
        self.as_of_world = as_of_world or self.catalog_meta.get("as_of_world")
        self._vocab: list[str] | None = None
        self._place_counts: dict[str, tuple[int, int]] = {}

    # -- opening ------------------------------------------------------------ #

    @classmethod
    def open(
        cls,
        catalog_path: Path | str,
        members: Iterable[tuple[Path | str, Path | str | None]],
    ) -> SearchEngineV2:
        """Open the catalog + per-compartment record/claim_ref indexes.

        ``members`` is ``[(record_index_path, claim_ref_path|None)]``; each
        file is opened ``mode=ro`` and its ``meta`` contract pinned
        (``check_index_contract_v2`` — a kind/schema/tokenizer/app-id
        mismatch refuses). Integrity verification is the caller's job —
        ``open_release`` runs it from the manifest.
        """
        catalog_path = Path(catalog_path)
        cconn = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
        cmeta = check_index_contract_v2(cconn, kind="catalog")
        comps: list[CompartmentIndex] = []
        for rec_path, cref_path in members:
            rconn = sqlite3.connect(f"file:{Path(rec_path)}?mode=ro", uri=True)
            rmeta = check_index_contract_v2(rconn, kind="record-index")
            cconn2 = None
            if cref_path is not None:
                cconn2 = sqlite3.connect(f"file:{Path(cref_path)}?mode=ro", uri=True)
                check_index_contract_v2(cconn2, kind="claim-ref")
            comps.append(
                CompartmentIndex(
                    compartment=str(rmeta["compartment"]),
                    license=str(rmeta.get("license") or ""),
                    conn=rconn,
                    meta=rmeta,
                    claim_ref=cconn2,
                )
            )
        return cls(
            cconn,
            cmeta,
            comps,
            release_label=str(cmeta.get("release_label") or "") or None,
            as_of_world=str(cmeta.get("as_of_world") or "") or None,
        )

    @classmethod
    def open_release(
        cls, release_dir: Path | str, *, publication_id: str | None = None
    ) -> SearchEngineV2:
        """SIG-SRCH-011's serve path: stream-hash every v2 artifact against
        the integrity manifest, pin each contract, then open — a drifted
        artifact fails, it is never silently served."""
        release_dir = Path(release_dir)
        manifests = list(release_dir.glob("releases/*/integrity_manifest.json"))
        if len(manifests) != 1:
            raise SearchQueryV2Error(
                503,
                "release_layout",
                f"expected exactly one integrity manifest, found {len(manifests)}",
            )
        integrity = json.loads(manifests[0].read_text(encoding="utf-8"))
        pub = str(integrity["publication_id"])
        if publication_id is not None and pub != publication_id:
            raise SearchQueryV2Error(
                503,
                "release_mismatch",
                f"release is {pub!r}, not {publication_id!r}",
            )
        arts = {str(a["path"]): a for a in integrity.get("artifacts") or []}

        def _verified(rel: str) -> Path:
            if rel not in arts:
                raise SearchQueryV2Error(
                    503, "release_layout", f"{rel} is not in the integrity manifest"
                )
            return release_dir / rel

        cat_rel = f"releases/{pub}/search/{CATALOG_V2_FILE}"
        verify_search_index(
            _verified(cat_rel),
            arts[cat_rel]["sha256"],
            kind="catalog",
            publication_id=pub,
        )
        members: list[tuple[Path, Path | None]] = []
        for comp in integrity.get("compartments") or []:
            cid = str(comp["compartment"])
            rec_rel = f"r/{pub}/c/{cid}/{RECORD_INDEX_V2_FILE}"
            verify_search_index(
                _verified(rec_rel),
                arts[rec_rel]["sha256"],
                kind="record-index",
                publication_id=pub,
            )
            cr_rel = f"r/{pub}/c/{cid}/{CLAIM_REF_FILE}"
            cr_path = release_dir / cr_rel
            if cr_rel in arts and cr_path.is_file():
                verify_search_index(
                    cr_path,
                    arts[cr_rel]["sha256"],
                    kind="claim-ref",
                    publication_id=pub,
                )
                members.append((release_dir / rec_rel, cr_path))
            else:
                members.append((release_dir / rec_rel, None))
        return cls.open(release_dir / cat_rel, members)

    def close(self) -> None:
        for comp in self.compartments:
            comp.conn.close()
            if comp.claim_ref is not None:
                comp.claim_ref.close()
        self.catalog.close()

    # -- catalog lookups ----------------------------------------------------- #

    def _doc_row(self, doc_id: str) -> dict[str, Any] | None:
        row = self.catalog.execute(
            "SELECT doc_id, doc_type, name, href, meta FROM docs WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
        if row is None:
            return None
        meta = json.loads(row[4]) if row[4] else {}
        return {
            "doc_id": row[0],
            "type": row[1],
            "name": row[2],
            "href": row[3],
            "meta": meta,
        }

    def _alias_row(self, key: str) -> dict[str, Any] | None:
        row = self.catalog.execute(
            "SELECT alias_key, case_sensitive, expansion, target, source_url"
            " FROM aliases WHERE alias_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return {
            "key": row[0],
            "case_sensitive": bool(row[1]),
            "expansion": row[2],
            "target": row[3],
            "source_url": row[4],
        }

    def _aliases(self) -> list[dict[str, Any]]:
        return [
            {
                "key": r[0],
                "case_sensitive": bool(r[1]),
                "expansion": r[2],
                "target": r[3],
                "source_url": r[4],
            }
            for r in self.catalog.execute(
                "SELECT alias_key, case_sensitive, expansion, target, source_url"
                " FROM aliases ORDER BY alias_key"
            )
        ]

    def _records_held(self, jkey: str, deadline: float) -> tuple[int, int]:
        """(records, distinct sources) the release holds for a jkey — the
        card's evidence basis, counted live per compartment under the
        query deadline."""
        if jkey in self._place_counts:
            return self._place_counts[jkey]
        total = 0
        sources: set[str] = set()
        for comp in self.compartments:
            if time.monotonic() > deadline:
                raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
            for n, s in comp.conn.execute(
                "SELECT COUNT(*), source_id FROM records WHERE place_key = ? GROUP BY source_id",
                (jkey,),
            ):
                total += int(n)
                sources.add(str(s))
        self._place_counts[jkey] = (total, len(sources))
        return self._place_counts[jkey]

    # -- cards --------------------------------------------------------------- #

    def _doc_card(self, doc: Mapping[str, Any], matched: str, deadline: float) -> dict[str, Any]:
        card = {
            "type": doc["type"],
            "doc_id": doc["doc_id"],
            "name": doc["name"],
            "href": doc["href"],
            "matched": matched,
        }
        meta = doc.get("meta") or {}
        for k in (
            "jkey",
            "level",
            "parent",
            "source_id",
            "slug",
            "family",
            "entity_id",
            "entity_type",
            "artifact_id",
            "artifact_type",
            "license",
            "status",
        ):
            if meta.get(k):
                card[k] = meta[k]
        if doc["type"] == "place" and meta.get("jkey"):
            total, n_sources = self._records_held(str(meta["jkey"]), deadline)
            card["records"] = {
                "total": total,
                "sources": n_sources,
                "href": f"/search/?jurisdiction={meta['jkey']}",
            }
        return card

    def _record_card(
        self,
        row: tuple,
        comp: CompartmentIndex,
        matched: str,
        tier: int | None,
        score: float | None,
    ) -> dict[str, Any]:
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
        ) = row[:10]
        card: dict[str, Any] = {
            "type": "record",
            "record_key": record_key,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "name": name,
            "name_derived": str(name_basis).startswith("derived"),
            "name_basis": name_basis,
            "jurisdiction": place_key if place_key != "unreported" else None,
            "place": place_text,
            "sources": [source_id] if source_id else [],
            "source_names": [source_name] if source_name else [],
            "matched": matched,
            "href": (
                f"/r/{self.publication_id}/c/{comp.compartment}/entity/{entity_type}/{entity_id}/"
            ),
            "license": comp.license,
        }
        if technology:
            card["technology"] = technology
        if tier is not None:
            card["tier"] = tier
        if score is not None:
            card["score"] = score
        return card

    # -- stage 0: identifier -------------------------------------------------- #

    def _identifier(self, token: str, deadline: float) -> list[dict[str, Any]]:
        """Tier 0 — record key, entity id, claim id, source/catalog id → the
        exact thing; a hit stops the pipeline (K3 §4.2 stage 1)."""
        hits: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for comp in self.compartments:
            if time.monotonic() > deadline:
                raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
            for row in comp.conn.execute(
                "SELECT record_key, entity_id, entity_type, name, name_basis,"
                " place_key, place_text, source_id, source_name, technology"
                " FROM records WHERE record_key = ? OR entity_id = ?",
                (token, token),
            ):
                seen_keys.add(str(row[0]))
                hits.append(self._record_card(row, comp, "identifier", 0, None))
            if comp.claim_ref is not None:
                for rk in self._claim_ref_keys(comp, token):
                    if rk in seen_keys:
                        continue
                    for row in comp.conn.execute(
                        "SELECT record_key, entity_id, entity_type, name,"
                        " name_basis, place_key, place_text, source_id,"
                        " source_name, technology FROM records"
                        " WHERE record_key = ?",
                        (rk,),
                    ):
                        seen_keys.add(str(row[0]))
                        hits.append(self._record_card(row, comp, "identifier", 0, None))
        # A source id or any catalog doc_id resolves as an identifier too.
        for prefix in ("source:", "place:", "technology:", "entity:", "document:", "page:"):
            doc = self._doc_row(prefix + token)
            if doc is not None:
                hits.append(self._doc_card(doc, "identifier", deadline))
        return hits

    def _claim_ref_keys(self, comp: CompartmentIndex, token: str) -> list[str]:
        if comp.claim_ref is None:
            return []
        return [
            str(r[0])
            for r in comp.claim_ref.execute(
                "SELECT record_key FROM claim_ref WHERE claim = ? ORDER BY record_key",
                (_claim_blob(token),),
            )
        ]

    # -- stage 1: aliases ----------------------------------------------------- #

    def _alias_stage(
        self, q_raw: str | None, q_norm: str | None, deadline: float
    ) -> tuple[list[dict[str, Any]], bool]:
        """Tier 1 — acronym/term aliases. A case-SENSITIVE key compares the
        raw query (never the normalized one — SIG-SRCH-005); a case-
        insensitive key resolves through the exact_names ``alias`` basis.
        Returns (cards, word_hits_collapsed)."""
        cards: list[dict[str, Any]] = []
        collapsed = False
        if not q_raw:
            return cards, collapsed
        raw = q_raw.strip()
        for al in self._aliases():
            hit = False
            if al["case_sensitive"]:
                # The RAW token equality is the whole point: "ice" is a
                # word, "ICE" is the alias. Word-hits collapse below.
                hit = raw == al["key"]
            elif q_norm and q_norm == normalize_id(al["key"]):
                hit = True
            if not hit:
                continue
            card: dict[str, Any] = {
                "type": "alias",
                "doc_id": f"alias:{al['key']}",
                "key": al["key"],
                "expansion": al["expansion"],
                "expansion_source": al["source_url"],
                "matched": "alias",
                "tier": 1,
            }
            target = str(al.get("target") or "")
            if target:
                doc = self._doc_row(target)
                if doc is not None:
                    card["target"] = self._doc_card(doc, "alias target", deadline)
                else:
                    card["target"] = target
            else:
                card["target"] = None
            cards.append(card)
            if al["case_sensitive"]:
                collapsed = True  # word-hits of the same letters collapse
        return cards, collapsed

    # -- stage 1: exact names -------------------------------------------------- #

    def _exact_names(self, q_norm: str | None, deadline: float) -> list[dict[str, Any]]:
        """Tier 1 — official/alternate/identifier names resolve first
        (SIG-SRCH-004); every homonym is shown with its parent, places
        ordered by records held then level."""
        if not q_norm:
            return []
        rows = list(
            self.catalog.execute(
                "SELECT e.doc_id, e.basis FROM exact_names e WHERE e.norm_name = ?",
                (q_norm,),
            )
        )
        docs: list[tuple[dict[str, Any], str]] = []
        for doc_id, basis in rows:
            if str(doc_id).startswith("alias:"):
                continue  # alias basis — the alias stage owns the card
            doc = self._doc_row(str(doc_id))
            if doc is None:
                continue
            docs.append((doc, str(basis)))
        held = {
            d[0]["doc_id"]: (
                self._records_held(str((d[0]["meta"] or {}).get("jkey") or ""), deadline)[0]
                if d[0]["type"] == "place"
                else 0
            )
            for d in docs
        }
        type_rank = {
            t: i
            for i, t in enumerate(
                ("place", "source", "organization", "entity", "technology", "document", "page")
            )
        }
        docs.sort(
            key=lambda d: (
                type_rank.get(d[0]["type"], 9),
                -held.get(d[0]["doc_id"], 0),
                _LEVEL_ORDER.get(str((d[0]["meta"] or {}).get("level") or ""), 5),
                normalize_sort_key(d[0]["name"]),
                d[0]["doc_id"],
            )
        )
        return [self._doc_card(doc, f"exact name ({basis})", deadline) for doc, basis in docs]

    # -- stage 2: catalog text -------------------------------------------------- #

    def _catalog_text(
        self,
        tokens: list[str],
        params: SearchParamsV2,
        exclude_doc_ids: set[str],
        deadline: float,
    ) -> dict[str, dict[str, Any]]:
        """Tier 2 — weighted FTS × type prior; results group by doc type."""
        sections: dict[str, dict[str, Any]] = {}
        if not tokens or all(len(t) < MIN_TEXT_QUERY for t in tokens):
            return sections
        match = _fts_all(tokens)
        rows = list(
            self.catalog.execute(
                "SELECT d.doc_id, bm25(docs_fts, ?, ?, ?) AS score"
                " FROM docs_fts JOIN docs d ON d.doc_seq = docs_fts.rowid"
                " WHERE docs_fts MATCH ?"
                " ORDER BY score, d.doc_id LIMIT ?",
                (
                    CATALOG_BM25_WEIGHTS["name"],
                    CATALOG_BM25_WEIGHTS["alternates"],
                    CATALOG_BM25_WEIGHTS["context"],
                    match,
                    CATALOG_CANDIDATE_CAP,
                ),
            )
        )
        adjusted: list[tuple[float, str]] = []
        for doc_id, score in rows:
            if str(doc_id) in exclude_doc_ids:
                continue
            doc = self._doc_row(str(doc_id))
            if doc is None:
                continue
            prior = CATALOG_TYPE_PRIOR.get(doc["type"], 1.0)
            # bm25 lower = better; subtracting the prior's log boosts the
            # preferred type without ever reordering by popularity.
            adjusted.append((float(score) - math.log(max(prior, 1e-9)), str(doc_id)))
            if time.monotonic() > deadline:
                raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
        adjusted.sort()
        seen: set[str] = set()
        for _adj, doc_id in adjusted:
            if doc_id in seen or doc_id in exclude_doc_ids:
                continue
            doc = self._doc_row(doc_id)
            assert doc is not None
            if params.types and doc["type"] not in params.types:
                continue
            seen.add(doc_id)
            sec = sections.setdefault(doc["type"], {"type": doc["type"], "total": 0, "results": []})
            sec["total"] += 1
            if len(sec["results"]) < params.limit:
                card = self._doc_card(doc, "catalog text", deadline)
                card["tier"] = 2
                sec["results"].append(card)
        return sections

    # -- stages 2–4: records ---------------------------------------------------- #

    _RECORD_COLS = (
        "record_key, entity_id, entity_type, name, name_basis, place_key,"
        " place_text, source_id, source_name, technology"
    )

    def _record_filters(self, params: SearchParamsV2) -> tuple[list[str], dict[str, Any]]:
        where: list[str] = []
        bind: dict[str, Any] = {}
        for name, col in (
            ("kind", "entity_type"),
            ("jurisdiction", "place_key"),
            ("source", "source_id"),
            ("technology", "technology"),
        ):
            if name in params.filters:
                where.append(f"r.{col} = :f_{name}")
                bind[f"f_{name}"] = params.filters[name]
        return where, bind

    def _group_total(
        self,
        comp: CompartmentIndex,
        params: SearchParamsV2,
        tokens: list[str],
        deadline: float,
    ) -> int:
        where, bind = self._record_filters(params)
        sql = "SELECT COUNT(*) FROM records r"
        if tokens:
            sql += (
                " JOIN records_fts ON r.record_seq = records_fts.rowid"
                " WHERE records_fts MATCH :match"
            )
            bind = dict(bind, match=_fts_all(tokens))
            if where:
                sql += " AND " + " AND ".join(where)
        elif where:
            sql += " WHERE " + " AND ".join(where)
        try:
            return int(comp.conn.execute(sql, bind).fetchone()[0])
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc):
                raise _deadline_raise(QUERY_TIMEOUT_SECONDS) from exc
            raise

    def _group_facets(
        self,
        comp: CompartmentIndex,
        params: SearchParamsV2,
        tokens: list[str],
        deadline: float,
    ) -> dict[str, list[tuple[str, int]]]:
        where, bind = self._record_filters(params)
        base = " FROM records r"
        if tokens:
            base += " JOIN records_fts ON r.record_seq = records_fts.rowid"
            bind = dict(bind, match=_fts_all(tokens))
            clauses = ["records_fts MATCH :match"] + where
        else:
            clauses = where or ["1 = 1"]
        out: dict[str, list[tuple[str, int]]] = {}
        for facet, col in (
            ("jurisdiction", "place_key"),
            ("source", "source_id"),
            ("technology", "technology"),
        ):
            if time.monotonic() > deadline:
                raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
            sql = f"SELECT r.{col}, COUNT(*){base} WHERE {' AND '.join(clauses)} GROUP BY r.{col}"
            try:
                vals = [
                    (str(v), int(n))
                    for v, n in comp.conn.execute(sql, bind)
                    if str(v) and str(v) != "unreported"
                ]
            except sqlite3.OperationalError as exc:
                if "interrupted" in str(exc):
                    raise _deadline_raise(QUERY_TIMEOUT_SECONDS) from exc
                raise
            if vals:
                out[facet] = sorted(vals)
        return out

    def _tier_queries(self, tokens: list[str]) -> list[tuple[int, str, str]]:
        """The (tier, match, matched-reason) ladder — tier order
        dominates bm25 (K3 §4.2 stages 2–4)."""
        phrase = _fts_phrase(tokens)
        name_all = _fts_name_all(tokens)
        all_cols = _fts_all(tokens)
        tiers: list[tuple[int, str, str]] = []
        tiers.append((2, f"name : {phrase}", "name phrase"))
        tiers.append((3, f"({name_all}) NOT ({'name : ' + phrase})", "all words in name"))
        tiers.append((4, f"({all_cols}) NOT ({name_all})", "words in place/source"))
        return tiers

    def _records_page(
        self,
        comp: CompartmentIndex,
        params: SearchParamsV2,
        tokens: list[str],
        last_key: tuple[int, float, str] | None,
        denied: Callable[[tuple], Any] | None,
        deadline: float,
    ) -> tuple[list[dict[str, Any]], tuple[int, float, str] | None]:
        """One dense page of a licence group: tier → bm25 → record_key,
        the denial barrier evaluated per candidate BEFORE pagination.

        Collects ``limit + 1`` allowed rows so ``next_cursor`` is minted
        only when a next page genuinely exists — the cursor always tracks
        the last EMITTED key, so re-evaluated denials never duplicate or
        skip a row (the v1 contract carried over)."""
        where, bind = self._record_filters(params)
        target = params.limit + 1
        results: list[dict[str, Any]] = []
        last: tuple[int, float, str] | None = None
        if not tokens:
            # Browse: a deterministic record_key walk (no text to rank on).
            sql = f"SELECT {self._RECORD_COLS} FROM records r"
            clauses = list(where)
            if last_key is not None:
                clauses.append("r.record_key > :lastk")
                bind["lastk"] = last_key[2]
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY r.record_key LIMIT :lim"
            bind["lim"] = target
            try:
                for row in comp.conn.execute(sql, bind):
                    if time.monotonic() > deadline:
                        raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
                    if denied is not None and denied(row):
                        continue
                    last = (0, 0.0, str(row[0]))
                    results.append(self._record_card(row, comp, "browse", None, None))
                    if len(results) >= target:
                        break
            except sqlite3.OperationalError as exc:
                if "interrupted" in str(exc):
                    raise _deadline_raise(QUERY_TIMEOUT_SECONDS) from exc
                raise
        else:
            for tier, match, reason in self._tier_queries(tokens):
                if len(results) >= target:
                    break
                if last_key is not None and tier < last_key[0]:
                    continue
                # Keyset-walk the tier in bounded windows: the seek tracks
                # the last CANDIDATE (denied or emitted), so a window full
                # of denials never truncates the walk and never leaks one.
                seek: tuple[float, str] | None = (
                    (last_key[1], last_key[2])
                    if last_key is not None and tier == last_key[0]
                    else None
                )
                while len(results) < target:
                    # The MATCH runs in an inner query over records_fts
                    # alone — a bare `name :` column filter is unambiguous
                    # only when the joined `records.name` is out of scope.
                    t_where = list(where)
                    t_bind = dict(bind, match=match)
                    if seek is not None:
                        t_where.append("(s.score > :ls OR (s.score = :ls AND r.record_key > :lk))")
                        t_bind["ls"] = seek[0]
                        t_bind["lk"] = seek[1]
                    sql = (
                        f"SELECT {self._RECORD_COLS}, s.score"
                        " FROM (SELECT rowid AS rid,"
                        " bm25(records_fts, 10.0, 2.0, 1.0) AS score"
                        " FROM records_fts WHERE records_fts MATCH :match) s"
                        " JOIN records r ON r.record_seq = s.rid"
                    )
                    if t_where:
                        sql += " AND " + " AND ".join(t_where)
                    sql += " ORDER BY s.score, r.record_key LIMIT :lim"
                    t_bind["lim"] = 512
                    seen_any = False
                    try:
                        for row in comp.conn.execute(sql, t_bind):
                            if time.monotonic() > deadline:
                                raise _deadline_raise(QUERY_TIMEOUT_SECONDS)
                            seen_any = True
                            score = float(row[10])
                            seek = (score, str(row[0]))
                            if denied is not None and denied(row):
                                continue
                            last = (tier, score, str(row[0]))
                            results.append(self._record_card(row, comp, reason, tier, score))
                            if len(results) >= target:
                                break
                    except sqlite3.OperationalError as exc:
                        if "interrupted" in str(exc):
                            raise _deadline_raise(QUERY_TIMEOUT_SECONDS) from exc
                        raise
                    if not seen_any or len(results) >= target:
                        break
        has_more = len(results) > params.limit
        emitted = results[: params.limit]
        if has_more and emitted:
            last_card = emitted[-1]
            last = (
                int(last_card.get("tier") or 0),
                float(last_card.get("score") or 0.0),
                str(last_card["record_key"]),
            )
        elif not has_more:
            last = None
        return emitted, last if has_more else None

    # -- stage 5: suggestion ---------------------------------------------------- #

    def _vocabulary(self) -> list[str]:
        if self._vocab is None:
            self._vocab = sorted(
                {
                    str(r[0])
                    for r in self.catalog.execute(
                        "SELECT DISTINCT norm_name FROM exact_names WHERE length(norm_name) >= ?",
                        (SUGGEST_MIN_LEN,),
                    )
                    if " " not in str(r[0]) or True
                }
            )
        return self._vocab

    def _suggest_correction(self, tokens: list[str]) -> str | None:
        """K3 §4.2 stage 6 — per word, the vocabulary term within edit
        distance 1 (<= 8 letters) or 2 (longer) sharing a first or last
        letter; deterministic (distance, term) order."""
        vocab = self._vocabulary()
        # Single-token candidates from names AND the individual words of
        # multi-word names ("canberra" lives inside "canberra ave").
        single = vocab + sorted(
            {w for name in vocab for w in name.split() if len(w) >= SUGGEST_MIN_LEN}
        )
        corrected: list[str] = []
        changed = False
        for tok in tokens:
            if len(tok) < SUGGEST_MIN_LEN:
                corrected.append(tok)
                continue
            limit = 1 if len(tok) <= 8 else 2
            best: tuple[int, str] | None = None
            for term in single:
                if not term or (term[0] != tok[0] and term[-1] != tok[-1]):
                    continue
                d = _edit_distance(tok, term, limit)
                if d <= limit and (best is None or (d, term) < best):
                    best = (d, term)
            corrected.append(best[1] if best else tok)
            changed = changed or best is not None and best[1] != tok
        q2 = " ".join(corrected)
        return q2 if changed else None

    # -- assembly --------------------------------------------------------------- #

    def _denied_counts(
        self,
        denied: Callable[[tuple], Any],
        deadline: float,
        deadline_seconds: float,
    ) -> dict[str, int]:
        """DR-C4-09 carried over: one bounded pass per compartment counts
        the access-time denials by public-safe reason — exhaustion 503s,
        never a partial scope presented as whole."""
        counts: dict[str, int] = {}
        for comp in self.compartments:
            for row in comp.conn.execute(f"SELECT {self._RECORD_COLS} FROM records r"):
                if time.monotonic() > deadline:
                    raise _deadline_raise(deadline_seconds)
                reason = denied(row)
                if reason:
                    key = reason if isinstance(reason, str) else "denied"
                    counts[key] = counts.get(key, 0) + 1
        return counts

    def search(
        self,
        params: SearchParamsV2,
        *,
        denied: Callable[[tuple], Any] | None = None,
        deadline_seconds: float = QUERY_TIMEOUT_SECONDS,
        _allow_suggest: bool = True,
    ) -> dict[str, Any]:
        """Execute one ``sig.search-results/2`` page over verified ro
        connections. See the module docstring for the stage semantics."""
        deadline = time.monotonic() + max(0.001, deadline_seconds)
        conns = (
            [self.catalog]
            + [c.conn for c in self.compartments]
            + [c.claim_ref for c in self.compartments if c.claim_ref is not None]
        )
        for conn in conns:
            _progress_deadline(conn, deadline)
        try:
            return self._search(
                params,
                denied=denied,
                deadline=deadline,
                deadline_seconds=deadline_seconds,
                _allow_suggest=_allow_suggest,
            )
        finally:
            for conn in conns:
                conn.set_progress_handler(None, 0)

    def _search(
        self,
        params: SearchParamsV2,
        *,
        denied: Callable[[tuple], Any] | None,
        deadline: float,
        deadline_seconds: float,
        _allow_suggest: bool,
    ) -> dict[str, Any]:
        q_norm = " ".join(params.q_tokens) if params.q_tokens else None
        fh = _filter_hash(q_norm, params)
        suggestion: dict[str, Any] | None = None
        top: list[dict[str, Any]] = []
        sections: dict[str, dict[str, Any]] = {}
        groups: list[dict[str, Any]] = []
        collapsed_word = False
        filter_link: dict[str, Any] | None = None

        # -- stage 0: identifier (stops the pipeline) ---------------------- #
        if params.q_raw and len(params.q_tokens) == 1 and not params.filters and not params.types:
            id_hits = self._identifier(params.q_raw.strip(), deadline)
            if id_hits:
                top.extend(id_hits)
                return self._assemble(
                    params,
                    q_norm,
                    fh,
                    top,
                    sections,
                    groups,
                    suggestion=None,
                    denied=denied,
                    deadline=deadline,
                    deadline_seconds=deadline_seconds,
                    collapsed_word=False,
                    filter_link=None,
                )

        # -- stage 1: aliases ---------------------------------------------- #
        alias_cards, collapsed_word = self._alias_stage(params.q_raw, q_norm, deadline)
        alias_cards = [c for c in alias_cards if not params.types or "alias" in params.types]
        top.extend(alias_cards)

        # -- stage 1: exact names ------------------------------------------- #
        exact_cards = self._exact_names(q_norm, deadline) if q_norm else []
        seen_docs: set[str] = {str(c["doc_id"]) for c in top if c.get("doc_id")}
        for card in exact_cards:
            if card["doc_id"] in seen_docs:
                continue
            if params.types and card["type"] not in params.types:
                continue
            seen_docs.add(card["doc_id"])
            top.append(card)

        # Name-only resolution → records arrive as a FILTER (a scoped-
        # search link with the exact count on every resolved card), never
        # as text hits. Homonyms each carry their own count — SIG-SRCH-004
        # shows them all, never guesses.
        resolved = [c for c in exact_cards if c["type"] in ("place", "source")]
        name_only = bool(resolved) and all(c["type"] in ("place", "source") for c in exact_cards)
        if name_only and not collapsed_word and params.q_raw is not None:
            for r in resolved:
                key = r.get("jkey") or r.get("source_id")
                scope = "jurisdiction" if r["type"] == "place" else "source"
                if key:
                    cnt_where = "place_key" if scope == "jurisdiction" else "source_id"
                    by_group: dict[str, int] = {}
                    total = 0
                    for comp in self.compartments:
                        n = int(
                            comp.conn.execute(
                                f"SELECT COUNT(*) FROM records WHERE {cnt_where} = ?",
                                (key,),
                            ).fetchone()[0]
                        )
                        if n:
                            by_group[comp.compartment] = n
                            total += n
                    r["records"] = {
                        "total": total,
                        "by_licence_group": by_group,
                        "href": f"/search/?{scope}={key}",
                    }
                    filter_link = r["records"]

        # -- stage 2: catalog text ------------------------------------------ #
        sections = self._catalog_text(params.q_tokens, params, seen_docs, deadline)

        # -- stages 2–4: records ---------------------------------------------- #
        run_records = filter_link is None and (not params.types or "record" in params.types)
        # A lone too-short token is id/name-resolved only — a one- or
        # two-letter word is never text-matched against every row.
        if params.q_tokens and all(len(t) < MIN_TEXT_QUERY for t in params.q_tokens):
            run_records = False
        comp_ids = [
            c
            for c in self.compartments
            if "collection" not in params.filters or c.compartment == params.filters["collection"]
        ]
        if params.cursor and all(c.compartment != params.group for c in comp_ids):
            raise SearchQueryV2Error(
                409,
                "cursor_context_mismatch",
                "cursor was minted for a group this request does not search",
            )
        for comp in comp_ids:
            group = {
                "compartment": comp.compartment,
                "license": comp.license,
                "total": 0,
                "collapsed_reason": None,
                "results": [],
                "next_cursor": None,
            }
            groups.append(group)
            if not run_records:
                continue
            tokens = params.q_tokens
            total = self._group_total(comp, params, tokens, deadline)
            group["total"] = total
            last_key = None
            if params.cursor and params.group == comp.compartment:
                last_key = decode_group_cursor(
                    params.cursor,
                    publication_id=self.publication_id,
                    compartment=comp.compartment,
                    filter_hash=fh,
                )
            rows, new_last = self._records_page(comp, params, tokens, last_key, denied, deadline)
            if collapsed_word and not params.expand_collapsed:
                group["collapsed_reason"] = "word matches for an acronym alias"
                group["results"] = []
            else:
                group["results"] = rows
            if new_last is not None:
                group["next_cursor"] = f"{comp.compartment}:" + encode_group_cursor(
                    self.publication_id,
                    comp.compartment,
                    fh,
                    (new_last[0], repr(new_last[1]), new_last[2]),
                )

        # -- stage 5: suggestion ----------------------------------------------- #
        strong = (
            bool(top)
            or any(s["results"] for s in sections.values())
            or any(g["total"] or g["results"] for g in groups)
        )
        if not strong and params.q_tokens and _allow_suggest:
            corrected = self._suggest_correction(params.q_tokens)
            if corrected:
                retry = self.search(
                    params.with_q(corrected),
                    denied=denied,
                    deadline_seconds=max(0.001, deadline - time.monotonic()),
                    _allow_suggest=False,
                )
                r_strong = (
                    bool(retry["top"])
                    or any(s["results"] for s in retry["sections"])
                    or any(g["total"] or g["results"] for g in retry["record_groups"])
                )
                if r_strong:
                    retry["query"]["suggestion"] = {
                        "original": params.q_raw,
                        "corrected": corrected,
                    }
                    retry["query"]["q"] = params.q_raw
                    return retry
        return self._assemble(
            params,
            q_norm,
            fh,
            top,
            sections,
            groups,
            suggestion=suggestion,
            denied=denied,
            deadline=deadline,
            deadline_seconds=deadline_seconds,
            collapsed_word=collapsed_word,
            filter_link=filter_link,
        )

    def _assemble(
        self,
        params: SearchParamsV2,
        q_norm: str | None,
        fh: str,
        top: list[dict[str, Any]],
        sections: dict[str, dict[str, Any]],
        groups: list[dict[str, Any]],
        *,
        suggestion: dict[str, Any] | None,
        denied: Callable[[tuple], Any] | None,
        deadline: float,
        deadline_seconds: float,
        collapsed_word: bool,
        filter_link: dict[str, Any] | None,
    ) -> dict[str, Any]:
        # Scope: indexed totals, access-time denials counted under the same
        # deadline (DR-C4-09 carried over verbatim).
        indexed = sum(
            int((c.meta.get("scope") or {}).get("indexed_records") or 0) for c in self.compartments
        )
        excluded: dict[str, int] = {}
        denied_counts = self._denied_counts(denied, deadline, deadline_seconds) if denied else {}
        for k, n in denied_counts.items():
            excluded[k] = excluded.get(k, 0) + n
        for c in self.compartments:
            comp_excl = (c.meta.get("scope") or {}).get("excluded_records_by_reason") or {}
            for k, n in dict(comp_excl).items():
                excluded[k] = excluded.get(k, 0) + int(n)
        searched = max(0, indexed - sum(denied_counts.values()))

        # Facets over the matched record sets + the typed result counts.
        facet_merged: dict[str, dict[str, int]] = {
            "type": {},
            "collection": {},
            "jurisdiction": {},
            "source": {},
            "technology": {},
        }
        for g in groups:
            if g["total"]:
                facet_merged["collection"][g["compartment"]] = g["total"]
                facet_merged["type"]["record"] = facet_merged["type"].get("record", 0) + g["total"]
        for card in top:
            t = str(card.get("type") or "")
            if t:
                facet_merged["type"][t] = facet_merged["type"].get(t, 0) + 1
        for sec in sections.values():
            if sec["total"]:
                facet_merged["type"][sec["type"]] = (
                    facet_merged["type"].get(sec["type"], 0) + sec["total"]
                )
        if any(g["total"] for g in groups):
            for comp in self.compartments:
                if (
                    "collection" in params.filters
                    and comp.compartment != params.filters["collection"]
                ):
                    continue
                for facet, vals in self._group_facets(
                    comp, params, params.q_tokens, deadline
                ).items():
                    for v, n in vals:
                        facet_merged[facet][v] = facet_merged[facet].get(v, 0) + n
        facets = {
            name: [[v, n] for v, n in sorted(vals.items())]
            for name, vals in facet_merged.items()
            if vals
        }

        empty: dict[str, Any] | None = None
        nothing = (
            not top
            and not any(s["results"] for s in sections.values())
            and not any(g["total"] or g["results"] for g in groups)
            and filter_link is None
        )
        if nothing:
            empty = {"kind": "no_match"}
            if params.filters:
                # filtered-to-zero: say what was searched before the filter.
                stripped = SearchParamsV2(
                    q_raw=params.q_raw,
                    q_tokens=params.q_tokens,
                    types=params.types,
                    filters={},
                    limit=params.limit,
                    group=None,
                    cursor=None,
                )
                unfiltered = 0
                for comp in self.compartments:
                    unfiltered += self._group_total(comp, stripped, params.q_tokens, deadline)
                if unfiltered:
                    empty = {
                        "kind": "filtered_to_zero",
                        "matching_without_filters": unfiltered,
                    }

        result: dict[str, Any] = {
            "schema": SEARCH_RESULTS_SCHEMA,
            "release": {
                "label": self.release_label,
                "publication_id": self.publication_id,
                "as_of_world": self.as_of_world,
            },
            "query": {
                "q": params.q_raw,
                "normalized": q_norm,
                "filters": dict(params.filters),
                "types": sorted(params.types) if params.types else None,
                "suggestion": suggestion,
            },
            "scope": {
                "records_indexed": indexed,
                "records_searched": searched,
                "groups_searched": len(groups),
                "excluded_records_by_reason": excluded,
            },
            "top": top,
            "sections": [sections[t] for t in CATALOG_DOC_TYPES if t in sections],
            "record_groups": groups,
            "facets": facets,
            "empty": empty,
            "truncated": False,
        }
        # The 100 KiB wire bound carried over: drop tail rows (re-minting
        # the group cursor on the last EMITTED key) rather than exceed it.
        while len(canonical_json(result)) > MAX_BODY_BYTES:
            dropped = False
            for g in reversed(groups):
                if g["results"]:
                    g["results"].pop()
                    dropped = True
                    if g["results"]:
                        last_row = g["results"][-1]
                        g["next_cursor"] = f"{g['compartment']}:" + encode_group_cursor(
                            self.publication_id,
                            g["compartment"],
                            fh,
                            (
                                int(last_row.get("tier") or 0),
                                repr(float(last_row.get("score") or 0.0)),
                                str(last_row["record_key"]),
                            ),
                        )
                    else:
                        g["next_cursor"] = None
                    break
            if not dropped:
                if top:
                    top.pop()
                    continue
                for sec in reversed(result["sections"]):
                    if sec["results"]:
                        sec["results"].pop()
                        dropped = True
                        break
                if not dropped:
                    break
            result["truncated"] = True
        return result
