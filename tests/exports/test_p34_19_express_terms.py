# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.19 — export-level disclosure + F-337 suppression (F-403, F-337).

The export writer carries the ADR-183 disclosure forward: every compartment
holding an express-terms source's rows gains an ``ATTRIBUTION.json`` with
the captured terms verbatim + the operator-accepted basis, and
``web/terms_disclosure.json`` is emitted for P34.17's interim page. The
committed ``sig.publication-withdrawals/1`` list is applied before any
surface is built, so the nine F-337 rows reach no artifact and land loudly
in ``exclusions.json``.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import build_spine_export

from policy import withdrawals


def _claim(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    spdx: str = "ODbL-1.0",
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
        effective_rights_id=f"rights-{source_id}-{spdx}",
        effective_spdx=spdx,
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://example/terms",
    )


def _site(subject: str, *, source_id: str, spdx: str, prefix: str = "") -> list[ShapingClaim]:
    return [
        _claim(
            f"{prefix}{subject}-{source_id}-lat",
            subject,
            "camera_latitude",
            value_text="35.46",
            source_id=source_id,
            spdx=spdx,
        ),
        _claim(
            f"{prefix}{subject}-{source_id}-lon",
            subject,
            "camera_longitude",
            value_text="-97.51",
            source_id=source_id,
            spdx=spdx,
        ),
        _claim(
            f"{prefix}{subject}-{source_id}-jur",
            subject,
            "camera_jurisdiction",
            value_text="Oklahoma",
            source_id=source_id,
            spdx=spdx,
        ),
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


def _build(claims: list[ShapingClaim]):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    return build_spine_export(
        dataset,
        {},
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 9, 22),
            as_of_belief=date(2026, 9, 22),
            ruleset_version="ruleset/1",
            resolver_version="resolver/1",
        ),
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )


def _json(export, path: str):
    return json.loads(export.web_artifacts[path].decode("utf-8"))


#: A committed F-337 target (San Mateo AOS000953 — claim, entity, upstream).
F337_CLAIM = "01a0a6cb-b1e9-7552-b25c-aba32b812402"
F337_ENTITY = "01a0a6cb-b180-7a78-921d-dddeae9bfa96"
F337_UPSTREAM = "AOS000953"


def _affected_site(subject: str = "SITE-EXP") -> list[ShapingClaim]:
    return _site(
        subject, source_id="camreg_trpa_us", spdx="LicenseRef-PublicRecord-FactualCompilation"
    )


def _compartment_with(export, source_id: str) -> str:
    for path, payload in export.bundle.artifact_bytes.items():
        if path.endswith("/sites.csv") or path.endswith("/sites.jsonl"):
            if source_id in payload.decode("utf-8"):
                return path.rsplit("/", 1)[0]
    raise AssertionError(f"no compartment carries {source_id} rows")


# --- F-403: disclosure artifacts ------------------------------------------- #


def test_terms_disclosure_artifact_carries_terms_and_basis() -> None:
    export = _build(_affected_site())
    payload = _json(export, "web/terms_disclosure.json")
    assert payload["schema"] == "sig.terms-disclosure/1"
    assert payload["basis"]["adr"] == "docs/adr/ADR-183-express-terms-acceptance.md"
    entry = next(s for s in payload["sources"] if s["source_id"] == "camreg_trpa_us")
    assert entry["captured_terms_verbatim"] == "CC BY-NC"
    assert entry["publication_basis"] == "operator-accepted express terms (ADR-183)"
    # the export's own computed count — never the acceptance narrative's total
    assert entry["export_row_count"] == 1
    assert "SB-2" in entry["refresh_scope"]


def test_attribution_json_written_into_each_affected_compartment() -> None:
    export = _build(_affected_site())
    comp = _compartment_with(export, "camreg_trpa_us")
    attribution = _json(export, f"{comp}/ATTRIBUTION.json")
    # P34.21a generalised the file to every source in the compartment (schema /2);
    # the express-terms keys stay additive on the affected source.
    assert attribution["schema"] == "sig.compartment-attribution/2"
    assert attribution["compartment"] == comp
    assert attribution["license_url"]
    assert attribution["publication_basis"].startswith(
        "Published on the operator's own determination"
    )
    entry = next(s for s in attribution["sources"] if s["source_id"] == "camreg_trpa_us")
    assert entry["captured_terms_verbatim"] == "CC BY-NC"
    assert entry["publication_basis"] == "operator-accepted express terms (ADR-183)"
    assert entry["captured_terms_evidence"]
    assert entry["rows"] == 1
    # the artifact is manifest-registered with its compartment + licence
    paths = {a.path: a for a in export.manifest.artifacts}
    assert f"{comp}/ATTRIBUTION.json" in paths
    assert paths[f"{comp}/ATTRIBUTION.json"].compartment == comp


def test_unaffected_export_emits_no_terms_disclosure_but_names_every_source() -> None:
    export = _build(_site("PLAIN", source_id="src_plain", spdx="CC0-1.0"))
    names = set(export.web_artifacts)
    # P34.19: no express-terms source → no terms_disclosure.json (unchanged).
    assert "web/terms_disclosure.json" not in names
    # P34.21a: EVERY compartment still gets its ATTRIBUTION.json naming the
    # sources whose rows it carries — an unaffected source simply carries no
    # express-terms keys.
    comp = _compartment_with(export, "src_plain")
    attribution = _json(export, f"{comp}/ATTRIBUTION.json")
    assert attribution["schema"] == "sig.compartment-attribution/2"
    entry = next(s for s in attribution["sources"] if s["source_id"] == "src_plain")
    assert "captured_terms_verbatim" not in entry
    assert entry["attribution"] == "© src_plain"
    assert entry["rows"] == 1


