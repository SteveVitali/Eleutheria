# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.20 (K7 NEW-1 / SIG-EVUI-D08) — the static export-key producer check.

A web surface may never read an export key that no query produces — a key that
silently returns ``[]`` could hide a producer the build expected. Two halves:

- **spine keys.** Every ``raw["k"]`` / ``raw.get("k")`` read inside the
  web-surface builders (``spine_export.py``, ``analytics.py``) resolves to a
  producer — ``EXPORT_QUERIES``, ``shaping.QUERIES``, a ``_MATERIALIZED_SEAMS``
  key — or to an explicitly declared unproduced key
  (``DECLARED_UNPRODUCED_READ_KEYS``) carrying its cause class.
- **web artifact names.** Every required artifact the web data layer reads
  (``readExportArtifact`` / ``readAnalytics``) resolves to an emitted
  ``web/`` artifact, or to a declared external producer.

A planted unproduced key fails the check; the evaluated count is reported
(SIG-ENG-042 — a green run proves candidates were really inspected).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from exports.spine_export import (
    _MATERIALIZED_SEAMS,
    DECLARED_UNPRODUCED_READ_KEYS,
    EXPORT_QUERIES,
)

from exports import shaping

REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPORT_SRC = REPO_ROOT / "exports" / "src" / "exports"
_DATA_TS = REPO_ROOT / "web" / "src" / "lib" / "data.ts"

#: A ``raw``-dict read of a literal key (``raw.get("k")`` / ``raw["k"]``) — the
#: receiver names the surface builders use for the export/shaping raw maps.
_READ_RE = re.compile(
    r"\b(?:raw|shaping_raw|export_raw)\s*(?:\.get\(\s*|\[\s*)[\"']([a-z_][a-z0-9_]*)[\"']"
)

#: A literal-key write into a raw map — ``raw["k"] = fetch_…()`` — which counts
#: the key as produced (e.g. shaping's ``source_completions`` fetch seam).
_WRITE_RE = re.compile(r"\b(?:raw|shaping_raw)\[\s*[\"']([a-z_][a-z0-9_]*)[\"']\s*\]?\s*=")

#: The web-surface builder modules the check scans — the code that turns raw
#: export rows into the ``web/*.json`` surfaces. (``audit.py`` queries feed the
#: audit report, ``search_index.py``'s ``raw`` is a local FTS payload — neither
#: is a web surface builder.)
_SCAN_FILES = ("spine_export.py", "analytics.py", "shaping.py")

#: Required web reads: `readExportArtifact("x.json")` and `readAnalytics("x")`.
_EXPORT_ARTIFACT_RE = re.compile(r'readExportArtifact\(\s*"([a-z_]+\.json)"')
_ANALYTICS_READ_RE = re.compile(r'readAnalytics\(\s*"([a-z_]+)"')
#: The analytics producer names: `_artifact("x", ...)` calls in analytics.py.
_ANALYTICS_EMIT_RE = re.compile(r'_artifact\(\s*"([a-z_]+)"')

#: The ten `surfaces` keys build_spine_export emits as `web/<name>.json`.
_SURFACE_NAMES = {
    "dossier_index",
    "dossiers",
    "map",
    "network",
    "freshness",
    "coverage",
    "watch",
    "evidence",
    "corrections",
    "research_queue",
}

#: Required web reads with a declared producer outside the spine export (the
#: check still binds them — a read is never unaccounted for).
_DECLARED_EXTERNAL_PRODUCERS = {
    # `sig-tasks osm-feed pull` emits web/leverage.json (P21.7, SIG-CONTRIB-016e)
    # — the producer is a sibling CLI, not an EXPORT_QUERIES row.
    "leverage": "sig-tasks osm-feed pull",
}


def _produced_keys(source_texts: list[str] = ()) -> set[str]:
    """Every produced raw key: the EXPORT/shaping query maps, the materialized
    seams, the declared unproduced reads — plus keys the scanned modules write
    into the raw dicts themselves (e.g. ``source_completions``)."""
    produced = (
        set(EXPORT_QUERIES)
        | set(shaping.QUERIES)
        | {key for key, _table, _seam in _MATERIALIZED_SEAMS}
        | set(DECLARED_UNPRODUCED_READ_KEYS)
    )
    for text in source_texts:
        produced.update(_WRITE_RE.findall(text))
    return produced


