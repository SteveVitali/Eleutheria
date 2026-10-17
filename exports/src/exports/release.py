# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Immutable release namespaces and specific public record routes
(P32.13 / ADR-132 — SIG-FIND-001/002).

Two-stage release identity:

1. **``publication_id``** (``p-<64 hex sha256>``) — the pre-render namespace,
   a pure function of the canonical ``sig.publication-descriptor/1`` document:
   the data-release id, both as-of cuts, ruleset/resolver versions, the
   publication-eligibility policy version, the projection schema, renderer
   identity, the INPUT export manifest's digest, and a per-compartment
   projection root hashed over the **ID-free** ``sig.published-record/1``
   documents (no publication id, no URLs inside the hashed content). Any
   parser/policy/projection/renderer/input change recomputes a different
   namespace; identical inputs reproduce it byte-for-byte.
2. **``manifest_sha256``** — a *separate* digest over the canonical
   ``sig.release-integrity/1`` manifest that lists every emitted artifact's
   (path, media type, compartment, licence, byte size, sha256). It is
   computed AFTER render and is never embedded in an artifact it covers —
   the hash graph stays acyclic (artifacts → manifest → digest → catalog
   entry → latest pointer).

The mutable serving state lives OUTSIDE the hashed bytes: ``catalog.json``,
``latest.json``, ``compat_index.json``, ``withdrawals.json`` and the
``activations/`` receipts (the only place real UTC instants are recorded).

Withdrawals reuse the ONE P32.5 rule — :func:`policy.eligibility.access_decision`
over :class:`policy.eligibility.DispositionRecord` rows evaluated at access
time — so a withhold recorded after release R2 still denies under a rollback
to R1, on the staged tree AND in the generated nginx deny map that matches
before any origin file access.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from policy.eligibility import (
    Disposition,
    DispositionRecord,
    ReasonCategory,
    TargetKind,
    access_decision,
    latest_disposition,
)

from . import release_identity as RI
from . import site_release as SR
from .manifest import canonical_json, sha256_hex
from .published_record import (
    PROJECTION_VERSION,
    claim_index_from_jsonl,
    projection_root,
    record_digest,
    record_from_site_row,
)
from .release_pages import (
    CORRECTIONS_HREF,
    EXTERNAL_LINK_PREFIXES,
    EXTERNAL_LINK_ROUTES,
    browse_page,
    compartment_page,
    dossier_page,
    dossier_slug,
    entity_stub,
    entity_stub_tombstone,
    evidence_page,
    jurisdiction_page,
    namespace_landing,
    record_page,
    release_landing,
    release_stamp_view,
    releases_index,
    tombstone_page,
)
from .search_index import (
    INDEX_DESCRIPTOR_FILE,
    INDEX_FILE,
    SEARCH_INDEX_VERSION,
    build_search_index,
)

#: Schema ids (the hand-authored ADR-132 vocabulary).
DESCRIPTOR_SCHEMA = "sig.publication-descriptor/1"
INTEGRITY_SCHEMA = "sig.release-integrity/1"
CATALOG_ENTRY_SCHEMA = "sig.publication/1"
CATALOG_SCHEMA = "sig.publication-catalog/1"
LATEST_SCHEMA = "sig.latest-pointer/1"
COMPAT_SCHEMA = "sig.compat-index/1"
WITHDRAWAL_SCHEMA = "sig.withdrawal-registry/1"
ACTIVATION_SCHEMA = "sig.activation-record/1"
TOMBSTONE_SCHEMA = "sig.tombstone/1"

PUBLICATION_RE = re.compile(r"^p-[0-9a-f]{64}$")
_PAGE_SIZE = 50

#: The repo root this source tree sits in (same derivation as versioning.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Compartments that never carry record routes (metadata/web are surfaces,
#: not record compartments) — and are therefore never searchable
#: (P34.36 / C4 NEW-29: they answer 404, never the readiness 503).
NON_RECORD_COMPARTMENTS = frozenset({"metadata", "web", "web_mixed", "code", "ontology"})


class ReleaseError(Exception):
    """A refused release operation (validation failure, namespace/byte
    collision, unknown target) — always loud, never partial."""


