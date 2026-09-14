#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Python dependency licence scan (CI.1 / GL-CI-01, ADR-078).

The stdlib-only counterpart of ``web/scripts/check-licenses.mjs`` (SIG-UI-039)
for the Python dependency tree: the *categories the spec excludes* are identical
(non-commercial, source-available, BUSL, SSPL, Elastic, Commons-Clause,
proprietary — a substring match, so e.g. ``CC-BY-NC-4.0`` trips on ``-NC``), an
unresolvable licence is a review-required failure, and a **strong-copyleft**
(GPL/AGPL) dependency must match a frozen expected set — adding a new GPL-family
dependency breaks the gate and forces an explicit review.

Licence metadata is read from the installed environment
(``importlib.metadata``: ``License-Expression``, the ``License`` field, then
``License ::`` classifiers — in that order of preference, merged). Real-world
metadata is messy (full licence texts, ``Dual License``, ``UNKNOWN``), so the
classifier normalises aggressively and treats *any* resolvable permissive signal
as a pass — while still failing closed when nothing resolves.

Usage (run under ``uv run`` so it sees the synced workspace env)::

    uv run python scripts/ci/license_scan.py                  # scan the env
    uv run python scripts/ci/license_scan.py --records-json F # replay records

``--records-json`` takes ``[{"name": str, "licenses": [str, ...]}]`` — the
deterministic fixture path the tests use to prove the gate fails on a seeded
violation without touching the real environment.

Exit codes: 0 pass · 1 violation(s) · 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# The excluded categories — identical to web/scripts/check-licenses.mjs so the
# two gates can never drift on *what is forbidden* (SIG-UI-039).
DENY = ("-NC", "NONCOMMERCIAL", "BUSL", "SSPL", "ELASTIC", "COMMONS-CLAUSE", "PROPRIETARY")

# Canonical licence ids that pass the gate. Mirrors the web gate's
# OSI_ALLOW + WAIVED sets (permissive OSI + CC0/BlueOak/Public-Domain), plus the
# weak-copyleft ids the existing tree legitimately carries (LGPL: psycopg;
# MPL-2.0: certifi/hypothesis — both file/library-level copyleft the web gate
# already allows). "BSD"/"W3C"/"PSF-2.0" are the Python-ecosystem spellings.
KNOWN_OK = {
    "MIT",
    "ISC",
    "Apache-2.0",
    "BSD",  # bare "BSD" metadata — ambiguous but always BSD-family permissive
    "BSD-2-Clause",
    "BSD-3-Clause",
    "0BSD",
    "MPL-2.0",
    "LGPL",
    "PSF-2.0",
    "Python-2.0",
    "CC0-1.0",
    "Public Domain",
    "Unlicense",
    "Zlib",
    "W3C",
    "BlueOak-1.0.0",
}
STRONG_COPYLEFT = {"GPL", "AGPL"}

# The frozen set of *expected* strong-copyleft dependencies in the current tree
# (env scan only): igraph (GPLv2+, via splink ER), rfc3987 (GPLv3+, via linkml
# IRI validation), docutils (mixed PD/BSD/GPL parts, via Sphinx toolchain).
# Each is dev/dependency-of-a-dep, reviewed when it entered. A NEW GPL/AGPL dep
# fails the gate (must be reviewed + appended here deliberately); a dep leaving
# the tree also fails (the set must shrink with it — never a stale allowlist).
EXPECTED_STRONG_COPYLEFT = frozenset({"docutils", "igraph", "rfc3987"})

