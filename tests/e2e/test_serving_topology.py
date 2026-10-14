# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.40 / ACT-17 (G3 §4.3) — the composed serving-topology proof.

`docker compose --profile serving` stands up the production serving SHAPE on
loopback: the real `sig-web` image (ops/web/Dockerfile — the P32.13 nginx
with the withdrawal/renamed/chrome/terms `conf/` glob includes) over a
staged fixture site at `/mnt/sig-web`; the real `sig-api` image
(ops/Dockerfile) with a real release registry bind-mounted read-only at
`/mnt/rel/registry` (the path its CMD conditionalises `--release-registry`
on); the intake receiver mounted but NON-OPERATIONAL (`[intake].operational`
stays false — `503 receiver_not_operating`); and `edge`, a stock nginx
running the committed `ops/edge.conf` — the render of `ops/lb_routes.toml`
that stands in for the external HTTPS LB's path rules.

What is proven here (composed only — never claimed as a live pass):

* every allow-listed route on the edge answers byte-for-byte what the web
  container answers — the ONLY diff is `/intake/`, the written-not-applied
  rule the composed stack exists to exercise;
* `/v1/*` routes to sig-api: a REAL activated release's FTS5 search answers
  through the edge (the registry mount + CMD flag doing their job) while the
  same path on web is the nginx 404;
* `/intake/*` routes to the non-operational receiver: `503
  receiver_not_operating` through the edge, 404 on the web surface;
* the withdrawal barrier + the dark chrome/terms fragments take effect on
  `nginx -s reload` — the exact activation path the runbook records;
* PMTiles byte-range serving with NO double compression, gzip on text.

Gating mirrors tests/db/conftest.py: no Docker daemon → skip (or hard-fail
under SIG_REQUIRE_DB_TESTS=1). Image builds are the real Dockerfiles —
first run is slow, subsequent runs hit the layer cache.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "ops" / "docker-compose.yml"
EDGE_CONF = REPO_ROOT / "ops" / "edge.conf"
COMPOSE_PROJECT = "sig-e2e-serving"

EDGE_PORT = int(os.environ.get("SIG_E2E_EDGE_PORT", "18090"))
WEB_PORT = int(os.environ.get("SIG_E2E_WEB_PORT", "18091"))
EDGE = f"http://127.0.0.1:{EDGE_PORT}"
WEB = f"http://127.0.0.1:{WEB_PORT}"


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; composed serving-topology tests skip (P34.40)",
        allow_module_level=True,
    )


def _compose(
    *args: str, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(COMPOSE_FILE), *args],
        capture_output=True,
        text=True,
        check=check,
        env=e,
        cwd=str(REPO_ROOT / "ops"),
    )


