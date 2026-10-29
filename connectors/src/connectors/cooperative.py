# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.78 — the Sourcewell + OMNIA Partners cooperative contract-page connector.

Row 353 lands the cooperative contract-page lane the I6/I7 discovery named
(the decision-catalog row is ``I7-C3`` — packet B-39, "fetch despite terms"
under ADR-184's envelope; the ticket's ``I7-C14`` label names no record —
recorded deviation): the committed seed set in
``data/cooperative_targets.toml`` — the public Sourcewell master-contract
page (101223-AXN), the two public OMNIA Partners supplier /
contract-documents index pages, and both platforms' governing terms pages —
is read as **redacted renditions only**. The connector never persists a
served page's own bytes: the Part VIII screen runs in memory over the
extraction surface and the canonical record before anything is written
(ADR-185), and a rendition that cannot be made reliable is a recorded
refusal — pointer + screened facts, never the raw page.

Five bounded kinds, one recorded GET each (leg A — the OM-20 row-353
mutation GATE-G5 named verbatim on 2026-10-25T18:40Z):

* ``contract_page`` — the Sourcewell public cooperative contract page
  (``/cooperative-purchasing/<slug>``): the master award's record of
  record — contract id + linked-document COUNT + title/meta extraction,
  never the linked PDF/XLSX binaries (pointers only).
* ``supplier_page`` — the OMNIA public supplier listing
  (``/suppliers/<slug>``): the cooperative-vehicle page a vendor states
  — no contract number on the public page, none minted.
* ``contract_documents_page`` — the OMNIA public contract-documents INDEX
  (``/suppliers/<slug>/public-sector/contract-documents``): the served
  public listing; the documents route through a member form — gated,
  recorded, never submitted, never fetched.
* ``sw_terms_page`` / ``om_terms_page`` — the platforms' terms pages
  captured verbatim (SIG-LIC-004a / the SIG-TRANSP-004 terms-capture
  family: URL + date + digest + text). Both platforms' terms
  affirmatively restrict automated extraction — the exposure is
  disclosed, the capture is verbatim, the bounded GET is the named
  mutation.

The redaction model (SIG-ENG-042): structural fields (URLs, ids, kinds,
counts, markers) are verbatim-allowlisted; every text candidate is
screened per field under the committed Part VIII declaration — a hit
drops the value into ``redacted_fields`` (name + classes + value sha256,
never the value); denied field NAMES in served payloads land in
``refused_fields`` (names only). The Sourcewell page's recorded hazard is
the I7-U478 private-person-name flag — staff contact names redact in
memory under the ``name`` screen. The finished rendition is screened
again: any residual hit — or an unparseable/binary page — persists only
a ``sig.cooperative-refusal/1`` record (upstream URL, classes, counts,
original sha256 + byte size), never raw bytes. Every emitted claim links
the cooperative's public contract page URL.

There is no discovery: ``discover()`` walks exactly the committed
inventory (a ``parameters["targets"]`` binding outside it is refused
loud), one polite GET per target through the shared layer — opt-out
register first (§26 rule 7), robots recorded under GL-GATE-08 (the I6
read recorded Sourcewell's robots.txt 200; a recorded verdict is never a
silent bypass), rate-limited, challenge-stopped (a 401/403/451/
2xx-interstitial ends the target's attempt — recorded, never defeated;
SIG-INGEST-037 permits no circumvention, challenge-solving, header
spoofing, proxy rotation, credentials or browser automation anywhere in
this module, and a test asserts none exists).

The source rows stay ``ingestion_permitted=false`` — ``sourcewell`` and
``omnia_partners`` are the cooperative-vehicle registry rows this lane
serves (``procurement_vocab.cooperative_vehicles`` members; the
piggyback-purchase claims a jurisdiction's contract rides are the
procurement lane's own records — never minted from a cooperative's
public page). Leg B, the first real host's wire/fetch as a connector
run, is the operator's act (OP-26), separately authorised. Nothing here
flips it.
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

CONNECTOR_NAME = "cooperative"
#: The registry source ids this connector serves: the two cooperative-
#: purchasing-vehicle rows whose public contract pages the lane reads
#: (``procurement_vocab.cooperative_vehicles`` members — the piggyback
#: claims a jurisdiction's purchase carries are the procurement lane's
#: own records, never minted from a cooperative's page).
SOURCE_IDS = ("omnia_partners", "sourcewell")

