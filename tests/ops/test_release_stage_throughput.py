# SPDX-License-Identifier: Apache-2.0
"""D-P37.65a-3 — the release-stage throughput fix's contract tests.

The defect the deferral bound: ``sig-ops release stage --apply`` ran a serial
``store.insert`` + per-object ``lock.refresh()`` (a full
``registry_state_digest``, ~6 GCS reads) and paid a ``gcloud
… print-access-token`` subprocess per request — measured ~5–6 s wall each,
~40–60 s/object, 8 objects in ~9.6 min before a token timeout killed the verb
mid-plan with the lock held.

The fix's pins:

* the access token resolves once and is reused until near expiry — no
  subprocess per request — and a transient resolution failure bounded-retries
  instead of hard-exiting;
* transient HTTP failures (5xx, throttling, transport errors) bounded-retry;
  a 401 drops the cached token and re-resolves once; a 412 precondition is
  never retried;
* ``lock.refresh()`` is a liveness heartbeat on a time/count interval — never
  per object — while ``lock.release()`` still re-checks the digest;
* inserts run through a bounded worker pool; the identical-byte resume skip
  is decided from a paged staged listing (no POST+stat pair per object) and a
  same-name different-byte object still refuses as a name collision.
"""

from __future__ import annotations

import time
import urllib.error
from pathlib import Path

import pytest

from ops import gcs as G
from ops import release_pipeline as rp


def _store(tmp_path: Path) -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path / "registry")