# Normalisation aliases: uppercased, punctuation→"-" spellings → canonical ids.
_ALIASES = {
    "MIT": "MIT", "MIT-LICENSE": "MIT", "MIT-LICENCE": "MIT",
    "APACHE": "Apache-2.0", "APACHE-2": "Apache-2.0", "APACHE-2-0": "Apache-2.0",
    "APACHE-LICENSE": "Apache-2.0", "APACHE-LICENSE-2-0": "Apache-2.0",
    "APACHE-SOFTWARE-LICENSE": "Apache-2.0",
    "BSD": "BSD", "BSD-LICENSE": "BSD",
    "BSD-2-CLAUSE": "BSD-2-Clause", "BSD-2-CLAUSE-LICENSE": "BSD-2-Clause",
    "BSD-3-CLAUSE": "BSD-3-Clause", "BSD-3-CLAUSE-LICENSE": "BSD-3-Clause",
    "BSD-3": "BSD-3-Clause", "NEW-BSD": "BSD-3-Clause", "NEW-BSD-LICENSE": "BSD-3-Clause",
    "MODIFIED-BSD": "BSD-3-Clause", "MODIFIED-BSD-LICENSE": "BSD-3-Clause",
    "0BSD": "0BSD",
    "ISC": "ISC", "ISC-LICENSE": "ISC", "ISCL": "ISC",
    "MPL": "MPL-2.0", "MPL-2": "MPL-2.0", "MPL-2-0": "MPL-2.0",
    "MOZILLA-PUBLIC-LICENSE": "MPL-2.0", "MOZILLA-PUBLIC-LICENSE-2-0": "MPL-2.0",
    "PSF": "PSF-2.0", "PSF-2-0": "PSF-2.0",
    "PYTHON-2-0": "Python-2.0",
    "PYTHON-SOFTWARE-FOUNDATION-LICENSE": "PSF-2.0",
    "CC0": "CC0-1.0", "CC0-1-0": "CC0-1.0", "CC0-1-0-UNIVERSAL": "CC0-1.0",
    "CC0-1-0-UNIVERSAL-CC0-1-0-PUBLIC-DOMAIN-DEDICATION": "CC0-1.0",
    "PUBLIC-DOMAIN": "Public Domain",
    "UNLICENSE": "Unlicense", "THE-UNLICENSE": "Unlicense",
    "ZLIB": "Zlib",
    "W3C": "W3C", "W3C-LICENSE": "W3C",
    "W3C-SOFTWARE-NOTICE-AND-LICENSE": "W3C",
    "W3C-SOFTWARE-NOTICE-AND-DOCUMENT-LICENSE": "W3C",
    "BLUEOAK-1-0-0": "BlueOak-1.0.0", "BLUE-OAK-1-0-0": "BlueOak-1.0.0",
    # LGPL spellings the head pattern might not begin with (belt + braces).
    "LGPL": "LGPL", "LGPL-3": "LGPL", "LGPL-3-0": "LGPL", "LGPL-3-0-ONLY": "LGPL",
    "LGPL-3-0-OR-LATER": "LGPL", "LGPL-2-1": "LGPL", "LGPL-2-1-OR-LATER": "LGPL",
    "GNU-LGPL": "LGPL", "GNU-LESSER-GENERAL-PUBLIC-LICENSE": "LGPL",
}
# Licence *strings* that are not identifiers — resolve to nothing (the package
# then stands or falls on its classifiers).
_NON_IDS = {"", "UNKNOWN", "DUAL-LICENSE", "NONE", "SEE-LICENSE", "LICENSE"}


# A copyleft FLAG only counts when the signal line *begins* with the licence
# token — i.e. the line is a licence identifier ("GNU General Public License
# (GPL)", "GNU GPLv3+", "GPL-3.0-or-later"), not licence *prose* mentioning GPL
# (pandas' bundled license-history table carries lines like "…GPL-compatible…"
# and "the GPL." — none begin with the token). LGPL/AGPL are checked by the same
# head pattern and flag the same way.
_COPYLEFT_HEAD = re.compile(
    r"^\s*\(?\s*(?:"
    r"(?:GNU\s+)?(?:LESSER\s+|AFFERO\s+)?GENERAL\s+PUBLIC\s+LICEN[CS]E"  # [GNU] [LESSER|AFFERO] GENERAL PUBLIC LICENSE
    r"|[AL]?GPL\s*-?\s*V?\d"  # GPL3 / GPLv3 / GPL-3.0 / LGPL-2.1 / AGPL-3.0 …
    r")",
    re.IGNORECASE,
)


def _canon(raw: str) -> str | None:
    """Normalise one licence string to a canonical id (or None = not an id)."""
    s = raw.strip().upper()
    s = re.sub(r"\(.*?\)", " ", s)  # drop parentheticals: (GPL), (MPL 2.0), (ISCL)
    s = re.sub(r"\s+OR\s+LATER\b", " ", s)  # "GPLv3 or later" → GPLv3 signal stays
    s = re.sub(r"[^A-Z0-9+]+", "-", s).strip("-")
    if not s or s in _NON_IDS:
        return None
    # Copyleft families — only when the RAW line is a licence identifier (see
    # _COPYLEFT_HEAD): LGPL before AGPL before GPL ("GNU LESSER GENERAL PUBLIC
    # LICENSE" and "GNU AFFERO …" both contain the GPL shape).
    if _COPYLEFT_HEAD.match(raw.strip()):
        if "LGPL" in s or "LESSER-GENERAL" in s:
            return "LGPL"
        if "AGPL" in s or "AFFERO" in s:
            return "AGPL"
        return "GPL"
    return _ALIASES.get(s)


