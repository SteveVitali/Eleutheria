# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Bounded document adapters for the three pilot-dossier source families (P32.12).

§55.6 / SIG-ACQ-003 requires new acquisition adapters to use the existing
connector stages, the typed assertion contract, the actual capture store and
the fail-closed loader — this module adds ONE registered connector
(:class:`DossierDocumentsConnector`, name ``dossier_documents``) shared by the
three pilot source families (``dossier_okc`` / ``dossier_tulsa`` /
``dossier_san_diego``, all registry-gated `ingestion_permitted=false`), with
the per-source behaviour carried as data in ``data/dossier_documents_vocab.toml``
and the frozen named-target crosswalk in ``data/dossier_field_crosswalk.toml``.

The **common adapter interface** is the :class:`DossierFormatHandler` seam:
each configured target names a ``kind`` that selects one narrowly scoped format
handler, and a handler parses captured bytes into a reviewed document envelope
and then maps its configured fields onto typed, evidenced claims:

* ``clause_fields`` — a single captured document (HTML page or digital-native
  PDF) against a reviewed **field map**: every field is a crosswalk id whose
  row already fixes the predicate, qualifier semantics, object role, valid-time
  class and dossier rubric question; the target supplies only the verbatim
  ``literal`` (which MUST appear in the captured text — an absent literal is a
  recorded :class:`ContentDrift`, never a claim beyond the capture), the typed
  ``value``, and an optional field ``state`` (``answered`` /
  ``present_but_empty`` / ``absent`` / ``redacted``).
* ``index_listing`` — a captured index page against a reviewed link set: each
  declared listing must match an ``<a href>`` on the captured page and emits
  ``document`` / ``title`` (verbatim label — a version inside a label is never
  promoted to an effective date) plus an optional ``posted_date``.

Bounds the ticket imposes are mechanical, not conventional:

* **≤2 document protocols** — ``html_text`` and ``pdf_text`` (the existing
  layer-2/layer-3 engines). A captured document that is neither is an explicit
  unsupported-document failure; OCR or a third parser stack is out of scope.
* **Resource bounds** — ``max_document_bytes`` / ``max_pdf_pages`` /
  ``max_fields_per_document`` / ``max_text_chars`` / ``max_index_links`` from
  the vocab; exceeding any bound is a :class:`ContentDrift` before any claim is
  built, so a malformed, oversized, encrypted or unsupported document yields an
  explicit failure and **no partial affirmative claim**.
* **Genre guards** — the reviewed artifact genre (ADR-122) bars claims the
  document class cannot support: ``template_execution_guard`` refuses party /
  signature / value / term predicates on a ``template`` (a blank MOU proves
  structure, never an executed agreement), and ``subscription_hardware_guard``
  refuses device/deployment predicates on a ``access_mode = "subscription"``
  document (database access is never local hardware). Claims on a
  non-probative genre are stamped ``claim_directness = "D6"`` — the P32.3
  construction, made mechanical.
* **Field states** — a configured field that is ``present_but_empty`` or
  ``absent`` emits a ``disclosure_field_state`` claim (mandated != populated,
  the P24.7 vocabulary); a ``redacted`` field emits a ``somevalue`` claim
  (a value exists but is unknown) under its mapped predicate — never a
  fabricated literal.
* **The frozen crosswalk** — every field a target configures must resolve to a
  ``dossier_field_crosswalk.toml`` row whose predicate is in the committed
  ``ontology/vocab/predicates.yaml`` term list and whose object role agrees
  with :func:`db.organization_roles.role_for_predicate`. An unmapped or
  ``needs_amendment`` **required** field fails :func:`check_crosswalk` — the
  review fails closed and the row's recorded ``amendment`` is the scoped schema
  route (never an ad-hoc predicate). ``needs_amendment`` fields emit only a
  field-state record, never a value claim.

Every claim routes through :func:`dossier_claim`, which applies the predicate
allowlist, the shared Part VIII forbidden-token guard and the officer-naming
gate (consumed from :mod:`connectors.okc_documents`, not forked), and stamps
the sensitivity class, the declared evidence genre, the derived document
genre, the dossier-field and source-field provenance, and the crosswalk's
``assertion_rationale`` applicability note. ``link()`` twins organisation-role
claims through :func:`resolution.partner_identity.partner_ref_rows` under the
adapter's jurisdiction scope — name-only mints stay unmerged candidates
(SIG-TRUST-004). Nothing here fetches live: replay/shadow run over committed
fixtures under network isolation, and the three source rows stay
``ingestion_permitted=false`` until the operator's HG-03 review.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from db.organization_roles import OrganizationRole, role_for_predicate
from ontology.generate import load_vocab as ontology_vocab
from parsing.document import (
    byte_range_locator,
    html_links,
    html_text,
    page_locator_for,
    pdf_text_pages,
)
from parsing.genre import DocumentGenre, classify_genre
from parsing.locator import Locator
from policy.sensitivity import SensitivityClass, geo_tier_for
from resolution.partner_identity import PARTNER_PREDICATES, partner_ref_rows

