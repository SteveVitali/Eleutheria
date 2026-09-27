#!/usr/bin/env python3
"""Run the vendored build-memory validator with an isolated, unique report path.

Historical note: before P32.8 the vendored ``check-build-memory.sh`` hard-wrote
``/tmp/build-memory-check.json``, so concurrent worktrees raced over one shared
report and this wrapper sed-patched a private copy. P32.8 patched the validator
itself (SIG-MEM-003, ADR-127): it now accepts ``--json PATH``. The wrapper is
kept — it names a unique report under the worktree's own gitignored
``docs/build/logs/`` and prints the parsed counts — but no longer modifies the
script, so what runs is byte-for-byte the committed validator.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def main() -> int:
    report = ROOT / "docs/build/logs" / ("six-stream-memory-" + uuid.uuid4().hex + ".json")
    report.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / "scripts/docs/check-build-memory.sh"
    result = subprocess.run(
        ["bash", str(source), str(ROOT), "--json", str(report)], cwd=ROOT
    )
    if report.exists():
        value = json.loads(report.read_text())
        print("Private report:", report)
        summary = value.get("summary", {})
        print(
            "Report counts:",
            {"violations": summary.get("violations"), "warnings": summary.get("warnings")},
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
