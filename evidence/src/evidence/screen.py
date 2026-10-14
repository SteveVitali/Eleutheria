# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Part VIII at-rest byte screen (P34.49 / ADR-185, F-406, SIG-PUB-002).

One deterministic rules engine answers the question *"does this stored capture
carry material SIG may not hold?"* in **counts only** — a field name or value is
an input, never an output. The classes it screens:

* **F-406** — the three findings the Round-11 audit caught pre-ingest
  (SIG-GOV-007):

  - ``F406-OSM-USERUID`` — OSM ``user``/``uid`` identity metadata the
    ``out meta`` Overpass query carried into stored captures before the
    D-R11-OSMUID-1 ingest fix landed;
  - ``F406-EOF-FREETEXT`` — Eyes-on-Flock ``summary.top_search_reasons``
    free-text search reasons;
  - ``F406-ARCGIS-ATTRS`` — all-attribute ArcGIS captures carrying
    editor-tracking / operator / contact fields (``created_user``,
    ``last_edited_user``, contact names, e-mail/phone values).

* **I7 S1–S9** — the nine screen classes the Tier-2 lanes impose on a captured
  lane member (SIG-PUB-012/013/014a). Lane rules only run on sources the
  committed declaration names as members — a lane with no captured member
  counts zero honestly, and each lane's rule keeps its own vocabulary so a
  lane never inherits another lane's screen by accident.

* **SIG-PUB-002** — the five never-publish categories (plates, home addresses,
  person names, personal ids, travel histories) screened on every capture so
  the operator's later true-purge decision (WV-11, ADR-181 control 2, ADR-189)
  gets a categorical listing — counts by category, never the material.