def _http(url: str, *, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 — loopback only
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _wait_for(url: str, timeout_s: int = 240, want_status: int | None = None) -> None:
    """Poll until ``url`` answers (any status), or answers ``want_status``
    when given — a wrong status means the upstream isn't routed yet, so keep
    waiting (an edge 502/404 before `api` is up is not readiness)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            status, _h, _b = _http(url)
            if want_status is None or status == want_status:
                return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    raise AssertionError(f"{url} never answered {want_status or 'anything'} within {timeout_s}s")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stage_site(site: Path) -> None:
    """A minimal staged web tree standing in for the bucket mount: the
    branded pages, a homepage, a PMTiles object, a dir without an index
    (403 material), a release path, and an EMPTY conf/ — the fragments land
    mid-test, exercising the include-and-reload activation path."""
    site.mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html><title>SIG</title><h1>home</h1>\n")
    (site / "404.html").write_text("<!doctype html><title>404</title><h1>sig-404</h1>\n")
    (site / "403.html").write_text("<!doctype html><title>403</title><h1>sig-403-branded</h1>\n")
    (site / "410.html").write_text("<!doctype html><title>410</title><h1>sig-410-branded</h1>\n")
    # >256 bytes so it crosses the web nginx's gzip_min_length floor.
    (site / "robots.txt").write_text(
        "User-agent: *\nDisallow:\n" + ("# sitemap pointer padding\n" * 16)
    )
    (site / "dossier").mkdir()
    (site / "dossier" / "index.html").write_text("<!doctype html><h1>dossiers</h1>\n")
    # A directory with content but no index → nginx answers 403 (autoindex off).
    (site / "noindex_dir").mkdir()
    (site / "noindex_dir" / "x.txt").write_text("content\n")
    # A release path for the withdrawal-barrier proof.
    (site / "r" / "pub-e2e" / "page").mkdir(parents=True)
    (site / "r" / "pub-e2e" / "page" / "index.html").write_text(
        "<!doctype html><h1>release page</h1>\n"
    )
    # A PMTiles fixture: a few KiB of deterministic bytes (the range proof
    # only needs the file to exist under /tiles/).
    (site / "tiles").mkdir()
    (site / "tiles" / "comp.pmtiles").write_bytes(bytes(range(256)) * 64)
    # The conf/ fragment dir — the glob includes resolve against it.
    (site / "conf").mkdir()


def _stage_registry(registry: Path) -> str:
    """Build + activate a REAL release (exports.release) into the registry
    root the api container mounts — the same artifacts P32.14 serves."""
    sys.path.insert(0, str(REPO_ROOT / "tests" / "exports"))
    from exports.release import activate, build_release  # noqa: PLC0415
    from test_release import REVISION, _write_export  # noqa: PLC0415

    export = _write_export(registry.parent / "export", n_records=30)
    built = build_release(export, registry.parent / "rel", renderer_revision=REVISION)
    activate(registry, built.out_dir)
    return built.publication_id


@pytest.fixture(scope="module")
def serving_stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    if not _docker_reachable():
        pytest.fail("SIG_REQUIRE_DB_TESTS=1 but the Docker daemon is unreachable")
    root = tmp_path_factory.mktemp("serving")
    site = root / "site"
    registry = root / "registry"
    _stage_site(site)
    pub = _stage_registry(registry)

    env = {
        "SIG_SITE_ROOT": str(site),
        "SIG_RELEASE_REGISTRY": str(registry),
        "SIG_EDGE_PORT": str(EDGE_PORT),
        "SIG_WEB_PORT": str(WEB_PORT),
    }
    # `--profile serving` on the downs as well: profile-scoped services (edge
    # included) are outside a profile-less `down`'s model and would otherwise
    # leak across runs with stale upstream IPs pinned in nginx.
    _compose("--profile", "serving", "down", "-v", "--remove-orphans", env=env, check=False)
    up = _compose("--profile", "serving", "up", "-d", "--build", env=env, check=False)
    if up.returncode != 0:
        pytest.fail(f"compose up failed:\n{up.stdout}\n{up.stderr}")
    try:
        # want_status=200: a 502/404 answers before the upstream is routed and
        # would let the byte-compare capture a still-booting web container.
        _wait_for(f"{EDGE}/", want_status=200)
        _wait_for(f"{WEB}/", want_status=200)
        # Readiness = the registry-backed route answering 200 through the
        # edge — proves api is up AND its CMD picked up the registry mount.
        _wait_for(
            f"{EDGE}/v1/releases/{pub}/compartments/sig_graph/search?q=Site",
            want_status=200,
        )
        _wait_for(f"{EDGE}/intake/new", want_status=503)
        yield {"site": site, "registry": registry, "pub": pub, "env": env}
    finally:
        _compose("--profile", "serving", "down", "-v", "--remove-orphans", env=env, check=False)


def _web_reload(env: dict[str, str]) -> None:
    """Reload the web nginx so a freshly-dropped conf/ fragment takes effect
    — the same activation path the ops runbook records."""
    proc = _compose("exec", "-T", "web", "nginx", "-s", "reload", env=env, check=False)
    assert proc.returncode == 0, proc.stderr
    time.sleep(1)


# --------------------------------------------------------------------------- #
# The composed proofs                                                           #
# --------------------------------------------------------------------------- #


def test_allowlist_byte_equal_edge_vs_web_except_dark_intake(serving_stack) -> None:
    """The dark check (deliverable 6): every allow-listed route on the edge
    answers byte-for-byte what the plain web container answers — except the
    written-not-applied `/intake/` rule, which the edge deliberately routes
    to the (non-operational) receiver instead of the web 404."""
    from ops.route_compare import capture, verify

    cap_edge = capture(EDGE)
    cap_web = capture(WEB)
    diffs = verify(cap_edge, cap_web)
    # Exactly one route differs: /intake/ — the web answers its static 404
    # page while the edge routes it to the receiver's own (FastAPI) 404.
    # Same status, different bytes — the byte-compare catches it.
    assert len(diffs) == 1 and diffs[0].startswith("/intake/:"), diffs
    status, _h, body = _http(f"{EDGE}/intake/")
    assert status == 404 and b"sig-404" not in body  # the API's 404, not nginx's


def test_v1_routes_to_the_registry_backed_api(serving_stack) -> None:
    pub = serving_stack["pub"]
    status, _h, body = _http(
        f"{EDGE}/v1/releases/{pub}/compartments/sig_graph/search?q=Site",
    )
    # The registry-backed route answers with the API's JSON/HTML shape…
    assert status == 200
    # …while the same path on the web surface is nginx's static 404.
    w_status, _wh, w_body = _http(f"{WEB}/v1/releases/{pub}/compartments/sig_graph/search")
    assert w_status == 404 and b"sig-404" in w_body

    status, _h, body = _http(
        f"{EDGE}/v1/releases/{pub}/compartments/sig_graph/search?q=Site",
        headers={"Accept": "application/json"},
    )
    assert status == 200
    doc = json.loads(body)
    assert doc["publication_id"] == pub and doc["compartment"] == "sig_graph"


def test_intake_is_dark_and_non_operational(serving_stack) -> None:
    # Through the edge the receiver answers — mounted but refusing new
    # reports (the operating gates stay off): the non-operational page.
    status, _h, body = _http(f"{EDGE}/intake/new")
    assert status == 503
    assert b"not yet operating" in body
    # On the web surface (the public default backend) the route stays denied.
    status, _h, _b = _http(f"{WEB}/intake/")
    assert status == 404


def test_prefix_boundaries_do_not_leak(serving_stack) -> None:
    # /v1foo is NOT inside the /v1 rule — it falls through to web, answering
    # the nginx 404 page (HTML), never the API's JSON 404.
    status, _h, body = _http(f"{EDGE}/v1foo")
    assert status == 404 and b"sig-404" in body
    status, _h, body = _http(f"{EDGE}/v1/health")
    # The API's own 404 — FastAPI JSON, not the nginx page: the proof the
    # /v1/ prefix reaches sig-api even for routes the API does not define.
    assert status == 404 and b"sig-404" not in body


def test_pmtiles_byte_range_and_no_double_compression(serving_stack) -> None:
    status, headers, body = _http(f"{EDGE}/tiles/comp.pmtiles", headers={"Range": "bytes=0-99"})
    assert status == 206
    assert len(body) == 100
    assert body == (bytes(range(256)) * 64)[:100]
    assert headers.get("Content-Type") == "application/vnd.pmtiles"
    # Never gzip/Brotli over the already-compressed archive.
    assert "Content-Encoding" not in headers


def test_gzip_on_text_types(serving_stack) -> None:
    status, headers, body = _http(f"{EDGE}/robots.txt", headers={"Accept-Encoding": "gzip"})
    assert status == 200
    assert headers.get("Content-Encoding") == "gzip"


def test_conf_fragments_activate_on_reload(serving_stack) -> None:
    """The D-P34.13-1 activation path: drop the generated fragments + a
    withdrawal rule under conf/, `nginx -s reload`, and the wiring is live
    — branded 403/410, /task/ → 404, /terms a real 302, the withdrawn route
    denied before origin access."""
    site = serving_stack["site"]
    env = serving_stack["env"]

    # Generate the committed fragments into the staged conf/ dir.
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "web-conf",
            "--out-dir",
            str(site / "conf"),
            "--api-base",
            "http://api:8080",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    # A withdrawal barrier fragment (the shape `release-serve apply` writes).
    (site / "conf" / "withdrawn_e2e.conf").write_text(
        "location = /r/pub-e2e/page/ { return 410; }\n"
    )
    _web_reload(env)

    # The withdrawn route is denied — with the branded 410 page served.
    status, _h, body = _http(f"{EDGE}/r/pub-e2e/page/")
    assert status == 410 and b"sig-410-branded" in body

    # A directory without an index → 403 → the branded page, not stock nginx.
    status, _h, body = _http(f"{EDGE}/noindex_dir/")
    assert status == 403 and b"sig-403-branded" in body

    # The bare /task/ prefix maps to a plain 404 (branded), /task/<h>/ unrouted.
    status, _h, body = _http(f"{EDGE}/task/")
    assert status == 404 and b"sig-404" in body

    # /terms is a true 302 to the API's terms document — never meta-refresh.
    # urllib follows redirects, and the target host only resolves inside the
    # compose network — so drive the raw status + Location with http.client.
    conn = http.client.HTTPConnection("127.0.0.1", EDGE_PORT, timeout=15)
    conn.request("GET", "/terms")
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 302
    assert resp.getheader("Location") == "http://api:8080/terms"
    conn.close()