_TARGETS_TABLE = "cooperative_targets"
_VOCAB_TABLE = "cooperative_vocab"

TARGETS_SCHEMA = "sig.cooperative-targets/1"
VOCAB_SCHEMA_ID = "sig.cooperative-vocab/1"
RENDITION_SCHEMA = "sig.cooperative-rendition/1"
REFUSAL_SCHEMA = "sig.cooperative-refusal/1"
TERMS_SCHEMA = "sig.cooperative-terms/1"

#: The committed Part VIII screen declaration (P34.49 / ADR-185) — the same
#: document the at-rest audit parses, consumed through the same parser so the
#: connector-side screen is the auditable screen, never a drifted copy.
DEFAULT_SCREEN_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "at_rest_audit.toml"

#: Bounded verbatim captures — a runaway terms block flags itself.
_TERMS_CAP = 100_000

_JSON_SCRIPT_TYPES = frozenset({"application/json", "application/ld+json"})


# --- the committed seed inventory (data, not code) ----------------------------


@dataclass(frozen=True)
class ContractTarget:
    """One committed seed — identifiers + provenance, never content."""

    id: str
    source: str
    platform: str
    kind: str
    url: str
    contract_id: str
    expect: tuple[str, ...]
    evidence: str
    opted_out: bool = False


@dataclass(frozen=True)
class ContractInventory:
    """The committed seed set with its derivation provenance."""

    source_ref: str
    evidence_ref: str
    captured_on: str
    selection_rule: str
    targets: tuple[ContractTarget, ...]

    @property
    def urls(self) -> frozenset[str]:
        return frozenset(t.url for t in self.targets)

    def for_source(self, source_id: str) -> tuple[ContractTarget, ...]:
        return tuple(t for t in self.targets if t.source == source_id)

    def for_url(self, url: str) -> ContractTarget | None:
        for t in self.targets:
            if t.url == url:
                return t
        return None

    def get(self, target_id: str) -> ContractTarget | None:
        for t in self.targets:
            if t.id == target_id:
                return t
        return None


def _vocab() -> Mapping[str, Any]:
    """The committed ``sig.cooperative-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"cooperative vocabulary must be {VOCAB_SCHEMA_ID!r}")
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
            f"predicate {predicate_id!r} is not in the cooperative allowlist "
            f"({sorted(predicate_allowlist())})"
        )
    return predicate_id


def _kind_spec(kind: str) -> Mapping[str, Any]:
    spec = (_vocab().get("kinds") or {}).get(kind)
    if not isinstance(spec, Mapping):
        raise ValueError(f"cooperative vocabulary names no kind {kind!r}")
    return spec


def _url_is_public_surface(url: str, *, kind: str, platform: str) -> bool:
    """Whether ``url`` is a public unauthenticated surface of the committed kind.

    Public-only is a structural invariant, checked twice (inventory load and
    fetch): https only, no userinfo/query/fragment, the host in the
    platform's committed host set, the path matching the kind's reviewed
    pattern (``/cooperative-purchasing/<slug>``, ``/suppliers/<slug>``,
    ``/suppliers/<slug>/public-sector/contract-documents``, ``/terms-use``,
    ``/terms-of-use``). Anything else — a credential-bearing URL, a member
    endpoint, an uncommitted host — is not addressable.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.query or parts.fragment:
        return False
    hosts = {str(h) for h in (_vocab().get("hosts") or {}).get(platform) or ()}
    if parts.netloc.lower() not in hosts:
        return False
    return bool(re.search(str(_kind_spec(kind).get("path_re") or "$^"), parts.path))


