# SPDX-License-Identifier: Apache-2.0
"""P35.55 (REL-08, SIG-REL-013): the composed-stack proof for the release
reversal verbs — withdrawal followed by rollback, in the same serve shape
P35.54's generation suite uses.

`docker compose --profile release-serving` stands the real `sig-web`
image up against a fixture release root mounted at /mnt/rel. The
proves-in-compose claims:

  * `sig-ops release withdraw` appends the disposition, writes
    `conf/<gen+1>` with the full-alias deny map, and every alias of the
    withdrawn route answers **410 with its own sig.tombstone/1 body**
    through the rendered nginx (no-slash, trailing-slash, index.html,
    and the `.json` twin);
  * `sig-ops release rollback --to <pub>` re-points the latest view —
    the withdrawal barrier survives the rollback byte-for-byte (a
    rollback NEVER resurrects withdrawn material, GT-3/SIG-REL-013);
  * `clear-latest` serves the honest no-current-release state —
    `/` 404s under `v/none/` while the archive + barrier keep serving;
  * the conf-gen regression probe answers `sig.probe-run/1` pass against
    the live conf gen and FAILS when an older generation serves — the
    P1 alarm, never asserted, always probed.

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
from ops import release_reversal as rr  # noqa: E402

COMPOSE_FILE = REPO_ROOT / "ops" / "docker-compose.yml"
COMPOSE_PROJECT = "sig-e2e-reversal"

WEB_PORT = int(os.environ.get("SIG_E2E_REV_PORT", "18095"))
WEB = f"http://127.0.0.1:{WEB_PORT}"

PUB1 = "p-" + "a" * 64
PUB2 = "p-" + "b" * 64
LABEL1 = "sig-2026-10-01.1"
LABEL2 = "sig-2026-10-02.1"
EID = "ent-gone-1"
ROUTE = f"r/{PUB1}/c/sig_graph/entity/deployment/{EID}"
NOW = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; composed release-reversal tests skip (P35.55)",
        allow_module_level=True,
    )


def _compose(
    *args: str, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(COMPOSE_FILE), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    if check:
        assert proc.returncode == 0, f"compose {args} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc


def _http(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _wait_for(url: str, timeout_s: int = 300, want_status: int = 200) -> None:
    deadline = time.monotonic() + timeout_s
    last = "no response"
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", WEB_PORT, timeout=5)
            conn.request("GET", "/")
            resp = conn.getresponse()
            resp.read()
            if resp.status == want_status:
                return
            last = f"HTTP {resp.status}"
        except Exception as e:
            last = repr(e)
        time.sleep(1)
    raise AssertionError(f"web never answered {want_status} at {url}: {last}")


def _serve_env(gen: int, pub: str, label: str, root: Path) -> dict[str, str]:
    return {
        "SIG_CONF_GEN": str(gen),
        "SIG_LATEST_PUB": pub,
        "SIG_LATEST_LABEL": label,
        "SIG_RELEASE_ROOT": str(root),
        "SIG_WEB_PORT": str(WEB_PORT),
    }


def _up_web(gen: int, pub: str, label: str, root: Path, want: int = 200) -> None:
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
    assert up.returncode == 0, f"compose up web failed:\n{up.stdout}\n{up.stderr}"
    _wait_for(f"{WEB}/", want_status=want)


def _put(store: rp.Store, name: str, body: bytes | dict) -> None:
    data = json.dumps(body, sort_keys=True).encode() if isinstance(body, dict) else body
    meta = store.stat(name)
    if meta is None:
        store.insert(name, data, content_type="application/json")
    else:
        store.replace(
            name, data, generation=int(meta["generation"]), content_type="application/json"
        )


def _seed_pub(store: rp.Store, pub: str, label: str) -> None:
    entry = {
        "schema": "sig.publication-catalog-entry/1",
        "publication_id": pub,
        "data_release_id": label,
        "label": label,
        "manifest_sha256": "0" * 64,
        "descriptor_sha256": "1" * 64,
        "compartments": [{"compartment": "sig_graph"}],
        "compat": {"as_of_world": "2026-10-01"},
    }
    _put(store, f"staged/releases/{pub}/catalog_entry.json", entry)
    _put(
        store,
        f"staged/releases/{pub}/release.json",
        {"schema": "sig.site-release/1", "data_release_id": label},
    )
    _put(
        store,
        f"staged/releases/{pub}/descriptor.json",
        {"schema": "sig.release-descriptor/2", "label": label, "code": {"commit": "0" * 40}},
    )
    store.insert(f"staged/releases/{pub}/index.html", f"<html>landing {label}</html>".encode())
    store.insert(f"staged/r/{pub}/index.html", f"<html>records {label}</html>".encode())
    store.insert(f"staged/v/{pub}/index.html", f"<html>latest {label}</html>".encode())
    store.insert(f"staged/s/{pub}/index.html", f"<html>snapshot {label}</html>".encode())


def _gen_files(store: rp.Store, gen: int, pubs: set[str], latest: dict) -> dict[str, bytes]:
    latest_bytes = json.dumps(latest, sort_keys=True).encode()
    return {
        "promoted.map": rc.render_promoted_map(pubs, gen=gen),
        "latest.json": latest_bytes,
        "withdrawn.conf": b"# no denials recorded\n",
        "selectors.conf": rc._empty_selectors(gen),
        "labels.conf": rc.render_labels_conf(rc.read_label_map(store), gen=gen),
        "releases/index.html": b"<html>releases</html>",
        "releases/catalog.json": b"{}",
        "releases/latest.json": latest_bytes,
    }


@pytest.fixture(scope="module")
def release_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A two-generation registry: gen-1 promotes PUB1, gen-2 promotes PUB2
    (the promoted set carries both). One entity record route under
    PUB1's ``c/sig_graph`` compartment is the withdraw target."""
    root = tmp_path_factory.mktemp("release-root")
    # 0700 mkdtemp breaks the bind mount for the container's nginx uid —
    # the real release root is world-traversable (see P35.54's note).
    root.chmod(0o755)
    store = rp.LocalDirStore(root)
    for pub, label in ((PUB1, LABEL1), (PUB2, LABEL2)):
        _seed_pub(store, pub, label)
    # the withdraw target — an entity record (page + .json twin)
    store.insert(f"staged/{ROUTE}/index.html", f"<html>record {EID}</html>".encode())
    store.insert(f"staged/{ROUTE}.json", json.dumps({"entity_id": EID}).encode())
    _put(
        store,
        "registry/catalog.json",
        {
            "schema": "sig.publication-catalog/1",
            "publications": [
                {"publication_id": PUB1, "data_release_id": LABEL1},
                {"publication_id": PUB2, "data_release_id": LABEL2},
            ],
        },
    )
    _put(store, "registry/withdrawals.json", {"schema": "sig.withdrawal-registry/1", "entries": []})
    _put(
        store,
        "registry/labels.json",
        {
            "schema": "sig.release-labels/1",
            "labels": [
                {"label": LABEL1, "publication_id": PUB1},
                {"label": LABEL2, "publication_id": PUB2},
            ],
        },
    )
    _put(
        store,
        f"{rr.AUTHORITIES_PREFIX}go",
        {"schema": rr.AUTHORITY_SCHEMA, "kind": "go", "ref": "OPS-g4"},
    )
    for gen, pub, label in ((1, PUB1, LABEL1), (2, PUB2, LABEL2)):
        latest = {
            "schema": rc.LATEST_SCHEMA_V2,
            "publication_id": pub,
            "label": label,
            "activated_at": NOW.isoformat(),
            "conf_gen": gen,
            "rolled_back": False,
            "withdrawals_sha256": rr.withdrawals_sha256(store),
        }
        promoted = {PUB1} if gen == 1 else {PUB1, PUB2}
        for name, body in _gen_files(store, gen, promoted, latest).items():
            store.insert(f"registry/conf/{gen}/{name}", body)
    yield root
    _compose("--profile", "release-serving", "down", "-v", check=False)


