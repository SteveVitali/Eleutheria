# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The canonical-origin LB path declaration (P34.40 / ACT-17, G3 §4.3).

``ops/lb_routes.toml`` is the committed record of which path prefixes the
external HTTPS load balancer routes OFF the default ``sig-web`` backend onto
another Cloud Run service — one origin, nginx never proxying (G3 §4.3).
This module is the pure engine behind it:

* ``load_declaration`` — parse + validate the TOML (fail-closed).
* ``apply_rules`` — merge the *enabled* rules onto a live URL map (the
  `gcloud compute url-maps describe --format json` shape), producing the map
  an ``url-maps import`` writes. Everything the declaration does not own —
  the default service, host rules, the www→apex redirect — passes through
  byte-identical.
* ``diff_urlmap`` — the ``--verify`` half: every way the live map can
  disagree with the declaration, listed.
* ``render_edge_conf`` — the composed-stack stand-in: an nginx edge that
  routes exactly the declared rules (INCLUDING the dark ``enabled = false``
  ones — the composed stack is where the not-applied intake route is
  exercised) onto the compose services.

Offline only: nothing here shells out to gcloud; the shell wrapper
(``ops/gcp/lb-routes.sh``) owns every mutation and stays window-gated.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

SCHEMA = "sig.lb-routes/1"

DEFAULT_DECLARATION = Path(__file__).resolve().parents[2] / "lb_routes.toml"


@dataclass(frozen=True)
class LBService:
    """One backend the URL map can route to (a Cloud Run service behind a
    serverless NEG + EXTERNAL_MANAGED backend service)."""

    cloud_run: str
    neg: str
    backend: str
    edge_upstream: str


@dataclass(frozen=True)
class LBRule:
    """A URL-map ``pathRules`` entry: ``paths`` (exact or ``/*`` prefixes)
    → ``service``. ``enabled = false`` means written-not-applied (the rule
    renders into the composed edge but never into the import document)."""

    paths: tuple[str, ...]
    service: str
    enabled: bool


@dataclass(frozen=True)
class LBDeclaration:
    apex_matcher: str
    rules: tuple[LBRule, ...]
    services: dict[str, LBService]
    default_edge_upstream: str


def _fail(msg: str) -> NoReturn:
    raise ValueError(f"lb_routes declaration: {msg}")


def _check_path(path: object) -> str:
    """One URL-map path: ``/x`` exact or a ``/x/*`` prefix — nothing else."""
    if not isinstance(path, str) or not path.startswith("/"):
        _fail(f"path {path!r} must be an absolute string")
    if "*" in path and not path.endswith("/*"):
        _fail(f"path {path!r} may only carry a trailing /*")
    return path


def load_declaration(path: str | Path | None = None) -> LBDeclaration:
    """Parse + validate ``ops/lb_routes.toml`` — fail-closed on any drift."""
    p = Path(path) if path else DEFAULT_DECLARATION
    if not p.is_file():
        _fail(f"{p} not found — the path declaration is required")
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    if raw.get("schema") != SCHEMA:
        _fail(f"schema must be {SCHEMA!r}, got {raw.get('schema')!r}")
    apex = raw.get("apex_matcher")
    if not isinstance(apex, str) or not apex:
        _fail("apex_matcher must be a non-empty string")
    services: dict[str, LBService] = {}
    for name, svc in (raw.get("service") or {}).items():
        for field in ("cloud_run", "neg", "backend", "edge_upstream"):
            if not isinstance(svc.get(field), str) or not svc[field]:
                _fail(f"service.{name}.{field} must be a non-empty string")
        services[name] = LBService(
            cloud_run=svc["cloud_run"],
            neg=svc["neg"],
            backend=svc["backend"],
            edge_upstream=svc["edge_upstream"],
        )
    rules: list[LBRule] = []
    seen_paths: set[str] = set()
    for i, r in enumerate(raw.get("rule") or []):
        paths = tuple(_check_path(x) for x in r.get("paths") or ())
        if not paths:
            _fail(f"rule {i} carries no paths")
        for x in paths:
            if x in seen_paths:
                _fail(f"path {x!r} declared twice")
            seen_paths.add(x)
        service = r.get("service")
        if service not in services:
            _fail(f"rule {i} names unknown service {service!r}")
        if not isinstance(r.get("enabled"), bool):
            _fail(f"rule {i}.enabled must be a boolean")
        rules.append(LBRule(paths=paths, service=service, enabled=r["enabled"]))
    edge = raw.get("edge") or {}
    default_upstream = edge.get("default_upstream", "web:8080")
    if not isinstance(default_upstream, str) or not default_upstream:
        _fail("edge.default_upstream must be a non-empty string")
    return LBDeclaration(
        apex_matcher=apex,
        rules=tuple(rules),
        services=services,
        default_edge_upstream=default_upstream,
    )


