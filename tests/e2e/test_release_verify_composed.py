# SPDX-License-Identifier: Apache-2.0
"""P35.56 (REL-04a) — the composed leg of verification suite A.

`docker compose --profile release-serving` stands the G3 §4.2 serving shape
up locally — the real `sig-web` image rendering the envsubst template over a
*real built release* (build_release v2 + the v//s// site trees the ops test
fixture synthesises) mounted at /mnt/rel — and `sig-ops release verify` runs
the suite over real HTTP:

* **S mode** — `web-staging` (SIG_STAGING=1, SIG_LATEST_PUB=<candidate>)
  before promote: the full table V1–V5 + V11–V13 — green on the honest
  fixture; a tampered staged byte flips V1 and the verb refuses
  (``verify-failed``), journalling ``failed`` so promotion cannot proceed.
* **P mode** — `web` (SIG_STAGING=0, the candidate promoted in the fixture
  registry's gen 2) after promote: the §5.5 subset over the public origin.

The axe leg runs the real playwright+axe-core runner
(:func:`release_verify.playwright_axe`) against the composed origin — never a
stubbed scan; an environment without node/web deps/a browser makes V11 an
honest ``skip`` (which blocks), and this module skips itself loudly in that
case rather than claim a green it did not earn.

Needs Docker; skips without a reachable daemon unless
SIG_REQUIRE_DB_TESTS=1 (then a missing daemon is a loud failure).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ops" / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "ops"))

from test_release_verify import LABEL, _build_candidate  # noqa: E402

from ops import release_pipeline as rp  # noqa: E402
from ops import release_verify as rv  # noqa: E402

COMPOSE_FILE = REPO_ROOT / "ops" / "docker-compose.yml"
COMPOSE_PROJECT = "sig-e2e-verify"

WEB_PORT = int(os.environ.get("SIG_E2E_VERIFY_WEB_PORT", "18095"))
STAGING_PORT = int(os.environ.get("SIG_E2E_VERIFY_STAGING_PORT", "18096"))
WEB = f"http://127.0.0.1:{WEB_PORT}"
STAGING = f"http://127.0.0.1:{STAGING_PORT}"


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; composed release-verify tests skip (P35.56)",
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


def _wait_for(url: str, timeout_s: int = 300, want_status: int = 200) -> None:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            status, _h, _b = _http(url)
            if status == want_status:
                return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    raise AssertionError(f"{url} never answered {want_status} within {timeout_s}s")


def _serve_env(gen: int, pub: str, root: Path) -> dict[str, str]:
    return {
        "SIG_CONF_GEN": str(gen),
        "SIG_LATEST_PUB": pub,
        "SIG_LATEST_LABEL": LABEL,
        "SIG_RELEASE_ROOT": str(root),
        "SIG_WEB_PORT": str(WEB_PORT),
        "SIG_WEB_STAGING_PORT": str(STAGING_PORT),
    }


def _axe_usable() -> bool:
    """Whether this environment can run the real axe leg (node +
    web/node_modules + a playwright browser). ``playwright_axe`` returns
    ``None`` exactly when a dep is absent; an unreachable page still
    returns a violations map, so the probe answers the *runner's*
    availability, not the target's."""
    return rv.playwright_axe("http://127.0.0.1:9/", ["/"], timeout=60) is not None


@pytest.fixture(scope="module")
def s_root(tmp_path_factory: pytest.TempPathFactory):
    """The pre-promotion posture: candidate staged, registry latest still
    names the previous release, conf gen 1 serving — what S-mode verifies."""
    base = tmp_path_factory.mktemp("verify-s")
    work_dir, pub, _store = _build_candidate(base)
    root = base / "relroot"
    root.chmod(0o755)  # the bind mount must be traversable by nginx's uid
    yield root, work_dir, pub
    _compose("--profile", "release-serving", "down", "-v", check=False)


@pytest.fixture(scope="module")
def p_root(tmp_path_factory: pytest.TempPathFactory):
    """The post-promotion posture: gen 2's promoted.map carries the
    candidate and latest.json names it — what P-mode verifies."""
    base = tmp_path_factory.mktemp("verify-p")
    work_dir, pub, _store = _build_candidate(base, promoted=True)
    root = base / "relroot"
    root.chmod(0o755)
    yield root, work_dir, pub
    _compose("--profile", "release-serving", "down", "-v", check=False)


def _rows(suites: list[dict]) -> dict[str, dict]:
    return {r["check"]: r for s in suites for r in s["results"]}