from ._data import load_table
from .okc_documents import (
    assert_part_viii_safe,
    assert_person_naming_permitted,
)
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

__all__ = [
    "DOSSIER_DOCUMENTS",
    "DOSSIER_SOURCES",
    "CrosswalkViolation",
    "GenreGuardViolation",
    "UnmappedField",
    "DossierDocumentsConnector",
    "adapter_config",
    "check_crosswalk",
    "crosswalk",
    "crosswalk_version",
    "document_protocols",
    "field_map",
    "non_probative_genres",
    "predicate_allowlist",
    "resource_bounds",
    "vocab",
    "vocab_version",
]

DOSSIER_DOCUMENTS = "dossier_documents"

#: The three pilot source-family registry rows this connector serves. All stay
#: ``ingestion_permitted=false`` — the fixture runs are an engineering check,
#: never a rights decision or a live-access proof (SIG-ACQ-003).
DOSSIER_SOURCES = ("dossier_okc", "dossier_tulsa", "dossier_san_diego")


# --- the versioned vocabulary + frozen crosswalk (data, not code) --------------


@cache
def vocab() -> dict[str, Any]:
    """The adapter vocabulary (``data/dossier_documents_vocab.toml``)."""
    return load_table("dossier_documents_vocab")


def vocab_version() -> str:
    return str(vocab()["vocab_version"])


@cache
def crosswalk() -> dict[str, Any]:
    """The frozen named-target crosswalk (``data/dossier_field_crosswalk.toml``)."""
    return load_table("dossier_field_crosswalk")


def crosswalk_version() -> str:
    return str(crosswalk()["version"])


def document_protocols() -> tuple[str, ...]:
    """The ≤2 existing document protocols this adapter is bounded to."""
    return tuple(str(p) for p in vocab()["document_protocols"])


def non_probative_genres() -> frozenset[str]:
    """ADR-122 genres whose claims are stamped ``claim_directness = "D6"``."""
    return frozenset(str(g) for g in vocab()["non_probative_genres"])


def resource_bounds() -> Mapping[str, Any]:
    return vocab()["resource_bounds"]


def field_states() -> frozenset[str]:
    return frozenset(str(s) for s in vocab()["field_states"])


def adapter_config(source_id: str) -> Mapping[str, Any]:
    """The per-source adapter block (jurisdiction + predicate allowlist)."""
    adapters = vocab()["adapters"]
    if source_id not in adapters:
        raise KeyError(
            f"no dossier adapter configured for source {source_id!r}; known: {sorted(adapters)}"
        )
    return adapters[source_id]


def predicate_allowlist(source_id: str) -> frozenset[str]:
    """The predicates the adapter for ``source_id`` may write (SIG-INGEST-033)."""
    return frozenset(str(p) for p in adapter_config(source_id)["predicate_allowlist"])


# --- the crosswalk contract -----------------------------------------------------


@cache
def _ontology_predicate_ids() -> frozenset[str]:
    """The committed predicate vocabulary (ontology/vocab/predicates.yaml)."""
    return frozenset(str(p["predicate_id"]) for p in ontology_vocab("predicates")["predicates"])


@cache
def _ontology_artifact_genres() -> frozenset[str]:
    """The committed artifact-genre vocabulary (ADR-122)."""
    return frozenset(str(g) for g in ontology_vocab("predicates")["artifact_genres"])


class UnmappedField(ValueError):
    """A configured target field has no mapped crosswalk row (review fails closed)."""


class CrosswalkViolation(ValueError):
    """The frozen crosswalk is internally inconsistent or its fields do not resolve."""


class GenreGuardViolation(ValueError):
    """A document's reviewed genre/access mode bars the configured predicate."""


def field_map(field_id: str) -> Mapping[str, Any]:
    """The crosswalk row for ``field_id`` — every configured field MUST resolve."""
    fields = crosswalk()["fields"]
    if field_id not in fields:
        raise UnmappedField(
            f"field {field_id!r} has no row in dossier-field-crosswalk/1 — an unmapped "
            "field fails review and routes a scoped schema amendment, never an ad-hoc "
            "predicate (§55.6, SIG-ACQ-003)"
        )
    return fields[field_id]


def _validate_crosswalk_row(field_id: str, row: Mapping[str, Any]) -> list[str]:
    """Every invariant one crosswalk row must hold (reviewed, mechanical)."""
    problems: list[str] = []
    status = str(row.get("status", "mapped"))
    if status not in {"mapped", "needs_amendment"}:
        problems.append(f"field {field_id!r}: status {status!r} is not mapped/needs_amendment")
    predicate = str(row.get("predicate") or "")
    if status == "mapped":
        if not predicate:
            problems.append(f"field {field_id!r}: mapped row names no predicate")
        elif predicate not in _ontology_predicate_ids():
            problems.append(
                f"field {field_id!r}: predicate {predicate!r} is not in the committed "
                "predicates.yaml term list — no ad-hoc ontology (SIG-ACQ-003)"
            )
        role = str(row.get("object_role") or "")
        if role:
            try:
                expected = OrganizationRole(role)
            except ValueError:
                problems.append(f"field {field_id!r}: object_role {role!r} is not canonical")
                expected = None
            actual = role_for_predicate(predicate)
            if expected is not None and actual is not expected:
                problems.append(
                    f"field {field_id!r}: object_role {role!r} disagrees with "
                    f"role_for_predicate({predicate!r}) -> {actual}"
                )
    if status == "needs_amendment" and not str(row.get("amendment") or "").strip():
        problems.append(
            f"field {field_id!r}: needs_amendment row must record the scoped amendment text"
        )
    rubric = {str(q) for q in crosswalk()["dossier_fields"]}
    if str(row.get("dossier_field") or "") not in rubric:
        problems.append(
            f"field {field_id!r}: dossier_field {row.get('dossier_field')!r} is not "
            "a rubric q1..q12"
        )
    if str(row.get("valid_time") or "") not in {str(k) for k in crosswalk()["valid_time_kinds"]}:
        problems.append(f"field {field_id!r}: valid_time {row.get('valid_time')!r} is unknown")
    return problems