The engine is pure: :func:`screen_blob` takes bytes + metadata and returns a
``{class_id: field_hit_count}`` map. Value-level rules (e-mail, phone, plate
shape) report a hit on the *field they were found under* — the value is never
recorded. Declared rule configuration (class enablement, lane membership,
field vocabularies) travels in ``sig.at-rest-audit-decl/1`` (the committed
``ops/at_rest_audit.toml``), so the screen applied is auditable byte-for-byte.
"""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

# --- class ids ---------------------------------------------------------------

#: The three F-406 classes (pre-ingest findings → at-rest check).
F406_OSM_USERUID = "F406-OSM-USERUID"
F406_EOF_FREETEXT = "F406-EOF-FREETEXT"
F406_ARCGIS_ATTRS = "F406-ARCGIS-ATTRS"
F406_CLASSES: tuple[str, ...] = (F406_OSM_USERUID, F406_EOF_FREETEXT, F406_ARCGIS_ATTRS)

#: The nine I7 lane screen classes.
I7_CLASSES: tuple[str, ...] = tuple(f"I7-S{i}" for i in range(1, 10))

#: The five SIG-PUB-002 never-publish categories (screened on every capture).
PUB002_PLATES = "PUB002-PLATES"
PUB002_HOME_ADDRESSES = "PUB002-HOME-ADDRESSES"
PUB002_PERSON_NAMES = "PUB002-PERSON-NAMES"
PUB002_PERSONAL_IDS = "PUB002-PERSONAL-IDS"
PUB002_TRAVEL_HISTORIES = "PUB002-TRAVEL-HISTORIES"
PUB002_CLASSES: tuple[str, ...] = (
    PUB002_PLATES,
    PUB002_HOME_ADDRESSES,
    PUB002_PERSON_NAMES,
    PUB002_PERSONAL_IDS,
    PUB002_TRAVEL_HISTORIES,
)

ALL_CLASSES: tuple[str, ...] = F406_CLASSES + I7_CLASSES + PUB002_CLASSES

#: Schema ids this module emits/validates (the declaration is loaded by
#: ``ops.at_rest_audit``; the reports are emitted there too).
SCHEMA_DECL = "sig.at-rest-audit-decl/1"
SCHEMA_REPORT = "sig.at-rest-audit/1"
SCHEMA_FLAGGED = "sig.at-rest-flagged/1"
SCHEMA_SEAL_PLAN = "sig.at-rest-seal-plan/1"

# --- rule kinds + declaration ------------------------------------------------

#: Field-vocabulary rule — a dict key (case-insensitive) in ``fields`` anywhere
#: in the document counts one hit per field.
KIND_FIELDS = "fields"
#: Value-pattern rule — a string value matching a declared pattern under any
#: key counts one hit per field (the VALUE is never recorded).
KIND_VALUE_PATTERNS = "value_patterns"
#: Document-shape rule — ``json_elements`` = OSM ``out meta`` element list;
#: ``arcgis_attributes`` = ArcGIS feature rows; ``row_level`` = a member whose
#: payload is row-level records where an aggregate-only lane allows none.
KIND_SHAPE = "shape"

#: Named value patterns (pattern *names* travel in the declaration — the regex
#: lives here so a TOML typo can never weaken or over-broaden the screen).
_VALUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
    # A plate *shape* — applied only under plate-named fields by the rules
    # below, so a generic 5–8 char token never fires it.
    "plate": re.compile(r"\b[A-Z0-9]{5,8}\b"),
}

#: Keys that disqualify a generic ``name`` field from PUB002-PERSON-NAMES —
#: organisation/system names are infrastructure, not persons.
_ORG_CONTEXT_KEYS = frozenset(
    {
        "organization",
        "organisation",
        "agency",
        "department",
        "vendor",
        "company",
        "operator_type",
        "source",
    }
)


@dataclass(frozen=True)
class Rule:
    """One screen rule inside a class: kind + its vocabulary.

    ``applies`` (source-id globs) scopes an F-406 rule to the family the
    finding named; an empty tuple applies to every source. ``shapes`` names the
    document-shape checks (``KIND_SHAPE``) the rule runs.
    """

    kind: str
    fields: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    shapes: tuple[str, ...] = ()
    applies: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassRule:
    """One screen class — id + its rules + (lanes only) member globs."""

    class_id: str
    rules: tuple[Rule, ...]
    #: Source-id globs whose captures this class screens. Empty = every
    #: capture (the PUB-002 categories; shape-only F-406 rules).
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreenDeclaration:
    """``sig.at-rest-audit-decl/1`` — the committed rule table.

    Fail-closed: every declared class must be one the engine implements
    (``ALL_CLASSES``); an unknown rule kind, value pattern, or shape refuses.
    """

    classes: tuple[ClassRule, ...]
    #: Where the L1 leg writes its outputs on the restricted bucket.
    report_prefix: str = "ops/probes/at-rest/"
    #: The deny-set object key (bucket-relative) — a new object version per
    #: update, never an overwrite.
    deny_set_object: str = "ops/seal/deny-set.json"
    #: Where L2 persists the counts-only SIG-PUB-002 listing for the operator.
    pub002_object: str = "ops/seal/pub002-listing.json"

    def rule_for(self, class_id: str) -> ClassRule | None:
        for c in self.classes:
            if c.class_id == class_id:
                return c
        return None


def validate_declaration(decl: ScreenDeclaration) -> None:
    """Fail-closed checks on a parsed declaration."""
    known = set(ALL_CLASSES)
    ids: set[str] = set()
    for c in decl.classes:
        if c.class_id not in known:
            raise ValueError(f"screen class {c.class_id!r} is not a declared class")
        if c.class_id in ids:
            raise ValueError(f"screen class {c.class_id!r} declared twice")
        ids.add(c.class_id)
        if not c.rules:
            raise ValueError(f"screen class {c.class_id!r} carries no rules")
        for r in c.rules:
            if r.kind not in {KIND_FIELDS, KIND_VALUE_PATTERNS, KIND_SHAPE}:
                raise ValueError(f"{c.class_id}: rule kind {r.kind!r} is not implemented")
            for p in r.patterns:
                if p not in _VALUE_PATTERNS:
                    raise ValueError(f"{c.class_id}: value pattern {p!r} is not implemented")
            for s in r.shapes:
                if s not in {"json_elements", "arcgis_attributes", "row_level"}:
                    raise ValueError(f"{c.class_id}: shape {s!r} is not implemented")
    missing = [c for c in ALL_CLASSES if c not in ids]
    if missing:
        raise ValueError(f"declaration does not screen every class: missing {missing}")


# --- payload parsing -----------------------------------------------------------

_JSON_MEDIA = {"application/json", "application/geo+json", "application/ld+json"}
_XML_MEDIA = {
    "text/xml",
    "application/xml",
    "application/osm+xml",
    "application/xhtml+xml",
}


def _media(media_type: str) -> str:
    return media_type.split(";", 1)[0].strip().lower()


def _parse_doc(blob: bytes, media_type: str) -> tuple[Any | None, str]:
    """Parse ``blob`` into (document, flavour).

    flavour ∈ ``json`` | ``xml`` | ``binary``. JSON/XML sniffed by media type
    then by first non-space byte; anything else is ``binary`` — field rules do
    not apply and the capture still counts as scanned (a WACZ/zip/pdf is
    screened as an object, never opened).
    """
    mt = _media(media_type)
    head = blob[:256].lstrip()
    if mt in _XML_MEDIA or head.startswith(b"<"):
        try:
            import xml.etree.ElementTree as ET

            return ET.fromstring(blob.decode("utf-8")), "xml"
        except Exception:
            return None, "xml"
    if mt in _JSON_MEDIA or head.startswith((b"{", b"[")):
        try:
            return json.loads(blob.decode("utf-8")), "json"
        except Exception:
            return None, "json"
    return None, "binary"


def _iter_dicts(node: Any) -> Iterator[dict[str, Any]]:
    """Yield every dict node in a parsed JSON document (pre-order)."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_dicts(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_dicts(item)


