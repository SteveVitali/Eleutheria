# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.60 (REL-06 / G3 §7.3) — the deterministic template fingerprint.

The §7.3 Class-R row "same template fingerprint" needs a value that changes
iff the renderer's output changes. ``template_fingerprint()`` is it: a
sha256 over the **emitted byte set** of one fixed-fixture build of the same
commit — a tiny synthetic export assembled here in a tmp dir and run through
the real ``build_release``. Data stays fixed, so the digest moves only with
the templates/renderer/serialisation code (and the recorded version
strings). V14 carries candidate-vs-previous ``template_fingerprint`` in its
``deltas`` block; the classifier reads that emitted pair, never re-derives
it.

Determinism discipline: the fixture build stamps every instant field
(``as_of``, ``built_at``, label) with constants, and the digest skips the
build report (it embeds the caller's tmp path — a host detail, not a
rendered byte). Everything else the build emits is content-defined, so the
digest is reproducible across hosts and checkouts of the same commit.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .manifest import sha256_hex

#: Fixed fixture constants — the fingerprint must not drift with wall-clock
#: or host state; only renderer/template/serialisation code moves it.
FIXTURE_AS_OF = "2000-01-01T00:00:00Z"
FIXTURE_LABEL = "sig-2000-01-01.1"
FIXTURE_COMMIT = "0" * 40
FIXTURE_ENVIRONMENT = "fixture"

#: Files the build emits whose bytes embed the caller's own directory path —
#: excluded from the digest (the bytes a site serves are all relative-named).
_DIGEST_EXCLUDE = ("release/build_report.json",)


def _fixture_export(root: Path) -> Path:
    """Assemble the fixed one-record export the fingerprint builds.

    The row set is deliberately minimal — one sig_graph record exercising
    the real record/JSON+HTML emit path, one jurisdiction, one claim anchor.
    """
    comp = "sig_graph"
    (root / comp).mkdir(parents=True)
    (root / "web").mkdir(parents=True)
    (root / comp / "sites.jsonl").write_text(
        json.dumps(
            {
                "entity_type": "camera",
                "entity_id": "fp-ent-1",
                "source_id": "fp_src",
                "label": "Fingerprint Fixture Site",
                "technology": "alpr",
                "jurisdiction": "OK",
                "claim_ids": ["fp-claim-1"],
                "geometry": None,
                "_rights": {
                    "source_id": "fp_src",
                    "attribution_required": True,
                    "attribution": "Fingerprint Fixture Source",
                    "spdx": "CC-BY-4.0",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / comp / "record_claims.jsonl").write_text(
        json.dumps(
            {
                "claim_id": "fp-claim-1",
                "entity_id": "fp-ent-1",
                "source_id": "fp_src",
                "evidence_artifact_ids": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "web" / "evidence.json").write_text(
        json.dumps({"artifacts": [], "claim_views": []}), encoding="utf-8"
    )
    manifest = {
        "artifacts": [
            {
                "path": f"{comp}/sites.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "0" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            }
        ],
        "concept_id": "sig",
        "content_key": "f" * 64,
        "release_id": "sig-export-20000101T000000Z-fingerprint",
        "reproducibility_inputs": {
            "as_of_belief": "2000-01-01",
            "as_of_snapshot": "2000-01-01",
            "resolver_version": "0.0.0+fingerprint",
            "ruleset_version": "fingerprint/0",
        },
        "snapshot": {
            "as_of_world": FIXTURE_AS_OF,
            "as_of_belief": FIXTURE_AS_OF,
            "belief_pinned": False,
            "spine_watermark": "claims=0 closed=0 bump=0",
            "materialize_run": None,
            "sqitch_head": "fingerprint",
            "restore_point": None,
        },
        "environment": FIXTURE_ENVIRONMENT,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _emitted_digests(out_dir: Path) -> list[tuple[str, str]]:
    """``(relative path, sha256)`` pairs for every emitted file, sorted."""
    pairs: list[tuple[str, str]] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        if rel in _DIGEST_EXCLUDE:
            continue
        pairs.append((rel, sha256_hex(path.read_bytes())))
    return pairs


def template_fingerprint() -> str:
    """Return the sha256 digest of the fixed-fixture build's emitted bytes.

    Runs the real ``build_release`` over the fixed fixture export in a tmp
    dir; the digest is ``sha256`` over the sorted ``path`` + ``sha256``
    pairs of every emitted artifact except the path-embedding build report.
    Pure function of the checked-out code — safe to call from the build
    pipeline, the classifier's recorded evidence, and tests.
    """
    # Deferred import: release_fingerprint is imported by build_release's
    # stamping seam; importing release at module import would be circular.
    from .release import build_release

    with tempfile.TemporaryDirectory(prefix="sig-fp-") as tmp:
        tmp_root = Path(tmp)
        export_dir = _fixture_export(tmp_root / "export")
        out_dir = tmp_root / "out"
        build_release(
            export_dir,
            out_dir,
            descriptor_version=2,
            environment=FIXTURE_ENVIRONMENT,
            label=FIXTURE_LABEL,
            built_at=FIXTURE_AS_OF,
            code_commit=FIXTURE_COMMIT,
            # opt out of self-stamping — the fixture build is the fingerprint's
            # input; stamping inside it would recurse forever.
            template_fingerprint=None,
        )
        digest_input = b"".join(
            f"{rel}\0{sha}\n".encode() for rel, sha in _emitted_digests(out_dir)
        )
    return sha256_hex(digest_input)


__all__ = [
    "FIXTURE_AS_OF",
    "FIXTURE_COMMIT",
    "FIXTURE_ENVIRONMENT",
    "FIXTURE_LABEL",
    "template_fingerprint",
]
