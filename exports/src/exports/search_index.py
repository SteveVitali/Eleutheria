# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-compartment released-corpus search indexes (P32.14 / ADR-133 — SIG-FIND-003).

Each immutable release compartment ships ONE deterministic SQLite FTS5 index
artifact built from its ``sig.published-record/1`` projections — never from the
current claim spine, so a pinned release can never silently fall back to
current-only PostgreSQL search:

* ``records`` — the normalized record table (one row per eligible released
  record: key, entity id/type, label + sort key, jurisdiction, location kind,
  source, technology, claim carriers) with covering indexes for keyset browse.
* ``records_fts`` — an FTS5 (``unicode61``) index over the searchable text
  columns, sharing ``record_seq`` rowids with ``records``.
* ``identifiers`` — the normalized identifier table (entity id, full record
  key and every claim id) powering exact-id lookup.
* ``facets`` — the normalized facet table (kind / jurisdiction / source /
  location / technology → record keys) powering facet values and filtering.
* ``meta`` — the index contract pins: tokenizer, sort definition, cursor
  version, scope counters and the recording sqlite version.

Determinism: fixed page size, journal off, a fixed application id, rows
inserted in ``record_key`` order inside one transaction — identical inputs on
an identical SQLite build reproduce identical bytes (the recording version is
pinned in ``meta`` + the ``sig.release-search-index/1`` descriptor so a
library change is visible, never silent).

The serving side is read-only: the API opens the verified file ``mode=ro``
and evaluates the CURRENT withdrawal registry at access time — a deny
recorded after activation still denies under an older release (ADR-124/132).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import unicodedata
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manifest import canonical_json

#: The machine contract stamped on ``search_index.json`` and ``meta``.
SEARCH_INDEX_SCHEMA = "sig.release-search-index/1"
#: The format version — a descriptor input, so an index-format change mints a
#: new publication namespace (two-stage identity, ADR-132).
SEARCH_INDEX_VERSION = "release-search-index/1"
#: Artifact names inside ``r/<pub>/c/<comp>/``.
INDEX_FILE = "search_index.sqlite"
INDEX_DESCRIPTOR_FILE = "search_index.json"
#: Fixed physical layout (determinism) + a registered application id.
PAGE_SIZE = 4096
APPLICATION_ID = 0x53494731  # "SIG1"
#: The pinned tokenizer + sort definitions (recorded in every index).
TOKENIZER = "unicode61"
SORT_ID = "label-type-id/1"
CURSOR_VERSION = 1
#: Query contract bounds (S4 research §10 + the ticket ACs).
MAX_QUERY_CODEPOINTS = 200
MIN_TEXT_QUERY = 3
DEFAULT_LIMIT = 50
MAX_LIMIT = 50
QUERY_TIMEOUT_SECONDS = 2.0
#: The serialized response ceiling (the ticket's <=100 KiB wire bound —
#: checked on the canonical JSON body, which dominates the compressed size).
MAX_BODY_BYTES = 100 * 1024
#: Supported facet names → records columns.
FACETS: dict[str, str] = {
    "kind": "entity_type",
    "jurisdiction": "jurisdiction",
    "source": "source_id",
    "location": "location_kind",
    "technology": "technology",
}
LOCATION_VALUES = ("any", "public-point", "no-public-point")

_DDL = """
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE records (
  record_seq INTEGER PRIMARY KEY,
  record_key TEXT NOT NULL UNIQUE,
  entity_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  label TEXT NOT NULL,
  label_sort TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  location_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  technology TEXT NOT NULL,
  claim_ids TEXT NOT NULL
);
CREATE VIRTUAL TABLE records_fts USING fts5(
  label, entity_id, source_id, jurisdiction, tokenize='unicode61'
);
CREATE TABLE identifiers (
  norm_id TEXT NOT NULL,
  record_key TEXT NOT NULL,
  PRIMARY KEY (norm_id, record_key)
) WITHOUT ROWID;
CREATE TABLE facets (
  facet TEXT NOT NULL,
  value TEXT NOT NULL,
  record_key TEXT NOT NULL,
  PRIMARY KEY (facet, value, record_key)
) WITHOUT ROWID;
CREATE INDEX records_sort ON records (label_sort, entity_type, entity_id);
CREATE INDEX records_jur ON records (jurisdiction, label_sort, entity_type, entity_id);
CREATE INDEX records_src ON records (source_id, label_sort, entity_type, entity_id);
CREATE INDEX records_kind ON records (entity_type, label_sort, entity_type, entity_id);
CREATE INDEX records_loc ON records (location_kind, label_sort, entity_type, entity_id);
CREATE INDEX records_tech ON records (technology, label_sort, entity_type, entity_id);
"""