def _order(root: Path) -> Path:
    p = root / "order.json"
    p.write_bytes(
        json.dumps(
            {
                "schema": rr.ORDER_SCHEMA,
                "order_id": "ord-e2e-1",
                "entries": [
                    {
                        "target_kind": "entity",
                        "target_id": EID,
                        "disposition": "withdraw",
                        "reason_category": "safety_withdrawal",
                    }
                ],
            }
        ).encode()
    )
    return p


def test_withdraw_then_every_alias_410s_with_its_tombstone(release_root: Path):
    """withdraw → gen 3 → every alias of the route 410s its own tombstone."""
    root = release_root
    store = rp.LocalDirStore(root)
    out = rr.verb_withdraw(
        store,
        apply_=True,
        disposition=_order(root),
        authority="go",
        now=NOW,
    )
    assert out["applied"] is True and out["conf_gen"] == 3
    failed = [p for p in out["probes"] if p["status"] == "fail"]
    assert not failed, f"alias probes failed: {failed}"
    _up_web(3, PUB2, LABEL2, root)
    # every alias — no-slash, trailing-slash, index.html, .json — 410s with
    # a dated sig.tombstone/1 body, never a generic nginx page
    for alias in (f"/{ROUTE}", f"/{ROUTE}/", f"/{ROUTE}/index.html", f"/{ROUTE}.json"):
        status, _h, body = _http(f"{WEB}{alias}")
        assert status == 410, f"{alias} answered {status}, not 410"
        assert b"withdrawn" in body or b"tombstone" in body, f"{alias}: no tombstone body"
        assert b"record ent-gone-1" not in body, f"{alias} serves the withdrawn bytes"
    # everything else keeps serving — the barrier is surgical
    status, _h, body = _http(f"{WEB}/")
    assert status == 200 and body == b"<html>latest sig-2026-10-02.1</html>"
    status, _h, _b = _http(f"{WEB}/r/{PUB1}/")
    assert status == 200
    status, headers, _b = _http(f"{WEB}/r/{PUB2}/")
    assert status == 200 and headers.get("X-SIG-Conf-Gen") == "3"


