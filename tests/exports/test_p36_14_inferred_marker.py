# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.14 / SIG-RECON-052 (§30.4) — the cross-surface L4 inference marker.

One fixture inference — a materialized ``accountability_link:*``
(``inference.derived_fact``) row — is run through every surface and must be
marked on each, or the test fails:

* **export bytes** — ``web/dossiers.json`` section rows and the
  ``governance_chain`` link entries carry the typed pair ``inferred: true`` +
  ``layer: "L4"`` (emitted by ``inference.marking.mark_inferred``);
* **API payloads** — the same marked rows arrive verbatim through
  ``/v1/dossier`` and every fact/assertion response model carries the typed
  ``inferred``/``layer`` fields (``false``/``null`` on observed records);
* **the frozen web contract** — the marked row validates against the
  ``public_surface_contracts.schema.json`` ``Row`` definition the renderer
  consumes; the rendered-HTML leg (``sig-inferred`` + glyph + label, JS and
  no-JS) is asserted by ``web/tests/e2e/inferred-marker{,.nojs}.spec.ts``.

Removing the marker fails the test: an emitted record stripped of the pair no
longer satisfies :func:`inference.marking.is_inferred_record`, and every leg
below asserts the marker's presence directly — an unmarked emission is a red
build, never a quiet pass (SIG-ENG-042).
"""

from __future__ import annotations

import json

import jsonschema
import pytest
from api.demo import build_demo_store
from api.store import DossierRecord
from exports.dedup import DedupView
from exports.published_record import PublishedRecord, record_from_site_row
from inference.marking import INFERRED_LAYER, is_inferred_record, mark_inferred
from reconcile.model import Inference
from starlette.testclient import TestClient
from support import REPO_ROOT
from test_spine_export import _acct_link, _build, _materialized_raw, _site

from api import create_app

SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "build" / "reports" / "public_surface_contracts.schema.json").read_text(
        encoding="utf-8"
    )
)
_DEFS = SCHEMA["$defs"]
ROW_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": _DEFS,
    "$ref": "#/$defs/Row",
}


def _fixture_export():
    """The fixture inferred claim: one L4 accountability link over a geolocated
    deployment, exported through the real ``build_spine_export`` path."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    links = [
        _acct_link("A", "has_vendor", "ven1", "organization", ["c-op", "c-buy"], via_org="org1")
    ]
    return _build(claims, _materialized_raw(accountability_links=links))


def _web(export, name: str):
    return json.loads(export.web_artifacts[f"web/{name}.json"].decode("utf-8"))


def _all_rows(dossier: dict) -> list[dict]:
    return [row for s in dossier["sections"] for row in s.get("rows", ())]


def _marked(rows) -> list[dict]:
    return [r for r in rows if is_inferred_record(r)]


# --------------------------------------------------------------------------- #
# The marker contract itself                                                  #
# --------------------------------------------------------------------------- #


def test_marker_contract() -> None:
    """``inference.marking`` is the single contract; ``layer`` mirrors the L4
    ``Inference`` record's pinned layer value."""
    assert (
        INFERRED_LAYER
        == "L4"
        == Inference(
            subject_id="s",
            predicate_id="p",
            value=None,
            derivation_rule="r",
            rule_version="1",
            input_claim_ids=("c",),
        ).layer
    )
    assert mark_inferred({"k": 1}) == {"k": 1, "inferred": True, "layer": "L4"}
    # A half-marker is unmarked — the pair is coherent or absent.
    assert not is_inferred_record({"inferred": True})
    assert not is_inferred_record({"layer": "L4"})
    assert not is_inferred_record({"inferred": False, "layer": "L4"})
    assert not is_inferred_record({})
    assert not is_inferred_record(None)


# --------------------------------------------------------------------------- #
# Export bytes                                                                #
# --------------------------------------------------------------------------- #


def test_export_bytes_carry_the_typed_marker() -> None:
    export = _fixture_export()
    dossier = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Oklahoma")

    # The section row is marked — typed fields, not only prose.
    rows = _marked(_all_rows(dossier))
    assert rows, "the governance-chain row must carry the L4 marker in export bytes"
    row = rows[0]
    assert row["inferred"] is True and row["layer"] == "L4"
    # The marker survives the frozen Row contract the web surface renders from.
    jsonschema.validate(row, ROW_SCHEMA)

    # The structured chain links are marked too.
    links = dossier["governance_chain"]["segments"]["vendor"]["links"]
    assert links and all(is_inferred_record(link) for link in links)

    # …and the marker is present in the emitted bytes, not reconstructed later.
    raw = export.web_artifacts["web/dossiers.json"].decode("utf-8")
    assert '"inferred":true' in raw.replace(" ", "") or '"inferred": true' in raw
    assert '"layer":"L4"' in raw.replace(" ", "") or '"layer": "L4"' in raw


def test_unmarked_surface_rows_are_never_inferences() -> None:
    """No observed/resolved row in the export silently carries the marker —
    and an unmarked governance row would fail ``is_inferred_record`` (the
    removal leg: strip the pair and the record is unmarked)."""
    export = _fixture_export()
    dossier = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Oklahoma")
    rows = _all_rows(dossier)
    marked = _marked(rows)
    others = [r for r in rows if not is_inferred_record(r)]
    assert len(marked) == 1
    assert all(r.get("inferred") is not True for r in others)

    stripped = {k: v for k, v in marked[0].items() if k not in ("inferred", "layer")}
    assert not is_inferred_record(stripped)