def _iter_strings(node: Any) -> Iterator[tuple[str, str]]:
    """Yield (key, string) pairs — dict keys with string values."""
    for d in _iter_dicts(node):
        for k, v in d.items():
            if isinstance(v, str):
                yield k, v


def _key_set(node: Any) -> set[str]:
    return {str(k).lower() for d in _iter_dicts(node) for k in d.keys()}


# --- per-class evaluators -------------------------------------------------------


def _hits_fields(doc: Any, vocab: tuple[str, ...]) -> int:
    """Count dict keys (case-insensitive) matching the field vocabulary —
    a hit per distinct field NAME, not per occurrence."""
    vocab_l = {f.lower() for f in vocab}
    hits: set[str] = set()
    for d in _iter_dicts(doc):
        for k in d.keys():
            kl = str(k).lower()
            if kl in vocab_l:
                hits.add(kl)
            else:
                for f in vocab_l:
                    if "*" in f and fnmatch.fnmatch(kl, f):
                        hits.add(kl)
    return len(hits)


def _hits_values(doc: Any, patterns: tuple[str, ...]) -> int:
    """Count fields carrying a string value that matches a declared pattern
    (the value is never recorded)."""
    hits: set[str] = set()
    compiled = [_VALUE_PATTERNS[p] for p in patterns]
    for k, v in _iter_strings(doc):
        if any(p.search(v) for p in compiled):
            hits.add(str(k).lower())
    return len(hits)


def _hits_values_scoped(doc: Any, patterns: tuple[str, ...], field_vocab: tuple[str, ...]) -> int:
    """Value-pattern hits scoped to a field vocabulary (e.g. plate shape under
    plate-named fields only)."""
    vocab_l = {f.lower() for f in field_vocab}
    hits: set[str] = set()
    compiled = [_VALUE_PATTERNS[p] for p in patterns]
    for k, v in _iter_strings(doc):
        kl = str(k).lower()
        if kl in vocab_l or any("*" in f and fnmatch.fnmatch(kl, f) for f in vocab_l):
            if any(p.search(v) for p in compiled):
                hits.add(kl)
    return len(hits)


def _shape_osm_meta(doc: Any) -> int:
    """OSM ``out meta`` elements carrying ``user``/``uid`` — JSON elements list
    or element-shaped dicts carrying the identity pair."""
    hits = 0
    elements: list[Any] = []
    if isinstance(doc, dict) and isinstance(doc.get("elements"), list):
        elements = [e for e in doc["elements"] if isinstance(e, dict)]
    elif isinstance(doc, list):
        elements = [e for e in doc if isinstance(e, dict)]
    for d in elements:
        if "user" in d or "uid" in d:
            hits += 1
    if hits == 0:
        # The pair anywhere outside an elements list still counts (a nested
        # meta payload): dicts carrying BOTH user and uid.
        for d in _iter_dicts(doc):
            if "user" in d and "uid" in d:
                hits += 1
    return hits


