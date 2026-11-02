# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The search index v2 builder (P36.31 / K3 SRCH-01 — SIG-UI-073, SIG-UI-074,
SIG-SRCH-004, SIG-SRCH-005, SIG-SRCH-011).

Three artifacts, all ``sig.release-search-index/2``, all built from the bound
release projection — never the live claim spine (SIG-UI-076):

* ``search_index_v2.sqlite`` — ONE compact record index per compartment: a
  contentless weighted FTS5 over ``name`` (the published label, or a *marked*
  derived name under the interim rule until K2's derivation lands), ``place``
  (jurisdiction name + country + code — the K4 place text) and ``source``
  (the registry source name + id), joined back to a normalised ``records``
  table carrying the entity id and two filter indexes (place, source).
* ``claim_ref.sqlite`` — a compact claim → record table per compartment
  (``claim BLOB PRIMARY KEY … WITHOUT ROWID``; UUID claim ids pack to 16
  bytes) keeping SIG-FIND-003's exact claim-id lookup at a fraction of the
  v1 text ``identifiers`` table.
* ``releases/<pub>/search/catalog.sqlite`` — ONE catalog index for every
  entry type (SIG-UI-073): places from the JUR-01 jurisdiction registry
  (``sig.jurisdiction-registry/1``) or, in the interim, the export's
  ``jurisdiction_key_map`` (the NE gazetteer stays HG-03 gated); sources with
  their registry facet fields; the technology vocabulary
  (``ontology/vocab/technology.yaml``, ``evidence_signature`` synonyms);
  K2 entities as present; K8 evidence documents; content pages. Weighted
  FTS5 (``porter unicode61 remove_diacritics 2`` + prefix 2/3), a trigram
  table over names and alternates, an ``exact_names`` table (SIG-SRCH-004 —
  official/alternate/identifier names resolve first), and the ``aliases``
  table (SIG-SRCH-005 — case-sensitive acronym expansions, never
  word-matched).

The alias registry itself is DATA, not code: ``data/search_aliases.toml``
(K3 §4.4 — reviewed like a registry row; only abbreviations and official
alternate names; every alias shows its expansion and its cited source).

Determinism: fixed page size, journal off, a fixed application id, rows
inserted in sorted order inside one transaction — identical inputs on an
identical SQLite build reproduce identical bytes (the recording version is
pinned in ``meta`` + the descriptor so a library change is visible, never
silent).

Release-verified (SIG-SRCH-011): every descriptor pins the bound release
(publication id, release label, as-of-world) and its hashed inputs;
``verify_search_index`` streams the file in 1 MiB chunks, hashes it, and
compares against the integrity manifest before any ``mode=ro`` open — a
drifted artifact fails, it is never silently served.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from policy.sensitivity import assert_public_layer_subject

from .manifest import canonical_json
from .search_index import normalize_id, normalize_sort_key

#: The machine contract stamped on every v2 descriptor and ``meta`` table.
SEARCH_INDEX_V2_SCHEMA = "sig.release-search-index/2"
#: The format version — a descriptor input, so an index-format change mints
#: a new publication namespace (two-stage identity, ADR-132).
SEARCH_INDEX_V2_VERSION = "release-search-index/2"
#: Artifact names. The v1 ``search_index.sqlite``/``search_index.json``
#: artifacts keep their names (SRCH-03 flips serving); v2 files are
#: additive until then.
RECORD_INDEX_V2_FILE = "search_index_v2.sqlite"
RECORD_INDEX_V2_DESCRIPTOR_FILE = "search_index_v2.json"
CLAIM_REF_FILE = "claim_ref.sqlite"
CATALOG_V2_FILE = "catalog.sqlite"
CATALOG_V2_DESCRIPTOR_FILE = "catalog.json"
ALIASES_RESOLVED_FILE = "aliases.json"
#: The committed alias registry (K3 §4.4).
DEFAULT_ALIASES_PATH = Path(__file__).resolve().parent / "data" / "search_aliases.toml"
#: Fixed physical layout (determinism) + a registered application id.
PAGE_SIZE = 4096
APPLICATION_ID_V2 = 0x53494732  # "SIG2"
#: The pinned tokenizer + weight profiles (recorded in every index).
TOKENIZER_V2 = "porter unicode61 remove_diacritics 2"
CATALOG_PREFIX_LENGTHS = (2, 3)
#: bm25 column weights applied at query time — pinned here so the serving
#: layer and the descriptor never disagree.
RECORD_BM25_WEIGHTS = {"name": 10.0, "place": 2.0, "source": 1.0}
CATALOG_BM25_WEIGHTS = {"name": 10.0, "alternates": 6.0, "context": 1.0}
#: The type prior the query engine multiplies bm25 by (K3 §4.2 stage 4).
CATALOG_TYPE_PRIOR = {
    "place": 1.4,
    "entity": 1.2,
    "organization": 1.2,
    "technology": 1.0,
    "source": 1.0,
    "document": 0.9,
    "page": 0.9,
}
CATALOG_DOC_TYPES = (
    "place",
    "entity",
    "organization",
    "technology",
    "source",
    "document",
    "page",
)
#: Chunk size for the streaming integrity read (K3 §5.5 — verify and copy,
#: never read whole).
STREAM_CHUNK_BYTES = 1 << 20
#: The interim derived-name rule (the ticket records "K2's rule or an
#: interim rule"): "<kind phrase> · <registry source name>". Marked, so a
#: reader always sees the name is derived (SIG-SRCH-007).
INTERIM_NAME_RULE = "kind-phrase + registry-source-name (P36.31 interim; K2 derivation pending)"
#: Human phrases per record kind for the interim derived name.
KIND_PHRASES = {
    "camera_site": "Camera site",
    "camera": "Camera site",
    "site": "Camera site",
    "deployment": "Camera site",
    "sensor": "Sensor site",
    "organization": "Organization",
    "organisation": "Organisation",
    "agency": "Agency",
    "vendor": "Vendor",
    "jurisdiction": "Place",
    "document": "Document",
}


class SearchIndexV2Error(Exception):
    """One typed v2 search failure — machine code + public detail."""

    def __init__(self, code: str, detail: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.extra = extra or {}


# --------------------------------------------------------------------------- #
# The alias registry (K3 §4.4)                                                #
# --------------------------------------------------------------------------- #

_ALIAS_REQUIRED = ("key", "case_sensitive", "expansion", "source_url", "added_by", "reviewed_on")
_ALIAS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"^https?://\S+$")


def load_search_aliases(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load + validate ``search_aliases.toml`` — fail closed (SIG-ENG-042).

    Rows are data reviewed like registry rows: ``key``, ``case_sensitive``,
    ``expansion``, ``source_url``, ``added_by``, ``reviewed_on``, optional
    ``target`` (a SIG id the alias resolves to, else empty). Returns the
    rows sorted by key. Any malformed row is a build error — never a
    silently skipped alias.
    """
    import tomllib

    p = Path(path) if path is not None else DEFAULT_ALIASES_PATH
    doc = tomllib.loads(p.read_text(encoding="utf-8"))
    rows = doc.get("aliases")
    if not isinstance(rows, list):
        raise SearchIndexV2Error("alias_registry", f"{p}: missing [[aliases]] rows")
    failures: list[str] = []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, dict):
            failures.append(f"aliases[{i}]: not a table")
            continue
        for field_name in _ALIAS_REQUIRED:
            if field_name not in raw:
                failures.append(f"aliases[{i}]: missing {field_name!r}")
        key = str(raw.get("key") or "")
        if not key:
            failures.append(f"aliases[{i}]: empty key")
        elif key in seen:
            failures.append(f"aliases[{i}] {key!r}: duplicate key")
        seen.add(key)
        if not isinstance(raw.get("case_sensitive"), bool):
            failures.append(f"aliases[{i}] {key!r}: case_sensitive must be a boolean")
        if not str(raw.get("expansion") or ""):
            failures.append(f"aliases[{i}] {key!r}: empty expansion")
        if not _URL_RE.match(str(raw.get("source_url") or "")):
            failures.append(f"aliases[{i}] {key!r}: source_url must be an http(s) URL")
        if not _ALIAS_DATE_RE.match(str(raw.get("reviewed_on") or "")):
            failures.append(f"aliases[{i}] {key!r}: reviewed_on must be YYYY-MM-DD")
        target = raw.get("target")
        if target is not None and not isinstance(target, str):
            failures.append(f"aliases[{i}] {key!r}: target must be a string when present")
        out.append(
            {
                "key": key,
                "case_sensitive": bool(raw.get("case_sensitive")),
                "expansion": str(raw.get("expansion") or ""),
                "target": str(raw.get("target") or ""),
                "source_url": str(raw.get("source_url") or ""),
                "added_by": str(raw.get("added_by") or ""),
                "reviewed_on": str(raw.get("reviewed_on") or ""),
            }
        )
    if failures:
        raise SearchIndexV2Error(
            "alias_registry",
            "search_aliases.toml fails validation:\n  " + "\n  ".join(failures),
        )
    return sorted(out, key=lambda r: r["key"])


def aliases_sha256(path: Path | str | None = None) -> str:
    """sha256 of the committed alias registry — a descriptor input."""
    p = Path(path) if path is not None else DEFAULT_ALIASES_PATH
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Record index (per compartment)                                              #
# --------------------------------------------------------------------------- #

_RECORD_DDL = """
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE records (
  record_seq INTEGER PRIMARY KEY,
  record_key TEXT NOT NULL UNIQUE,
  entity_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  name TEXT NOT NULL,
  name_basis TEXT NOT NULL,
  place_key TEXT NOT NULL,
  place_text TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  technology TEXT NOT NULL
);
CREATE VIRTUAL TABLE records_fts USING fts5(
  name, place, source, tokenize='porter unicode61 remove_diacritics 2',
  content=''
);
CREATE INDEX records_place ON records (place_key, name, record_key);
CREATE INDEX records_source ON records (source_id, name, record_key);
"""

_CLAIM_REF_DDL = """
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE claim_ref (
  claim BLOB PRIMARY KEY,
  record_key TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX claim_ref_record ON claim_ref (record_key, claim);
"""


def _claim_blob(claim_id: str) -> bytes:
    """claim id → the compact key bytes: UUIDs pack to 16 bytes (the
    ``BLOB(16)`` the K3 prototype measured); anything else keeps its UTF-8
    bytes so exact lookup stays exact."""
    s = claim_id.strip()
    try:
        return uuid.UUID(s).bytes
    except (ValueError, AttributeError, TypeError):
        return s.encode("utf-8")


def derive_record_name(row: Mapping[str, Any], source_name: str) -> tuple[str, str]:
    """The display name + its basis. The published label wins (its recorded
    ``label_basis`` is K2's rule); an unlabelled record gets the interim
    derived name — always *marked* (SIG-SRCH-007)."""
    label = row.get("label")
    if label:
        basis = str(row.get("label_basis") or "source_label")
        return str(label), basis
    kind = str(row.get("entity_type") or "")
    phrase = KIND_PHRASES.get(kind, kind.replace("_", " ").title() if kind else "Record")
    return f"{phrase} · {source_name}", "derived_interim"


def _open_index(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA page_size = {PAGE_SIZE}")
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID_V2}")
    conn.execute("PRAGMA user_version = 2")
    conn.execute("BEGIN")
    return conn


def _meta_rows(
    descriptor: Mapping[str, Any],
    extra: Sequence[tuple[str, str]] = (),
    *,
    kind: str | None = None,
) -> list[tuple[str, str]]:
    rows = [
        ("schema", SEARCH_INDEX_V2_SCHEMA),
        ("version", SEARCH_INDEX_V2_VERSION),
        ("publication_id", str(descriptor["publication_id"])),
        ("release_label", str(descriptor.get("release_label") or "")),
        ("as_of_world", str(descriptor.get("as_of_world") or "")),
        ("kind", str(kind or descriptor["kind"])),
        ("format", canonical_json(descriptor["format"]).decode()),
        ("scope", canonical_json(descriptor["scope"]).decode()),
        ("sqlite_version", sqlite3.sqlite_version),
    ]
    if "compartment" in descriptor:
        rows.append(("compartment", str(descriptor["compartment"])))
    if "license" in descriptor:
        rows.append(("license", str(descriptor["license"])))
    rows.extend(extra)
    return rows


def _descriptor_base(
    *,
    kind: str,
    publication_id: str,
    release_label: str | None,
    as_of_world: str | None,
    fmt: Mapping[str, Any],
    scope: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SEARCH_INDEX_V2_SCHEMA,
        "version": SEARCH_INDEX_V2_VERSION,
        "kind": kind,
        "publication_id": publication_id,
        "release_label": release_label,
        "as_of_world": as_of_world,
        "format": dict(fmt),
        "scope": dict(scope),
        "inputs": dict(inputs),
        "sqlite_version": sqlite3.sqlite_version,
    }


def build_record_index_v2(
    records: Iterable[Mapping[str, Any]],
    *,
    publication_id: str,
    compartment: str,
    license_id: str,
    out: Path,
    claim_ref_out: Path | None = None,
    release_label: str | None = None,
    as_of_world: str | None = None,
    source_names: Mapping[str, str] | None = None,
    place_names: Mapping[str, str] | None = None,
    aliases_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build the compact per-compartment v2 record index + ``claim_ref``.

    ``records`` carries one mapping per eligible released record with keys
    ``record_key, entity_id, entity_type, label, jurisdiction, claim_ids``
    (+ optional ``label_basis``, ``place_text``, ``source_id``,
    ``technology``). ``source_names``/``place_names`` map ids/keys to the
    registry display strings; an unmapped id falls back to the id itself so
    nothing is silently dropped. Writes ``out`` (the record index) and
    ``claim_ref_out`` (defaults to ``claim_ref.sqlite`` beside ``out``).
    Returns the ``sig.release-search-index/2`` descriptor with the sibling
    file digests under ``files``.
    """
    rows = sorted(records, key=lambda r: str(r["record_key"]))
    # Same fail-closed gate as v1 (P35.66, SIG-PUB-011/013): refuse BEFORE
    # opening the index.
    for row in rows:
        assert_public_layer_subject(
            str(row.get("entity_type") or ""),
            residential_parcel_flag=bool(row.get("residential_parcel_flag")),
            surface="search_index_v2",
        )
    source_names = dict(source_names or {})
    place_names = dict(place_names or {})
    claim_ref_out = claim_ref_out or out.parent / CLAIM_REF_FILE

    fmt = {
        "tokenizer": TOKENIZER_V2,
        "bm25_weights": RECORD_BM25_WEIGHTS,
        "contentless": True,
        "filter_indexes": ["place_key", "source_id"],
        "page_size": PAGE_SIZE,
        "application_id": APPLICATION_ID_V2,
        "name_rule": INTERIM_NAME_RULE,
        "identifier_normalization": "trim+casefold",
    }
    # The scope + inputs are computed BEFORE the meta rows are written —
    # the descriptor and the in-file meta table must agree byte-for-byte.
    claim_ids_seen = sum(len(row.get("claim_ids") or []) for row in rows)
    derived_names = 0
    name_plan: list[tuple[str, str]] = []
    for row in rows:
        src = str(row.get("source_id") or "")
        name, name_basis = derive_record_name(row, source_names.get(src, src))
        if name_basis.startswith("derived"):
            derived_names += 1
        name_plan.append((name, name_basis))
    descriptor = _descriptor_base(
        kind="record-index",
        publication_id=publication_id,
        release_label=release_label,
        as_of_world=as_of_world,
        fmt=fmt,
        scope={
            "indexed_records": len(rows),
            "eligible_records": len(rows),
            "derived_names": derived_names,
            "claim_refs": claim_ids_seen,
            "excluded_records_by_reason": {},
        },
        inputs={
            "aliases_sha256": aliases_sha256(aliases_path),
            "source_names_sha256": sha256_canonical(dict(sorted(source_names.items()))),
            "place_names_sha256": sha256_canonical(dict(sorted(place_names.items()))),
        },
    )
    descriptor["compartment"] = compartment
    descriptor["license"] = license_id

    conn = _open_index(out)
    try:
        conn.executescript(_RECORD_DDL)
        seq = 0
        for row, (name, name_basis) in zip(rows, name_plan, strict=True):
            seq += 1
            rk = str(row["record_key"])
            eid = str(row["entity_id"])
            et = str(row["entity_type"])
            src = str(row.get("source_id") or "")
            source_name = source_names.get(src, src)
            place_key = str(row.get("jurisdiction") or row.get("place_key") or "unreported")
            place_text = str(row.get("place_text") or place_names.get(place_key) or place_key)
            tech = str(row.get("technology") or "")
            conn.execute(
                "INSERT INTO records (record_seq, record_key, entity_id,"
                " entity_type, name, name_basis, place_key, place_text,"
                " source_id, source_name, technology)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    seq,
                    rk,
                    eid,
                    et,
                    name,
                    name_basis,
                    place_key,
                    place_text,
                    src,
                    source_name,
                    tech,
                ),
            )
            conn.execute(
                "INSERT INTO records_fts (rowid, name, place, source) VALUES (?,?,?,?)",
                (seq, name, place_text, f"{source_name} {src}".strip()),
            )
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?,?)",
            _meta_rows(descriptor),
        )
        conn.commit()
    finally:
        conn.close()

    cref = _open_index(claim_ref_out)
    try:
        cref.executescript(_CLAIM_REF_DDL)
        pairs: list[tuple[bytes, str]] = []
        for row in rows:
            rk = str(row["record_key"])
            for cid in row.get("claim_ids") or []:
                pairs.append((_claim_blob(str(cid)), rk))
        pairs.sort()
        cref.executemany("INSERT INTO claim_ref (claim, record_key) VALUES (?,?)", pairs)
        cref.executemany(
            "INSERT INTO meta (key, value) VALUES (?,?)",
            _meta_rows(
                descriptor,
                extra=(("claim_refs", str(len(pairs))),),
                kind="claim-ref",
            ),
        )
        cref.commit()
    finally:
        cref.close()

    descriptor["files"] = {
        RECORD_INDEX_V2_FILE: _file_digest(out),
        CLAIM_REF_FILE: _file_digest(claim_ref_out),
    }
    return descriptor


def sha256_canonical(obj: Any) -> str:
    """sha256 over the canonical JSON of an input mapping."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "byte_size": len(data)}


def claim_ref_lookup(claim_ref_db: Path, claim_id: str) -> list[str]:
    """Exact claim-id → record keys (SIG-FIND-003)."""
    conn = sqlite3.connect(f"file:{claim_ref_db}?mode=ro", uri=True)
    try:
        return [
            str(r[0])
            for r in conn.execute(
                "SELECT record_key FROM claim_ref WHERE claim = ? ORDER BY record_key",
                (_claim_blob(claim_id),),
            )
        ]
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Catalog index (one per release)                                             #
# --------------------------------------------------------------------------- #

_CATALOG_DDL = """
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE docs (
  doc_seq INTEGER PRIMARY KEY,
  doc_id TEXT NOT NULL UNIQUE,
  doc_type TEXT NOT NULL,
  name TEXT NOT NULL,
  href TEXT NOT NULL,
  meta TEXT NOT NULL
);
CREATE VIRTUAL TABLE docs_fts USING fts5(
  name, alternates, context,
  tokenize='porter unicode61 remove_diacritics 2',
  prefix='2 3'
);
CREATE TABLE exact_names (
  norm_name TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  basis TEXT NOT NULL,
  PRIMARY KEY (norm_name, doc_id, basis)
) WITHOUT ROWID;
CREATE TABLE trigrams (
  gram TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  PRIMARY KEY (gram, doc_id)
) WITHOUT ROWID;
CREATE TABLE aliases (
  alias_key TEXT PRIMARY KEY,
  case_sensitive INTEGER NOT NULL,
  expansion TEXT NOT NULL,
  target TEXT NOT NULL,
  source_url TEXT NOT NULL,
  added_by TEXT NOT NULL,
  reviewed_on TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX docs_type ON docs (doc_type, doc_id);
"""


def _trigrams(text: str) -> set[str]:
    """The character trigrams of a normalized name/alternate (substring +
    edit-distance fallback, K3 §4.2 — SIG-IDENT-024: suggests only, never
    merges)."""
    norm = normalize_sort_key(text)
    if len(norm) < 3:
        return {norm} if norm else set()
    return {norm[i : i + 3] for i in range(len(norm) - 2)}


def build_catalog_index(
    docs: Iterable[Mapping[str, Any]],
    *,
    publication_id: str,
    out: Path,
    aliases: Sequence[Mapping[str, Any]] | None = None,
    release_label: str | None = None,
    as_of_world: str | None = None,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the release-level catalog index.

    ``docs`` carries one mapping per catalog entry: ``doc_id``, ``type``
    (place/entity/organization/technology/source/document/page), ``name``,
    ``href`` + optional ``alternates``, ``context``, ``meta``. Rows are
    sorted by ``doc_id``; a duplicate ``doc_id`` is a build error, never a
    silently-kept row. ``aliases`` are the validated ``load_search_aliases``
    rows (loaded from the default registry when omitted — a None alias
    registry is still recorded in scope). Returns the descriptor.
    """
    if aliases is None:
        aliases = load_search_aliases()
    doc_rows = sorted((dict(d) for d in docs), key=lambda d: str(d.get("doc_id") or ""))
    seen: set[str] = set()
    for d in doc_rows:
        did = str(d.get("doc_id") or "")
        if not did:
            raise SearchIndexV2Error("catalog", "a catalog doc has an empty doc_id")
        if did in seen:
            raise SearchIndexV2Error("catalog", f"duplicate catalog doc_id {did!r}")
        seen.add(did)
        if str(d.get("type") or "") not in CATALOG_DOC_TYPES:
            raise SearchIndexV2Error(
                "catalog",
                f"catalog doc {did!r}: type {d.get('type')!r} not in {CATALOG_DOC_TYPES}",
            )

    fmt = {
        "tokenizer": TOKENIZER_V2,
        "bm25_weights": CATALOG_BM25_WEIGHTS,
        "type_prior": CATALOG_TYPE_PRIOR,
        "prefix_lengths": list(CATALOG_PREFIX_LENGTHS),
        "page_size": PAGE_SIZE,
        "application_id": APPLICATION_ID_V2,
        "exact_name_bases": ["official", "alternate", "identifier", "alias"],
        "identifier_normalization": "trim+casefold",
        "name_normalization": "NFKC+casefold+collapse-ws",
    }
    by_type: dict[str, int] = {}
    for d in doc_rows:
        t = str(d["type"])
        by_type[t] = by_type.get(t, 0) + 1
    descriptor = _descriptor_base(
        kind="catalog",
        publication_id=publication_id,
        release_label=release_label,
        as_of_world=as_of_world,
        fmt=fmt,
        scope={
            "catalog_docs": len(doc_rows),
            "by_type": {k: by_type[k] for k in sorted(by_type)},
            "aliases": len(aliases),
        },
        inputs=dict(inputs or {}),
    )

    conn = _open_index(out)
    try:
        conn.executescript(_CATALOG_DDL)
        seq = 0
        exact: list[tuple[str, str, str]] = []
        grams: list[tuple[str, str]] = []
        for d in doc_rows:
            seq += 1
            did = str(d["doc_id"])
            dtype = str(d["type"])
            name = str(d.get("name") or "")
            alternates = sorted({str(a) for a in (d.get("alternates") or []) if str(a)})
            context = str(d.get("context") or "")
            conn.execute(
                "INSERT INTO docs (doc_seq, doc_id, doc_type, name, href, meta)"
                " VALUES (?,?,?,?,?,?)",
                (
                    seq,
                    did,
                    dtype,
                    name,
                    str(d.get("href") or ""),
                    canonical_json(dict(d.get("meta") or {})).decode(),
                ),
            )
            conn.execute(
                "INSERT INTO docs_fts (rowid, name, alternates, context) VALUES (?,?,?,?)",
                (seq, name, " ".join(alternates), context),
            )
            exact.append((normalize_id(name), did, "official"))
            for a in alternates:
                exact.append((normalize_id(a), did, "alternate"))
            doc_grams = set(_trigrams(name))
            for a in alternates:
                doc_grams |= _trigrams(a)
            for t in sorted(doc_grams):
                grams.append((t, did))
        # Case-INsensitive aliases join exact-name resolution as their own
        # basis. A case-SENSITIVE acronym (SIG-SRCH-005) is deliberately
        # NOT added: matching it must compare the verbatim ``alias_key``
        # against the raw query token — a normalized lookup would present
        # a word-match ("ice") as the acronym (ICE), which is forbidden.
        for al in aliases:
            if not al.get("case_sensitive"):
                exact.append((normalize_id(str(al["key"])), f"alias:{al['key']}", "alias"))
            conn.execute(
                "INSERT INTO aliases (alias_key, case_sensitive, expansion,"
                " target, source_url, added_by, reviewed_on)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    str(al["key"]),
                    1 if al.get("case_sensitive") else 0,
                    str(al["expansion"]),
                    str(al.get("target") or ""),
                    str(al["source_url"]),
                    str(al["added_by"]),
                    str(al["reviewed_on"]),
                ),
            )
        exact.sort()
        grams.sort()
        conn.executemany(
            "INSERT INTO exact_names (norm_name, doc_id, basis) VALUES (?,?,?)",
            exact,
        )
        conn.executemany(
            "INSERT INTO trigrams (gram, doc_id) VALUES (?,?)",
            grams,
        )
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?,?)",
            _meta_rows(descriptor),
        )
        conn.commit()
    finally:
        conn.close()
    descriptor["files"] = {CATALOG_V2_FILE: _file_digest(out)}
    return descriptor


