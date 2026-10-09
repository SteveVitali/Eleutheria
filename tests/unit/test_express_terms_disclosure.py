# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.19 (F-403, ADR-183) — the express-terms disclosure record.

Every express-terms source the operator chose to keep public (**"Keep all,
accept risk"** / **"Keep everything as is"**, extended to scheduled refreshes
of the same sources by SB-2 **"Yes, same sources (Recommended)"**) carries its
captured terms verbatim and the basis ``operator-accepted express terms
(ADR-183)`` — as data in ``policy/data/express_terms.json``, mirrored into
each affected ``sources.toml`` rights block, and threaded onto every
downstream obligations record (SIG-LIC-001/004/011).
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pytest
from connectors.registry import _rights_from_row, sources
from policy.licensing import downstream_obligations
from policy.rights import RightsRecord

from policy import disclosure

REPO_ROOT = Path(__file__).resolve().parents[2]

SWEEP_PATH = REPO_ROOT / "docs" / "build" / "reports" / "catalog_sweep_2026-09-18_qualified.json"
SOURCES_TOML = REPO_ROOT / "connectors" / "src" / "connectors" / "data" / "sources.toml"
RELEASE_SITES = REPO_ROOT / "exports" / "out" / "national"

#: The J4 NEW-1 seven + camreg_txdot_rep_tx (the acceptance covered the three
#: live NC rows inside NEW-1 — Keizer, TRPA, Cal OES).
AFFECTED = {
    "camreg_caloes_ca",
    "camreg_cotgeo",
    "camreg_keizer_or",
    "camreg_ramallah_ps",
    "camreg_und_023",
    "camreg_trpa_us",
    "camreg_txdot_rep_tx",
    "camreg_ukm_my",
}


def _entries() -> dict[str, dict]:
    return {s["source_id"]: s for s in disclosure.express_terms()["sources"]}


def test_the_affected_list_is_exactly_the_eight_adr_183_sources() -> None:
    assert disclosure.affected_source_ids() == AFFECTED


def test_every_affected_source_carries_terms_verbatim_basis_and_evidence() -> None:
    for sid in sorted(AFFECTED):
        entry = _entries()[sid]
        assert entry["captured_terms_verbatim"].strip(), sid
        assert entry["publication_basis"] == "operator-accepted express terms (ADR-183)", sid
        assert entry["captured_terms_evidence"].strip(), sid
        assert entry["terms_url"].startswith("https://"), sid
        assert entry["spdx_registry"], sid
        assert "SB-2" in entry["refresh_scope"], sid


def test_row_counts_sum_to_the_recorded_8088_and_each_is_positive() -> None:
    entries = _entries()
    for sid, entry in entries.items():
        assert isinstance(entry["public_row_count"], int) and entry["public_row_count"] > 0, sid
    assert sum(e["public_row_count"] for e in entries.values()) == 8088
    assert disclosure.express_terms()["counts"]["total_public_rows"] == 8088


@pytest.mark.skipif(
    not RELEASE_SITES.is_dir(),
    reason="the release compartment rows (exports/out/national) are a local build artifact",
)
def test_row_counts_recompute_from_the_release_compartments() -> None:
    """The committed counts are code-computed — recompute them here (F-403)."""
    import csv

    counts: dict[str, int] = {}
    for csv_path in sorted(RELEASE_SITES.glob("*/sites.csv")):
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                sid = (row.get("source_id") or "").split("@", 1)[0]
                counts[sid] = counts.get(sid, 0) + 1
    for sid, entry in _entries().items():
        assert counts.get(sid, 0) == entry["public_row_count"], sid


def test_verbatim_text_equals_the_catalog_sweep_capture() -> None:
    sweep = json.loads(SWEEP_PATH.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in sweep["datasets"]}
    for sid, entry in _entries().items():
        if sid == "camreg_txdot_rep_tx":
            # TxDOT's republished item carries licence "none"; its captured
            # terms live on the origin org's sibling items (I5-Q021/Q012) —
            # the record labels that caveat instead of pretending the item
            # itself carried them.
            assert "sibling items in the TxDOT ArcGIS org" in entry["capture_note"]
            assert entry["captured_terms_verbatim"].startswith(
                "GIS content and data provided is the property of TxDOT"
            )
            continue
        ref = entry["captured_terms_evidence"]
        assert "catalog_sweep_2026-09-18_qualified.json" in ref
        item_id = ref.rsplit("id=", 1)[1].rstrip("]")
        assert by_id[item_id]["licence_verbatim"] == entry["captured_terms_verbatim"], sid


