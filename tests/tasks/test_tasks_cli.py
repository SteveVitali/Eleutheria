# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""`sig-tasks` CLI: contribution-back live edge (P21.7).

Covers the ticket ACs: ``maproulette push`` exits 3 with the OE-registration reason
while registered=false; ``maproulette push --dry-run`` prints the challenge JSON when
registered; ``osm-feed pull`` reports the attributed count.
"""

from __future__ import annotations

import json
from pathlib import Path

from tasks.cli import main

from tasks import contribution as C


def test_maproulette_push_exits_3_while_unregistered(capsys) -> None:
    # ops/config.toml ships registered=false (HG-08) → the real gate refuses.
    code = main(["maproulette", "push", "--jurisdiction", "okc"])
    assert code == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "registered=false" in out or "not registered" in out


def test_maproulette_push_prints_challenge_json_when_registered(capsys, monkeypatch) -> None:
    monkeypatch.setattr(C, "contribution_registered", lambda: True)
    # cli imported the symbol into its namespace; patch there too.
    import tasks.cli as cli

    monkeypatch.setattr(cli, "contribution_registered", lambda: True)
    code = main(["maproulette", "push", "--jurisdiction", "okc"])
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out.split("# dry-run")[0])
    assert payload["dry_run"] is True
    assert payload["payload"]["cooperativeType"] == "tags"
    # The sensitive-tier demo task is excluded from the pushed payload (RISK-P21-12).
    assert payload["payload"]["excluded_sensitive_task_count"] == 1
    assert len(payload["payload"]["tasks"]) == 2


def test_maproulette_pull_dry_run(capsys) -> None:
    code = main(["maproulette", "pull", "--challenge", "77"])
    assert code == 0
    out = capsys.readouterr().out
    assert '"dry_run": true' in out
    assert "/challenge/77/" in out


def test_osm_feed_pull_reports_attributions(capsys) -> None:
    code = main(["osm-feed", "pull"])
    assert code == 0
    out = capsys.readouterr().out
    assert "newly attributed changesets this run: 4" in out
    assert "accepted operator-attributions: 3" in out


def test_osm_feed_pull_writes_export_json(capsys, tmp_path: Path) -> None:
    code = main(["osm-feed", "pull", "--out", str(tmp_path)])
    assert code == 0
    written = tmp_path / "web" / "leverage.json"
    assert written.exists()
    metric = json.loads(written.read_text())
    assert metric["accepted_operator_attributions"] == 3
    assert metric["hashtag"] == C.CHANGESET_HASHTAG


def test_contribution_registered_fails_closed(tmp_path: Path) -> None:
    # Absent file → False (fail closed).
    assert C.contribution_registered(tmp_path / "nope.toml") is False
    # Explicit false / true.
    cfg = tmp_path / "config.toml"
    cfg.write_text("[tasks.contribution]\nregistered = false\n")
    assert C.contribution_registered(cfg) is False
    cfg.write_text("[tasks.contribution]\nregistered = true\n")
    assert C.contribution_registered(cfg) is True


def test_shipped_ops_config_is_unregistered() -> None:
    # The committed ops/config.toml must keep the push gated (HG-08).
    assert C.contribution_registered() is False
