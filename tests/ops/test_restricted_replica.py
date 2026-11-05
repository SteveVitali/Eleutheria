# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_restricted_replica.py — the P37.3 replica runner
(SIG-STORE-048, ADR-177). Fixture-verified over a fake GcsBucket: the
evidence/captures/ exclusion (the sealed-material exclusion), the
dest == source − excluded parity, idempotent re-runs, the record schema,
and the CLI exit codes — never a living read (OM-15).
"""

from __future__ import annotations

import json

from ops.gcs import GcsBucket
from ops.restricted_replica import (
    DEFAULT_EXCLUDED_PREFIXES,
    RECORD_PREFIX,
    plan_replica,
    run_replica,
    verify_replica,
)


class FakeBucket:
    """In-memory GcsBucket-shaped fake: list details, copyTo, put, meta."""

    def __init__(self, bucket: str, objects: dict[str, bytes] | None = None):
        self.bucket = bucket
        self.objects: dict[str, bytes] = dict(objects or {})
        self.deleted: list[str] = []

    def _md5(self, b: bytes) -> str:
        import base64
        import hashlib

        return base64.b64encode(hashlib.md5(b).digest()).decode()

    def list_object_details(self, prefix: str) -> list[dict]:
        return [
            {"name": n, "md5Hash": self._md5(b), "size": str(len(b))}
            for n, b in sorted(self.objects.items())
            if n.startswith(prefix)
        ]

    def list_objects(self, prefix: str) -> list[str]:
        return [n for n in sorted(self.objects) if n.startswith(prefix)]

    def copy_object_to(self, name: str, *, dest: FakeBucket, dest_name: str | None = None) -> dict:
        dest.objects[dest_name or name] = self.objects[name]
        return {"name": dest_name or name, "bucket": dest.bucket}

    def put_object(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> str:
        self.objects[name] = body
        return name

    def get_object_meta(self, name: str) -> dict | None:
        if name not in self.objects:
            return None
        return {"name": name, "md5Hash": self._md5(self.objects[name])}

    def get_object(self, name: str) -> bytes:
        return self.objects[name]


SRC = {
    "ops/runs/a/2026-11-01/1.json": b"run-a",
    "ops/probes/2026-11-01/t.jsonl": b"probe",
    "exports/national/2026-09-27/x.parquet": b"export",
    "evidence/captures/ocfl-root-1/inventory.json": b"sealed-or-not-capture",
    "evidence/captures/ocfl-root-2/inventory.json": b"capture-2",
    "ops/seal/deny-set.json": b"deny-metadata",
}


def test_plan_excludes_the_superseded_capture_store_wholesale() -> None:
    plan = plan_replica(
        sorted(SRC), source_bucket="p-sig-restricted", dest_bucket="p-sig-restricted-dr"
    )
    assert set(plan.excluded) == {n for n in SRC if n.startswith("evidence/captures/")}
    # the seal deny-set is metadata, never material — it DOES replicate
    assert "ops/seal/deny-set.json" in plan.to_copy


def test_run_copies_all_but_excluded_and_records_on_dest() -> None:
    src = FakeBucket("p-sig-restricted", SRC)
    dst = FakeBucket("p-sig-restricted-dr")
    rec = run_replica(src, dst, now="2026-11-05T15:00:00Z")
    # nothing under evidence/captures/ reached the replica — sealed material
    # can never land on the off-instance copy (S4c)
    assert not any(n.startswith("evidence/captures/") for n in dst.objects)
    assert rec["counts"]["excluded"] == 2
    assert rec["counts"]["copied"] == len(SRC) - 2
    assert rec["verified"] is True
    # the record itself landed on the destination
    recs = [n for n in dst.objects if n.startswith(RECORD_PREFIX)]
    assert len(recs) == 1
    stored = json.loads(dst.objects[recs[0]])
    assert stored["schema"] == "sig.restricted-replica/1"


def test_rerun_is_a_noop_for_identical_objects() -> None:
    src = FakeBucket("p-sig-restricted", SRC)
    dst = FakeBucket("p-sig-restricted-dr")
    run_replica(src, dst, now="2026-11-05T15:00:00Z")
    # remove the record object so the second run's copy set is compared clean
    rec = run_replica(src, dst, now="2026-11-05T16:00:00Z")
    assert rec["counts"]["copied"] == 0
    assert rec["counts"]["skipped_unchanged"] == len(SRC) - 2


def test_verify_fails_loud_on_missing_and_mismatch() -> None:
    src = FakeBucket("p-sig-restricted", SRC)
    dst = FakeBucket("p-sig-restricted-dr")
    verdict = verify_replica(src, dst)
    assert verdict["ok"] is False
    assert set(verdict["missing"]) == set(
        plan_replica(sorted(SRC), source_bucket="s", dest_bucket="d").to_copy
    )
    # a divergent dest object is a mismatch, never smoothed
    dst2 = FakeBucket(
        "p-sig-restricted-dr",
        {k: v for k, v in SRC.items() if not k.startswith("evidence/captures/")},
    )
    dst2.objects["ops/probes/2026-11-01/t.jsonl"] = b"tampered"
    v2 = verify_replica(src, dst2)
    assert v2["ok"] is False and v2["mismatches"] == ["ops/probes/2026-11-01/t.jsonl"]


def test_cli_run_and_verify_exit_codes() -> None:
    import contextlib
    import io

    from ops import restricted_replica as mod

    src = FakeBucket("p-sig-restricted", SRC)
    dst = FakeBucket("p-sig-restricted-dr")
    orig_run, orig_verify, orig_gcs = mod.run, mod.verify, mod.GcsBucket
    mod.run = lambda **kw: run_replica(
        src,
        dst,
        now="2026-11-05T15:00:00Z",
        excluded_prefixes=kw.get("excluded_prefixes", DEFAULT_EXCLUDED_PREFIXES),
    )
    mod.verify = lambda **kw: verify_replica(
        src, dst, excluded_prefixes=kw.get("excluded_prefixes", DEFAULT_EXCLUDED_PREFIXES)
    )
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = mod.main(["run", "--source-bucket", "s", "--dest-bucket", "d"])
        assert rc == 0
        with contextlib.redirect_stdout(io.StringIO()):
            assert mod.main(["verify", "--source-bucket", "s", "--dest-bucket", "d"]) == 0
        # missing env/flags → usage error
        with contextlib.redirect_stderr(io.StringIO()):
            assert mod.main(["run"]) == 2
    finally:
        mod.run, mod.verify, mod.GcsBucket = orig_run, orig_verify, orig_gcs


def test_excluded_prefixes_are_part_of_the_contract() -> None:
    assert "evidence/captures/" in DEFAULT_EXCLUDED_PREFIXES
    # a record names what it excluded — never an unexplained count
    src = FakeBucket("p-sig-restricted", SRC)
    dst = FakeBucket("p-sig-restricted-dr")
    rec = run_replica(src, dst, now="2026-11-05T15:00:00Z")
    assert set(rec["excluded"]) == {
        "evidence/captures/ocfl-root-1/inventory.json",
        "evidence/captures/ocfl-root-2/inventory.json",
    }
    # GcsBucket gained the server-side copyTo + the md5 detail list the leg uses
    assert hasattr(GcsBucket, "copy_object_to") and hasattr(GcsBucket, "list_object_details")