def _shape_osm_meta_xml(root: Any) -> int:
    """OSM XML elements carrying ``user``/``uid`` attributes."""
    hits = 0
    for el in root.iter():
        if el.tag in {"node", "way", "relation", "changeset"} and (
            "user" in el.attrib or "uid" in el.attrib
        ):
            hits += 1
    return hits


def _shape_arcgis(doc: Any, rule: Rule) -> int:
    """ArcGIS all-attribute payloads: ``features[].attributes`` dicts and layer
    ``fields`` schemas. Field-name + scoped value-pattern hits."""
    hits = 0
    vocab = rule.fields
    vocab_l = [v.lower() for v in vocab]
    if isinstance(doc, dict):
        # Layer schema captures: fields = [{"name": ...}, ...]
        if isinstance(doc.get("fields"), list):
            for f in doc["fields"]:
                name = str(f.get("name", "")).lower() if isinstance(f, dict) else ""
                if name in vocab_l or any("*" in v and fnmatch.fnmatch(name, v) for v in vocab_l):
                    hits += 1
        features = doc.get("features")
        if isinstance(features, list):
            for feat in features:
                attrs = feat.get("attributes") if isinstance(feat, dict) else None
                if isinstance(attrs, dict):
                    for k, v in attrs.items():
                        kl = str(k).lower()
                        name_hit = kl in {x.lower() for x in vocab} or any(
                            "*" in x and fnmatch.fnmatch(kl, x.lower()) for x in vocab
                        )
                        value_hit = isinstance(v, str) and any(
                            _VALUE_PATTERNS[p].search(v) for p in rule.patterns
                        )
                        if name_hit or value_hit:
                            hits += 1
    return hits


def _shape_row_level(doc: Any) -> int:
    """A row-level record set: a non-empty list of dicts (or ``features``/
    ``rows`` lists) whose items are not aggregate-shaped (no count/total
    fields). Aggregate-only lanes flag every row-level record."""
    rows: list[Any] = []
    if isinstance(doc, list):
        rows = [r for r in doc if isinstance(r, dict)]
    elif isinstance(doc, dict):
        for key in ("features", "rows", "records", "results", "elements"):
            v = doc.get(key)
            if isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
                rows = [
                    (r.get("attributes") if isinstance(r.get("attributes"), dict) else r) for r in v
                ]
                break
    aggregate_keys = {"count", "total", "sum", "avg", "average", "aggregate", "month", "year"}
    n = 0
    for r in rows:
        keys = {str(k).lower() for k in r.keys()}
        if len(keys) > 1 and not keys.issubset(aggregate_keys):
            n += 1
    return n


def _hits_person_names(doc: Any, vocab: tuple[str, ...]) -> int:
    """PUB002-PERSON-NAMES: a name-ish field counts only when it is not inside
    an organisation/system context — ``camera_name`` in a camera registry is a
    device label, ``registrant``/``first_name`` is a person."""
    hits: set[str] = set()
    vocab_l = {f.lower() for f in vocab}
    for d in _iter_dicts(doc):
        org_ctx = any(str(k).lower() in _ORG_CONTEXT_KEYS for k in d.keys())
        for k in d.keys():
            kl = str(k).lower()
            if kl in vocab_l and not (org_ctx and kl in {"name", "owner"}):
                hits.add(kl)
    return len(hits)


# --- the engine -----------------------------------------------------------------


def _applies(source_id: str, globs: tuple[str, ...]) -> bool:
    """A rule/class applies when no member globs are declared (screen-all) or
    the source id matches one glob."""
    if not globs:
        return True
    sid = source_id.lower()
    return any(fnmatch.fnmatch(sid, g.lower()) for g in globs)