def backend_link(project: str, backend: str) -> str:
    """The global backendService self-link shape url-maps import expects."""
    return (
        f"https://www.googleapis.com/compute/v1/projects/{project}/global/backendServices/{backend}"
    )


def _declared_paths(decl: LBDeclaration) -> set[str]:
    return {p for rule in decl.rules if rule.enabled for p in rule.paths}


def apply_rules(live_map: dict[str, Any], decl: LBDeclaration, project: str) -> dict[str, Any]:
    """The URL map ``url-maps import`` should write: the live map with the
    enabled declared rules applied to the apex path matcher.

    Idempotent: an already-applied map renders to itself. Every part of the
    map the declaration does not own (defaultService, hostRules, other
    matchers, the www redirect) passes through untouched.
    """
    out = copy.deepcopy(live_map)
    matchers = out.get("pathMatchers") or []
    apex: dict[str, Any] | None = None
    for m in matchers:
        if m.get("name") == decl.apex_matcher:
            apex = m
            break
    if apex is None:
        _fail(f"live URL map has no pathMatcher named {decl.apex_matcher!r}")
    owned = _declared_paths(decl)
    # Keep live rules that declare no owned path (fail closed on a collision:
    # a live rule routing a declared path to something else is replaced, and
    # diff_urlmap reports it).
    kept = [r for r in (apex.get("pathRules") or []) if not (set(r.get("paths") or ()) & owned)]
    merged = list(kept)
    for rule in decl.rules:
        if not rule.enabled:
            continue
        merged.append(
            {
                "paths": list(rule.paths),
                "service": backend_link(project, decl.services[rule.service].backend),
            }
        )
    if merged:
        apex["pathRules"] = merged
    else:
        apex.pop("pathRules", None)
    return out


def diff_urlmap(live_map: dict[str, Any], decl: LBDeclaration, project: str) -> list[str]:
    """The ``--verify`` diff: every way the live apex matcher disagrees with
    the declaration. Empty list = the live map carries exactly the declared
    enabled rules (and nothing the declaration owns points elsewhere).
    """
    diffs: list[str] = []
    apex: dict[str, Any] | None = None
    for m in live_map.get("pathMatchers") or []:
        if m.get("name") == decl.apex_matcher:
            apex = m
            break
    if apex is None:
        return [f"no pathMatcher named {decl.apex_matcher!r} on the live map"]
    owned = _declared_paths(decl)
    live_rules = apex.get("pathRules") or []
    for rule in live_rules:
        paths = set(rule.get("paths") or ())
        svc = rule.get("service", "")
        declared_hit = paths & owned
        if declared_hit:
            expected = {r for r in decl.rules if r.enabled and set(r.paths) & declared_hit}
            want = {backend_link(project, decl.services[r.service].backend) for r in expected}
            if svc not in want or not any(paths == set(r.paths) for r in expected):
                diffs.append(
                    f"pathRule {sorted(paths)} routes to {svc!r}; "
                    f"the declaration expects {sorted(want)} on "
                    f"{sorted(p for r in expected for p in r.paths)}"
                )
        else:
            diffs.append(
                f"undeclared pathRule on matcher {decl.apex_matcher!r}: {sorted(paths)} -> {svc!r}"
            )
    live_pathsets = {tuple(sorted(r.get("paths") or [])) for r in live_rules}
    for rule in decl.rules:
        if rule.enabled and tuple(sorted(rule.paths)) not in live_pathsets:
            diffs.append(
                f"missing pathRule: {sorted(rule.paths)} -> "
                f"{backend_link(project, decl.services[rule.service].backend)!r}"
            )
    return diffs


