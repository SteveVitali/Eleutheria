# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The release manifest + versioning contract (§38.1, SIG-EXPORT-001/003)."""

from __future__ import annotations

from datetime import date

import pytest
from exports.manifest import Artifact, BuildSpec, Manifest, canonical_json, sha256_hex


def _spec(**kw: object) -> BuildSpec:
    defaults: dict[str, object] = dict(
        as_of_snapshot=date(2026, 6, 30),
        as_of_belief=date(2026, 6, 30),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    defaults.update(kw)
    return BuildSpec(**defaults)  # type: ignore[arg-type]


def test_build_spec_requires_versions() -> None:
    with pytest.raises(ValueError):
        _spec(ruleset_version="")
    with pytest.raises(ValueError):
        _spec(resolver_version="")


def test_release_id_is_a_deterministic_function_of_the_repro_inputs() -> None:
    # SIG-EXPORT-003: same (as_of pair + ruleset + resolver) => same release id.
    assert _spec().release_id() == _spec().release_id()
    assert _spec().release_id().startswith("sig-2026-06-30-")


def test_release_id_changes_when_any_repro_input_changes() -> None:
    base = _spec().release_id()
    assert _spec(ruleset_version="ruleset/2").release_id() != base
    assert _spec(resolver_version="resolver/2").release_id() != base
    assert _spec(as_of_belief=date(2026, 5, 1)).release_id() != base


def test_concept_id_is_stable_across_releases() -> None:
    # The concept id (Zenodo concept DOI) does not move when a release input changes.
    assert _spec().concept_id() == _spec(ruleset_version="ruleset/9").concept_id() == "sig"


def test_artifact_of_computes_size_and_checksum() -> None:
    data = b"hello world\n"
    art = Artifact.of(
        name="x.csv",
        path="c/x.csv",
        media_type="text/csv",
        compartment="c",
        license="CC-BY-4.0",
        data=data,
        row_count=1,
    )
    assert art.byte_size == len(data)
    assert art.sha256 == sha256_hex(data)


def test_manifest_digest_manifest_is_path_to_sha256() -> None:
    a = Artifact.of(
        name="a",
        path="z/a.csv",
        media_type="text/csv",
        compartment="z",
        license="CC-BY-4.0",
        data=b"a",
    )
    b = Artifact.of(
        name="b",
        path="a/b.csv",
        media_type="text/csv",
        compartment="a",
        license="ODbL-1.0",
        data=b"bb",
    )
    man = Manifest(build_spec=_spec(), artifacts=(a, b))
    digests = man.digest_manifest()
    assert digests == {"z/a.csv": a.sha256, "a/b.csv": b.sha256}
    # manifest bytes are order-independent (sorted by path) and byte-stable.
    assert Manifest(_spec(), (a, b)).to_bytes() == Manifest(_spec(), (b, a)).to_bytes()


def test_canonical_json_is_sorted_and_newline_terminated() -> None:
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}\n'
