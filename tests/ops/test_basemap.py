# SPDX-License-Identifier: Apache-2.0
"""P36.33 (K1 MAP-02, SIG-UI-100): the basemap pipeline + host machinery.

Every assertion is a contract, never a living record (OM-15): the lock's
shape, the glyph fetch/verify chain over an injected fetcher, the
context.pmtiles build over a fixture pack, the refresh/host plan + the
OM-19 apply gate (queued 42), the kill-switch flip, and the offline
`sig-ops basemap check` posture proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops import basemap

REPO = Path(__file__).resolve().parents[2]
LOCK_PATH = REPO / "ops" / "basemap.lock.json"


def _lock(tmp_path: Path | None = None) -> dict:
    lock = json.loads(LOCK_PATH.read_text())
    if tmp_path is not None:
        (tmp_path / "lock.json").write_text(json.dumps(lock))
    return lock


class TestLock:
    def test_committed_lock_validates(self):
        lock = basemap.load_lock(LOCK_PATH)
        assert lock["schema"] == "sig.basemap-lock/1"
        assert lock["host"]["origin"].startswith("https://")
        assert lock["serving"]["active_source"] == "basemap"

    def test_decisions_carried_verbatim(self):
        lock = basemap.load_lock(LOCK_PATH)
        for k in ("D-K1-1", "Q-31/D-K1-2 [A-3]", "D-K1-3 [B-22]"):
            assert k in lock["decisions"]

    def test_invalid_lock_refuses(self):
        assert "schema" in " ".join(basemap.validate_lock({"schema": "x"}))

    def test_served_key_falls_back_to_reference(self):
        lock = _lock()
        assert basemap.served_key(lock) == "basemap/20260930.pmtiles"
        lock["host"]["served"] = {"key": "basemap/20261101.pmtiles"}
        assert basemap.served_key(lock) == "basemap/20261101.pmtiles"

    def test_pairing_refuses_v5_tiles(self):
        lock = _lock()
        lock["upstream"]["reference_build"]["tile_schema"] = "v5"
        assert any("pairing" in f for f in basemap.validate_lock(lock))


class TestGlyphs:
    def test_ranges_cover_unicode(self):
        assert len(basemap.glyph_ranges()) == 256
        assert basemap.glyph_ranges()[0] == "0-255"
        assert basemap.glyph_ranges()[-1] == "65280-65535"

    def test_fetch_writes_tree_and_manifest(self, tmp_path):
        lock = _lock()
        lock["glyphs"]["fontstacks"] = ["Noto Sans Regular"]

        def fake_fetch(url: str) -> bytes:
            return ("blob:" + url.rsplit("/", 1)[-1]).encode()

        files, _ = basemap.fetch_glyph_set(lock, fetch=fake_fetch)
        assert "Noto Sans Regular/0-255.pbf" in files
        assert "OFL.txt" in files
        manifest = basemap.write_glyph_tree(files, tmp_path / "fonts", lock, fetched_at="t")
        assert manifest["schema"] == "sig.basemap-glyphs/1"
        assert basemap.verify_glyph_tree(tmp_path / "fonts") == []
        (tmp_path / "fonts" / "manifest.json").read_text()

    def test_verify_catches_drift(self, tmp_path):
        lock = _lock()
        lock["glyphs"]["fontstacks"] = ["Noto Sans Regular"]
        files, _ = basemap.fetch_glyph_set(lock, fetch=lambda u: b"x" + u.encode()[:4])
        basemap.write_glyph_tree(files, tmp_path / "fonts", lock, fetched_at="t")
        (tmp_path / "fonts" / "Noto Sans Regular" / "0-255.pbf").write_bytes(b"drift")
        failures = basemap.verify_glyph_tree(tmp_path / "fonts")
        assert any("sha256 drift" in f for f in failures)

    def test_committed_glyph_tree_verifies(self):
        assert basemap.verify_glyph_tree(REPO / "web" / "public" / "map" / "fonts") == []

    def test_lock_manifest_root_stamped(self):
        lock = basemap.load_lock(LOCK_PATH)
        man = json.loads((REPO / "web" / "public" / "map" / "fonts" / "manifest.json").read_text())
        assert lock["glyphs"]["manifest_sha256"] == man["root"]


class TestContextBuild:
    def test_build_from_fixture_pack(self, tmp_path):
        import sys

        sys.path.insert(0, str(REPO / "tests" / "exports"))
        from boundary_pack_fixtures import (  # noqa: E402
            build_fixture_pack,
            write_fixture_spec,
        )

        from exports import boundary_pack  # noqa: E402

        spec = boundary_pack.load_spec(write_fixture_spec(tmp_path / "fixture.toml"))
        pack, _manifest = build_fixture_pack(tmp_path, spec)
        summary = basemap.build_context_pmtiles(pack, tmp_path / "context.pmtiles")
        assert summary["features"] > 0
        assert summary["tiles"] > 0
        blob = (tmp_path / "context.pmtiles").read_bytes()
        header = blob[:127]
        assert header[:7] == b"PMTiles"
        assert summary["boundaries_root"]

    def test_unverified_pack_refuses(self, tmp_path):
        with pytest.raises(basemap.BasemapError):
            basemap.build_context_pmtiles(tmp_path / "nope", tmp_path / "x.pmtiles")


class TestApplyGate:
    def test_apply_gate_reports_unmet_env(self, monkeypatch):
        for v in (
            "SIG_CF_ACCOUNT_ID",
            "SIG_CF_API_TOKEN",
            "SIG_R2_ACCESS_KEY_ID",
            "SIG_R2_SECRET_ACCESS_KEY",
            "SIG_BASEMAP_AUTHOR",
        ):
            monkeypatch.delenv(v, raising=False)
        unmet = basemap.apply_gate(_lock(), env={basemap.NOW_ENV: "2026-10-30T12:00:00Z"})
        assert len(unmet) >= 5

    def test_ar3_windows_block(self):
        unmet = basemap.apply_gate(
            _lock(),
            env={
                "SIG_CF_ACCOUNT_ID": "a",
                "SIG_CF_API_TOKEN": "t",
                "SIG_R2_ACCESS_KEY_ID": "k",
                "SIG_R2_SECRET_ACCESS_KEY": "s",
                "SIG_BASEMAP_AUTHOR": "op",
                basemap.NOW_ENV: "2026-10-07T12:00:00Z",
            },
        )
        assert any("batch window" in u for u in unmet)
        unmet = basemap.apply_gate(
            _lock(),
            env={
                "SIG_CF_ACCOUNT_ID": "a",
                "SIG_CF_API_TOKEN": "t",
                "SIG_R2_ACCESS_KEY_ID": "k",
                "SIG_R2_SECRET_ACCESS_KEY": "s",
                "SIG_BASEMAP_AUTHOR": "op",
                basemap.NOW_ENV: "2026-10-30T04:00:00Z",
            },
        )
        assert any("03:00-06:30Z" in u for u in unmet)

    def test_cli_apply_queues_42(self):
        rc = basemap.main(["refresh", "--apply"])
        assert rc == 42
        rc = basemap.main(["host", "--apply"])
        assert rc == 42


class TestPlans:
    def test_refresh_plan_verbatim_shape(self):
        lines = basemap.refresh_plan(_lock())
        assert any("b3sum" in line for line in lines)
        assert any("versioned key" in line for line in lines)

    def test_host_plan_carries_cors_and_rerun(self):
        lines = basemap.host_plan(_lock())
        joined = "\n".join(lines)
        assert "CORS" in joined and "immutable" in joined
        assert "implement-spec spec=docs/tickets/374_P36.33" in joined

    def test_resolve_build(self):
        index = [
            {"key": "20260101.pmtiles", "size": 1, "b3sum": "x", "version": "4.15.2"},
            {"key": "20260102.pmtiles", "size": 2, "b3sum": "y", "version": "4.15.2"},
        ]
        row = basemap.resolve_build("u", "latest", fetch=lambda u: json.dumps(index).encode())
        assert row["key"] == "20260102.pmtiles"
        with pytest.raises(basemap.BasemapError):
            basemap.resolve_build(
                "u", "20250101.pmtiles", fetch=lambda u: json.dumps(index).encode()
            )
        bad = [{"key": "x.pmtiles", "size": 1, "b3sum": "z", "version": "5.0"}]
        with pytest.raises(basemap.BasemapError):
            basemap.resolve_build("u", "latest", fetch=lambda u: json.dumps(bad).encode())


class TestKillSwitch:
    def test_check_does_not_write(self, tmp_path):
        lock_file = tmp_path / "lock.json"
        lock_file.write_text(json.dumps(_lock()))
        basemap.kill_switch(lock_file, apply=False)
        assert json.loads(lock_file.read_text())["serving"]["active_source"] == "basemap"

    def test_apply_flips_to_context(self, tmp_path):
        lock_file = tmp_path / "lock.json"
        lock_file.write_text(json.dumps(_lock()))
        basemap.kill_switch(lock_file, apply=True)
        assert json.loads(lock_file.read_text())["serving"]["active_source"] == "context"


class TestCheck:
    def test_check_green_on_repo(self):
        results = {r.id: r for r in basemap.run_checks(REPO)}
        assert results["lock-parse"].ok
        assert results["styles"].ok, results["styles"].detail
        assert results["glyphs"].ok
        assert results["csp-connect-src"].ok
        assert results["budget-alert"].ok
        assert basemap.main(["check", "--repo-root", str(REPO)]) == 0


class TestHostApply:
    def test_host_apply_calls_api_in_order(self):
        calls = []

        def fake_api(token, account, method, path, body=None):
            calls.append((method, path))
            return {"ok": True}

        rec = basemap.host_apply(
            _lock(),
            env={"SIG_CF_ACCOUNT_ID": "a", "SIG_CF_API_TOKEN": "t", "SIG_BASEMAP_AUTHOR": "op"},
            api=fake_api,
        )
        assert [c[0] for c in calls] == ["POST", "PUT", "POST"]
        assert calls[0][1] == "/r2/buckets"
        assert "cors" in calls[1][1]
        assert "domains/custom" in calls[2][1]
        assert rec["author"] == "op"
