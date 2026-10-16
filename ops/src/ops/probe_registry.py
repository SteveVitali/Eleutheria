# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""probe_registry — the committed production-truth probe registry (P35.3, G10).

The registry is ``docs/build/tools/record_policy/tail_probe_sweep.toml`` —
the ADR-199 tail-sweep contract this row *extends*, never forks. One entry per
production-truth probe: id, subject requirement, owner row, trigger points ⊆
{pr, candidate, publish, schedule, tail}, producer command, record location.

Validation is **one implementation** — ``check_round_close.load_sweep`` (the
grammar: >= 1 trigger point, vocab, owner row, record location) plus
``check_round_close.check_probe_surfaces`` (dry-run resolution: every ``via``
surface resolves against a real job/trigger/verb/row). This module imports
that tool by path — ops never re-derives its own registry grammar.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ROUND_CLOSE_TOOL = REPO_ROOT / "docs" / "build" / "tools" / "check_round_close.py"
SWEEP_PATH = "docs/build/tools/record_policy/tail_probe_sweep.toml"

_TRIGGER_LABELS = {
    "pr": "pull request",
    "candidate": "release candidate",
    "publish": "publish",
    "schedule": "schedule",
    "tail": "round tail",
}


def _load_checker() -> Any:
    """Import the round-close checker by path — one validation, zero forks."""
    spec = importlib.util.spec_from_file_location("check_round_close", ROUND_CLOSE_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ROUND_CLOSE_TOOL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_registry(root: Path = REPO_ROOT) -> tuple[list[dict[str, Any]], list[str]]:
    """``(probes, errors)`` — the grammar leg (load_sweep + surface resolution)."""
    if not ROUND_CLOSE_TOOL.is_file():
        return [], [f"{ROUND_CLOSE_TOOL}: the registry validator is absent"]
    try:
        crc = _load_checker()
    except Exception as e:  # noqa: BLE001 — surface the load failure honestly
        return [], [f"{ROUND_CLOSE_TOOL}: failed to import: {e}"]
    probes, err = crc.load_sweep(root)
    errors: list[str] = [err] if err else []
    if probes:
        surf_errors, stats = crc.check_probe_surfaces(probes, root)
        errors.extend(surf_errors)
        if stats["via_declarations"] > 0 and stats["via_evaluated"] == 0:
            errors.append("every via declaration failed to resolve (G11)")
    return probes, errors


def describe(probe: dict[str, Any]) -> str:
    """One line: id · owner · trigger points → record."""
    triggers = ", ".join(_TRIGGER_LABELS.get(t, t) for t in probe.get("triggers", []))
    return (
        f"{probe['id']:<24} {probe.get('owner', '?'):<9} [{triggers}] → {probe.get('record', '')}"
    )


def registry_report(root: Path = REPO_ROOT) -> dict[str, Any]:
    """The offline report — the same data `probe-registry` prints."""
    if not ROUND_CLOSE_TOOL.is_file():
        return {
            "registry": SWEEP_PATH,
            "probes": [],
            "probe_count": 0,
            "via_total": 0,
            "via_resolved": 0,
            "errors": [f"{ROUND_CLOSE_TOOL}: the registry validator is absent"],
        }
    crc = _load_checker()
    probes, err = crc.load_sweep(root)
    errors: list[str] = [err] if err else []
    via_total = via_resolved = 0
    if probes:
        surf_errors, stats = crc.check_probe_surfaces(probes, root)
        errors.extend(surf_errors)
        via_total = stats["via_declarations"]
        via_resolved = stats["via_evaluated"]
        if via_total > 0 and via_resolved == 0:
            errors.append("every via declaration failed to resolve (G11)")
    return {
        "registry": SWEEP_PATH,
        "probes": [
            {
                "id": p["id"],
                "owner": p.get("owner"),
                "requires": p.get("requires", []),
                "triggers": p.get("triggers", []),
                "via": p.get("via", {}),
                "command": p.get("command"),
                "record": p.get("record"),
            }
            for p in probes
        ],
        "probe_count": len(probes),
        "via_total": via_total,
        "via_resolved": via_resolved,
        "errors": errors,
    }