def test_dedup_inferential_entries_are_marked() -> None:
    """The SIG-CONF-005 inferential family — ``possible_duplicates`` and the
    derived ``multi_view`` classification — carries the same marker."""
    view = DedupView(
        run_key="camsite:test",
        declared_distance_m=25.0,
        member_site={"rec-a": "site-a", "rec-b": "site-b"},
        site_members={"site-a": ("rec-a",), "site-b": ("rec-b",)},
        member_source={"rec-a": "src_a", "rec-b": "src_b"},
        preferred={"site-a": "rec-a", "site-b": "rec-b"},
        copies={},
        possible={
            "site-a": (
                {
                    "record": "rec-b",
                    "site_id": "site-b",
                    "source": "src_b",
                    "source_name": "Source B",
                    "distance_m": 12.0,
                    "reason": "within declared distance",
                    "display": "Possible duplicate: …",
                },
            )
        },
        multi_view={
            "site-a": (
                {
                    "record": "rec-c",
                    "site_id": "site-c",
                    "distance_m": 9.0,
                    "display": "Multi-view: …",
                },
            )
        },
        n_lineages={"site-a": 1, "site-b": 1},
        lineage_names={"site-a": ("src_a",), "site-b": ("src_b",)},
    )
    fields = view.record_fields("rec-a")
    assert all(is_inferred_record(e) for e in fields["possible_duplicates"])
    assert all(is_inferred_record(e) for e in fields["multi_view"])


def test_published_record_carries_the_marker_field() -> None:
    """Every released ``sig.published-record`` carries the typed pair — the
    observed state is ``inferred: false, layer: null`` (structurally
    distinguishable, never absent-by-convention); an L4 record carries
    ``true``/``"L4"``; a half-marker cannot be constructed."""
    row = {
        "entity_id": "e-1",
        "entity_type": "deployment",
        "jurisdiction": "Oklahoma",
        "claim_ids": [],
        "_rights": {"source_id": "src_a"},
    }
    rec = record_from_site_row(row, compartment="c", license_id="L")
    doc = json.loads(rec.bind("p-" + "0" * 64).json_bytes())
    assert doc["inferred"] is False and doc["layer"] is None

    inferred_rec = PublishedRecord(
        record_key="c:deployment:e-1",
        entity_id="e-1",
        entity_type="deployment",
        compartment="c",
        license="L",
        label={"text": None, "basis": "unlabelled"},
        technology={"id": None, "basis": "unreported"},
        jurisdiction={"id": None, "basis": "unreported"},
        location={"kind": "unreported"},
        inferred=True,
        layer="L4",
    )
    doc = json.loads(inferred_rec.bind("p-" + "0" * 64).json_bytes())
    assert is_inferred_record(doc)

    with pytest.raises(ValueError, match="marker is coherent or absent"):
        PublishedRecord(
            record_key="c:deployment:e-1",
            entity_id="e-1",
            entity_type="deployment",
            compartment="c",
            license="L",
            label={"text": None, "basis": "unlabelled"},
            technology={"id": None, "basis": "unreported"},
            jurisdiction={"id": None, "basis": "unreported"},
            location={"kind": "unreported"},
            inferred=True,  # no layer → a broken marker, refused
        )


# --------------------------------------------------------------------------- #
# API payloads                                                                #
# --------------------------------------------------------------------------- #


def _api_client_with_marked_dossier(export) -> TestClient:
    store = build_demo_store()
    dossier = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Oklahoma")
    store.add_dossier(
        DossierRecord(
            scope="jurisdiction:fixture-okc",
            title=dossier["subject_label"],
            sections=tuple(dossier["sections"]),
            source_ids=("src:portal", "src:records"),
        )
    )
    return TestClient(create_app(store))


def test_api_dossier_payload_carries_the_marker() -> None:
    client = _api_client_with_marked_dossier(_fixture_export())
    body = client.get("/v1/dossier/jurisdiction:fixture-okc").json()
    rows = [row for s in body["sections"] for row in s.get("rows", ())]
    marked = [r for r in rows if r.get("inferred") is True]
    assert marked, "the served dossier must carry the typed L4 marker"
    assert all(r.get("layer") == "L4" for r in marked)
    assert all(is_inferred_record(r) for r in marked)


def test_api_fact_and_claim_records_carry_the_typed_field() -> None:
    """The marker pair is a typed field on every fact/assertion model —
    ``inferred: false, layer: null`` declares the record is NOT an L4
    inference (observed and inferred answers are structurally distinct)."""
    client = TestClient(create_app(build_demo_store()))
    claim = client.get("/v1/claim/portal").json()
    assert claim["inferred"] is False and claim["layer"] is None
    res = client.get("/v1/resolution/agency:okcpd/active_device_count").json()
    env = res["fact"]["envelope"]
    assert env["inferred"] is False and env["layer"] is None


def test_api_marker_pair_is_coherent_or_refused() -> None:
    """The wire model refuses a broken marker — ``inferred`` without
    ``layer: "L4"`` (or the reverse) cannot be constructed."""
    from api.models import ResolutionEnvelope

    with pytest.raises(Exception, match="coherent or absent"):
        ResolutionEnvelope(
            value=1,
            resolution_status="RESOLVED",
            support="CONFIRMED",
            agreement="UNCONTESTED",
            currency="CURRENT",
            rationale={"code": "x", "text": "x"},
            supporting_claim_ids=[],
            dissenting_claim_ids=[],
            as_of_world="2026-09-01",
            as_of_belief="2026-09-01",
            ruleset_version="r/1",
            inferred=True,  # layer missing → refused
        )