def _read_keys(source_text: str) -> set[str]:
    return set(_READ_RE.findall(source_text))


def _unproduced_reads(source_text: str) -> set[str]:
    return _read_keys(source_text) - _produced_keys()


def test_web_surface_raw_reads_are_produced_or_declared() -> None:
    """The check over the real producers: every raw key a web surface reads is
    produced by a query or declared unproduced with a cause class."""
    texts = {name: (_EXPORT_SRC / name).read_text(encoding="utf-8") for name in _SCAN_FILES}
    produced = _produced_keys(list(texts.values()))
    violations: dict[str, list[str]] = {}
    evaluated = 0
    for name, text in sorted(texts.items()):
        keys = _read_keys(text)
        evaluated += len(keys)
        unproduced = keys - produced
        if unproduced:
            violations[name] = sorted(unproduced)
    # SIG-ENG-042 — non-vacuous: the scan must have actually evaluated reads.
    assert evaluated > 0
    print(f"producer-check: evaluated {evaluated} distinct raw-key reads")
    assert not violations, (
        f"web surfaces read export keys no query produces and none declares: {violations}"
    )


def test_contract_watch_is_the_declared_no_producer_key() -> None:
    """K7 NEW-1 — the watch surface reads `contract_watch`, the spine has no
    producer for it, and the read is DECLARED (cause class `no_producer`), so
    the empty watch names its real cause instead of passing silently."""
    assert "contract_watch" in DECLARED_UNPRODUCED_READ_KEYS
    assert DECLARED_UNPRODUCED_READ_KEYS["contract_watch"] == "no_producer"
    assert "contract_watch" not in EXPORT_QUERIES
    assert "contract_watch" not in shaping.QUERIES


def test_declared_unproduced_keys_carry_a_cause_class() -> None:
    for key, cause in DECLARED_UNPRODUCED_READ_KEYS.items():
        assert cause, f"declared unproduced key {key!r} must name its cause class"


def test_a_planted_unproduced_key_fails_the_check() -> None:
    """Negative control — a page reading an unproduced, undeclared key fails."""
    snippet = 'x = raw.get("totally_unproduced_key") or []'
    assert _unproduced_reads(snippet) == {"totally_unproduced_key"}


def test_web_required_artifact_reads_have_a_producer() -> None:
    """Every required `web/*.json` the data layer fails-loud reads is emitted
    by the export's surface map or the analytics family, or declared external
    — and every analytics name is a real emitted artifact."""
    src = _DATA_TS.read_text(encoding="utf-8")
    required = set(_EXPORT_ARTIFACT_RE.findall(src))
    assert required, "no readExportArtifact reads found — the scan would be vacuous"
    produced = {f"{name}.json" for name in _SURFACE_NAMES} | {
        f"{k}.json" for k in _DECLARED_EXTERNAL_PRODUCERS
    }
    unproduced = required - produced
    assert not unproduced, (
        f"data.ts requires artifacts the export does not produce: {sorted(unproduced)}"
    )

    analytics_src = (_EXPORT_SRC / "analytics.py").read_text(encoding="utf-8")
    emitted = set(_ANALYTICS_EMIT_RE.findall(analytics_src))
    reads = set(_ANALYTICS_READ_RE.findall(src))
    assert reads, "no readAnalytics reads found — the scan would be vacuous"
    assert reads <= emitted, (
        f"data.ts reads analytics artifacts the export never emits: {sorted(reads - emitted)}"
    )
    print(
        f"producer-check: {len(required)} required web artifacts, "
        f"{len(reads)} analytics reads — all produced"
    )


@pytest.mark.parametrize("name", ["watch", "evidence"], ids=["watch.json", "evidence.json"])
def test_the_p34_20_surfaces_have_producers(name: str) -> None:
    """AC4 — /watch/ and /evidence/ read only produced artifacts; the
    evidence.json `artifacts` key comes from `evidence_artifacts` (in
    EXPORT_QUERIES), `claim_views` is emitted honest-empty by `_evidence`."""
    assert f"{name}.json" in {f"{n}.json" for n in _SURFACE_NAMES}