# --- deterministic YAML emission (url-maps import shape) ---------------------


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _redirect_lines(key: str, redirect: dict[str, Any], indent: str) -> list[str]:
    lines = [f"{indent}{key}:"]
    for k in ("hostRedirect", "redirectResponseCode", "httpsRedirect", "stripQuery"):
        if k in redirect:
            v = redirect[k]
            lines.append(f"{indent}  {k}: {str(v).lower() if isinstance(v, bool) else _q(str(v))}")
    return lines


def render_urlmap_yaml(url_map: dict[str, Any]) -> str:
    """Emit the deterministic ``url-maps import`` document — only the
    semantic fields (never read-only export fields like fingerprint)."""
    lines = [f"name: {_q(url_map['name'])}"]
    if "defaultService" in url_map:
        lines.append(f"defaultService: {_q(url_map['defaultService'])}")
    if "defaultUrlRedirect" in url_map:
        lines += _redirect_lines("defaultUrlRedirect", url_map["defaultUrlRedirect"], "")
    if url_map.get("hostRules"):
        lines.append("hostRules:")
        for hr in url_map["hostRules"]:
            lines.append("- hosts:")
            for h in hr["hosts"]:
                lines.append(f"  - {_q(h)}")
            lines.append(f"  pathMatcher: {_q(hr['pathMatcher'])}")
    if url_map.get("pathMatchers"):
        lines.append("pathMatchers:")
        for pm in url_map["pathMatchers"]:
            lines.append(f"- name: {_q(pm['name'])}")
            if "defaultService" in pm:
                lines.append(f"  defaultService: {_q(pm['defaultService'])}")
            if "defaultUrlRedirect" in pm:
                lines += _redirect_lines("defaultUrlRedirect", pm["defaultUrlRedirect"], "  ")
            if pm.get("pathRules"):
                lines.append("  pathRules:")
                for pr in pm["pathRules"]:
                    lines.append("  - paths:")
                    for pth in pr["paths"]:
                        lines.append(f"    - {_q(pth)}")
                    lines.append(f"    service: {_q(pr['service'])}")
    return "\n".join(lines) + "\n"


# --- the composed edge (the LB stand-in) -------------------------------------


def render_edge_conf(decl: LBDeclaration) -> str:
    """The nginx conf for the compose ``edge`` service — a byte-deterministic
    proxy that routes EXACTLY the declared rules (dark ones included: the
    composed stack is where the written-not-applied intake rule is
    exercised) and everything else to the web stand-in.

    ``location = /x`` mirrors a ``/x`` path entry; ``location /x/`` mirrors
    ``/x/*`` — nginx's longest-prefix + exact-match semantics stand in for
    the URL map's pathRules match.

    Upstreams go through Docker's embedded DNS (``127.0.0.11``) via a
    variable ``proxy_pass``: a static ``proxy_pass http://svc:8080`` is
    resolved once at nginx start, so a recreated upstream's new IP leaves
    the edge proxying into a refused connection for the rest of its life.
    The variable form re-resolves at request time (``valid=10s`` cache),
    which is also why the edge does not need upstream health ordering.
    """
    lines = [
        "# SPDX-License-Identifier: Apache-2.0",
        "# GENERATED by `sig-ops lb-map render-edge` from ops/lb_routes.toml —",
        "# do not hand-edit (the drift check is tests/ops/test_lb_routes.py).",
        "# The composed stand-in for the canonical origin's LB path rules",
        "# (P34.40 / G3 §4.3): declared rules proxy to their service; every",
        "# other route falls through to the sig-web container.",
        "",
        "worker_processes 1;",
        "error_log /dev/stderr warn;",
        "pid /tmp/sig-edge.pid;",
        "",
        "events {",
        "    worker_connections 256;",
        "}",
        "",
        "http {",
        "    server {",
        "        listen 8080;",
        "        server_name _;",
        "",
        "        # Docker's embedded DNS — re-resolve upstreams at request time.",
        "        resolver 127.0.0.11 valid=10s ipv6=off;",
        "",
    ]
    for rule in decl.rules:
        svc = decl.services[rule.service]
        note = "" if rule.enabled else "  # written-not-applied live"
        for path in rule.paths:
            loc = f"= {path}" if not path.endswith("/*") else path[:-1]
            lines += [
                f"        location {loc} {{{note}".rstrip(),
                f"            set $sig_upstream {svc.edge_upstream};",
                # HTTP/1.1 upstream — required inside the location: at server
                # level it does not apply to the variable proxy_pass form, and
                # the web nginx's gzip only applies to HTTP/1.1+ requests.
                "            proxy_http_version 1.1;",
                "            proxy_set_header Host $host;",
                "            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
                "            proxy_set_header X-Forwarded-Proto https;",
                "            proxy_pass http://$sig_upstream;",
                "        }",
                "",
            ]
    lines += [
        "        location / {",
        f"            set $sig_upstream {decl.default_edge_upstream};",
        "            proxy_http_version 1.1;",
        "            proxy_set_header Host $host;",
        "            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "            proxy_set_header X-Forwarded-Proto https;",
        "            proxy_pass http://$sig_upstream;",
        "        }",
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)


