# SPDX-License-Identifier: Apache-2.0
"""P36.29 — the ``sig.slug-history/1`` entity URL-key history through the export.

Fixture-level, never living records: entity rows, dispositions and label
facts are fabricated ``raw`` rows (the same tuple shape ``fetch_export_raw``
produces inside the read snapshot) — the same harness
``test_entity_labels.py`` drives.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import build_spine_export
from policy.labels import entity_hash, name_slug

HISTORY_PATH = "web/entity_slug_history.json"


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


def _export(claims: list[ShapingClaim], raw_over: dict, **kw):
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
    return build_spine_export(
        dataset,
        raw_over,
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
        **kw,
    )


def _history_doc(export) -> dict:
    return json.loads(export.web_artifacts[HISTORY_PATH].decode("utf-8"))


# ---------------------------------------------------------------------------
# The emitted artifact
# ---------------------------------------------------------------------------


def test_artifact_emitted_with_schema_and_current_rows():
    org = _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(org, "organisation", f"organization:{org}", "Acme Surveillance LLC"),
        ],
    )
    export = _export(claims, raw)
    assert HISTORY_PATH in export.web_artifacts
    doc = _history_doc(export)
    assert doc["schema"] == "sig.slug-history/1"
    assert doc["publication"] == export.bundle.build_spec.release_id()
    rows = [r for r in doc["rows"] if r["uuid"] == org]
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "current"
    assert row["hash"] == entity_hash(org)
    assert row["slug"] == name_slug("Acme Surveillance LLC")
    assert row["url_type"] == "org"
    assert row["from_pub"] == doc["publication"]
    assert row["to_pub"] is None


def test_person_entities_emit_no_history_row():
    person = _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(person, "person", f"person:{person}", "Pat Example"),
        ],
    )
    doc = _history_doc(_export(claims, raw))
    assert [r for r in doc["rows"] if r["uuid"] == person] == []
    assert not any(r["url_type"] == "person" for r in doc["rows"])


def test_unlabelled_entity_emits_no_key():
    org = _eid()
    claims = _site(_eid())
    # Withheld by disposition — the registry emits no label, so no key.
    raw = _raw_for(
        entities=[_ent(org, "organisation", f"organization:{org}", None)],
        dispositions=[(org, "withhold")],
    )
    doc = _history_doc(_export(claims, raw))
    assert [r for r in doc["rows"] if r["uuid"] == org] == []


def test_merged_entity_tombstones_to_survivor():
    survivor, gone = _eid(), _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(
                survivor,
                "organisation",
                f"organization:{survivor}",
                "Surviving Org LLC",
            ),
            _ent(
                gone,
                "organisation",
                f"organization:{gone}",
                None,
                merged=survivor,
            ),
        ],
    )
    doc = _history_doc(_export(claims, raw))
    merged = [r for r in doc["rows"] if r["uuid"] == gone]
    assert len(merged) == 1
    assert merged[0]["status"] == "merged"
    assert merged[0]["slug"] is None  # never fabricated
    assert merged[0]["hash"] == entity_hash(gone)
    surv_slug = name_slug("Surviving Org LLC")
    assert merged[0]["target"] == f"/entity/org/{surv_slug}--{entity_hash(survivor)}/"


def test_prior_history_carries_verbatim_and_appends_transitions():
    org = _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(org, "organisation", f"organization:{org}", "Renamed Org LLC"),
        ],
    )
    prior_rows = [
        {
            "hash": entity_hash(org),
            "uuid": org,
            "url_type": "org",
            "slug": "old-org-name",
            "status": "current",
            "target": None,
            "from_pub": "sig-release-2026.08",
            "to_pub": None,
        },
        {
            "hash": entity_hash(_eid()),
            "uuid": str(uuid.uuid4()),
            "url_type": "org",
            "slug": "untouched-org",
            "status": "current",
            "target": None,
            "from_pub": "sig-release-2026.08",
            "to_pub": None,
        },
    ]
    doc = _history_doc(_export(claims, raw, previous_entity_history=prior_rows))
    rows = doc["rows"]
    # The untouched prior row reappears verbatim (append-only) — including
    # the retired `current` row, which stays `status: current` forever; the
    # appended `renamed` row is what retires the key.
    assert prior_rows[1] in rows
    assert prior_rows[0] in rows
    renamed = [r for r in rows if r["uuid"] == org and r["status"] == "renamed"]
    live = [
        r
        for r in rows
        if r["uuid"] == org and r["status"] == "current" and r["from_pub"] == doc["publication"]
    ]
    assert len(renamed) == 1 and len(live) == 1
    assert renamed[0]["slug"] == "old-org-name"
    assert renamed[0]["hash"] == live[0]["hash"] == entity_hash(org)
    assert renamed[0]["target"].endswith(f"--{entity_hash(org)}/")
    assert renamed[0]["to_pub"] == doc["publication"]
    assert live[0]["slug"] == name_slug("Renamed Org LLC")


def test_stable_entity_keeps_single_current_row_across_releases():
    org = _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(org, "organisation", f"organization:{org}", "Stable Org LLC"),
        ],
    )
    first = _history_doc(_export(claims, raw))
    second = _history_doc(_export(claims, raw, previous_entity_history=first["rows"]))
    assert second["rows"] == first["rows"]  # additive-only: nothing churns


def test_sig_ui_111_same_name_entities_emit_distinct_keys():
    """SIG-UI-111 holds on the EMITTED rows: two same-named orgs are
    disambiguated (label + slug differ), and the fail-closed
    ``check_unique_labels`` backstop in the emit path never lets a
    duplicate through."""
    a, b = _eid(), _eid()
    claims = _site(_eid())
    raw = _raw_for(
        entities=[
            _ent(a, "organisation", f"organization:{a}", "Duplicate Name LLC"),
            _ent(b, "organisation", f"organization:{b}", "Duplicate Name LLC"),
        ],
    )
    doc = _history_doc(_export(claims, raw))
    rows = {r["uuid"]: r for r in doc["rows"] if r["uuid"] in {a, b}}
    assert set(rows) == {a, b}
    assert rows[a]["slug"] != rows[b]["slug"]
    assert rows[a]["hash"] != rows[b]["hash"]


def test_sig_ui_111_unresolved_duplicate_refuses_export():
    """The backstop itself: a registry that still carries a duplicate full
    label after disambiguation refuses the export — never ships it."""
    from policy.slug_history import check_unique_labels

    labels = {eid: _label_row(eid, "Same LLC") for eid in (_eid(), _eid())}
    with pytest.raises(ValueError, match="SIG-UI-111"):
        check_unique_labels(labels)


def _label_row(eid: str, name: str):
    from policy.labels import EntityLabel, entity_url

    slug = name_slug(name)
    h = entity_hash(eid)
    return EntityLabel(
        entity_id=eid,
        sig_id=None,
        kind="org",
        url_type="org",
        label=name,
        descriptor=None,
        label_basis="key_name",
        label_source_id=None,
        place_jkey=None,
        slug=slug,
        hash=h,
        url=entity_url("org", slug, h),
        disambiguator=None,
        component_id=None,
        part8="pass",
    )
