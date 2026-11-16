# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.61a (RULING H-1) — the fallback republish engineering:

* the lane keep-set in `ops.publish` — lane-exclusive remote objects are
  never deleted AND never overwritten (put-skip), derived from the remote
  listing, no-op when the listing shows none;
* `ops.republish_transform` — the scripted minimal-delta transform of the
  captured served tree (denied-prefix sweep, the three named items,
  pause-not-strip on `data-copy`/secret refusals);
* `ops/gcp/sig-web-restore.sh` — the bounded-delete rollback leg, tested
  offline against a canned `gcloud` on PATH.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from ops.gcs import GcsBucket

from ops import publish as P
from ops import republish_transform as T

REPO = Path(__file__).resolve().parents[2]
RESTORE = REPO / "ops/gcp/sig-web-restore.sh"


# --- the fake bucket (same shape as tests/ops/test_publish.py) ---------------


class _FakeSiteStore:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.delete_calls: list[str] = []
        self.put_calls: list[str] = []

    def bucket(self) -> GcsBucket:
        store = self

        class _B(GcsBucket):
            def __init__(self) -> None:
                pass

            def list_objects(self, prefix: str = "") -> list[str]:
                return sorted(store.objects)

            def put_object(self, name: str, data: bytes, content_type: str = "") -> None:
                store.put_calls.append(name)
                store.objects[name] = data

            def delete_object(self, name: str) -> None:
                store.delete_calls.append(name)
                store.objects.pop(name, None)

        return _B()


# --- lane keep-set ------------------------------------------------------------


def test_is_lane_object_covers_only_lane_exclusive_names() -> None:
    for name in (
        "status/state.json",
        "status/lane.json",
        "status/sources/osm.json",
        "status/archive/2026-11-01.json",
        "watch/state.json",
        "watch/lane.json",
        "watch/watch.json",
        "watch/archive/2026-11-01.json",
    ):
        assert P.is_lane_object(name), name
    for name in (
        "status/index.html",  # shared namespace — the site build emits it
        "watch/index.html",
        "watch/place/okc/index.html",
        "watch/item/x/index.html",
        "index.html",
        "r/p-abc/x.json",
    ):
        assert not P.is_lane_object(name), name


def test_plan_site_sync_keeps_lane_objects_from_deletes() -> None:
    remote = [
        "index.html",
        "stale/index.html",
        "status/state.json",
        "status/sources/osm.json",
        "watch/archive/2026-11-01.json",
        "watch/index.html",  # shared namespace — NOT lane, may be deleted
        "r/p-abc/x.json",
    ]
    keep = P.lane_keep_set(remote)
    assert keep == frozenset(
        {"status/state.json", "status/sources/osm.json", "watch/archive/2026-11-01.json"}
    )
    plan = P.plan_site_sync(["index.html"], remote, keep=keep)
    assert sorted(plan.deletes) == ["stale/index.html", "watch/index.html"]
    assert sorted(plan.lane_kept) == sorted(keep)
    assert "r/p-abc/x.json" in plan.protected_kept


def test_plan_site_sync_lane_keep_is_a_noop_when_listing_shows_none() -> None:
    remote = ["index.html", "stale/index.html"]
    keep = P.lane_keep_set(remote)
    assert keep == frozenset()
    plan = P.plan_site_sync(["index.html"], remote, keep=keep)
    assert plan.deletes == ("stale/index.html",)
    assert plan.lane_kept == ()


