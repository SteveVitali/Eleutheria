#!/usr/bin/env python3
"""Run the current vendored detector without its shared /tmp report collision.

Only the output destination is substituted in a private temporary copy. Detection
logic and the committed vendored script are unchanged; not the P32.8 writer fix.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def main() -> int:
    report = ROOT / "docs/build/logs" / ("six-stream-memory-" + uuid.uuid4().hex + ".json")
    report.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / "scripts/docs/check-build-memory.sh"
    text = source.read_text()
    needle = "JSON='/tmp/build-memory-check.json'"
    if text.count(needle) != 1:
        raise SystemExit("Validator output assignment changed; re-review wrapper before running")
    # Quote a generated local path as shell data, not executable interpolation.
    quoted = "'" + str(report).replace("'", "'\"'\"'") + "'"
    with tempfile.TemporaryDirectory(prefix="sig-memory-check-") as tmp:
        runner = Path(tmp) / "check-build-memory.sh"
        runner.write_text(text.replace(needle, "JSON=" + quoted))
        shutil.copyfile(ROOT / "scripts/docs/adr-index.sh", Path(tmp) / "adr-index.sh")
        result = subprocess.run(["bash", str(runner), str(ROOT)], cwd=ROOT)
    if report.exists():
        value = json.loads(report.read_text())
        print("Private report:", report)
        print("Report counts:", {k: len(value.get(k, [])) for k in ("violations", "warnings")})
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
