# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.79 / R11-K13-SRCH-00 — the held-out search relevance set (B-28 = b).

The seal is the contract: the emitted bytes live only in the restricted
bucket; the repo carries the label, the reader rule and the sha256. These
tests pin the generated artifact's invariants (never a living record) and
the structural boundary — a tuning-context read attempt must stay
impossible inside the repo.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from ops import held_out_relevance as h

REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "docs/build/reports/p36.79-held-out-relevance"
SCRIPT = REPO / "ops/gcp/held-out-seal.sh"

MIN_QUERIES = 40


@pytest.fixture(scope="module")
def doc() -> dict:
    return h.build_set()


# --- the set ---------------------------------------------------------------


def test_at_least_forty_queries(doc):
    assert doc["counts"]["queries"] >= MIN_QUERIES
    assert len(doc["queries"]) == doc["counts"]["queries"]


def test_closed_vocabularies_and_unique_queries(doc):
    kinds = {q["kind"] for q in doc["queries"]}
    assert kinds <= h._KINDS, kinds - h._KINDS
    assert {q["judgement"] for q in doc["queries"]} <= h._JUDGEMENTS
    assert {q["expected"]["type"] for q in doc["queries"]} <= h._EXPECTED_TYPES
    assert {s.surface for s in h._SLOTS} <= h._SURFACES
    queries = [q["query"].lower() for q in doc["queries"]]
    assert len(queries) == len(set(queries)), "duplicate query text"
    assert len({q["id"] for q in doc["queries"]}) == len(queries)
    for q in doc["queries"]:
        assert q["query"].strip() == q["query"] and q["query"], q


def test_honest_set_expects_nothing(doc):
    honest = [q for q in doc["queries"] if q["judgement"] == "honest"]
    assert honest, "the honest set must be non-empty (0 misleading top hits)"
    for q in honest:
        assert q["expected"]["type"] == "none", q
        assert q["answerable"] is False


def test_typos_misspell_and_expect_the_subject(doc):
    typos = [q for q in doc["queries"] if q["kind"] == "typo"]
    assert typos
    for q in typos:
        assert q["expected"]["expects_suggestion"] is True
        assert q["query"] != q["expected"]["match"], q


def test_label_verbatim_everywhere(doc):
    label = "agent-authored held-out set; not independent"
    assert doc["label"] == label
    assert doc["metric"]["estimand_label"] == label
    desc = json.loads((REPORT_DIR / "descriptor.json").read_text())
    pkt = json.loads((REPORT_DIR / "packet.json").read_text())
    assert desc["label"] == desc["metric_label"] == label
    assert pkt["label"] == label


def test_access_rule_names_only_the_acceptance_row(doc):
    assert doc["access"]["reader"].startswith("R11-K13-SRCH-07")
    assert "P36.71" in doc["access"]["reader"]
    assert "P36.31" in doc["access"]["rule"]


def test_deterministic_emit(doc):
    a, b = h.emit_bytes(), h.emit_bytes()
    assert a == b
    assert h.canonical_bytes(doc) == a


def test_committed_descriptor_matches_emitted_bytes():
    desc = json.loads((REPORT_DIR / "descriptor.json").read_text())
    blob = h.emit_bytes()
    assert desc["schema"] == h.DESCRIPTOR_SCHEMA
    assert desc["sha256"] == hashlib.sha256(blob).hexdigest()
    assert desc["bytes"] == len(blob)
    assert desc["status"] == "prepared_not_executed"
    # The descriptor is the reader contract: digest + rule, never a set row.
    for k in desc:
        assert k not in {"queries", "slots", "subjects"}, k
    assert "queries" not in json.dumps(desc)


def test_verify_object_round_trip():
    blob = h.emit_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert h.verify_object(blob, digest)
    assert not h.verify_object(blob + b"x", digest)
    assert not h.verify_object(b"forged", digest)


def test_packet_records_prepared_not_executed_and_rerun():
    pkt = json.loads((REPORT_DIR / "packet.json").read_text())
    assert pkt["schema"] == h.SEAL_SCHEMA
    assert pkt["status"] == "prepared_not_executed"
    assert pkt["sha256"] == hashlib.sha256(h.emit_bytes()).hexdigest()
    assert pkt["queue"]["rerun"] == (
        "implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md "
        "live_verification=true"
    )
    assert "P36.79" in pkt["authority"] and "GATE-G5" in pkt["authority"]
    assert pkt["counts"]["queries"] >= MIN_QUERIES


# --- the seal boundary: no read path in the repo ---------------------------


def _committed_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, check=True, text=True)
    return [ln for ln in out.stdout.splitlines() if ln]