def _release_tree(work: Path, pub: str, objects: int = 2) -> Path:
    """A staged-shape tree with ``objects`` files split across two namespaces."""
    per_ns = max(1, objects // 2)
    made = 0
    for ns in ("r", "releases"):
        d = work / ns / pub
        d.mkdir(parents=True, exist_ok=True)
        for i in range(per_ns):
            (d / f"obj-{i:05d}.json").write_text(f'{{"ns":"{ns}","i":{i}}}', encoding="utf-8")
            made += 1
        if made >= objects:
            break
    return work


# --------------------------------------------------------------------------- #
# The token provider — cached, expiry-aware, bounded-retry                    #
# --------------------------------------------------------------------------- #


def _provider(**kw) -> G.CachingTokenProvider:
    kw.setdefault("env", lambda _k: "")
    kw.setdefault("metadata_token", lambda _t: None)
    kw.setdefault("sleep", lambda _s: None)
    return G.CachingTokenProvider(**kw)


def _sequenced(prefix: str):
    """A token source returning ``<prefix>-1``, ``<prefix>-2``, … and
    recording how often resolution ran (the subprocess count the fix kills)."""
    calls = {"n": 0}

    def source(_t: float) -> str:
        calls["n"] += 1
        return f"{prefix}-{calls['n']}"

    return source, calls


def test_token_resolves_once_and_is_reused_within_ttl() -> None:
    gcloud, calls = _sequenced("tok")
    p = _provider(gcloud_token=gcloud)
    assert [p() for _ in range(5)] == ["tok-1"] * 5
    assert calls["n"] == 1  # no subprocess per request


def test_token_re_resolves_after_the_gcloud_ttl() -> None:
    now = {"t": 1000.0}
    gcloud, calls = _sequenced("tok")
    p = _provider(gcloud_token=gcloud, clock=lambda: now["t"], gcloud_ttl=60.0)
    assert p() == "tok-1"
    now["t"] += 61.0  # past the conservative gcloud TTL
    assert p() == "tok-2"
    assert calls["n"] == 2


def test_metadata_expiry_drives_the_refresh() -> None:
    now = {"t": 0.0}
    calls = {"n": 0}

    def meta(_t: float) -> dict:
        calls["n"] += 1
        return {"access_token": f"mtok-{calls['n']}", "expires_in": 100.0}

    p = _provider(metadata_token=meta, clock=lambda: now["t"], expiry_margin=10.0)
    assert p() == "mtok-1"
    now["t"] = 89.0  # inside the margin-before-expiry window
    assert p() == "mtok-1"
    now["t"] = 91.0  # within expiry margin → refresh
    assert p() == "mtok-2"


def test_env_override_token_is_static_for_the_process() -> None:
    def gcloud(_t: float) -> str:
        raise AssertionError("gcloud must not run under an explicit token")

    p = _provider(env=lambda _k: "explicit-tok", gcloud_token=gcloud)
    assert p() == p() == "explicit-tok"


def test_transient_resolution_failure_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky(_t: float) -> str | None:
        calls["n"] += 1
        return "tok" if calls["n"] >= 2 else None  # one transient miss

    p = _provider(gcloud_token=flaky)
    assert p() == "tok"
    assert calls["n"] == 2


def test_resolution_is_bounded_never_a_hang() -> None:
    calls = {"n": 0}

    def gone(_t: float) -> None:
        calls["n"] += 1
        return None

    p = _provider(gcloud_token=gone, attempts=3)
    assert p() is None
    assert calls["n"] == 3  # bounded — then the caller's honest GcsError


def test_invalidate_forces_re_resolution() -> None:
    gcloud, calls = _sequenced("t")
    p = _provider(gcloud_token=gcloud)
    assert p() == "t-1"
    p.invalidate()
    assert p() == "t-2"


# --------------------------------------------------------------------------- #
# The request path — bounded transient retry, never a retried refusal         #
# --------------------------------------------------------------------------- #


def _bucket(opener, provider=None) -> G.GcsBucket:
    return G.GcsBucket("b", token_provider=provider or (lambda: "t"), opener=opener)


def test_transient_5xx_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        return (503, b"") if calls["n"] == 1 else (200, b"{}")

    bucket = _bucket(opener)
    assert bucket.get_object("x") == b"{}"
    assert calls["n"] == 2


def test_transport_error_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("timed out")
        return 200, b"{}"

    bucket = _bucket(opener)
    bucket.put_object("x", b"")
    assert calls["n"] == 3


def test_persistent_failure_raises_bounded_never_forever() -> None:
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        raise urllib.error.URLError("down")

    with pytest.raises(G.GcsError):
        _bucket(opener).put_object("x", b"")
    assert calls["n"] == 3


def test_4xx_is_never_retried() -> None:
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        return 403, b"denied"

    with pytest.raises(G.GcsError, match="HTTP 403"):
        _bucket(opener).list_objects("x/")
    assert calls["n"] == 1


def test_412_precondition_is_never_retried() -> None:
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        return 412, b""

    with pytest.raises(G.GcsPreconditionFailed):
        _bucket(opener).insert_object("x", b"", if_generation_match=0)
    assert calls["n"] == 1


def test_401_drops_the_cached_token_and_re_resolves_once() -> None:
    gcloud, resolutions = _sequenced("tok")
    provider = _provider(gcloud_token=gcloud)
    calls = {"n": 0}

    def opener(req, timeout):
        calls["n"] += 1
        token = req.headers["Authorization"]
        if calls["n"] == 1:
            return 401, b""  # the cached token was revoked early
        assert token == "Bearer tok-2"  # invalidated → re-resolved
        return 200, b"{}"

    _bucket(opener, provider=provider).put_object("x", b"")
    assert resolutions["n"] == 2


# --------------------------------------------------------------------------- #
# The stage loop — amortised heartbeat, bounded pool, listing-decided resume  #
# --------------------------------------------------------------------------- #


class _CountingStore:
    """A LocalDirStore wrapper counting calls — the digest/refresh and
    insert/stat costs the fix amortises."""

    def __init__(self, inner: rp.LocalDirStore) -> None:
        self.inner = inner
        self.counts = {"insert": 0, "stat": 0, "read": 0, "list": 0, "details": 0, "delete": 0}

    def describe(self) -> str:
        return self.inner.describe()

    def read(self, name):
        self.counts["read"] += 1
        return self.inner.read(name)

    def stat(self, name):
        self.counts["stat"] += 1
        return self.inner.stat(name)

    def insert(self, name, body, *, content_type="application/octet-stream"):
        self.counts["insert"] += 1
        return self.inner.insert(name, body, content_type=content_type)

    def replace(self, name, body, *, generation, content_type="application/octet-stream"):
        return self.inner.replace(name, body, generation=generation, content_type=content_type)

    def delete(self, name):
        self.counts["delete"] += 1
        return self.inner.delete(name)

    def list(self, prefix):
        self.counts["list"] += 1
        return self.inner.list(prefix)

    def details(self, prefix):
        self.counts["details"] += 1
        return self.inner.details(prefix)


def _registry_reads(store: _CountingStore) -> int:
    return store.counts["read"]


def test_parallel_stage_stages_the_whole_plan(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "1" * 64
    work = _release_tree(tmp_path / "work", pub, objects=24)
    out = rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    assert out["staged"] == 24 and out["resumed"] == 0 and out["applied"] is True
    assert len(store.list(f"staged/r/{pub}/")) + len(store.list(f"staged/releases/{pub}/")) == 24


def test_parallel_resume_skips_identical_bytes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "2" * 64
    work = _release_tree(tmp_path / "work", pub, objects=20)
    rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    again = rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    assert again["staged"] == 0 and again["resumed"] == 20


def test_parallel_name_collision_refuses_and_overwrites_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "3" * 64
    work = _release_tree(tmp_path / "work", pub, objects=16)
    rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    victim = work / "r" / pub / "obj-00000.json"
    victim.write_text("mutated", encoding="utf-8")
    with pytest.raises(rp.NameCollision):
        rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    assert store.read(f"staged/r/{pub}/obj-00000.json") == b'{"ns":"r","i":0}'
    # the refusal is recorded, not masked — and the dead run's lock stays held
    assert store.read("registry/LOCK") is not None


def test_lock_refresh_is_a_heartbeat_not_per_object(tmp_path: Path) -> None:
    inner = _store(tmp_path)
    store = _CountingStore(inner)
    pub = "p-" + "4" * 64
    work = _release_tree(tmp_path / "work", pub, objects=40)
    rp.verb_stage(
        store,
        apply_=True,
        work_dir=work,
        workers=4,
        lock_refresh_seconds=3600.0,  # heartbeat off: count + time intervals out of reach
        lock_refresh_objects=10_000,
    )
    # store.read calls: 1 lock probe + 5-file digest at acquire + 5-file
    # digest at release = 11 — the old per-object shape was
    # 1 + 5 × (40 objects + 2) = 211.
    assert _registry_reads(store) == 11


def test_heartbeat_fires_on_the_count_interval(tmp_path: Path) -> None:
    inner = _store(tmp_path)
    store = _CountingStore(inner)
    pub = "p-" + "5" * 64
    work = _release_tree(tmp_path / "work", pub, objects=40)
    rp.verb_stage(
        store,
        apply_=True,
        work_dir=work,
        workers=1,
        lock_refresh_seconds=3600.0,
        lock_refresh_objects=8,
    )
    # 1 lock probe + acquire digest(5) + floor(40/8)=5 heartbeats ×5 files
    # + release digest(5) → 36 registry reads.
    assert _registry_reads(store) == 36


def test_drift_mid_run_still_refuses_at_release(tmp_path: Path) -> None:
    """The amortised heartbeat never weakens the stale-generation guard:
    registry drift under the held lock is caught no later than release."""
    inner = _store(tmp_path)
    store = _CountingStore(inner)
    pub = "p-" + "6" * 64
    work = _release_tree(tmp_path / "work", pub, objects=10)
    orig = inner.insert
    fired = {"n": 0}

    def drifting_insert(name, body, *, content_type="application/octet-stream"):
        out = orig(name, body, content_type=content_type)
        if name.startswith("staged/") and not fired["n"]:
            fired["n"] = 1
            orig("registry/latest.json", b"{}", content_type="application/json")
        return out

    inner.insert = drifting_insert  # type: ignore[method-assign]
    with pytest.raises(rp.StaleGeneration):
        rp.verb_stage(
            store,
            apply_=True,
            work_dir=work,
            workers=2,
            lock_refresh_seconds=3600.0,  # heartbeats off → the release() check catches it
            lock_refresh_objects=10_000,
        )


def test_resume_decides_from_the_listing_no_post_stat_pairs(tmp_path: Path) -> None:
    inner = _store(tmp_path)
    store = _CountingStore(inner)
    pub = "p-" + "7" * 64
    work = _release_tree(tmp_path / "work", pub, objects=30)
    rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    store.counts.update({k: 0 for k in store.counts})
    again = rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    assert again["resumed"] == 30
    # the listing path: 4 namespace listings (details) + the lock + journal
    # inserts — zero per-object insert/stat pairs.
    assert store.counts["details"] == 4
    assert store.counts["stat"] == 0
    assert store.counts["insert"] == 2  # registry/LOCK + the staged journal event


def test_staged_event_carries_the_worker_width(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pub = "p-" + "8" * 64
    work = _release_tree(tmp_path / "work", pub, objects=4)
    rp.verb_stage(store, apply_=True, work_dir=work, workers=4)
    staged_events = [e for e in rp.list_events(store) if e["verb"] == "staged"]
    assert staged_events and staged_events[0]["stage_workers"] == 4


# --------------------------------------------------------------------------- #
# The owed rate benchmark — the measured obj/s the deferral's verify cell      #
# names, over a latency-honest fake store                                     #
# --------------------------------------------------------------------------- #


class _LatentStore:
    """A LocalDirStore that bills a fixed latency per remote-shaped call —
    the ~150 ms a real GCS JSON-API round trip costs, so the measured obj/s
    is an honest projection of the live path, not a disk-speed artefact."""

    def __init__(self, inner: rp.LocalDirStore, latency_s: float) -> None:
        self.inner = inner
        self.latency = latency_s

    def _bill(self) -> None:
        time.sleep(self.latency)

    def describe(self) -> str:
        return f"latent({self.latency}s):{self.inner.describe()}"

    def read(self, name):
        self._bill()
        return self.inner.read(name)

    def stat(self, name):
        self._bill()
        return self.inner.stat(name)

    def insert(self, name, body, *, content_type="application/octet-stream"):
        self._bill()
        return self.inner.insert(name, body, content_type=content_type)

    def replace(self, name, body, *, generation, content_type="application/octet-stream"):
        self._bill()
        return self.inner.replace(name, body, generation=generation, content_type=content_type)

    def delete(self, name):
        self._bill()
        return self.inner.delete(name)

    def list(self, prefix):
        self._bill()
        return self.inner.list(prefix)

    def details(self, prefix):
        self._bill()  # one paged call stands in for the whole listing
        return self.inner.details(prefix)


def test_parallel_stage_sustains_a_bounded_plan_rate(tmp_path: Path) -> None:
    """The throughput contract: under a latency-honest fake GCS the pooled
    stage's obj/s leaves the measured 0.014 obj/s baseline by orders of
    magnitude — the run ledger records the full-scale projection."""
    n = 120
    latency = 0.05  # ~a third of a real GCS JSON-API RTT — the test stays fast
    inner = _store(tmp_path)
    pub = "p-" + "9" * 64
    work = _release_tree(tmp_path / "work", pub, objects=n)

    store = _LatentStore(inner, latency)
    t0 = time.monotonic()
    out = rp.verb_stage(store, apply_=True, work_dir=work, workers=8)
    parallel_s = time.monotonic() - t0
    assert out["staged"] == n
    parallel_rate = n / parallel_s

    # Serial reference under the same latency: workers=1 keeps the original
    # per-object insert shape (heartbeat still amortised — the fix's floor).
    inner2 = rp.LocalDirStore(tmp_path / "registry2")
    store2 = _LatentStore(inner2, latency)
    t0 = time.monotonic()
    out2 = rp.verb_stage(store2, apply_=True, work_dir=work, workers=1)
    serial_s = time.monotonic() - t0
    assert out2["staged"] == n
    serial_rate = n / serial_s

    # The pool buys real concurrency: well past 3× the serial rate at 8
    # workers, and thousands of times the measured 0.014 obj/s baseline —
    # the ~380-day serial projection becomes a bounded run window (the
    # ledger's full-latency projection: ~40–110 obj/s ⇒ ~1.2–3.2 h).
    assert parallel_rate > serial_rate * 3
    assert parallel_rate > 40
