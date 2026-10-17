# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The release manifest and versioning contract for bulk exports (§38.1).

P14.2 **owns** this contract; the Phase-15 download surfaces reference it, and the
Zenodo deposit (§38.2) deposits it. Two invariants live here rather than in prose:

* **A release is a pure function of its inputs (SIG-EXPORT-003).** A bulk export is
  reproducible from ``(as_of pair + ruleset version + resolver version)`` — the four
  values of :class:`BuildSpec`. The :meth:`BuildSpec.release_id` is derived
  deterministically from exactly those inputs, so "a hand-built export is a different
  dataset wearing the same name" (§38.1) is structurally impossible: two builds from
  the same :class:`BuildSpec` produce the same release id and byte-identical artifacts.
* **Every artifact carries a checksum (SIG-EXPORT-001).** The manifest lists each
  artifact with its SHA-256, byte size, media type, and — crucially for the licence
  model — its compartment and computed licence, so a consumer can verify integrity and
  know the governing licence of every file without opening it.

The **concept id** is stable across every release of the dataset (it maps to the
Zenodo *concept DOI*, §38.2); the **release id** identifies one versioned release (the
Zenodo *version DOI*). That concept/version split is the whole point of the Zenodo
deposit: cite the dataset once, pin a run forever.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date

#: The canonical JSON encoding for every manifest/descriptor artifact SIG writes:
#: sorted keys, compact separators, a trailing newline. Byte-stable across runs and
#: platforms, so a release artifact is diffable and its digest is reproducible.
_JSON_KW: dict[str, object] = {"sort_keys": True, "separators": (",", ":"), "ensure_ascii": False}

#: The publication-basis label every export descriptor carries (E2 H-6; OM-08,
#: ADR-167/ADR-182). The exact sentence is the agent-drafted label the copy batch
#: confirms for republish #2 — never a counsel claim: no counsel exists. The same
#: string lands in ``manifest.json``, ``datapackage.json`` and ``LICENCES.json``.
PUBLICATION_BASIS = (
    "Published on the operator's own determination (no counsel). No lawyer's "
    "written opinion has been obtained; nothing here states that this "
    "publication has been cleared by counsel."
)


def canonical_json(obj: object) -> bytes:
    """Serialise ``obj`` to the canonical, byte-stable JSON encoding (UTF-8, newline)."""
    return (json.dumps(obj, **_JSON_KW) + "\n").encode("utf-8")  # type: ignore[arg-type]


def sha256_hex(data: bytes) -> str:
    """The SHA-256 hex digest of ``data`` (SIG-EXPORT-001 checksums)."""
    return hashlib.sha256(data).hexdigest()