def check_crosswalk() -> list[str]:
    """Review the frozen crosswalk against the configured targets — ``[]`` is clean.

    Two independent checks: (1) every crosswalk row is internally valid
    (:func:`_validate_crosswalk_row`); (2) every field a ``dossier_*`` live
    target configures resolves to a mapped row — a **required** field that is
    unmapped or ``needs_amendment`` is a review failure routing the recorded
    scoped amendment, never an ad-hoc predicate.
    """
    violations: list[str] = []
    fields = crosswalk()["fields"]
    for field_id, row in fields.items():
        violations.extend(_validate_crosswalk_row(str(field_id), row))
    targets = load_table("live_targets")
    for source_id in DOSSIER_SOURCES:
        spec = targets.get(source_id) or {}
        for target in spec.get("targets", ()) or ():
            target_id = str(target.get("id") or target.get("url") or "target")
            genre = str(target.get("document_genre") or "")
            if genre and genre not in _ontology_artifact_genres():
                violations.append(
                    f"{source_id}:{target_id}: document_genre {genre!r} is not an "
                    "artifact genre in predicates.yaml"
                )
            configured = list(target.get("fields", ()) or ()) + [
                {**item, "field": "document"} for item in target.get("listings", ()) or ()
            ]
            for entry in configured:
                field_id = str(entry.get("field") or "")
                if field_id not in fields:
                    violations.append(
                        f"{source_id}:{target_id}: field {field_id!r} has no crosswalk row"
                    )
                    continue
                row = fields[field_id]
                if bool(row.get("required")) and str(row.get("status")) != "mapped":
                    violations.append(
                        f"{source_id}:{target_id}: required field {field_id!r} is "
                        f"{row.get('status')} — fails review; route the recorded scoped "
                        f"amendment: {str(row.get('amendment') or '(none)')[:120]}"
                    )
    return violations


# --- the genre guards (the ticket's three negative constructions) ---------------


def assert_genre_permits(
    source_id: str,
    *,
    document_genre: str,
    access_mode: str,
    predicate: str,
    doc_id: str,
) -> None:
    """Refuse a claim the document's reviewed genre/access mode cannot support.

    * ``template_execution_guard`` — a ``template`` never asserts an executed
      instrument (parties, signatures, values, term dates): a blank MOU is
      structure only.
    * ``subscription_hardware_guard`` — an ``access_mode = "subscription"``
      document never asserts local owned hardware (device counts, deployments,
      fixed assets): hosted database access is not sensor inventory.
    """
    allowed = predicate_allowlist(source_id)
    if predicate not in allowed:
        raise GenreGuardViolation(
            f"source {source_id!r} may write only {sorted(allowed)} "
            f"(SIG-INGEST-033); predicate {predicate!r} on document {doc_id!r} is "
            "outside its allowlist"
        )
    if document_genre == "template" and predicate in set(vocab()["template_execution_guard"]):
        raise GenreGuardViolation(
            f"document {doc_id!r} is genre 'template' — a template proves structure only "
            f"and may never assert {predicate!r} (an executed-instrument predicate; "
            "S2: a blank MOU is not a participant, purchase or deployment)"
        )
    if access_mode == "subscription" and predicate in set(vocab()["subscription_hardware_guard"]):
        raise GenreGuardViolation(
            f"document {doc_id!r} is access_mode 'subscription' — hosted database "
            f"access may never assert {predicate!r} (a local-hardware predicate; "
            "S2: the Vigilant subscription is access without hardware assets)"
        )


# --- the dossier claim shape -----------------------------------------------------


@dataclass(frozen=True)
class DocumentContext:
    """The provenance of one captured dossier document a claim was read from."""

    source_id: str
    source_url: str
    retrieved_date: str
    derived_genre: DocumentGenre  # byte-derived parsing genre — never trusted
    evidence_genre: str  # reviewed artifact genre (ADR-122)
    subject_id: str
    doc_id: str
    method: str
    access_mode: str
    media_type: str = "application/octet-stream"


