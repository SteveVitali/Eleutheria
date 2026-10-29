# SPDX-License-Identifier: Apache-2.0
"""P35.54 (REL-03b, SIG-REL-006, ADR-220): the composed-stack proof for
configuration generations + metadata-only promotion.

`docker compose --profile release-serving` stands the release serving
shape up locally: the real `sig-web` image rendering the G3 §4.2 envsubst
template against a fixture release root mounted at /mnt/rel, plus the
`web-staging` origin (SIG_STAGING=1 rendered in — the GT-9 bypass). The
proves-in-compose claims, verbatim from the ticket:

  * an unpromoted namespace 404s by construction (the `default 0` map);
  * a staged-never-promoted release answers on the staging origin (with
    `X-Robots-Tag: noindex`) and 404s on the public service;
  * `X-SIG-Release` + `X-SIG-Conf-Gen` ride every response;
  * `sig-ops release promote` writes `conf/<gen+1>`, copies NO release
    bytes, and the latest view flips byte-for-byte on the next revision
    (the env swap is the roll — the composed stand-in for the digest
    roll the machinery plans api→web with min-instances=1);
  * the carried withdrawn.conf deny still answers 410 through the
    internal /conf/tombstone/ location;
  * the label alias 301s to the promoted pub landing.

Needs Docker; skips without a reachable daemon unless
SIG_REQUIRE_DB_TESTS=1 (then a missing daemon is a loud failure).
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ops" / "src"))

from ops import release_conf as rc  # noqa: E402
from ops import release_pipeline as rp  # noqa: E402

COMPOSE_FILE = REPO_ROOT / "ops" / "docker-compose.yml"
COMPOSE_PROJECT = "sig-e2e-release"

WEB_PORT = int(os.environ.get("SIG_E2E_WEB_PORT", "18093"))
STAGING_PORT = int(os.environ.get("SIG_E2E_STAGING_PORT", "18094"))
WEB = f"http://127.0.0.1:{WEB_PORT}"
STAGING = f"http://127.0.0.1:{STAGING_PORT}"

PUB1 = "p-" + "a" * 64
PUB2 = "p-" + "b" * 64
PUB3 = "p-" + "c" * 64  # staged, never promoted — the gate's proof
LABEL1 = "sig-2026-10-01.1"
LABEL2 = "sig-2026-10-02.1"
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)

DENY_ROUTE = f"/r/{PUB1}/gone/"
TOMBSTONE_BODY = b"<html><body>withdrawn - sig.tombstone/1 fixture body</body></html>"

# P36.19 (UXK0-3, K0 §4.8, SIG-UI-096, ADR-223): the strict response layer the
# $sig_csp / $sig_permissions_policy maps + sig-security.conf must emit.
SIG_CSP_UNIFORM = (
    "frame-ancestors 'none'; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; script-src-attr 'none'; style-src-attr 'none'"
)
SIG_CSP_SVG = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"
SIG_PP_DENY_PREFIX = "geolocation=()"


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; composed release-generation tests skip (P35.54)",
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


def _http(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 — loopback only
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _status_location(url: str) -> tuple[int, str | None]:
    """Raw status + Location without following the redirect (the label
    alias's 301 is the assertion)."""
    conn = http.client.HTTPConnection("127.0.0.1", WEB_PORT, timeout=15)
    conn.request("GET", url)
    resp = conn.getresponse()
    resp.read()
    return resp.status, resp.getheader("Location")


def _container_state() -> str:
    """`docker ps` + per-container logs/env/rendered-conf — the failure-path
    diagnostics a 300s timeout otherwise swallows (CI runs pytest -q;
    captured output only surfaces on failure). Plain `docker`, not
    `compose logs` — a profile-less `logs` sees an empty service model."""
    out = []
    ps = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    out.append(f"--- docker ps -a ---\n{ps.stdout}{ps.stderr}")
    for name in ("sig-e2e-release-web-1", "sig-e2e-release-web-staging-1"):
        logs = subprocess.run(
            ["docker", "logs", "--tail", "60", name],
            capture_output=True,
            text=True,
            check=False,
        )
        out.append(f"--- docker logs {name} ---\n{logs.stdout}{logs.stderr}")
        env = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-c",
                "env | sort | grep -i '^SIG' ; "
                "echo '--- rendered server/root lines ---' ; "
                "grep -n 'root \\|listen\\|include /mnt' /etc/nginx/nginx.conf ; "
                "echo '--- /mnt/rel tree ---' ; "
                "ls -la /mnt/rel /mnt/rel/staged/v 2>&1 | head -20",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        out.append(f"--- docker exec {name} ---\n{env.stdout}{env.stderr}")
    return "\n".join(out)


def _wait_for(url: str, timeout_s: int = 300, want_status: int = 200) -> None:
    deadline = time.monotonic() + timeout_s
    last_status: int | None = None
    while time.monotonic() < deadline:
        try:
            status, _h, _b = _http(url)
            last_status = status
            if status == want_status:
                return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    raise AssertionError(
        f"{url} never answered {want_status} within {timeout_s}s "
        f"(last_status={last_status})\n{_container_state()}"
    )


def _hash_tree(root: Path, prefix: str) -> dict[str, str]:
    import hashlib

    out: dict[str, str] = {}
    for p in sorted((root / prefix).rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _serve_env(gen: int, pub: str, label: str, root: Path) -> dict[str, str]:
    return {
        "SIG_CONF_GEN": str(gen),
        "SIG_LATEST_PUB": pub,
        "SIG_LATEST_LABEL": label,
        "SIG_RELEASE_ROOT": str(root),
        "SIG_WEB_PORT": str(WEB_PORT),
        "SIG_WEB_STAGING_PORT": str(STAGING_PORT),
    }


def _up_web(gen: int, pub: str, label: str, root: Path) -> None:
    up = _compose(
        "--profile",
        "release-serving",
        "up",
        "-d",
        "--build",
        "web",
        env=_serve_env(gen, pub, label, root),
        check=False,
    )
    assert up.returncode == 0, (
        f"compose up web failed:\n{up.stdout}\n{up.stderr}\n{_container_state()}"
    )
    _wait_for(f"{WEB}/", want_status=200)


def _up_staging(gen: int, pub: str, label: str, root: Path) -> None:
    up = _compose(
        "--profile",
        "release-serving",
        "up",
        "-d",
        "--build",
        "web-staging",
        env=_serve_env(gen, pub, label, root),
        check=False,
    )
    assert up.returncode == 0, (
        f"compose up web-staging failed:\n{up.stdout}\n{up.stderr}\n{_container_state()}"
    )
    _wait_for(f"{STAGING}/", want_status=200)


@pytest.fixture(scope="module")
def image_built() -> None:
    _compose("--profile", "release-serving", "build", "web")


@pytest.fixture(scope="module")
def release_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture release root — the /mnt/rel mount. staged/ trees stand
    in for the private release bytes; the registry carries the approval
    record + labels + the journal's verified/classified events.

    Gen-2 is written in the *withdraw writer's shape* (P35.55): a whole
    conf/<gen>/ naming the still-latest pub with a deny line + tombstone
    body — promote then carries it byte-identical into gen-3."""
    root = tmp_path_factory.mktemp("release-root")
    # mkdtemp is 0700 — the bind mount's root inode is what the container
    # sees as /mnt/rel, and a native-Linux nginx worker (uid 101) cannot
    # traverse a 0700 foreign-owned dir (CI found this as stat() EACCES →
    # 404; Docker Desktop's virtiofs squash masks it locally). The real
    # release root is a bucket mount — world-traversable — so 0755 is the
    # honest fixture posture, not a test convenience.
    root.chmod(0o755)
    for pub, tag in ((PUB1, "one"), (PUB2, "two"), (PUB3, "three")):
        (root / "staged/v" / pub).mkdir(parents=True, exist_ok=True)
        (root / "staged/v" / pub / "index.html").write_bytes(
            f"<html>latest view {tag}</html>".encode()
        )
        # P36.19: the /map/ Permissions-Policy exception + a standalone .svg
        # need real bytes in the fixture trees to assert the response layer.
        (root / "staged/v" / pub / "map").mkdir(parents=True, exist_ok=True)
        (root / "staged/v" / pub / "map" / "index.html").write_bytes(
            f"<html>map {tag}</html>".encode()
        )
        (root / "staged/v" / pub / "figures").mkdir(parents=True, exist_ok=True)
        (root / "staged/v" / pub / "figures" / "f.svg").write_bytes(
            b"<svg xmlns='http://www.w3.org/2000/svg'><style>rect{fill:#000}</style></svg>"
        )
        (root / "staged/r" / pub).mkdir(parents=True, exist_ok=True)
        (root / "staged/r" / pub / "index.html").write_bytes(f"<html>records {tag}</html>".encode())
        (root / "staged/r" / pub / "fig.svg").write_bytes(
            b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        )
        (root / "staged/r" / pub / "gone").mkdir(parents=True, exist_ok=True)
        (root / "staged/r" / pub / "gone" / "index.html").write_bytes(b"<html>gone</html>")
        (root / "staged/s" / pub).mkdir(parents=True, exist_ok=True)
        (root / "staged/s" / pub / "index.html").write_bytes(
            f"<html>snapshot {tag}</html>".encode()
        )
        (root / "staged/releases" / pub).mkdir(parents=True, exist_ok=True)
        (root / "staged/releases" / pub / "index.html").write_bytes(
            f"<html>landing {tag}</html>".encode()
        )
    for pub, label in ((PUB1, LABEL1), (PUB2, LABEL2), (PUB3, "sig-2026-10-03.1")):
        (root / "staged/releases" / pub / "catalog_entry.json").write_bytes(
            json.dumps(
                {
                    "schema": "sig.catalog-entry/1",
                    "publication_id": pub,
                    "data_release_id": label,
                    "manifest_sha256": "f" * 64,
                    "compat": {"as_of_world": "2026-10-01"},
                }
            ).encode()
        )
        (root / "staged/releases" / pub / "descriptor.json").write_bytes(
            json.dumps({"label": label, "code": {"commit": "0" * 40}}).encode()
        )
    # the tombstone body the deny's error_page serves
    tomb = root / "staged/conf/tombstone"
    tomb.mkdir(parents=True)
    (tomb / "dead.html").write_bytes(TOMBSTONE_BODY)
    # the approval record (the operator's, checked never created)
    appr = root / "registry/approvals"
    appr.mkdir(parents=True)
    (appr / "go.json").write_bytes(
        json.dumps(
            {
                "schema": "sig.promotion-approval/1",
                "kind": "standing_go",
                "class": "class_r",
                "ref": "GATE-G4 §4",
                "approved_at": "2026-10-09T17:32:00Z",
            }
        ).encode()
    )
    # the label map labels.conf composes from
    (root / "registry").mkdir(parents=True, exist_ok=True)
    (root / "registry/labels.json").write_bytes(
        json.dumps(
            {
                "schema": "sig.release-labels/1",
                "labels": [
                    {"label": LABEL1, "publication_id": PUB1},
                    {"label": LABEL2, "publication_id": PUB2},
                ],
            }
        ).encode()
    )
    store = rp.LocalDirStore(root)
    for pub in (PUB1, PUB2):
        rp.emit_event(store, "verified", pub, {"outcome": "recorded"}, now=NOW)
        rp.emit_event(
            store, "classified", pub, {"outcome": "recorded", "class": "class_r"}, now=NOW
        )
    yield root
    _compose("--profile", "release-serving", "down", "-v", check=False)


def _promote(root: Path, pub: str) -> dict:
    return rc.verb_promote(
        rp.LocalDirStore(root),
        apply_=True,
        publication_id=pub,
        approval="go.json",
        api_image="gcr.io/sig/sig-api@sha256:" + "1" * 64,
        web_image="gcr.io/sig/sig-web@sha256:" + "2" * 64,
        project="sig-fixture",
        region="us-central1",
        now=NOW,
    )


def test_metadata_only_promotion_and_the_generation_flip(release_root: Path):
    root = release_root

    # -- phase A: gen 1 — pub1 promoted, pub2 unpromoted ------------------ #
    staged_before = _hash_tree(root, "staged")
    r1 = _promote(root, PUB1)
    assert r1["outcome"] == "promoted" and r1["conf_gen"] == 1
    _up_web(1, PUB1, LABEL1, root)

    status, headers, body = _http(f"{WEB}/")
    assert status == 200 and body == b"<html>latest view one</html>"
    assert headers.get("X-SIG-Conf-Gen") == "1"
    assert headers.get("X-SIG-Release") == f"{LABEL1} {PUB1}"
    assert "X-Robots-Tag" not in headers

    # P36.19: the strict response layer on the served bytes — HSTS +
    # nosniff on every response, the hash-independent CSP guards on HTML,
    # the /map/ geolocation exception, and K0 §4.8's dedicated figure-SVG
    # policy under BOTH the latest view and the /r/ release tree (the
    # $sig_csp map keys on the request, never on a location).
    assert headers.get("Strict-Transport-Security") == "max-age=63072000; includeSubDomains"
    assert headers.get("Content-Security-Policy") == SIG_CSP_UNIFORM
    assert headers.get("Permissions-Policy", "").startswith(SIG_PP_DENY_PREFIX)
    assert headers.get("X-Content-Type-Options") == "nosniff"
    status, headers, body = _http(f"{WEB}/map/")
    assert status == 200
    assert headers.get("Permissions-Policy", "").startswith("geolocation=(self)")
    assert headers.get("Content-Security-Policy") == SIG_CSP_UNIFORM
    status, headers, body = _http(f"{WEB}/figures/f.svg")
    assert status == 200
    assert headers.get("Content-Security-Policy") == SIG_CSP_SVG
    assert headers.get("X-Content-Type-Options") == "nosniff"
    status, headers, body = _http(f"{WEB}/r/{PUB1}/fig.svg")
    assert status == 200
    assert headers.get("Content-Security-Policy") == SIG_CSP_SVG, (
        "the dedicated figure policy follows the bytes under /r/ too"
    )

    status, headers, body = _http(f"{WEB}/r/{PUB1}/")
    assert status == 200 and body == b"<html>records one</html>"
    assert headers.get("X-SIG-Conf-Gen") == "1"

    status, _h, _b = _http(f"{WEB}/r/{PUB2}/")
    assert status == 404, "the unpromoted namespace must 404 (default 0)"
    status, _h, _b = _http(f"{WEB}/r/{PUB3}/")
    assert status == 404, "staged-never-promoted is private too"
    status, _h, body = _http(f"{WEB}/s/{PUB1}/")
    assert status == 200 and body == b"<html>snapshot one</html>"
    status, _h, _b = _http(f"{WEB}/s/{PUB2}/")
    assert status == 404, "the /s/ gate is the same map (default 0)"
    status, _h, _b = _http(f"{WEB}/releases/{PUB2}/")
    assert status == 404

    status, _h, body = _http(f"{WEB}/releases/")
    assert status == 200 and b"conf_gen" in body and b"sig-2026-10-01.1" in body
    status, _h, body = _http(f"{WEB}/releases/index.html")
    assert status == 200
    status, _h, body = _http(f"{WEB}/releases/latest.json")
    assert status == 200
    latest = json.loads(body)
    assert latest["schema"] == "sig.latest-pointer/2"
    assert latest["publication_id"] == PUB1 and latest["conf_gen"] == 1
    status, _h, body = _http(f"{WEB}/releases/catalog.json")
    cat = json.loads(body)
    assert cat["schema"] == "sig.publication-catalog/2"
    assert [e["publication_id"] for e in cat["entries"] if e["state"] == "promoted"] == [PUB1]

    # the label alias resolves to the promoted pub landing
    status, location = _status_location(f"/releases/{LABEL1}/")
    assert status == 301 and location == f"/releases/{PUB1}/"

    # -- phase B: a withdraw-shape gen 2, then pub2's promote → gen 3 ----- #
    # The P35.55 writer's shape: a whole generation naming the still-latest
    # pub, carrying a deny. Promote must carry it byte-identical (contract:
    # consumed here, written there).
    store = rp.LocalDirStore(root)
    deny = f"location = {DENY_ROUTE} {{ error_page 410 /conf/tombstone/dead.html; return 410; }}\n"
    gen2 = rc.compose_generation(
        store,
        gen=2,
        pub=PUB1,
        label=LABEL1,
        release_class="class_r",
        approval_ref=None,
        meta=rc.read_release_meta(store, PUB1),
        api_image=None,
        web_image=None,
        now=NOW,
    )
    gen2["withdrawn.conf"] += deny.encode()
    rc.write_generation(store, 2, gen2)

    r2 = _promote(root, PUB2)
    assert r2["conf_gen"] == 3 and r2["outcome"] == "promoted"
    assert _hash_tree(root, "staged") == staged_before, (
        "SIG-REL-006: promotion copies/writes zero staged bytes"
    )
    assert deny.encode() in (root / "registry/conf/3/withdrawn.conf").read_bytes()

    _up_web(3, PUB2, LABEL2, root)
    status, headers, body = _http(f"{WEB}/")
    assert status == 200 and body == b"<html>latest view two</html>", (
        "the latest view flips byte-for-byte on the new revision"
    )
    assert headers.get("X-SIG-Conf-Gen") == "3"
    assert headers.get("X-SIG-Release") == f"{LABEL2} {PUB2}"

    status, _h, body = _http(f"{WEB}/r/{PUB2}/")
    assert status == 200 and body == b"<html>records two</html>"
    status, _h, _b = _http(f"{WEB}/r/{PUB1}/")
    assert status == 200, "gen 3's promoted map carries pub1's set forward"
    status, headers, body = _http(f"{WEB}{DENY_ROUTE}")
    assert status == 410, "the carried deny still answers through the internal tombstone"
    assert TOMBSTONE_BODY in body
    status, _h, body = _http(f"{WEB}/releases/latest.json")
    assert json.loads(body)["publication_id"] == PUB2

    # -- phase C: the staging origin — GT-9 bypass + noindex -------------- #
    _up_staging(3, PUB2, LABEL2, root)
    status, headers, body = _http(f"{STAGING}/r/{PUB3}/")
    assert status == 200, "staging never gates — every staged byte is reviewable"
    assert body == b"<html>records three</html>"
    assert headers.get("X-Robots-Tag") == "noindex"
    status, headers, body = _http(f"{STAGING}/s/{PUB3}/")
    assert status == 200 and headers.get("X-Robots-Tag") == "noindex"
    status, headers, _b = _http(f"{STAGING}/")
    assert headers.get("X-Robots-Tag") == "noindex"
    status, _h, body = _http(f"{STAGING}{DENY_ROUTE}")
    assert status == 410, "the deny barrier applies on staging too"
    # and the public service still 404s the staged-never-promoted pub
    status, _h, _b = _http(f"{WEB}/r/{PUB3}/")
    assert status == 404

    # -- phase D: an old generation stays servable — revision agreement --- #
    _up_web(1, PUB1, LABEL1, root)
    status, headers, body = _http(f"{WEB}/")
    assert status == 200 and body == b"<html>latest view one</html>"
    assert headers.get("X-SIG-Conf-Gen") == "1"
    status, _h, _b = _http(f"{WEB}/r/{PUB2}/")
    assert status == 404, "gen 1's promoted map never learned about pub2"


def test_the_entrypoint_refuses_a_half_set_env_in_the_image(release_root: Path, image_built: None):
    """The image-level guard: a revision env missing half the pair exits 1
    instead of silently rendering a half-templated site."""
    out = _compose(
        "--profile",
        "release-serving",
        "run",
        "-T",
        "--rm",
        "--no-deps",
        "-e",
        "SIG_CONF_GEN=3",
        "-e",
        "SIG_LATEST_PUB=",
        "web",
        "sh",
        "-c",
        "/docker-entrypoint.d/40-sig-conf.sh",
        env=_serve_env(3, PUB2, LABEL2, release_root),
        check=False,
    )
    assert out.returncode == 1
    assert "half-set" in (out.stderr + out.stdout)


def test_the_entrypoint_renders_inside_the_image(release_root: Path, image_built: None):
    """The image-level render path: the script + templates are in the image
    at the pinned paths, envsubst substituting only the SIG_* names."""
    out = _compose(
        "--profile",
        "release-serving",
        "run",
        "-T",
        "--rm",
        "--no-deps",
        "-e",
        "SIG_CONF_GEN=3",
        "-e",
        f"SIG_LATEST_PUB={PUB2}",
        "-e",
        f"SIG_LATEST_LABEL={LABEL2}",
        "-e",
        "SIG_STAGING=1",
        "web",
        "sh",
        "-c",
        "/docker-entrypoint.d/40-sig-conf.sh && "
        "grep -c 'conf/3/promoted.map' /etc/nginx/nginx.conf",
        env=_serve_env(3, PUB2, LABEL2, release_root),
        check=False,
    )
    assert out.returncode == 0
    assert out.stdout.strip().endswith("1")