def compact_utc_ts(instant: str) -> str:
    """``2026-06-30T15:00:00Z`` → ``20260630T150000Z`` (the export-id <ts> part).

    Any ``YYYY-MM-DDTHH:MM:SS[.f][Z|±HH:MM]`` instant is normalised to UTC
    first; a bare ``YYYY-MM-DD`` date compacts to its UTC midnight.
    """
    from datetime import UTC, datetime

    text = instant.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        text += "T00:00:00+00:00"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{instant!r} is not an ISO-8601 date or instant") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class BuildSpec:
    """The reproducibility inputs of one bulk-export release (SIG-EXPORT-003).

    Exactly the four values §38.1 names: the two-axis as-of cut (observation-time
    snapshot + assertion-time belief), the ruleset version, and the resolver version.
    Everything derived from a :class:`BuildSpec` — the release id, the artifact bytes,
    the manifest — is a deterministic function of these, so the same spec always names
    and produces the same release.
    """

    #: Observation-time cut, the T4 snapshot axis (§37.2 ``as_of_snapshot``).
    as_of_snapshot: date
    #: Assertion-time cut, the belief axis (§37.2 ``as_of_belief``).
    as_of_belief: date
    #: The reconciliation ruleset version the resolver ran under (SIG-RECON-*).
    ruleset_version: str
    #: The resolver code version (SIG-EXPORT-003 names it distinctly from the ruleset).
    resolver_version: str
    #: Stable dataset slug; the concept-level identity, constant across releases.
    dataset_slug: str = "sig"
    #: P35.12 / SIG-REL-001: the full ISO instants behind the date-grain as-of
    #: pair (``as_of`` arrives as a *time* in the spine export; the dates are
    #: its UTC date). Populated by ``--from-spine``/``export.sh``; ``None`` on
    #: a legacy date-only BuildSpec.
    as_of_snapshot_instant: str | None = None
    as_of_belief_instant: str | None = None
    #: Whether the belief axis was typed/pinned (``--belief``) or followed the
    #: snapshot instant (default False → follows).
    belief_pinned: bool = False
    #: The append-only spine watermark string (``db.occurrences.spine_watermark``)
    #: this export read at — part of the export-id key (the NEW-1 fix).
    spine_watermark: str | None = None
    #: The git sha of the code that ran the export — part of the id key.
    code_commit: str | None = None
    #: The declared environment (production/staging/fixture/replay) — two
    #: runs of the same inputs under different environments are different
    #: exports.
    environment: str | None = None
    #: The ``--replay`` reason (Class S) when this spec replays a historical
    #: snapshot; ``None`` on the live cut.
    replay: str | None = None
    #: The materialization run the export read (G3 §3.2 ``materialize_run``);
    #: ``None`` until the hosted materialization names one.
    materialize_run: str | None = None
    #: The sqitch head the export ran against (schema state of the read).
    sqitch_head: str | None = None
    #: The operator-declared snapshot restore point (replays only).
    restore_point: str | None = None

    def __post_init__(self) -> None:
        if not self.ruleset_version:
            raise ValueError("BuildSpec requires a ruleset_version (SIG-EXPORT-003)")
        if not self.resolver_version:
            raise ValueError("BuildSpec requires a resolver_version (SIG-EXPORT-003)")
        if not self.dataset_slug:
            raise ValueError("BuildSpec requires a dataset_slug")

    def reproducibility_inputs(self) -> dict[str, str]:
        """The `(as_of pair + ruleset + resolver)` tuple, as stable strings."""
        return {
            "as_of_snapshot": self.as_of_snapshot.isoformat(),
            "as_of_belief": self.as_of_belief.isoformat(),
            "ruleset_version": self.ruleset_version,
            "resolver_version": self.resolver_version,
        }

    def export_id_inputs(self) -> dict[str, object]:
        """The NEW-1 export-id key inputs (G3 §3.1).

        The §38.1 reproducibility tuple *plus* everything that makes two
        same-day exports different datasets: the full snapshot/belief
        instants, the spine watermark and the code commit — so a re-export
        that read a different watermark or ran different code can never
        collide with the earlier id.
        """
        inputs: dict[str, object] = dict(self.reproducibility_inputs())
        inputs["as_of_snapshot_instant"] = (
            self.as_of_snapshot_instant or f"{self.as_of_snapshot.isoformat()}T00:00:00Z"
        )
        inputs["as_of_belief_instant"] = (
            self.as_of_belief_instant or f"{self.as_of_belief.isoformat()}T00:00:00Z"
        )
        inputs["belief_pinned"] = self.belief_pinned
        inputs["spine_watermark"] = self.spine_watermark
        inputs["code_commit"] = self.code_commit
        inputs["environment"] = self.environment
        inputs["replay"] = self.replay
        inputs["materialize_run"] = self.materialize_run
        inputs["sqitch_head"] = self.sqitch_head
        inputs["restore_point"] = self.restore_point
        return inputs

    def snapshot_block(self) -> dict[str, object] | None:
        """The descriptor ``snapshot`` block this spec records — ``None`` on a
        legacy date-only spec (the release builder falls back to its
        reproducibility fields then)."""
        if self.as_of_snapshot_instant is None and self.spine_watermark is None:
            return None
        return {
            "as_of_world": self.as_of_snapshot_instant
            or f"{self.as_of_snapshot.isoformat()}T00:00:00Z",
            "as_of_belief": self.as_of_belief_instant
            or f"{self.as_of_belief.isoformat()}T00:00:00Z",
            "belief_pinned": self.belief_pinned,
            "spine_watermark": self.spine_watermark,
            "materialize_run": self.materialize_run,
            "sqitch_head": self.sqitch_head,
            "restore_point": self.restore_point,
        }

    def content_key(self) -> str:
        """The deterministic digest of the reproducibility inputs.

        Two :class:`BuildSpec`s produce the same key iff they would produce the same
        dataset. It is the version fingerprint that makes a hand-built export
        detectable as a different dataset (§38.1).
        """
        return sha256_hex(canonical_json(self.reproducibility_inputs()))

    def concept_id(self) -> str:
        """The dataset-level identity, stable across releases (Zenodo concept DOI)."""
        return self.dataset_slug

    def release_id(self) -> str:
        """The internal export id ``sig-export-<YYYYMMDDTHHMMSSZ>-<key8>``.

        P35.12 / NEW-1 (SIG-REL-001): the timestamp is the *snapshot instant*
        (date-grain specs render their as-of date's UTC midnight) and ``key8``
        is the leading sha256 of :meth:`export_id_inputs` — instants,
        watermark and commit included — so two same-day exports with
        different inputs can never share an id (the defect G3 names). Two
        builds of *the same* spec still name the same export — the id is a
        pure function of the inputs (SIG-EXPORT-003).
        """
        instant = self.as_of_snapshot_instant or f"{self.as_of_snapshot.isoformat()}T00:00:00Z"
        ts = compact_utc_ts(instant)
        key8 = sha256_hex(canonical_json(self.export_id_inputs()))[:8]
        return f"sig-export-{ts}-{key8}"