def dossier_claim(
    ctx: DocumentContext,
    *,
    field_id: str,
    row: Mapping[str, Any],
    predicate: str,
    value: Any,
    raw_value: str,
    locator: Mapping[str, Any],
    value_kind: str | None = None,
    qualifiers: list[Mapping[str, Any]] | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    valid_edtf: str | None = None,
    raw_context: str | None = None,
    field_state: str | None = None,
    unit: str | None = None,
    object_type: str | None = None,
    rationale: str | None = None,
) -> dict[str, Any]:
    """Build one typed, evidenced, Part VIII-guarded dossier claim.

    Every predicate must (a) be inside the adapter allowlist AND the reviewed
    genre/access mode, (b) survive the shared Part VIII token guard and the
    officer-naming gate (consumed from :mod:`connectors.okc_documents`), and
    (c) carry the verbatim literal, the parser-layer locator, the declared
    evidence genre, the derived document genre, the dossier/source-field
    provenance, the sensitivity tier, and the crosswalk's applicability note.
    A non-probative evidence genre stamps ``claim_directness = "D6"``.
    """
    assert_genre_permits(
        ctx.source_id,
        document_genre=ctx.evidence_genre,
        access_mode=ctx.access_mode,
        predicate=predicate,
        doc_id=ctx.doc_id,
    )
    assert_part_viii_safe(predicate, raw_value)
    assert_person_naming_permitted(predicate)
    sensitivity = SensitivityClass(str(vocab()["default_sensitivity_class"]))
    claim: dict[str, Any] = {
        "record_kind": "claim",
        "connector": DOSSIER_DOCUMENTS,
        "source_id": ctx.source_id,
        "subject_id": ctx.subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2 — the source literal preserved verbatim
        "document_genre": ctx.derived_genre.value,
        "evidence_genre": ctx.evidence_genre,
        "document_id": ctx.doc_id,
        "source_field": field_id,
        "dossier_field": str(row.get("dossier_field") or ""),
        "sensitivity_class": sensitivity.value,
        "geo_tier": geo_tier_for(sensitivity),
        "assertion_rationale": rationale or str(row.get("applicability") or ""),
        "normalization_id": "dossier-field-crosswalk",
        "normalization_version": crosswalk_version(),
        "evidence": {
            "source_url": ctx.source_url,
            "retrieved_date": ctx.retrieved_date,
            "extraction_method": ctx.method,
            "locator": dict(locator),
        },
        "observed_at": ctx.retrieved_date,
        "source_attribution": ctx.source_id,
    }
    if ctx.evidence_genre in non_probative_genres():
        claim["claim_directness"] = "D6"
    if value_kind is not None:
        claim["value_kind"] = value_kind
    if object_type is not None:
        claim["object_type"] = object_type
    if unit is not None:
        claim["unit"] = unit
    if qualifiers:
        claim["qualifiers"] = [dict(q) for q in qualifiers]
    if valid_from is not None:
        claim["valid_from"] = valid_from
        claim["valid_from_kind"] = "exact"
    if valid_to is not None:
        claim["valid_to"] = valid_to
        claim["valid_to_kind"] = "exact"
    if valid_edtf is not None:
        claim["valid_edtf"] = valid_edtf
    if raw_context is not None:
        claim["raw_context"] = raw_context
    if field_state is not None:
        claim["field_state"] = field_state
    return claim


def _artifact_row(ctx: DocumentContext, capture_digest: str, byte_size: int) -> dict[str, Any]:
    """The ``evidence_artifact`` provenance row for one captured document."""
    return {
        "record_kind": "evidence_artifact",
        "connector": DOSSIER_DOCUMENTS,
        "source_id": ctx.source_id,
        "source_uri": ctx.source_url,
        "capture_digest": capture_digest,
        "media_type": ctx.media_type,
        "byte_size": byte_size,
        "document_id": ctx.doc_id,
        "document_genre_derived": ctx.derived_genre.value,
        "evidence_genre": ctx.evidence_genre,
        "access_mode": ctx.access_mode,
        "method": ctx.method,
        "retrieved_date": ctx.retrieved_date,
        "sensitivity_class": str(vocab()["default_sensitivity_class"]),
    }


# --- parse helpers ---------------------------------------------------------------


def _sniff(data: bytes) -> str:
    head = data[:512].lstrip()
    if head[:5] == b"%PDF-":
        kind = "a PDF document"
    elif head[:1] in (b"<",) or head[:14].lower().startswith(b"<!doctype html"):
        kind = "an HTML/XML page"
    elif head[:1] in (b"{", b"["):
        kind = "JSON"
    else:
        kind = "an unrecognised byte stream"
    return f"{len(data)} bytes of {kind}"


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _check_size(source_id: str, data: bytes, doc_id: str) -> None:
    bound = int(resource_bounds()["max_document_bytes"])
    if len(data) > bound:
        raise ContentDrift(
            source_id,
            f"document {doc_id!r} is {len(data)} bytes, over the {bound}-byte bound",
            details="an oversized document is an explicit failure — never a partial "
            "affirmative claim (§55.6 resource bound)",
        )


