# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The sig.seal-deny/1 deny set + seal records (P34.49 / ADR-185) — the
serving/export deny set is versioned (a new version per update, never an
in-place rewrite), carries ids + class ids only, and fails closed on any
malformed shape."""

from __future__ import annotations

import json

import pytest
from evidence.seal import (
    DenyEntry,
    SealDocError,
    build_deny_set,
    denied_digests,
    denied_ids,
    load_deny_set,
    seal_action,
    validate_deny_set,
)

CAPTURE = "12345678-1234-1234-1234-1234567890ab"
DIGEST = "b3:abcdef"


def _v1() -> dict:
    return build_deny_set(
        [
            DenyEntry("capture", CAPTURE, ("F406-OSM-USERUID",)),
            DenyEntry("digest", DIGEST, ("F406-OSM-USERUID",)),
        ],
        generated_at="2026-10-08T00:00:00Z",
        audit_report="gs://b/ops/probes/at-rest/t/report.json",
    )


def test_deny_set_roundtrip() -> None:
    doc = _v1()
    loaded = load_deny_set(json.dumps(doc))
    assert loaded["schema"] == "sig.seal-deny/1"
    assert loaded["version"] == 1
    assert denied_ids(loaded, "capture") == {CAPTURE}


def test_superseding_version_carries_prior_entries() -> None:
    v1 = _v1()
    v2 = build_deny_set(
        [DenyEntry("capture", CAPTURE, ("F406-OSM-USERUID", "I7-S4"))],
        generated_at="2026-10-09T00:00:00Z",  # future-ok: synthetic: fixture stamp
        prior=v1,
    )
    assert v2["version"] == 2
    assert v2["supersedes"] == v1["entries"]


def test_denied_digests_covers_both_kinds() -> None:
    doc = _v1()
    assert denied_digests(doc) == {DIGEST}


def test_validate_rejects_free_text_and_bad_shapes() -> None:
    with pytest.raises(SealDocError):
        validate_deny_set(
            {
                "schema": "sig.seal-deny/1",
                "version": 1,
                "entries": [{"kind": "capture", "id": "x", "rules": [], "note": "no free text"}],
            }
        )
    with pytest.raises(SealDocError):
        validate_deny_set({"schema": "sig.seal-deny/1", "version": 0, "entries": []})
    with pytest.raises(SealDocError):
        validate_deny_set({"schema": "other", "version": 1, "entries": []})
    with pytest.raises(SealDocError):
        validate_deny_set(
            {
                "schema": "sig.seal-deny/1",
                "version": 1,
                "entries": [{"kind": "bogus", "id": "x", "rules": []}],
            }
        )


def test_seal_action_validates() -> None:
    rec = seal_action(
        CAPTURE,
        DIGEST,
        ("F406-OSM-USERUID", "I7-S4"),
        author="op",
        audit_report="gs://b/r.json",
    )
    assert rec.action == "seal" and rec.rules == ("F406-OSM-USERUID", "I7-S4")
    with pytest.raises(SealDocError):
        seal_action("not-a-uuid", DIGEST, (), author="op", audit_report="")
    with pytest.raises(SealDocError):
        seal_action(CAPTURE, DIGEST, (), author="op", audit_report="", action="purge")


def test_no_delete_action_exists() -> None:
    """The seal vocabulary carries only seal/unseal — true purge is the
    operator's WV-11 action, never a record type this mechanism can emit."""
    from evidence.seal import SEAL_ACTIONS

    assert set(SEAL_ACTIONS) == {"seal", "unseal"}
