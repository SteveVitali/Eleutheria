# SPDX-License-Identifier: Apache-2.0
"""P35.29 — the shared ``sig.entity-label/1`` registry through the export.

Fixture-level, never living records: entity rows, dispositions and label
facts are fabricated ``raw`` rows (the same tuple shape ``fetch_export_raw``
produces inside the read snapshot). The DB-backed seeded-spine e2e exercises
the SQL seam itself.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import (
    _label_artifacts,
    _label_registry,
    build_spine_export,
)


def _eid() -> str:
    return str(uuid.uuid4())


def _claim(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    spdx: str = "CC-BY-4.0",
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=0,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id=f"rights-{spdx}",
        effective_spdx=spdx,
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://example/terms",
    )


def _site(subject: str, juris: str = "Oklahoma", **over) -> list[ShapingClaim]:
    return [
        _claim(f"{subject}-lat", subject, "camera_latitude", value_text="35.46", **over),
        _claim(f"{subject}-lon", subject, "camera_longitude", value_text="-97.51", **over),
        _claim(f"{subject}-jur", subject, "camera_jurisdiction", value_text=juris, **over),
    ]


def _rows(claims: list[ShapingClaim]) -> list[tuple]:
    return [
        (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]


def _dataset_and_export(claims: list[ShapingClaim], raw_over: dict):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    base_raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        base_raw,
        as_of="2026-09-22",
        generated_at="2026-09-22T00:00:00Z",
        spine_label="unit",
    )
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    export = build_spine_export(
        dataset,
        raw_over,
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )
    return dataset, export


def _ent(
    eid: str,
    etype: str,
    skey: str | None,
    cname: str | None,
    req: bool = False,
    status: str | None = None,
    merged: str | None = None,
) -> tuple:
    """``(entity_id, type, subject_key, merged_into, canonical, review_req, status)``."""
    return (eid, etype, skey, merged, cname, req, status)


def _raw_for(**kw) -> dict:
    return {
        "label_entities": kw.get("entities", []),
        "label_entity_dispositions": kw.get("dispositions", []),
        "label_facts": kw.get("facts", []),
        "entity_labels": kw.get("identifiers", []),
    }


def _fact(
    sid: str,
    pred: str,
    val: str,
    *,
    source_id: str = "src_a",
    spdx: str = "CC-BY-4.0",
    rid: str = "rights-a",
) -> tuple:
    return (
        sid,
        pred,
        val,
        source_id,
        spdx,
        f"© {source_id}",
        "yes",
        "yes",
        "https://example/terms",
        rid,
    )


# ---------------------------------------------------------------------------
# Registry derivation over the export snapshot
# ---------------------------------------------------------------------------


def test_registry_labels_each_kind_and_carries_basis():
    site_eid = _eid()
    org_eid = _eid()
    claims = _site(site_eid)
    raw = _raw_for(
        entities=[
            _ent(site_eid, "deployment", f"cam:{site_eid}", None),
            _ent(
                org_eid,
                "organisation",
                "organization:acme",
                "Acme Surveillance LLC",
                status="active",
            ),
        ],
        facts=[_fact(site_eid, "camera_name", "I-44 @ Riverside")],
        identifiers=[(site_eid, "sig.connector.subject", f"cam:{site_eid}")],
    )
    dataset, export = _dataset_and_export(claims, raw)
    registry, comps = _label_registry(raw, dataset, retrieval=date(2026, 9, 22), registry=None)
    org = registry[org_eid]
    assert org.label == "Acme Surveillance LLC"
    assert org.label_basis == "source_name"
    assert org.slug and org.hash and org.url
    site = registry[site_eid]
    assert site.label is not None
    assert site.label_basis in ("source_name", "derived")
    assert site.label != site_eid
    assert site_eid not in (site.label or "")


def test_unmatched_org_emits_typed_not_yet_reviewed_row():
    org_eid = _eid()
    raw = _raw_for(
        entities=[
            _ent(
                org_eid,
                "organisation",
                "organization:unrev",
                "Unreviewed Vendor Corp",
                req=True,
                status="active",
            ),
        ],
    )
    registry, comps = _label_registry(
        raw, _empty_dataset(), retrieval=date(2026, 9, 22), registry=None
    )
    row = _label_artifacts(registry, comps, default_compartment="sig")
    all_rows = [r for rows in row.values() for r in rows]
    assert len(all_rows) == 1
    assert all_rows[0]["label_state"] == "not_yet_reviewed"
    assert all_rows[0]["label"] is None
    assert all_rows[0]["slug"] is None and all_rows[0]["hash"] is None
    assert "Unreviewed Vendor Corp" not in (all_rows[0]["descriptor"] or "")


def test_withheld_and_person_entities_emit_no_rows():
    denied = _eid()
    person = _eid()
    merged = _eid()
    raw = _raw_for(
        entities=[
            _ent(denied, "organisation", "organization:blocked", "Blocked Corp", status="active"),
            _ent(person, "person", "person:x", "Any Name"),
            _ent(
                merged,
                "organisation",
                "organization:merged",
                "Merged Corp",
                status="active",
                merged=_eid(),
            ),
        ],
        dispositions=[(denied, "withhold")],
    )
    registry, comps = _label_registry(
        raw, _empty_dataset(), retrieval=date(2026, 9, 22), registry=None
    )
    rows = _label_artifacts(registry, comps, default_compartment="sig")
    assert all(rows.get(c) in (None, []) for c in rows)  # zero rows anywhere
    flat = [r for rs in rows.values() for r in rs]
    assert not flat


def _empty_dataset():
    raw = {
        "shaping_claims": [],
        "subject_entities": [],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=0",
    }
    return build_shaped_dataset(
        raw,
        as_of="2026-09-22",
        generated_at="2026-09-22T00:00:00Z",
        spine_label="unit",
    )


def test_labels_jsonl_emitted_per_compartment():
    site_eid = _eid()
    org_eid = _eid()
    claims = _site(site_eid)
    raw = _raw_for(
        entities=[
            _ent(site_eid, "deployment", f"cam:{site_eid}", None),
            _ent(
                org_eid,
                "organisation",
                "organization:acme",
                "Acme Surveillance LLC",
                status="active",
            ),
        ],
        facts=[_fact(site_eid, "camera_name", "I-44 @ Riverside")],
    )
    _dataset, export = _dataset_and_export(claims, raw)
    label_paths = [p for p in export.web_artifacts if p.startswith("labels/")]
    assert label_paths, "labels/<comp>.jsonl artifacts must be emitted"
    rows = []
    for p in label_paths:
        for line in export.web_artifacts[p].decode("utf-8").splitlines():
            rows.append(json.loads(line))
    by_eid = {r["entity_id"]: r for r in rows}
    assert org_eid in by_eid and site_eid in by_eid
    org = by_eid[org_eid]
    assert org["label"] == "Acme Surveillance LLC"
    assert org["kind"] == "org" and org["url_type"] == "org"
    assert org["url"].startswith("/entity/org/") and org["url"].endswith("/")
    assert org["label_basis"] == "source_name"
    assert org["part8"] in ("pass", "fallback")
    # schema fields present
    for key in (
        "entity_id",
        "sig_id",
        "kind",
        "url_type",
        "descriptor",
        "label_source_id",
        "place_jkey",
        "slug",
        "hash",
        "disambiguator",
        "component_id",
    ):
        assert key in org


def test_label_bytes_are_deterministic():
    site_eid = _eid()
    org_eid = _eid()
    claims = _site(site_eid)
    raw = _raw_for(
        entities=[
            _ent(site_eid, "deployment", f"cam:{site_eid}", None),
            _ent(
                org_eid,
                "organisation",
                "organization:acme",
                "Acme Surveillance LLC",
                status="active",
            ),
        ],
        facts=[_fact(site_eid, "camera_name", "Riverside array")],
    )
    _, exp1 = _dataset_and_export(claims, raw)
    _, exp2 = _dataset_and_export(claims, raw)
    paths = sorted(p for p in exp1.web_artifacts if p.startswith("labels/"))
    for p in paths:
        assert exp1.web_artifacts[p] == exp2.web_artifacts[p]


def test_no_emitted_label_is_an_identifier():
    site_eid = _eid()
    claims = _site(site_eid)
    raw = _raw_for(
        entities=[_ent(site_eid, "deployment", f"cam:{site_eid}", None)],
        identifiers=[(site_eid, "sourceid", "SRC-9981")],
    )
    _, export = _dataset_and_export(claims, raw)
    map_json = json.loads(export.web_artifacts["web/map.json"].decode("utf-8"))
    for asset in map_json["assets"]:
        assert asset["label"] != asset["id"]
        assert "SRC-9981" not in asset["label"]
