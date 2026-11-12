# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.67 / SIG-TRANSP-024 + SIG-UI-087 (K13 TX-14, J3 §8.4) — the per-release
id-level diff, the human changelog, and the ``/v1/changes`` release backing.

Each release publishes a **record-id-keyed diff against the previous
activated release** under ``r/<pub>/transparency/changes/`` plus a human
``releases/<pub>/CHANGELOG.md``. The diff is a build-time input: the builder
names the previous release's tree (a built release dir, a registry
``staged/`` root, or a registry root — the current pointer resolves the
previous publication), so every changes byte is manifest-pinned and
reproducible — same export + same previous ⇒ byte-identical diff.

What the diff compares (J3 §8.4's contract):

* ``added.parquet`` / ``removed.parquet`` / ``changed.parquet`` per
  compartment, keyed on ``record_key`` — never on row position;
* ``removed`` rows carry a closed reason class — ``withdrawn`` (a presented
  disposition denies the record), ``superseded`` (the entity survives under
  a different record key), ``source_withdrawn`` (every source the record
  carried is absent from the current release's source universe) —
  defaulting to ``no_longer_published``, each with its ``reason_basis``;
* ``changed`` rows name their changed columns over a declared compared-field
  set — **sources and confidence are never compared** (the Overture GERS
  lesson: claim/statements re-mints are renderer churn, not world change);
  claim anchors are compared as an id set only, and the doc discloses that
  claim ids are not yet stable (SIG-CONF-003 unlanded — a claim-id diff may
  reflect re-minting, the k13 row's disclosed-noise clause);
* ``sources.json`` — the per-source four-class diff (added / retired /
  newly_failing / lane_changed) from the two exports' ``sig.source-row/1``
  sets; a source input never presented to the build renders the honest
  ``not_evaluable`` absence, never a fabricated verdict;
* ``changes.json`` — the ``sig.release-changes-feed/1`` document
  ``/v1/changes`` serves (field-level events carrying ``new_date`` so the
  route's ``since`` filter applies unchanged);
* ``index.json`` — the ``sig.release-changes/1`` summary: identities,
  per-compartment counts, the compared/excluded field declaration, the
  versions diff and the file manifest;
* ``releases/<pub>/CHANGELOG.md`` — the human changelog (sources, counts,
  schema/ontology/ruleset versions, deprecations with dates).

The first release is the baseline: ``previous: null`` and every record is
``added`` — never a fabricated "no previous" placeholder (J3 §8.4).

SIG-UI-087's half also lives here: ``LIVE_CLOCK_MARKERS`` is the closed
vocabulary of values that depend on the reader's current time (status-lane
markers, next-run phrasing, relative-time values) — a release page
(``r/<pub>/**.html``, ``releases/<pub>/**.html``) carrying one fails the
build and re-validation (``live_clock_page_failures``); those values belong
only under ``/status/**`` labelled with the status clock.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from .formats import write_parquet
from .manifest import canonical_json, sha256_hex

#: The wire schema of ``transparency/changes/index.json`` (J3 §3.2).
CHANGES_SCHEMA = "sig.release-changes/1"
#: The wire schema of ``transparency/changes/sources.json``.
SOURCE_CHANGES_SCHEMA = "sig.release-source-changes/1"
#: The wire schema of ``transparency/changes/changes.json`` — the
#: ``/v1/changes`` backing document.
CHANGES_FEED_SCHEMA = "sig.release-changes-feed/1"

#: The release-relative path of the feed document the API serves.
CHANGES_FEED_REL_SUFFIX = "transparency/changes/changes.json"

#: The record fields the "changed" comparison reads — the record's own
#: facts. ``claim_anchors`` compares as an id+locator+access_kind set only.
COMPARED_FIELDS: tuple[str, ...] = (
    "claim_anchors",
    "coverage",
    "dedup",
    "inferred",
    "label",
    "layer",
    "jurisdiction",
    "location",
    "review",
    "technology",
)
#: The record fields never compared — J3 §8.4's "sources/confidence not
#: compared" plus the projection ``schema`` (a renderer version, not a
#: record fact; a projection bump is recorded in the changelog's versions
#: block, not as per-record churn).
EXCLUDED_FIELDS: tuple[str, ...] = (
    "schema",
    "source_refs",
    "claim_statements",
    "evidence_refs",
)
#: The bound-namespace fields stripped before any comparison — they differ
#: between releases by construction and are never record facts.
_BOUND_FIELDS: tuple[str, ...] = ("publication_id", "href", "json_href", "release", "licence")

#: The closed removal-reason vocabulary (J3 §8.4).
REMOVED_REASONS: tuple[str, ...] = (
    "withdrawn",
    "superseded",
    "source_withdrawn",
    "no_longer_published",
)

#: ``lifecycle_state`` transitions INTO these classes count as the source
#: losing its published footing — J3 §8.4's "newly failing" over the
#: published ``sig.source-row/1`` partition.
_FAILING_LIFECYCLE: frozenset[str] = frozenset(
    {"ingested_not_published", "gated", "refused", "withdrawn"}
)

#: The feed document bounds its events list at this count — the full
#: record-level diff always lives in the parquet files; a truncated feed
#: says so and names the total (SIG-ENG-042, never a smoothed count).
FEED_EVENT_CAP = 5000

#: SIG-UI-087 — the closed vocabulary of values that depend on the reader's
#: current time. A release page carrying one fails: these belong only under
#: ``/status/**`` labelled with the status clock. Compiled once; the scan is
#: case-insensitive over emitted HTML bytes.
_LIVE_CLOCK_NEEDLES: tuple[str, ...] = (
    "status_time",
    "status-lane",
    "sig.status-lane",
    "sig.status-heartbeat",
    "status heartbeat",
    "heartbeat_interval",
    "next run",
    "next scheduled",
    "scheduled next",
    "freshness verdict",
    "current verdict",
    "currently failing",
    "as of now",
    "just now",
)
_LIVE_CLOCK_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # relative-time values the release page could only compute at read
        # time — "3 days ago", "in 2 hours"
        r"\b\d+\s+(?:second|minute|hour|day|week|month|year)s?\s+ago\b",
        r"\bin\s+\d+\s+(?:second|minute|hour|day|week|month|year)s?\b",
    )
)


def live_clock_page_failures(html: bytes | str, rel: str) -> list[str]:
    """SIG-UI-087: the live-clock violations one emitted page carries.

    A release page must never show a value that depends on the reader's
    current time — next-run dates, current freshness verdicts, status-lane
    counts, relative-time phrasing. Each failure names the page-relative
    path and the matched marker so the refusal is reviewable."""
    text = html.decode("utf-8", "replace") if isinstance(html, bytes) else html
    lowered = text.lower()
    failures: list[str] = []
    for needle in _LIVE_CLOCK_NEEDLES:
        if needle in lowered:
            failures.append(f"{rel}: live-clock marker {needle!r}")
    for rx in _LIVE_CLOCK_RES:
        m = rx.search(text)
        if m is not None:
            failures.append(f"{rel}: relative-time value {m.group(0)!r}")
    return failures


def live_clock_release_failures(release_root: Path) -> list[str]:
    """SIG-UI-087: scan every emitted HTML page under ``r/`` and
    ``releases/`` — a live-clock value on a release page fails the build
    and re-validation alike."""
    failures: list[str] = []
    for base in ("r", "releases"):
        root = Path(release_root) / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.html")):
            rel = path.relative_to(release_root).as_posix()
            failures.extend(live_clock_page_failures(path.read_bytes(), rel))
    return failures


# --------------------------------------------------------------------------- #
# Release-tree reading                                                         #
# --------------------------------------------------------------------------- #


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_record_index(root: Path, pub: str) -> dict[str, dict[str, dict[str, Any]]]:
    """``{compartment: {record_key: index row}}`` for one release tree —
    the record-id universe the diff keys on."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    comp_root = Path(root) / "r" / pub / "c"
    if not comp_root.is_dir():
        return out
    for comp_dir in sorted(comp_root.iterdir()):
        if not comp_dir.is_dir():
            continue
        idx = comp_dir / "records.index.jsonl"
        rows: dict[str, dict[str, Any]] = {}
        if idx.is_file():
            for row in _iter_jsonl(idx):
                rows[str(row.get("record_key"))] = dict(row)
        out[comp_dir.name] = rows
    return out


def _record_content(doc: Mapping[str, Any]) -> dict[str, Any]:
    """The compared content of one released record: bound-namespace and
    excluded (source/confidence/projection-schema) fields stripped;
    ``claim_anchors`` normalised to its id+locator+access_kind set."""
    out: dict[str, Any] = {}
    for field in COMPARED_FIELDS:
        if field == "claim_anchors":
            anchors = sorted(
                (
                    str(a.get("claim_id")),
                    str(a.get("locator") or ""),
                    str(a.get("access_kind") or ""),
                )
                for a in doc.get("claim_anchors") or []
                if isinstance(a, Mapping)
            )
            out[field] = [list(t) for t in anchors]
            continue
        value = doc.get(field)
        if field == "dedup" and value is None:
            # sparse by contract (pre-P35.47 exports) — absent and null are
            # the same compared state.
            continue
        if field in doc or field in ("inferred", "layer"):
            out[field] = value
    return out


def _content_digest(doc: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(_record_content(doc)))


def _read_record(root: Path, index_row: Mapping[str, Any]) -> dict[str, Any] | None:
    rel = index_row.get("json_path")
    if not rel:
        return None
    path = Path(root) / str(rel)
    if not path.is_file():
        return None
    try:
        doc = _read_json(path)
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _record_source_ids(doc: Mapping[str, Any] | None) -> set[str]:
    """The source ids one released record carries — claim anchors plus the
    record's ``source_refs`` identity list."""
    if not doc:
        return set()
    out: set[str] = set()
    for a in doc.get("claim_anchors") or []:
        if isinstance(a, Mapping) and a.get("source_id"):
            out.add(str(a["source_id"]))
    for s in doc.get("source_refs") or []:
        if isinstance(s, Mapping) and s.get("source_id"):
            out.add(str(s["source_id"]))
    return out


# --------------------------------------------------------------------------- #
# The previous release                                                        #
# --------------------------------------------------------------------------- #


def resolve_previous(
    previous: Path | str | None,
    previous_publication_id: str | None = None,
) -> tuple[Path, str] | None:
    """Resolve the previous-release input to ``(tree_root, publication_id)``.

    Accepted forms: a built release dir or a staged tree (``r/`` +
    ``releases/`` at top level — the pub is named or the single
    ``releases/p-*`` child), or a registry root (``latest.json`` +
    ``staged/`` — the pub is the current pointer's unless named). ``None``
    on no input; a named-but-unresolvable input raises — fail closed, never
    silently baseline."""
    if previous is None:
        return None
    root = Path(previous)
    if (root / "latest.json").is_file() and (root / "staged").is_dir():
        latest = _read_json(root / "latest.json")
        pub = previous_publication_id or str(latest.get("publication_id") or "")
        if not pub:
            raise ValueError(f"registry {root} has a latest pointer naming no publication")
        return root / "staged", pub
    pub = previous_publication_id or ""
    if not pub:
        pubs = (
            sorted(p.name for p in (root / "releases").glob("p-*") if p.is_dir())
            if (root / "releases").is_dir()
            else []
        )
        if len(pubs) == 1:
            pub = pubs[0]
        elif not pubs:
            raise ValueError(
                f"{root} holds no releases/p-* directory — the previous "
                "release could not be resolved"
            )
        else:
            raise ValueError(
                f"{root} holds {len(pubs)} releases — name --previous-publication explicitly"
            )
    return root, pub


# --------------------------------------------------------------------------- #
# The record diff                                                             #
# --------------------------------------------------------------------------- #


def _removed_reason(
    prev_row: Mapping[str, Any],
    prev_doc: Mapping[str, Any] | None,
    *,
    current_entity_keys: Mapping[str, str],
    current_source_ids: set[str],
    denied_record_keys: set[str],
) -> tuple[str, str]:
    """The closed removal reason + its recorded derivation basis."""
    key = str(prev_row.get("record_key"))
    if key in denied_record_keys:
        return (
            "withdrawn",
            "a publication disposition presented to the diff denies this record",
        )
    entity_id = str(prev_row.get("entity_id") or "")
    if entity_id and entity_id in current_entity_keys:
        return (
            "superseded",
            f"the entity survives under record key {current_entity_keys[entity_id]}",
        )
    src = _record_source_ids(prev_doc)
    if src and src.isdisjoint(current_source_ids):
        return (
            "source_withdrawn",
            "every source this record carried is absent from the current release's source universe",
        )
    return (
        "no_longer_published",
        "the record key is absent from this release; no withdrawal, "
        "re-keying or source loss was presented to the diff",
    )


def diff_records(
    prev_root: Path | None,
    prev_pub: str | None,
    cur_root: Path,
    cur_pub: str,
    *,
    denied_record_keys: set[str] | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """The record-id-keyed per-compartment diff (J3 §8.4).

    ``denied_record_keys`` names records a presented disposition withdraws;
    absent (or empty) no removal can be classed ``withdrawn``. Baseline
    (``prev_root is None``): every current record is ``added``."""
    denied = denied_record_keys or set()
    prev_index = load_record_index(prev_root, prev_pub) if prev_root and prev_pub else {}
    cur_index = load_record_index(cur_root, cur_pub)

    current_entity_keys: dict[str, str] = {}
    for _comp, rows in cur_index.items():
        for key, row in rows.items():
            eid = str(row.get("entity_id") or "")
            if eid:
                current_entity_keys.setdefault(eid, key)

    # the current release's source universe — from the emitted record docs
    # (bounded to records whose sources a removed row may cite)
    cur_source_ids: set[str] = set()
    for _comp, rows in cur_index.items():
        for row in rows.values():
            doc = _read_record(cur_root, row)
            cur_source_ids |= _record_source_ids(doc)

    diff: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for comp in sorted(set(prev_index) | set(cur_index)):
        prev_rows = prev_index.get(comp, {})
        cur_rows = cur_index.get(comp, {})
        added: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        changed: list[dict[str, Any]] = []
        for key in sorted(set(cur_rows) - set(prev_rows)):
            row = cur_rows[key]
            added.append(
                {
                    "record_key": key,
                    "entity_type": row.get("entity_type"),
                    "entity_id": row.get("entity_id"),
                    "label": row.get("label"),
                    "jurisdiction": row.get("slug_path") or row.get("jurisdiction"),
                }
            )
        for key in sorted(set(prev_rows) - set(cur_rows)):
            row = prev_rows[key]
            prev_doc = _read_record(prev_root, row) if prev_root else None
            reason, basis = _removed_reason(
                row,
                prev_doc,
                current_entity_keys=current_entity_keys,
                current_source_ids=cur_source_ids,
                denied_record_keys=denied,
            )
            removed.append(
                {
                    "record_key": key,
                    "entity_type": row.get("entity_type"),
                    "entity_id": row.get("entity_id"),
                    "label": row.get("label"),
                    "reason": reason,
                    "reason_basis": basis,
                }
            )
        for key in sorted(set(cur_rows) & set(prev_rows)):
            crow = cur_rows[key]
            prow = prev_rows[key]
            cdoc = _read_record(cur_root, crow)
            pdoc = _read_record(prev_root, prow) if prev_root else None
            if cdoc is None or pdoc is None:
                changed.append(
                    {
                        "record_key": key,
                        "entity_type": crow.get("entity_type"),
                        "entity_id": crow.get("entity_id"),
                        "changed_columns": "record_json_unreadable",
                    }
                )
                continue
            ccont = _record_content(cdoc)
            pcont = _record_content(pdoc)
            cols = sorted(k for k in set(ccont) | set(pcont) if ccont.get(k) != pcont.get(k))
            if cols:
                changed.append(
                    {
                        "record_key": key,
                        "entity_type": crow.get("entity_type"),
                        "entity_id": crow.get("entity_id"),
                        "changed_columns": "|".join(cols),
                    }
                )
        diff[comp] = {"added": added, "removed": removed, "changed": changed}
    return diff


# --------------------------------------------------------------------------- #
# The source diff                                                             #
# --------------------------------------------------------------------------- #


def _source_rows(payload: Any) -> dict[str, dict[str, Any]]:
    """Normalise a ``sig.source-row/1`` artifact (``{"sources": [...]}``, a
    bare list, or an id-keyed map) to ``{source_id: row}``."""
    rows: Iterable[Any]
    if isinstance(payload, Mapping):
        if isinstance(payload.get("sources"), list):
            rows = payload["sources"]
        else:
            rows = payload.values()
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if isinstance(r, Mapping) and r.get("source_id"):
            out[str(r["source_id"])] = dict(r)
    return out


def load_source_rows(export_dir: Path | str | None) -> dict[str, dict[str, Any]] | None:
    """The export's ``transparency/sources.json`` (``sig.source-row/1``)
    keyed by source id — ``None`` when the input was never presented (the
    honest ``not_evaluable`` state, never an empty universe)."""
    if export_dir is None:
        return None
    path = Path(export_dir) / "transparency" / "sources.json"
    if not path.is_file():
        # tolerate the ``web/sources.json`` mirror when it is the only one
        alt = Path(export_dir) / "web" / "sources.json"
        if not alt.is_file():
            return None
        path = alt
    try:
        return _source_rows(_read_json(path))
    except (OSError, ValueError):
        return None


def diff_sources(
    prev_rows: Mapping[str, Any] | None,
    cur_rows: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The per-source four-class diff (J3 §8.4).

    ``None`` on either side is a named ``not_evaluable`` absence — the
    source universe was never presented, so no class is asserted."""
    if prev_rows is None or cur_rows is None:
        return {
            "schema": SOURCE_CHANGES_SCHEMA,
            "state": "not_evaluable",
            "reason": (
                "the source-row universe was not presented to this diff "
                "(transparency/sources.json of both exports) — no added, "
                "retired, newly_failing or lane_changed class is asserted"
            ),
            "added": [],
            "retired": [],
            "newly_failing": [],
            "lane_changed": [],
        }
    added = sorted(set(cur_rows) - set(prev_rows))
    retired = sorted(set(prev_rows) - set(cur_rows))
    newly_failing: list[dict[str, Any]] = []
    lane_changed: list[dict[str, Any]] = []
    for sid in sorted(set(prev_rows) & set(cur_rows)):
        prow, crow = prev_rows[sid], cur_rows[sid]
        plife = str(prow.get("lifecycle_state") or "")
        clife = str(crow.get("lifecycle_state") or "")
        if plife == "published" and clife in _FAILING_LIFECYCLE:
            newly_failing.append(
                {
                    "source_id": sid,
                    "name": crow.get("name") or prow.get("name"),
                    "previous_lifecycle_state": plife,
                    "lifecycle_state": clife,
                }
            )
        plane = str(prow.get("lane") or "")
        clane = str(crow.get("lane") or "")
        if plane != clane:
            lane_changed.append({"source_id": sid, "previous_lane": plane, "lane": clane})
    return {
        "schema": SOURCE_CHANGES_SCHEMA,
        "state": "evaluated",
        "added": [
            {
                "source_id": s,
                "name": cur_rows[s].get("name"),
                "lifecycle_state": cur_rows[s].get("lifecycle_state"),
            }
            for s in added
        ],
        "retired": [
            {
                "source_id": s,
                "name": prev_rows[s].get("name"),
                "lifecycle_state": prev_rows[s].get("lifecycle_state"),
            }
            for s in retired
        ],
        "newly_failing": newly_failing,
        "lane_changed": lane_changed,
    }


# --------------------------------------------------------------------------- #
# The documents                                                               #
# --------------------------------------------------------------------------- #


def _release_block(descriptor: Mapping[str, Any] | None, pub: str) -> dict[str, Any]:
    d = descriptor or {}
    snap = d.get("snapshot") or {}
    return {
        "label": d.get("label"),
        "publication_id": pub,
        "as_of_world": snap.get("as_of_world") or d.get("as_of_world"),
        "as_of_belief": snap.get("as_of_belief") or d.get("as_of_belief"),
    }


def _versions_diff(
    prev_descriptor: Mapping[str, Any] | None, descriptor: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """The schema/ontology/ruleset version changes — per key, previous →
    current (J3 §8.4's changelog version block)."""
    cur = dict(descriptor.get("versions") or {})
    prev = dict((prev_descriptor or {}).get("versions") or {})
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(set(prev) | set(cur)):
        if prev.get(key) != cur.get(key):
            out[key] = {"previous": prev.get(key), "current": cur.get(key)}
    return out


def _feed_events(
    diff: Mapping[str, Any],
    *,
    new_date: str | None,
    old_date: str | None,
    digests: Mapping[str, tuple[str | None, str | None]],
    meta: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The field-level events ``/v1/changes`` serves — record-keyed,
    ``new_date`` carried so the route's ``since`` filter applies.

    Each event also carries the additive P37.40 (CHG-01) routing fields the
    per-place and per-source Atom feeds key on — ``jurisdiction`` (the
    record's display slug path), ``source_ids`` (the claim-anchor +
    source-ref universe of the compared record doc), ``label``,
    ``entity_type`` and ``compartment``. They are additive keys over the
    landed ``sig.release-changes-feed/1`` shape: API consumers ignore what
    they do not read, and the feed doc's own schema id is unchanged."""
    meta = meta or {}
    events: list[dict[str, Any]] = []
    for comp in sorted(diff):
        cell = diff[comp]

        def _routing(record_key: str, row: Mapping[str, Any]) -> dict[str, Any]:
            m = meta.get(record_key) or {}
            return {
                "compartment": comp,
                "entity_type": row.get("entity_type"),
                "entity_id": row.get("entity_id"),
                "label": row.get("label"),
                "jurisdiction": m.get("jurisdiction"),
                "source_ids": m.get("source_ids") or [],
            }

        for row in cell["added"]:
            _, nd = digests.get(row["record_key"], (None, None))
            events.append(
                {
                    "artifact_id": row["record_key"],
                    "field": "record",
                    "change_type": "added",
                    "old_value": None,
                    "new_value": {"label": row.get("label"), "entity_id": row.get("entity_id")},
                    "old_date": old_date,
                    "new_date": new_date,
                    "old_record_digest": None,
                    "new_record_digest": nd,
                    **_routing(row["record_key"], row),
                }
            )
        for row in cell["removed"]:
            od, _ = digests.get(row["record_key"], (None, None))
            events.append(
                {
                    "artifact_id": row["record_key"],
                    "field": "record",
                    "change_type": "removed",
                    "old_value": {"label": row.get("label"), "entity_id": row.get("entity_id")},
                    "new_value": None,
                    "old_date": old_date,
                    "new_date": new_date,
                    "old_record_digest": od,
                    "new_record_digest": None,
                    "reason": row.get("reason"),
                    **_routing(row["record_key"], row),
                }
            )
        for row in cell["changed"]:
            od, nd = digests.get(row["record_key"], (None, None))
            for col in str(row.get("changed_columns") or "").split("|"):
                if not col:
                    continue
                events.append(
                    {
                        "artifact_id": row["record_key"],
                        "field": col,
                        "change_type": "changed",
                        "old_value": None,
                        "new_value": None,
                        "old_date": old_date,
                        "new_date": new_date,
                        "old_record_digest": od,
                        "new_record_digest": nd,
                        **_routing(row["record_key"], row),
                    }
                )
    return events


def release_changes_documents(
    cur_root: Path,
    cur_pub: str,
    descriptor: Mapping[str, Any],
    *,
    prev_root: Path | None = None,
    prev_pub: str | None = None,
    prev_descriptor: Mapping[str, Any] | None = None,
    prev_sources: Mapping[str, Any] | None = None,
    cur_sources: Mapping[str, Any] | None = None,
    denied_record_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Assemble the whole changes document set — index, sources, feed,
    per-compartment row sets and the changelog inputs."""
    diff = diff_records(
        prev_root,
        prev_pub,
        cur_root,
        cur_pub,
        denied_record_keys=denied_record_keys,
    )
    sources = diff_sources(prev_sources, cur_sources)

    # record-content digests for the feed events (re-read is bounded to the
    # records the diff actually names); alongside them the P37.40 routing
    # meta — the record's slug path + source-id set, read from the same
    # index row / record doc the digest pass already loads.
    digests: dict[str, tuple[str | None, str | None]] = {}
    meta: dict[str, dict[str, Any]] = {}
    if prev_root is not None and prev_pub is not None:
        prev_index = load_record_index(prev_root, prev_pub)
    else:
        prev_index = {}
    cur_index = load_record_index(cur_root, cur_pub)

    def _meta_for(
        index: Mapping[str, Mapping[str, Any]],
        comp: str,
        key: str,
        doc: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        row = index.get(comp, {}).get(key, {})
        return {
            "jurisdiction": row.get("slug_path") or row.get("jurisdiction"),
            "label": row.get("label"),
            "source_ids": sorted(_record_source_ids(doc)),
        }

    for comp, cell in diff.items():
        for row in cell["removed"]:
            doc = (
                _read_record(prev_root, prev_index.get(comp, {}).get(row["record_key"], {}))
                if prev_root
                else None
            )
            digests[row["record_key"]] = (
                _content_digest(doc) if doc else None,
                None,
            )
            meta[row["record_key"]] = _meta_for(prev_index, comp, row["record_key"], doc)
        for row in cell["added"]:
            doc = _read_record(cur_root, cur_index.get(comp, {}).get(row["record_key"], {}))
            digests[row["record_key"]] = (
                None,
                _content_digest(doc) if doc else None,
            )
            meta[row["record_key"]] = _meta_for(cur_index, comp, row["record_key"], doc)
        for row in cell["changed"]:
            pdoc = (
                _read_record(prev_root, prev_index.get(comp, {}).get(row["record_key"], {}))
                if prev_root
                else None
            )
            cdoc = _read_record(cur_root, cur_index.get(comp, {}).get(row["record_key"], {}))
            digests[row["record_key"]] = (
                _content_digest(pdoc) if pdoc else None,
                _content_digest(cdoc) if cdoc else None,
            )
            meta[row["record_key"]] = _meta_for(cur_index, comp, row["record_key"], cdoc)

    rel = _release_block(descriptor, cur_pub)
    prev_block = _release_block(prev_descriptor, prev_pub) if prev_pub is not None else None
    old_date = str(prev_block.get("as_of_world") or "")[:10] or None if prev_block else None
    new_date = str(rel.get("as_of_world") or "")[:10] or None

    counts = {
        comp: {
            "added": len(cell["added"]),
            "removed": len(cell["removed"]),
            "changed": len(cell["changed"]),
            "records": len(cur_index.get(comp, {})),
            "previous_records": len(prev_index.get(comp, {})) if prev_root else 0,
        }
        for comp, cell in diff.items()
    }
    totals = {
        k: sum(c[k] for c in counts.values())
        for k in ("added", "removed", "changed", "records", "previous_records")
    }

    events = _feed_events(
        diff, new_date=new_date, old_date=old_date, digests=digests, meta=meta
    )

    disclosures = [
        "Sources and confidence are never compared per record — the "
        "changed-columns set is declared in compared_fields (J3 §8.4).",
        "Claim ids are not yet identity-stable across releases "
        "(SIG-CONF-003 unlanded): a claim_anchors diff may reflect claim "
        "re-minting, not a world change.",
    ]
    if prev_block is None:
        disclosures.append(
            "Baseline release — no previous activated release was "
            "presented; every record is recorded as added."
        )

    index_doc: dict[str, Any] = {
        "schema": CHANGES_SCHEMA,
        "release": rel,
        "previous": prev_block,
        "baseline": prev_block is None,
        "compared_fields": list(COMPARED_FIELDS),
        "excluded_fields": list(EXCLUDED_FIELDS),
        "compartments": counts,
        "totals": totals,
        "versions": _versions_diff(prev_descriptor, descriptor),
        "sources_state": sources.get("state"),
        "disclosures": disclosures,
        "files": [],  # filled by the emitter with the emitted artifact list
    }
    feed_doc: dict[str, Any] = {
        "schema": CHANGES_FEED_SCHEMA,
        "release": rel,
        "previous": prev_block,
        "baseline": prev_block is None,
        "since": None,
        "events": events[:FEED_EVENT_CAP],
        "event_count": len(events),
        "truncated": len(events) > FEED_EVENT_CAP,
        "note": (
            "The record-id-keyed diff of this release against the previous "
            "activated release; the full diff lives under "
            f"r/{cur_pub}/transparency/changes/ (sig.release-changes/1)."
        ),
        "disclosures": disclosures,
    }
    return {
        "index": index_doc,
        "sources": sources,
        "feed": feed_doc,
        "compartments": diff,
        "counts": counts,
        "totals": totals,
        "versions": _versions_diff(prev_descriptor, descriptor),
        "events": events,
    }


def changelog_markdown(
    docs: Mapping[str, Any],
    *,
    deprecations: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """The human ``CHANGELOG.md`` — sources, counts, versions,
    deprecations with dates (J3 §8.4); derived, never editorialised."""
    idx = docs["index"]
    rel = idx["release"]
    prev = idx.get("previous")
    totals = docs["totals"]
    counts = docs["counts"]
    sources = docs["sources"]
    lines: list[str] = []
    label = rel.get("label") or rel.get("publication_id")
    lines.append(f"# Release changelog — {label}")
    lines.append("")
    if prev is None:
        lines.append(
            "Baseline release — no previous activated release exists; every "
            "record below is new in this release."
        )
    else:
        prev_label = prev.get("label") or prev.get("publication_id")
        lines.append(
            f"Changes from {prev_label} (`{prev.get('publication_id')}`) to "
            f"{label} (`{rel.get('publication_id')}`)."
        )
        lines.append(
            f"Snapshot moved: world `{prev.get('as_of_world')}` → "
            f"`{rel.get('as_of_world')}`; belief `{prev.get('as_of_belief')}` "
            f"→ `{rel.get('as_of_belief')}`."
        )
    lines.append("")
    lines.append("## Records")
    lines.append("")
    lines.append(
        f"Total: **+{totals['added']} added · −{totals['removed']} removed · "
        f"~{totals['changed']} changed** (of {totals['records']} records; "
        f"{totals['previous_records']} before)."
    )
    lines.append("")
    for comp in sorted(counts):
        c = counts[comp]
        lines.append(
            f"- `{comp}`: +{c['added']} −{c['removed']} ~{c['changed']} ({c['records']} records)"
        )
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    if sources.get("state") == "evaluated":
        lines.append(f"- added: {len(sources.get('added') or [])}")
        lines.append(f"- retired: {len(sources.get('retired') or [])}")
        lines.append(f"- newly failing: {len(sources.get('newly_failing') or [])}")
        lines.append(f"- lane changed: {len(sources.get('lane_changed') or [])}")
    else:
        lines.append(
            "- not evaluable: the per-source diff input "
            "(`transparency/sources.json` of both exports) was not presented "
            "to this build — no source change is asserted."
        )
    lines.append("")
    lines.append("## Versions")
    lines.append("")
    versions = docs.get("versions") or {}
    if versions:
        for key in sorted(versions):
            v = versions[key]
            lines.append(f"- `{key}`: `{v.get('previous')}` → `{v.get('current')}`")
    else:
        lines.append("- unchanged against the previous release")
    lines.append("")
    lines.append("## Deprecations")
    lines.append("")
    if deprecations:
        for d in deprecations:
            when = d.get("date") or d.get("effective") or "date not recorded"
            lines.append(
                f"- {d.get('id') or d.get('name') or 'deprecation'} — {when}: "
                f"{d.get('note') or d.get('text') or ''}".rstrip()
            )
    else:
        lines.append("- none recorded")
    lines.append("")
    lines.append("## Disclosures")
    lines.append("")
    for note in idx.get("disclosures") or []:
        lines.append(f"- {note}")
    lines.append("")
    lines.append(
        "Record-level detail: `r/{}/transparency/changes/index.json` "
        "(`sig.release-changes/1`); the `/v1/changes` feed is backed by "
        "`changes.json` in the same directory.".format(rel.get("publication_id"))
    )
    lines.append("")
    return "\n".join(lines)


def emitted_changes_artifacts(
    out_dir: Path,
    pub: str,
    docs: Mapping[str, Any],
) -> list[tuple[str, bytes, str | None, str]]:
    """The ``(rel_path, bytes, compartment, licence)`` tuples the build's
    ``emit`` writes — every changes byte manifest-pinned under
    ``r/<pub>/transparency/changes/`` plus ``releases/<pub>/CHANGELOG.md``.
    The index doc's ``files`` list names every emitted artifact."""
    prefix = f"r/{pub}/transparency/changes"
    files: list[str] = []
    out: list[tuple[str, bytes, str | None, str]] = []

    def add(rel: str, data: bytes, lic: str = "CC-BY-4.0") -> None:
        out.append((rel, data, "metadata", lic))
        files.append(rel)

    index_doc = dict(docs["index"])
    # files list assembled after the parquet/docs are staged — patched below
    for comp in sorted(docs["compartments"]):
        cell = docs["compartments"][comp]
        add(f"{prefix}/{comp}/added.parquet", write_parquet(cell["added"], table_name="added"))
        add(
            f"{prefix}/{comp}/removed.parquet", write_parquet(cell["removed"], table_name="removed")
        )
        add(
            f"{prefix}/{comp}/changed.parquet", write_parquet(cell["changed"], table_name="changed")
        )
    add(f"{prefix}/sources.json", canonical_json(docs["sources"]))
    add(f"{prefix}/changes.json", canonical_json(docs["feed"]))
    add(f"releases/{pub}/CHANGELOG.md", changelog_markdown(docs).encode("utf-8"))
    index_doc["files"] = files + [f"{prefix}/index.json"]
    out.append((f"{prefix}/index.json", canonical_json(index_doc), "metadata", "CC-BY-4.0"))
    return out


__all__ = [
    "CHANGES_SCHEMA",
    "SOURCE_CHANGES_SCHEMA",
    "CHANGES_FEED_SCHEMA",
    "CHANGES_FEED_REL_SUFFIX",
    "COMPARED_FIELDS",
    "EXCLUDED_FIELDS",
    "REMOVED_REASONS",
    "FEED_EVENT_CAP",
    "changelog_markdown",
    "diff_records",
    "diff_sources",
    "emitted_changes_artifacts",
    "live_clock_page_failures",
    "live_clock_release_failures",
    "load_record_index",
    "load_source_rows",
    "release_changes_documents",
    "resolve_previous",
]
