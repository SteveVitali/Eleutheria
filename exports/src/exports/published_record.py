# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.published-record`` UI projection (P32.13 / ADR-132, SIG-FIND-002).

One ``PublishedRecord`` is the citation unit of a released public record: a
compartment-scoped view of one entity's published site slice — label, point,
published facts (claim anchors), source attribution, evidence anchors and
honest unavailability states — serialised deterministically under the release
namespace ``/r/<publication_id>/c/<compartment>/entity/<type>/<uuid>``.

The projection is deliberately **ID-free until the namespace is bound**: the
document hashed into the release descriptor carries no ``publication_id`` and
no ``href`` (those fields exist only after the descriptor digest is known), so
the projection root is a pure function of the ADMITTED CONTENT — alter any
projection input and the namespace changes; recompute the same inputs and the
namespace is byte-identical (SIG-FIND-001).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from policy.sensitivity import assert_public_layer_subject
from policy.transparency import NO_UPSTREAM_URL

from .manifest import canonical_json, sha256_hex
from .statements import STATEMENT_SCHEMA

#: The projection schema/version stamped on every record and hashed into the
#: publication descriptor — a renderer/projection change is a NEW namespace.
#: /1 → /2 (P35.15a / PKG-07): the record doc gains ``technology`` — the
#: subject's declared SKOS slug (id + basis), the map/search facet source.
#: /3 → /4 (P35.36 / R11-K13-TX-08a, SIG-TRANSP-011): ``source_refs`` gains the
#: S-6-gated ``upstream_*`` block (``upstream_href`` stops being a constant
#: ``None`` — J1 NEW-10) and the record embeds ``claim_statements`` — the
#: ``sig.statement/1`` rows the per-claim provenance panel renders (UXR-33's
#: one contract — the record page reads the same statements the release's
#: ``statements.jsonl`` publishes).
PROJECTION_VERSION = "sig.published-record/4"


def record_key(compartment: str, entity_type: str, entity_id: str) -> str:
    """The stable, compartment-scoped record key (``ccby3:deployment:<uuid>``)."""
    return f"{compartment}:{entity_type}:{entity_id}"


@dataclass(frozen=True)
class ClaimAnchor:
    """One claim anchor: the spine-issued claim id plus the published-shape
    detail the release admits (never a raw sensitive literal — predicate,
    basis and status only, matching the site-row gating)."""

    claim_id: str
    predicate_id: str | None = None
    observed_at: str | None = None
    source_id: str | None = None
    #: ``recorded`` when the claim detail was published with the record;
    #: ``unlocated`` when only the opaque anchor is known for this release.
    locator: str = "recorded"
    #: P34.34a (SIG-UI-024): the §12.2 access-edge type the claim carries —
    #: ``configured_access`` / ``observed_use`` / ``declared_policy`` /
    #: ``unclassified`` — emitted on the JSON only when the claim is an
    #: access-typed claim (``None`` on an ordinary observation claim keeps
    #: the released document byte-identical for non-edge records).
    access_kind: str | None = None

    def as_json(self) -> dict[str, Any]:
        doc = {
            "claim_id": self.claim_id,
            "predicate_id": self.predicate_id,
            "observed_at": self.observed_at,
            "source_id": self.source_id,
            "locator": self.locator,
        }
        if self.access_kind is not None:
            doc["access_kind"] = self.access_kind
        return doc


@dataclass(frozen=True)
class EvidenceRef:
    """One evidence anchor: claim → capture → artifact, honest about every
    unlocatable leg (``capture_id``/``artifact_id`` may be ``None`` — the
    anchor still resolves, to an explicit unavailable state)."""

    claim_id: str
    capture_id: str | None
    artifact_id: str | None
    role: str | None = None
    #: ``metadata_only`` — the capture bytes are not served (§17.5); the page
    #: states the metadata locator. ``unlocated`` — no binding published.
    access: str = "metadata_only"
    #: P35.36 (J3 §5.1): the binding's recorded ``claim_evidence.binding_status``
    #: — carried through from the ``sig.statement/1`` row; ``None`` on a
    #: pre-P35.36 claim index (the old ``record_claims`` shape) keeps the
    #: released document byte-identical.
    binding_status: str | None = None

    def as_json(self) -> dict[str, Any]:
        doc = {
            "claim_id": self.claim_id,
            "capture_id": self.capture_id,
            "artifact_id": self.artifact_id,
            "role": self.role,
            "access": self.access,
        }
        if self.binding_status is not None:
            doc["binding_status"] = self.binding_status
        return doc