# --------------------------------------------------------------------------- #
# Small IO helpers                                                             #
# --------------------------------------------------------------------------- #


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _atomic_write(path: Path, data: bytes) -> None:
    """Write-then-rename — the atomic latest-pointer/catalog update."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _media_type(path: str) -> str:
    if path.endswith(".json") or path.endswith(".jsonl"):
        return "application/json"
    if path.endswith(".html"):
        return "text/html"
    if path.endswith(".pmtiles"):
        return "application/vnd.pmtiles"
    return "application/octet-stream"


# --------------------------------------------------------------------------- #
# The publication descriptor — pre-render identity                            #
# --------------------------------------------------------------------------- #


def descriptor_document(
    *,
    manifest: Mapping[str, Any],
    input_manifest_sha256: str,
    compartment_projections: Mapping[str, Mapping[str, Any]],
    evidence_root: str | None,
    dossier_root: str | None,
    renderer_revision: str,
) -> dict[str, Any]:
    """The canonical ``sig.publication-descriptor/1`` document.

    Every field is an intentional rendering input — ID-free with respect to
    the namespace it produces (no publication id, no URLs)."""
    repro = dict(manifest.get("reproducibility_inputs") or {})
    from . import __version__

    return {
        "schema": DESCRIPTOR_SCHEMA,
        "data_release_id": str(manifest.get("release_id") or ""),
        "content_key": str(manifest.get("content_key") or ""),
        "as_of_world": str(repro.get("as_of_snapshot") or ""),
        "as_of_belief": str(repro.get("as_of_belief") or ""),
        "ruleset_version": str(repro.get("ruleset_version") or ""),
        "resolver_version": str(repro.get("resolver_version") or ""),
        "policy_version": "publication-eligibility/1",
        "projection_version": PROJECTION_VERSION,
        "search_index_version": SEARCH_INDEX_VERSION,
        "renderer": {
            "package": "sig-exports",
            "version": __version__,
            "revision": renderer_revision,
        },
        "input_manifest_sha256": input_manifest_sha256,
        "compartment_projections": {
            comp: dict(proj) for comp, proj in sorted(compartment_projections.items())
        },
        "evidence_root": evidence_root,
        "dossier_root": dossier_root,
    }


def descriptor_sha256(descriptor: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(descriptor))


def publication_id(descriptor: Mapping[str, Any]) -> str:
    return f"p-{descriptor_sha256(descriptor)}"


# --------------------------------------------------------------------------- #
# Release build                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class CompartmentBuild:
    compartment: str
    license: str
    record_digests: list[str] = field(default_factory=list)
    index_rows: list[dict[str, Any]] = field(default_factory=list)
    kinds: dict[str, int] = field(default_factory=dict)
    jurisdictions: dict[str, int] = field(default_factory=dict)
    search_index_sha256: str = ""
    search_indexed_records: int = 0
    site_rows_read: int = 0
    duplicate_rows_dropped: int = 0


@dataclass
class ReleaseBuild:
    publication_id: str
    descriptor: dict[str, Any]
    manifest_sha256: str
    out_dir: Path
    report: dict[str, Any]


def _export_compartments(export_dir: Path) -> dict[str, str]:
    """``{compartment: licence}`` for every dir carrying a ``sites.jsonl`` —
    the licence label comes from the export manifest's own artifact entry
    (never recomputed, never co-mingled)."""
    manifest = _read_json(export_dir / "manifest.json")
    licence_by_comp: dict[str, str] = {}
    for art in manifest.get("artifacts") or []:
        path = str(art.get("path") or "")
        if path.endswith("/sites.jsonl"):
            comp = path.split("/")[0]
            licence_by_comp[comp] = str(art.get("license") or "")
    return licence_by_comp


def _source_to_compartment(export_dir: Path, comps: Mapping[str, str]) -> dict[str, str]:
    """Map each published source to the compartment its sites were placed in
    (used to compartment-scope evidence pages for the same licence slice)."""
    out: dict[str, str] = {}
    for comp in comps:
        path = export_dir / comp / "sites.jsonl"
        if not path.exists():
            continue
        for row in _iter_jsonl(path):
            sid = str((row.get("_rights") or {}).get("source_id") or row.get("source_id"))
            out.setdefault(sid, comp)
    return out


def _iter_unique_site_rows(path: Path, dropped: dict[str, int]) -> Iterator[dict[str, Any]]:
    """Yield exactly one site row per (entity_type, entity_id).

    A record namespace can host one record per key; upstream exports can
    carry the SAME record twice (the ``portal`` compartment re-extracts
    thousands of deployments through a second rights registration — the
    rows differ only in ``_rights``/``rights_id``). The first occurrence
    wins the payload, ``claim_ids`` are unioned across duplicates (sorted,
    so identical input always merges identically), and every drop is
    counted honestly in ``dropped`` for the reconciliation report.
    """
    counts: dict[tuple[str, str], int] = {}
    n_read = 0
    for row in _iter_jsonl(path):
        n_read += 1
        key = (str(row.get("entity_type") or ""), str(row.get("entity_id") or ""))
        counts[key] = counts.get(key, 0) + 1
    dropped["rows_read"] = n_read
    dup_keys = {k for k, n in counts.items() if n > 1}
    if not dup_keys:
        yield from _iter_jsonl(path)
        return
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {k: [] for k in dup_keys}
    for row in _iter_jsonl(path):
        key = (str(row.get("entity_type") or ""), str(row.get("entity_id") or ""))
        if key in dup_keys:
            groups[key].append(row)
        else:
            yield row
    for key in sorted(groups):
        rows = groups[key]
        dropped["duplicate_record_key"] = dropped.get("duplicate_record_key", 0) + len(rows) - 1
        merged = dict(rows[0])
        claims: set[str] = set()
        for r in rows:
            claims.update(str(c) for c in (r.get("claim_ids") or []))
        merged["claim_ids"] = sorted(claims)
        yield merged


def _claim_index(export_dir: Path) -> dict[str, dict[str, Any]]:
    """The merged ``record_claims`` index across compartments (each claim row
    lives under its OWN licence compartment; lookup is release-wide — a claim
    may sit in a compartment that has no sites of its own)."""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(export_dir.glob("*/record_claims.jsonl")):
        out.update(claim_index_from_jsonl(_iter_jsonl(path)))
    return out


def _content_root(payload: Any) -> str:
    """sha256 over a canonical JSON payload (an ID-free content root)."""
    return sha256_hex(canonical_json(payload))


# --------------------------------------------------------------------------- #
# Descriptor v2 helpers (P35.12 / SIG-REL-001)                                 #
# --------------------------------------------------------------------------- #


def _transparency_root(export_dir: Path, manifest: Mapping[str, Any]) -> str | None:
    """The J3 TX-13b transparency-surfaces root: a content root over the
    ``{path: sha256}`` map of the export's disclosure/exclusion artifacts
    (``exclusions.json``, ``web/terms_disclosure.json``, any emitted
    ``*transparency*``/``*methodology*``/``*provenance*`` artifact). ``None``
    — declared-empty — when the export carried none."""
    roots: dict[str, str] = {}
    for art in manifest.get("artifacts") or []:
        path = str(art.get("path") or "")
        name = path.rsplit("/", 1)[-1]
        if (
            path == "exclusions.json"
            or path == "web/terms_disclosure.json"
            or any(
                marker in name
                for marker in ("transparency", "methodology", "provenance", "disclosure")
            )
        ):
            roots[path] = str(art.get("sha256") or "")
    return _content_root(roots) if roots else None


def _rights_registry_sha256(path: Path | None) -> str | None:
    """sha256 of the committed rights registry (``connectors` sources.toml``)
    the export's rights decisions read — ``None`` when the file is absent."""
    if path is None or not path.exists():
        return None
    return sha256_hex(path.read_bytes())


def _disposition_root(dispositions: Sequence[Mapping[str, Any]] | None) -> str:
    """sha256 over the ADR-124 dispositions effective at the snapshot.

    The committed ``sig.publication-withdrawals/1`` entries the export itself
    applied are the fixture-machinery source (``policy.withdrawals``); a cut
    (row 297+) supplies the spine-disposition set explicitly."""
    if dispositions is None:
        from policy.withdrawals import withdrawal_entries

        entries: Sequence[Mapping[str, Any]] = withdrawal_entries()
    else:
        entries = dispositions
    return _content_root(list(entries))


def _ontology_facts() -> tuple[str | None, str | None]:
    """``(ontology_version, ontology_generated_sha256)`` — the LinkML source
    version plus a digest over the committed generated tree. The digest is a
    ``{path: sha256}`` map root, never a hand-edited file."""
    ont_version: str | None
    try:
        from ontology import __version__ as _v

        ont_version = _v
    except Exception:  # noqa: BLE001 - version unresolvable is honest None
        ont_version = None
    gen_root = _REPO_ROOT / "ontology" / "generated"
    digest: str | None = None
    if gen_root.exists():
        digests = {
            str(p.relative_to(gen_root)): sha256_hex(p.read_bytes())
            for p in sorted(gen_root.rglob("*"))
            if p.is_file()
        }
        digest = _content_root(digests) if digests else None
    return ont_version, digest


def _load_disclosures(
    path: Path | None, entries: Sequence[Mapping[str, Any]] | None
) -> list[dict[str, Any]]:
    """The descriptor ``disclosures`` list — ``[{id, text_sha256}, …]``.

    Reads the committed ``ops/disclosures.toml`` (row 297's input file is
    declared-empty until it lands) or a caller-supplied list; each entry's
    ``text`` is digested so the descriptor carries only the hash.
    """
    raw: list[Mapping[str, Any]] = []
    if entries is not None:
        raw = list(entries)
    elif path is not None and path.exists():
        import tomllib

        doc = tomllib.loads(path.read_text(encoding="utf-8"))
        raw = list(doc.get("disclosures") or [])
    out: list[dict[str, Any]] = []
    for entry in raw:
        text_sha = entry.get("text_sha256")
        if not text_sha and entry.get("text") is not None:
            text_sha = sha256_hex(str(entry["text"]).encode("utf-8"))
        out.append({"id": str(entry.get("id") or ""), "text_sha256": text_sha})
    return out


def _attribution_gate_pass_count(export_dir: Path, comps: Mapping[str, str]) -> int:
    """How many attribution-required rows passed the E2-12 gate into this
    export (each exported row with ``_rights.attribution_required`` is a
    counted pass — the gate already refused any violator at build)."""
    n = 0
    for comp in comps:
        path = export_dir / comp / "sites.jsonl"
        if not path.exists():
            continue
        for row in _iter_jsonl(path):
            rights = row.get("_rights")
            if isinstance(rights, Mapping) and rights.get("attribution_required"):
                n += 1
    return n


def _v2_descriptor(
    export_dir: Path,
    manifest: Mapping[str, Any],
    *,
    input_manifest_sha256: str,
    compartment_projections: Mapping[str, Mapping[str, Any]],
    evidence_root: str | None,
    dossier_root: str | None,
    comps: Mapping[str, str],
    environment: str | None,
    label: str | None,
    labels_registry: Path | str | None,
    built_at: datetime | str | None,
    code_commit: str | None,
    code_tree: str | None,
    images_export: str | None,
    boundaries_root: str | None,
    disclosures: Sequence[Mapping[str, Any]] | None,
    disclosures_path: Path | None,
    evaluation: Mapping[str, Any] | None,
    dispositions: Sequence[Mapping[str, Any]] | None,
    graph_quality: Mapping[str, Any] | None,
    rights_registry_path: Path | None,
    ontology_generated_sha256: str | None | object = ...,
    repo_root: Path | None,
) -> dict[str, Any]:
    """Assemble + validate the ``sig.publication-descriptor/2`` document.

    The label's date derives from ``snapshot.as_of_world`` — never typed
    (§3.3 rule 6); the commit is read from the tree, never typed (GT-7);
    every required field is populated or explicitly declared-empty before
    :func:`release_identity.validate_descriptor` signs off.
    """
    from . import __version__
    from . import versioning as V

    t0 = RI.parse_instant(built_at) or datetime.now(UTC)
    built_at_s = t0.strftime("%Y-%m-%dT%H:%M:%SZ")

    repro = dict(manifest.get("reproducibility_inputs") or {})
    snap = dict(manifest.get("snapshot") or {})
    # A legacy export manifest carries date-grain reproducibility inputs and
    # no snapshot block — the v2 descriptor still records real instants
    # (UTC midnights of the declared dates), honestly derived.
    as_of_world = snap.get("as_of_world") or f"{repro.get('as_of_snapshot', '')}T00:00:00Z"
    as_of_belief = snap.get("as_of_belief") or f"{repro.get('as_of_belief', '')}T00:00:00Z"
    env = environment or manifest.get("environment") or "fixture"
    if env not in RI.ENVIRONMENTS:
        raise ReleaseError(
            f"environment {env!r} is not one of {sorted(RI.ENVIRONMENTS)} — "
            "a release declares its environment explicitly (SIG-REL-001)"
        )
    replay_reason = manifest.get("replay")
    if env == "replay" and not replay_reason:
        raise ReleaseError("environment=replay requires a recorded --replay reason (Class S)")

    # The human label: typed (validated against derivation), registry-
    # allocated under the lock, or refused — never silently minted.
    world_dt = RI.parse_instant(as_of_world)
    if world_dt is None:
        raise ReleaseError(f"snapshot.as_of_world {as_of_world!r} is not an ISO instant")
    if label is not None:
        if not RI.LABEL_RE.match(label):
            raise ReleaseError(f"--label {label!r} is not sig-YYYY-MM-DD.N")
        ordinal = int(RI.LABEL_RE.match(label)[4])  # type: ignore[index]
        if label != RI.label_for(world_dt, ordinal):
            raise ReleaseError(
                f"--label {label!r} does not derive from snapshot.as_of_world "
                f"{as_of_world!r} — the label date is the data date, never typed"
            )
    elif labels_registry is not None:
        label = RI.allocate_label(
            Path(labels_registry),
            world_dt,
            allocated_at=t0,
            environment=env,
        )
    else:
        raise ReleaseError(
            "a v2 release needs a label: pass --labels-registry (locked "
            "allocation) or --label sig-YYYY-MM-DD.N (validated against the "
            "snapshot date) — a release label is never silently minted"
        )

    commit = code_commit or V.code_commit(repo_root)
    if not commit:
        raise ReleaseError(
            "code.commit could not be read from the tree (git rev-parse HEAD) "
            "— a release never invents a commit (GT-7)"
        )
    tree = code_tree or V.code_tree(repo_root)

    ont_version, ont_generated = _ontology_facts()
    if ontology_generated_sha256 is not ...:
        ont_generated = (
            ontology_generated_sha256 if isinstance(ontology_generated_sha256, str) else None
        )

    descriptor = RI.descriptor_v2_document(
        label=label,
        environment=env,
        snapshot={
            "as_of_world": as_of_world,
            "as_of_belief": as_of_belief,
            "belief_pinned": snap.get("belief_pinned", False),
            "spine_watermark": snap.get("spine_watermark"),
            "materialize_run": snap.get("materialize_run"),
            "sqitch_head": snap.get("sqitch_head"),
            "restore_point": snap.get("restore_point"),
        },
        export={
            "id": str(manifest.get("release_id") or ""),
            "input_manifest_sha256": input_manifest_sha256,
            "content_key": str(manifest.get("content_key") or ""),
        },
        code={
            "commit": commit,
            "tree": tree,
            "images_export": images_export,
            "renderer": {"version": __version__},
        },
        versions={
            "ruleset_version": str(repro.get("ruleset_version") or ""),
            "resolver_version": str(repro.get("resolver_version") or ""),
            "policy_version": "publication-eligibility/1",
            "projection_version": PROJECTION_VERSION,
            "search_index_version": SEARCH_INDEX_VERSION,
            "ontology_version": ont_version,
            "ontology_generated_sha256": ont_generated,
        },
        gates={
            "disposition_root": _disposition_root(dispositions),
            "rights_registry_sha256": _rights_registry_sha256(
                rights_registry_path or (_REPO_ROOT / "connectors/src/connectors/data/sources.toml")
            ),
            "attribution_gate": {
                "version": "sig.attribution-gate/1",
                "pass_count": _attribution_gate_pass_count(export_dir, comps),
            },
            "graph_quality": graph_quality,
        },
        evaluation=dict(evaluation or {}),
        disclosures=_load_disclosures(
            disclosures_path or (_REPO_ROOT / "ops" / "disclosures.toml"),
            disclosures,
        ),
        compartment_projections=compartment_projections,
        evidence_root=evidence_root,
        dossier_root=dossier_root,
        transparency_root=_transparency_root(export_dir, manifest),
        boundaries_root=boundaries_root,
        built_at=built_at_s,
        replay_reason=str(replay_reason) if replay_reason else None,
    )
    failures = RI.validate_descriptor(descriptor, now=t0)
    if failures:
        raise ReleaseError(
            "the assembled sig.publication-descriptor/2 fails validation — "
            "refusing to emit an invalid descriptor:\n  " + "\n  ".join(failures)
        )
    return descriptor


def build_release(
    export_dir: Path | str,
    out_dir: Path | str,
    *,
    renderer_revision: str | None = None,
    descriptor_version: int = 1,
    page_size: int = _PAGE_SIZE,
    environment: str | None = None,
    label: str | None = None,
    labels_registry: Path | str | None = None,
    built_at: datetime | str | None = None,
    code_commit: str | None = None,
    code_tree: str | None = None,
    images_export: str | None = None,
    boundaries_root: str | None = None,
    disclosures: Sequence[Mapping[str, Any]] | None = None,
    disclosures_path: Path | None = None,
    evaluation: Mapping[str, Any] | None = None,
    dispositions: Sequence[Mapping[str, Any]] | None = None,
    graph_quality: Mapping[str, Any] | None = None,
    rights_registry_path: Path | None = None,
    ontology_generated_sha256: str | None | object = ...,
    repo_root: Path | None = None,
) -> ReleaseBuild:
    """Build the immutable release bundle from an export directory.

    Two passes per compartment: the first computes the ID-free record digests
    (→ projection roots → descriptor → ``publication_id``); the second emits
    the bound artifacts. Streaming — records are never all held in memory.
    """
    export_dir = Path(export_dir)
    out_dir = Path(out_dir)
    manifest = _read_json(export_dir / "manifest.json")
    manifest_bytes = (export_dir / "manifest.json").read_bytes()

    comps = _export_compartments(export_dir)
    # Non-record compartments are page surfaces — a sites.jsonl under one is
    # a malformed export, and minting a searchable record namespace for it is
    # the defect P34.36 (C4 NEW-29) bars. Fail closed, loudly.
    non_record = sorted(set(comps) & NON_RECORD_COMPARTMENTS)
    if non_record:
        raise ReleaseError(
            "non-record compartment(s) carry sites.jsonl — they can never "
            f"hold record routes or a search index: {', '.join(non_record)}"
        )
    claim_index = _claim_index(export_dir)
    source_to_comp = _source_to_compartment(export_dir, comps)

    evidence_payload = (
        _read_json(export_dir / "web" / "evidence.json")
        if (export_dir / "web" / "evidence.json").exists()
        else {"artifacts": [], "claim_views": []}
    )
    dossiers = (
        _read_json(export_dir / "web" / "dossiers.json")
        if (export_dir / "web" / "dossiers.json").exists()
        else []
    )

    # --- pass 1: projection roots per compartment --------------------------- #
    builds: dict[str, CompartmentBuild] = {}
    for comp in sorted(comps):
        cb = CompartmentBuild(compartment=comp, license=comps[comp])
        dropped: dict[str, int] = {}
        for row in _iter_unique_site_rows(export_dir / comp / "sites.jsonl", dropped):
            record = record_from_site_row(
                row, compartment=comp, license_id=comps[comp], claim_index=claim_index
            )
            cb.record_digests.append(record_digest(record))
        cb.site_rows_read = int(dropped.get("rows_read") or 0)
        cb.duplicate_rows_dropped = int(dropped.get("duplicate_record_key") or 0)
        builds[comp] = cb

    compartment_projections = {
        comp: {"sha256": projection_root(cb.record_digests), "records": len(cb.record_digests)}
        for comp, cb in sorted(builds.items())
    }
    evidence_root = (
        _content_root(
            sorted(
                (dict(a) for a in evidence_payload.get("artifacts") or []),
                key=lambda a: str(a.get("artifact_id")),
            )
        )
        if evidence_payload.get("artifacts")
        else None
    )
    dossier_root = _content_root(dossiers) if dossiers else None

    if descriptor_version == 2:
        if renderer_revision is not None:
            raise ReleaseError(
                "a v2 descriptor carries one code identity — renderer.revision "
                "is code.commit; do not pass renderer_revision (NEW-3)"
            )
        descriptor = _v2_descriptor(
            export_dir,
            manifest,
            input_manifest_sha256=sha256_hex(manifest_bytes),
            compartment_projections=compartment_projections,
            evidence_root=evidence_root,
            dossier_root=dossier_root,
            comps=comps,
            environment=environment,
            label=label,
            labels_registry=labels_registry,
            built_at=built_at,
            code_commit=code_commit,
            code_tree=code_tree,
            images_export=images_export,
            boundaries_root=boundaries_root,
            disclosures=disclosures,
            disclosures_path=disclosures_path,
            evaluation=evaluation,
            dispositions=dispositions,
            graph_quality=graph_quality,
            rights_registry_path=rights_registry_path,
            ontology_generated_sha256=ontology_generated_sha256,
            repo_root=repo_root,
        )
    else:
        if renderer_revision is None:
            raise ReleaseError("a v1 descriptor requires renderer_revision")
        descriptor = descriptor_document(
            manifest=manifest,
            input_manifest_sha256=sha256_hex(manifest_bytes),
            compartment_projections=compartment_projections,
            evidence_root=evidence_root,
            dossier_root=dossier_root,
            renderer_revision=renderer_revision,
        )
    pub = publication_id(descriptor)
    if not PUBLICATION_RE.match(pub):
        raise ReleaseError(f"internal: malformed publication id {pub!r}")
    if labels_registry is not None and descriptor.get("schema") == RI.DESCRIPTOR_SCHEMA_V2:
        RI.record_label_publication(labels_registry, str(descriptor["label"]), pub)

    # P35.13 / SIG-REL-009 (G3 §6.1): the §6.1 provenance stamp — one view the
    # whole bound tree's pages share. Its fields are the v2 descriptor's own
    # (label, as-of pair, build instant, code commit) projected through
    # release_stamp_view — the stamp never recomputes a value. v1 releases
    # carry no label → no stamp (the honest unstamped state).
    release_stamp: dict[str, str] | None = None
    release_label: str | None = None
    release_as_of_world: str | None = None
    if descriptor.get("schema") == RI.DESCRIPTOR_SCHEMA_V2:
        release_label = str(descriptor.get("label") or "") or None
        release_as_of_world = RI.descriptor_as_of_world(descriptor)
        _code = descriptor.get("code") or {}
        _commit = str(_code.get("commit") or "")
        release_stamp = release_stamp_view(
            {
                "label": release_label,
                "publication_id": pub,
                "as_of_world": release_as_of_world,
                "built_at": (descriptor.get("build") or {}).get("built_at"),
                "code": {
                    "commit": _commit,
                    "url": f"{RI.CODE_REPOSITORY}/commit/{_commit}" if _commit else "",
                },
            },
            describedby=f"/releases/{pub}/release.json",
            variant="fixed",
        )

    # --- pass 2: emit the bound tree ---------------------------------------- #
    artifacts: list[dict[str, Any]] = []

    def emit(rel: str, data: bytes, *, compartment: str | None, licence: str) -> Path:
        target = out_dir / rel
        _write(target, data)
        digest, size = _sha256_file(target)
        artifacts.append(
            {
                "path": rel,
                "media_type": _media_type(rel),
                "compartment": compartment,
                "license": licence,
                "sha256": digest,
                "byte_size": size,
            }
        )
        return target

    # P34.34a fix-forward: an evidence anchor page lives under the artifact's
    # OWN compartment (source_to_comp, the emit loop below), not the citing
    # record's — a record in osm_physical can cite a web/sig_graph artifact.
    # The map lets record_page link the true route (or state the absence) so
    # the same-origin crawl sees no dead link.
    evidence_compartment = {
        str(a.get("artifact_id")): source_to_comp.get(str(a.get("source")), "web")
        for a in evidence_payload.get("artifacts") or []
    }

    comp_meta: list[dict[str, Any]] = []
    total_records = 0
    for comp in sorted(builds):
        cb = builds[comp]
        comp_dir = f"r/{pub}/c/{comp}"
        index_lines: list[dict[str, Any]] = []
        search_rows: list[dict[str, Any]] = []
        for row in _iter_unique_site_rows(export_dir / comp / "sites.jsonl", {}):
            record = record_from_site_row(
                row, compartment=comp, license_id=comps[comp], claim_index=claim_index
            ).bind(
                pub,
                release_label=release_label,
                as_of_world=release_as_of_world,
            )
            et, eid = record.entity_type, record.entity_id
            json_rel = f"{comp_dir}/entity/{et}/{eid}.json"
            emit(json_rel, record.json_bytes(), compartment=comp, licence=comps[comp])
            emit(
                f"{comp_dir}/entity/{et}/{eid}/index.html",
                record_page(
                    record,
                    latest_stub=f"/entity/{et}/{eid}/",
                    evidence_compartment=evidence_compartment,
                    stamp=release_stamp,
                ),
                compartment=comp,
                licence=comps[comp],
            )
            index_lines.append(
                {
                    "record_key": record.record_key,
                    "entity_id": eid,
                    "entity_type": et,
                    "path": f"{comp_dir}/entity/{et}/{eid}/index.html",
                    "json_path": json_rel,
                    "claim_ids": [a.claim_id for a in record.claim_anchors],
                    "jurisdiction": record.jurisdiction.get("id"),
                    "label": record.label.get("text"),
                }
            )
            cb.index_rows.append(index_lines[-1])
            cb.kinds[et] = cb.kinds.get(et, 0) + 1
            jur = str(record.jurisdiction.get("id") or "unreported")
            cb.jurisdictions[jur] = cb.jurisdictions.get(jur, 0) + 1
            total_records += 1
            # P32.14 (SIG-FIND-003): one normalized index row per eligible
            # record — unlocated + unreported-jurisdiction records are indexed
            # by construction (every row of the bound projection).
            search_rows.append(
                {
                    "record_key": record.record_key,
                    "entity_id": eid,
                    "entity_type": et,
                    "label": record.label.get("text"),
                    "jurisdiction": record.jurisdiction.get("id"),
                    "location_kind": ("public-point" if row.get("geometry") else "no-public-point"),
                    "source_id": str(row.get("source_id") or ""),
                    "technology": str(row.get("technology") or ""),
                    "claim_ids": [a.claim_id for a in record.claim_anchors],
                }
            )

        index_bytes = b"".join(
            canonical_json(row) for row in sorted(index_lines, key=lambda r: r["record_key"])
        )
        emit(
            f"{comp_dir}/records.index.jsonl",
            index_bytes,
            compartment=comp,
            licence=comps[comp],
        )
        # P32.14 (SIG-FIND-003, ADR-133): the deterministic per-compartment
        # FTS5 search index — a licensed artifact of the same bound
        # projection, verified by hash before any ro open at serve time.
        fd, tmp_name = tempfile.mkstemp(suffix=".sqlite", prefix="sig-idx-")
        os.close(fd)
        try:
            idx_descriptor = build_search_index(
                search_rows,
                publication_id=pub,
                compartment=comp,
                license_id=comps[comp],
                out=Path(tmp_name),
            )
            idx_bytes = Path(tmp_name).read_bytes()
        finally:
            Path(tmp_name).unlink(missing_ok=True)
        emit(
            f"{comp_dir}/{INDEX_FILE}",
            idx_bytes,
            compartment=comp,
            licence=comps[comp],
        )
        emit(
            f"{comp_dir}/{INDEX_DESCRIPTOR_FILE}",
            canonical_json(idx_descriptor),
            compartment=comp,
            licence=comps[comp],
        )
        cb.search_index_sha256 = sha256_hex(idx_bytes)
        cb.search_indexed_records = int(idx_descriptor["scope"]["indexed_records"])
        emit(
            f"{comp_dir}/index.html",
            compartment_page(
                publication_id=pub,
                compartment=comp,
                licence=comps[comp],
                record_count=len(cb.index_rows),
                kinds=cb.kinds,
                jurisdictions=cb.jurisdictions,
                stamp=release_stamp,
            ),
            compartment=comp,
            licence=comps[comp],
        )
        # browse indexes per kind
        by_kind: dict[str, list[dict[str, Any]]] = {}
        for r in sorted(index_lines, key=lambda r: r["record_key"]):
            by_kind.setdefault(r["entity_type"], []).append(
                {
                    "entity_id": r["entity_id"],
                    "entity_type": r["entity_type"],
                    "jurisdiction": r["jurisdiction"],
                    "label": r["label"],
                }
            )
        for kind, items in sorted(by_kind.items()):
            page_count = max(1, (len(items) + page_size - 1) // page_size)
            for page in range(1, page_count + 1):
                chunk = items[(page - 1) * page_size : page * page_size]
                emit(
                    f"{comp_dir}/browse/{kind}/{page}/index.html",
                    browse_page(
                        publication_id=pub,
                        compartment=comp,
                        kind=kind,
                        page=page,
                        page_count=page_count,
                        items=chunk,
                        total=len(items),
                        licence=comps[comp],
                        stamp=release_stamp,
                    ),
                    compartment=comp,
                    licence=comps[comp],
                )
        # jurisdiction indexes
        by_jur: dict[str, list[dict[str, Any]]] = {}
        for r in index_lines:
            by_jur.setdefault(str(r["jurisdiction"] or "unreported"), []).append(
                {
                    "entity_id": r["entity_id"],
                    "entity_type": r["entity_type"],
                    "jurisdiction": r["jurisdiction"],
                    "label": r["label"],
                }
            )
        for jur, items in sorted(by_jur.items()):
            page_count = max(1, (len(items) + page_size - 1) // page_size)
            for page in range(1, page_count + 1):
                chunk = items[(page - 1) * page_size : page * page_size]
                emit(
                    f"{comp_dir}/jurisdiction/{jur}/{page}/index.html",
                    jurisdiction_page(
                        publication_id=pub,
                        compartment=comp,
                        jurisdiction=jur,
                        page=page,
                        page_count=page_count,
                        items=chunk,
                        total=len(items),
                        licence=comps[comp],
                        stamp=release_stamp,
                    ),
                    compartment=comp,
                    licence=comps[comp],
                )
        comp_meta.append(
            {
                "compartment": comp,
                "license": comps[comp],
                "record_count": len(cb.index_rows),
                "site_rows": cb.site_rows_read,
                "duplicate_rows_dropped": cb.duplicate_rows_dropped,
                "artifact_count": 0,  # filled below
                "index_sha256": sha256_hex(index_bytes),
                "search_index_sha256": cb.search_index_sha256,
                "search_indexed_records": cb.search_indexed_records,
            }
        )

    # --- evidence anchor pages ---------------------------------------------- #
    evidence_count = 0
    for art in sorted(
        (dict(a) for a in evidence_payload.get("artifacts") or []),
        key=lambda a: str(a.get("artifact_id")),
    ):
        aid = str(art.get("artifact_id"))
        comp = source_to_comp.get(str(art.get("source")), "web")
        emit(
            f"r/{pub}/c/{comp}/evidence/{aid}/index.html",
            evidence_page(
                publication_id=pub,
                compartment=comp,
                artifact=art,
                licence=comps.get(comp, "CC-BY-4.0"),
                stamp=release_stamp,
            ),
            compartment=comp,
            licence=comps.get(comp, "CC-BY-4.0"),
        )
        evidence_count += 1

    # --- released dossier overviews ------------------------------------------ #
    dossier_count = 0
    for dossier in dossiers:
        slug = dossier_slug(dossier)
        emit(
            f"r/{pub}/dossier/{slug}/index.html",
            dossier_page(
                publication_id=pub,
                dossier=dossier,
                licence="CC-BY-4.0",
                stamp=release_stamp,
            ),
            compartment="web",
            licence="CC-BY-4.0",
        )
        dossier_count += 1

    # --- release landing + descriptor (both covered by the manifest) --------- #
    # Completeness over an empty corpus is not evaluable (P34.36 / F5
    # PKG-03b): a verified zero-record release says so, never a bare
    # "complete" on an empty denominator.
    completeness = (
        {
            "state": "not_evaluable",
            "failures": [],
            "detail": "no published records — completeness is not evaluable",
        }
        if total_records == 0
        else {"state": "complete", "failures": []}
    )
    descriptor_rel = f"releases/{pub}/descriptor.json"
    emit(
        descriptor_rel,
        canonical_json(descriptor),
        compartment="metadata",
        licence="CC-BY-4.0",
    )

    # per-compartment artifact counts (computed after all emits)
    per_comp_count: dict[str, int] = {}
    for a in artifacts:
        c = a.get("compartment")
        if c:
            per_comp_count[c] = per_comp_count.get(c, 0) + 1
    for meta in comp_meta:
        meta["artifact_count"] = per_comp_count.get(meta["compartment"], 0)

    # v1/v2 share the catalog entry shape; the accessors read whichever
    # descriptor form the build emitted (v2's label is the data_release_id).
    _repro_block = RI.descriptor_versions_block(descriptor)
    _as_of_world = RI.descriptor_as_of_world(descriptor)
    _as_of_belief = RI.descriptor_as_of_belief(descriptor)
    catalog_entry = {
        "schema": CATALOG_ENTRY_SCHEMA,
        "publication_id": pub,
        "descriptor_sha256": descriptor_sha256(descriptor),
        "data_release_id": RI.descriptor_release_id(descriptor),
        "reproducibility": _repro_block,
        "compartments": comp_meta,
        "record_count": total_records,
        "artifact_count": 0,  # filled after manifest assembly
        "completeness": completeness,
        "compat": {
            # the resolver selector matches date-grain instants (G3 labels are
            # day-grain), so compat carries the as-of pair's UTC dates
            "as_of_world": _as_of_world[:10],
            "as_of_belief": _as_of_belief[:10],
            "ruleset_version": _repro_block.get("ruleset_version"),
        },
    }
    landing_rel = f"releases/{pub}/index.html"
    emit(
        landing_rel,
        release_landing(catalog_entry, dossiers=dossiers, stamp=release_stamp),
        compartment="metadata",
        licence="CC-BY-4.0",
    )
    # The namespace root landing (P34.41 / C4 NEW-29): ``/r/<pub>/`` resolves
    # to a real page — never a 403 from a directory with no index. Immutable
    # like every other ``r/`` byte; covered by the manifest below.
    emit(
        f"r/{pub}/index.html",
        namespace_landing(catalog_entry, stamp=release_stamp),
        compartment="metadata",
        licence="CC-BY-4.0",
    )

    # --- the integrity manifest (external digest over every emitted artifact) - #
    artifacts.sort(key=lambda a: a["path"])
    integrity = {
        "schema": INTEGRITY_SCHEMA,
        "publication_id": pub,
        "descriptor_sha256": descriptor_sha256(descriptor),
        "artifacts": artifacts,
        "compartments": [
            {
                "compartment": m["compartment"],
                "license": m["license"],
                "record_count": m["record_count"],
                "site_rows": m["site_rows"],
                "duplicate_rows_dropped": m["duplicate_rows_dropped"],
                "index_sha256": m["index_sha256"],
                "search_index_sha256": m["search_index_sha256"],
                "search_indexed_records": m["search_indexed_records"],
            }
            for m in comp_meta
        ],
        "counts": {
            "input_records": sum(int(m["site_rows"]) for m in comp_meta),
            "output_records": total_records,
            "evidence_pages": evidence_count,
            "dossier_pages": dossier_count,
        },
        "completeness": completeness,
    }
    integrity_bytes = canonical_json(integrity)
    manifest_sha = sha256_hex(integrity_bytes)
    _write(out_dir / f"releases/{pub}/integrity_manifest.json", integrity_bytes)

    catalog_entry["manifest_sha256"] = manifest_sha
    catalog_entry["artifact_count"] = len(artifacts)
    # The catalog entry carries the final digest — it is the EXTERNAL signed
    # record, deliberately NOT covered by the manifest it would close the
    # cycle on (ADR-132: artifacts → manifest → digest → catalog entry).
    _write(out_dir / f"releases/{pub}/catalog_entry.json", canonical_json(catalog_entry))

    # P35.13 / SIG-REL-009 (G3 §6.2): the ``sig.site-release/1`` object —
    # the stamp's machine-readable twin. Emitted AFTER the manifest because
    # its ``integrity_manifest.sha256`` names the manifest digest: like the
    # catalog entry it is deliberately NOT covered by the manifest it would
    # close the hash cycle on. The validator cross-checks it against the
    # descriptor + manifest instead (the §6.2 fields all derive from the v2
    # descriptor — no independently fabricated values). Two byte-identical
    # copies: the immutable one inside the release namespace and the
    # release-tree root object ``/release.json`` resolves to when this
    # release is the active one (the activation seam stages it; the publish
    # allow-list protects the name — PROTECTED_NAMES).
    site_release_rel: str | None = None
    if descriptor.get("schema") == RI.DESCRIPTOR_SCHEMA_V2:
        routes_path = (repo_root or _REPO_ROOT) / "ops" / "public_routes.toml"
        routes_sha = sha256_hex(routes_path.read_bytes()) if routes_path.is_file() else None
        site_release = SR.site_release_document(
            descriptor,
            pub,
            integrity_manifest_sha256=manifest_sha,
            routes_sha256=routes_sha,
        )
        site_release_failures = SR.validate_site_release(site_release)
        if site_release_failures:
            raise ReleaseError(
                "the assembled sig.site-release/1 fails validation — "
                "refusing to emit an invalid release.json:\n  " + "\n  ".join(site_release_failures)
            )
        site_release_bytes = canonical_json(site_release)
        site_release_rel = f"releases/{pub}/release.json"
        _write(out_dir / site_release_rel, site_release_bytes)
        _write(out_dir / "release.json", site_release_bytes)

    report = {
        "schema": "sig.release-build-report/1",
        "publication_id": pub,
        "manifest_sha256": manifest_sha,
        "descriptor_sha256": descriptor_sha256(descriptor),
        "records": total_records,
        "compartments": comp_meta,
        "evidence_pages": evidence_count,
        "dossier_pages": dossier_count,
        "artifacts": len(artifacts),
        "export_dir": str(export_dir),
    }
    _write(out_dir / "release/build_report.json", canonical_json(report))

    # §3.3 rule 4 (P35.12): no emitted date may be later than built_at —
    # scanned over the stamp surfaces (descriptor, catalog entry, report,
    # landings) after emit, fail-closed.
    if descriptor.get("schema") == RI.DESCRIPTOR_SCHEMA_V2:
        built_dt = RI.parse_instant((descriptor.get("build") or {}).get("built_at"))
        if built_dt is not None:
            date_failures = RI.emitted_file_date_failures(
                [
                    out_dir / f"releases/{pub}/descriptor.json",
                    out_dir / f"releases/{pub}/catalog_entry.json",
                    out_dir / "release/build_report.json",
                    out_dir / f"releases/{pub}/index.html",
                    out_dir / f"r/{pub}/index.html",
                    # P35.13: the stamp + its machine twin are date surfaces
                    # too — release.json's instants derive from the
                    # descriptor, never the wall clock.
                    out_dir / f"releases/{pub}/release.json",
                    out_dir / "release.json",
                ],
                built_dt,
            )
            if date_failures:
                raise ReleaseError(
                    "emitted date later than built_at — the release stamps are "
                    "not date-true (SIG-REL-003):\n  " + "\n  ".join(date_failures)
                )

    return ReleaseBuild(
        publication_id=pub,
        descriptor=descriptor,
        manifest_sha256=manifest_sha,
        out_dir=out_dir,
        report=report,
    )


# --------------------------------------------------------------------------- #
# Validation                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class ValidationReport:
    publication_id: str
    state: str  # "complete" | "incomplete"
    failures: list[str]
    artifacts_checked: int


class _LinkParser(HTMLParser):
    """Collect every ``href``/``action`` target an exports-rendered page
    declares (P34.34a). Parse-time only — nothing is fetched."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in ("href", "action") and value:
                self.links.append(value)


def _link_target(page_rel: str, href: str) -> str | None:
    """Normalise one ``href``/``action`` to the site-root-relative route it
    resolves to, or ``None`` when the crawl does not follow it (external
    scheme, protocol-relative, fragment-only, query-only)."""
    href = href.strip()
    if not href or href.startswith("#") or href.startswith("?"):
        return None
    # fragment + query never change the resolved file
    path = href.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None
    if path.startswith("//"):
        return None  # protocol-relative external
    schemeish = path.split("/", 1)[0]
    if ":" in schemeish:
        return None  # http: https: mailto: tel: data: etc.
    path = unquote(path)
    if path.startswith("/"):
        return path.lstrip("/")
    # relative link — resolve against the page's directory route
    base = page_rel
    if base.endswith("index.html"):
        base = base[: -len("index.html")]
    elif "/" in base:
        base = base.rsplit("/", 1)[0] + "/"
    else:
        base = ""
    return posixpath.normpath(posixpath.join(base, path)).lstrip("/")


def _route_resolves(root: Path, route: str) -> bool:
    """Whether ``route`` (site-root-relative, already unquoted) maps to a real
    file under ``root`` — a literal asset or a directory-style index page."""
    rel = route.rstrip("/")
    if not rel:
        return (root / "index.html").is_file()
    return (root / rel).is_file() or (root / rel / "index.html").is_file()


def _route_is_external_or_denied(route: str, denied: frozenset[str]) -> bool:
    """Whether a missing-from-corpus route is still an honest resolution:
    a known site-shell/overlay route (the public Astro surface and the
    activation overlay own them — enumerated in ``release_pages``), or a
    route the withdrawal barrier denies explicitly (the 410 is a recorded
    answer, never a 404)."""
    norm = route.rstrip("/")
    if norm in EXTERNAL_LINK_ROUTES:
        return True
    if any(norm.startswith(p) for p in EXTERNAL_LINK_PREFIXES):
        return True
    return norm in denied or f"{norm}/index.html" in denied


def link_crawl_failures(corpus_root: Path | str, *, denied_routes: Iterable[str] = ()) -> list[str]:
    """P34.34a (DR-C4-01): crawl every exports-rendered page under
    ``corpus_root`` and return one failure line per same-origin
    ``href``/``action`` that resolves to nothing — neither a staged file, a
    known site-shell/overlay route, nor an explicitly denied (410) route.

    No HTTP: routes resolve over local paths (``dir/index.html`` is a
    directory route's target), so the check is byte-deterministic on the
    release corpus itself. ``denied_routes`` is the staged withdrawal
    barrier's route list (``apply_withdrawals``'s ``routes``), empty when
    crawling a pre-activation ``release_dir``.
    """
    root = Path(corpus_root)
    denied = frozenset(r.strip("/") for r in denied_routes)
    failures: list[str] = []
    for html_path in sorted(root.rglob("*.html")):
        page_rel = html_path.relative_to(root).as_posix()
        try:
            text = html_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"{page_rel}: unreadable html ({exc})")
            continue
        parser = _LinkParser()
        try:
            parser.feed(text)
        except Exception as exc:  # noqa: BLE001 - malformed markup is a failure
            failures.append(f"{page_rel}: unparseable html ({exc})")
            continue
        for href in parser.links:
            route = _link_target(page_rel, href)
            if route is None:
                continue
            if _route_resolves(root, route) or _route_is_external_or_denied(route, denied):
                continue
            failures.append(
                f"{page_rel}: unresolved same-origin link {href!r} (route /{route.rstrip('/')}/)"
            )
    return failures


def validate_release(release_dir: Path | str) -> ValidationReport:
    """Re-verify a built release bundle against its integrity manifest.

    Every listed artifact must exist with the recorded byte size + sha256;
    no undeclared file may sit under ``r/`` (except the external
    ``catalog_entry.json``/``integrity_manifest.json``); each compartment's
    ``records.index.jsonl`` must enumerate every emitted record exactly
    once; and every same-origin link on every exports-rendered page must
    resolve (P34.34a — the link-resolution crawl). Incomplete → the caller
    refuses staging; the latest pointer never moves on a partial release.
    """
    release_dir = Path(release_dir)
    manifest_paths = list(release_dir.glob("releases/*/integrity_manifest.json"))
    if len(manifest_paths) != 1:
        return ValidationReport(
            publication_id="",
            state="incomplete",
            failures=[f"expected exactly one integrity manifest, found {len(manifest_paths)}"],
            artifacts_checked=0,
        )
    integrity = _read_json(manifest_paths[0])
    pub = str(integrity["publication_id"])
    failures: list[str] = []
    listed = {a["path"] for a in integrity.get("artifacts") or []}
    checked = 0
    for art in integrity.get("artifacts") or []:
        rel = str(art["path"])
        target = release_dir / rel
        if not target.exists():
            failures.append(f"missing artifact: {rel}")
            continue
        digest, size = _sha256_file(target)
        checked += 1
        if digest != art["sha256"] or size != art["byte_size"]:
            failures.append(f"digest/size mismatch: {rel}")
    # undeclared files under r/ and the release landing dir
    external = {
        f"releases/{pub}/integrity_manifest.json",
        f"releases/{pub}/catalog_entry.json",
        # P35.13: the site-release object is emitted after the manifest like
        # the catalog entry — external to the hash cycle by construction.
        f"releases/{pub}/release.json",
    }
    for base in ("r", f"releases/{pub}"):
        root = release_dir / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(release_dir).as_posix()
                if rel not in listed and rel not in external:
                    failures.append(f"undeclared artifact present: {rel}")
    # per-compartment index completeness
    for comp in integrity.get("compartments") or []:
        cid = comp["compartment"]
        idx_rel = f"r/{pub}/c/{cid}/records.index.jsonl"
        idx_path = release_dir / idx_rel
        if not idx_path.exists():
            failures.append(f"missing compartment index: {idx_rel}")
            continue
        try:
            rows = list(_iter_jsonl(idx_path))
        except Exception:  # noqa: BLE001 - malformed index IS a validation failure
            failures.append(f"compartment index not parseable: {idx_rel}")
            continue
        keys = [str(r.get("record_key")) for r in rows]
        if len(keys) != len(set(keys)):
            failures.append(f"duplicate record keys in {idx_rel}")
        if len(keys) != int(comp["record_count"]):
            failures.append(
                f"compartment {cid}: index has {len(keys)} records, "
                f"manifest declares {comp['record_count']}"
            )
        index_digest, _ = _sha256_file(idx_path)
        if index_digest != comp.get("index_sha256"):
            failures.append(f"compartment {cid}: index digest mismatch")
        for r in rows:
            for rel in (str(r.get("path")), str(r.get("json_path"))):
                if rel == "None" or not (release_dir / rel).exists():
                    failures.append(f"index references missing file: {rel}")
        # P32.14 (SIG-FIND-003): the per-compartment search index must
        # reconcile to the same record count and digest before staging.
        sdesc_rel = f"r/{pub}/c/{cid}/{INDEX_DESCRIPTOR_FILE}"
        sdesc_path = release_dir / sdesc_rel
        if not sdesc_path.exists():
            failures.append(f"missing search index descriptor: {sdesc_rel}")
        else:
            try:
                sdesc = _read_json(sdesc_path)
                scope = sdesc.get("scope") or {}
            except Exception:  # noqa: BLE001 - malformed = incomplete
                scope = {}
                failures.append(f"search index descriptor not parseable: {sdesc_rel}")
            # `or -1` would misread a legitimate scope of 0 as missing (the
            # honest zero-record release, C4 NEW-31) — test for None only.
            _indexed = scope.get("indexed_records")
            if _indexed is None or int(_indexed) != int(comp["record_count"]):
                failures.append(
                    f"compartment {cid}: search index scope "
                    f"{scope.get('indexed_records')} != {comp['record_count']}"
                )
            _eligible = scope.get("eligible_records")
            if _eligible is None or int(_eligible) != int(comp["record_count"]):
                failures.append(
                    f"compartment {cid}: search index eligible scope "
                    f"{scope.get('eligible_records')} != {comp['record_count']}"
                )
            if scope.get("excluded_records_by_reason"):
                failures.append(
                    f"compartment {cid}: search index claims exclusions "
                    f"{scope['excluded_records_by_reason']} — the released "
                    "projection must index every eligible record"
                )
        sdb_rel = f"r/{pub}/c/{cid}/{INDEX_FILE}"
        sdb_path = release_dir / sdb_rel
        if not sdb_path.exists():
            failures.append(f"missing search index: {sdb_rel}")
        else:
            sdigest, _ = _sha256_file(sdb_path)
            if sdigest != comp.get("search_index_sha256"):
                failures.append(f"compartment {cid}: search index digest mismatch")
            n_indexed = comp.get("search_indexed_records")
            if n_indexed is not None and int(n_indexed) != int(comp["record_count"]):
                failures.append(
                    f"compartment {cid}: catalog search_indexed_records "
                    f"{n_indexed} != {comp['record_count']}"
                )
    # P35.12 (SIG-REL-001): a v2 descriptor is also re-validated field-by-field —
    # an integrity-complete bundle whose descriptor fails §3.2 is incomplete.
    descriptor: Any = None
    desc_path = release_dir / f"releases/{pub}/descriptor.json"
    if desc_path.exists():
        try:
            descriptor = _read_json(desc_path)
        except Exception:  # noqa: BLE001 - unparseable descriptor is a failure
            descriptor = None
            failures.append(f"descriptor not parseable: {desc_path.name}")
        if isinstance(descriptor, Mapping) and descriptor.get("schema") == (
            RI.DESCRIPTOR_SCHEMA_V2
        ):
            for f in RI.validate_descriptor(descriptor):
                failures.append(f"descriptor: {f}")
    # P35.13 / SIG-REL-009 (G3 §6.2): the ``sig.site-release/1`` object — the
    # stamp's machine twin — sits OUTSIDE the manifest cycle (its
    # ``integrity_manifest.sha256`` names the manifest digest; hashing it in
    # would close the cycle), so it is verified by cross-check instead:
    # schema-valid, byte-identical across its two copies, and every
    # descriptor-derived field equal to the descriptor's own value. A v1
    # release carries none; a release.json on a v1 tree is a failure.
    is_v2 = isinstance(descriptor, Mapping) and descriptor.get("schema") == (
        RI.DESCRIPTOR_SCHEMA_V2
    )
    sr_rel = f"releases/{pub}/release.json"
    sr_path = release_dir / sr_rel
    root_path = release_dir / "release.json"
    if is_v2:
        if not sr_path.exists():
            failures.append(f"missing site-release object: {sr_rel}")
        else:
            try:
                site_doc = _read_json(sr_path)
            except Exception:  # noqa: BLE001 - unparseable = failure
                site_doc = None
                failures.append(f"site-release object not parseable: {sr_rel}")
            if isinstance(site_doc, Mapping):
                for f in SR.validate_site_release(site_doc):
                    failures.append(f"release.json: {f}")
                if site_doc.get("publication_id") != pub:
                    failures.append(
                        f"release.json publication_id {site_doc.get('publication_id')!r} "
                        f"!= the release's {pub!r}"
                    )
                if site_doc.get("descriptor_sha256") != descriptor_sha256(descriptor):
                    failures.append("release.json descriptor_sha256 != descriptor digest")
                snap = descriptor.get("snapshot") or {}
                for field, want in (
                    ("label", descriptor.get("label")),
                    ("as_of_world", snap.get("as_of_world")),
                    ("as_of_belief", snap.get("as_of_belief")),
                    ("belief_pinned", bool(snap.get("belief_pinned"))),
                    ("spine_watermark", snap.get("spine_watermark")),
                    ("built_at", (descriptor.get("build") or {}).get("built_at")),
                ):
                    if site_doc.get(field) != want:
                        failures.append(
                            f"release.json {field} {site_doc.get(field)!r} != descriptor's {want!r}"
                        )
                code = descriptor.get("code") or {}
                if (site_doc.get("code") or {}).get("commit") != code.get("commit"):
                    failures.append("release.json code.commit != descriptor's code.commit")
                integrity_ptr = site_doc.get("integrity_manifest") or {}
                if integrity_ptr.get("path") != f"releases/{pub}/integrity_manifest.json":
                    failures.append(
                        f"release.json integrity_manifest.path "
                        f"{integrity_ptr.get('path')!r} != "
                        f"releases/{pub}/integrity_manifest.json"
                    )
                if integrity_ptr.get("sha256") != sha256_hex(manifest_paths[0].read_bytes()):
                    failures.append("release.json integrity_manifest.sha256 != manifest digest")
        if not root_path.exists():
            failures.append(
                "missing site-root release.json copy — every stamped page's "
                "describedby must resolve"
            )
        elif sr_path.exists() and root_path.read_bytes() != sr_path.read_bytes():
            failures.append(
                "release.json copies drift — the site-root object and the "
                "namespace copy must be byte-identical"
            )
    elif sr_path.exists() or root_path.exists():
        failures.append(
            "release.json present on a non-v2 release — the sig.site-release/1 "
            "schema carries a sig-YYYY-MM-DD.N label v1 never has"
        )
    # P34.34a (DR-C4-01): the same-origin link-resolution crawl — every
    # href/action on every emitted page must resolve to a corpus file or a
    # known site-shell/overlay route; a broken link is a release failure
    # naming the page and the target.
    failures.extend(link_crawl_failures(release_dir))
    return ValidationReport(
        publication_id=pub,
        state="complete" if not failures else "incomplete",
        failures=failures,
        artifacts_checked=checked,
    )


# --------------------------------------------------------------------------- #
# The registry: catalog, latest pointer, compat index, withdrawals             #
# --------------------------------------------------------------------------- #


@dataclass
class ReleaseRegistry:
    """The mutable serving registry — everything here is OUTSIDE the hashed
    release bytes (activation timestamps live in ``activations/`` receipts,
    never inside artifacts)."""

    root: Path

    def _path(self, name: str) -> Path:
        return self.root / name

    def _load(self, name: str, default: Any) -> Any:
        p = self._path(name)
        return _read_json(p) if p.exists() else default

    def catalog(self) -> dict[str, Any]:
        return self._load("catalog.json", {"schema": CATALOG_SCHEMA, "publications": []})

    def latest(self) -> dict[str, Any] | None:
        return self._load("latest.json", None)

    def compat(self) -> dict[str, Any]:
        return self._load("compat_index.json", {"schema": COMPAT_SCHEMA, "entries": []})

    def withdrawals(self) -> list[DispositionRecord]:
        raw = self._load("withdrawals.json", {"schema": WITHDRAWAL_SCHEMA, "entries": []})
        out: list[DispositionRecord] = []
        for e in raw.get("entries") or []:
            out.append(
                DispositionRecord(
                    target_kind=TargetKind(str(e["target_kind"])),
                    target_id=str(e["target_id"]),
                    disposition=Disposition(str(e["disposition"])),
                    reason_category=ReasonCategory(str(e["reason_category"])),
                    authority=str(e["authority"]),
                    decided_at=(
                        datetime.fromisoformat(e["decided_at"]) if e.get("decided_at") else None
                    ),
                    policy_version=str(e.get("policy_version") or "publication-eligibility/1"),
                    evidence_claim_id=e.get("evidence_claim_id"),
                    supersedes=e.get("supersedes"),
                    seq=int(e.get("seq") or 0),
                )
            )
        return out

    def save_withdrawals(self, entries: Sequence[DispositionRecord]) -> None:
        payload = {
            "schema": WITHDRAWAL_SCHEMA,
            "entries": [
                {
                    "target_kind": e.target_kind.value,
                    "target_id": e.target_id,
                    "disposition": e.disposition.value,
                    "reason_category": e.reason_category.value,
                    "authority": e.authority,
                    "decided_at": e.decided_at.isoformat() if e.decided_at else None,
                    "policy_version": e.policy_version,
                    "evidence_claim_id": e.evidence_claim_id,
                    "supersedes": e.supersedes,
                    "seq": e.seq,
                }
                for e in entries
            ],
        }
        _atomic_write(self._path("withdrawals.json"), canonical_json(payload))

    def find(self, pub: str) -> dict[str, Any] | None:
        for e in self.catalog().get("publications") or []:
            if e.get("publication_id") == pub:
                return e
        return None


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if dst.exists():
            dst.unlink()
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _stage_tree(release_dir: Path, staged: Path, pub: str) -> None:
    """Materialise one release's public routes into the staged tree
    (hardlinks where possible — the same immutable bytes, never rewritten)."""
    for base in ("r", f"releases/{pub}"):
        root = release_dir / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(release_dir)
                _link_or_copy(path, staged / rel)


def load_mutable_stamp(source: Path) -> dict[str, str] | None:
    """The §6.1 "latest view" stamp for the mutable overlay pages
    (P35.13 / SIG-REL-009): the releases index, the entity convenience
    stubs and the withdrawal tombstones all answer for the CURRENT
    release, so they carry its identity — projected from that release's
    ``sig.site-release/1`` with the site-root ``/release.json`` as the
    describedby target. A release that emits no site-release object (v1)
    leaves the overlay honestly unstamped; an unparseable file fails open
    the same way — the immutable copy's own validation is fail-closed."""
    if not source.is_file():
        return None
    try:
        doc = _read_json(source)
    except (OSError, ValueError):
        return None
    return release_stamp_view(doc, describedby="/release.json", variant="latest")


def _stage_root_release_json(staged: Path, source: Path | None) -> None:
    """Re-point the site-root ``release.json`` at the ACTIVE release's
    immutable copy — the target every mutable page's
    ``<link rel="describedby" href="/release.json">`` resolves to.
    Mutable like the latest pointer it names: removed when no release is
    current, never edited (the bytes are always the release's own)."""
    target = staged / "release.json"
    if source is not None and source.is_file():
        _link_or_copy(source, target)
    elif target.exists():
        target.unlink()


def _entity_overlay(
    staged: Path,
    release_dir: Path,
    pub: str,
    catalog_entry: Mapping[str, Any],
    denied_stubs: Mapping[str, DispositionRecord] | None = None,
    stamp: Mapping[str, Any] | None = None,
) -> int:
    """Emit ``/entity/<type>/<uuid>/`` convenience stubs for the ACTIVE
    release — mutable pointers, never citations.

    ``denied_stubs`` is the withdrawal barrier's stub deny set
    (``entity/<type>/<id>`` route → the effective denying disposition): a
    stub for a denied record emits the ``sig.tombstone/1`` stub page
    instead of a link into denied bytes — the stubs are generated FROM the
    deny set, never a divergent hand list."""
    denied = denied_stubs or {}
    count = 0
    for comp in catalog_entry.get("compartments") or []:
        idx = release_dir / f"r/{pub}/c/{comp['compartment']}/records.index.jsonl"
        if not idx.is_file():
            # denied bytes may have been tombstoned into a route directory —
            # never parse a tombstone as an index
            continue
        for row in _iter_jsonl(idx):
            stub_route = f"entity/{row['entity_type']}/{row['entity_id']}"
            if stub_route in denied:
                stub = _stub_tombstone(
                    str(row["entity_type"]),
                    str(row["entity_id"]),
                    denied[stub_route],
                    release_label=str(catalog_entry.get("data_release_id") or "") or None,
                    stamp=stamp,
                )
            else:
                stub = entity_stub(
                    entity_type=str(row["entity_type"]),
                    entity_id=str(row["entity_id"]),
                    latest_publication=pub,
                    record_href="/" + str(row["path"]),
                    stamp=stamp,
                )
            _write(
                staged / f"{stub_route}/index.html",
                stub,
            )
            count += 1
    return count


#: Sentinel for ``_emit_overlay``'s ``latest_pub`` — "read the pointer file"
#: vs the explicit ``None`` ("no current release") a clear passes.
_LATEST_FROM_REGISTRY: Any = object()


def _emit_overlay(
    registry: ReleaseRegistry,
    *,
    stamp: Mapping[str, Any] | None = None,
    latest_pub: Any = _LATEST_FROM_REGISTRY,
) -> None:
    """Regenerate the mutable overlay — releases index + compat index copy —
    deterministically from the catalog. ``stamp`` is the §6.1 provenance
    view of the release the overlay names (P35.13): the callers pass the
    release they are pointing at — ``latest.json`` has not necessarily
    flipped yet when the overlay is written. ``latest_pub`` carries the
    target release for the same reason: the callers that flip the pointer
    pass it explicitly, so the ``(latest)`` marker never lands on the
    release being replaced."""
    staged = registry.root / "staged"
    cat = registry.catalog()
    latest = registry.latest() or {}
    target = latest.get("publication_id") if latest_pub is _LATEST_FROM_REGISTRY else latest_pub
    entries = cat.get("publications") or []
    _write(
        staged / "releases/index.html",
        releases_index(entries, latest=target, stamp=stamp),
    )
    _atomic_write(staged / "releases" / "catalog.json", canonical_json(cat))
    compat = registry.compat()
    _atomic_write(staged / "compat_index.json", canonical_json(compat))


def _update_compat(registry: ReleaseRegistry, entry: Mapping[str, Any]) -> None:
    compat = registry.compat()
    entries = compat.get("entries") or []
    c = entry.get("compat") or {}
    row = {
        "as_of_world": c.get("as_of_world"),
        "as_of_belief": c.get("as_of_belief"),
        "ruleset_version": c.get("ruleset_version"),
        "publication_id": entry["publication_id"],
    }
    if row not in entries:
        entries.append(row)
    entries = sorted(
        entries,
        key=lambda e: (
            str(e.get("as_of_world")),
            str(e.get("as_of_belief")),
            str(e.get("ruleset_version")),
            str(e.get("publication_id")),
        ),
    )
    _atomic_write(
        registry._path("compat_index.json"),
        canonical_json({"schema": COMPAT_SCHEMA, "entries": entries}),
    )


def activate(
    registry_dir: Path | str,
    release_dir: Path | str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate + stage + activate a built release; flip the latest pointer.

    * A namespace whose descriptor rebinds to **different final bytes**
      (same ``publication_id``, different ``manifest_sha256``) is REFUSED —
      immutable namespaces never accept second contents.
    * Re-activation with identical bytes is an idempotent no-op.
    * The latest pointer flips only after the whole staged tree verifies.
    """
    registry = ReleaseRegistry(Path(registry_dir))
    release_dir = Path(release_dir)
    report = validate_release(release_dir)
    if report.state != "complete":
        raise ReleaseError(
            f"release {report.publication_id or '?'} failed validation — "
            f"staging refused: {report.failures[:5]}"
        )
    entry = _read_json(release_dir / f"releases/{report.publication_id}/catalog_entry.json")
    pub = str(entry["publication_id"])
    manifest_sha = str(entry["manifest_sha256"])

    now = now or datetime.now(UTC)
    # §3.3 rule 3 (P35.12): for any activation, activated_at ≥ built_at —
    # a release can never be activated before its recorded build instant.
    desc_path = release_dir / f"releases/{pub}/descriptor.json"
    if desc_path.exists():
        desc = _read_json(desc_path)
        if desc.get("schema") == RI.DESCRIPTOR_SCHEMA_V2:
            built = RI.parse_instant((desc.get("build") or {}).get("built_at"))
            if built is not None and now < built:
                raise ReleaseError(
                    f"activated_at {now.isoformat()} is earlier than built_at "
                    f"{built.isoformat()} — activation refused (SIG-REL-003)"
                )

    existing = registry.find(pub)
    if existing is not None and str(existing.get("manifest_sha256")) != manifest_sha:
        raise ReleaseError(
            f"publication {pub} already activated with manifest "
            f"{existing.get('manifest_sha256')} — different bytes under the "
            "same namespace are refused (SIG-FIND-001)"
        )

    staged = registry.root / "staged"
    _stage_tree(release_dir, staged, pub)
    # P35.13 / SIG-REL-009: the mutable pages (releases index, entity stubs,
    # tombstones) answer for THIS release once the pointer flips — project
    # the §6.1 stamp from its sig.site-release/1 before the overlay writes.
    mutable_stamp = load_mutable_stamp(release_dir / "release.json")
    # The withdrawal barrier applies to EVERY staged release, current AND
    # historical (a withhold in R2 denies under an R1 rollback). The stubs
    # this activation emits point at THIS release — the deny set scopes
    # them to pub.
    applied = apply_withdrawals(staged, registry.withdrawals(), active_pub=pub, stamp=mutable_stamp)
    # P34.34a (DR-C4-01): the staged corpus gets the same link-resolution
    # crawl the release passed alone — now over the composed tree, where an
    # explicitly denied route (the withdrawal barrier's 410 tombstone)
    # counts as resolved. A broken same-origin link refuses activation
    # before the catalog or the latest pointer moves.
    link_failures = link_crawl_failures(staged, denied_routes=applied.get("routes") or ())
    if link_failures:
        raise ReleaseError(
            f"staged tree for {pub} carries {len(link_failures)} unresolved "
            f"same-origin link(s) — activation refused: {link_failures[:5]}"
        )

    catalog = registry.catalog()
    pubs = catalog.get("publications") or []
    if existing is None:
        pubs.append(dict(entry))
        _atomic_write(
            registry._path("catalog.json"),
            canonical_json({"schema": CATALOG_SCHEMA, "publications": pubs}),
        )
    _update_compat(registry, entry)

    stubs = _entity_overlay(
        staged,
        release_dir,
        pub,
        entry,
        denied_stubs=applied.get("entity_stubs"),
        stamp=mutable_stamp,
    )
    _emit_overlay(registry, stamp=mutable_stamp, latest_pub=pub)

    now = now or datetime.now(UTC)
    ordinal = len(pubs)
    activation = {
        "schema": ACTIVATION_SCHEMA,
        "publication_id": pub,
        "manifest_sha256": manifest_sha,
        "activated_at": now.isoformat(),
        "ordinal": ordinal,
        "validator": {
            "state": report.state,
            "artifacts_checked": report.artifacts_checked,
        },
        "withdrawals_applied": _apply_summary(applied),
        "entity_stubs": stubs,
    }
    _write(registry._path(f"activations/{pub}.json"), canonical_json(activation))
    _atomic_write(
        registry._path("latest.json"),
        canonical_json(
            {
                "schema": LATEST_SCHEMA,
                "publication_id": pub,
                "manifest_sha256": manifest_sha,
                "data_release_id": entry.get("data_release_id"),
                "ordinal": ordinal,
            }
        ),
    )
    # P35.13: the site-root release.json follows the pointer — the active
    # release's immutable copy, staged only after latest.json names it.
    _stage_root_release_json(staged, release_dir / "release.json")
    return activation


def promote(
    registry_dir: Path | str,
    release_dir: Path | str,
    *,
    repo_root: Path | str | None = None,
    tree_clean: bool | None = None,
    pushed: bool | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The SIG-REL-002 promotion gate — ``activate()`` behind every refusal.

    Only a ``sig.publication-descriptor/2`` release may promote: v1
    candidates (the ``p-17b713`` fixture class) are refused by the v2-only
    rule alone. The remaining refusals are named by
    :func:`release_identity.promotion_refusals` — dirty tree (recorded or
    live), unpushed commit, ``0.0.0``/missing version fields, a non-sha
    commit, an as-of not later than the latest activated release's. On
    zero refusals the release activates exactly as :func:`activate` does —
    the gate adds checks, never a different activation path. Nothing
    hosted is touched: the registry is the caller's local directory.
    """
    release_dir = Path(release_dir)
    # Find the descriptor under releases/<pub>/descriptor.json — the release
    # dir's own report names the namespace when it exists.
    descriptor: Mapping[str, Any] | None = None
    for cand in sorted(release_dir.glob("releases/*/descriptor.json")):
        descriptor = _read_json(cand)
        break
    if descriptor is None:
        raise ReleaseError(
            f"{release_dir} carries no releases/*/descriptor.json — nothing to promote"
        )
    registry = ReleaseRegistry(Path(registry_dir))
    previous = registry.latest()
    previous_asof: str | None = None
    if previous is not None:
        prev_pub = str(previous.get("publication_id") or "")
        prev_entry = registry.find(prev_pub)
        if prev_entry is not None:
            previous_asof = (
                str((prev_entry.get("reproducibility") or {}).get("as_of_world") or "") or None
            )
    refusals = RI.promotion_refusals(
        descriptor,
        repo_root=repo_root,
        previous_as_of_world=previous_asof,
        tree_clean=tree_clean,
        pushed=pushed,
    )
    if refusals:
        raise ReleaseError("promotion refused (SIG-REL-002):\n  - " + "\n  - ".join(refusals))
    return activate(registry_dir, release_dir, now=now)


def rollback(
    registry_dir: Path | str,
    publication_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Flip the latest pointer back to an earlier ACTIVATED release.

    The staged namespace bytes stay put (every activated release remains
    reachable); only the mutable overlay re-points — and the CURRENT
    withdrawal registry is re-applied, so a withhold recorded under a later
    release still denies under the rollback (ADR-124/ADR-132). Rolling the
    latest pointer to a namespace that is itself under a current denying
    release-level disposition is REFUSED: "latest" must never retarget
    every convenience URL at a wholly-denied namespace (the release stays
    reachable at its own routes only as tombstones).
    """
    registry = ReleaseRegistry(Path(registry_dir))
    entry = registry.find(publication_id)
    if entry is None:
        raise ReleaseError(f"publication {publication_id} is not activated")
    pub = str(entry["publication_id"])
    eff_release = latest_disposition(
        [
            r
            for r in registry.withdrawals()
            if r.target_kind == TargetKind.RELEASE_ARTIFACT and r.target_id == pub
        ]
    )
    if eff_release is not None and not access_decision(eff_release).permitted:
        raise ReleaseError(
            f"publication {pub} is under a current {eff_release.disposition.value} "
            "disposition — the latest pointer cannot be rolled to a denied "
            "namespace (ADR-132)"
        )
    staged = registry.root / "staged"
    if not (staged / f"r/{pub}").exists():
        raise ReleaseError(
            f"staged tree for {pub} is absent — cannot roll back to a "
            "release whose bytes were never staged"
        )
    # P35.13: the rolled-to release's stamp names the mutable pages —
    # read its sig.site-release/1 from the staged namespace copy.
    mutable_stamp = load_mutable_stamp(staged / f"releases/{pub}/release.json")
    applied = apply_withdrawals(staged, registry.withdrawals(), active_pub=pub, stamp=mutable_stamp)
    stubs = _entity_overlay(
        staged,
        registry.root / "staged",
        pub,
        entry,
        denied_stubs=applied.get("entity_stubs"),
        stamp=mutable_stamp,
    )
    _emit_overlay(registry, stamp=mutable_stamp, latest_pub=pub)
    now = now or datetime.now(UTC)
    latest = {
        "schema": LATEST_SCHEMA,
        "publication_id": pub,
        "manifest_sha256": entry.get("manifest_sha256"),
        "data_release_id": entry.get("data_release_id"),
        "ordinal": -1,  # rollback events carry ordinal -1 (receipts hold order)
        "rolled_back": True,
    }
    _atomic_write(registry._path("latest.json"), canonical_json(latest))
    _stage_root_release_json(staged, staged / f"releases/{pub}/release.json")
    _write(
        registry._path(f"activations/rollback-{pub}-{_ts(now)}.json"),
        canonical_json(
            {
                "schema": ACTIVATION_SCHEMA,
                "publication_id": pub,
                "manifest_sha256": entry.get("manifest_sha256"),
                "activated_at": now.isoformat(),
                "action": "rollback",
                "withdrawals_applied": _apply_summary(applied),
                "entity_stubs": stubs,
            }
        ),
    )
    return {"latest": pub, "stubs": stubs, "withdrawals_applied": _apply_summary(applied)}


def clear_latest_pointer(
    registry_dir: Path | str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Rollback to the honest 'no current release' state — the no-prior-
    pointer path a release rollback packet names (the first immutable
    release has no predecessor to re-point at).

    Removes the mutable ``latest.json`` convenience pointer rather than
    fabricating a predecessor, re-applies the CURRENT withdrawal registry,
    drops the active-release entity convenience stubs, re-emits the mutable
    overlay, and receipts the action. Every activated release stays
    reachable at its own immutable ``r/<pub>`` routes — nothing deletes
    release bytes, and the catalog/compat indexes are untouched.
    """
    registry = ReleaseRegistry(Path(registry_dir))
    latest_path = registry._path("latest.json")
    previous = registry.latest()
    if previous is None:
        raise ReleaseError(
            "latest.json is already absent — nothing to clear "
            "(a missing pointer is never silently re-cleared)"
        )
    staged = registry.root / "staged"
    applied = apply_withdrawals(staged, registry.withdrawals())
    entity_dir = staged / "entity"
    if entity_dir.exists():
        shutil.rmtree(entity_dir)
    latest_path.unlink()
    _emit_overlay(registry, latest_pub=None)
    # P35.13: with no current release the site-root release.json is absent —
    # an honest no-release answer, never a stale one.
    _stage_root_release_json(staged, None)
    now = now or datetime.now(UTC)
    _write(
        registry._path(f"activations/rollback-none-{_ts(now)}.json"),
        canonical_json(
            {
                "schema": ACTIVATION_SCHEMA,
                "publication_id": None,
                "manifest_sha256": previous.get("manifest_sha256"),
                "activated_at": now.isoformat(),
                "action": "rollback",
                "cleared_latest": previous.get("publication_id"),
                "withdrawals_applied": _apply_summary(applied),
            }
        ),
    )
    return {
        "cleared": True,
        "previous_latest": previous.get("publication_id"),
        "withdrawals_applied": _apply_summary(applied),
    }


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def record_withdrawal(
    registry_dir: Path | str,
    entries: Sequence[DispositionRecord],
) -> int:
    """Append disposition rows to the withdrawal registry (public-safe
    columns only — the write path validates via ``new_disposition``)."""
    registry = ReleaseRegistry(Path(registry_dir))
    current = registry.withdrawals()
    current.extend(entries)
    registry.save_withdrawals(current)
    staged = registry.root / "staged"
    if staged.exists():
        # The stubs the tree carries point at the CURRENT latest pointer —
        # the deny set's stub scope follows it.
        latest = registry.latest() or {}
        apply_withdrawals(staged, current, active_pub=latest.get("publication_id"))
    return len(entries)


# --------------------------------------------------------------------------- #
# The withdrawal barrier — before origin/CDN access                           #
# --------------------------------------------------------------------------- #


def _route_targets(staged: Path) -> Iterator[tuple[str, str, str, str]]:
    """Yield ``(route_kind, target_id, rel_path, shape)`` for every route a
    withdrawal can deny: entity record pages + their ``.json`` twins,
    evidence pages, whole release namespaces, and the ``/entity/<t>/<id>/``
    convenience stubs (``entity_stub`` — folded into the deny set under the
    stub rule below, not a bare entity lookup).

    ``shape`` is ``"page"`` for a directory/index route (``<route>/`` +
    ``<route>/index.html`` + the no-slash form all alias it) and ``"file"``
    for an exact-path file route — the deny map derives its alias set from
    it (P34.41: every alias of a denied route must answer the same 410
    tombstone)."""
    r_root = staged / "r"
    if r_root.exists():
        for pub_dir in sorted(r_root.glob("*")):
            pub = pub_dir.name
            yield ("release", pub, f"r/{pub}", "page")
            for rec in pub_dir.glob("c/*/entity/*/*/"):
                yield (
                    "entity",
                    rec.name,
                    f"{rec.relative_to(staged).as_posix()}".rstrip("/"),
                    "page",
                )
            for jf in pub_dir.glob("c/*/entity/*/*.json"):
                yield (
                    "entity",
                    jf.stem,
                    jf.relative_to(staged).as_posix(),
                    "file",
                )
            for ev in pub_dir.glob("c/*/evidence/*/"):
                yield (
                    "artifact",
                    ev.name,
                    f"{ev.relative_to(staged).as_posix()}".rstrip("/"),
                    "page",
                )
    entity_root = staged / "entity"
    if entity_root.exists():
        for stub_dir in sorted(entity_root.glob("*/*/")):
            yield (
                "entity_stub",
                stub_dir.name,
                stub_dir.relative_to(staged).as_posix().rstrip("/"),
                "page",
            )


# --------------------------------------------------------------------------- #
# sig.tombstone/1 — the deny-map body (P34.41)                                  #
# --------------------------------------------------------------------------- #

#: The serving-only subtree ``apply_withdrawals`` regenerates: one
#: ``sig.tombstone/1`` body per denied route, served BY the deny map's
#: ``error_page 410`` internal redirect — never a public route itself
#: (nginx.conf marks the whole prefix ``internal``). Hash-named so the map
#: stays deterministic and can never collide with a content route.
TOMBSTONE_BODY_DIR = "conf/tombstone"

#: nginx ``location =`` URIs carry a route verbatim — fail closed on any
#: character outside the URI-unreserved set plus ``/`` so a malformed route
#: can never emit a broken conf line (a route here is an artifact filename
#: — alnum plus ``-._~/`` in practice). No ``%``: nginx matches locations
#: on the decoded URI, so a literal percent could never match safely.
_CONF_URI_SAFE = re.compile(r"^/[A-Za-z0-9._~/-]+$")


def _tombstone_body_rel(route: str, ext: str) -> str:
    """The deterministic staged path of one denied route's nginx body file
    (``conf/tombstone/<sha24>.<ext>``)."""
    return f"{TOMBSTONE_BODY_DIR}/{sha256_hex(route.encode('utf-8'))[:24]}.{ext}"


def _disposition_ref(eff: DispositionRecord) -> str:
    """The content-derived public reference for a recorded disposition:
    ``sha256:`` over the public-safe columns ``withdrawals.json``
    serialises — a stable handle a tombstone may name without exposing the
    row's privileged fields."""
    body = canonical_json(
        {
            "target_kind": eff.target_kind.value,
            "target_id": eff.target_id,
            "disposition": eff.disposition.value,
            "reason_category": eff.reason_category.value,
            "authority": eff.authority,
            "decided_at": eff.decided_at.isoformat() if eff.decided_at else None,
            "policy_version": eff.policy_version,
            "evidence_claim_id": eff.evidence_claim_id,
            "supersedes": eff.supersedes,
            "seq": eff.seq,
        }
    )
    return "sha256:" + sha256_hex(body)


def _decided_iso(eff: DispositionRecord) -> str:
    return eff.decided_at.isoformat() if eff.decided_at else "unrecorded"


def _tombstone_doc(
    eff: DispositionRecord, route: str, *, release_label: str | None
) -> dict[str, Any]:
    """The ``sig.tombstone/1`` body one denied route serves (P34.41): the
    machine form of the tombstone page — target identity, the withdrawal
    instant, the public-safe reason class, the content-derived disposition
    reference, the release label and the corrections link. ``superseded_by``
    names a recorded successor when one exists (the effective disposition
    is by definition current — no superseding record is known at deny
    time). Never the privileged rationale, never an e-mail address."""
    dec = access_decision(eff)
    reason = dec.reason_category.value if dec.reason_category else None
    return {
        "schema": TOMBSTONE_SCHEMA,
        "permitted": False,
        "route": route,
        "target_kind": eff.target_kind.value,
        "target_id": eff.target_id,
        "disposition": eff.disposition.value,
        "reason_class": reason,
        "withdrawn_at": _decided_iso(eff),
        "authority": dec.authority,
        "policy_version": dec.policy_version,
        "disposition_ref": _disposition_ref(eff),
        "superseded_by": None,
        "release": release_label,
        "corrections": CORRECTIONS_HREF,
        # Back-compat fields earlier consumers read (P32.13/P32.14).
        "reason_category": reason,
        "decided": _decided_iso(eff),
    }


def _record_entity_ref(route: str, pub: str) -> tuple[str, str] | None:
    """``r/<pub>/c/<comp>/entity/<type>/<id>`` (or its ``.json`` twin) →
    ``(entity_type, entity_id)`` for a denied route, else ``None``."""
    rel = route[: -len(".json")] if route.endswith(".json") else route
    parts = rel.split("/")
    if (
        len(parts) == 7
        and parts[0] == "r"
        and parts[1] == pub
        and parts[2] == "c"
        and parts[4] == "entity"
    ):
        return parts[5], parts[6]
    return None


def _entity_types(staged: Path, entity_id: str) -> set[str]:
    """Every entity ``<type>`` an id is staged under — the existing stub
    dirs plus the record routes of every activated release (so a denied
    entity's stub alias is covered even before the overlay emits it)."""
    types: set[str] = set()
    for d in (staged / "entity").glob(f"*/{entity_id}"):
        types.add(d.parent.name)
    r_root = staged / "r"
    if r_root.exists():
        for d in r_root.glob(f"*/c/*/entity/*/{entity_id}"):
            types.add(d.parent.name)
        for jf in r_root.glob(f"*/c/*/entity/*/{entity_id}.json"):
            types.add(jf.parent.name)
    return types


def _stub_tombstone(
    entity_type: str,
    entity_id: str,
    eff: DispositionRecord,
    *,
    release_label: str | None = None,
    stamp: Mapping[str, Any] | None = None,
) -> bytes:
    dec = access_decision(eff)
    return entity_stub_tombstone(
        entity_type=entity_type,
        entity_id=entity_id,
        reason_category=(
            dec.reason_category.value if dec.reason_category else "withheld_after_review"
        ),
        authority=str(dec.authority or "recorded disposition"),
        decided=_decided_iso(eff),
        policy_version=dec.policy_version,
        disposition_ref=_disposition_ref(eff),
        release_label=release_label,
        stamp=stamp,
    )


def _claim_route_index(staged: Path) -> dict[str, list[str]]:
    """claim_id → every record route asserting it (from the per-compartment
    indexes — a claim withdrawal denies the records carrying it, whole)."""
    out: dict[str, list[str]] = {}
    for idx in staged.glob("r/*/c/*/records.index.jsonl"):
        for row in _iter_jsonl(idx):
            # the directory route (drop the index.html leaf) + the .json route
            html_route = str(row["path"])
            dir_route = (
                html_route[: -len("index.html")].rstrip("/")
                if html_route.endswith("index.html")
                else html_route
            )
            for cid in row.get("claim_ids") or []:
                out.setdefault(str(cid), []).append(dir_route)
                out[str(cid)].append(str(row["json_path"]))
    return out


def _denied_pub_of(route: str) -> str | None:
    """The ``<pub>`` a denied route lives under (``r/``, ``releases/`` and
    the ``s/``/``v/`` snapshot namespaces all carry it at position 1)."""
    parts = route.split("/")
    return parts[1] if parts[0] in ("r", "releases", "s", "v") and len(parts) > 1 else None


def apply_withdrawals(
    staged: Path,
    records: Sequence[DispositionRecord],
    *,
    active_pub: str | None = None,
    stamp: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the CURRENT withdrawal registry to the staged public tree.

    One deny set drives everything (P34.41): for every route under a
    current denying disposition — page routes AND exact-path file routes —
    the artifact bytes are removed whole (immutable artifacts are denied,
    never rewritten), a ``sig.tombstone/1`` tombstone takes the route (the
    HTML index page on a page route, the JSON body on a ``.json`` file
    route), and ``conf/withdrawn_routes.conf`` carries a ``location =``
    deny for EVERY alias (``/<route>``, ``/<route>/``,
    ``/<route>/index.html``; ``/<route>`` for a file route) with
    ``error_page 410`` onto the staged ``conf/tombstone/<hash>`` body — so
    nginx answers 410 with the route's OWN tombstone, matched BEFORE any
    origin file or CDN access, never a generic 410 page (C4 NEW-14).

    ``active_pub`` scopes the ``/entity/<t>/<id>/`` convenience-stub deny:
    the stubs are mutable pointers at the ACTIVE release's records, so a
    stub denies when its entity is under an entity-level disposition OR
    its record route under ``active_pub`` is denied (claim, artifact or
    release deny). The map covers a denied stub predictively — even before
    the activation overlay emits its page.

    ``stamp`` (P35.13 / SIG-REL-009) is the active release's §6.1
    provenance view — the tombstone pages it rewrites still answer for a
    release, so they carry its stamp like every other mutable page;
    ``None`` (no current release, or a caller outside activation) leaves
    them honestly unstamped.
    """
    records = list(records)
    by_target: dict[tuple[str, str], list[DispositionRecord]] = {}
    for r in records:
        by_target.setdefault((r.target_kind.value, r.target_id), []).append(r)

    def _eff(kind: str, tid: str) -> DispositionRecord | None:
        eff = latest_disposition(by_target.get((kind, tid), []))
        if eff is not None and not access_decision(eff).permitted:
            return eff
        return None

    claim_index = _claim_route_index(staged)
    # route → the effective denying record (drives the tombstone's safe
    # fields): page routes vs exact-path file routes are kept apart so the
    # map emits each shape's alias set.
    denied: dict[str, DispositionRecord] = {}
    denied_files: dict[str, DispositionRecord] = {}

    def _deny(target_kind: str, target_id: str, route: str, shape: str) -> None:
        eff = _eff(target_kind, target_id)
        if eff is not None:
            (denied_files if shape == "file" else denied).setdefault(route, eff)

    stub_targets: list[tuple[str, str]] = []
    for kind, tid, rel, shape in _route_targets(staged):
        if kind == "entity_stub":
            stub_targets.append((tid, rel))
            continue
        if kind == "release":
            _deny(TargetKind.RELEASE_ARTIFACT.value, tid, rel, shape)
            continue
        _deny(kind, tid, rel, shape)

    # claim-level withdrawals deny every record route asserting the claim
    for (kind, tid), _rs in by_target.items():
        if kind != TargetKind.CLAIM.value:
            continue
        eff = _eff(kind, tid)
        if eff is None:
            continue
        for route in claim_index.get(tid, []):
            (denied_files if route.endswith(".json") else denied).setdefault(route, eff)

    # release-level withdrawal denies everything under the namespaces
    for (kind, tid), _rs in by_target.items():
        if kind != TargetKind.RELEASE_ARTIFACT.value:
            continue
        eff = _eff(kind, tid)
        if eff is None:
            continue
        for base in (f"r/{tid}", f"releases/{tid}", f"s/{tid}", f"v/{tid}"):
            for path in staged.glob(f"{base}/**/*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(staged).as_posix()
                if rel.endswith("index.html"):
                    # a page route is its directory — the tombstone page
                    # takes the route, not a JSON body over the HTML file
                    denied.setdefault(rel[: -len("index.html")].rstrip("/"), eff)
                else:
                    denied_files.setdefault(rel, eff)
        # the namespace roots deny even when the glob found no files (a
        # pre-P34.41 staged tree has no r/<pub>/index.html — the root must
        # still tombstone, never 403).
        denied.setdefault(f"r/{tid}", eff)
        denied.setdefault(f"releases/{tid}", eff)

    # --- entity stubs: generated FROM the deny set ------------------------ #
    # A stub denies when (a) its entity is under an entity-level deny —
    # covering every stub the tree carries plus each type the entity is
    # staged under, predictively — or (b) the ACTIVE release's own record
    # route for the entity is denied (the stub points at denied bytes).
    stub_denies: dict[str, DispositionRecord] = {}
    for tid, rel in stub_targets:
        eff = _eff(TargetKind.ENTITY.value, tid)
        if eff is not None:
            stub_denies[rel] = eff
    for (kind, tid), _rs in by_target.items():
        if kind != TargetKind.ENTITY.value:
            continue
        eff = _eff(kind, tid)
        if eff is None:
            continue
        for etype in sorted(_entity_types(staged, tid)):
            stub_denies.setdefault(f"entity/{etype}/{tid}", eff)
    if active_pub:
        for route, eff in list(denied.items()) + list(denied_files.items()):
            ref = _record_entity_ref(route, active_pub)
            if ref is not None:
                stub_denies.setdefault(f"entity/{ref[0]}/{ref[1]}", eff)
    for route, eff in stub_denies.items():
        denied.setdefault(route, eff)

    # --- page_index coverage ---------------------------------------------- #
    # A page_index.json page that embeds a denied target id is denied whole
    # — the route answers its tombstone — and the staged index entry is
    # marked withdrawn in place (the "show the tombstone" half of the
    # contract: the listing names the deny, never a silently stale entry).
    denied_ids: dict[str, DispositionRecord] = {}
    for (kind, tid), _rs in by_target.items():
        if kind not in (
            TargetKind.ENTITY.value,
            TargetKind.CLAIM.value,
            TargetKind.ARTIFACT.value,
        ):
            continue
        eff = _eff(kind, tid)
        if eff is not None:
            denied_ids[tid] = eff
    if denied_ids:
        for idx_path in sorted(staged.rglob("page_index.json")):
            if not idx_path.is_file():
                continue
            doc = _read_json(idx_path)
            pages = doc.get("pages") if isinstance(doc, dict) else None
            if not isinstance(pages, list):
                continue
            changed = False
            for entry in pages:
                if not isinstance(entry, dict):
                    continue
                embedded = {
                    str(v)
                    for key in (
                        "entity_ids",
                        "claim_ids",
                        "artifact_ids",
                        "entities",
                        "claims",
                        "artifacts",
                    )
                    for v in (entry.get(key) or [])
                }
                hit = next((tid for tid in sorted(embedded) if tid in denied_ids), None)
                if hit is None:
                    continue
                eff = denied_ids[hit]
                route = str(entry.get("route") or "").strip("/")
                if route:
                    if "." in route.rsplit("/", 1)[-1]:
                        denied_files.setdefault(route, eff)
                    else:
                        denied.setdefault(route, eff)
                if not entry.get("withdrawn"):
                    entry["withdrawn"] = True
                    entry["withdrawal_reason"] = eff.reason_category.value
                    changed = True
            if changed:
                # the staged index may be a hardlink to release bytes —
                # break the link before annotating (P32.25/ADR-144)
                if os.stat(idx_path).st_nlink > 1:
                    data = idx_path.read_bytes()
                    idx_path.unlink()
                    idx_path.write_bytes(data)
                _atomic_write(idx_path, canonical_json(doc))

    # The release label for a denied route — read the catalog entries
    # BEFORE any tombstone lands (a withdrawn release's own catalog_entry
    # is itself denied).
    pub_labels: dict[str, str] = {}
    rel_root = staged / "releases"
    if rel_root.exists():
        for ce in sorted(rel_root.glob("*/catalog_entry.json")):
            label = ce.parent.name
            try:
                doc = _read_json(ce)
                if isinstance(doc, dict) and doc.get("data_release_id"):
                    label = str(doc["data_release_id"])
            except (OSError, ValueError):
                pass
            pub_labels[ce.parent.name] = label

    def _label_for(route: str) -> str | None:
        pub = _denied_pub_of(route) or (active_pub if route.startswith("entity/") else None)
        return pub_labels.get(pub) if pub else None

    # materialise tombstones + remove denied bytes (whole-deny only)
    for route in sorted(denied):
        path = staged / route
        eff = denied[route]
        dec = access_decision(eff)
        if path.exists() and not path.is_dir():
            # a normalized page route that arrived as a file (never expected —
            # remove the denied bytes whole, then take the route)
            path.unlink()
        if path.is_dir():
            for child in list(path.iterdir()):
                if child.name == "index.html":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            # break the hardlink to the immutable release bytes before the
            # tombstone page takes the route (P32.25/ADR-144)
            index = path / "index.html"
            if index.exists() and index.is_file() and os.stat(index).st_nlink > 1:
                index.unlink()
        if route.startswith("entity/") and route.count("/") == 2:
            # the /entity/<t>/<id>/ convenience stub — the stub-shaped
            # tombstone, generated from the deny set like the map line.
            etype, _, eid = route.partition("/")[2].partition("/")
            page = _stub_tombstone(etype, eid, eff, release_label=_label_for(route), stamp=stamp)
        else:
            page = tombstone_page(
                path="/" + route + "/",
                reason_category=(
                    dec.reason_category.value if dec.reason_category else "withheld_after_review"
                ),
                authority=str(dec.authority or "recorded disposition"),
                decided=_decided_iso(eff),
                policy_version=dec.policy_version,
                target_kind=eff.target_kind.value,
                target_id=eff.target_id,
                disposition_ref=_disposition_ref(eff),
                release_label=_label_for(route),
                stamp=stamp,
            )
        _write(path / "index.html", page)

    for route in sorted(denied_files):
        path = staged / route
        eff = denied_files[route]
        # staged artifacts are hardlinks to the release dir — break the
        # link before writing so the immutable release input can never be
        # mutated by a tombstone write (P32.25/ADR-144)
        if path.exists() and not path.is_dir() and os.stat(path).st_nlink > 1:
            path.unlink()
        if route.endswith(".json"):
            _write(
                path,
                canonical_json(_tombstone_doc(eff, route, release_label=_label_for(route))),
            )
        else:
            # artifact bytes denied whole — the conf deny answers the route
            # (a deleted file without its deny line would answer 404).
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    # -- the deny map: every alias of every denied route ------------------- #
    tomb_dir = staged / TOMBSTONE_BODY_DIR
    if tomb_dir.exists():
        shutil.rmtree(tomb_dir)
    alias_map: dict[str, str] = {}
    for route in sorted(denied):
        body = "/" + _tombstone_body_rel(route, "html")
        _write(
            staged / _tombstone_body_rel(route, "html"),
            (staged / route / "index.html").read_bytes(),
        )
        for alias in (f"/{route}", f"/{route}/", f"/{route}/index.html"):
            alias_map[alias] = body
    for route in sorted(denied_files):
        body = "/" + _tombstone_body_rel(route, "json")
        _write(
            staged / _tombstone_body_rel(route, "json"),
            canonical_json(
                _tombstone_doc(denied_files[route], route, release_label=_label_for(route))
            ),
        )
        alias_map[f"/{route}"] = body
    conf = staged / "conf" / "withdrawn_routes.conf"
    lines = [
        "# Generated by the SIG release tooling — withdrawn release routes (P34.41).",
        "# location = exact matches evaluate BEFORE the /r/ prefix location, so a",
        "# withdrawal denies before any origin file or CDN access (ADR-132). Every",
        "# alias of a denied route — the no-slash form, the trailing-slash form",
        "# and /index.html for a page route; the exact path for a file route —",
        "# answers 410 with that route's own sig.tombstone/1 body: error_page",
        "# internal-redirects to the staged conf/tombstone/ body (the prefix is",
        "# `internal` in nginx.conf), never a generic nginx 410 (C4 NEW-14).",
    ]
    for alias, body in sorted(alias_map.items()):
        if not _CONF_URI_SAFE.match(alias):
            raise ReleaseError(
                f"withdrawn route {alias!r} is not URI-safe — refusing to "
                "emit a deny line that would corrupt the generated conf"
            )
        lines.append(f"location = {alias} {{ error_page 410 {body}; return 410; }}")
    _write(conf, ("\n".join(lines) + "\n").encode("utf-8"))
    return {
        "denied": len(denied) + len(denied_files),
        "routes": sorted(set(denied) | set(denied_files)),
        "entity_stubs": stub_denies,
    }


def _apply_summary(applied: Mapping[str, Any]) -> dict[str, Any]:
    """The JSON-safe receipt view of an :func:`apply_withdrawals` report —
    ``entity_stubs`` is the internal route→disposition map the overlay
    consumes; receipts and the CLI carry the sorted route list."""
    out = dict(applied)
    stubs = applied.get("entity_stubs") or {}
    out["entity_stubs"] = sorted(stubs) if isinstance(stubs, Mapping) else stubs
    return out


def _norm_route(route: str) -> str:
    """Canonical deny-map form of a queried route: strip the slashes and
    fold the ``/index.html`` alias onto its page route."""
    norm = route.strip("/")
    if norm.endswith("/index.html"):
        norm = norm[: -len("index.html")].rstrip("/")
    return norm


def route_access(registry_dir: Path | str, route: str) -> dict[str, Any]:
    """The serving barrier's pure check: may ``route`` be publicly served
    under the CURRENT withdrawal registry? Returns the decision + the
    public-safe tombstone payload for a denial.

    P34.41: the ``/entity/<type>/<id>/`` convenience stubs are covered too
    — a stub is denied when its entity is under an entity-level deny, when
    the latest release's own namespace is denied, or when a denied claim
    binds the record route the stub points at (the same rule the generated
    deny map encodes)."""
    registry = ReleaseRegistry(Path(registry_dir))
    records = registry.withdrawals()
    norm = _norm_route(route)
    parts = norm.split("/")
    kind = None
    target = None
    if len(parts) >= 2 and parts[0] == "r":
        if "entity" in parts:
            kind = TargetKind.ENTITY
            target = parts[parts.index("entity") + 2].removesuffix(".json")
        elif "evidence" in parts:
            kind = TargetKind.ARTIFACT
            target = parts[parts.index("evidence") + 1].removesuffix("/")
        else:
            kind = TargetKind.RELEASE_ARTIFACT
            target = parts[1]
    elif len(parts) >= 2 and parts[0] == "releases":
        kind = TargetKind.RELEASE_ARTIFACT
        target = parts[1]
    elif len(parts) >= 3 and parts[0] == "entity":
        # the /entity/<type>/<id>/ convenience alias
        kind = TargetKind.ENTITY
        target = parts[2].removesuffix(".json")
    # A route under a withdrawn release namespace is denied even when the
    # route's own target has no disposition — the namespace deny dominates.
    # The entity stub follows the release its pointer names (the current
    # latest): a denied latest namespace denies its stubs. The ``s/``/``v/``
    # snapshot namespaces and the ``releases/`` landings carry the pub at the
    # same position — a release deny dominates them too, exactly as the deny
    # map's glob does.
    ns_pub = None
    if len(parts) >= 2 and parts[0] in ("r", "releases", "s", "v"):
        ns_pub = parts[1]
    elif parts[0] == "entity":
        ns_pub = (registry.latest() or {}).get("publication_id")
    if ns_pub:
        eff_release = latest_disposition(
            [
                r
                for r in records
                if r.target_kind == TargetKind.RELEASE_ARTIFACT and r.target_id == ns_pub
            ]
        )
        dec_release = access_decision(eff_release)
        if not dec_release.permitted:
            return {"permitted": False, "tombstone": dec_release.tombstone()}
    if kind is None or target is None:
        return {"permitted": True, "tombstone": None}
    eff = latest_disposition(
        [r for r in records if r.target_kind == kind and r.target_id == target]
    )
    dec = access_decision(eff)
    if not dec.permitted:
        return {"permitted": False, "tombstone": dec.tombstone()}
    # A record route carrying a currently-denied CLAIM is denied too — the
    # staged claim index (when present) is the carrier of that binding.
    staged = registry.root / "staged"
    if staged.exists() and any(r.target_kind == TargetKind.CLAIM for r in records):
        idx = _claim_route_index(staged)
        by_claim: dict[str, list[DispositionRecord]] = {}
        for r in records:
            if r.target_kind == TargetKind.CLAIM:
                by_claim.setdefault(r.target_id, []).append(r)
        for tid, rs in by_claim.items():
            eff_c = latest_disposition(rs)
            if eff_c is None or access_decision(eff_c).permitted:
                continue
            bound = {_norm_route(rt) for rt in idx.get(tid, [])}
            if norm in bound:
                return {
                    "permitted": False,
                    "tombstone": access_decision(eff_c).tombstone(),
                }
            if parts[0] == "entity" and ns_pub:
                # the stub denies when the record route it would point at
                # (under the ACTIVE release) is claim-denied.
                suffix = f"/entity/{parts[1]}/{target}"
                if any(
                    rt.startswith(f"r/{ns_pub}/c/") and rt.removesuffix(".json").endswith(suffix)
                    for rt in bound
                ):
                    return {
                        "permitted": False,
                        "tombstone": access_decision(eff_c).tombstone(),
                    }
    return {"permitted": dec.permitted, "tombstone": dec.tombstone()}


# --------------------------------------------------------------------------- #
# Legacy historical-selector resolution                                        #
# --------------------------------------------------------------------------- #

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def _normalise_selector(value: str) -> str | None:
    """Strict historical-selector parse — a date or an ISO instant both
    normalise to the UTC date the export semantics used. Anything else is an
    invalid selector (never silently current)."""
    value = value.strip()
    if _DATE_RE.match(value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            return None
    if _INSTANT_RE.match(value):
        try:
            dt = datetime.fromisoformat(value.replace(" ", "T"))
            return dt.date().isoformat()
        except ValueError:
            return None
    return None


def resolve_selector(
    registry_dir: Path | str,
    *,
    as_of_world: str | None,
    as_of_belief: str | None,
    ruleset: str | None,
    path: str | None = None,
) -> dict[str, Any]:
    """Resolve a legacy ``?as_of_world=&as_of_belief=&ruleset=`` selector to a
    REAL activated release — or an honest failure.

    * malformed selector → ``{"status": "invalid"}`` (400);
    * no activated release matches → ``{"status": "unavailable"}`` (404);
    * more than one → ``{"status": "ambiguous", "candidates": [...]}`` (409);
    * exactly one → ``{"status": "redirect", "publication_id": …}`` — the
      immutable namespace the selector actually names (a 302 to the release
      landing, or to the mapped record when ``path`` addresses one);
    * no selectors at all → ``{"status": "current"}`` (the latest pointer —
      a convenience answer, never a citation).
    """
    registry = ReleaseRegistry(Path(registry_dir))
    if as_of_world is None and as_of_belief is None and ruleset is None:
        latest = registry.latest() or {}
        return {"status": "current", "publication_id": latest.get("publication_id")}

    norm_w = _normalise_selector(as_of_world) if as_of_world is not None else None
    if as_of_world is not None and norm_w is None:
        return {"status": "invalid", "detail": f"as_of_world {as_of_world!r} is not a date"}
    norm_b = _normalise_selector(as_of_belief) if as_of_belief is not None else None
    if as_of_belief is not None and norm_b is None:
        return {"status": "invalid", "detail": f"as_of_belief {as_of_belief!r} is not a date"}

    matches = []
    for e in registry.compat().get("entries") or []:
        if norm_w is not None and e.get("as_of_world") != norm_w:
            continue
        if norm_b is not None and e.get("as_of_belief") != norm_b:
            continue
        if ruleset is not None and e.get("ruleset_version") != ruleset:
            continue
        matches.append(str(e.get("publication_id")))
    if not matches:
        return {
            "status": "unavailable",
            "detail": "no activated release covers that selector — "
            "SIG never substitutes a different cut and labels it historical",
        }
    if len(matches) > 1:
        return {"status": "ambiguous", "candidates": sorted(matches)}
    pub = matches[0]
    out: dict[str, Any] = {"status": "redirect", "publication_id": pub, "href": f"/releases/{pub}/"}
    if path:
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "entity":
            # map the convenience entity URL to the released record route —
            # existence checked against the release index (no masquerade)
            et, eid = parts[1], parts[2].removesuffix(".json")
            idx = registry.root / "staged" / "r" / pub / "c"
            hit = None
            if idx.exists():
                for comp_dir in sorted(idx.iterdir()):
                    rec = comp_dir / "entity" / et / f"{eid}.json"
                    if rec.exists():
                        hit = f"/r/{pub}/c/{comp_dir.name}/entity/{et}/{eid}" + (
                            ".json" if parts[2].endswith(".json") else "/"
                        )
                        break
            if hit is None:
                out = {
                    "status": "unavailable",
                    "publication_id": pub,
                    "detail": f"record {et}/{eid} is not in release {pub}",
                }
            else:
                out["href"] = hit
    return out


# --------------------------------------------------------------------------- #
# Measured generation report                                                   #
# --------------------------------------------------------------------------- #


def measure_build(
    export_dir: Path | str,
    out_dir: Path | str,
    *,
    renderer_revision: str,
) -> dict[str, Any]:
    """Build a release and MEASURE it — the representative-scale cost report
    the ticket demands before any rollout: wall time, peak RSS, file count,
    bytes, per-compartment record counts."""
    import resource

    t0 = time.monotonic()
    build = build_release(export_dir, out_dir, renderer_revision=renderer_revision)
    elapsed = time.monotonic() - t0
    out = Path(out_dir)
    files = 0
    total_bytes = 0
    for p in out.rglob("*"):
        if p.is_file():
            files += 1
            total_bytes += p.stat().st_size
    report = {
        "schema": "sig.release-generation-measurement/1",
        "publication_id": build.publication_id,
        "manifest_sha256": build.manifest_sha256,
        "export_dir": str(export_dir),
        "records": build.report["records"],
        "files": files,
        "bytes": total_bytes,
        "wall_seconds": round(elapsed, 3),
        # ru_maxrss is BYTES on macOS, KiB on Linux — normalise to bytes so the
        # report means the same thing on either host.
        "peak_rss_bytes": (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin"
            else resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        ),
        "compartments": build.report["compartments"],
        "measured_at": datetime.now(UTC).isoformat(),
    }
    _write(out / "release/generation_measurement.json", canonical_json(report))
    return report