def screen_blob(
    blob: bytes,
    *,
    source_id: str,
    media_type: str,
    decl: ScreenDeclaration,
) -> dict[str, int]:
    """Screen one capture's bytes. Returns ``{class_id: hit_count}`` — zero-hit
    classes are omitted. Counts are FIELDS/ELEMENTS, never values."""
    doc, flavour = _parse_doc(blob, media_type)
    out: dict[str, int] = {}
    for cls in decl.classes:
        if not _applies(source_id, cls.members):
            continue
        hits = 0
        for rule in cls.rules:
            if rule.applies and not _applies(source_id, rule.applies):
                continue
            if doc is None:
                continue
            if flavour == "json":
                if rule.kind == KIND_FIELDS:
                    if cls.class_id == PUB002_PERSON_NAMES:
                        hits += _hits_person_names(doc, rule.fields)
                    else:
                        hits += _hits_fields(doc, rule.fields)
                elif rule.kind == KIND_VALUE_PATTERNS:
                    if cls.class_id == PUB002_PLATES:
                        hits += _hits_values_scoped(doc, rule.patterns, rule.fields)
                    else:
                        hits += _hits_values(doc, rule.patterns)
                elif rule.kind == KIND_SHAPE:
                    for shape in rule.shapes:
                        if shape == "json_elements":
                            hits += _shape_osm_meta(doc)
                        elif shape == "arcgis_attributes":
                            hits += _shape_arcgis(doc, rule)
                        elif shape == "row_level":
                            hits += _shape_row_level(doc)
            elif flavour == "xml":
                if rule.kind == KIND_SHAPE and "json_elements" in rule.shapes:
                    hits += _shape_osm_meta_xml(doc)
                elif rule.kind == KIND_FIELDS:
                    # Attribute names = field names in XML payloads.
                    attr_keys = {str(a).lower() for el in doc.iter() for a in el.attrib.keys()}
                    vocab_l = {f.lower() for f in rule.fields}
                    hits += len(attr_keys & vocab_l)
        if hits:
            out[cls.class_id] = hits
    return out


def classes_flagged(hits: dict[str, int]) -> list[str]:
    """Class ids with at least one hit, sorted."""
    return sorted(hits)


def is_f406(class_id: str) -> bool:
    return class_id in F406_CLASSES


def is_i7(class_id: str) -> bool:
    return class_id in I7_CLASSES


def is_pub002(class_id: str) -> bool:
    return class_id in PUB002_CLASSES


@dataclass(frozen=True)
class FlaggedObject:
    """One flagged capture object — the restricted-side record (ADR-185).

    Ids + digest only: a flagged object is named so L2 can seal exactly it;
    the fields that fired the rule stay inside counts on the report."""

    object_id: str
    digest: str
    classes: tuple[str, ...]
    source_id: str = ""
    artifact_id: str | None = None
    capture_id: str | None = None
    already_sealed: bool = False
    pub002_categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanStats:
    """The counts-only shape ``sig.at-rest-audit/1`` carries per class."""

    objects_flagged: int = 0
    hits: int = 0
    by_source: dict[str, dict[str, int]] = field(default_factory=dict)


__all__ = [
    "ALL_CLASSES",
    "F406_CLASSES",
    "F406_ARCGIS_ATTRS",
    "F406_EOF_FREETEXT",
    "F406_OSM_USERUID",
    "FlaggedObject",
    "I7_CLASSES",
    "KIND_FIELDS",
    "KIND_SHAPE",
    "KIND_VALUE_PATTERNS",
    "PUB002_CLASSES",
    "PUB002_HOME_ADDRESSES",
    "PUB002_PERSONAL_IDS",
    "PUB002_PERSON_NAMES",
    "PUB002_PLATES",
    "PUB002_TRAVEL_HISTORIES",
    "ClassRule",
    "Rule",
    "SCHEMA_DECL",
    "SCHEMA_FLAGGED",
    "SCHEMA_REPORT",
    "SCHEMA_SEAL_PLAN",
    "ScanStats",
    "ScreenDeclaration",
    "classes_flagged",
    "is_f406",
    "is_i7",
    "is_pub002",
    "screen_blob",
    "validate_declaration",
]
