# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.68 / R11-K13-UX9-4 (K9 §7.2, SIG-TRANSP-032) — the per-source version
index ``r/<pub>/transparency/sources/<id>/versions.json``
(``sig.source-versions/1``).

One entry per activated release containing the source — release label +
publication id, ``as_of_world``, rows (sites), claims (statements), files
(name, format, bytes, sha256, mirror URL) and, vs the previous entry,
``added / removed / changed`` record counts from the TX-14 id-level diff
filtered by source (P36.67's ``release_changes`` machinery) plus a
``changed`` flag.

Append-only across releases (K9 §7.3): a release whose predecessor already
carried a ``versions.json`` inherits its entries verbatim and appends its
own — the index is a superset of the previous one, never rewritten. Prior
(pre-version-index) releases appear as **manifest-only** entries
(``state: "manifest_only"`` — counts + sha256 as the previous release's own
integrity manifest and source row record them, "not republished — reason",
D-K9-2 [B-22] = a; a missing extract shows its manifest record, never a
fabricated download).

A published source with no emitted ``by-source/<id>/`` files records the
honest ``extract_absent`` state — SIG-TRANSP-032 requires the extract, so
its absence is named, never smoothed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .release_changes import _read_record, _record_source_ids, load_record_index

#: The version-index document schema.
SOURCE_VERSIONS_SCHEMA = "sig.source-versions/1"

#: The D-K9-2 [B-22] = a reason a manifest-only entry states, verbatim-ish:
#: prior releases are not republished — the entry reconstructs from the
#: previous release's own manifest + source row, never re-derived bytes
#: (the restricted snapshots carry NEW-1 rows and wrong attribution).
MANIFEST_ONLY_REASON = (
    "release predates the version index — the entry is reconstructed from "
    "the previous release's own integrity manifest and source row, never "
    "re-derived bytes (D-K9-2 = a: manifest-only entries; the restricted "
    "snapshots carry NEW-1 rows and wrong attribution)"
)

VERSIONS_GLOB = "transparency/sources/{source_id}/versions.json"


# --------------------------------------------------------------------------- #
# The per-source slice files (from the download listing — the export's own
# bytes, never a parallel derivation)
# --------------------------------------------------------------------------- #


def slice_files_from_listing(
    listing: Mapping[str, Any] | None,
    source_id: str,
) -> list[dict[str, Any]]:
    """The ``by-source/<id>/`` file rows the download listing recorded —
    name, format, bytes, sha256 and the content-hash mirror href."""
    out: list[dict[str, Any]] = []
    for f in (listing or {}).get("files") or []:
        if not isinstance(f, Mapping):
            continue
        if str(f.get("source_id") or "") != source_id:
            continue
        out.append(
            {
                "path": str(f.get("path") or ""),
                "name": str(f.get("name") or ""),
                "format": str(f.get("format") or ""),
                "bytes": int(f.get("byte_size") or 0),
                "sha256": str(f.get("sha256") or ""),
                "href": str(f.get("href") or ""),
                **({"rows": int(f["row_count"])} if f.get("row_count") is not None else {}),
            }
        )
    out.sort(key=lambda r: str(r["path"]))
    return out


def _slice_rows(files: list[dict[str, Any]]) -> dict[str, int | None]:
    """The sites/statements row counts the file list carries."""
    rows: dict[str, int | None] = {"sites": None, "statements": None}
    for f in files:
        name = str(f.get("name") or "")
        if name == "sites.csv.gz":
            rows["sites"] = int(f.get("rows") or 0)
        elif name == "statements.jsonl.gz":
            rows["statements"] = int(f.get("rows") or 0)
    return rows


# --------------------------------------------------------------------------- #
# The per-source TX-14 diff filter
# --------------------------------------------------------------------------- #


def _docs_sources(root: Path | None, index: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    """``record_key → source ids`` over one release's record index."""
    out: dict[str, frozenset[str]] = {}
    if root is None:
        return out
    for _comp, rows in index.items():
        for key, row in rows.items():
            doc = _read_record(root, row)
            out[key] = frozenset(_record_source_ids(doc))
    return out


def per_source_diff_counts(
    diff: Mapping[str, Any],
    *,
    cur_root: Path | None,
    cur_pub: str | None,
    prev_root: Path | None = None,
    prev_pub: str | None = None,
) -> dict[str, dict[str, int]]:
    """The added/removed/changed record counts per source id — TX-14's
    id-level diff filtered by the sources each named record carries.

    Added/changed rows resolve source ids on the CURRENT record doc;
    removed rows on the previous one (its doc no longer exists in the
    current tree). Records naming no source contribute nothing — the count
    never fabricates an attribution.
    """
    cur_index = load_record_index(cur_root, cur_pub) if cur_root and cur_pub else {}
    prev_index = load_record_index(prev_root, prev_pub) if prev_root and prev_pub else {}
    cur_src = _docs_sources(cur_root, cur_index)
    prev_src = _docs_sources(prev_root, prev_index)
    counts: dict[str, dict[str, int]] = {}

    def bump(sid: str, cls: str) -> None:
        cell = counts.setdefault(sid, {"added": 0, "removed": 0, "changed": 0})
        cell[cls] += 1

    for _comp, cell in diff.items():
        for row in cell.get("added") or []:
            for sid in cur_src.get(str(row.get("record_key") or ""), ()):
                bump(sid, "added")
        for row in cell.get("removed") or []:
            for sid in prev_src.get(str(row.get("record_key") or ""), ()):
                bump(sid, "removed")
        for row in cell.get("changed") or []:
            key = str(row.get("record_key") or "")
            for sid in cur_src.get(key) or prev_src.get(key) or ():
                bump(sid, "changed")
    return counts


# --------------------------------------------------------------------------- #
# Entries
# --------------------------------------------------------------------------- #


def release_block(descriptor: Mapping[str, Any] | None, pub: str | None) -> dict[str, Any]:
    """The release identity block a version entry records — the descriptor's
    own label/publication/as-of pair (never re-derived)."""
    d = descriptor or {}
    snap = d.get("snapshot") or {}
    return {
        "label": d.get("label"),
        "publication_id": pub,
        "as_of_world": snap.get("as_of_world") or d.get("as_of_world"),
        "as_of_belief": snap.get("as_of_belief") or d.get("as_of_belief"),
    }


def published_claims_of(source_row: Mapping[str, Any] | None) -> int | None:
    """The source row's published-claims count, when it records one."""
    v = (source_row or {}).get("published_claims")
    return int(v) if isinstance(v, int) else None


def version_entry(
    source_id: str,
    *,
    release: Mapping[str, Any],
    files: list[dict[str, Any]],
    diff_counts: Mapping[str, int] | None,
    baseline: bool,
    previous_slice_sha: str | None = None,
    published_claims: int | None = None,
) -> dict[str, Any]:
    """One release's version entry for a source.

    ``changed`` is the slice-digest/content rule of K9 §7.2/§10: the
    statements slice's sha256 differs from the previous entry's, or the
    id-level diff names records for the source; a baseline release is
    always a change. ``files: []`` names the honest ``extract_absent``
    state — a published source whose slice was never emitted.
    """
    counts = dict(diff_counts or {"added": 0, "removed": 0, "changed": 0})
    diff_nonzero = any(counts.values())
    statements_sha = next(
        (str(f["sha256"]) for f in files if f.get("name") == "statements.jsonl.gz"),
        None,
    )
    if baseline:
        changed = True
        diff_state = "baseline"
    elif diff_counts is None:
        changed = statements_sha is not None and statements_sha != previous_slice_sha
        diff_state = "not_evaluable"
    else:
        changed = diff_nonzero or (
            statements_sha is not None and statements_sha != previous_slice_sha
        )
        diff_state = "evaluated"
    entry: dict[str, Any] = {
        "release": dict(release),
        "state": "extract" if files else "extract_absent",
        "rows": _slice_rows(files),
        "published_claims": published_claims,
        "files": files,
        "diff": {
            "state": diff_state,
            "added": int(counts.get("added") or 0),
            "removed": int(counts.get("removed") or 0),
            "changed": int(counts.get("changed") or 0),
        },
        "changed": bool(changed),
        "slice_sha256": statements_sha,
    }
    if not files:
        entry["absence"] = (
            "no by-source/<id>/ extract was emitted for this release — a "
            "published source always carries the statements slice (K9 C-8), "
            "so this absence is named, never smoothed (SIG-TRANSP-032)"
        )
    return entry


def manifest_only_entry(
    source_id: str,
    *,
    release: Mapping[str, Any],
    manifest_files: list[dict[str, Any]],
    published_claims: int | None = None,
) -> dict[str, Any]:
    """The manifest-only entry a pre-version-index release records
    (D-K9-2 = a): counts + sha256 as that release's own integrity manifest
    and source row state them, ``not_republished`` — the objects are never
    re-pushed or re-derived under the new release."""
    rows = _slice_rows(manifest_files)
    return {
        "release": dict(release),
        "state": "manifest_only",
        "extract": "not_republished",
        "reason": MANIFEST_ONLY_REASON,
        "rows": rows,
        "published_claims": published_claims,
        "files": manifest_files,
        "changed": None,
    }


def manifest_files_from_integrity(
    integrity: Mapping[str, Any] | None, source_id: str
) -> list[dict[str, Any]]:
    """The ``by-source/<id>/`` artifact rows an integrity manifest records —
    path, sha256, bytes (the manifest's own counts, never re-derived)."""
    out: list[dict[str, Any]] = []
    for a in (integrity or {}).get("artifacts") or []:
        path = str(a.get("path") or "")
        if not path.startswith(f"by-source/{source_id}/"):
            continue
        out.append(
            {
                "path": path,
                "name": path.rsplit("/", 1)[-1],
                "sha256": str(a.get("sha256") or ""),
                "bytes": int(a.get("byte_size") or a.get("bytes") or 0),
            }
        )
    out.sort(key=lambda r: str(r["path"]))
    return out


# --------------------------------------------------------------------------- #
# Prior entries — the append-only superset
# --------------------------------------------------------------------------- #


def load_previous_versions(
    prev_root: Path | None, prev_pub: str | None, source_id: str
) -> list[dict[str, Any]] | None:
    """The previous release's versions.json entries for the source —
    ``None`` when the tree carried no version index (the manifest-only
    case); the inherited list otherwise (a superset by construction)."""
    if prev_root is None or prev_pub is None:
        return None
    path = (
        Path(prev_root) / "r" / prev_pub / "transparency" / "sources" / source_id / "versions.json"
    )
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or doc.get("schema") != SOURCE_VERSIONS_SCHEMA:
        return None
    entries = doc.get("entries")
    return list(entries) if isinstance(entries, list) else None


def versions_document(
    source_id: str,
    entries: list[dict[str, Any]],
    *,
    name: str | None = None,
) -> dict[str, Any]:
    """The ``sig.source-versions/1`` document — entries oldest → newest,
    append-only (each release's doc is a superset of its predecessor's)."""
    disclosures = [
        "Latest released data — never 'the latest run's data': runs land on "
        "the spine between releases without passing the release gates; their "
        "data appears in the next release (K9 §7.2).",
        "Unchanged slices share one content hash across entries — a new "
        "entry pointing at the same object adds zero bytes on the mirror.",
    ]
    return {
        "schema": SOURCE_VERSIONS_SCHEMA,
        "source_id": source_id,
        "name": name or source_id,
        "entries": entries,
        "entry_count": len(entries),
        "disclosures": disclosures,
    }


__all__ = [
    "MANIFEST_ONLY_REASON",
    "SOURCE_VERSIONS_SCHEMA",
    "VERSIONS_GLOB",
    "load_previous_versions",
    "published_claims_of",
    "release_block",
    "manifest_files_from_integrity",
    "manifest_only_entry",
    "per_source_diff_counts",
    "slice_files_from_listing",
    "version_entry",
    "versions_document",
]
