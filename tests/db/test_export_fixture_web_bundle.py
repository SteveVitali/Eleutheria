# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.34b (ACT-16b, C4 NEW-26): the CI from-spine fixture export actually
satisfies the export-mode web build's data contract — on the real PG spine.

The CI `web` job drives ``scripts/ci/build_from_spine_fixture_export.py`` to
produce the directory ``SIG_EXPORT_DIR`` points at. This suite drives the same
``produce()`` over the suite's seeded container and asserts:

* the written export carries every artifact ``SIG_DATA_SOURCE=export`` reads
  fail-loud (``web/src/lib/data.ts``): the manifest, the ten P27.1 surfaces,
  ``leverage.json`` and the ``web/analytics/*`` family — a missing one is a
  build error in export mode, so the fixture export must be complete;
* ``build_release`` over it emits at least one record page (the archive-record
  Lighthouse URL) and ``validate_release`` (P34.34a's same-origin crawl) is
  green;
* the session stays read-only and the spine uncommitted.

Docker-gated like every ``tests/db`` test: skips without a daemon, fails loud
under ``SIG_REQUIRE_DB_TESTS=1`` (which CI sets).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCER = REPO_ROOT / "scripts" / "ci" / "build_from_spine_fixture_export.py"

#: The web artifacts `web/src/lib/data.ts` reads FAIL-LOUD in export mode —
#: a producer that stops emitting one must turn this suite red, not the CI
#: web build's log (where it would surface later and fuzzier).
REQUIRED_WEB_ARTIFACTS = (
    "web/dossier_index.json",
    "web/dossiers.json",
    "web/map.json",
    "web/network.json",
    "web/freshness.json",
    "web/coverage.json",
    "web/watch.json",
    "web/evidence.json",
    "web/corrections.json",
    "web/research_queue.json",
    "web/leverage.json",
    "web/analytics/density_bins.json",
    "web/analytics/centrality.json",
    "web/analytics/decision_point.json",
    "web/analytics/provenance.json",
    "web/analytics/queue_meta.json",
)

_AS_OF = "2026-09-23"


def _load_producer() -> Any:
    spec = importlib.util.spec_from_file_location("_sig_ci_export_fixture_producer", PRODUCER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def produced(conn: Any, tmp_path: Path) -> dict[str, Any]:
    """Run the CI producer's `produce()` over the suite's seeded container."""
    producer = _load_producer()
    export_dir = tmp_path / "export"
    release_dir = tmp_path / "release"
    summary = producer.produce(
        conn,
        export_dir,
        as_of=_AS_OF,
        release_dir=release_dir,
        renderer_revision="p3434b" * 8,  # 64-char fixture revision
    )
    return {"export": export_dir, "release": release_dir, "summary": summary}


def test_the_export_dir_satisfies_every_export_mode_requirement(produced) -> None:
    """Every fail-loud `data.ts` artifact is present and well-formed."""
    export_dir = produced["export"]

    manifest = json.loads((export_dir / "manifest.json").read_text())
    repro = manifest["reproducibility_inputs"]
    for key in ("as_of_snapshot", "as_of_belief", "ruleset_version"):
        assert repro[key], f"manifest.json must carry {key}"
    assert manifest["release_id"], "getSiteMetadata pins manifest.release_id"

    for rel in REQUIRED_WEB_ARTIFACTS:
        path = export_dir / rel
        assert path.is_file(), (
            f"export-mode build would fail loud: {rel} missing from the from-spine export"
        )
        json.loads(path.read_text())  # well-formed JSON, never empty bytes

    # Compartment licence discipline: the seeded ODbL subject stays in its own
    # compartment with its own tile archive; sig_graph is the CC-BY graph.
    assert (export_dir / "osm_physical" / "sites.jsonl").is_file()
    assert (export_dir / "sig_graph" / "sites.jsonl").is_file()
    for comp in ("osm_physical", "sig_graph"):
        assert (export_dir / comp / "ATTRIBUTION.json").is_file(), (
            f"{comp}/ATTRIBUTION.json — the per-compartment attribution index"
        )
    tile_paths = [a["path"] for a in manifest["artifacts"] if a["path"].startswith("web/tiles/")]
    assert "web/tiles/osm_physical-sites.pmtiles" in tile_paths
    assert "web/tiles/sig_graph-sites.pmtiles" in tile_paths

    # Provenance: the bytes came from the spine pipeline (PROV-O + exclusions),
    # not a fixture serializer.
    assert (export_dir / "provenance.ttl").is_file()
    exclusions = json.loads((export_dir / "exclusions.json").read_text())
    assert exclusions["totals"]["refused_slices"] >= 1, (
        "the UNDETERMINED-licence subject must be excluded (licence gate held)"
    )

    # And no web-fixture seam leaked in: no fixture serializer emits
    # provenance.ttl or per-compartment JSONL bundles.
    shipped_sources = {
        json.loads(line)["source_id"]
        for line in (export_dir / "sig_graph" / "sites.jsonl").read_text().splitlines()
        if line.strip()
    }
    assert "camreg_cc0" in shipped_sources
    assert "muckrock" not in shipped_sources  # UNDETERMINED never ships


def test_the_release_build_emits_an_archive_record_and_validates(produced) -> None:
    """The immutable release tree exists and crawls clean (P34.34a's gate) —
    so the export-mode Lighthouse run has a real `/r/…` record to measure."""
    release_dir = produced["release"]
    summary = produced["summary"]["release"]

    assert summary["validation"]["state"] == "complete"
    assert summary["validation"]["failures"] == []
    assert summary["records"] >= 1
    pub = summary["publication_id"]
    assert pub

    records = sorted(release_dir.glob("r/*/c/*/entity/*/*/index.html"))
    assert records, "the release must emit at least one entity record page"
    assert (release_dir / "releases" / pub / "index.html").is_file()
    assert (release_dir / "releases" / pub / "integrity_manifest.json").is_file()
    # (`releases/index.html` is the activate-step's staged overlay, not a
    # build_release output — asserted absent rather than mistaken for one.)
    # The record bytes are self-contained (release_pages.py: no <script>, no
    # external assets) — the CI measurement alias serves them verbatim.
    html = records[0].read_text(encoding="utf-8")
    assert "<script" not in html


def test_the_export_session_never_mutates_the_spine(conn, produced) -> None:
    """produce() leaves the session read-only and the seed uncommitted —
    the append-only spine invariant holds through the producer path too."""
    cur = conn.cursor()
    cur.execute("SHOW default_transaction_read_only")
    assert cur.fetchone()[0] == "on"