def test_disclosure_covers_only_affected_sources_in_a_mixed_export() -> None:
    export = _build(_affected_site("MIX-A") + _site("MIX-B", source_id="src_plain", spdx="CC0-1.0"))
    payload = _json(export, "web/terms_disclosure.json")
    assert {s["source_id"] for s in payload["sources"]} == {"camreg_trpa_us"}
    comp_plain = _compartment_with(export, "src_plain")
    # P34.21a: the unaffected compartment's ATTRIBUTION.json names its source
    # but carries no express-terms keys — disclosure keys stay affected-only.
    if comp_plain != _compartment_with(export, "camreg_trpa_us"):
        plain = _json(export, f"{comp_plain}/ATTRIBUTION.json")
        entry = next(s for s in plain["sources"] if s["source_id"] == "src_plain")
        assert "captured_terms_verbatim" not in entry


# --- F-337: the nine leak-tainted rows leave every artifact ----------------- #


def _f337_site() -> list[ShapingClaim]:
    """A site whose claims carry the committed F-337 claim id."""
    return [
        _claim(
            F337_CLAIM,
            F337_ENTITY,
            "camera_latitude",
            value_text="37.56",
            source_id="eff_atlas_of_surveillance",
            spdx="CC-BY-4.0",
        ),
        _claim(
            f"{F337_ENTITY}-lon",
            F337_ENTITY,
            "camera_longitude",
            value_text="-122.32",
            source_id="eff_atlas_of_surveillance",
            spdx="CC-BY-4.0",
        ),
        _claim(
            f"{F337_ENTITY}-jur",
            F337_ENTITY,
            "camera_jurisdiction",
            value_text="California",
            source_id="eff_atlas_of_surveillance",
            spdx="CC-BY-4.0",
        ),
    ]


def _every_artifact_text(export) -> str:
    parts = [export.provenance.decode("utf-8")]
    parts += [b.decode("utf-8", errors="replace") for b in export.web_artifacts.values()]
    parts += [b.decode("utf-8", errors="replace") for b in export.bundle.artifact_bytes.values()]
    return "\n".join(parts)


def test_withdrawn_claim_leaves_every_public_artifact() -> None:
    export = _build(_f337_site() + _affected_site("KEEP"))
    body = _every_artifact_text(export)
    assert F337_CLAIM not in body
    assert F337_ENTITY not in body
    # map surface + dossiers never draw the entity
    assert all(a["id"] != F337_ENTITY for a in _json(export, "web/map.json")["assets"])
    assert all(F337_ENTITY not in json.dumps(d) for d in _json(export, "web/dossiers.json"))


def test_withdrawn_claims_are_recorded_loudly_in_exclusions() -> None:
    export = _build(_f337_site() + _affected_site("KEEP"))
    withdrawn = export.exclusions["withdrawn"]
    assert {w["claim_id"] for w in withdrawn} == {
        F337_CLAIM,
        f"{F337_ENTITY}-lon",
        f"{F337_ENTITY}-jur",
    }
    by_id = {w["claim_id"]: w for w in withdrawn}
    assert by_id[F337_CLAIM]["upstream_id"] == F337_UPSTREAM
    assert by_id[F337_CLAIM]["reason"] == "leak-provenance"
    assert "F-337" in by_id[F337_CLAIM]["authority"]
    # entity-matched claims are suppressed fail-closed under the same entry
    assert by_id[f"{F337_ENTITY}-lon"]["entity_id"] == F337_ENTITY
    assert export.exclusions["totals"]["withdrawn_claims"] == 3


def test_entity_sites_leave_dataset_derived_surfaces() -> None:
    """Every claim about a withdrawn ENTITY is suppressed fail-closed — the
    sites table, the map and the dossiers all drop it consistently."""
    export = _build(_f337_site() + _affected_site("KEEP"))
    assert all(a["id"] != F337_ENTITY for a in _json(export, "web/map.json")["assets"])
    for comp, payload in export.bundle.artifact_bytes.items():
        if comp.endswith("sites.csv") or comp.endswith("sites.jsonl"):
            assert F337_ENTITY not in payload.decode("utf-8")


def test_miami_candidate_claim_is_suppressed_fail_closed() -> None:
    candidate = "01a0a6cb-bca2-7111-b994-11c9b0fc129f"
    assert candidate in withdrawals.withdrawn_claim_ids()
    claims = [
        _claim(
            candidate,
            "01a0a6cb-bc2c-7d8f-9d8b-18e491cfce74",
            "camera_latitude",
            value_text="25.77",
            source_id="eff_atlas_of_surveillance",
            spdx="CC-BY-4.0",
        )
    ] + _affected_site("KEEP")
    export = _build(claims)
    assert _every_artifact_text(export).find(candidate) == -1
    assert any(w["claim_id"] == candidate for w in export.exclusions["withdrawn"])


def test_deterministic_output_for_identical_inputs() -> None:
    first = _build(_affected_site("DET"))
    second = _build(_affected_site("DET"))
    assert (
        first.web_artifacts["web/terms_disclosure.json"]
        == second.web_artifacts["web/terms_disclosure.json"]
    )


@pytest.mark.parametrize("name", ["map", "dossiers", "dossier_index"])
def test_no_f337_id_reaches_any_web_surface(name: str) -> None:
    export = _build(_f337_site() + _affected_site("KEEP"))
    text = export.web_artifacts[f"web/{name}.json"].decode("utf-8")
    for target in withdrawals.withdrawn_ids():
        assert target not in text
