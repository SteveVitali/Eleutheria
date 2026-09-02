# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The generation gate (AC1 / SIG-STORE-034 / SIG-ENG-016): committed generated
artifacts equal a fresh generation from the single source."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from support import generated_dir

# The five downstream forms §20.1 requires, plus the SKOS schemes and the registry.
REQUIRED_ARTIFACTS = [
    "jsonschema/sig.schema.json",
    "pydantic/sig_models.py",
    "sql/sig.sql",
    "owl/sig.owl.nt",
    "shacl/sig.shacl.nt",
    "skos/technology.nt",
    "skos/capability.nt",
    "skos/predicate.nt",
    "skos/structural.nt",
    "skos/crosswalks.nt",
    "registry/predicate_registry.json",
    "registry/vocab_summary.json",
    "docs/index.md",
]


@pytest.mark.parametrize("rel", REQUIRED_ARTIFACTS)
def test_every_downstream_form_is_committed(rel: str) -> None:
    assert (generated_dir() / rel).is_file(), rel


def test_committed_artifacts_match_a_fresh_generation() -> None:
    # The heart of AC1: regenerate into a temp tree and diff against committed.
    # PYTHONHASHSEED is pinned so set-ordered generator output is byte-stable,
    # matching how `make gen` produced the committed tree.
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    result = subprocess.run(
        [sys.executable, "-m", "ontology", "generate", "--check"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