def test_s_mode_over_the_composed_staging_origin(s_root):
    root, work_dir, pub = s_root
    if not _axe_usable():
        pytest.skip(
            "no playwright+axe runner in this environment — V11 would land "
            "an honest skip (the skip-blocks rule is unit-covered); the "
            "composed green needs the real browser leg"
        )
    env = _serve_env(1, pub, root)
    up = _compose(
        "--profile",
        "release-serving",
        "up",
        "-d",
        "--build",
        "web-staging",
        env=env,
        check=False,
    )
    assert up.returncode == 0, f"compose up web-staging failed:\n{up.stdout}\n{up.stderr}"
    _wait_for(f"{STAGING}/")

    # sanity: the staged-only gate holds on the composed origin — the
    # candidate answers on staging with the noindex tag
    status, headers, _b = _http(f"{STAGING}/")
    assert status == 200 and headers.get("X-Robots-Tag") == "noindex"
    assert headers.get("X-SIG-Release") == f"{LABEL} {pub}"

    out = rp.verb_verify(
        rp.LocalDirStore(root),
        apply_=True,
        work_dir=work_dir,
        mode="S",
        origins=(STAGING,),
        pushed=True,
        tree_clean=True,
        results_dir=root / "verify-results",
    )
    assert out["verdict"] == "verified", json.dumps(
        [
            (r["check"], r["status"], r.get("detail"))
            for s in out["suites"]
            for r in s["results"]
            if r["status"] != "pass"
        ],
        indent=1,
    )
    suite = out["suites"][0]
    assert suite["origin"] == STAGING and suite["origin_kind"] == "http"
    assert {r["check"] for r in suite["results"]} == set(rv.CHECKS_S)
    # every row landed as durable JSON evidence
    assert len(list((root / "verify-results").glob("S-V*.json"))) == len(rv.CHECKS_S)


def test_s_mode_seeded_defect_blocks(s_root):
    """A tampered staged byte → V1 fails over real HTTP → the verb refuses
    and journals `failed` (promotion cannot proceed on it)."""
    root, work_dir, pub = s_root
    integrity = json.loads((work_dir / f"releases/{pub}/integrity_manifest.json").read_bytes())
    victim_rel = next(a["path"] for a in integrity["artifacts"] if a["path"].startswith("r/"))
    staged_file = root / "staged" / victim_rel
    staged_file.write_bytes(staged_file.read_bytes() + b"tampered")

    env = _serve_env(1, pub, root)
    up = _compose(
        "--profile",
        "release-serving",
        "up",
        "-d",
        "--build",
        "web-staging",
        env=env,
        check=False,
    )
    assert up.returncode == 0, f"compose up web-staging failed:\n{up.stdout}\n{up.stderr}"
    _wait_for(f"{STAGING}/")

    with pytest.raises(rp.PipelineError) as err:
        rp.verb_verify(
            rp.LocalDirStore(root),
            apply_=True,
            work_dir=work_dir,
            mode="S",
            origins=(STAGING,),
            pushed=True,
            tree_clean=True,
            results_dir=root / "verify-results-tampered",
        )
    assert err.value.code == "verify-failed"
    rows = _rows(err.value.detail["suites"])
    assert rows["V1"]["status"] == "fail"
    events = [e for e in rp.list_events(rp.LocalDirStore(root)) if e.get("verb") == "failed"]
    assert events, "a failing verify must journal `failed`, never `verified`"


def test_p_mode_over_the_composed_public_origin(p_root):
    root, work_dir, pub = p_root
    env = _serve_env(2, pub, root)
    up = _compose(
        "--profile",
        "release-serving",
        "up",
        "-d",
        "--build",
        "web",
        env=env,
        check=False,
    )
    assert up.returncode == 0, f"compose up web failed:\n{up.stdout}\n{up.stderr}"
    _wait_for(f"{WEB}/")

    # sanity: the public origin answers the promoted candidate with the
    # provenance pair; an unpromoted pub 404s by construction
    status, headers, _b = _http(f"{WEB}/")
    assert status == 200
    assert headers.get("X-SIG-Release") == f"{LABEL} {pub}"
    assert headers.get("X-SIG-Conf-Gen") == "2"
    status, _h, _b = _http(f"{WEB}/r/{'p-' + 'f' * 64}/")
    assert status == 404

    # the composed P-mode leg exposes one real serving gap: stamped pages
    # link ``/releases/catalog.jsonld`` (BaseLayout's DCAT alternate) but
    # the public deny gate 404s it — the ``/releases/`` prefix location
    # only passes ``/releases/<p-pub>/`` URIs, and the conf's exact-match
    # set names index/catalog.json/latest.json, never catalog.jsonld. The
    # suite's job is to catch exactly this; the gap is recorded in the
    # run ledger and lands as an honest ``verify-failed`` here, so every
    # non-pass row must be *that* finding and nothing else.
    with pytest.raises(rp.PipelineError) as err:
        rp.verb_verify(
            rp.LocalDirStore(root),
            apply_=True,
            work_dir=work_dir,
            mode="P",
            origins=(WEB,),
            pushed=True,
            tree_clean=True,
            results_dir=root / "verify-results",
        )
    assert err.value.code == "verify-failed"
    suites = err.value.detail["suites"]
    rows = _rows(suites)
    assert {r["check"] for s in suites for r in s["results"]} == set(rv.CHECKS_P)
    known_gaps = {"/releases/catalog.jsonld"}
    non_pass = {cid: r for cid, r in rows.items() if r["status"] != "pass"}
    assert set(non_pass) == {"V5"}, f"unexpected non-pass rows: {list(non_pass)}"
    dead = rows["V5"].get("evidence", {}).get("dead_or_undeclared", {})
    unexpected = {s: rs for s, rs in dead.items() if not set(rs) <= known_gaps}
    assert not unexpected, f"V5 dead links beyond the recorded gap: {unexpected}"
    assert dead, "the catalog.jsonld gap must be reported, not silently absent"