@dataclass(frozen=True)
class Artifact:
    """One published artifact, with the integrity + licence facts a consumer needs.

    ``compartment`` and ``license`` are load-bearing, not decoration: a bulk consumer
    must be able to tell the ODbL file from the CC-BY file without opening either
    (SIG-EXPORT-005), and the checksum lets them verify the download (SIG-EXPORT-001).
    """

    name: str
    path: str
    media_type: str
    compartment: str
    license: str
    sha256: str
    byte_size: int
    row_count: int | None = None
    #: P35.16 (R11-DATA-01, F-322): the distinct ``entity_id`` count across the
    #: artifact's rows, when the table is entity-bearing (``None`` otherwise).
    #: Export rows are OBSERVATION-level records — "N observations across M
    #: sources", never a resolved census (ADR-092 / SIG-RECON-058) — and a
    #: licence-conflicted site splits one entity across compartment files
    #: (P27.4), so ``row_count`` alone can read as an entity count. The pair
    #: ``(row_count, distinct_entities)`` is the honest disclosure: rows are
    #: physical output rows; entities are the distinct subjects observed.
    distinct_entities: int | None = None

    @classmethod
    def of(
        cls,
        *,
        name: str,
        path: str,
        media_type: str,
        compartment: str,
        license: str,
        data: bytes,
        row_count: int | None = None,
        distinct_entities: int | None = None,
    ) -> Artifact:
        """Build an artifact record from its bytes, computing size + checksum."""
        return cls(
            name=name,
            path=path,
            media_type=media_type,
            compartment=compartment,
            license=license,
            sha256=sha256_hex(data),
            byte_size=len(data),
            row_count=row_count,
            distinct_entities=distinct_entities,
        )

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "media_type": self.media_type,
            "compartment": self.compartment,
            "license": self.license,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "row_count": self.row_count,
            "distinct_entities": self.distinct_entities,
        }


@dataclass(frozen=True)
class Manifest:
    """The release manifest: the build spec plus every artifact's integrity record."""

    build_spec: BuildSpec
    artifacts: tuple[Artifact, ...] = field(default_factory=tuple)

    def _sorted(self) -> list[Artifact]:
        # Sort by path so the manifest (and its digest) is order-independent.
        return sorted(self.artifacts, key=lambda a: a.path)

    def as_json(self) -> dict[str, object]:
        doc: dict[str, object] = {
            "concept_id": self.build_spec.concept_id(),
            "release_id": self.build_spec.release_id(),
            "reproducibility_inputs": self.build_spec.reproducibility_inputs(),
            "content_key": self.build_spec.content_key(),
            # P34.21a (E2 H-6, OM-08, ADR-167/ADR-182): the publication-basis
            # label — the operator's own determination, never a counsel claim.
            "publication_basis": PUBLICATION_BASIS,
            "artifacts": [a.as_json() for a in self._sorted()],
        }
        # P35.12 / SIG-REL-001: the release builder reads the snapshot block
        # and the declared environment off the manifest for the v2
        # descriptor; absent keys mean a legacy date-only spec.
        snapshot = self.build_spec.snapshot_block()
        if snapshot is not None:
            doc["snapshot"] = snapshot
        if self.build_spec.environment is not None:
            doc["environment"] = self.build_spec.environment
        if self.build_spec.replay is not None:
            doc["replay"] = self.build_spec.replay
        return doc

    def to_bytes(self) -> bytes:
        """The canonical, byte-stable manifest document (SIG-EXPORT-001)."""
        return canonical_json(self.as_json())

    def digest_manifest(self) -> dict[str, str]:
        """The ``path -> sha256`` map deposited to Zenodo in place of evidence bytes.

        Evidence bytes are excluded from the Zenodo deposit by size (§38.2); the
        manifest of digests is deposited instead, so a citation still pins exactly
        which bytes the release comprised.
        """
        return {a.path: a.sha256 for a in self._sorted()}

    def licenses(self) -> set[str]:
        """The distinct licences present across the release's artifacts."""
        return {a.license for a in self.artifacts}


__all__ = [
    "BuildSpec",
    "Artifact",
    "Manifest",
    "canonical_json",
    "compact_utc_ts",
    "sha256_hex",
]
