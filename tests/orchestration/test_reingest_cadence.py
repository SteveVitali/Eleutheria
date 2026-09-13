# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Acceptance + unit tests for the re-ingest cadence seam (SCHED.1, GL-SCHED-01, ADR-076).

The three deterministic acceptance criteria of P24.2, each written so it FAILS if
the behaviour it guards is removed:

1. a scheduled run re-ingests a source, produces **new dated claims** (never
   overwrites) and **records freshness**;
2. a source going dark triggers a **disappearance record**;
3. **append-only** is preserved — a re-ingest only adds claims / freshness rows,
   and the cadence module issues NO UPDATE/DELETE anywhere.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from connectors.net import ChallengeEncountered
from connectors.stages import InMemoryClaimSink

from orchestration import cadence

REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DRIVEN = REPO_ROOT / "tests" / "connectors" / "fixtures" / "data_driven"
_V1 = _DATA_DRIVEN / "release_v1.json"
_V2 = _DATA_DRIVEN / "release_v2.json"
_SOURCE = "eff_data_driven"
_CADENCE_MODULE = REPO_ROOT / "orchestration" / "src" / "orchestration" / "cadence.py"


def _claim_key(claim: dict) -> tuple:
    """A claim's identity for the append/overwrite check (subject+predicate+version)."""
    return (
        claim.get("subject_id"),
        claim.get("predicate_id"),
        claim.get("release_version"),
        claim.get("release_digest"),
    )


# --- Acceptance 1: scheduled re-ingest → new dated claims + freshness ----------


def test_scheduled_reingest_produces_new_dated_claims_and_records_freshness(
    tmp_path: Path,
) -> None:
    ledger = cadence.FreshnessLedger(tmp_path / "freshness")
    sink = InMemoryClaimSink()  # one shared sink across ticks == the persistent spine

    # Tick 1: first ever ingest of the source (release v1). Always due.
    t1 = datetime(2026, 1, 1, tzinfo=UTC)
    r1 = cadence.run_scheduled_source(_SOURCE, fixture=_V1, ledger=ledger, sink=sink, now=t1)
    assert r1.ran and r1.claim_count > 0
    # The re-ingest produces DATED claims — every substantive (predicate-bearing)
    # claim carries a retrieval date and an observed period.
    dated = [c for c in r1.claims if c.get("predicate_id")]
    assert dated and all(c.get("retrieved_date") and c.get("observed_at") for c in dated)
    after_tick1 = list(sink.claims)
    assert len(after_tick1) == r1.claim_count

    # Freshness was recorded for tick 1.
    assert ledger.last_ingested_at(_SOURCE) == t1
    assert r1.freshness is not None and r1.freshness.claim_count == r1.claim_count

    # Tick 2: the upstream has published a NEW release (v2); the scheduler is past
    # the source's re-ingest interval, so it re-ingests (force past the interval).
    t2 = t1 + timedelta(days=cadence.reingest_interval_days(_SOURCE) + 1)
    assert cadence.is_due(_SOURCE, ledger, t2)
    r2 = cadence.run_scheduled_source(_SOURCE, fixture=_V2, ledger=ledger, sink=sink, now=t2)
    assert r2.ran and r2.claim_count > 0

    # NEW dated claims: v2's claims are disjoint from v1's (a new version/digest).
    v1_keys = {_claim_key(c) for c in after_tick1}
    v2_keys = {_claim_key(c) for c in r2.claims}
    assert v1_keys.isdisjoint(v2_keys), "a re-ingest must yield NEW dated claims, not collisions"

    # NEVER overwrites: the shared sink still holds every v1 claim PLUS the v2 ones.
    combined = list(sink.claims)
    assert len(combined) == len(after_tick1) + r2.claim_count
    combined_keys = {_claim_key(c) for c in combined}
    assert v1_keys <= combined_keys, "v1 claims must survive the re-ingest (never overwritten)"

    # Freshness updated to the newer tick; the older record is preserved (history).
    records = ledger.records_for(_SOURCE)
    assert len(records) == 2
    assert [r.ingested_at for r in records] == [t1.isoformat(), t2.isoformat()]
    assert ledger.last_ingested_at(_SOURCE) == t2


def test_source_not_due_is_skipped_without_reingesting(tmp_path: Path) -> None:
    ledger = cadence.FreshnessLedger(tmp_path / "freshness")
    sink = InMemoryClaimSink()
    t1 = datetime(2026, 1, 1, tzinfo=UTC)
    cadence.run_scheduled_source(_SOURCE, fixture=_V1, ledger=ledger, sink=sink, now=t1)
    before = len(sink.claims)

    # One day later — well inside the 30-day interval — the source is not due.
    t_soon = t1 + timedelta(days=1)
    assert not cadence.is_due(_SOURCE, ledger, t_soon)
    skipped = cadence.run_scheduled_source(
        _SOURCE, fixture=_V2, ledger=ledger, sink=sink, now=t_soon
    )
    assert not skipped.ran and skipped.skipped_reason
    assert len(sink.claims) == before  # nothing re-ingested
    assert len(ledger.records_for(_SOURCE)) == 1  # no extra freshness row


