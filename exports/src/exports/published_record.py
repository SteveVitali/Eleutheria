# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.published-record/1`` UI projection (P32.13 / ADR-132, SIG-FIND-002).

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

from .manifest import canonical_json, sha256_hex

#: The projection schema/version stamped on every record and hashed into the
#: publication descriptor — a renderer/projection change is a NEW namespace.
PROJECTION_VERSION = "sig.published-record/1"


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

    def as_json(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "capture_id": self.capture_id,
            "artifact_id": self.artifact_id,
            "role": self.role,
            "access": self.access,
        }


@dataclass(frozen=True)
class PublishedRecord:
    """The ``sig.published-record/1`` document — one released public record."""

    record_key: str
    entity_id: str
    entity_type: str
    compartment: str
    license: str
    label: dict[str, Any]  # {"text": str|None, "basis": str}
    jurisdiction: dict[str, Any]  # {"id": str|None, "basis": str}
    location: dict[str, Any]  # {"kind", "lat"?, "lon"?, "precision"?}
    claim_anchors: tuple[ClaimAnchor, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    source_refs: tuple[dict[str, Any], ...] = ()
    coverage: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    #: Bound AFTER the namespace is computed — excluded from the ID-free doc.
    publication_id: str | None = None
    href: str | None = None
    json_href: str | None = None
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
            "jurisdiction": self.jurisdiction,
            "location": self.location,
            "claim_anchors": [a.as_json() for a in self.claim_anchors],
            "evidence_refs": [e.as_json() for e in self.evidence_refs],
            "source_refs": [dict(s) for s in self.source_refs],
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
        return doc

    def json_bytes(self) -> bytes:
        return canonical_json(self.as_json())

    def bind(self, publication_id: str) -> PublishedRecord:
        """Bind the namespace: fill ``publication_id``/``href``/``json_href``."""
        base = (
            f"/r/{publication_id}/c/{self.compartment}/entity/{self.entity_type}/{self.entity_id}"
        )
        return replace(
            self,
            publication_id=publication_id,
            href=f"{base}/",
            json_href=f"{base}.json",
        )


def record_from_site_row(
    row: Mapping[str, Any],
    *,
    compartment: str,
    license_id: str,
    claim_index: Mapping[str, Mapping[str, Any]] | None = None,
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
    rights = dict(row.get("_rights") or {})
    geometry = row.get("geometry")
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    point_status = str(row.get("point_status") or "")
    if coords and point_status == "resolved":
        location: dict[str, Any] = {
            "kind": "point",
            "lat": coords[1],
            "lon": coords[0],
            "precision": str(row.get("precision") or "unreported"),
        }
    elif coords:
        location = {"kind": "unresolved_point", "precision": point_status or "unreported"}
    else:
        location = {"kind": "unreported"}

    label_text = row.get("label")
    label = {
        "text": str(label_text) if label_text else None,
        "basis": "source_label" if label_text else "unlabelled",
    }
    jurisdiction_id = row.get("jurisdiction")
    jurisdiction = {
        "id": str(jurisdiction_id) if jurisdiction_id else None,
        "basis": "camera_jurisdiction" if jurisdiction_id else "unreported",
    }

    claim_index = claim_index or {}
    anchors: list[ClaimAnchor] = []
    evidence: list[EvidenceRef] = []
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
        for ev in crow.get("evidence") or []:
            evidence.append(
                EvidenceRef(
                    claim_id=cid_s,
                    capture_id=str(ev["capture_id"]) if ev.get("capture_id") else None,
                    artifact_id=(str(ev["artifact_id"]) if ev.get("artifact_id") else None),
                    role=str(ev["role"]) if ev.get("role") else None,
                    access="metadata_only",
                )
            )

    source_refs = (
        {
            "source_id": str(row.get("source_id") or rights.get("source_id") or ""),
            "attribution": str(rights.get("attribution") or ""),
            "terms_url": rights.get("terms_url"),
            "upstream_href": None,
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
        jurisdiction=jurisdiction,
        location=location,
        claim_anchors=tuple(anchors),
        evidence_refs=tuple(evidence),
        source_refs=source_refs,
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