def test_sync_tree_never_deletes_or_overwrites_lane_objects(tmp_path: Path) -> None:
    store = _FakeSiteStore(
        {
            "old/index.html": b"stale",
            "status/state.json": b"FRESH lane heartbeat",
            "watch/watch.json": b"FRESH watch doc",
            "index.html": b"old-root",
        }
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("new-root", encoding="utf-8")
    # the fallback dist carries CAPTURED lane bytes — stale by construction
    (dist / "status").mkdir()
    (dist / "status" / "state.json").write_text("STALE capture", encoding="utf-8")
    (dist / "watch").mkdir()
    (dist / "watch" / "watch.json").write_text("STALE capture", encoding="utf-8")

    remote = store.bucket().list_objects("")
    keep = P.lane_keep_set(remote)
    plan = P.sync_tree(
        store.bucket(),
        dist,
        delete_extras=True,
        keep=keep,
    )
    # lane objects: not deleted AND not overwritten by the captured bytes
    assert store.objects["status/state.json"] == b"FRESH lane heartbeat"
    assert store.objects["watch/watch.json"] == b"FRESH watch doc"
    assert "status/state.json" not in store.put_calls
    assert "watch/watch.json" not in store.put_calls
    assert set(plan.put_skipped) == {"status/state.json", "watch/watch.json"}
    # ordinary deltas still apply
    assert store.objects["index.html"] == b"new-root"
    assert "old/index.html" in store.delete_calls


def test_sync_tree_write_time_belt_refuses_a_lane_delete(tmp_path: Path) -> None:
    store = _FakeSiteStore()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("x", encoding="utf-8")
    plan = P.SyncPlan(
        uploads=(), deletes=("watch/state.json",), protected_kept=(), remote_known=True
    )
    with pytest.raises(P.PublishError, match="lane-kept|protected"):
        P.sync_tree(store.bucket(), dist, delete_extras=True, plan=plan)
    assert store.delete_calls == []


# --- the transform -----------------------------------------------------------


def _prestate_fixture(root: Path) -> Path:
    """A minimal captured tree shaped like the 09-27 serve."""
    pages = {
        "index.html": (
            '<html><body><main id="main"><p>home</p>'
            '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
            'or a privacy or safety concern?<a data-testid="dispute-link" '
            'href="/dispute/">Dispute or correct this record</a> — one click, '
            "no account required.</p></main></body></html>"
        ),
        "dossier/okc/index.html": (
            '<html><body><main id="main"><p>dossier</p>'
            '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
            'or a privacy or safety concern?<a data-testid="dispute-link" '
            'href="/dispute/">Dispute or correct this record</a> — one click, '
            "no account required.</p></main></body></html>"
        ),
        "visual-language/index.html": (
            '<html><body><main id="main"><p>Oklahoma City Police Department</p>'
            "</main></body></html>"
        ),
        "editorial-standards/index.html": (
            '<html><body><main id="main"><h1>Editorial standards</h1>'
            "<p>Releasable — every finding dispositioned</p>"
            '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
            'or a privacy or safety concern?<a data-testid="dispute-link" '
            'href="/dispute/">Dispute or correct this record</a> — one click, '
            "no account required.</p></main></body></html>"
        ),
        "dispute/index.html": (
            '<html><body><main id="main"><h1>Dispute or correct a record</h1>'
            "<p>This channel is reachable in one click from any claim.</p>"
            '<p class="sig-dispute" data-testid="dispute-link-block">Something wrong, '
            'or a privacy or safety concern?<a data-testid="dispute-link" '
            'href="/dispute/">Dispute or correct this record</a> — one click, '
            "no account required.</p></main></body></html>"
        ),
        "task/new/demo_x/index.html": "<html><body>demo task</body></html>",
        "task/new/WyJq/index.html": "<html><body>task page</body></html>",
        "map/style.json": "{}",
    }
    for rel, text in pages.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_transform_removes_the_three_items_and_sweeps_denied(tmp_path: Path) -> None:
    src = _prestate_fixture(tmp_path / "prestate")
    dst = tmp_path / "dist"
    report = T.transform_prestatetree(src, dst)

    # visual-language + the whole denied task/new prefix are gone → 404
    assert not (dst / "visual-language").exists()
    assert not (dst / "task").exists()
    assert "visual-language/index.html" in report.removed_objects
    assert "task/new/WyJq/index.html" in report.removed_objects

    # the dispute promise is the honest DL-01 wording site-wide
    pages = (
        "index.html",
        "dossier/okc/index.html",
        "editorial-standards/index.html",
        "dispute/index.html",
    )
    for page in pages:
        text = (dst / page).read_text(encoding="utf-8")
        assert "one click, no account required" not in text, page
        assert "reports arrive by e-mail" in text, page
    assert report.promise_replacements == 4

    # editorial-standards → the holding notice (N-1, no data-copy)
    es = (dst / "editorial-standards" / "index.html").read_text(encoding="utf-8")
    assert "Not yet performed." in es
    assert "data-copy" not in es
    assert "Releasable" not in es
    assert "incorrect and has been removed" in es

    # /dispute/ → the honest wording, no inbox promise, no data-copy
    dp = (dst / "dispute" / "index.html").read_text(encoding="utf-8")
    assert "Reports and corrections arrive by e-mail" in dp
    assert "one click" not in dp
    assert "data-copy" not in dp
    assert 'data-intake-email="unset"' not in dp

    # surviving real content is untouched
    assert (dst / "dossier/okc/index.html").is_file()
    assert (dst / "map/style.json").is_file()


def test_transform_refuses_a_pending_data_copy_collision(tmp_path: Path) -> None:
    src = _prestate_fixture(tmp_path / "prestate")
    target = src / "dossier/okc/index.html"
    target.write_text(
        '<html><body><main id="main"><p data-copy="XX-99">x</p></main></body></html>',
        encoding="utf-8",
    )
    with pytest.raises(P.PublishError, match="data-copy|copy"):
        T.transform_prestatetree(src, tmp_path / "dist")


def test_transform_refuses_without_the_promise(tmp_path: Path) -> None:
    src = _prestate_fixture(tmp_path / "prestate")
    (src / "index.html").write_text("<html><body>no promise</body></html>", encoding="utf-8")
    (src / "dossier/okc/index.html").write_text("<html><body>x</body></html>", encoding="utf-8")
    (src / "dispute/index.html").write_text("<html><body>x</body></html>", encoding="utf-8")
    (src / "editorial-standards/index.html").write_text(
        '<html><body><main id="main">x</main></body></html>', encoding="utf-8"
    )
    with pytest.raises(P.PublishError, match="one click"):
        T.transform_prestatetree(src, tmp_path / "dist")


def test_denied_prefixes_are_a_union_with_a_floor(tmp_path: Path) -> None:
    prefixes = T.denied_prefixes()
    for expected in (
        "curate/",
        "task/new/",
        "releases/",
        "research-dossier/",
        "intake/",
        "visual-language/",
    ):
        assert expected in prefixes


# --- the restore script (offline: a canned gcloud on PATH) --------------------


def _fake_gcloud(tmp_path: Path, precopy: list[str], live: list[str]) -> Path:
    """A `gcloud` stub answering `storage ls` with the canned listings — the
    URI argument selects which set it prints (the restore script's `**`
    suffix is glob-quoted, so the arg arrives literal)."""
    stub = tmp_path / "gcloud"
    precopy_uri = "gs://fake-sig-restricted/rollback/sig-web-pre-x/fake-sig-web/"
    live_uri = "gs://fake-sig-web/"

    def block(uri: str, names: list[str]) -> str:
        body = "".join(f"    echo '{uri}{n}'\n" for n in names)
        return f"    {uri}*)\n{body}    ;;\n"

    stub.write_text(
        "#!/usr/bin/env bash\n"
        'uri="${!#}"\n'
        'case "$uri" in\n'
        + block(precopy_uri, precopy)
        + block(live_uri, live)
        + "    *) echo 'unknown uri' >&2; exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub


def _run_restore(args: list[str], tmp_path: Path, gcloud: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = f"{gcloud.parent}:{env['PATH']}"
    return subprocess.run(
        ["bash", str(RESTORE), *args], capture_output=True, text=True, env=env, cwd=REPO
    )


def test_restore_dry_run_enumerates_the_bounded_plan(tmp_path: Path) -> None:
    gcloud = _fake_gcloud(
        tmp_path,
        precopy=[
            "index.html",
            "dispute/index.html",
            "watch/state.json",
            "r/p-abc/x.json",
        ],
        live=[
            "index.html",
            "dispute/index.html",
            "new-page/index.html",  # publish-added → deleted by restore
            "watch/state.json",  # lane → kept (delete-skip AND put-skip)
            "status/archive/2026-11-16.json",  # lane, absent from precopy → kept
            "r/p-abc/x.json",
            "releases/p-old/index.html",  # protected → kept
            "conf/withdrawn.conf",  # protected → kept
        ],
    )
    proc = _run_restore(
        ["gs://fake-sig-restricted/rollback/sig-web-pre-x/fake-sig-web/", "--dry-run"],
        tmp_path,
        gcloud,
    )
    assert proc.returncode == 0, proc.stderr
    assert "DELETE new-page/index.html" in proc.stdout
    assert "releases/p-old/index.html" not in proc.stdout.split("planned deletes:")[-1]
    assert "status/archive/2026-11-16.json" not in proc.stdout.split("planned deletes:")[-1]
    assert "SKIP-PUT watch/state.json" in proc.stdout
    assert "nothing written" in proc.stderr


def test_restore_refuses_a_non_sig_web_target(tmp_path: Path) -> None:
    proc = _run_restore(
        ["gs://fake-sig-restricted/rollback/x/not-a-site-bucket/", "--dry-run"],
        tmp_path,
        tmp_path / "gcloud-missing",
    )
    assert proc.returncode == 2
    assert "sig-web" in proc.stderr
