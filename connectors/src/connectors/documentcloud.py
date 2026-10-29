# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.77 — the DocumentCloud / MuckRock released-materials connector.

Row 352 lands the public-pages rendition lane the I7 discovery anticipated
(the decision-catalog row is ``I7-C2``; the ticket's ``I7-C13`` label names no
record — recorded deviation): the committed seed set in
``data/documentcloud_targets.toml`` — DocumentCloud released-document pages
and API records, DocumentCloud project indexes, and MuckRock's public
``/foi/`` request pages — is read as **redacted renditions only**. The
connector never persists a served page's own bytes: the Part VIII screen
runs in memory over the extraction surface and the canonical record before
anything is written (ADR-185), and a rendition that cannot be made reliable
is a recorded refusal — pointer + screened facts, never the raw page.

Six bounded kinds, one recorded GET each (leg A — the OM-20 row-352 mutation
GATE-G5 named verbatim on 2026-10-25T18:40Z):

* ``api_document`` / ``api_project`` — the documented unauthenticated API
  (``api.www.documentcloud.org/api/{documents,projects}/<id>/``) — §26 rule
  5's offered channel; the JSON record is parsed to the allowlisted fields.
* ``document_page`` / ``project_page`` — the uploader's own public pages on
  ``www.documentcloud.org`` — title/meta extraction only, never page bodies.
* ``muckrock_page`` — the MuckRock public ``/foi/`` request page (the
  ``muckrock_public`` source's bounded lane — the api_v2 half stays the
  ``records`` connector's, untouched).
* ``terms_page`` — the platform terms page captured verbatim (SIG-LIC-004a /
  the SIG-TRANSP-004 terms-capture family: URL + date + digest + text).

The redaction model (SIG-ENG-042): structural fields (URLs, ids, statuses,
dates, counts) are verbatim-allowlisted; every text candidate is screened
per field under the committed Part VIII declaration — a hit drops the value
into ``redacted_fields`` (name + classes + value sha256, never the value);
denied field NAMES in served payloads land in ``refused_fields`` (names
only). The finished rendition is screened again: any residual hit — or an
unparseable/binary page — persists only a ``sig.documentcloud-refusal/1``
record (upstream URL, classes, counts, original sha256 + byte size), never
raw bytes. Every emitted claim links the uploader's public page URL.

There is no discovery: ``discover()`` walks exactly the committed inventory
(a ``parameters["targets"]`` binding outside it is refused loud), one polite
GET per target through the shared layer — opt-out register first (§26 rule
7), robots recorded under GL-GATE-08, rate-limited, challenge-stopped (a
401/403/451/2xx-interstitial ends the target's attempt — recorded, never
defeated; SIG-INGEST-037 permits no circumvention, challenge-solving, header
spoofing, proxy rotation, credentials or browser automation anywhere in
this module, and a test asserts none exists).

The source rows stay ``ingestion_permitted=false`` — ``documentcloud``
(remapped from the ``records`` index path this lane supersedes) and the new
``muckrock_public`` row. Leg B, the first real host's wire/fetch as a
connector run, is the operator's act (OP-26), separately authorised. Nothing
here flips it.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from evidence.screen import ScreenDeclaration, declaration_from_table, screen_blob

from ._data import load_table
from .accountability import load_claims_for_l1
from .disappearance import failing_status_for_error, failing_status_for_http
from .field_denylist import is_denied
from .net import ChallengeEncountered, HostOptOut, ReservationRefused
from .stages import (
    CaptureRef,
    Connector,
    FetchResult,
    RunContext,
    SchemaRefusal,
    register,
)

CONNECTOR_NAME = "documentcloud"
#: The registry source ids this connector serves: the DocumentCloud lane
#: (remapped from the ``records`` index path — P26.2's `document_lookup` is
#: subsumed by ``api_document``) and the MuckRock public-pages row this row
#: appends. The ``muckrock`` api_v2 source stays the ``records`` connector's.
SOURCE_IDS = ("documentcloud", "muckrock_public")

_TARGETS_TABLE = "documentcloud_targets"
_VOCAB_TABLE = "documentcloud_vocab"

TARGETS_SCHEMA = "sig.documentcloud-targets/1"
VOCAB_SCHEMA_ID = "sig.documentcloud-vocab/1"
RENDITION_SCHEMA = "sig.documentcloud-rendition/1"
REFUSAL_SCHEMA = "sig.documentcloud-refusal/1"
TERMS_SCHEMA = "sig.documentcloud-terms/1"

#: The committed Part VIII screen declaration (P34.49 / ADR-185) — the same
#: document the at-rest audit parses, consumed through the same parser so the
#: connector-side screen is the auditable screen, never a drifted copy.
DEFAULT_SCREEN_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "at_rest_audit.toml"

#: Bounded verbatim captures — a runaway terms block flags itself.
_TERMS_CAP = 100_000

_JSON_SCRIPT_TYPES = frozenset({"application/json", "application/ld+json"})


# --- the committed seed inventory (data, not code) ----------------------------


@dataclass(frozen=True)
class ReleaseTarget:
    """One committed seed — identifiers + provenance, never content."""

    id: str
    source: str
    platform: str
    kind: str
    url: str
    document_id: str
    expect: tuple[str, ...]
    evidence: str
    opted_out: bool = False


@dataclass(frozen=True)
class ReleaseInventory:
    """The committed seed set with its derivation provenance."""

    source_ref: str
    evidence_ref: str
    captured_on: str
    selection_rule: str
    targets: tuple[ReleaseTarget, ...]

    @property
    def urls(self) -> frozenset[str]:
        return frozenset(t.url for t in self.targets)

    def for_source(self, source_id: str) -> tuple[ReleaseTarget, ...]:
        return tuple(t for t in self.targets if t.source == source_id)

    def for_url(self, url: str) -> ReleaseTarget | None:
        for t in self.targets:
            if t.url == url:
                return t
        return None

    def get(self, target_id: str) -> ReleaseTarget | None:
        for t in self.targets:
            if t.id == target_id:
                return t
        return None


def _vocab() -> Mapping[str, Any]:
    """The committed ``sig.documentcloud-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"documentcloud vocabulary must be {VOCAB_SCHEMA_ID!r}")
    return table


def vocab_version() -> str:
    return str(_vocab().get("vocab_version") or "unknown")


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.4 closed allowlist)."""
    return frozenset(str(p) for p in _vocab().get("predicate_allowlist") or ())


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def assert_predicate_allowed(predicate_id: str) -> str:
    if predicate_id not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"predicate {predicate_id!r} is not in the documentcloud allowlist "
            f"({sorted(predicate_allowlist())})"
        )
    return predicate_id