class _TextView:
    """The extracted text of a captured document + the locator factory for it."""

    def __init__(self, *, method: str, text: str, pages: tuple[str, ...], raw: bytes) -> None:
        self.method = method
        self.text = text
        self.pages = pages
        self.raw = raw

    def locate(self, needle: str) -> dict[str, Any] | None:
        """A typed locator for ``needle`` — byte_range into the capture for HTML,
        a 1-based page for a PDF (SIG-PARSE-003)."""
        if self.pages:
            return page_locator_for(self.pages, needle)
        return byte_range_locator(self.raw, needle)

    def document_scope_locator(self) -> dict[str, Any]:
        """A locator spanning the whole document — the evidence for a reviewed
        'absent' field (searched the whole capture, found nothing)."""
        if self.pages:
            return Locator.page(1).to_row()
        return Locator.byte_range(0, len(self.raw)).to_row()


def _text_view(source_id: str, data: bytes, doc_id: str) -> _TextView:
    """Extract the text layer via the ≤2 bounded protocols — fail closed.

    Anything that is not a text-bearing PDF or an HTML page is an explicit
    unsupported/malformed-document failure (no partial extraction ever leaves
    this function): encrypted, malformed, image-only and over-bound documents
    all surface here as :class:`ContentDrift`.
    """
    _check_size(source_id, data, doc_id)
    bounds = resource_bounds()
    head = data[:1024].lstrip()
    if head[:5] == b"%PDF-":
        pages = pdf_text_pages(data)
        if not pages:
            raise ContentDrift(
                source_id,
                f"document {doc_id!r} yielded no text layer (malformed, encrypted "
                "or image-only PDF)",
                details=_sniff(data),
            )
        if len(pages) > int(bounds["max_pdf_pages"]):
            raise ContentDrift(
                source_id,
                f"document {doc_id!r} has {len(pages)} pages, over the "
                f"{bounds['max_pdf_pages']}-page bound",
                details=_sniff(data),
            )
        text = "\n\n".join(pages)
        return _TextView(method="pdf_text", text=text, pages=pages, raw=data)
    if head[:1] == b"<" or head[:14].lower().startswith(b"<!doctype html"):
        text = html_text(data)
        if not text.strip():
            raise ContentDrift(
                source_id,
                f"document {doc_id!r} yielded no visible text",
                details=_sniff(data),
            )
        return _TextView(method="html_text", text=text, pages=(), raw=data)
    raise ContentDrift(
        source_id,
        f"document {doc_id!r} is not a supported format — this adapter reads "
        f"only {sorted(document_protocols())} (OCR/other parsers are out of scope)",
        details=_sniff(data),
    )


def _retrieved_date(capture: CaptureRef) -> str:
    if capture.retrieved_at is not None:
        return capture.retrieved_at.date().isoformat()
    return datetime.now(UTC).date().isoformat()