def load_inventory() -> ContractInventory:
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
        raise ValueError(f"cooperative inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    opted = {str(s) for s in (inv.get("opted_out_targets") or [])}
    targets: list[ContractTarget] = []
    for i, row in enumerate(inv.get("targets") or []):
        if not isinstance(row, dict):
            raise ValueError(f"cooperative inventory target {i} must be a table")
        tid = str(row.get("id") or "")
        source = str(row.get("source") or "")
        platform = str(row.get("platform") or "")
        kind = str(row.get("kind") or "")
        url = str(row.get("url") or "")
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if not tid or not source or not platform or not kind or not url:
            raise ValueError(f"cooperative inventory target {i} needs id/source/platform/kind/url")
        if source not in SOURCE_IDS:
            raise ValueError(
                f"cooperative inventory target {tid!r}: source {source!r} is not one "
                f"of {SOURCE_IDS} — this connector serves no other row"
            )
        spec = _kind_spec(kind)
        if str(spec.get("platform") or "") != platform:
            raise ValueError(
                f"cooperative inventory target {tid!r}: kind {kind!r} is a "
                f"{spec.get('platform')!r} kind, not {platform!r}"
            )
        if not _url_is_public_surface(url, kind=kind, platform=platform):
            raise ValueError(
                f"cooperative inventory target {tid!r}: {url!r} is not the committed "
                "public unauthenticated surface of its kind (fail-closed)"
            )
        needs_expect = kind not in {"sw_terms_page", "om_terms_page"}
        if needs_expect and not expect:
            raise ValueError(
                f"cooperative inventory target {tid!r}: an empty expect list leaves "
                "the page-identity check unenforceable (fail-closed)"
            )
        targets.append(
            ContractTarget(
                id=tid,
                source=source,
                platform=platform,
                kind=kind,
                url=url,
                contract_id=str(row.get("contract_id") or ""),
                expect=expect,
                evidence=str(row.get("evidence") or ""),
                opted_out=tid in opted or url in opted,
            )
        )
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("cooperative inventory carries duplicate target ids")
    if ids != sorted(ids):
        raise ValueError("cooperative inventory is not id-sorted (deterministic order required)")
    declared = int(inv.get("target_count") or -1)
    if declared != len(targets):
        raise ValueError(
            f"cooperative inventory target_count={declared} but {len(targets)} rows committed"
        )
    return ContractInventory(
        source_ref=str(inv.get("source_ref") or ""),
        evidence_ref=str(inv.get("evidence_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        selection_rule=str(inv.get("selection_rule") or ""),
        targets=tuple(targets),
    )


def _targets_for(
    inventory: ContractInventory, *, source_id: str | None = None
) -> list[dict[str, Any]]:
    rows = inventory.targets if source_id is None else inventory.for_source(source_id)
    return [
        {
            "id": t.id,
            "url": t.url,
            "kind": t.kind,
            "source": t.source,
            "platform": t.platform,
            "contract_id": t.contract_id,
        }
        for t in rows
    ]


def cooperative_targets(source_id: str | None = None) -> list[dict[str, Any]]:
    """The ``{"id","url","kind"}`` targets ``live_targets.toml`` delegates to."""
    return _targets_for(load_inventory(), source_id=source_id)


def load_screen_declaration(path: str | Path | None = None) -> ScreenDeclaration:
    """The committed ``sig.at-rest-audit-decl/1`` — one parser, one document (ADR-185)."""
    p = Path(path) if path else DEFAULT_SCREEN_DECLARATION
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    return declaration_from_table(raw, source=str(p))


# --- extraction (pure — HTML meta/text, never a document binary) ---------------


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
    """Lift title text, meta fields, terms blocks, JSON islands and link counts."""

    def __init__(self, terms_ids: frozenset[str], doc_suffixes: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self._terms_ids = terms_ids
        self._doc_suffixes = doc_suffixes
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.json_blocks: list[str] = []
        self.terms_blocks: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical: str = ""
        self.doc_link_count = 0
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
        elif tag == "a":
            href = (attr.get("href") or "").strip().lower()
            if href and any(href.split("?")[0].endswith(sfx) for sfx in self._doc_suffixes):
                self.doc_link_count += 1
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

    target: ContractTarget
    contract_page: str
    contract_id: str
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
            "contract_page": self.contract_page,
            "contract_id": self.contract_id,
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
    target: ContractTarget,
    *,
    reason: str,
    screen_hits: Mapping[str, int] | None = None,
    redacted_count: int = 0,
    refused_count: int = 0,
    contract_page: str = "",
    body: bytes = b"",
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """The ``sig.cooperative-refusal/1`` record — pointer + screened facts only.

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
        "contract_page": contract_page,
        "reason": reason,
        "screen_hits": {str(k): int(v) for k, v in sorted((screen_hits or {}).items())},
        "redacted_field_count": int(redacted_count),
        "refused_field_count": int(refused_count),
        "original_sha256": _sha256(body),
        "original_bytes": len(body),
        "retrieved_at": retrieved_at,
    }


def terms_record(
    target: ContractTarget,
    *,
    terms_text: str,
    truncated: bool,
    body: bytes,
    retrieved_at: str | None,
) -> dict[str, Any]:
    """The ``sig.cooperative-terms/1`` verbatim terms capture (SIG-LIC-004a)."""
    return {
        "schema": TERMS_SCHEMA,
        "target_id": target.id,
        "kind": target.kind,
        "platform": target.platform,
        "source": target.source,
        "upstream_url": target.url,
        "contract_page": target.url,
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
    target: ContractTarget,
    structural: Mapping[str, Any],
    candidates: Mapping[str, Any],
    contract_page: str,
    contract_id: str,
    payloads: Iterable[Any],
    body: bytes,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], Rendition | None, dict[str, int], str]:
    """The in-memory redaction: fields in, a screened rendition or a refusal out.

    Returns ``(record_bytes_ready_state, rendition_or_None, payload_screen_hits,
    refusal_reason)`` — ``record`` is the rendition when the finished record
    screens clean, else the persisted ``sig.cooperative-refusal/1`` record.
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
        contract_page=contract_page,
        contract_id=contract_id,
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
                contract_page=contract_page,
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


def _html_scan(body: bytes) -> _PageScanner:
    terms_ids = frozenset(
        str(t).lower() for t in (_vocab().get("page") or {}).get("terms_element_ids") or ()
    )
    doc_suffixes = tuple(
        str(s).lower() for s in (_vocab().get("page") or {}).get("document_link_suffixes") or ()
    )
    scanner = _PageScanner(terms_ids, doc_suffixes)
    scanner.feed(body.decode("utf-8", errors="replace"))
    scanner.close()
    return scanner


def parse_public_page(
    body: bytes,
    *,
    target: ContractTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A public contract/supplier/index page → rendition/refusal.

    Title/meta extraction plus the linked-document COUNT — the page body and
    the linked documents are never carried. ``expect`` tokens verify page
    identity (a page contradicting its committed seed is refused whole);
    embedded JSON islands are scanned for denylist field NAMES
    (``refused_fields`` — names only); meta/title candidates screen
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
    contract_id = (
        target.contract_id or _opt_str(meta.get("contract_id") or meta.get("sig:contract_id")) or ""
    )
    contract_page = _opt_str(scanner.canonical) or _opt_str(meta.get("og:url")) or target.url
    if kind == "contract_page":
        collection_kind = "sourcewell_contract_page"
    elif kind == "supplier_page":
        collection_kind = "omnia_supplier_page"
    else:
        collection_kind = "omnia_contract_documents_page"
    member_gated = bool(_kind_spec(kind).get("member_gated"))
    slug = urlsplit(target.url).path.rstrip("/").rsplit("/", 1)[-1]
    structural = {
        "collection_kind": collection_kind,
        "canonical_url": contract_page,
        "page_slug": slug,
        "page_title_found": bool(title),
        "linked_document_count": scanner.doc_link_count,
        "documents_member_gated": member_gated or None,
    }
    candidates = {
        "title": _opt_str(title) or _opt_str(meta.get("og:title")),
        "description": _opt_str(meta.get("description") or meta.get("og:description")),
        "site_name": _opt_str(meta.get("og:site_name")),
        "author": _opt_str(meta.get("author") or meta.get("article:author")),
        "supplier_name": _opt_str(meta.get("sig:supplier") or meta.get("supplier")),
        "contact_name": _opt_str(meta.get("contact") or meta.get("sig:contact")),
        "agency": _opt_str(meta.get("sig:agency") or meta.get("jurisdiction")),
    }
    record, rendition, _hits, reason = _build_rendition(
        target=target,
        structural={k: v for k, v in structural.items() if v is not None},
        candidates=candidates,
        contract_page=contract_page,
        contract_id=contract_id,
        payloads=payloads,
        body=body,
        retrieved_at=retrieved_at,
        decl=decl,
    )
    return record, reason


def parse_terms_page(
    body: bytes,
    *,
    target: ContractTarget,
    retrieved_at: str | None,
    decl: ScreenDeclaration,
) -> tuple[dict[str, Any], str]:
    """A platform terms page → the verbatim ``sig.cooperative-terms/1`` capture.

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
                contract_page=target.url,
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

    def __init__(self, target: ContractTarget) -> None:
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
class CooperativeConnector(Connector):
    """The `cooperative` connector — public contract-page renditions.

    One polite GET per committed target per run through the shared politeness
    layer. The connector holds no HTTP client, no credential, no retry, and no
    circumvention capability of any kind (SIG-INGEST-011/013/037). It never
    performs entity resolution — claims are candidate linkages to the
    cooperative's public contract page only (SIG-INGEST-034); the contract
    subject key a contract_page emits is a candidate identifier the identity
    layer resolves.
    """

    name = CONNECTOR_NAME
    version = "1.0.0"

    def __init__(
        self,
        *,
        inventory: ContractInventory | None = None,
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
                    f"target {url!r} is not in the committed cooperative "
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
            raise ValueError(f"target {url!r} names no committed cooperative seed")
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

    def _dispatch(self, ctx: RunContext, row: ContractTarget, result: FetchResult) -> FetchResult:
        url = row.url
        retrieved_at = result.retrieved_at.isoformat() if result.retrieved_at is not None else None
        body = result.body or b""
        try:
            if row.kind in {"sw_terms_page", "om_terms_page"}:
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
            # artifact is the sig.cooperative-refusal/1 record itself.
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
                    "contract_page": record.get("contract_page"),
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

        ``sig.cooperative-rendition/1`` (allowlisted fields + redaction +
        refusal provenance + the original's sha256), ``sig.cooperative-
        terms/1`` (verbatim bounded terms), or ``sig.cooperative-refusal/1``
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
            RENDITION_SCHEMA: "cooperative_rendition",
            REFUSAL_SCHEMA: "cooperative_refusal",
            TERMS_SCHEMA: "cooperative_terms",
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
        """Claims + record rows, in served order — contract-page linkage on all.

        Per rendition capture: the ``contract_index``/``page_index`` row
        (the cooperative-page linkage — every claim carries
        ``contract_page``), the ``evidence_artifact`` row (integrity
        ``screened_rendition`` — the rendition's digest is the provenance,
        never a document byte), the ``platform`` + ``acquisition_method``
        claims, the ``contract``/``contract_number``/``external_id``
        claims on a ``contract_page`` (the master award's candidate
        subject — the record of record, never a piggyback or party),
        and a per-capture ``quality_report``. Per terms capture: the
        ``terms_capture`` record row (SIG-TRANSP-004). Per refusal: the
        ``capture_refusal`` record row — counts-only facts. Every emitted
        field name is checked against the committed Part VIII denylist: a
        denied name in emitted facts fails loud, never a warning.
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
            contract_page = str(raw.get("contract_page") or "")
            capture_digest = str(raw.get("capture_digest") or "")
            if kind == "cooperative_refusal":
                out.append(
                    _stamp(
                        {
                            "record_kind": "capture_refusal",
                            "subject_id": f"cooperative:target:{raw.get('target_id')}",
                            "kind": str(raw.get("kind") or ""),
                            "platform": str(raw.get("platform") or ""),
                            "upstream_url": str(raw.get("upstream_url") or ""),
                            "contract_page": contract_page,
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
            if kind == "cooperative_terms":
                out.append(
                    _stamp(
                        {
                            "record_kind": "terms_capture",
                            "subject_id": f"cooperative:target:{raw.get('target_id')}",
                            "terms_url": str(raw.get("terms_url") or ""),
                            "terms_sha256": str(raw.get("terms_sha256") or ""),
                            "terms_truncated": bool(raw.get("terms_truncated")),
                            "contract_page": contract_page,
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
            # cooperative_rendition — the artifact + index + claims.
            from .records import EvidenceArtifactRow, evidence_artifact_id

            artifact_id = evidence_artifact_id(contract_page or str(raw.get("upstream_url") or ""))
            artifact = EvidenceArtifactRow(
                artifact_id=artifact_id,
                source_id=source_id or ctx.source.id,
                source_uri=contract_page or str(raw.get("upstream_url") or ""),
                capture_digest=capture_digest,
                media_type="application/json",
                byte_size=int(raw.get("stored_byte_size") or 0),
                records_request_id="",
                classification={
                    "verdict": "cooperative_screened_rendition",
                    "kind": str(raw.get("kind") or ""),
                    "platform": str(raw.get("platform") or ""),
                },
                integrity="screened_rendition",
            )
            fields = dict(raw.get("fields") or {})
            is_contract = str(raw.get("kind") or "") == "contract_page"
            contract_id = str(raw.get("contract_id") or "")
            if is_contract:
                subject = _contract_subject(source_id, contract_id)
            else:
                subject = artifact_id
            index_row = _stamp(
                {
                    "record_kind": "contract_index" if is_contract else "page_index",
                    "subject_id": subject,
                    "predicate_id": assert_predicate_allowed(
                        "contract" if is_contract else "document"
                    ),
                    "external_id": contract_id,
                    "raw_value": contract_page,
                    "canonical_url": contract_page,
                    "contract_page": contract_page,
                    "upstream_url": str(raw.get("upstream_url") or ""),
                    "platform": str(raw.get("platform") or ""),
                    "artifact_id": artifact_id,
                    "title": fields.get("title"),
                    "linked_document_count": fields.get("linked_document_count"),
                    "documents_member_gated": fields.get("documents_member_gated"),
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
            if is_contract and contract_id:
                # The master award's record of record (§11.11): the contract
                # entity claim + its stated number/id — a candidate subject
                # key (SIG-INGEST-034), never a party or piggyback linkage.
                out.append(
                    _stamp(
                        {
                            "record_kind": "claim",
                            "subject_id": subject,
                            "predicate_id": assert_predicate_allowed("contract"),
                            "value": contract_id,
                            "raw_value": contract_id,
                            "capture_digest": capture_digest,
                            "contract_page": contract_page,
                            "observed_at": _observed_date(raw.get("retrieved_at")),
                            "extracted_field": "contract",
                        },
                        attribution=attribution,
                        source_id=source_id,
                    )
                )
                for predicate in ("contract_number", "external_id"):
                    out.append(
                        _stamp(
                            {
                                "record_kind": "claim",
                                "subject_id": subject,
                                "predicate_id": assert_predicate_allowed(predicate),
                                "value": contract_id,
                                "raw_value": contract_id,
                                "capture_digest": capture_digest,
                                "contract_page": contract_page,
                                "observed_at": _observed_date(raw.get("retrieved_at")),
                                "extracted_field": predicate,
                            },
                            attribution=attribution,
                            source_id=source_id,
                        )
                    )
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
                            "contract_page": contract_page,
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
                            "contract_page": contract_page,
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
                        "capture_kind": "cooperative_contract_page_rendition",
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


def _contract_subject(source_id: str, contract_id: str) -> str:
    """The master award's candidate subject key — a candidate, never a resolution.

    ``contract:<source>:<contract_id>`` under the pinned subject-key grammar
    (SIG-INGEST-034 — the identity layer resolves it; the connector only
    names the record of record the cooperative published).
    """
    from db.subject_keys import mint_subject_key

    return mint_subject_key("contract", source_id=source_id, external_id=contract_id)


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
        return "Sourcewell / OMNIA Partners public cooperative contract page (P36.78)"


def _stamp(row: dict[str, Any], *, attribution: str = "", source_id: str = "") -> dict[str, Any]:
    """Stamp source attribution + the training-deny marker onto a row.

    No licence label is invented for an UNDETERMINED-rights source — the
    export gate stays fail-closed. ``ai_training_permitted = false`` is
    stamped explicitly so the training gate refuses regardless of how the row
    travels downstream (SIG-LIC-004b). ``source_id`` is the inventory row's
    own source — an ``omnia_partners``-sourced rendition never borrows the
    ``sourcewell`` row's identity.
    """
    row["source_attribution"] = attribution
    row["source_id"] = source_id or row.get("source_id") or "sourcewell"
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
    "ContractInventory",
    "ContractTarget",
    "CooperativeConnector",
    "InterstitialEncountered",
    "PredicateNotAllowed",
    "RedactionField",
    "Rendition",
    "RenditionSchemaError",
    "TargetOptedOut",
    "assert_predicate_allowed",
    "cooperative_targets",
    "load_inventory",
    "load_screen_declaration",
    "parse_public_page",
    "parse_terms_page",
    "predicate_allowlist",
    "refusal_record",
    "terms_record",
    "vocab_version",
]