# --------------------------------------------------------------------------- #
# Catalog doc loaders — JUR-01 places, registry sources, the vocabulary       #
# --------------------------------------------------------------------------- #


def place_docs_from_registry(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """JUR-01 ``sig.jurisdiction-registry/1`` rows → place catalog docs.

    Names + alternates + identifier values (ISO and postal codes — the
    SIG-SRCH-004 exact-name surface); the parent jkey names the homonym
    parent shown on the card (SIG-UI-074)."""
    docs = []
    for r in rows:
        jkey = str(r.get("jkey") or "")
        alternates = [str(a) for a in (r.get("alternates") or [])]
        for ident in r.get("identifiers") or []:
            v = str((ident or {}).get("value") or "")
            if v:
                alternates.append(v)
        docs.append(
            {
                "doc_id": f"place:{jkey}",
                "type": "place",
                "name": str(r.get("name") or jkey),
                "alternates": sorted(set(alternates)),
                "context": str(r.get("parent") or ""),
                "href": f"/dossier/{r.get('slug_path') or jkey}/",
                "meta": {
                    "jkey": jkey,
                    "level": str(r.get("level") or ""),
                    "parent": str(r.get("parent") or ""),
                    "vintage": str(r.get("vintage") or ""),
                },
            }
        )
    return docs


def place_docs_from_key_map(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The interim gazetteer: ``web/jurisdiction_key_map.json`` entries →
    place docs while the NE/interim gazetteer stays HG-03 gated. ISO and
    postal codes come off the jkey + code fields."""
    docs = []
    for e in entries:
        jkey = str(e.get("jkey") or "")
        alternates = {
            str(e.get("code") or ""),
            str(e.get("country_code") or ""),
        }
        # iso3166-2:US-OK → the USPS code "OK"; iso3166-1:US → "US".
        tail = jkey.rsplit(":", 1)[-1]
        if tail:
            alternates.add(tail)
            if "-" in tail:
                alternates.add(tail.split("-", 1)[1])
        docs.append(
            {
                "doc_id": f"place:{jkey}",
                "type": "place",
                "name": str(e.get("display_name") or e.get("name") or jkey),
                "alternates": sorted(a for a in alternates if a),
                "context": str(e.get("parent") or ""),
                "href": f"/dossier/{e.get('slug_path') or jkey}/",
                "meta": {
                    "jkey": jkey,
                    "level": str(e.get("level") or ""),
                    "parent": str(e.get("parent") or ""),
                    "scheme": str(e.get("scheme") or ""),
                    "vintage": str(e.get("vintage") or ""),
                },
            }
        )
    return docs


#: The registry source fields the catalog keeps as facet meta (the K9 facet
#: fields that exist today; a missing key is simply absent).
_SOURCE_FACET_FIELDS = (
    "source_kind",
    "default_tier",
    "compact_status",
    "custody_posture",
    "robots_policy",
    "homepage_url",
)


def source_docs_from_registry(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """``connectors`` ``sources.toml`` (parsed) → source catalog docs with
    the facet fields SIG-SRCH-002's typed result cards show."""
    docs = []
    for sid in sorted(registry):
        row = registry[sid] or {}
        meta: dict[str, Any] = {"source_id": sid}
        for f in _SOURCE_FACET_FIELDS:
            if row.get(f) is not None:
                meta[f] = row[f]
        rights = row.get("rights") or {}
        if rights.get("spdx"):
            meta["license"] = rights["spdx"]
        redist = row.get("redistribution") or {}
        if redist.get("lane"):
            meta["lane"] = redist["lane"]
        context = " ".join(str(row.get(k) or "") for k in ("source_kind", "default_tier")).strip()
        docs.append(
            {
                "doc_id": f"source:{sid}",
                "type": "source",
                "name": str(row.get("name") or sid),
                "alternates": [sid],
                "context": context,
                "href": f"/sources/{sid}/",
                "meta": meta,
            }
        )
    return docs


def technology_docs_from_vocab(vocab: Mapping[str, Any]) -> list[dict[str, Any]]:
    """``ontology/vocab/technology.yaml`` (parsed) → technology docs; the
    ``evidence_signature`` synonyms become alternates (K3 §4.4). Retired
    slugs stay resolvable but are marked (SIG-ONTO-053)."""
    docs = []
    for domain in vocab.get("domains") or []:
        dlabel = str(domain.get("label") or domain.get("slug") or "")
        for family in domain.get("families") or []:
            flabel = str(family.get("label") or family.get("slug") or "")
            for tech in family.get("technologies") or []:
                slug = str(tech.get("slug") or "")
                status = str(tech.get("status") or "active")
                alternates = [str(s) for s in (tech.get("evidence_signature") or [])]
                superseded = str(tech.get("superseded_by") or "")
                meta = {
                    "slug": slug,
                    "family": flabel,
                    "domain": dlabel,
                    "salience": str(tech.get("salience") or ""),
                    "status": status,
                }
                if superseded:
                    meta["superseded_by"] = superseded
                docs.append(
                    {
                        "doc_id": f"technology:{slug}",
                        "type": "technology",
                        "name": str(tech.get("label") or slug),
                        "alternates": sorted(set(alternates)),
                        "context": f"{dlabel} — {flabel}".strip(" —"),
                        "href": f"/search/?technology={slug}",
                        "meta": meta,
                    }
                )
    return docs


def entity_docs(entities: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """K2 entity export rows → entity catalog docs "as present" (K3 §3).
    Each row: ``entity_id``, ``entity_type``/``type``, ``name``/``label``,
    optional ``aliases``, ``href``. Entity links use the shared identifier
    keys (SIG-UI-067, adopted by UXR-A04)."""
    docs = []
    for e in entities:
        eid = str(e.get("entity_id") or e.get("id") or "")
        etype = str(e.get("entity_type") or e.get("type") or "entity")
        doc_type = "organization" if etype in ("organization", "organisation") else "entity"
        docs.append(
            {
                "doc_id": f"entity:{eid}",
                "type": doc_type,
                "name": str(e.get("name") or e.get("label") or eid),
                "alternates": sorted({str(a) for a in (e.get("aliases") or []) if str(a)}),
                "context": etype.replace("_", " "),
                "href": str(e.get("href") or f"/entity/{etype}/{eid}/"),
                "meta": {"entity_id": eid, "entity_type": etype},
            }
        )
    return docs


def document_docs_from_evidence(
    artifacts: Iterable[Mapping[str, Any]],
    *,
    source_names: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """K8 evidence documents → document docs (type + source name — the
    release's artifact titles are identifiers today, so the name is the
    honest typed label, never a fabricated title)."""
    source_names = dict(source_names or {})
    docs = []
    for a in artifacts:
        aid = str(a.get("artifact_id") or "")
        atype = str(a.get("artifact_type") or "artifact")
        src = str(a.get("source") or "")
        sname = source_names.get(src, src)
        title = str(a.get("title") or "")
        name = title if title else f"{atype.replace('_', ' ').title()} · {sname}"
        docs.append(
            {
                "doc_id": f"document:{aid}",
                "type": "document",
                "name": name,
                "alternates": [aid] if title else sorted({aid, sname}),
                "context": f"{atype} — {sname}".strip(" —"),
                "href": f"/evidence/{aid}/",
                "meta": {
                    "artifact_id": aid,
                    "artifact_type": atype,
                    "source": src,
                    "as_of": str(a.get("as_of") or ""),
                },
            }
        )
    return docs


def page_docs(dossiers: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Content pages → page docs. First pass: dossier pages (their display
    names are the titles readers search by)."""
    docs = []
    for d in dossiers:
        slug = str(d.get("slug_path") or d.get("slug") or d.get("jurisdiction") or "")
        name = str(d.get("display_name") or d.get("name") or d.get("title") or slug)
        docs.append(
            {
                "doc_id": f"page:dossier:{slug}",
                "type": "page",
                "name": name,
                "alternates": [slug] if slug else [],
                "context": "Dossier",
                "href": f"/dossier/{slug}/",
                "meta": {"kind": "dossier"},
            }
        )
    return docs


# --------------------------------------------------------------------------- #
# Verification (SIG-SRCH-011)                                                 #
# --------------------------------------------------------------------------- #


def streaming_sha256(path: Path) -> str:
    """sha256 over a file in 1 MiB chunks — verify-and-copy, never
    ``read_bytes()`` on the release mount (K3 §5.5 / NEW-2)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(STREAM_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def check_index_contract_v2(conn: sqlite3.Connection, *, kind: str) -> dict[str, Any]:
    """The ``meta`` contract a serving layer pins before answering."""
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    if meta.get("schema") != SEARCH_INDEX_V2_SCHEMA:
        raise SearchIndexV2Error(
            "index_contract", "search index schema is not sig.release-search-index/2"
        )
    if meta.get("kind") != kind:
        raise SearchIndexV2Error(
            "index_contract",
            f"index kind {meta.get('kind')!r} is not {kind!r}",
        )
    fmt = json.loads(meta["format"])
    if fmt.get("tokenizer") != TOKENIZER_V2:
        raise SearchIndexV2Error(
            "index_contract", "index tokenizer does not match the pinned contract"
        )
    if int(fmt.get("application_id") or 0) != APPLICATION_ID_V2:
        raise SearchIndexV2Error(
            "index_contract", "index application id does not match the pinned contract"
        )
    meta["format"] = fmt
    meta["scope"] = json.loads(meta["scope"])
    return meta


def verify_search_index(
    path: Path,
    expected_sha256: str,
    *,
    kind: str,
    publication_id: str | None = None,
) -> dict[str, Any]:
    """SIG-SRCH-011 — stream-hash the artifact, compare against the
    integrity manifest, then pin the contract before use. Built from the
    bound release projection, verified before serving, served only for
    promoted releases (the promotion check is the serving layer's)."""
    actual = streaming_sha256(path)
    if actual != expected_sha256:
        raise SearchIndexV2Error(
            "integrity_mismatch",
            f"{path.name}: sha256 {actual} != manifest {expected_sha256} — "
            "the index does not match its bound release",
        )
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        meta = check_index_contract_v2(conn, kind=kind)
        if publication_id is not None and meta.get("publication_id") != publication_id:
            raise SearchIndexV2Error(
                "release_mismatch",
                f"index is bound to {meta.get('publication_id')!r}, not {publication_id!r}",
            )
    finally:
        conn.close()
    return meta