def test_rollback_keeps_the_barrier_while_repointing_latest(release_root: Path):
    """rollback → gen 4 → the denied route STILL 410s; the latest view
    re-points at PUB1 — never a resurrected route (GT-3)."""
    root = release_root
    store = rp.LocalDirStore(root)
    out = rr.verb_rollback(store, apply_=True, to=PUB1, reason="gen-2 defect", go="go", now=NOW)
    assert out["applied"] is True and out["conf_gen"] == 4
    _up_web(4, PUB1, LABEL1, root)
    status, _h, body = _http(f"{WEB}/")
    assert status == 200 and body == b"<html>latest sig-2026-10-01.1</html>", (
        "the latest view rolled back to PUB1's bytes"
    )
    # the barrier: every alias still denies with its tombstone — a rollback
    # NEVER resurrects withdrawn material
    for alias in (f"/{ROUTE}", f"/{ROUTE}/", f"/{ROUTE}/index.html", f"/{ROUTE}.json"):
        status, _h, body = _http(f"{WEB}{alias}")
        assert status == 410, f"post-rollback {alias} answered {status} — the barrier lapsed"
    status, _h, _b = _http(f"{WEB}/r/{PUB2}/")
    assert status == 200, "the promoted map keeps PUB2 — rollback is a pointer, not a deletion"


def test_clear_latest_serves_the_archive_only(release_root: Path):
    """clear-latest → gen 5 → `/` 404s under v/none/; the archive + the
    barrier keep serving — the honest no-current-release state."""
    root = release_root
    store = rp.LocalDirStore(root)
    out = rr.verb_clear_latest(store, apply_=True, reason="full review window", go="go", now=NOW)
    assert out["applied"] is True and out["conf_gen"] == 5
    _up_web(5, rr.NO_LATEST_SENTINEL, rr.NO_LATEST_LABEL, root, want=404)
    status, _h, _b = _http(f"{WEB}/")
    assert status == 404, "v/none/ never exists — the latest view is honestly absent"
    status, _h, _b = _http(f"{WEB}/r/{PUB1}/")
    assert status == 200, "the archive keeps serving every promoted namespace"
    status, _h, _b = _http(f"{WEB}/{ROUTE}/")
    assert status == 410, "the barrier outlives the latest pointer entirely"


def test_conf_gen_probe_against_the_live_generation(release_root: Path):
    """The P1 probe: pass when the origin serves the recorded generation,
    fail when it serves an older one — measured, never asserted."""
    root = release_root
    store = rp.LocalDirStore(root)
    rec = rr.conf_gen_probe(store, origins=[WEB], fetch=None)
    assert rec["overall"] == "pass", rec["checks"]
    assert rec["version"].startswith("sig.probe-run")
    # roll the web back to gen 2 — recorded is 5; the probe MUST alarm
    _up_web(2, PUB2, LABEL2, root)
    rec2 = rr.conf_gen_probe(store, origins=[WEB], fetch=None)
    assert rec2["overall"] == "fail", "served-older-generation must alarm"
    leg = next(iter(rec2["checks"].values()))
    assert leg["served_gen"] == 2 and leg["recorded_gen"] == 5
