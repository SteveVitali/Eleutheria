# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ingest_run recording + reproducibility (SIG-EVID-016/017/018)."""

from __future__ import annotations

import pytest
from evidence.ingest_run import (
    IngestRun,
    assert_deterministic_environment,
    canonical_claim_tuple,
    claim_set_fingerprint,
    deterministic_environment,
)


def test_deterministic_environment_is_lc_all_c_tz_utc() -> None:
    env = deterministic_environment()
    assert env["LC_ALL"] == "C"
    assert env["TZ"] == "UTC"


def test_non_deterministic_environment_is_rejected() -> None:
    with pytest.raises(ValueError):
        assert_deterministic_environment({"LC_ALL": "en_US.UTF-8", "TZ": "UTC"})


def test_ingest_run_records_the_reproducibility_fields() -> None:
    run = IngestRun(
        connector_name="flock",
        connector_version="1.2.3",
        code_commit="abc123",
        ruleset_version="r5",
        vocab_version="1.0.0",
        input_digests=("bdigest1", "bdigest2"),
        parameters={"page": 1},
    )
    row = run.to_row()
    assert row["connector_version"] == "1.2.3"
    assert row["input_digests"] == ["bdigest1", "bdigest2"]
    assert row["environment"]["LC_ALL"] == "C"


def test_ingest_run_rejects_bad_environment() -> None:
    with pytest.raises(ValueError):
        IngestRun(
            connector_name="x",
            connector_version="1",
            code_commit="c",
            ruleset_version="r",
            vocab_version="v",
            input_digests=(),
            environment={"LC_ALL": "C"},  # missing TZ=UTC
        )


def test_reproducibility_modulo_claim_id_and_sys_period() -> None:
    """SIG-EVID-017: re-run over pinned digests => byte-identical tuples modulo id/time."""
    run_a = {
        "claim_id": "id-1",
        "sys_period": "[t1,)",
        "recorded_at": "t1",
        "subject_id": "s",
        "predicate_id": "p",
        "value_num": 42,
    }
    run_b = {
        "claim_id": "id-2",
        "sys_period": "[t2,)",
        "recorded_at": "t2",
        "subject_id": "s",
        "predicate_id": "p",
        "value_num": 42,
    }
    assert canonical_claim_tuple(run_a) == canonical_claim_tuple(run_b)

    # A genuine difference in a derived value IS detected.
    run_c = dict(run_b, value_num=43)
    assert canonical_claim_tuple(run_a) != canonical_claim_tuple(run_c)


def test_claim_set_fingerprint_is_order_independent() -> None:
    a = {"claim_id": "1", "subject_id": "s", "value_num": 1}
    b = {"claim_id": "2", "subject_id": "s", "value_num": 2}
    assert claim_set_fingerprint([a, b]) == claim_set_fingerprint([b, a])