_KEYSET_ORDER = "r.label_sort, r.entity_type, r.entity_id"
_KEYSET_AFTER = (
    "(r.label_sort > :ls OR (r.label_sort = :ls AND r.entity_type > :et) "
    "OR (r.label_sort = :ls AND r.entity_type = :et AND r.entity_id > :eid))"
)


# --------------------------------------------------------------------------- #
# Errors                                                                      #
# --------------------------------------------------------------------------- #


class SearchIndexError(Exception):
    """One typed search failure — status + machine code + public detail."""

    def __init__(
        self, status: int, code: str, detail: str, extra: dict[str, Any] | None = None
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.extra = extra or {}


# --------------------------------------------------------------------------- #
# Normalisation                                                               #
# --------------------------------------------------------------------------- #


def normalize_sort_key(text: str | None) -> str:
    """The stable label sort key: NFKC + casefold + collapsed whitespace."""
    if not text:
        return ""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def normalize_id(text: str) -> str:
    """Identifier normalisation for exact-id lookup (case-insensitive)."""
    return " ".join(text.split()).casefold()


def normalize_query(q: str) -> list[str]:
    """q → NFKC+casefold tokens. Rejects >200 code points (422)."""
    if len(q) > MAX_QUERY_CODEPOINTS:
        raise SearchIndexError(
            422, "query_too_long", f"q exceeds {MAX_QUERY_CODEPOINTS} code points"
        )
    folded = unicodedata.normalize("NFKC", q).casefold()
    return folded.split()


def fts_match(tokens: list[str]) -> str:
    """Tokens → a bounded FTS5 MATCH: each token a quoted string, space = AND.
    No regex/wildcard/FTS grammar is ever exposed to the caller."""
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


# --------------------------------------------------------------------------- #
# Index build                                                                #
# --------------------------------------------------------------------------- #


def _facet_pairs(row: Mapping[str, Any]) -> list[tuple[str, str]]:
    pairs = [
        ("kind", str(row["entity_type"])),
        ("jurisdiction", str(row["jurisdiction"] or "unreported")),
        ("location", str(row["location_kind"])),
        ("source", str(row["source_id"])),
    ]
    tech = str(row.get("technology") or "")
    if tech:
        pairs.append(("technology", tech))
    return pairs


def build_search_index(
    records: Iterable[Mapping[str, Any]],
    *,
    publication_id: str,
    compartment: str,
    license_id: str,
    out: Path,
) -> dict[str, Any]:
    """Build the deterministic per-compartment FTS5 index at ``out``.

    ``records`` carries one mapping per eligible released record with keys
    ``record_key, entity_id, entity_type, label, jurisdiction, location_kind,
    source_id, claim_ids`` (+ optional ``technology``). Rows are sorted by
    ``record_key`` before insertion — the corpus order is the contract.
    Returns the ``sig.release-search-index/1`` descriptor (the bytes written
    to ``search_index.json`` beside the sqlite file).
    """
    rows = sorted(records, key=lambda r: str(r["record_key"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    conn = sqlite3.connect(out)
    try:
        conn.execute(f"PRAGMA page_size = {PAGE_SIZE}")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        conn.execute("PRAGMA user_version = 1")
        conn.execute("BEGIN")
        conn.executescript(_DDL)
        seq = 0
        for row in rows:
            seq += 1
            rk = str(row["record_key"])
            eid = str(row["entity_id"])
            et = str(row["entity_type"])
            label = str(row["label"] or "")
            jur = str(row["jurisdiction"] or "unreported")
            loc = str(row["location_kind"])
            src = str(row["source_id"])
            tech = str(row.get("technology") or "")
            claims = [str(c) for c in (row.get("claim_ids") or [])]
            conn.execute(
                "INSERT INTO records (record_seq, record_key, entity_id,"
                " entity_type, label, label_sort, jurisdiction, location_kind,"
                " source_id, technology, claim_ids)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    seq,
                    rk,
                    eid,
                    et,
                    label,
                    normalize_sort_key(label),
                    jur,
                    loc,
                    src,
                    tech,
                    canonical_json(claims).decode(),
                ),
            )
            conn.execute(
                "INSERT INTO records_fts (rowid, label, entity_id, source_id,"
                " jurisdiction) VALUES (?,?,?,?,?)",
                (seq, label, eid, src, jur),
            )
            conn.executemany(
                "INSERT INTO identifiers (norm_id, record_key) VALUES (?,?)",
                [(normalize_id(v), rk) for v in (eid, rk, *claims)],
            )
            conn.executemany(
                "INSERT INTO facets (facet, value, record_key) VALUES (?,?,?)",
                [(f, v, rk) for f, v in _facet_pairs(row)],
            )
        descriptor = {
            "schema": SEARCH_INDEX_SCHEMA,
            "version": SEARCH_INDEX_VERSION,
            "publication_id": publication_id,
            "compartment": compartment,
            "license": license_id,
            "format": {
                "tokenizer": TOKENIZER,
                "sort": SORT_ID,
                "cursor_version": CURSOR_VERSION,
                "page_size": PAGE_SIZE,
                "identifier_normalization": "trim+casefold",
                "label_sort": "NFKC+casefold+collapse-ws",
            },
            "facets": sorted(FACETS),
            "scope": {
                "indexed_records": seq,
                "eligible_records": seq,
                "excluded_records_by_reason": {},
            },
            "sqlite_version": sqlite3.sqlite_version,
        }
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?,?)",
            [
                ("schema", descriptor["schema"]),
                ("version", descriptor["version"]),
                ("publication_id", publication_id),
                ("compartment", compartment),
                ("license", license_id),
                ("format", canonical_json(descriptor["format"]).decode()),
                ("facets", canonical_json(descriptor["facets"]).decode()),
                ("scope", canonical_json(descriptor["scope"]).decode()),
                ("sqlite_version", sqlite3.sqlite_version),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return descriptor


def index_descriptor_from_file(path: Path) -> dict[str, Any]:
    """Re-read the index ``meta`` table as the descriptor (verification)."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()
    fmt = json.loads(meta["format"])
    return {
        "schema": meta["schema"],
        "version": meta["version"],
        "publication_id": meta["publication_id"],
        "compartment": meta["compartment"],
        "license": meta["license"],
        "format": fmt,
        "facets": json.loads(meta["facets"]),
        "scope": json.loads(meta["scope"]),
        "sqlite_version": meta["sqlite_version"],
    }


def check_index_contract(conn: sqlite3.Connection) -> dict[str, Any]:
    """The ``meta`` contract a serving layer pins before answering."""
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    if meta.get("schema") != SEARCH_INDEX_SCHEMA:
        raise SearchIndexError(503, "index_contract", "search index schema is not supported")
    fmt = json.loads(meta["format"])
    if fmt.get("tokenizer") != TOKENIZER or fmt.get("sort") != SORT_ID:
        raise SearchIndexError(
            503, "index_contract", "index format does not match the pinned contract"
        )
    if int(fmt.get("cursor_version") or 0) != CURSOR_VERSION:
        raise SearchIndexError(503, "index_contract", "cursor contract mismatch")
    meta["format"] = fmt
    meta["facets"] = json.loads(meta["facets"])
    meta["scope"] = json.loads(meta["scope"])
    return meta


# --------------------------------------------------------------------------- #
# Cursors                                                                     #
# --------------------------------------------------------------------------- #


def _filter_hash(q_norm: str | None, filters: Mapping[str, str]) -> str:
    payload = canonical_json({"f": dict(sorted(filters.items())), "q": q_norm})
    return hashlib.sha256(payload).hexdigest()[:16]


def encode_cursor(
    publication_id: str,
    compartment: str,
    filter_hash: str,
    last_key: tuple[str, str, str],
) -> str:
    payload = {
        "v": CURSOR_VERSION,
        "p": publication_id,
        "c": compartment,
        "fh": filter_hash,
        "s": SORT_ID,
        "k": list(last_key),
    }
    return urlsafe_b64encode(canonical_json(payload)).rstrip(b"=").decode()


def decode_cursor(
    cursor: str,
    *,
    publication_id: str,
    compartment: str,
    filter_hash: str,
) -> tuple[str, str, str]:
    """Validate + decode → the last emitted key. Malformed → 422; a cursor
    minted for another release/compartment/filter → 409 cursor_context_mismatch."""
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = json.loads(urlsafe_b64decode(cursor + pad))
    except Exception as exc:  # noqa: BLE001 - every decode failure is malformed
        raise SearchIndexError(422, "malformed_cursor", "cursor is not decodable") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("k"), list) or len(raw["k"]) != 3:
        raise SearchIndexError(422, "malformed_cursor", "cursor payload has the wrong shape")
    if (
        raw.get("v") != CURSOR_VERSION
        or raw.get("s") != SORT_ID
        or raw.get("p") != publication_id
        or raw.get("c") != compartment
        or raw.get("fh") != filter_hash
    ):
        raise SearchIndexError(
            409,
            "cursor_context_mismatch",
            "cursor was minted for a different release, compartment or filter set",
        )
    return (str(raw["k"][0]), str(raw["k"][1]), str(raw["k"][2]))


# --------------------------------------------------------------------------- #
# Query                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class SearchParams:
    """The normalized search request (post-validation)."""

    q_raw: str | None
    q_tokens: list[str]
    filters: dict[str, str]
    limit: int
    cursor: str | None
    unsupported: list[str] = field(default_factory=list)


def parse_params(
    *,
    q: str | None,
    kind: str | None,
    jurisdiction: str | None,
    source: str | None,
    location: str | None,
    technology: str | None,
    limit: int | None,
    cursor: str | None,
    extra: Iterable[str] = (),
) -> SearchParams:
    """Validate the request params; every failure is explicit, never guessed."""
    unsupported = sorted(str(e) for e in extra)
    if unsupported:
        raise SearchIndexError(
            422, "unsupported_query", f"unsupported parameters: {', '.join(unsupported)}"
        )
    filters: dict[str, str] = {}
    for name, raw in (
        ("kind", kind),
        ("jurisdiction", jurisdiction),
        ("source", source),
        ("location", location),
        ("technology", technology),
    ):
        if raw is None or str(raw).strip() == "":
            continue
        v = str(raw).strip()
        if name == "location":
            if v not in LOCATION_VALUES:
                raise SearchIndexError(
                    422,
                    "unsupported_query",
                    f"location must be one of {', '.join(LOCATION_VALUES)}",
                )
            if v == "any":
                continue  # `any` is the explicit no-filter marker
        if len(v) > 200:
            raise SearchIndexError(422, "unsupported_query", f"{name} filter is too long")
        filters[name] = v
    lim = DEFAULT_LIMIT if limit is None else limit
    if not (1 <= lim <= MAX_LIMIT):
        raise SearchIndexError(422, "unsupported_query", f"limit must be between 1 and {MAX_LIMIT}")
    tokens = normalize_query(q) if q is not None and q.strip() else []
    return SearchParams(
        q_raw=q if q is not None and q.strip() else None,
        q_tokens=tokens,
        filters=filters,
        limit=lim,
        cursor=cursor or None,
    )


def _exact_id_keys(conn: sqlite3.Connection, norm: str) -> list[str]:
    return [
        str(r[0])
        for r in conn.execute(
            "SELECT record_key FROM identifiers WHERE norm_id = ? ORDER BY record_key",
            (norm,),
        )
    ]


def _row_dict(row: tuple, publication_id: str, compartment: str, matched: list[str]) -> dict:
    (record_key, entity_id, entity_type, label, jur, loc, src, _claims, _ls) = row
    return {
        "record_key": record_key,
        "href": f"/r/{publication_id}/c/{compartment}/entity/{entity_type}/{entity_id}/",
        "json_href": f"/r/{publication_id}/c/{compartment}/entity/{entity_type}/{entity_id}.json",
        "label": label or None,
        "kind": entity_type,
        "jurisdiction": jur if jur != "unreported" else None,
        "jurisdiction_state": jur,
        "sources": [src] if src else [],
        "location": loc,
        "matched_fields": matched,
        "status": "published",
    }


def _progress_deadline(conn: sqlite3.Connection, deadline: float) -> None:
    def _tick() -> int:
        return 1 if time.monotonic() > deadline else 0

    conn.set_progress_handler(_tick, 10_000)


def search(
    conn: sqlite3.Connection,
    meta: Mapping[str, Any],
    params: SearchParams,
    *,
    denied: Callable[[tuple], bool] | None = None,
    deadline_seconds: float = QUERY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute one bounded search page over a verified ro index connection.

    * exact-id: a ``q`` equal to a normalized identifier resolves directly.
    * short q (<3 chars): exact-id, then jurisdiction-facet match, else 422.
    * FTS: tokens ANDed over label/entity_id/source_id/jurisdiction columns.
    * keyset pagination on (label_sort, entity_type, entity_id); the cursor
      tracks the last EMITTED row so re-evaluated withdrawals never duplicate
      or skip a key.
    * ``denied`` is evaluated per candidate row before pagination — denied
      records are skipped (never returned), so pages stay dense and nothing
      withheld leaks through the result list.
    """
    publication_id = str(meta["publication_id"])
    compartment = str(meta["compartment"])
    deadline = time.monotonic() + max(0.001, deadline_seconds)
    _progress_deadline(conn, deadline)

    exact_keys: list[str] | None = None
    q_norm: str | None = None
    if params.q_raw is not None:
        q_norm = " ".join(params.q_tokens)
        nid = normalize_id(params.q_raw)
        if nid:
            keys = _exact_id_keys(conn, nid)
            if keys:
                exact_keys = keys
        if (
            exact_keys is None
            and len(params.q_tokens) == 1
            and len(params.q_tokens[0]) < MIN_TEXT_QUERY
        ):
            # Two-letter place codes resolve through the jurisdiction facet —
            # never rejected as bare text (S4 contract).
            hit = conn.execute(
                "SELECT value FROM facets WHERE facet = 'jurisdiction'"
                " AND value = ? COLLATE NOCASE LIMIT 1",
                (params.q_raw.strip(),),
            ).fetchone()
            if hit is None:
                raise SearchIndexError(
                    422,
                    "query_too_short",
                    f"text queries need at least {MIN_TEXT_QUERY} characters; "
                    "short strings must be an exact identifier or a jurisdiction facet",
                )
            params = SearchParams(
                q_raw=params.q_raw,
                q_tokens=[],
                filters={**params.filters, "jurisdiction": str(hit[0])},
                limit=params.limit,
                cursor=params.cursor,
            )
            q_norm = None

    fh = _filter_hash(q_norm, params.filters)
    last_key = None
    if params.cursor:
        last_key = decode_cursor(
            params.cursor,
            publication_id=publication_id,
            compartment=compartment,
            filter_hash=fh,
        )

    where: list[str] = []
    bind: dict[str, Any] = {}
    matched: list[str] = []
    if exact_keys is not None:
        where.append("r.record_key IN (SELECT record_key FROM identifiers WHERE norm_id = :nid)")
        bind["nid"] = normalize_id(params.q_raw or "")
        matched.append("identifier")
    else:
        for name, value in params.filters.items():
            col = FACETS[name]
            where.append(f"r.{col} = :f_{name}")
            bind[f"f_{name}"] = value
            matched.append(name)
        if params.q_tokens:
            where.append(
                "r.record_seq IN (SELECT rowid FROM records_fts WHERE records_fts MATCH :match)"
            )
            bind["match"] = fts_match(params.q_tokens)
            matched.append("text")
    if last_key is not None:
        where.append(_KEYSET_AFTER)
        bind.update({"ls": last_key[0], "et": last_key[1], "eid": last_key[2]})

    sql = (
        "SELECT r.record_key, r.entity_id, r.entity_type, r.label,"
        " r.jurisdiction, r.location_kind, r.source_id, r.claim_ids, r.label_sort"
        " FROM records r"
    )
    if where:
        sql += " WHERE " + " AND ".join(f"({w})" for w in where)
    sql += f" ORDER BY {_KEYSET_ORDER}"

    out_rows: list[tuple] = []
    exhausted = False
    try:
        cur = conn.execute(sql, bind)
        for row in cur:
            # Row-granular deadline — the progress handler alone can miss a
            # fast index scan (the 2 s budget is a hard limit, not a hint).
            if time.monotonic() > deadline:
                raise SearchIndexError(
                    503,
                    "query_timeout",
                    f"query exceeded the {QUERY_TIMEOUT_SECONDS:.0f}s execution budget",
                )
            if denied is not None and denied(row):
                continue  # withdrawal barrier: skipped before pagination
            out_rows.append(row)
            if len(out_rows) > params.limit:
                break
        else:
            exhausted = True
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc):
            raise SearchIndexError(
                503,
                "query_timeout",
                f"query exceeded the {QUERY_TIMEOUT_SECONDS:.0f}s execution budget",
            ) from exc
        raise
    finally:
        conn.set_progress_handler(None, 0)

    scope = meta.get("scope") or {}
    emitted_rows = out_rows[: params.limit]
    has_more = not exhausted and len(out_rows) > params.limit

    def _cursor_for(row: tuple) -> str:
        return encode_cursor(
            publication_id, compartment, fh, (str(row[8]), str(row[2]), str(row[1]))
        )

    def _assemble(rows: list[tuple], next_cursor: str | None, truncated: bool) -> dict:
        return {
            "publication_id": publication_id,
            "compartment": compartment,
            "license": str(meta.get("license") or ""),
            "query": {
                "q": params.q_raw,
                "normalized": q_norm,
                "exact_id": exact_keys is not None,
                "filters": params.filters,
            },
            "scope": {
                "indexed_records": scope.get("indexed_records"),
                "eligible_records": scope.get("eligible_records"),
                "excluded_records_by_reason": scope.get("excluded_records_by_reason") or {},
            },
            "results": [_row_dict(r, publication_id, compartment, matched) for r in rows],
            "next_cursor": next_cursor,
            "total_matches": {"value": None, "relation": "not_computed"},
            "truncated": truncated,
        }

    result = _assemble(
        emitted_rows,
        _cursor_for(emitted_rows[-1]) if has_more and emitted_rows else None,
        False,
    )
    # The <=100 KiB wire bound: drop tail rows (re-minting the cursor on the
    # last EMITTED key — nothing is skipped or duplicated) rather than ever
    # exceed the ceiling.
    while len(emitted_rows) > 1 and len(canonical_json(result)) > MAX_BODY_BYTES:
        emitted_rows = emitted_rows[:-1]
        result = _assemble(emitted_rows, _cursor_for(emitted_rows[-1]), True)
    return result


def facet_values(conn: sqlite3.Connection, facet: str) -> list[tuple[str, int]]:
    """``[(value, record_count)]`` for one facet — used by the no-JS form."""
    if facet not in FACETS:
        raise SearchIndexError(422, "unsupported_query", f"unknown facet {facet!r}")
    return [
        (str(v), int(n))
        for v, n in conn.execute(
            "SELECT value, COUNT(*) FROM facets WHERE facet = ? GROUP BY value ORDER BY value",
            (facet,),
        )
    ]
