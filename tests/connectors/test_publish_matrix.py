# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The registry publish matrix (P36.45 / R11-K13-UX10-1, SIG-TRANSP-035,
K10 §4): the field verdict table as code, the closed access/auth
vocabularies, the publisher/one_time_load seeds, and the D-J3-12 description
batch binding — 'description pending review' until the operator confirms a
batch verbatim.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from connectors.publish_matrix import (
    ACCESS_METHOD_VOCAB,
    AUTH_MODEL_VOCAB,
    DESCRIPTION_PENDING_REVIEW,
    NOT_RECORDED,
    PUBLISHER_TYPES,
    PublishVerdict,
    UnmappedVocabulary,
    batch_dir,
    batch_drift,
    batch_rows,
    classify_access_method,
    classify_auth_model,
    description_for,
    field_verdict,
    parse_batches,
    publish_matrix_violations,
    published_field,
    render_batch,
    sha256_text,
)
from connectors.registry import get, registry, sources
from support import REPO_ROOT

_SOURCES_TOML = REPO_ROOT / "connectors" / "src" / "connectors" / "data" / "sources.toml"


# --- The verdict table itself -------------------------------------------------


def test_every_registry_field_is_classified() -> None:
    """SIG-TRANSP-035: every field on every registry row has a verdict;
    an unclassified field is the failure the lint exists to catch."""
    raw = tomllib.loads(_SOURCES_TOML.read_text())["sources"]
    fields = tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/publish_matrix.toml").read_text()
    )["fields"]

    def walk(prefix: str | None, node: dict) -> list[str]:
        missing: list[str] = []
        for key, value in node.items():
            if prefix is None:
                if key not in fields:
                    missing.append(key)
                    continue
                sub = fields[key].get("sub") or {}
                for sub_key in walk_children(key, value, sub):
                    missing.append(sub_key)
            else:
                missing.append(f"{prefix}.{key}")
        return missing

    def walk_children(parent: str, value: object, sub: dict) -> list[str]:
        missing: list[str] = []
        if isinstance(value, dict):
            for k, v in value.items():
                if k not in sub:
                    missing.append(f"{parent}.{k}")
                elif isinstance(v, dict):
                    missing.extend(walk_children(f"{parent}.{k}", v, sub.get(k, {}).get("sub", {})))
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    missing.extend(walk_children(parent, entry, sub))
        return missing

    missing: list[str] = []
    for source_id, row in raw.items():
        for key, value in row.items():
            if key not in fields:
                missing.append(f"{source_id}.{key}")
            else:
                sub = fields[key].get("sub") or {}
                for m in walk_children(key, value, sub):
                    missing.append(f"{source_id}.{m}")
    assert not missing, missing[:20]


def test_unclassified_field_defaults_to_never() -> None:
    assert field_verdict("a_field_the_matrix_does_not_know") is PublishVerdict.NEVER
    assert field_verdict("bogus", parent="rights") is PublishVerdict.NEVER


def test_the_never_fields_are_k10s_unsafe_list() -> None:
    """P-8/NEW-6: notes, contact, robots_policy never reach an artifact."""
    for field in ("notes", "contact", "robots_policy"):
        assert field_verdict(field) is PublishVerdict.NEVER, field
        with pytest.raises(ValueError):
            published_field(get("osm_copyright"), field)


def test_new_metadata_fields_publish() -> None:
    for field in ("publisher", "publisher_type", "one_time_load", "description"):
        assert field_verdict(field) is PublishVerdict.PUBLISH, field


# --- The closed vocabularies --------------------------------------------------


def test_vocabulary_membership() -> None:
    assert ACCESS_METHOD_VOCAB == {
        "api",
        "bulk_file",
        "html",
        "pdf",
        "arcgis",
        "socrata",
        "ckan",
        "document_index",
    }
    assert AUTH_MODEL_VOCAB == {"none", "api_key", "login", "session"}
    assert "gov-open-data" in PUBLISHER_TYPES and "other" in PUBLISHER_TYPES


def test_every_access_method_classifies() -> None:
    for s in sources():
        token = classify_access_method(s.access_method)
        assert token in ACCESS_METHOD_VOCAB | {NOT_RECORDED}, (s.id, token)


def test_every_auth_model_classifies() -> None:
    for s in sources():
        assert classify_auth_model(s.auth_model) in AUTH_MODEL_VOCAB, s.id


def test_access_classification_examples() -> None:
    assert (
        classify_access_method("rest_api (arcgis feature layer query — registry rows only)")
        == "arcgis"
    )
    assert classify_access_method("Socrata SODA/SoQL — bounded $where slices only") == "socrata"
    assert classify_access_method("CKAN action API — registration prepared by ACQ-01") == "ckan"
    assert classify_access_method("HTML page(s) — registration prepared by ACQ-01") == "html"
    assert (
        classify_access_method("PDF document(s) — dossier_documents clause_fields adapter")
        == "document_index"
    )
    assert (
        classify_access_method("bulk file download — registration prepared by ACQ-01")
        == "bulk_file"
    )
    assert classify_access_method("wiki") == "html"
    assert classify_access_method("") == NOT_RECORDED
    with pytest.raises(UnmappedVocabulary):
        classify_access_method("carrier pigeon (unreviewed lane)")


def test_auth_classification_examples() -> None:
    assert classify_auth_model("none") == "none"
    assert classify_auth_model("") == "none"
    assert classify_auth_model("api key ($SIG_DATA_GOV_KEY, HG-09)") == "api_key"
    assert classify_auth_model("ICPSR login") == "login"
    assert classify_auth_model("5-min JWT") == "api_key"
    with pytest.raises(UnmappedVocabulary):
        classify_auth_model("smoke signals")


