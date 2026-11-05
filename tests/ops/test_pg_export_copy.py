# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_pg_export_copy.py — the P37.3 monthly-export cross-project
copy (SIG-STORE-048, ADR-177). Fixture-verified: pg/monthly/ prefix parity,
idempotent re-runs, the record on the destination bucket, CLI exit codes.
"""

from __future__ import annotations

import contextlib
import io
import json

from ops.pg_export_copy import RECORD_PREFIX, main, run_copy, verify_copy


class FakeBucket:
    def __init__(self, bucket: str, objects: dict[str, bytes] | None = None):
        self.bucket = bucket
        self.objects = dict(objects or {})

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

    def copy_object_to(self, name: str, *, dest: FakeBucket, dest_name: str | None = None) -> dict:
        dest.objects[dest_name or name] = self.objects[name]
        return {"name": dest_name or name}

    def put_object(
        self, name: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> str:
        self.objects[name] = body
        return name


SRC = {
    "pg/monthly/2026-10/sig-20261001T1200Z.sql": b"dump-oct",
    "pg/monthly/2026-11/sig-20261101T1200Z.sql": b"dump-nov",
    "pg/seed-2026-09-15/sig-a.sql": b"seed-dump",  # outside pg/monthly/ — never copied
}


def test_run_copies_monthly_prefix_only_and_records_on_dest() -> None:
    src = FakeBucket("p-sig-backups", SRC)
    dst = FakeBucket("q-sig-backups")
    rec = run_copy(src, dst, now="2026-11-05T15:00:00Z")
    assert rec["counts"]["copied"] == 2
    assert "pg/seed-2026-09-15/sig-a.sql" not in dst.objects
    assert rec["verified"] is True
    recs = [n for n in dst.objects if n.startswith(RECORD_PREFIX)]
    assert len(recs) == 1 and json.loads(dst.objects[recs[0]])["schema"] == "sig.pg-export-copy/1"


def test_rerun_is_idempotent_and_verify_loud_on_drift() -> None:
    src = FakeBucket("p-sig-backups", SRC)
    dst = FakeBucket("q-sig-backups")
    run_copy(src, dst, now="2026-11-05T15:00:00Z")
    rec = run_copy(src, dst, now="2026-11-05T16:00:00Z")
    assert rec["counts"]["copied"] == 0
    dst.objects["pg/monthly/2026-10/sig-20261001T1200Z.sql"] = b"tampered"
    v = verify_copy(src, dst)
    assert v["ok"] is False and v["mismatches"] == ["pg/monthly/2026-10/sig-20261001T1200Z.sql"]


def test_cli_exit_codes() -> None:
    src = FakeBucket("p-sig-backups", SRC)
    dst = FakeBucket("q-sig-backups")
    with contextlib.redirect_stderr(io.StringIO()):
        assert main(["run"]) == 2  # missing bucket args → usage
    # monkeypatched buckets (injected module attribute)
    import ops.pg_export_copy as mod

    orig = mod.GcsBucket
    mod.GcsBucket = lambda b: src if b == "s" else dst
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(["run", "--source-bucket", "s", "--dest-bucket", "d"]) == 0
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(["verify", "--source-bucket", "s", "--dest-bucket", "d"]) == 0
        dst.objects.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(["verify", "--source-bucket", "s", "--dest-bucket", "d"]) == 4
    finally:
        mod.GcsBucket = orig
