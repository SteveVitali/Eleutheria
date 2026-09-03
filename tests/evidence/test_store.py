# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The EvidenceStore facade: capture set -> OCFL version -> rows (SIG-EVID-004/008)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from evidence.capture import CapturedResponse, RawCapture
from evidence.ocfl import OcflStore
from evidence.storage import LocalFileStore
from evidence.store import EvidenceStore
from evidence.tiers import StorageTier

_WHEN = datetime(2026, 5, 1, tzinfo=UTC)


def _raw() -> RawCapture:
    return RawCapture(
        url="https://portal.example/app",
        responses=(
            CapturedResponse("https://portal.example/app", 200, b"<html>x</html>", "text/html"),
        ),
        screenshot_png=b"PNG",
        raw_html=b"<html>x</html>",
        captured_at=_WHEN,
        extracted_payload=b'{"n": 1}',
    )


def _store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(OcflStore(LocalFileStore(tmp_path)))


def test_capture_set_becomes_n_rows_under_one_object(tmp_path: Path) -> None:
    stored = _store(tmp_path).store_capture_set(
        object_id="urn:sig:source:portal:x",
        source_uri="urn:sig:source:portal:x",
        raw=_raw(),
        tier=StorageTier.RESTRICTED,
    )
    # Four capture rows (WACZ + screenshot + raw HTML + payload), one OCFL version.
    assert len(stored.capture_rows) == 4
    assert {r["ocfl_version"] for r in stored.capture_rows} == {"v1"}
    assert {r["ocfl_object_id"] for r in stored.capture_rows} == {"urn:sig:source:portal:x"}
    assert {r["storage_tier"] for r in stored.capture_rows} == {"restricted"}
    # Each file is content-addressed distinctly.
    assert len({r["content_digest"] for r in stored.capture_rows}) == 4
    assert all(r["source_uri"] == "urn:sig:source:portal:x" for r in stored.capture_rows)


def test_refetch_of_unchanged_bytes_dedups_blobs(tmp_path: Path) -> None:
    """SIG-EVID-004: one stored blob, N capture rows across re-fetches."""
    store = _store(tmp_path)
    kwargs = dict(
        object_id="urn:sig:source:portal:y",
        source_uri="urn:sig:source:portal:y",
        raw=_raw(),
    )
    first = store.store_capture_set(**kwargs)
    second = store.store_capture_set(**kwargs)

    assert first.version == "v1" and second.version == "v2"
    # The second fetch created capture rows again (N rows)...
    assert len(second.capture_rows) == 4
    # ...but every blob was already stored (dedup).
    assert all(b["deduplicated"] for b in second.blob_rows)