def test_basis_block_carries_the_operator_words_and_adopted_sentence() -> None:
    basis = disclosure.basis()
    assert basis["adr"] == "docs/adr/ADR-183-express-terms-acceptance.md"
    texts = {w["key"]: w["text"] for w in basis["operator_words"]}
    assert texts["A-8"] == "Keep all, accept risk"
    assert texts["A-8 wording"] == "Keep everything as is"
    assert texts["SB-2"] == "Yes, same sources (Recommended)"
    adopted = basis["adopted_sentence"]
    assert adopted.startswith("I accept the express-terms risk for all ≈8,088")
    assert hashlib.sha256(adopted.encode()).hexdigest() == basis["adopted_sentence_sha256"]
    assert "A-9 applies to new sources only" in adopted


def test_sources_toml_rights_blocks_carry_the_same_fields() -> None:
    registry_toml = tomllib.loads(SOURCES_TOML.read_text(encoding="utf-8"))["sources"]
    for sid, entry in _entries().items():
        rights = registry_toml[sid]["rights"]
        assert rights["captured_terms_verbatim"] == entry["captured_terms_verbatim"], sid
        assert rights["publication_basis"] == entry["publication_basis"], sid
        assert rights["captured_terms_evidence"] == entry["captured_terms_evidence"], sid


def test_registry_loader_threads_the_fields_onto_rights_records() -> None:
    records = {s.id: s.rights for s in sources() if s.id in AFFECTED}
    assert set(records) == AFFECTED
    for sid, entry in _entries().items():
        rec = records[sid]
        assert rec.captured_terms_verbatim == entry["captured_terms_verbatim"], sid
        assert rec.publication_basis == "operator-accepted express terms (ADR-183)", sid


def test_downstream_obligations_carry_terms_and_basis_per_row() -> None:
    """SIG-LIC-011: a consumer complies without re-deriving the chain."""
    record = _rights_from_row(
        "camreg_trpa_us",
        tomllib.loads(SOURCES_TOML.read_text(encoding="utf-8"))["sources"]["camreg_trpa_us"],
    )
    obligations = downstream_obligations(record)
    assert obligations["captured_terms_verbatim"] == "CC BY-NC"
    assert obligations["publication_basis"] == "operator-accepted express terms (ADR-183)"
    assert obligations["captured_terms_evidence"]

    unaffected = RightsRecord(
        source_id="src_unaffected",
        spdx="CC-BY-4.0",
        attribution="x",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=__import__("datetime").date(2026, 9, 18),
    )
    plain = downstream_obligations(unaffected)
    assert "captured_terms_verbatim" not in plain
    assert "publication_basis" not in plain


def test_apply_to_record_decorates_only_affected_sources() -> None:
    from datetime import date

    base = RightsRecord(
        source_id="camreg_und_023",
        spdx="LicenseRef-OperatorAccepted-DBRight",
        attribution="x",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 9, 18),
    )
    decorated = disclosure.apply_to_record(base)
    assert (
        decorated.captured_terms_verbatim == _entries()["camreg_und_023"]["captured_terms_verbatim"]
    )

    other = disclosure.apply_to_record(
        RightsRecord(
            source_id="not_affected",
            spdx="CC0-1.0",
            attribution="x",
            redistributable=True,
            derivative_permitted=True,
            terms_url="",
            retrieval_date=date(2026, 9, 18),
        )
    )
    assert other.captured_terms_verbatim == ""


def test_all_eight_release_rows_land_the_disclosure() -> None:
    """P34.19 AC1 — non-empty captured-terms + basis on EVERY affected source."""
    for sid in sorted(AFFECTED):
        entry = disclosure.disclosure_for(sid)
        assert entry is not None, sid
        assert entry["captured_terms_verbatim"], sid
        assert entry["publication_basis"], sid


def test_schema_gate_fails_on_a_wrong_table(tmp_path: Path) -> None:
    # The loader is schema-pinned — a table that drifts fails closed.
    assert disclosure.express_terms()["schema"] == "sig.express-terms-disclosure/1"