def _kind_spec(kind: str) -> Mapping[str, Any]:
    spec = (_vocab().get("kinds") or {}).get(kind)
    if not isinstance(spec, Mapping):
        raise ValueError(f"documentcloud vocabulary names no kind {kind!r}")
    return spec


def _url_is_public_surface(url: str, *, kind: str, platform: str) -> bool:
    """Whether ``url`` is a public unauthenticated surface of the committed kind.

    Public-only is a structural invariant, checked twice (inventory load and
    fetch): https only, no userinfo/query/fragment, the host in the
    platform's committed host set, the path matching the kind's reviewed
    pattern (``/api/{documents,projects}/<id>/``, ``/documents/<id>-<slug>``,
    ``/projects/<slug>``, ``/foi/<area>/<slug>-<id>/``, ``/tos/``). Anything
    else — a credential-bearing URL, a private endpoint, an uncommitted host
    — is not addressable.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.query or parts.fragment:
        return False
    hosts = {str(h) for h in (_vocab().get("hosts") or {}).get(platform) or ()}
    if parts.netloc.lower() not in hosts:
        return False
    return bool(re.search(str(_kind_spec(kind).get("path_re") or "$^"), parts.path))


def load_inventory() -> ReleaseInventory:
    """Parse + validate the committed seed set (fail-closed on drift).

    A malformed inventory — wrong schema, unsorted or duplicate ids, a row
    whose URL is not the committed public surface of its kind, a ``source``
    naming a row this connector does not serve, a page kind without an
    ``expect`` token (the identity check would be unenforceable), a
    ``target_count`` that disagrees — refuses the load rather than
    addressing outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"documentcloud inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    opted = {str(s) for s in (inv.get("opted_out_targets") or [])}
    targets: list[ReleaseTarget] = []
    for i, row in enumerate(inv.get("targets") or []):
        if not isinstance(row, dict):
            raise ValueError(f"documentcloud inventory target {i} must be a table")
        tid = str(row.get("id") or "")
        source = str(row.get("source") or "")
        platform = str(row.get("platform") or "")
        kind = str(row.get("kind") or "")
        url = str(row.get("url") or "")
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if not tid or not source or not platform or not kind or not url:
            raise ValueError(
                f"documentcloud inventory target {i} needs id/source/platform/kind/url"
            )
        if source not in SOURCE_IDS:
            raise ValueError(
                f"documentcloud inventory target {tid!r}: source {source!r} is not one "
                f"of {SOURCE_IDS} — this connector serves no other row"
            )
        spec = _kind_spec(kind)
        if str(spec.get("platform") or "") != platform:
            raise ValueError(
                f"documentcloud inventory target {tid!r}: kind {kind!r} is a "
                f"{spec.get('platform')!r} kind, not {platform!r}"
            )
        if not _url_is_public_surface(url, kind=kind, platform=platform):
            raise ValueError(
                f"documentcloud inventory target {tid!r}: {url!r} is not the committed "
                "public unauthenticated surface of its kind (fail-closed)"
            )
        needs_expect = kind != "terms_page"
        if needs_expect and not expect:
            raise ValueError(
                f"documentcloud inventory target {tid!r}: an empty expect list leaves "
                "the page-identity check unenforceable (fail-closed)"
            )
        targets.append(
            ReleaseTarget(
                id=tid,
                source=source,
                platform=platform,
                kind=kind,
                url=url,
                document_id=str(row.get("document_id") or ""),
                expect=expect,
                evidence=str(row.get("evidence") or ""),
                opted_out=tid in opted or url in opted,
            )
        )
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("documentcloud inventory carries duplicate target ids")
    if ids != sorted(ids):
        raise ValueError("documentcloud inventory is not id-sorted (deterministic order required)")
    declared = int(inv.get("target_count") or -1)
    if declared != len(targets):
        raise ValueError(
            f"documentcloud inventory target_count={declared} but {len(targets)} rows committed"
        )
    return ReleaseInventory(
        source_ref=str(inv.get("source_ref") or ""),
        evidence_ref=str(inv.get("evidence_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        selection_rule=str(inv.get("selection_rule") or ""),
        targets=tuple(targets),
    )


def _targets_for(
    inventory: ReleaseInventory, *, source_id: str | None = None
) -> list[dict[str, Any]]:
    rows = inventory.targets if source_id is None else inventory.for_source(source_id)
    return [
        {
            "id": t.id,
            "url": t.url,
            "kind": t.kind,
            "source": t.source,
            "platform": t.platform,
            "document_id": t.document_id,
        }
        for t in rows
    ]


def documentcloud_targets(source_id: str | None = None) -> list[dict[str, Any]]:
    """The ``{"id","url","kind"}`` targets ``live_targets.toml`` delegates to."""
    return _targets_for(load_inventory(), source_id=source_id)


def load_screen_declaration(path: str | Path | None = None) -> ScreenDeclaration:
    """The committed ``sig.at-rest-audit-decl/1`` — one parser, one document (ADR-185)."""
    p = Path(path) if path else DEFAULT_SCREEN_DECLARATION
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    return declaration_from_table(raw, source=str(p))


# --- extraction (pure — JSON records + HTML meta/text) -------------------------


class RenditionSchemaError(ValueError):
    """A served page cannot satisfy the committed rendition schema."""


def _iter_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_dicts(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_dicts(item)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _value_sha256(value: Any) -> str:
    return _sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


class _PageScanner(HTMLParser):
    """Lift title text, meta fields, terms blocks and embedded JSON islands."""

    def __init__(self, terms_ids: frozenset[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._terms_ids = terms_ids
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.json_blocks: list[str] = []
        self.terms_blocks: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical: str = ""
        self._in_title = False
        self._skip_depth = 0
        self._script_buf: list[str] | None = None
        self._terms_tag: str | None = None
        self._terms_depth = 0
        self._terms_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag in {"style", "noscript"}:
            self._skip_depth += 1
        elif tag == "script":
            self._skip_depth += 1
            mtype = attr.get("type", "").split(";")[0].strip().lower()
            if mtype in _JSON_SCRIPT_TYPES:
                self._script_buf = []
        elif tag == "meta":
            name = (attr.get("name") or attr.get("property") or "").strip().lower()
            content = attr.get("content", "")
            if name and content and name not in self.meta:
                self.meta[name] = content
        elif tag == "link" and attr.get("rel", "").strip().lower() == "canonical":
            if attr.get("href"):
                self.canonical = attr["href"]
        tid = attr.get("id", "").strip().lower()
        classes = {c.lower() for c in attr.get("class", "").split()}
        if self._terms_tag is not None:
            self._terms_depth += 1
        elif tid in self._terms_ids or (classes & self._terms_ids):
            self._terms_tag = tag
            self._terms_depth = 1
            self._terms_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in {"style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "script":
            if self._script_buf is not None:
                self.json_blocks.append("".join(self._script_buf))
                self._script_buf = None
            if self._skip_depth:
                self._skip_depth -= 1
        if self._terms_tag is not None:
            self._terms_depth -= 1
            if self._terms_depth <= 0:
                text = "".join(self._terms_buf)
                if text.strip():
                    self.terms_blocks.append(text)
                self._terms_tag = None
                self._terms_buf = []

    def handle_data(self, data: str) -> None:
        if self._script_buf is not None:
            self._script_buf.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._terms_tag is not None:
            self._terms_buf.append(data)
        if self._skip_depth == 0 and not self._in_title:
            self.text_parts.append(data)


@dataclass(frozen=True)
class RedactionField:
    """One dropped field — name + screen classes + value hash, never the value."""

    field: str
    screen_as: str
    classes: tuple[str, ...]
    value_sha256: str

    def to_row(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "screen_as": self.screen_as,
            "classes": list(self.classes),
            "value_sha256": self.value_sha256,
        }


@dataclass(frozen=True)
class Rendition:
    """The screened rendition of one served surface — the only persistable body.

    ``fields`` carries only the allowlisted values that survived the per-field
    screen; ``redacted_fields`` records every dropped field by name + classes +
    value sha256; ``refused_fields`` names (never values) the served payload
    keys matching the Part VIII denylist. The original's sha256 + byte size
    ride the record as evidence (SIG-ENG-042).
    """

    target: ReleaseTarget
    uploader_page: str
    document_id: str
    fields: Mapping[str, Any]
    redacted_fields: tuple[RedactionField, ...]
    refused_fields: tuple[str, ...]
    original_sha256: str
    original_bytes: int
    retrieved_at: str | None

    def record(self) -> dict[str, Any]:
        """The canonical persisted artifact — the ONLY bytes capture() stores."""
        return {
            "schema": RENDITION_SCHEMA,
            "target_id": self.target.id,
            "kind": self.target.kind,
            "platform": self.target.platform,
            "source": self.target.source,
            "upstream_url": self.target.url,
            "uploader_page": self.uploader_page,
            "document_id": self.document_id,
            "fields": dict(self.fields),
            "redacted_fields": [f.to_row() for f in self.redacted_fields],
            "refused_fields": list(self.refused_fields),
            "original_sha256": self.original_sha256,
            "original_bytes": self.original_bytes,
            "retrieved_at": self.retrieved_at,
        }

    def record_bytes(self) -> bytes:
        return json.dumps(self.record(), sort_keys=True, ensure_ascii=False).encode("utf-8")


def refusal_record(
    target: ReleaseTarget,
    *,
    reason: str,
    screen_hits: Mapping[str, int] | None = None,
    redacted_count: int = 0,
    refused_count: int = 0,
    uploader_page: str = "",
    body: bytes = b"",
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """The ``sig.documentcloud-refusal/1`` record — pointer + screened facts only.

    Persisted where a rendition cannot be made reliable (SIG-ENG-042): the
    upstream URL, the reason, the screen-hit classes with COUNTS, the
    redacted/refused field COUNTS, and the original's sha256 + byte size —
    never a served byte, never a field value.
    """
    return {
        "schema": REFUSAL_SCHEMA,
        "target_id": target.id,
        "kind": target.kind,
        "platform": target.platform,
        "source": target.source,
        "upstream_url": target.url,
        "uploader_page": uploader_page,
        "reason": reason,
        "screen_hits": {str(k): int(v) for k, v in sorted((screen_hits or {}).items())},
        "redacted_field_count": int(redacted_count),
        "refused_field_count": int(refused_count),
        "original_sha256": _sha256(body),
        "original_bytes": len(body),
        "retrieved_at": retrieved_at,
    }


def terms_record(
    target: ReleaseTarget,
    *,
    terms_text: str,
    truncated: bool,
    body: bytes,
    retrieved_at: str | None,
) -> dict[str, Any]:
    """The ``sig.documentcloud-terms/1`` verbatim terms capture (SIG-LIC-004a)."""
    return {
        "schema": TERMS_SCHEMA,
        "target_id": target.id,
        "kind": target.kind,
        "platform": target.platform,
        "source": target.source,
        "upstream_url": target.url,
        "uploader_page": target.url,
        "terms_url": target.url,
        "terms_text": terms_text,
        "terms_truncated": bool(truncated),
        "terms_sha256": _sha256(terms_text.encode("utf-8")),
        "original_sha256": _sha256(body),
        "original_bytes": len(body),
        "retrieved_at": retrieved_at,
    }


def _screen_field(
    value: Any, *, screen_as: str, source_id: str, decl: ScreenDeclaration
) -> dict[str, int]:
    """Screen one candidate value under a hazardous field name (in memory)."""
    blob = json.dumps({screen_as: value}, ensure_ascii=False, default=str).encode("utf-8")
    return dict(screen_blob(blob, source_id=source_id, media_type="application/json", decl=decl))


def _build_rendition(
    *,
    target: ReleaseTarget,
    structural: Mapping[str, Any],
    candidates: Mapping[str, Any],
    uploader_page: str,
    document_id: str,
    payloads: Iterable[Any],
    body: bytes,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], Rendition | None, dict[str, int], str]:
    """The in-memory redaction: fields in, a screened rendition or a refusal out.

    Returns ``(record_bytes_ready_state, rendition_or_None, payload_screen_hits,
    refusal_reason)`` — ``record`` is the rendition when the finished record
    screens clean, else the persisted ``sig.documentcloud-refusal/1`` record.
    """
    screen_map = _vocab().get("screen_as") or {}
    refused: set[str] = set()
    payload_docs: list[Any] = list(payloads)
    for doc in payload_docs:
        for d in _iter_dicts(doc):
            for key in d:
                if is_denied(str(key)):
                    refused.add(str(key))

    kept: dict[str, Any] = {}
    redacted: list[RedactionField] = []
    for name, value in candidates.items():
        if value is None:
            continue
        screen_as = str(screen_map.get(name) or name)
        field_hits = _screen_field(value, screen_as=screen_as, source_id=target.source, decl=decl)
        if field_hits:
            redacted.append(
                RedactionField(
                    field=name,
                    screen_as=screen_as,
                    classes=tuple(sorted(field_hits)),
                    value_sha256=_value_sha256(value),
                )
            )
        else:
            kept[name] = value

    rendition = Rendition(
        target=target,
        uploader_page=uploader_page,
        document_id=document_id,
        fields={**dict(structural), **kept},
        redacted_fields=tuple(redacted),
        refused_fields=tuple(sorted(refused)),
        original_sha256=_sha256(body),
        original_bytes=len(body),
        retrieved_at=retrieved_at,
    )
    # ADR-185 — the finished rendition screens again before persistence. Any
    # residual hit (a structural field, a kept field that surprised) means the
    # redaction is not reliable: the persisted artifact is the refusal record.
    hits: dict[str, int] = {}
    for cls, n in screen_blob(
        rendition.record_bytes(),
        source_id=target.source,
        media_type="application/json",
        decl=decl,
    ).items():
        hits[cls] = hits.get(cls, 0) + int(n)
    if hits:
        return (
            refusal_record(
                target,
                reason="unreliable_redaction",
                screen_hits=hits,
                redacted_count=len(redacted),
                refused_count=len(refused),
                uploader_page=uploader_page,
                body=body,
                retrieved_at=retrieved_at,
            ),
            None,
            hits,
            "unreliable_redaction",
        )
    return (rendition.record(), rendition, hits, "")


def _opt_str(v: Any) -> str | None:
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _nested_name(node: Any) -> str | None:
    """A nested ``{name: ...}``'s name — a person/org label, always a candidate."""
    if isinstance(node, Mapping):
        return _opt_str(node.get("name"))
    return _opt_str(node)


def parse_api_document(
    body: bytes,
    *,
    target: ReleaseTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A DocumentCloud ``/api/documents/<id>/`` record → rendition/refusal record.

    Structural fields (id, access, canonical_url, dates, pages, status, slug,
    asset/derived URLs) are allowlisted verbatim — never the document's own
    bytes; the uploader's public page is ``canonical_url``. ``title`` keeps
    verbatim when screen-clean; ``description``/``source``/``contributor``
    (person-named or free-text candidates) screen under their committed
    hazard names and drop to ``redacted_fields`` on any hit. An ``access``
    other than ``public`` is not a public surface — the rendition refuses.
    """
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RenditionSchemaError(f"api_document payload is not JSON: {exc}") from exc
    if not isinstance(doc, Mapping):
        raise RenditionSchemaError("api_document payload is not an object")
    access = str(doc.get("access") or "").strip().lower()
    if access != "public":
        raise RenditionSchemaError(
            f"document access={access or 'absent'} — not a public released "
            "document; this connector reads public unauthenticated surfaces only"
        )
    canonical = _opt_str(doc.get("canonical_url") or doc.get("document_url")) or target.url
    document_id = str(doc.get("id") or target.document_id or "")
    if target.expect:
        blob = json.dumps(doc, ensure_ascii=False, default=str).lower()
        if not any(e.lower() in blob for e in target.expect):
            raise RenditionSchemaError(
                f"api_document record carries none of target {target.id!r}'s "
                "committed expect tokens — refused, never guessed"
            )
    structural = {
        "id": document_id,
        "access": access,
        "canonical_url": canonical,
        "created_at": _opt_str(doc.get("created_at")),
        "updated_at": _opt_str(doc.get("updated_at")),
        "pages": doc.get("pages"),
        "slug": _opt_str(doc.get("slug")),
        "status": _opt_str(doc.get("status")),
        "language": _opt_str(doc.get("language")),
        "asset_url": _opt_str(doc.get("asset_url")),
    }
    candidates = {
        "title": _opt_str(doc.get("title")),
        "description": _opt_str(doc.get("description")),
        "source": _opt_str(doc.get("source")),
        "contributor": _opt_str(doc.get("contributor")) or _nested_name(doc.get("user")),
        "organization_name": _nested_name(doc.get("organization")),
    }
    record, rendition, _hits, reason = _build_rendition(
        target=target,
        structural={k: v for k, v in structural.items() if v is not None},
        candidates=candidates,
        uploader_page=canonical,
        document_id=document_id,
        payloads=[doc],
        body=body,
        retrieved_at=retrieved_at,
        decl=decl,
    )
    return record, reason


def parse_api_project(
    body: bytes,
    *,
    target: ReleaseTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A DocumentCloud ``/api/projects/<id>/`` record → rendition/refusal record.

    A project is a released-document INDEX surface: the rendition carries the
    project's id/title/url/user+created facts and member COUNTS — member
    document names/descriptions are never extracted (no discovery, no
    member-content claims).
    """
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RenditionSchemaError(f"api_project payload is not JSON: {exc}") from exc
    if not isinstance(doc, Mapping):
        raise RenditionSchemaError("api_project payload is not an object")
    if target.expect:
        blob = json.dumps(doc, ensure_ascii=False, default=str).lower()
        if not any(e.lower() in blob for e in target.expect):
            raise RenditionSchemaError(
                f"api_project record carries none of target {target.id!r}'s "
                "committed expect tokens — refused, never guessed"
            )
    project_id = str(doc.get("id") or target.document_id or "")
    documents = doc.get("documents") or doc.get("document_ids") or []
    uploader_page = (
        _opt_str(doc.get("canonical_url"))
        or _opt_str(doc.get("url"))
        or f"https://www.documentcloud.org/projects/{project_id}/"
    )
    structural = {
        "id": project_id,
        "collection_kind": "documentcloud_project",
        "member_count": len(documents) if isinstance(documents, list) else None,
        "created_at": _opt_str(doc.get("created_at")),
        "updated_at": _opt_str(doc.get("updated_at")),
    }
    candidates = {
        "title": _opt_str(doc.get("title")),
        "description": _opt_str(doc.get("description")),
        "contributor": _nested_name(doc.get("user")),
    }
    record, rendition, _hits, reason = _build_rendition(
        target=target,
        structural={k: v for k, v in structural.items() if v is not None},
        candidates=candidates,
        uploader_page=uploader_page,
        document_id=project_id,
        payloads=[doc],
        body=body,
        retrieved_at=retrieved_at,
        decl=decl,
    )
    return record, reason


def _html_scan(body: bytes) -> _PageScanner:
    terms_ids = frozenset(
        str(t).lower() for t in (_vocab().get("page") or {}).get("terms_element_ids") or ()
    )
    scanner = _PageScanner(terms_ids)
    scanner.feed(body.decode("utf-8", errors="replace"))
    scanner.close()
    return scanner


def parse_public_page(
    body: bytes,
    *,
    target: ReleaseTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A public uploader page (document/project/request) → rendition/refusal.

    Title/meta extraction only — the page body is never carried. ``expect``
    tokens verify page identity (a page contradicting its committed seed is
    refused whole); embedded JSON islands are scanned for denylist field
    NAMES (``refused_fields`` — names only); meta/title candidates screen
    per-field and drop to ``redacted_fields`` on any hit.
    """
    scanner = _html_scan(body)
    payloads: list[Any] = []
    for block in scanner.json_blocks:
        try:
            payloads.append(json.loads(block))
        except (json.JSONDecodeError, ValueError):
            continue
    title = " ".join(scanner.title_parts).strip()
    visible = " ".join(scanner.text_parts)
    identity_blob = " ".join(
        [title, visible[:65_536], json.dumps(payloads, default=str)[:65_536]]
    ).lower()
    if target.expect and not any(e.lower() in identity_blob for e in target.expect):
        raise RenditionSchemaError(
            f"served page carries none of target {target.id!r}'s committed expect "
            "tokens — the page is not the committed seed (refused, never guessed)"
        )
    meta = scanner.meta
    kind = target.kind
    document_id = target.document_id or str(
        meta.get("documentcloud:id") or meta.get("og:document_id") or ""
    )
    uploader_page = _opt_str(scanner.canonical) or _opt_str(meta.get("og:url")) or target.url
    if kind == "project_page":
        collection_kind = "documentcloud_project"
    elif kind == "muckrock_page":
        collection_kind = "muckrock_request_page"
    else:
        collection_kind = "documentcloud_document_page"
    status_marker = ""
    if kind == "muckrock_page":
        markers = [str(m).lower() for m in (_vocab().get("page") or {}).get("status_markers") or ()]
        status_marker = next((m for m in markers if m in identity_blob), "")
    structural = {
        "collection_kind": collection_kind,
        "canonical_url": uploader_page,
        "page_title_found": bool(title),
        "status_marker": status_marker or None,
    }
    candidates = {
        "title": _opt_str(title) or _opt_str(meta.get("og:title")),
        "description": _opt_str(meta.get("description") or meta.get("og:description")),
        "site_name": _opt_str(meta.get("og:site_name")),
        "author": _opt_str(meta.get("author") or meta.get("article:author")),
        "agency": _opt_str(meta.get("sig:agency") or meta.get("jurisdiction")),
    }
    record, rendition, _hits, reason = _build_rendition(
        target=target,
        structural={k: v for k, v in structural.items() if v is not None},
        candidates=candidates,
        uploader_page=uploader_page,
        document_id=document_id,
        payloads=payloads,
        body=body,
        retrieved_at=retrieved_at,
        decl=decl,
    )
    return record, reason


def parse_terms_page(
    body: bytes,
    *,
    target: ReleaseTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A platform terms page → the verbatim ``sig.documentcloud-terms/1`` capture.

    SIG-LIC-004a / SIG-TRANSP-004: the terms text is captured VERBATIM
    (bounded), never paraphrased — the terms block, its sha256, the page's
    own sha256 + byte size. The terms record itself screens clean or the
    persisted artifact is the refusal record.
    """
    scanner = _html_scan(body)
    text = ""
    if scanner.terms_blocks:
        text = " ".join(b.strip() for b in scanner.terms_blocks if b.strip())
    elif scanner.text_parts:
        # Terms pages are predominantly terms copy — the whole visible text is
        # the capture (bounded); a page with no extractable text refuses.
        text = " ".join(" ".join(scanner.text_parts).split())
    if not text:
        raise RenditionSchemaError("terms page carried no extractable terms text")
    truncated = len(text) > _TERMS_CAP
    if truncated:
        text = text[:_TERMS_CAP]
    record = terms_record(
        target,
        terms_text=text,
        truncated=truncated,
        body=body,
        retrieved_at=retrieved_at,
    )
    hits = dict(
        screen_blob(
            json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8"),
            source_id=target.source,
            media_type="application/json",
            decl=decl,
        )
    )
    if hits:
        return (
            refusal_record(
                target,
                reason="unreliable_redaction",
                screen_hits=hits,
                uploader_page=target.url,
                body=body,
                retrieved_at=retrieved_at,
            ),
            "unreliable_redaction",
        )
    return record, ""


# --- refusal types local to this connector -------------------------------------


class TargetOptedOut(HostOptOut):
    """A committed-target opt-out: the site asked SIG to stop addressing IT.

    The host-level register (§26 rule 7) is consulted by the shared fetcher
    before any egress; the committed inventory's ``opted_out_targets`` list is
    its target-granular counterpart, checked in ``fetch()`` before the request
    is issued. A subclass of :class:`HostOptOut` so the driver's
    rights-refusal path records it unchanged.
    """

    def __init__(self, target: ReleaseTarget) -> None:
        self.target = target
        super().__init__(
            target.url,
            urlsplit(target.url).netloc,
            f"target {target.id!r} is opted out of screening",
        )


class InterstitialEncountered(ChallengeEncountered):
    """A 2xx bot-management interstitial — a challenge, recorded as such.

    Any challenge ends the target's attempt (SIG-INGEST-013/037): recorded,
    never defeated. A subclass of :class:`ChallengeEncountered` so the driver
    records the ``access_restricted`` disappearance through the unchanged
    machinery while this connector's ledger keeps the finer ``interstitial``
    kind.
    """

    def __init__(self, url: str) -> None:
        super().__init__(
            f"{url!r} served a bot-management interstitial (2xx stub, not the "
            "page); the attempt ends here — recorded, never defeated "
            "(SIG-INGEST-013).",
            status=200,
        )


def _looks_like_interstitial(body: bytes) -> bool:
    """Whether the served 2xx body is a bot-management stub, not the real page."""
    markers = tuple(
        str(m).lower() for m in (_vocab().get("page") or {}).get("interstitial_markers") or ()
    )
    head = body[:65_536].decode("utf-8", errors="replace").lower()
    return any(m in head for m in markers)


# --- the connector --------------------------------------------------------------


@register
class DocumentCloudConnector(Connector):
    """The `documentcloud` connector — public released-materials renditions.

    One polite GET per committed target per run through the shared politeness
    layer. The connector holds no HTTP client, no credential, no retry, and no
    circumvention capability of any kind (SIG-INGEST-011/013/037). It never
    performs entity resolution — claims are candidate linkages to the
    uploader's public page only (SIG-INGEST-034).
    """

    name = CONNECTOR_NAME
    version = "1.0.0"

    def __init__(
        self,
        *,
        inventory: ReleaseInventory | None = None,
        screen: ScreenDeclaration | None = None,
        screen_declaration_path: str | Path | None = None,
    ) -> None:
        self._inventory = inventory or load_inventory()
        self._screen = screen or load_screen_declaration(screen_declaration_path)
        #: The run's per-target outcome ledger — one row per attempted target
        #: (served / refused + kind + counts-only detail; never content).
        self.outcomes: list[dict[str, Any]] = []
        #: The fetch → capture handoff: the rendition/refusal/terms records
        #: this connector persists, keyed by URL. Bounded by the committed set.
        self._artifacts: dict[str, bytes] = {}
        self._records: dict[str, dict[str, Any]] = {}

    # -- acquisition --

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """The committed target set — identifiers, not content (SIG-INGEST-045i).

        ``parameters["targets"]`` (live_targets rows or a fixture subset) bound
        the run but must stay inside the committed inventory: a target outside
        it is discovery — refused loud. Rows are scoped to the run's source id.
        """
        given = ctx.parameters.get("targets")
        source_id = getattr(ctx.source, "id", "") if ctx is not None else ""
        if not given:
            return [dict(t) for t in _targets_for(self._inventory, source_id=source_id)]
        known = self._inventory.urls
        out: list[Mapping[str, Any]] = []
        for t in given:
            url = str(t.get("url") or "")
            row = self._inventory.for_url(url)
            if url not in known or row is None:
                raise ValueError(
                    f"target {url!r} is not in the committed documentcloud "
                    "inventory — this connector discovers nothing; refusing to "
                    "address outside the committed set"
                )
            merged = {**dict(t)}
            merged.setdefault("id", row.id)
            merged.setdefault("kind", row.kind)
            merged.setdefault("source", row.source)
            merged.setdefault("platform", row.platform)
            out.append(merged)
        return out

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """The single bounded GET; the ONLY egress (SIG-INGEST-011).

        Order of the served path: target opt-out → politeness fetch →
        interstitial check → kind dispatch (parse + in-memory redaction +
        Part VIII screen → rendition, terms record, or the persisted refusal
        record). Every outcome lands on the run ledger BEFORE the exception
        carries it to the driver's recorded dispositions.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        url = str(target["url"])
        row = self._inventory.for_url(url) or self._inventory.get(str(target.get("id") or ""))
        if row is None:
            raise ValueError(f"target {url!r} names no committed documentcloud seed")
        if row.opted_out:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "opted_out",
                }
            )
            raise TargetOptedOut(row)
        try:
            result = ctx.fetcher.fetch(url)
        except HostOptOut:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "opt_out",
                }
            )
            raise
        except ReservationRefused as exc:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "rights_reservation",
                    "signals": sorted({s.kind for s in exc.verdict.signals}),
                }
            )
            raise
        except ChallengeEncountered as exc:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "challenge",
                    "status": exc.status,
                }
            )
            raise
        except Exception as exc:
            if failing_status_for_error(exc) is not None:
                self.outcomes.append(
                    {
                        "target": row.id,
                        "url": url,
                        "kind": row.kind,
                        "result": "refused",
                        "refusal_kind": "unreachable",
                    }
                )
            raise
        status = int(result.status)
        if failing_status_for_http(status) is not None:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": f"http_{status}",
                    "status": status,
                }
            )
            return result
        body = result.body or b""
        if _looks_like_interstitial(body):
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "interstitial",
                    "status": status,
                }
            )
            raise InterstitialEncountered(url)
        return self._dispatch(ctx, row, result)

    def _dispatch(self, ctx: RunContext, row: ReleaseTarget, result: FetchResult) -> FetchResult:
        url = row.url
        retrieved_at = result.retrieved_at.isoformat() if result.retrieved_at is not None else None
        body = result.body or b""
        try:
            if row.kind == "api_document":
                record, reason = parse_api_document(
                    body, target=row, retrieved_at=retrieved_at, decl=self._screen
                )
            elif row.kind == "api_project":
                record, reason = parse_api_project(
                    body, target=row, retrieved_at=retrieved_at, decl=self._screen
                )
            elif row.kind == "terms_page":
                record, reason = parse_terms_page(
                    body, target=row, retrieved_at=retrieved_at, decl=self._screen
                )
            else:
                record, reason = parse_public_page(
                    body, target=row, retrieved_at=retrieved_at, decl=self._screen
                )
        except RenditionSchemaError as exc:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refused",
                    "refusal_kind": "schema_refusal",
                    "detail": str(exc),
                }
            )
            raise SchemaRefusal(url, reason=str(exc)) from exc
        record_bytes = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        self._records[url] = record
        self._artifacts[url] = record_bytes
        if reason:
            # The rendition could not be made reliable — the persisted
            # artifact is the sig.documentcloud-refusal/1 record itself.
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "refusal_recorded",
                    "refusal_kind": reason,
                    "screen_hits": dict(record.get("screen_hits") or {}),
                    "original_sha256": record.get("original_sha256"),
                    "original_bytes": record.get("original_bytes"),
                }
            )
        else:
            self.outcomes.append(
                {
                    "target": row.id,
                    "url": url,
                    "kind": row.kind,
                    "result": "served",
                    "schema": record.get("schema"),
                    "uploader_page": record.get("uploader_page"),
                    "redacted_fields": [f["field"] for f in record.get("redacted_fields") or []],
                    "refused_fields": list(record.get("refused_fields") or []),
                    "original_sha256": record.get("original_sha256"),
                    "original_bytes": record.get("original_bytes"),
                    "screen": "clean",
                }
            )
        return result

    def capture(self, ctx: RunContext, fetched: FetchResult) -> CaptureRef:
        """Persist the screened record — NEVER the served page's own bytes.

        ``sig.documentcloud-rendition/1`` (allowlisted fields + redaction +
        refusal provenance + the original's sha256), ``sig.documentcloud-
        terms/1`` (verbatim bounded terms), or ``sig.documentcloud-refusal/1``
        (the recorded refusal) is the only artifact this connector stores —
        the bytes the in-memory screen demonstrably produced (ADR-185).
        """
        stored = self._artifacts.get(fetched.url)
        if stored is None:
            # Defensive path (a capture handed a FetchResult that never passed
            # through this connector's fetch — e.g. a resumed mark): refuse
            # rather than persist unscreened bytes (fail-closed).
            raise ValueError(
                f"{fetched.url!r} has no screened artifact — refused to persist "
                "bytes the in-memory screen never saw (ADR-185)"
            )
        return ctx.captures.put(
            stored,
            media_type="application/json",
            source_uri=fetched.url,
            retrieved_at=fetched.retrieved_at,
        )

    # -- interpretation (pure functions of the screened capture) --

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Read back the screened artifact (pure)."""
        doc = json.loads(ctx.captures.get(capture.digest).decode("utf-8"))
        if doc.get("schema") not in {RENDITION_SCHEMA, REFUSAL_SCHEMA, TERMS_SCHEMA}:
            raise ValueError(
                f"capture {capture.digest} is not a {RENDITION_SCHEMA}/"
                f"{REFUSAL_SCHEMA}/{TERMS_SCHEMA} record"
            )
        doc["_capture_digest"] = capture.digest
        doc["_retrieved_at"] = capture.retrieved_at.isoformat() if capture.retrieved_at else None
        return doc

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """One raw record per screened artifact — preserving raw values (P2)."""
        kind = {
            RENDITION_SCHEMA: "documentcloud_rendition",
            REFUSAL_SCHEMA: "documentcloud_refusal",
            TERMS_SCHEMA: "documentcloud_terms",
        }[str(parsed["schema"])]
        raw = {k: v for k, v in parsed.items() if not k.startswith("_")}
        raw.update(
            {
                "record_kind": kind,
                "capture_digest": str(parsed.get("_capture_digest", "")),
                "stored_media_type": "application/json",
                "stored_byte_size": len(
                    json.dumps(raw, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
                ),
                "retrieved_at": parsed.get("_retrieved_at"),
            }
        )
        return [raw]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Claims + record rows, in served order — uploader-page linkage on all.

        Per rendition capture: the ``document_index``/``collection_index``
        row (``released_documents`` linkage to the uploader's public page —
        every claim carries ``uploader_page``), the ``evidence_artifact``
        row (integrity ``screened_rendition`` — the rendition's digest is
        the provenance, never a document byte), the ``platform`` +
        ``acquisition_method`` claims, and a per-capture ``quality_report``.
        Per terms capture: the ``terms_capture`` record row (SIG-TRANSP-004).
        Per refusal: the ``capture_refusal`` record row — counts-only facts.
        Every emitted field name is checked against the committed Part VIII
        denylist: a denied name in emitted facts fails loud, never a warning.
        """
        attribution = _source_attribution(ctx)
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            denied = [k for k in raw.keys() if is_denied(str(k))]
            if denied:
                raise PredicateNotAllowed(
                    f"emitted fact carries Part VIII-denied field names {denied} — "
                    "protected fields fail loud, never a warning (SIG-PUB-002)"
                )
            kind = str(raw.get("record_kind") or "")
            source_id = str(raw.get("source") or "")
            uploader_page = str(raw.get("uploader_page") or "")
            capture_digest = str(raw.get("capture_digest") or "")
            if kind == "documentcloud_refusal":
                out.append(
                    _stamp(
                        {
                            "record_kind": "capture_refusal",
                            "subject_id": f"documentcloud:target:{raw.get('target_id')}",
                            "kind": str(raw.get("kind") or ""),
                            "platform": str(raw.get("platform") or ""),
                            "upstream_url": str(raw.get("upstream_url") or ""),
                            "uploader_page": uploader_page,
                            "reason": str(raw.get("reason") or ""),
                            "screen_hits": dict(raw.get("screen_hits") or {}),
                            "redacted_field_count": int(raw.get("redacted_field_count") or 0),
                            "refused_field_count": int(raw.get("refused_field_count") or 0),
                            "original_sha256": str(raw.get("original_sha256") or ""),
                            "original_bytes": int(raw.get("original_bytes") or 0),
                            "capture_digest": capture_digest,
                            "observed_at": _observed_date(raw.get("retrieved_at")),
                        },
                        attribution=attribution,
                        source_id=source_id,
                    )
                )
                continue
            if kind == "documentcloud_terms":
                out.append(
                    _stamp(
                        {
                            "record_kind": "terms_capture",
                            "subject_id": f"documentcloud:target:{raw.get('target_id')}",
                            "terms_url": str(raw.get("terms_url") or ""),
                            "terms_sha256": str(raw.get("terms_sha256") or ""),
                            "terms_truncated": bool(raw.get("terms_truncated")),
                            "uploader_page": uploader_page,
                            "capture_digest": capture_digest,
                            "captured_at": raw.get("retrieved_at"),
                            "observed_at": _observed_date(raw.get("retrieved_at")),
                            "note": "the platform terms text is captured verbatim on "
                            "the rendition record; this row carries its digest + "
                            "the capture facts (SIG-TRANSP-004)",
                        },
                        attribution=attribution,
                        source_id=source_id,
                    )
                )
                continue
            # documentcloud_rendition — the artifact + index + claims.
            from .records import EvidenceArtifactRow, evidence_artifact_id

            artifact_id = evidence_artifact_id(uploader_page or str(raw.get("upstream_url") or ""))
            artifact = EvidenceArtifactRow(
                artifact_id=artifact_id,
                source_id=source_id or ctx.source.id,
                source_uri=uploader_page or str(raw.get("upstream_url") or ""),
                capture_digest=capture_digest,
                media_type="application/json",
                byte_size=int(raw.get("stored_byte_size") or 0),
                records_request_id="",
                classification={
                    "verdict": "documentcloud_screened_rendition",
                    "kind": str(raw.get("kind") or ""),
                    "platform": str(raw.get("platform") or ""),
                },
                integrity="screened_rendition",
            )
            fields = dict(raw.get("fields") or {})
            is_collection = str(raw.get("kind") or "") in {"api_project", "project_page"}
            index_row = _stamp(
                {
                    "record_kind": "collection_index" if is_collection else "document_index",
                    "subject_id": artifact_id,
                    "predicate_id": assert_predicate_allowed("released_documents"),
                    "external_id": str(raw.get("document_id") or ""),
                    "raw_value": uploader_page,
                    "canonical_url": uploader_page,
                    "uploader_page": uploader_page,
                    "upstream_url": str(raw.get("upstream_url") or ""),
                    "platform": str(raw.get("platform") or ""),
                    "title": fields.get("title"),
                    "redacted_fields": [f["field"] for f in raw.get("redacted_fields") or []],
                    "refused_fields": list(raw.get("refused_fields") or []),
                    "integrity": "screened_rendition",
                    "original_sha256": str(raw.get("original_sha256") or ""),
                    "capture_digest": capture_digest,
                },
                attribution=attribution,
                source_id=source_id,
            )
            out.append(index_row)
            out.append(artifact.to_row())
            for predicate, value in (
                ("platform", str(raw.get("platform") or "")),
                ("acquisition_method", "public_page"),
            ):
                if not value:
                    continue
                out.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": artifact_id,
                            "predicate_id": assert_predicate_allowed(predicate),
                            "value": value,
                            "raw_value": value,
                            "capture_digest": capture_digest,
                            "uploader_page": uploader_page,
                            "observed_at": _observed_date(raw.get("retrieved_at")),
                            "extracted_field": predicate,
                        },
                        attribution=attribution,
                        source_id=source_id,
                    )
                )
            if fields.get("title"):
                out.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": artifact_id,
                            "predicate_id": assert_predicate_allowed("title"),
                            "value": str(fields["title"]),
                            "raw_value": str(fields["title"]),
                            "capture_digest": capture_digest,
                            "uploader_page": uploader_page,
                            "extracted_field": "title",
                        },
                        attribution=attribution,
                        source_id=source_id,
                    )
                )
            out.append(
                _stamp(
                    {
                        "record_kind": "quality_report",
                        "source_id": source_id,
                        "capture_digest": capture_digest,
                        "media_type": "application/json",
                        "byte_size": int(raw.get("stored_byte_size") or 0),
                        "capture_kind": "released_document_rendition",
                        "connector_name": self.name,
                        "connector_version": self.version,
                        "vocab_version": vocab_version(),
                        "claim_count": 0,
                        "note": "the persisted bytes are the screened rendition — "
                        "served page bytes were never stored (ADR-185)",
                    },
                    attribution=attribution,
                    source_id=source_id,
                )
            )
        return out

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Candidate linkages mint no entity refs (SIG-INGEST-034) — pass through."""
        return normalized

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only — leg B)."""
        return load_claims_for_l1(linked)


def _observed_date(raw: Any) -> date | None:
    """The capture's retrieval date — SIG's own observation time."""
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.strip()).date()
        except ValueError:
            try:
                return date.fromisoformat(raw.strip()[:10])
            except ValueError:
                return None
    return None


def _source_attribution(ctx: RunContext) -> str:
    """The source's recorded attribution (its rights block)."""
    try:
        return ctx.source.rights.attribution
    except AttributeError:  # pragma: no cover - defensive
        return "DocumentCloud / MuckRock public released-materials page (P36.77)"


def _stamp(row: dict[str, Any], *, attribution: str = "", source_id: str = "") -> dict[str, Any]:
    """Stamp source attribution + the training-deny marker onto a row.

    No licence label is invented for an UNDETERMINED-rights source — the
    export gate stays fail-closed. ``ai_training_permitted = false`` is
    stamped explicitly so the training gate refuses regardless of how the row
    travels downstream (SIG-LIC-004b). ``source_id`` is the inventory row's
    own source — a ``muckrock_public``-sourced rendition never borrows the
    ``documentcloud`` row's identity.
    """
    row["source_attribution"] = attribution
    row["source_id"] = source_id or row.get("source_id") or "documentcloud"
    row["ai_training_permitted"] = False
    if row.get("record_kind") == "claim":
        row.setdefault("evidence_genre", "released_records")
    return row


__all__ = [
    "CONNECTOR_NAME",
    "DEFAULT_SCREEN_DECLARATION",
    "REFUSAL_SCHEMA",
    "RENDITION_SCHEMA",
    "SOURCE_IDS",
    "TARGETS_SCHEMA",
    "TERMS_SCHEMA",
    "VOCAB_SCHEMA_ID",
    "DocumentCloudConnector",
    "InterstitialEncountered",
    "PredicateNotAllowed",
    "RedactionField",
    "ReleaseInventory",
    "ReleaseTarget",
    "Rendition",
    "RenditionSchemaError",
    "TargetOptedOut",
    "assert_predicate_allowed",
    "documentcloud_targets",
    "load_inventory",
    "load_screen_declaration",
    "parse_api_document",
    "parse_api_project",
    "parse_public_page",
    "parse_terms_page",
    "predicate_allowlist",
    "refusal_record",
    "terms_record",
    "vocab_version",
]