# --- Acceptance 2: a source going dark triggers a disappearance record ---------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, "link_rotted"),
        (410, "link_rotted"),
        (401, "access_restricted"),
        (451, "access_restricted"),
    ],
)
def test_source_going_dark_triggers_a_disappearance_record(status: int, expected: str) -> None:
    observed = datetime(2026, 2, 1, tzinfo=UTC)
    disappearance = cadence.detect_disappearance(
        artifact_id="artifact-okc-portal",
        observed_at=observed,
        http_status=status,
        subject_id="agency:okcpd",
    )
    assert disappearance is not None, "a dark source MUST produce a disappearance record"
    assert disappearance.event.failing_status == expected
    assert disappearance.event.observed_at == observed
    # It is data, not a swallowed error: the event AND a research task are produced.
    rows = disappearance.rows()
    assert rows["event"]["capture_status"] == expected
    assert rows["research_task"]["task_type"] == "source_disappeared"


def test_persistent_challenge_is_recorded_as_a_disappearance() -> None:
    disappearance = cadence.detect_disappearance(
        artifact_id="artifact-x",
        observed_at=datetime(2026, 2, 1, tzinfo=UTC),
        error=ChallengeEncountered("429 challenge"),
    )
    assert disappearance is not None
    assert disappearance.event.failing_status == "access_restricted"


def test_healthy_fetch_produces_no_disappearance() -> None:
    assert (
        cadence.detect_disappearance(
            artifact_id="artifact-x",
            observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            http_status=200,
        )
        is None
    )


def test_disappearance_sweep_cadence_is_volatility_proportional() -> None:
    # A volatile source is swept far more often than a glacial one (SIG-EVID-015).
    assert cadence.disappearance_sweep_days("VOLATILE") < cadence.disappearance_sweep_days("STABLE")
    assert cadence.disappearance_sweep_due(last_swept=None)  # never swept => due
    now = datetime(2026, 3, 1, tzinfo=UTC)
    fresh = now - timedelta(hours=1)
    assert not cadence.disappearance_sweep_due(fresh, now, volatility_class="STABLE")


# --- Acceptance 3: append-only preserved (no UPDATE/DELETE anywhere) -----------


def test_cadence_module_issues_no_update_or_delete() -> None:
    """The scheduling seam must never UPDATE/DELETE the claim spine (append-only)."""
    source = _CADENCE_MODULE.read_text(encoding="utf-8").lower()
    assert "update " not in source, "cadence.py must not issue UPDATE (append-only, P1–P3)"
    assert "delete " not in source, "cadence.py must not issue DELETE (append-only, P1–P3)"


def test_freshness_ledger_is_append_only(tmp_path: Path) -> None:
    ledger = cadence.FreshnessLedger(tmp_path / "freshness")
    r_a = cadence.FreshnessRecord(_SOURCE, "2026-01-01T00:00:00+00:00", "scheduled", 3)
    r_b = cadence.FreshnessRecord(_SOURCE, "2026-02-01T00:00:00+00:00", "scheduled", 5)
    path = ledger.record(r_a)
    first_bytes = path.read_bytes()
    ledger.record(r_b)
    second_bytes = path.read_bytes()
    # The second write only APPENDED — the first record's bytes are a prefix.
    assert second_bytes.startswith(first_bytes)
    assert len(second_bytes) > len(first_bytes)
    assert [r.ingested_at for r in ledger.records_for(_SOURCE)] == [
        r_a.ingested_at,
        r_b.ingested_at,
    ]


# --- cadence parsing (etiquette) ----------------------------------------------


@pytest.mark.parametrize(
    ("cadence_text", "expected"),
    [
        ("", cadence.DEFAULT_INTERVAL_DAYS),
        ("daily", 1),
        ("hourly", 1),  # clamped to the daily etiquette floor
        ("weekly", 7),
        ("monthly", 30),
        ("quarterly", 90),
        ("annually", 365),
        ("every 3 days", 3),
        ("refresh every 2 weeks", 14),
        ("do not poll faster than upstream refresh", cadence.DEFAULT_INTERVAL_DAYS),
    ],
)
def test_cadence_text_maps_to_interval_days(cadence_text: str, expected: int) -> None:
    import dataclasses

    from connectors.registry import get

    record = dataclasses.replace(get(_SOURCE), cadence=cadence_text)
    assert cadence.reingest_interval_days(record) == expected


def test_interval_is_never_below_the_etiquette_floor() -> None:
    import dataclasses

    from connectors.registry import get

    record = dataclasses.replace(get(_SOURCE), cadence="every 0 days")
    assert cadence.reingest_interval_days(record) >= cadence.MIN_INTERVAL_DAYS


def test_due_sources_lists_uningested_sources_then_none_when_fresh(tmp_path: Path) -> None:
    ledger = cadence.FreshnessLedger(tmp_path / "freshness")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert _SOURCE in cadence.due_sources(ledger, now)
    ledger.record(cadence.FreshnessRecord(_SOURCE, now.isoformat(), "scheduled", 1))
    # Just after ingest it is no longer due.
    assert _SOURCE not in cadence.due_sources(ledger, now + timedelta(days=1))