def _expr_atoms(expr: str) -> list[str]:
    """Split an SPDX-style expression into atoms: ``(MIT OR Apache-2.0)``."""
    parts = re.split(r"[()]|\s+(?:OR|AND|WITH)\s+|\s*/\s*", expr, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _signals(licenses: list[str]) -> list[str]:
    """Explode a package's raw licence strings into normalisable signal atoms."""
    out: list[str] = []
    for raw in licenses:
        # Lines longer than ~120 chars are licence *texts*, not identifiers —
        # still scanned for DENY substrings, but only the short lines are
        # treated as candidate identifiers.
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith("LICENSE ::"):
                out.append(line.split("::")[-1].strip())
            elif len(line) <= 120:
                out.extend(_expr_atoms(line))
    return out


def classify(records: list[dict[str, object]]) -> dict[str, list[str]]:
    """Classify ``{"name","licenses"}`` records → ok/flagged/denied/unresolvable.

    A record is ``denied`` when any DENY substring appears in its raw licence
    text; ``flagged`` when a strong-copyleft id resolves; ``unresolvable`` when
    no known id resolves; otherwise ``ok``.
    """
    result: dict[str, list[str]] = {"ok": [], "flagged": [], "denied": [], "unresolvable": []}
    for rec in records:
        name = str(rec.get("name", "?"))
        raw_licenses = rec.get("licenses", [])
        # Tolerate a bare string (treat as one licence) — a non-list value.
        if isinstance(raw_licenses, str):
            raw_licenses = [raw_licenses]
        if not isinstance(raw_licenses, list):
            raw_licenses = []
        raws = [str(x) for x in raw_licenses]
        raw_all = " | ".join(raws).upper()
        if any(d in raw_all for d in DENY):
            result["denied"].append(name)
            continue
        canons = {c for c in (_canon(s) for s in _signals(raws)) if c}
        if canons & STRONG_COPYLEFT:
            result["flagged"].append(name)
        elif canons and canons <= KNOWN_OK:
            result["ok"].append(name)
        else:
            result["unresolvable"].append(name)
    return result


def _env_records() -> list[dict[str, object]]:
    """Read licence records from the installed environment (the synced .venv)."""
    import importlib.metadata as md

    records: list[dict[str, object]] = []
    for dist in md.distributions():
        meta = dist.metadata
        name = meta.get("Name") or "?"
        if name.lower().startswith("sig-"):  # workspace members — repo Apache-2.0
            continue
        raws: list[str] = []
        if meta.get("License-Expression"):
            raws.append(str(meta["License-Expression"]))
        if meta.get("License"):
            raws.append(str(meta["License"]))
        raws.extend(c for c in (meta.get_all("Classifier") or []) if c.startswith("License"))
        records.append({"name": name, "licenses": raws})
    return records


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--records-json",
        metavar="PATH",
        help="scan a JSON fixture instead of the installed environment",
    )
    args = parser.parse_args(argv)

    env_mode = args.records_json is None
    if env_mode:
        records = _env_records()
    else:
        try:
            records = json.loads(Path(args.records_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"license_scan: cannot read --records-json: {exc}", file=sys.stderr)
            return 2

    verdict = classify(records)
    total = len(records)
    violations: list[str] = []

    for name in verdict["denied"]:
        violations.append(f"{name}: EXCLUDED licence category (non-commercial/source-available/BUSL-class)")
    for name in verdict["unresolvable"]:
        violations.append(f"{name}: licence could not be resolved to a known id — review required")

    flagged = set(verdict["flagged"])
    unexpected = flagged - EXPECTED_STRONG_COPYLEFT
    for name in sorted(unexpected):
        violations.append(
            f"{name}: NEW strong-copyleft (GPL/AGPL) dependency — needs an explicit review"
        )
    if env_mode:
        # In the real env the flagged set must equal the frozen expected set —
        # a vanished expected entry means the allowlist went stale.
        for name in sorted(EXPECTED_STRONG_COPYLEFT - flagged):
            violations.append(f"{name}: expected GPL-family dep no longer flagged — shrink EXPECTED_STRONG_COPYLEFT")

    print(f"license_scan: {total} distribution(s) — {len(verdict['ok'])} ok, "
          f"{len(flagged)} flagged-for-review (expected {len(EXPECTED_STRONG_COPYLEFT)}), "
          f"{len(verdict['denied'])} denied, {len(verdict['unresolvable'])} unresolvable.")
    if flagged:
        print(f"  flagged (strong copyleft, expected set): {', '.join(sorted(flagged)) or '—'}")
    if violations:
        print("\nlicense_scan: VIOLATIONS:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("license_scan: clean — every dependency is permissive/known-licensed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