def _configured_target(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The run-context target spec for a capture URI (configured, never resolved)."""
    targets = list(ctx.parameters.get("targets", []) or ())
    for target in targets:
        if str(target.get("url") or "") == uri:
            return target
    # A single-target context (the fixture-runner shape) binds its one target
    # regardless of the served URL; a multi-target context never guesses.
    if len(targets) == 1:
        return targets[0]
    return None


def _derived_genre(data: bytes, doc_id: str) -> DocumentGenre:
    return classify_genre(doc_id, data).genre


def _document_context(
    source_id: str,
    derived: DocumentGenre,
    doc_meta: Mapping[str, Any],
) -> DocumentContext:
    declared_genre = str(doc_meta.get("document_genre") or "official_statement")
    # A probative declared genre whose derived genre KNOWINGLY disagrees is
    # drift — a declared executed_contract that reads as vendor marketing is not
    # the reviewed artifact. Non-probative declared genres (template etc.) are
    # never gated by the derived genre: template text reads like policy text.
    if (
        declared_genre not in non_probative_genres()
        and derived is not DocumentGenre.UNKNOWN
        and declared_genre in {"executed_contract", "contract"}
        and derived not in {DocumentGenre.PROCUREMENT_RECORD, DocumentGenre.POLICY_DOCUMENT}
    ):
        raise ContentDrift(
            source_id,
            f"document {doc_meta.get('doc_id')!r} is declared {declared_genre!r} but "
            f"classifies as {derived.value!r} — the reviewed artifact genre and the "
            "byte-derived genre disagree",
        )
    return DocumentContext(
        source_id=source_id,
        source_url=str(doc_meta["source_uri"]),
        retrieved_date=str(doc_meta["retrieved_date"]),
        derived_genre=derived,
        evidence_genre=declared_genre,
        subject_id=str(doc_meta["subject_id"]),
        doc_id=str(doc_meta["doc_id"]),
        method=str(doc_meta["method"]),
        access_mode=str(doc_meta.get("access_mode") or "document"),
        media_type=str(doc_meta.get("media_type") or "application/octet-stream"),
    )


# --- format handler: clause_fields ------------------------------------------------


def _resolve_field(
    source_id: str,
    entry: Mapping[str, Any],
    view: _TextView,
) -> dict[str, Any]:
    """Resolve one configured field against the captured text — locate its
    verbatim evidence or record its reviewed non-answer state."""
    field_id = str(entry.get("field") or "")
    row = field_map(field_id)  # UnmappedField if the crosswalk has no row
    state = str(entry.get("state") or "answered")
    if state not in field_states():
        raise ContentDrift(
            source_id,
            f"field {field_id!r} declares state {state!r}; known: {sorted(field_states())}",
        )
    label = str(entry.get("label") or "")
    literal = str(entry.get("literal") or "")
    out = {**dict(entry), "field": field_id, "state": state, "mapped": row}
    if state == "answered":
        if not literal:
            raise ContentDrift(
                source_id, f"field {field_id!r} is 'answered' but carries no literal"
            )
        locator = view.locate(literal)
        if locator is None:
            raise ContentDrift(
                source_id,
                f"the reviewed literal for field {field_id!r} is absent from the captured document",
                details=_sniff(view.raw),
            )
        out["locator"] = locator
    elif state in {"present_but_empty", "redacted"}:
        if not label:
            raise ContentDrift(
                source_id,
                f"field {field_id!r} is {state!r} but carries no locatable label",
            )
        locator = view.locate(label)
        if locator is None:
            raise ContentDrift(
                source_id,
                f"the label for {state} field {field_id!r} is absent from the captured document",
                details=_sniff(view.raw),
            )
        out["locator"] = locator
    else:  # absent — the reviewed-absent literal MUST NOT appear in the capture
        probe = label or literal
        if probe and view.locate(probe) is not None:
            raise ContentDrift(
                source_id,
                f"field {field_id!r} is reviewed 'absent' but its literal was "
                "located in the captured document",
                details=_sniff(view.raw),
            )
        out["locator"] = view.document_scope_locator()
    # An optional verbatim context span (scope/exception) rides beside the field.
    context = str(entry.get("context") or "")
    if context:
        if view.locate(context) is None:
            raise ContentDrift(
                source_id,
                f"the reviewed context literal for field {field_id!r} is absent "
                "from the captured document",
                details=_sniff(view.raw),
            )
        out["raw_context"] = context
    return out


def _parse_clause_fields(
    ctx: RunContext, capture: CaptureRef, target: Mapping[str, Any]
) -> dict[str, Any]:
    source_id = ctx.source.id
    data = ctx.captures.get(capture.digest)
    doc_id = str(target.get("doc_id") or target["id"])
    view = _text_view(source_id, data, doc_id)
    bounds = resource_bounds()
    entries = list(target.get("fields", ()) or ())
    if len(entries) > int(bounds["max_fields_per_document"]):
        raise ContentDrift(
            source_id,
            f"document {doc_id!r} configures {len(entries)} fields, over the "
            f"{bounds['max_fields_per_document']} bound",
        )
    if len(view.text) > int(bounds["max_text_chars"]):
        raise ContentDrift(
            source_id,
            f"document {doc_id!r} extracted {len(view.text)} text chars, over the "
            f"{bounds['max_text_chars']} bound",
        )
    fields = [_resolve_field(source_id, e, view) for e in entries]
    derived = _derived_genre(data, doc_id)
    # The doc envelope carries the provenance extract() needs — the pipeline
    # hands extract the parsed payload alone, so the capture's source URI,
    # retrieval date and media type are recorded here (the content-addressed
    # digest still binds the bytes).
    doc_meta = {
        "doc_id": doc_id,
        "subject_id": str(target["subject_id"]),
        "document_genre": str(target.get("document_genre") or "official_statement"),
        "access_mode": str(target.get("access_mode") or "document"),
        "source_uri": capture.source_uri,
        "retrieved_date": _retrieved_date(capture),
        "media_type": capture.media_type,
        "method": view.method,
        "capture_digest": capture.digest,
        "byte_size": len(data),
        "derived_genre": derived.value,
    }
    _document_context(source_id, derived, doc_meta)  # declared-vs-derived drift check
    return {"documents": [{"kind": "clause_fields", **doc_meta, "fields": fields}]}


def _field_claims(
    source_id: str,
    dctx: DocumentContext,
    entry: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Map one resolved field to its typed claim(s) through the crosswalk."""
    field_id = str(entry["field"])
    row = field_map(field_id)
    state = str(entry["state"])
    locator = entry["locator"]
    # needs_amendment fields never emit a value claim — only the field-state row
    # that records the routed scoped amendment (§55.6).
    if str(row.get("status")) != "mapped":
        return [
            dossier_claim(
                dctx,
                field_id=field_id,
                row=row,
                predicate="disclosure_field_state",
                value=field_id,
                raw_value=str(entry.get("label") or field_id),
                locator=locator,
                field_state="present_but_empty" if state == "answered" else state,
                rationale=(
                    f"field {field_id!r} has no existing-predicate mapping; the scoped "
                    "amendment is recorded on the crosswalk row "
                    f"({str(row.get('amendment'))[:160]})"
                ),
            )
        ]
    predicate = str(row["predicate"])
    qualifiers = entry.get("qualifiers")
    q_rows: list[Mapping[str, Any]] | None = (
        [dict(q) for q in qualifiers] if isinstance(qualifiers, list) else None
    )
    valid_from = entry.get("valid_from")
    valid_to = entry.get("valid_to")
    valid_edtf = entry.get("valid_edtf")
    # The crosswalk's valid_time class gates date promotion: a 'none' field may
    # not carry valid_* (observed_at still records capture time).
    if (valid_from or valid_to or valid_edtf) and str(row.get("valid_time")) == "none":
        raise CrosswalkViolation(
            f"field {field_id!r} promotes valid_* but its crosswalk row is "
            "valid_time='none' — a record's posting/as-of is not an effective date"
        )
    if state == "answered":
        return [
            dossier_claim(
                dctx,
                field_id=field_id,
                row=row,
                predicate=predicate,
                value=entry.get("value"),
                raw_value=str(entry["literal"]),
                locator=locator,
                qualifiers=q_rows,
                valid_from=str(valid_from) if valid_from else None,
                valid_to=str(valid_to) if valid_to else None,
                valid_edtf=str(valid_edtf) if valid_edtf else None,
                raw_context=entry.get("raw_context"),
                object_type=str(row.get("object_type") or "") or None,
                unit=str(row.get("unit") or "") or None,
            )
        ]
    if state == "redacted":
        # A value exists but is withheld: `somevalue`, never a fabricated literal.
        return [
            dossier_claim(
                dctx,
                field_id=field_id,
                row=row,
                predicate=predicate,
                value=None,
                raw_value=str(entry.get("label") or field_id),
                locator=locator,
                value_kind="somevalue",
                field_state="redacted",
                rationale=(
                    f"field {field_id!r} is present but redacted on the document — "
                    "a value exists, unknown"
                ),
            )
        ]
    # present_but_empty / absent — the mandated != populated record.
    return [
        dossier_claim(
            dctx,
            field_id=field_id,
            row=row,
            predicate="disclosure_field_state",
            value=field_id,
            raw_value=str(entry.get("label") or field_id),
            locator=locator,
            field_state=state,
        )
    ]


def _extract_clause_fields(
    ctx: RunContext,
    parsed: Mapping[str, Any],
    doc: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    source_id = ctx.source.id
    derived = DocumentGenre(str(doc["derived_genre"]))
    dctx = _document_context(source_id, derived, doc)
    out: list[Mapping[str, Any]] = [
        _artifact_row(dctx, str(doc["capture_digest"]), int(doc["byte_size"]))
    ]
    for entry in doc["fields"]:
        out.extend(_field_claims(source_id, dctx, entry))
    return out


# --- format handler: index_listing -------------------------------------------------


def _parse_index_listing(
    ctx: RunContext, capture: CaptureRef, target: Mapping[str, Any]
) -> dict[str, Any]:
    source_id = ctx.source.id
    data = ctx.captures.get(capture.digest)
    doc_id = str(target.get("doc_id") or target["id"])
    if data[:1024].lstrip()[:5] == b"%PDF-":
        raise ContentDrift(
            source_id,
            f"index document {doc_id!r} is a PDF — the index_listing handler reads "
            "HTML index pages only",
            details=_sniff(data),
        )
    _check_size(source_id, data, doc_id)
    text = html_text(data)
    if not text.strip():
        raise ContentDrift(
            source_id, f"index document {doc_id!r} yielded no visible text", details=_sniff(data)
        )
    links = html_links(data, capture.source_uri)
    bound = int(resource_bounds()["max_index_links"])
    if len(links) > bound:
        raise ContentDrift(
            source_id,
            f"index document {doc_id!r} carries {len(links)} links, over the {bound}-link bound",
        )
    listings: list[dict[str, Any]] = []
    for spec in target.get("listings", ()) or ():
        url_contains = str(spec.get("url_contains") or "")
        label_contains = str(spec.get("label_contains") or "")
        matches = [
            link
            for link in links
            if url_contains in link.url and label_contains.lower() in link.anchor.lower()
        ]
        if not matches:
            raise ContentDrift(
                source_id,
                f"index document {doc_id!r} no longer lists the reviewed link "
                f"({label_contains!r} ~ {url_contains!r})",
                details=_sniff(data),
            )
        link = matches[0]
        locator = byte_range_locator(data, link.anchor)
        posted = str(spec.get("posted_date") or "")
        posted_locator = byte_range_locator(data, posted) if posted else None
        if posted and posted_locator is None:
            raise ContentDrift(
                source_id,
                f"the declared posted_date {posted!r} for listing {link.anchor!r} is "
                "absent from the captured index",
                details=_sniff(data),
            )
        listings.append(
            {
                **dict(spec),
                "url": link.url,
                "anchor": link.anchor,
                "locator": locator,
                "posted_locator": posted_locator,
            }
        )
    derived = _derived_genre(data, doc_id)
    doc_meta = {
        "doc_id": doc_id,
        "subject_id": str(target["subject_id"]),
        "document_genre": str(target.get("document_genre") or "portal_document"),
        "access_mode": str(target.get("access_mode") or "document"),
        "source_uri": capture.source_uri,
        "retrieved_date": _retrieved_date(capture),
        "media_type": capture.media_type,
        "method": "html_text",
        "capture_digest": capture.digest,
        "byte_size": len(data),
        "derived_genre": derived.value,
    }
    return {
        "documents": [
            {
                "kind": "index_listing",
                **doc_meta,
                "link_count": len(links),
                "listings": listings,
            }
        ]
    }


def _extract_index_listing(
    ctx: RunContext,
    parsed: Mapping[str, Any],
    doc: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    source_id = ctx.source.id
    derived = DocumentGenre(str(doc["derived_genre"]))
    dctx = _document_context(source_id, derived, doc)
    out: list[Mapping[str, Any]] = [
        _artifact_row(dctx, str(doc["capture_digest"]), int(doc["byte_size"]))
    ]
    for listing in doc["listings"]:
        anchor = str(listing["anchor"])
        # The listed document's existence + verbatim label. A year/version inside
        # the label stays text — never promoted to effective (S2).
        out.append(
            dossier_claim(
                dctx,
                field_id="document",
                row=field_map("document"),
                predicate="document",
                value=str(listing["url"]),
                raw_value=anchor,
                locator=listing["locator"],
                rationale="the index lists this document (existence + link) — the "
                "label is verbatim and asserts nothing about the document's contents",
            )
        )
        out.append(
            dossier_claim(
                dctx,
                field_id="title",
                row=field_map("title"),
                predicate="title",
                value=anchor,
                raw_value=anchor,
                locator=listing["locator"],
            )
        )
        if listing.get("posted_locator"):
            out.append(
                dossier_claim(
                    dctx,
                    field_id="posted_date",
                    row=field_map("posted_date"),
                    predicate="posted_date",
                    value=str(listing["posted_date"]),
                    raw_value=str(listing["posted_date"]),
                    locator=listing["posted_locator"],
                )
            )
    out.append(
        {
            "record_kind": "index_page",
            "connector": DOSSIER_DOCUMENTS,
            "source_id": source_id,
            "source_uri": dctx.source_url,
            "capture_digest": doc["capture_digest"],
            "media_type": dctx.media_type,
            "byte_size": doc["byte_size"],
            "document_id": doc["doc_id"],
            "link_count": doc["link_count"],
            "listings_resolved": len(doc["listings"]),
            "retrieved_date": dctx.retrieved_date,
        }
    )
    return out


_PARSE = {
    "clause_fields": _parse_clause_fields,
    "index_listing": _parse_index_listing,
}
_EXTRACT = {
    "clause_fields": _extract_clause_fields,
    "index_listing": _extract_index_listing,
}


# --- the shared connector -----------------------------------------------------------


@register
class DossierDocumentsConnector(Connector):
    """The common bounded document adapter for the pilot dossiers (P32.12).

    One registered connector shared by the three gated source rows; each
    configured target names a ``kind`` selecting a narrowly scoped format
    handler (``clause_fields`` / ``index_listing``). All eight stages are the
    framework's: discover→fetch acquire the reviewed document through the shared
    politeness layer, parse→extract are pure functions of the captured bytes,
    link() twins organisation roles under the adapter's jurisdiction scope, and
    load() stamps claim ids. Registry rows stay ``ingestion_permitted=false`` —
    fixture success is an engineering check, never a rights decision.
    """

    name = DOSSIER_DOCUMENTS
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        target = _configured_target(ctx, capture.source_uri)
        if target is None:
            raise ContentDrift(
                ctx.source.id,
                f"no configured dossier target names the captured URL "
                f"{capture.source_uri!r} — the adapter reads only reviewed targets",
            )
        kind = str(target.get("kind") or "")
        parser = _PARSE.get(kind)
        if parser is None:
            raise ContentDrift(
                ctx.source.id,
                f"target {target.get('id')!r} declares unknown kind {kind!r}; "
                f"known: {sorted(_PARSE)}",
            )
        return parser(ctx, capture, target)

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        out: list[Mapping[str, Any]] = []
        # The parsed envelope carries every provenance field extract needs
        # (capture digest, source URI, retrieved date, declared genre) — the
        # pipeline hands this stage the parsed payload alone.
        for doc in parsed.get("documents", []):
            kind = str(doc.get("kind") or "")
            extractor = _EXTRACT.get(kind)
            if extractor is None:
                raise ValueError(
                    f"unknown dossier document kind {kind!r} (document "
                    f"{doc.get('doc_id')!r}); known: {sorted(_EXTRACT)}"
                )
            out.extend(extractor(ctx, parsed, doc))
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        version = vocab_version()
        return [{**row, "vocab_version": version} for row in raw_claims]

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # P32.3: organisation-role claims get entity-ref twins under the adapter's
        # jurisdiction scope (name-only mints stay unmerged candidates).
        adapter = adapter_config(ctx.source.id)
        return partner_ref_rows(
            normalized,
            predicates=PARTNER_PREDICATES,
            scope=ctx.source.id,
            jurisdiction=str(adapter.get("jurisdiction") or "") or None,
        )

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in linked:
            if row.get("record_kind", "claim") == "claim":
                out.append(
                    {
                        **row,
                        "claim_id": str(uuid4()),
                        "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                    }
                )
            else:
                out.append(dict(row))
        return out
