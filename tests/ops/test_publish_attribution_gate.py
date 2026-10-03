# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21a — the publish-time attribution gate (E2-12 / ADR-194).

Two surfaces under test: (1) ``assert_attribution_complete`` — the shared scan
applied at export preparation (``run_public_prepare``) and at ``publish-web``
— refuses any public ``*.jsonl`` row whose ``_rights`` declares
``attribution_required`` with an empty credit; (2) the gate runs BEFORE any
sync/write, so a defected export tree refuses the publish outright.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops import publish as P


def _row(source: str, *, required: bool = True, attribution: str = "") -> str:
    return json.dumps(
        {
            "entity_id": "e1",
            "source_id": source,
            "_rights": {
                "source_id": source,
                "license": "CC-BY-4.0",
                "attribution_required": required,
                "attribution": attribution,
                "terms_url": "https://example/terms",
            },
        }
    )


def _public_tree(root: Path, rows: list[str]) -> Path:
    comp = root / "sig_graph"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "sites.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return root


def test_gate_refuses_an_empty_attribution_row(tmp_path: Path) -> None:
    tree = _public_tree(tmp_path / "public", [_row("defected_src")])
    violations = P.attribution_violations(tree)
    assert violations and "defected_src" in violations[0]
    with pytest.raises(P.AttributionLeak, match="E2-12"):
        P.assert_attribution_complete(tree)


def test_gate_refuses_whitespace_only_attribution(tmp_path: Path) -> None:
    tree = _public_tree(tmp_path / "public", [_row("s", attribution="   ")])
    with pytest.raises(P.AttributionLeak):
        P.assert_attribution_complete(tree)


def test_gate_passes_populated_and_unrequired_rows(tmp_path: Path) -> None:
    tree = _public_tree(
        tmp_path / "public",
        [
            _row("src_a", attribution="Council A open data"),
            _row("src_b", required=False),  # CC0-style: no credit required
            json.dumps({"plain": "row without a _rights block"}),
        ],
    )
    assert P.attribution_violations(tree) == []
    P.assert_attribution_complete(tree)  # no raise


def test_gate_identifies_file_and_line(tmp_path: Path) -> None:
    tree = _public_tree(tmp_path / "public", [_row("ok", attribution="ok"), _row("bad")])
    violations = P.attribution_violations(tree)
    assert violations[0].startswith("sig_graph/sites.jsonl:2")


def test_publish_web_refuses_a_defected_export_tree_before_any_sync(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    # a minimal allow-list so the built tree passes the earlier gates and the
    # attribution gate is what actually fires
    allowlist = tmp_path / "routes.toml"
    allowlist.write_text('[allowlist]\ntop_level = ["index.html"]\n', encoding="utf-8")
    export_tree = _public_tree(tmp_path / "export", [_row("defected_src")])
    with pytest.raises(P.AttributionLeak):
        P.run_publish_web(
            dist=dist,
            apply=False,
            export_tree=export_tree,
            allowlist_path=allowlist,
        )
    # …and a clean export tree publishes its plan (dry run — no writes)
    clean_tree = _public_tree(tmp_path / "export2", [_row("ok", attribution="Council A")])
    result = P.run_publish_web(
        dist=dist,
        apply=False,
        export_tree=clean_tree,
        allowlist_path=allowlist,
    )
    assert result.applied is False


def test_licence_index_carries_publication_basis_and_honest_license_urls(
    tmp_path: Path,
) -> None:
    manifest = {
        "release_id": "sig-2026-10-03-abcd1234",
        "artifacts": [
            {"path": "sig_graph/claims.csv", "compartment": "sig_graph", "license": "CC-BY-4.0"},
            {
                "path": "public_record/sites.csv",
                "compartment": "public_record",
                "license": "LicenseRef-PublicRecord-FactualCompilation",
            },
            {
                "path": "derived_facts/sites.csv",
                "compartment": "derived_facts",
                "license": "LicenseRef-DerivedFacts-Citations",
            },
        ],
    }
    root = tmp_path / "public"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    P.write_licence_index(root)
    doc = json.loads((root / "LICENCES.json").read_text(encoding="utf-8"))
    assert doc["publication_basis"].startswith("Published on the operator's own determination")
    assert "cleared by counsel" in doc["publication_basis"]
    by_comp = {c["compartment"]: c for c in doc["compartments"]}
    assert by_comp["sig_graph"]["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    # the Feist basis row declares a license_url fact; the internal
    # LicenseRef-DerivedFacts basis has no canonical upstream — null, never a
    # fabricated spdx.org link (E2-12).
    assert by_comp["public_record"]["license_url"] == (
        "https://supreme.justia.com/cases/federal/us/499/340/"
    )
    assert by_comp["derived_facts"]["license_url"] is None