@dataclass(frozen=True)
class PublishedRecord:
    """The ``sig.published-record/2`` document — one released public record."""

    record_key: str
    entity_id: str
    entity_type: str
    compartment: str
    license: str
    label: dict[str, Any]  # {"text": str|None, "basis": str}
    #: P35.15a / PKG-07: the subject's declared SKOS technology slug —
    #: {"id": str|None, "basis": "declared_technology_claim" | "conflicted" |
    #: "unreported"} — never an inferred class.
    technology: dict[str, Any]
    #: P35.19 / JUR-02b (K4 §3.4): ``{id, jkey, chain[], basis, check,
    #: declared:{scheme,value}|null, boundary_vintage}`` — ``id`` stays the
    #: legacy declared bucket; the placement fields are ``None``/``[]`` when
    #: the release's export ran no placement (declared-empty, never invented).
    jurisdiction: dict[
        str, Any
    ]  # {"id", "jkey", "chain", "basis", "check", "declared", "boundary_vintage"}
    location: dict[str, Any]  # {"kind", "lat"?, "lon"?, "precision"?}
    claim_anchors: tuple[ClaimAnchor, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    source_refs: tuple[dict[str, Any], ...] = ()
    #: P35.36 (R11-K13-TX-08a / J3 §5.1–5.2): the ``sig.statement/1`` rows for
    #: this record's claims — the same published statements the release's
    #: ``<comp>/statements.jsonl`` ships, embedded so the record JSON alone
    #: carries the provenance panel's full field set (the JSON twin IS the
    #: panel's data contract). Empty on a pre-P35.36 claim index — the page
    #: then renders the named-absence panel, never a fabricated statement.
    claim_statements: tuple[dict[str, Any], ...] = ()
    coverage: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    #: Bound AFTER the namespace is computed — excluded from the ID-free doc.
    publication_id: str | None = None
    href: str | None = None
    json_href: str | None = None
    #: P35.13 / SIG-REL-009 (G3 §6.1): the JSON twin's provenance blocks —
    #: ``release {label, publication_id, as_of_world}`` names the release the
    #: record is bound into (``label`` is ``None`` on a v1 build, which has no
    #: human label — declared-empty, never invented), and ``licence {id,
    #: compartment}`` restates the record's own licence in the block form.
    #: Both are bound-view fields, never hashed into the projection.
    release: dict[str, Any] | None = None
    licence: dict[str, Any] | None = None
    schema: str = PROJECTION_VERSION

    # -- serialisation -------------------------------------------------------- #

    def id_free_doc(self) -> dict[str, Any]:
        """The canonical content document hashed into the descriptor —
        every byte is a pure function of admitted inputs (no publication id,
        no public URLs, no timestamps)."""
        return {
            "schema": self.schema,
            "record_key": self.record_key,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "compartment": self.compartment,
            "license": self.license,
            "label": self.label,
            "technology": self.technology,
            "jurisdiction": self.jurisdiction,
            "location": self.location,
            "claim_anchors": [a.as_json() for a in self.claim_anchors],
            "evidence_refs": [e.as_json() for e in self.evidence_refs],
            "source_refs": [dict(s) for s in self.source_refs],
            "claim_statements": [dict(s) for s in self.claim_statements],
            "coverage": dict(self.coverage),
            "review": dict(self.review),
        }

    def as_json(self) -> dict[str, Any]:
        """The full served record (``<uuid>.json``) — the ID-free document plus
        the bound namespace fields. Byte-identical for identical inputs."""
        doc = self.id_free_doc()
        doc["publication_id"] = self.publication_id
        doc["href"] = self.href
        doc["json_href"] = self.json_href
        # P35.13 (SIG-REL-009): the JSON twin's provenance blocks — declared-
        # empty when the record was bound without a release (e.g. a bare
        # projection call outside a release build), never absent.
        doc["release"] = dict(self.release) if self.release is not None else None
        doc["licence"] = dict(self.licence) if self.licence is not None else None
        return doc

    def json_bytes(self) -> bytes:
        return canonical_json(self.as_json())

    def bind(
        self,
        publication_id: str,
        *,
        release_label: str | None = None,
        as_of_world: str | None = None,
    ) -> PublishedRecord:
        """Bind the namespace: fill ``publication_id``/``href``/``json_href``
        plus the §6.1 ``release``/``licence`` provenance blocks (P35.13,
        SIG-REL-009). ``release_label`` is the release's ``sig-YYYY-MM-DD.N``
        human label — ``None`` on a v1 build (declared-empty); ``as_of_world``
        is the release's data-as-of instant, never derived here."""
        base = (
            f"/r/{publication_id}/c/{self.compartment}/entity/{self.entity_type}/{self.entity_id}"
        )
        return replace(
            self,
            publication_id=publication_id,
            href=f"{base}/",
            json_href=f"{base}.json",
            release={
                "label": release_label,
                "publication_id": publication_id,
                "as_of_world": as_of_world,
            },
            licence={"id": self.license, "compartment": self.compartment},
        )


def record_from_site_row(
    row: Mapping[str, Any],
    *,
    compartment: str,
    license_id: str,
    claim_index: Mapping[str, Mapping[str, Any]] | None = None,
    jurisdiction_slug_paths: Mapping[str, str] | None = None,
) -> PublishedRecord:
    """Project one ``<comp>/sites.jsonl`` row into a :class:`PublishedRecord`.

    ``row`` is the licence-sliced site row already produced by
    ``_slice_sites`` — every field it carries survived the P32.5 publication
    gate, so the record NEVER reintroduces a refused/withdrawn subject.
    ``claim_index`` (optional) maps claim_id → the ``record_claims`` row
    emitted beside the sites (predicate/observed_at/source/evidence); a
    release built from a pre-P32.13 export that lacks the artifact degrades
    honestly — anchors carry ``locator: "unlocated"``, never a fabricated
    predicate.
    """
    entity_id = str(row["entity_id"])
    entity_type = str(row.get("entity_type") or "deployment")
    # P35.66 (SIG-PUB-011/013): the publish refusal at the record surface —
    # a candidate asset or a residential-parcel-flagged subject reaching this
    # projection is a build error, never a warning. The emit/shaping paths
    # already exclude them; this is the enforced backstop on the row itself.
    assert_public_layer_subject(
        entity_type,
        residential_parcel_flag=bool(row.get("residential_parcel_flag")),
        surface="published_record",
    )
    rights = dict(row.get("_rights") or {})
    geometry = row.get("geometry")
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    point_status = str(row.get("point_status") or "")
    placed = "placement_check" in row
    if coords and point_status == "resolved":
        location: dict[str, Any] = {
            "kind": "point",
            "lat": coords[1],
            "lon": coords[0],
            "precision": str(row.get("precision") or "unreported"),
        }
    elif placed and point_status == "resolved":
        # P35.19: the envelope resolved a point but ``placement@1`` withheld
        # it (suspected swap/flip, rejected null-island/invalid, or a guarded
        # agency centroid) — the record names the verdict, never re-publishes
        # the pair.
        location = {"kind": "point_withheld", "reason": row.get("placement_check")}
    elif coords:
        location = {"kind": "unresolved_point", "precision": point_status or "unreported"}
    else:
        location = {"kind": "unreported"}

    label_text = row.get("label")
    # P35.29 (K2 §3/L-1): the label is the shared registry's — its basis is the
    # row's recorded ``label_basis``; a pre-P35.29 row keeps the old vocabulary.
    label_basis = row.get("label_basis")
    label = {
        "text": str(label_text) if label_text else None,
        "basis": (
            str(label_basis) if label_basis else ("source_label" if label_text else "unlabelled")
        ),
    }
    jurisdiction_id = row.get("jurisdiction")
    jurisdiction: dict[str, Any] = {
        "id": str(jurisdiction_id) if jurisdiction_id else None,
        "basis": "camera_jurisdiction" if jurisdiction_id else "unreported",
    }
    # P35.19 / K4 §3.4: the placement block rides the same jurisdiction
    # object — ``jkey`` is the located-or-declared canonical key; ``declared``
    # is the scheme/value pair the claim carried (``null`` when undeclared).
    # The block shape is exactly §3.4's: ``basis`` names the placement basis
    # (point_in_polygon|declared|name_lookup); the legacy ``id`` provenance
    # ("camera_jurisdiction"/"unreported") is preserved under ``id_basis``.
    if placed:
        declared = (
            {"scheme": str(row["declared_scheme"]), "value": str(row["declared_value"])}
            if row.get("declared_scheme")
            else None
        )
        jurisdiction.update(
            {
                "id_basis": jurisdiction["basis"],
                "jkey": row.get("jurisdiction_key"),
                "chain": list(row.get("jurisdiction_chain") or []),
                "basis": row.get("placement_basis"),
                "check": row.get("placement_check"),
                "declared": declared,
                "boundary_vintage": row.get("boundary_vintage"),
                # P35.45 (K4 §5.2): the dossier slug path of the record's
                # placed leaf key — the ``jurisdiction/<slug-path>/`` record
                # list it files under; chain-less records carry the honest
                # ``unplaced`` data-quality segment, never a guessed place.
                "slug_path": (
                    (jurisdiction_slug_paths or {}).get(str(row["jurisdiction_key"]))
                    if row.get("jurisdiction_key")
                    else "unplaced"
                ),
            }
        )

    # P35.15a / PKG-07: the declared SKOS technology slug — basis stays honest:
    # a row never presents an unreported or CONFLICTED declaration as a class.
    technology_id = row.get("technology")
    technology = {
        "id": str(technology_id) if technology_id else None,
        "basis": (
            "declared_technology_claim"
            if technology_id
            else (
                "conflicted"
                if str(row.get("technology_status") or "") == "conflicted"
                else "unreported"
            )
        ),
    }

    claim_index = claim_index or {}
    anchors: list[ClaimAnchor] = []
    evidence: list[EvidenceRef] = []
    statements: list[dict[str, Any]] = []
    for cid in row.get("claim_ids") or []:
        cid_s = str(cid)
        crow = claim_index.get(cid_s)
        if crow is None:
            anchors.append(ClaimAnchor(claim_id=cid_s, locator="unlocated"))
            continue
        anchors.append(
            ClaimAnchor(
                claim_id=cid_s,
                predicate_id=(str(crow["predicate_id"]) if crow.get("predicate_id") else None),
                observed_at=(str(crow["observed_at"]) if crow.get("observed_at") else None),
                source_id=str(crow["source_id"]) if crow.get("source_id") else None,
                locator="recorded",
                # P34.34a: the access-edge type rides in from record_claims
                # (the reconciler's recorded kind wins there; never derived
                # again here).
                access_kind=(str(crow["access_kind"]) if crow.get("access_kind") else None),
            )
        )
        # P35.36: the sig.statement/1 row rides the record — the one contract
        # the provenance panel renders from (UXR-33). A pre-P35.36 claim-index
        # row (no ``schema``) embeds nothing — honest absence.
        if crow.get("schema") == STATEMENT_SCHEMA:
            statements.append(dict(crow))
        for ev in crow.get("evidence") or []:
            evidence.append(
                EvidenceRef(
                    claim_id=cid_s,
                    capture_id=str(ev["capture_id"]) if ev.get("capture_id") else None,
                    artifact_id=(str(ev["artifact_id"]) if ev.get("artifact_id") else None),
                    role=str(ev["role"]) if ev.get("role") else None,
                    access="metadata_only",
                    binding_status=(
                        str(ev["binding_status"]) if ev.get("binding_status") else None
                    ),
                )
            )

    # P35.36 (J1 NEW-10): ``upstream_href`` through the P35.31 S-6 gate. The
    # statement rows already carry the scrubbed upstream block — the first
    # claim statement naming this record's source supplies it (claims order
    # deterministically by the site row's claim_ids). A release built from a
    # pre-P35.36 export — or a claim whose upstream was never recorded —
    # carries the named absence ``no_upstream_url_recorded``, never a dropped
    # field and never a raw URL.
    source_id_text = str(row.get("source_id") or rights.get("source_id") or "")
    upstream_href: str | None = NO_UPSTREAM_URL
    upstream_host: str | None = None
    upstream_status = NO_UPSTREAM_URL
    for cid in row.get("claim_ids") or []:
        crow = claim_index.get(str(cid))
        if (
            crow is None
            or crow.get("schema") != STATEMENT_SCHEMA
            or str(crow.get("source_id") or "") != source_id_text
        ):
            continue
        up = crow.get("upstream") or {}
        upstream_status = str(up.get("status") or NO_UPSTREAM_URL)
        upstream_host = up.get("host") or None
        if upstream_status == "full_url":
            upstream_href = up.get("url") or None
        elif upstream_status == "host_only":
            upstream_href = (
                f"{up.get('host')}#path_sha256:{up.get('path_sha256')}"
                if up.get("host")
                else NO_UPSTREAM_URL
            )
        elif upstream_status == "withheld_by_policy":
            upstream_href = "not_publishable"
        else:
            upstream_href = NO_UPSTREAM_URL
        break
    source_refs = (
        {
            "source_id": source_id_text,
            "attribution": str(rights.get("attribution") or ""),
            "terms_url": rights.get("terms_url"),
            "upstream_href": upstream_href,
            "upstream_host": upstream_host,
            "upstream_status": upstream_status,
        },
    )
    coverage = {
        "kind": "site_record",
        "observation_claims": int(row.get("n_observation_claims") or 0),
        "source_count": int(row.get("n_sources") or 0),
        "sensitivity_tier": int(row.get("tier") or 0),
        "note": "Recorded observations from named sources — an inventory, "
        "not a census or an estimate (SIG-METRIC-008).",
    }
    review = {
        "status": "published",
        "resolution_eval": "provisional",
        "note": "Resolved-site counts rest on a provisional evaluation "
        "pending the preregistered human study (D-R6.1-EVAL).",
    }
    return PublishedRecord(
        record_key=record_key(compartment, entity_type, entity_id),
        entity_id=entity_id,
        entity_type=entity_type,
        compartment=compartment,
        license=str(row.get("spdx") or license_id),
        label=label,
        technology=technology,
        jurisdiction=jurisdiction,
        location=location,
        claim_anchors=tuple(anchors),
        evidence_refs=tuple(evidence),
        source_refs=source_refs,
        claim_statements=tuple(statements),
        coverage=coverage,
        review=review,
    )


def claim_index_from_jsonl(rows: Any) -> dict[str, dict[str, Any]]:
    """Index ``<comp>/record_claims.jsonl`` rows by claim_id (last wins — rows
    are unique by construction; duplicate ids are a defect the validator
    catches as an index mismatch, not a silent merge)."""
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        out[str(row["claim_id"])] = dict(row)
    return out


def record_digest(record: PublishedRecord) -> str:
    """The per-record content digest over the ID-free document."""
    return sha256_hex(canonical_json(record.id_free_doc()))


def projection_root(digests: list[str]) -> str:
    """The compartment projection root: sha256 over the sorted per-record
    digests — order-independent, so a re-emitted compartment with identical
    content roots identically."""
    return sha256_hex(("\n".join(sorted(digests)) + "\n").encode("utf-8"))