# --- The seeds ---------------------------------------------------------------


def test_publisher_seeded_from_target_agency() -> None:
    """K10 NEW-7: camreg/DOT publishers seed from the target's `agency`."""
    camreg = get("camreg_austin_tx")
    assert camreg.publisher == "City of Austin Transportation and Public Works"
    dot = get("dot_511_ky")
    assert dot.publisher == "Kentucky Transportation Cabinet"


def test_publisher_type_seeded_from_i1() -> None:
    """I1's §8.6 typing lands verbatim on the covered rows."""
    assert get("osm_surveillance_tagging").publisher_type == "crowdsourced"
    assert get("dot_511_ky").publisher_type in PUBLISHER_TYPES


def test_publisher_type_is_closed_vocabulary_or_absent() -> None:
    """A declared type is a §8.6 member; an untyped row stays absent —
    `other` is a recorded verdict, never a fill-in default."""
    for s in sources():
        assert not s.publisher_type or s.publisher_type in PUBLISHER_TYPES, s.id


def test_one_time_load_matches_the_static_cadence_rows() -> None:
    """SIG-INGEST-025b: the flag lands on the 'once (static; no recurrence)'
    rows and nowhere else."""
    for s in sources():
        if s.one_time_load:
            assert "once" in s.cadence.lower(), s.id


def test_description_interim_label() -> None:
    """D-J3-12: an unconfirmed row renders the interim label, never copy."""
    for s in sources():
        assert description_for(s) == (
            s.description if s.description else DESCRIPTION_PENDING_REVIEW
        )


# --- The lint -----------------------------------------------------------------


def test_registry_lint_is_green() -> None:
    """The CI pin: the committed registry passes the verdict table."""
    violations = publish_matrix_violations()
    assert not violations, violations[:25]


def test_planted_violation_fails_the_lint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The lint is a gate: an unclassified field on a row fails it."""
    raw = tomllib.loads(_SOURCES_TOML.read_text())
    raw["sources"]["osm_copyright"]["surprise_field"] = "x"
    monkeypatch.setattr(tomllib, "loads", lambda text: raw)
    violations = publish_matrix_violations()
    assert any("unclassified field 'surprise_field'" in v for v in violations), violations[:10]


def test_unconfirmed_description_fails_the_lint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-J3-12: a declared description whose batch row is only `pending`
    refuses — drafted copy never ships unconfirmed; 'description pending
    review' is the only interim."""
    raw = tomllib.loads(_SOURCES_TOML.read_text())
    sid = "osm_copyright"
    # An invented description (matches no confirmed row) must fail.
    raw["sources"][sid]["description"] = "An invented description, never confirmed."

    monkeypatch.setattr(tomllib, "loads", lambda text: raw)
    violations = publish_matrix_violations()
    assert any(sid in v and "description" in v for v in violations), violations[:10]


def test_confirmed_description_passes_the_lint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A description sha-matching a `confirmed` batch row lands."""
    raw = tomllib.loads(_SOURCES_TOML.read_text())
    sid = "osm_copyright"
    desc = "OSM copyright / licence — an upstream project source published by Example."
    raw["sources"][sid]["description"] = desc

    # Stage a batch dir where the row for sid is confirmed with desc.
    for path in tmp_path.glob("*.md"):
        path.unlink()
    rows = batch_rows(sources())
    # Find the batch containing sid; write all 24 files with sid's row flipped.
    for i, batch in enumerate(rows, 1):
        lines = [f"| {r} | {s} | {t} | {h} | pending |" for r, s, t, h in batch]
        (tmp_path / f"batch-{i:02d}.md").write_text(
            "| id | source | text | sha256 | status |\n|---|---|---|---|---|\n"
            + "\n".join(lines)
            + "\n"
        )
    # Flip sid's row to confirmed + desc.
    for path in tmp_path.glob("batch-*.md"):
        txt = path.read_text()
        if sid in txt:
            for line in txt.splitlines():
                if line.startswith("| D") and f"| {sid} |" in line:
                    parts = line.split("|")
                    new = f"|{parts[1]}| {sid} | {desc} | {sha256_text(desc)} | confirmed |"
                    txt = txt.replace(line, new)
            path.write_text(txt)
            break

    monkeypatch.setattr(tomllib, "loads", lambda text: raw)
    violations = publish_matrix_violations(directory=tmp_path)
    assert not any(sid in v and "description" in v for v in violations), violations[:15]


# --- The batch files ----------------------------------------------------------


def test_batch_files_cover_every_source_in_batches_of_25() -> None:
    directory = batch_dir()
    files = sorted(directory.glob("batch-*.md"))
    assert files, "no description batch files committed"
    parsed = parse_batches(directory)
    assert len(parsed) == len(registry()), f"batch rows {len(parsed)} != registry {len(registry())}"
    for path in files:
        text = path.read_text()
        n = sum(1 for line in text.splitlines() if line.startswith("| D"))
        assert 0 < n <= 25, f"{path.name}: {n} rows"


def test_batch_files_match_the_generator() -> None:
    """The committed batch rows equal a fresh generation (id, source, text,
    sha256) — the status column is the operator's write surface."""
    assert batch_drift() == []


def test_batch_row_hashes_verify() -> None:
    for sid, row in parse_batches(batch_dir()).items():
        assert row["sha256"] == sha256_text(row["text"]), sid
        assert row["status"] in {"pending", "confirmed"}, sid


def test_render_batch_shape() -> None:
    src = get("osm_copyright")
    rows = [("D01-01", src.id, "text of it", sha256_text("text of it"))]
    out = render_batch(1, rows)
    assert "| D01-01 | osm_copyright | text of it |" in out
    assert "| pending |" in out
