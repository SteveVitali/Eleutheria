#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_spec_src.py`` (P20.2, SIG-ENG-039).

Kept beside the tool under ``docs/build/tools/`` because P20.2's diff is scoped to
``docs/**``; it is therefore *not* collected by ``make check`` (``testpaths=["tests"]``).
Run it explicitly::

    uv run pytest docs/build/tools/test_check_spec_src.py
    # or, stdlib only:
    python3 docs/build/tools/test_check_spec_src.py
"""
from __future__ import annotations

import importlib.util
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_spec_src", _HERE / "check_spec_src.py")
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mod)


def test_grammar_accepts_real_ids() -> None:
    for good in ("SIG-UI-047", "SIG-EVID-020", "SIG-ENG-039", "SIG-CONTRIB-011a", "SIG-ONTO-069"):
        assert mod.GRAMMAR_RE.match(good), good


def test_grammar_rejects_malformed_ids() -> None:
    for bad in ("SIG-UI-47", "sig-ui-047", "SIG-TOOLONGAREA-001", "SIG-X-001", "UI-047"):
        assert not mod.GRAMMAR_RE.match(bad), bad


def test_definition_regex_needs_a_level_keyword() -> None:
    assert mod.DEF_RE.findall("**SIG-UI-047 (MAY).** text") == ["SIG-UI-047"]
    assert mod.DEF_RE.findall("**SIG-UI-047 (conforming form).**") == []
    # a bare reference is not a definition
    assert mod.DEF_RE.findall("see SIG-UI-047 for details") == []


def test_reserved_set_matches_the_ticket() -> None:
    assert {"SIG-ENG-006", "SIG-ENG-009", "SIG-ENG-028", "SIG-ENG-029"} <= mod.RESERVED


def test_fold_back_count_is_three() -> None:
    assert mod.EXPECTED_IDS == mod.BASELINE_IDS + len(mod.FOLD_BACK_IDS)
    assert mod.EXPECTED_IDS == 671


def test_appendix_f_ids_parses_rows() -> None:
    sample = (
        "# Appendix F — index\n"
        "| ADR | Decision | Phase |\n"
        "|---|---|---|\n"
        "| ADR-001 | x | P00.2 |\n"
        "| ADR-062 | y | P20.2 |\n"
        "# Appendix G — corrections\n"
        "| ADR-999 | should be ignored (after Appendix G) |\n"
    )
    assert mod.appendix_f_ids(sample) == {"ADR-001", "ADR-062"}


def test_assembled_reproduces_committed_spec_bytes() -> None:
    # the live tree must reproduce byte-for-byte (this is the deterministic AC)
    assert mod.assembled() == mod.SPEC.read_text()


def test_main_passes_on_the_committed_tree() -> None:
    assert mod.main() == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
