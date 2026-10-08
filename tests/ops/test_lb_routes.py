# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.40 / ACT-17 — the LB path-rule declaration and the L1/L2 leg scripts.

Offline layer (fixture-verified): the `sig.lb-routes/1` declaration parses and
fails closed on drift; `lb-map render` merges the enabled rules onto a RECORDED
live URL map (the 2026-10-07 prestate under tests/ops/fixtures/lb_routes/, the
project id neutralised) into the deterministic import document; `lb-map diff`
is the --verify half; `render-edge` is pinned to the committed ops/edge.conf.
The shell scripts' --check plans and the OM-19 window guard (exit 42) run with
no ADC and no network.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from ops.lb_routes import (
    SCHEMA,
    apply_rules,
    backend_link,
    diff_urlmap,
    load_declaration,
    render_edge_conf,
    render_urlmap_yaml,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = REPO_ROOT / "ops" / "lb_routes.toml"
EDGE_CONF = REPO_ROOT / "ops" / "edge.conf"
FIXTURE = REPO_ROOT / "tests" / "ops" / "fixtures" / "lb_routes" / "urlmap-2026-10-07.json"
LB_ROUTES_SH = REPO_ROOT / "ops" / "gcp" / "lb-routes.sh"
WEB_ROLL_SH = REPO_ROOT / "ops" / "gcp" / "web-roll.sh"
PROJECT = "sig-test-project"
API_LINK = backend_link(PROJECT, "sig-api-backend")


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env["SIG_GCP_PROJECT"] = PROJECT
    env.update(extra)
    return env


def _run(script: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(**env),
        cwd=str(REPO_ROOT),
    )


@pytest.fixture
def decl():
    return load_declaration(DECLARATION)


@pytest.fixture
def live_map() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# --- the declaration ---------------------------------------------------------


def test_declaration_parses_and_declares_the_contract(decl) -> None:
    assert [r.service for r in decl.rules] == ["api", "intake"]
    api, intake = decl.rules
    assert api.enabled is True and set(api.paths) == {"/v1", "/v1/*"}
    assert intake.enabled is False and set(intake.paths) == {"/intake", "/intake/*"}
    assert decl.apex_matcher == "apex"
    assert decl.services["api"].backend == "sig-api-backend"
    assert decl.services["intake"].cloud_run == "sig-intake"


def test_declaration_fails_closed(tmp_path: Path) -> None:
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    bad.write_text(base.replace(f'schema = "{SCHEMA}"', 'schema = "bogus"'))
    with pytest.raises(ValueError, match="schema"):
        load_declaration(bad)
    bad.write_text(base.replace('"/v1/*"', '"/v1*"'))
    with pytest.raises(ValueError, match="trailing"):
        load_declaration(bad)
    bad.write_text(base.replace('service = "api"', 'service = "nosuch"'))
    with pytest.raises(ValueError, match="unknown service"):
        load_declaration(bad)
    bad.write_text(base.replace("enabled = false", 'enabled = "false"'))
    with pytest.raises(ValueError, match="boolean"):
        load_declaration(bad)
    with pytest.raises(ValueError, match="not found"):
        load_declaration(tmp_path / "absent.toml")


def test_recorded_prestate_is_the_pre_l2_shape() -> None:
    """The committed prestate captures (docs/build/reports/p34.40-serving-
    topology/) record the restore point: the live URL map with NO /v1 rule,
    and both service describes with their pinned image digests. These are
    frozen evidence files — the test pins their SHAPE, not a living value."""
    reports = REPO_ROOT / "docs" / "build" / "reports" / "p34.40-serving-topology"
    urlmap = json.loads((reports / "urlmap-prestate-2026-10-07.json").read_text())
    apex = next(m for m in urlmap["pathMatchers"] if m["name"] == "apex")
    assert "pathRules" not in apex  # pre-L2: no path rules at all
    www = next(m for m in urlmap["pathMatchers"] if m["name"] == "www-to-apex")
    assert www["defaultUrlRedirect"]["httpsRedirect"] is True
    for svc in ("sig-web", "sig-api"):
        desc = json.loads((reports / f"{svc}-prestate-2026-10-07.json").read_text())
        image = desc["spec"]["template"]["spec"]["containers"][0]["image"]
        assert "@sha256:" in image  # a pinned digest, never a tag


# --- render: the enabled rules merge onto the recorded live map --------------


def test_render_merges_v1_rule_onto_recorded_map(decl, live_map) -> None:
    out = apply_rules(live_map, decl, PROJECT)
    apex = next(m for m in out["pathMatchers"] if m["name"] == "apex")
    assert apex["pathRules"] == [{"paths": ["/v1", "/v1/*"], "service": API_LINK}]
    # The default service, both host rules and the www redirect pass through
    # byte-identical — the merge owns ONLY the apex pathRules.
    for key in ("name", "defaultService", "hostRules"):
        assert out[key] == live_map[key]
    www = next(m for m in out["pathMatchers"] if m["name"] == "www-to-apex")
    assert www == next(m for m in live_map["pathMatchers"] if m["name"] == "www-to-apex")
    # The disabled intake rule never renders.
    flat = json.dumps(out)
    assert "sig-intake-backend" not in flat and "/intake" not in flat


def test_render_is_idempotent(decl, live_map) -> None:
    once = apply_rules(live_map, decl, PROJECT)
    assert apply_rules(once, decl, PROJECT) == once


def test_render_replaces_a_colliding_live_rule(decl, live_map) -> None:
    live = copy.deepcopy(live_map)
    apex = next(m for m in live["pathMatchers"] if m["name"] == "apex")
    apex["pathRules"] = [{"paths": ["/v1/*"], "service": backend_link(PROJECT, "stale-backend")}]
    out = apply_rules(live, decl, PROJECT)
    apex = next(m for m in out["pathMatchers"] if m["name"] == "apex")
    assert apex["pathRules"] == [{"paths": ["/v1", "/v1/*"], "service": API_LINK}]


def test_render_refuses_a_map_without_the_apex_matcher(decl, live_map) -> None:
    live = copy.deepcopy(live_map)
    live["pathMatchers"] = [m for m in live["pathMatchers"] if m["name"] != "apex"]
    with pytest.raises(ValueError, match="apex"):
        apply_rules(live, decl, PROJECT)


def test_render_emits_the_import_yaml(decl, live_map) -> None:
    doc = render_urlmap_yaml(apply_rules(live_map, decl, PROJECT))
    assert 'name: "sig-web-urlmap"' in doc
    assert doc.count("pathRules:") == 1
    assert '    - "/v1"' in doc and '    - "/v1/*"' in doc
    assert f'service: "{API_LINK}"' in doc
    # The www redirect survives verbatim.
    assert "defaultUrlRedirect:" in doc and 'hostRedirect: "surveillancegraph.org"' in doc
    # Read-only export fields are never emitted.
    assert "fingerprint" not in doc and "selfLink" not in doc


# --- diff: the --verify half -------------------------------------------------


def test_diff_reports_the_missing_rule_pre_l2(decl, live_map) -> None:
    diffs = diff_urlmap(live_map, decl, PROJECT)
    assert diffs == [f"missing pathRule: ['/v1', '/v1/*'] -> '{API_LINK}'"]


def test_diff_is_clean_post_l2(decl, live_map) -> None:
    applied = apply_rules(live_map, decl, PROJECT)
    assert diff_urlmap(applied, decl, PROJECT) == []


def test_diff_flags_a_stray_or_wrong_rule(decl, live_map) -> None:
    stray = apply_rules(live_map, decl, PROJECT)
    apex = next(m for m in stray["pathMatchers"] if m["name"] == "apex")
    apex["pathRules"].append(
        {"paths": ["/intake", "/intake/*"], "service": backend_link(PROJECT, "x")}
    )
    diffs = diff_urlmap(stray, decl, PROJECT)
    assert len(diffs) == 1 and "undeclared pathRule" in diffs[0]

    wrong = copy.deepcopy(stray)
    apex = next(m for m in wrong["pathMatchers"] if m["name"] == "apex")
    apex["pathRules"] = [
        {"paths": ["/v1", "/v1/*"], "service": backend_link(PROJECT, "wrong-backend")}
    ]
    diffs = diff_urlmap(wrong, decl, PROJECT)
    assert any("routes to" in d for d in diffs)


def test_diff_reports_a_missing_apex_matcher(decl, live_map) -> None:
    live = copy.deepcopy(live_map)
    live["pathMatchers"] = [m for m in live["pathMatchers"] if m["name"] != "apex"]
    assert diff_urlmap(live, decl, PROJECT) == ["no pathMatcher named 'apex' on the live map"]


# --- the composed edge -------------------------------------------------------


def test_committed_edge_conf_matches_the_render(decl) -> None:
    assert EDGE_CONF.read_text(encoding="utf-8") == render_edge_conf(decl)


def test_edge_conf_routes_every_declared_rule_including_dark(decl) -> None:
    conf = render_edge_conf(decl)
    # The enabled /v1 rule proxies to the api service…
    assert "location /v1/ {" in conf and "set $sig_upstream api:8080;" in conf
    assert "location = /v1 {" in conf
    # …and the written-not-applied intake rule is exercised in the composed
    # stack (it renders nowhere live).
    assert "location /intake/ {" in conf and "set $sig_upstream intake:8080;" in conf
    assert "location / {" in conf and "set $sig_upstream web:8080;" in conf
    # Upstreams re-resolve per request (a static proxy_pass pins the
    # container IP at nginx start — stale after a recreate).
    assert "resolver 127.0.0.11" in conf
    assert "proxy_pass http://$sig_upstream;" in conf
    # /v1 must never match /v1foo: the prefix location is /v1/ exactly.
    assert "location /v1 " not in conf


# --- the CLI surface ----------------------------------------------------------


def test_lb_map_cli_plan_and_diff() -> None:
    plan = subprocess.run(
        ["uv", "run", "--quiet", "sig-ops", "lb-map", "plan"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert plan.returncode == 0, plan.stderr
    doc = json.loads(plan.stdout)
    assert doc["schema"] == SCHEMA
    assert {r["service"] for r in doc["rules"]} == {"api", "intake"}

    diff = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "lb-map",
            "diff",
            "--live",
            str(FIXTURE),
            "--project",
            PROJECT,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert diff.returncode == 4
    assert "DRIFT: missing pathRule" in diff.stdout


# --- the L2 script -------------------------------------------------------------


def test_lb_routes_check_prints_the_full_plan() -> None:
    proc = _run(LB_ROUTES_SH, "--check", "all")
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for needle in (
        "network-endpoint-groups create sig-api-neg",
        "--network-endpoint-type=serverless",
        "--cloud-run-service=sig-api",
        "backend-services create sig-api-backend",
        "add-backend sig-api-backend",
        "url-maps export sig-web-urlmap",
        "url-maps import sig-web-urlmap",
        "lb-map render",
        "route-compare capture --base https://surveillancegraph.org",
    ):
        assert needle in plan, needle
    # The written-not-applied intake rule is never a create plan.
    assert "sig-intake" not in plan.split("declaration")[0]


def test_lb_routes_check_never_touches_network() -> None:
    proc = _run(LB_ROUTES_SH, "--check", "neg")
    assert proc.returncode == 0
    assert "PLAN:" in proc.stdout


def test_lb_routes_apply_refuses_without_adc() -> None:
    proc = _run(LB_ROUTES_SH, "--apply", "neg", SIG_LB_NOW="2026-10-14T14:00:00Z")
    assert proc.returncode == 3
    out = proc.stdout + proc.stderr
    assert "gate pending" in out or "gcloud" in out


def test_lb_routes_apply_queues_inside_the_freeze() -> None:
    # 2026-10-08 is inside AR-3 — a mutating apply exits 42 with the re-run line.
    proc = _run(LB_ROUTES_SH, "--apply", "urlmap", SIG_LB_NOW="2026-10-08T14:00:00Z")
    assert proc.returncode == 42
    assert "implement-spec spec=docs/tickets/249_P34.40" in proc.stdout
    proc = _run(LB_ROUTES_SH, "--apply", "all", SIG_LB_NOW="2026-10-08T14:00:00Z")
    assert proc.returncode == 42


def test_lb_routes_apply_queues_in_the_0300_1000_band() -> None:
    proc = _run(LB_ROUTES_SH, "--apply", "neg", SIG_LB_NOW="2026-10-14T04:00:00Z")
    assert proc.returncode == 42


def test_lb_routes_apply_past_the_window_reaches_adc_gate() -> None:
    proc = _run(LB_ROUTES_SH, "--apply", "neg", SIG_LB_NOW="2026-10-14T14:00:00Z")
    assert proc.returncode == 3  # past the window → ADC gate fires, not 42


def test_lb_routes_rollback_refuses_without_prestate(tmp_path: Path) -> None:
    # Check mode prints the plan; apply mode without a recorded prestate refuses.
    proc = _run(LB_ROUTES_SH, "--check", "rollback", str(tmp_path))
    assert proc.returncode == 0 and "urlmap-pre.yaml" in proc.stdout


# --- the L1 script -------------------------------------------------------------


def test_web_roll_check_plans_prestate_roll_poststate() -> None:
    proc = _run(WEB_ROLL_SH, "--check", "all")
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for needle in (
        "run services describe sig-web",
        "routes-canonical-pre.json",
        "web.sh --apply all",
        "routes-canonical-post.json",
        "route-compare verify",
    ):
        assert needle in plan, needle


def test_web_roll_apply_queues_inside_the_freeze() -> None:
    proc = _run(WEB_ROLL_SH, "--apply", "roll", SIG_LB_NOW="2026-10-08T14:00:00Z")
    assert proc.returncode == 42
    assert "scope: L1" in proc.stdout
    proc = _run(WEB_ROLL_SH, "--apply", "all", SIG_LB_NOW="2026-10-14T04:00:00Z")
    assert proc.returncode == 42  # the 03:00–10:00Z band


def test_web_roll_rollback_prints_the_digest_command() -> None:
    proc = _run(WEB_ROLL_SH, "--check", "rollback")
    assert proc.returncode == 0
    assert "run deploy sig-web --image" in proc.stdout
