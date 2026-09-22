# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ops/CLI commit-chunk-size resolver (P26.18 / SOURCES.17).

The PG claim sink's per-transaction commit size is operator config, not code:
the composition roots resolve an explicit flag, else ``$SIG_COMMIT_CHUNK_SIZE``,
else ``None`` (the sink applies its own default so ordinary sources commit in a
single chunk — unchanged behaviour). These tests pin that resolution and its
fail-loud behaviour on a misconfigured value, with no database or driver.
"""

from __future__ import annotations

import pytest
from connectors.sinks import ENV_COMMIT_CHUNK_SIZE, resolve_commit_chunk_size


def test_explicit_flag_wins_over_env() -> None:
    assert resolve_commit_chunk_size(50, env={ENV_COMMIT_CHUNK_SIZE: "10"}) == 50


def test_env_used_when_no_explicit_flag() -> None:
    assert resolve_commit_chunk_size(None, env={ENV_COMMIT_CHUNK_SIZE: "25000"}) == 25000


def test_unset_returns_none_so_the_sink_default_applies() -> None:
    assert resolve_commit_chunk_size(None, env={}) is None
    assert resolve_commit_chunk_size(None, env={ENV_COMMIT_CHUNK_SIZE: "  "}) is None


def test_non_positive_or_non_numeric_env_fails_loud() -> None:
    with pytest.raises(ValueError):
        resolve_commit_chunk_size(None, env={ENV_COMMIT_CHUNK_SIZE: "0"})
    with pytest.raises(ValueError):
        resolve_commit_chunk_size(None, env={ENV_COMMIT_CHUNK_SIZE: "-5"})
    with pytest.raises(ValueError):
        resolve_commit_chunk_size(None, env={ENV_COMMIT_CHUNK_SIZE: "lots"})