def test_no_emitted_content_lands_in_the_tree(doc):
    """Every emitted query string + the canonical blob must be absent from
    committed files — the seal keeps the set's bytes out of the repo."""
    blob = h.emit_bytes().decode()
    candidates = []
    for path in _committed_files():
        p = REPO / path
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(errors="strict")
        except (UnicodeDecodeError, ValueError):
            continue
        candidates.append((path, text))
    joined = "".join(t for _, t in candidates)
    assert blob not in joined
    # No committed file materialises a query↔id binding: a rendered query
    # string serialized as a JSON row, or named beside its slot id. Generic
    # words (a state name in a vocabulary map) are not the set — the leak the
    # seal forbids is the emitted *binding*.
    leaked = [
        (q["id"], q["query"])
        for q in doc["queries"]
        if f'"query":"{q["query"]}"' in blob.replace(" ", "")
        and (
            f'"query":"{q["query"]}"' in joined.replace(" ", "")
            or f'"query": "{q["query"]}"' in joined
            or re.search(rf"{q['id']}\b[^]]{{0,200}}{re.escape(q['query'])}", joined)
        )
    ]
    assert not leaked, f"committed tree leaks emitted query bindings: {leaked[:5]}"


def test_no_reader_imports_the_emit_path():
    """Only the ops seal lane may import held_out_relevance — a tuning or
    benchmark module importing it is a seal breach (B-28 = b)."""
    allowed = {
        "ops/src/ops/held_out_relevance.py",
        "ops/src/ops/cli.py",
        "tests/ops/test_held_out_relevance.py",
    }
    offenders = []
    for path in _committed_files():
        if path in allowed or not path.endswith((".py", ".ts", ".astro", ".mjs", ".sh", ".toml")):
            continue
        p = REPO / path
        if p.is_file() and "held_out_relevance" in p.read_text(errors="replace"):
            offenders.append(path)
    assert not offenders, offenders


def test_no_held_out_fixture_or_data_reader_exists(doc):
    """No committed fixture/data/reader file on a tuning surface may carry
    the artifact's record type or feed set rows to a reader — the
    descriptor under ``docs/build/reports/p36.79-*/`` is the only committed
    reference point (build memory — LEDGER/DEFERRALS/projection — may name
    the schema id: it is the obligation record, never a set row)."""
    hits = []
    for path in _committed_files():
        if not path.startswith(
            ("tests/", "web/", "exports/", "api/", "connectors/", "tasks/",
             "parsing/", "ontology/", "db/", "resolution/", "reconcile/",
             "inference/", "evidence/", "orchestration/")
        ):
            continue
        if path.startswith("tests/ops/test_held_out_relevance"):
            continue
        p = REPO / path
        if p.is_file() and h.SET_SCHEMA in p.read_text(errors="replace"):
            hits.append(path)
    assert not hits, hits


# --- the scripted leg -------------------------------------------------------


def _run_script(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("SIG_GCP_PROJECT", None)
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=REPO, capture_output=True, text=True, env=env
    )


def test_seal_script_check_mode_offline():
    r = _run_script("--check")
    assert r.returncode == 0, r.stderr
    assert "gcloud storage cp" in r.stdout
    assert "search/held-out/" in r.stdout


def test_seal_script_apply_refuses_without_author():
    r = _run_script(
        "--apply",
        env_extra={"SIG_GCP_PROJECT": "sig-x", "SIG_HELDOUT_NOW": "2026-10-29T12:00:00Z"},
    )
    assert r.returncode == 4
    assert "SIG_HELDOUT_AUTHOR" in r.stderr + r.stdout


def test_seal_script_window_guard_exits_42_inside_excluded_hours():
    r = _run_script(
        "--apply",
        env_extra={
            "SIG_GCP_PROJECT": "sig-x",
            "SIG_HELDOUT_AUTHOR": "op",
            "SIG_HELDOUT_NOW": "2026-10-29T05:30:00Z",
        },
    )
    assert r.returncode == 42
    assert "03:00-10:00Z" in r.stdout


def test_seal_script_window_guard_passes_outside_excluded_hours():
    r = _run_script(
        "--apply",
        env_extra={
            "SIG_GCP_PROJECT": "sig-x",
            "SIG_HELDOUT_NOW": "2026-10-29T12:00:00Z",
            "SIG_HELDOUT_AUTHOR": "op",
        },
    )
    assert r.returncode != 42 and "QUEUED" not in r.stdout  # window passes;
    # the ADC/author gates decide after — never a fabricated write


# --- the CLI ----------------------------------------------------------------


def test_cli_digest_and_verify(tmp_path):
    out = tmp_path / "set.json"
    r = subprocess.run(
        ["uv", "run", "python", "-m", "ops", "held-out", "emit", "--out", str(out)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    digest = h.set_sha256()
    r2 = subprocess.run(
        ["uv", "run", "python", "-m", "ops", "held-out", "verify", str(out), "--sha256", digest],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr
    r3 = subprocess.run(
        ["uv", "run", "python", "-m", "ops", "held-out", "verify", str(out), "--sha256", "0" * 64],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r3.returncode == 4