# --- CLI (the `sig-ops lb-map` verb surface) ---------------------------------


def _load_live(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops lb-map",
        description="P34.40 / G3 §4.3: the canonical-origin LB path-rule "
        "declaration — plan, render the import document, diff the live map, "
        "render the composed edge. Offline; lb-routes.sh owns mutations.",
    )
    sub = parser.add_subparsers(dest="map_command", required=True)

    plan = sub.add_parser("plan", help="print the declaration (offline)")
    plan.add_argument("--declaration", default=None)

    rnd = sub.add_parser("render", help="merge the enabled rules onto a live URL map → import YAML")
    rnd.add_argument("--live", required=True, help="url-maps describe --format json")
    rnd.add_argument("--project", required=True)
    rnd.add_argument("--declaration", default=None)
    rnd.add_argument("--out", default=None, help="write YAML here (default stdout)")

    diff = sub.add_parser("diff", help="verify: live map vs declaration (exit 4 on drift)")
    diff.add_argument("--live", required=True, help="url-maps describe --format json")
    diff.add_argument("--project", required=True)
    diff.add_argument("--declaration", default=None)

    edge = sub.add_parser("render-edge", help="emit the composed edge nginx conf (ops/edge.conf)")
    edge.add_argument("--declaration", default=None)
    edge.add_argument("--out", default=None, help="write conf here (default stdout)")

    args = parser.parse_args(argv)
    decl = load_declaration(args.declaration)

    if args.map_command == "plan":
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "apex_matcher": decl.apex_matcher,
                    "rules": [
                        {
                            "paths": list(r.paths),
                            "service": r.service,
                            "enabled": r.enabled,
                        }
                        for r in decl.rules
                    ],
                    "services": {k: vars(v) for k, v in decl.services.items()},
                    "default_edge_upstream": decl.default_edge_upstream,
                },
                indent=2,
            )
        )
        return 0
    if args.map_command == "render-edge":
        conf = render_edge_conf(decl)
        if args.out:
            Path(args.out).write_text(conf, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            sys.stdout.write(conf)
        return 0
    live = _load_live(args.live)
    if args.map_command == "render":
        yaml_doc = render_urlmap_yaml(apply_rules(live, decl, args.project))
        if args.out:
            Path(args.out).write_text(yaml_doc, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            sys.stdout.write(yaml_doc)
        return 0
    if args.map_command == "diff":
        diffs = diff_urlmap(live, decl, args.project)
        if diffs:
            for d in diffs:
                print(f"DRIFT: {d}")
            return 4
        print("lb-map diff: clean — the live apex matcher carries the declared rules")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
