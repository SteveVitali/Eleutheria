# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The registry field publish matrix as code (K10 §4, P36.45 / R11-K13-UX10-1,
SIG-TRANSP-035).

Every registry field carries a publish verdict — ``publish`` · ``transform`` ·
``never`` — read from the committed ``data/publish_matrix.toml`` table
(SIG-ENG-001 — data, not code). A field the table does not classify defaults to
``never`` (fail closed) AND fails the registry lint: a new field can never ship
an undeclared verdict by accident (K10 AT-K10-02 — "lint fails on a new
unclassified field").

The transform verdicts for ``access_method`` / ``auth_model`` publish ONLY a
member of their closed vocabularies — never the registry's free text, which
names fixture paths, internal connector ids and environment variables
(K10 P-8). The ordered ``[[access_method_map]]``/``[[auth_model_map]]`` rules in
the matrix classify each recorded free text onto one vocabulary member — first
substring match wins, no match is a lint violation.

``description`` is the D-J3-12 / OD-07-a batched verbatim flow: the operator
confirms drafted descriptions in batches of ~25; an unconfirmed row publishes
the honest interim label ``description_pending_review``, never drafted copy.
The lint enforces the binding: a registry row may declare ``description`` only
when its text sha256-matches a ``confirmed`` row for that source in the
committed batch files (``docs/build/reports/description-batches/``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from enum import StrEnum
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from ._data import load_table


class PublishVerdict(StrEnum):
    """The three publish verdicts (K10 §4)."""

    PUBLISH = "publish"
    TRANSFORM = "transform"
    NEVER = "never"


#: The honest absence the access transform emits for a row with no recorded
#: ``access_method`` (a LINK/REFERENCE-custody row is never fetched — the
#: vocabulary has no member for "nothing to classify", so the absence is named,
#: never guessed into a vocabulary token).
NOT_RECORDED = "not_recorded"

#: The interim label every unconfirmed source's description publishes as
#: (D-J3-12 / OD-07 a: "batches of ~25 confirmed verbatim; 'description
#: pending review' until then"). Never a drafted sentence.
DESCRIPTION_PENDING_REVIEW = "description_pending_review"

#: Batch files live beside the other operator-approval records.
BATCH_GLOB = "batch-*.md"

#: Rows per batch file (OD-07 a — "batches of ~25 confirmed verbatim").
BATCH_SIZE = 25


class UnmappedVocabulary(ValueError):
    """A recorded free text classified onto no closed-vocabulary member."""


@cache
def _matrix() -> dict[str, Any]:
    return load_table("publish_matrix")


def _vocab(name: str) -> frozenset[str]:
    return frozenset(str(v) for v in _matrix()["vocabularies"][name])


ACCESS_METHOD_VOCAB: frozenset[str] = _vocab("access_method")
AUTH_MODEL_VOCAB: frozenset[str] = _vocab("auth_model")
PUBLISHER_TYPES: frozenset[str] = _vocab("publisher_type")


def _field_table() -> Mapping[str, Any]:
    return _matrix()["fields"]


def field_verdict(field: str, *, parent: str | None = None) -> PublishVerdict:
    """The publish verdict for a registry field (fail closed).

    ``parent`` addresses a nested key (``rights``/``redistribution``/
    ``lineage``/``date_corrections``/``rights.reservation`` entry fields).
    An unclassified field is ``never`` — the lint turns that default into a
    violation, so a verdict is a recorded decision, never an accident.
    """
    fields = _field_table()
    node = fields.get(parent or field)
    if node is None:
        return PublishVerdict.NEVER
    if parent is not None:
        node = (node.get("sub") or {}).get(field)
        if node is None:
            return PublishVerdict.NEVER
    raw = str(node.get("verdict", ""))
    try:
        return PublishVerdict(raw)
    except ValueError:
        return PublishVerdict.NEVER


def _map_rules(name: str) -> tuple[tuple[str, str], ...]:
    return tuple((str(r["contains"]).lower(), str(r["token"])) for r in _matrix().get(name, ()))


def classify_access_method(text: str) -> str:
    """The closed-vocabulary access token a recorded ``access_method`` maps to.

    First case-insensitive substring match wins; an empty/absent text is the
    honest ``not_recorded``; an unmapped text raises (the lint's violation).
    """
    stripped = str(text).strip()
    if not stripped:
        return NOT_RECORDED
    low = stripped.lower()
    for pat, token in _map_rules("access_method_map"):
        if pat in low:
            return token
    raise UnmappedVocabulary(
        f"access_method {stripped!r} classifies onto no closed-vocabulary "
        f"member {sorted(ACCESS_METHOD_VOCAB)} — extend access_method_map in "
        "publish_matrix.toml deliberately (K10 §4)"
    )


def classify_auth_model(text: str) -> str:
    """The closed-vocabulary auth token a recorded ``auth_model`` maps to."""
    stripped = str(text).strip() or "none"
    low = stripped.lower()
    for pat, token in _map_rules("auth_model_map"):
        if pat in low:
            return token
    raise UnmappedVocabulary(
        f"auth_model {stripped!r} classifies onto no closed-vocabulary "
        f"member {sorted(AUTH_MODEL_VOCAB)} — extend auth_model_map in "
        "publish_matrix.toml deliberately (K10 §4)"
    )


def published_field(record: Any, field: str) -> Any:
    """The publishable form of a transform-verdict registry field.

    ``publish`` returns the recorded value; ``never`` is refused outright
    (a caller asking for a never-field gets a refusal, never the content);
    the ``access_method``/``auth_model`` transforms classify to their
    vocabulary member; other transforms return their declared transform
    name for the consumer to render (the glosses/labels live with the
    consumers — K9/K10 wording, UX10-3).
    """
    verdict = field_verdict(field)
    if verdict is PublishVerdict.NEVER:
        raise ValueError(
            f"registry field {field!r} carries verdict 'never' — it never "
            "reaches a public artifact (SIG-TRANSP-035)"
        )
    value = getattr(record, field, None)
    if verdict is PublishVerdict.PUBLISH:
        return value
    node = _field_table()[field]
    transform = str(node.get("transform") or "")
    if transform == "vocab:access_method":
        return classify_access_method(str(value or ""))
    if transform == "vocab:auth_model":
        return classify_auth_model(str(value or ""))
    return {"transform": transform, "value": value}


def description_for(record: Any) -> str:
    """The publishable description: the confirmed text or the interim label."""
    text = str(getattr(record, "description", "") or "").strip()
    return text if text else DESCRIPTION_PENDING_REVIEW


# ---------------------------------------------------------------------------
# Description batch files (D-J3-12 / OD-07 a) — agent drafts in batches of
# ~25; the operator confirms verbatim; an unconfirmed row is the interim label.
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return Path(str(files("connectors").joinpath("data", "sources.toml"))).parents[4]


def batch_dir() -> Path:
    """The committed description-batch directory."""
    return _repo_root() / "docs" / "build" / "reports" / "description-batches"


def sha256_text(text: str) -> str:
    """The ADR-168 hash convention: UTF-8, no trailing newline."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def draft_description(source: Any) -> str:
    """The agent-drafted description for one source — derived from registry
    facts only (name, kind, publisher), labelled pending until the operator
    confirms it verbatim (D-J3-12)."""
    kind_labels = {
        "upstream_project": "an upstream project",
        "vendor_site": "a vendor site",
        "government_portal": "a government portal",
        "government_mandated_disclosure": "a government mandated disclosure",
        "records_channel": "a records channel",
        "news_publisher": "a news publisher",
        "court_system": "a court system",
        "academic": "an academic",
        "community": "a community",
        "contributor": "a contributor",
        "commercial": "a commercial",
    }
    kind = str(getattr(source, "source_kind", "") or "")
    label = kind_labels.get(kind) or kind_labels.get(getattr(kind, "value", ""), "a registry")
    publisher = str(getattr(source, "publisher", "") or "").strip()

    # The name/publisher ride code spans: registry names can carry words like
    # `live`/`hosted` that a build-memory lint would otherwise read as a
    # production claim — the code span marks them as the identifier they are.
    # `|`/`;` sanitise the same way (a `|` would break the table; a `;` would
    # split a lint segment).
    def _cell(text: str) -> str:
        return text.replace("|", "·").replace(";", ",")

    by = f" published by `{_cell(publisher)}`" if publisher else ""
    return f"`{_cell(source.name)}` — {label} source{by}."


def batch_rows(sources: Any) -> list[list[tuple[str, str, str, str]]]:
    """The deterministic batch rows: ``(batch_id, source_id, text, sha256)``

    grouped in batches of ``BATCH_SIZE`` over the registry's id order.
    """
    ordered = sorted(sources, key=lambda s: s.id)
    batches: list[list[tuple[str, str, str, str]]] = []
    for start in range(0, len(ordered), BATCH_SIZE):
        group = ordered[start : start + BATCH_SIZE]
        batch_no = len(batches) + 1
        rows = [
            (
                f"D{batch_no:02d}-{i + 1:02d}",
                s.id,
                draft_description(s),
                sha256_text(draft_description(s)),
            )
            for i, s in enumerate(group)
        ]
        batches.append(rows)
    return batches


def render_batch(batch_no: int, rows: list[tuple[str, str, str, str]]) -> str:
    """One batch file's markdown (the row table the operator confirms)."""
    head = (
        f"# Description batch {batch_no:02d} — agent-drafted source descriptions "
        "awaiting operator verbatim confirmation\n\n"
        "<!-- P36.45 (R11-K13-UX10-1; D-J3-12 / OD-07 a — 'batches of ~25 "
        "confirmed verbatim; description pending review until then'). "
        "Append-only: a status change is recorded in the confirmation log "
        "below with a `date -u` stamp; rows are never deleted. -->\n\n"
        "## Convention\n\n"
        "One row per agent-drafted per-source description — the **source** id,\n"
        "the exact **text** as it will render, its **sha256** (UTF-8, no trailing\n"
        "newline), and a **status** (`pending` · `confirmed`). Only `confirmed`\n"
        "descriptions may land on the registry `description` field — the\n"
        "publish-matrix lint fails a declared description whose sha256 matches\n"
        "no confirmed row here. An unconfirmed source publishes\n"
        "`description_pending_review`.\n\n"
        "## Rows\n\n"
        "| id | source | text | sha256 | status |\n"
        "|---|---|---|---|---|\n"
    )
    body = "".join(f"| {i} | {s} | {t} | {h} | pending |\n" for i, s, t, h in rows)
    return head + body + "\n## Confirmation log\n\n(none yet)\n"


def parse_batches(directory: Path) -> dict[str, dict[str, str]]:
    """Parse committed batch files: ``{source_id: {text, sha256, status}}``."""
    out: dict[str, dict[str, str]] = {}
    for path in sorted(directory.glob(BATCH_GLOB)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5 or cells[0] in {"id", "---"} or cells[0].startswith("---"):
                continue
            _row_id, source_id, text, sha, status = cells
            out[source_id] = {"text": text, "sha256": sha, "status": status}
    return out


def confirmed_descriptions(directory: Path | None = None) -> dict[str, str]:
    """``{source_id: confirmed_text}`` from the batch files' confirmed rows."""
    directory = directory or batch_dir()
    if not directory.is_dir():
        return {}
    return {
        sid: r["text"] for sid, r in parse_batches(directory).items() if r["status"] == "confirmed"
    }


def batch_drift(directory: Path | None = None) -> list[str]:
    """Drift between committed batch rows and a fresh generation.

    Compares (row id, source, text, sha256) — the ``status`` column is the
    operator's write surface and never drifts the check. A pending→confirmed
    flip stays a valid committed file; an edited text, a dropped row or a
    wrong hash is drift.
    """
    from .registry import sources as _sources

    directory = directory or batch_dir()
    expected = batch_rows(_sources())
    problems: list[str] = []
    if not directory.is_dir():
        return [f"description batch dir missing: {directory}"]
    files_found = sorted(directory.glob(BATCH_GLOB))
    if len(files_found) != len(expected):
        problems.append(f"batch file count {len(files_found)} != expected {len(expected)}")
    seen: dict[str, tuple[str, str, str]] = {}
    for path in files_found:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5 or cells[0] in {"id", "---"} or cells[0].startswith("---"):
                continue
            row_id, source_id, text, sha, status = cells
            if status not in {"pending", "confirmed"}:
                problems.append(f"{path.name}: {row_id} has status {status!r}")
            seen[row_id] = (source_id, text, sha)
    flat = [(i, s, t, h) for batch in expected for (i, s, t, h) in batch]
    for row_id, source_id, text, sha in flat:
        got = seen.get(row_id)
        if got is None:
            problems.append(f"description batches: missing row {row_id} (source {source_id})")
        elif got != (source_id, text, sha):
            problems.append(
                f"description batches: row {row_id} drifted — committed "
                f"{got[0]!r}/{got[2][:12]}… vs generated {source_id!r}/{sha[:12]}…"
            )
    return problems


# ---------------------------------------------------------------------------
# The registry lint — the CI leg wired into `sig-connectors validate`.
# ---------------------------------------------------------------------------


def _row_field_keys(row: Mapping[str, Any]) -> list[tuple[tuple[str, ...], str]]:
    """Every (path, field) a registry row carries — ``((), f)`` top-level and
    nested keys under tables / arrays-of-tables with their path segments."""
    keys: list[tuple[tuple[str, ...], str]] = []

    def walk(prefix: tuple[str, ...], node: Mapping[str, Any]) -> None:
        for key, value in node.items():
            keys.append((prefix, key))
            if isinstance(value, Mapping):
                walk(prefix + (key,), value)
            elif isinstance(value, list):
                for entry in value:
                    if isinstance(entry, Mapping):
                        walk(prefix + (key,), entry)

    walk((), row)
    return keys


def _classified(path: tuple[str, ...], leaf: str) -> bool:
    """Whether the matrix classifies ``path.leaf`` — descending sub-tables."""
    node: Mapping[str, Any] = _field_table()
    for segment in path:
        if segment not in node:
            return False
        node = node[segment].get("sub") or {}
    return leaf in node


def publish_matrix_violations(directory: Path | None = None) -> list[str]:
    """Every registry row's conformance to the verdict table (K10 §4).

    * every field a row carries is classified (fail closed — an unclassified
      field is a violation, never a silent `never`);
    * every transform verdict names a transform;
    * every row's ``access_method``/``auth_model`` maps to its vocabulary;
    * a declared ``publisher_type`` is a vocabulary member;
    * ``one_time_load`` is boolean and consistent with a once-only cadence;
    * a declared ``description`` sha256-matches a confirmed batch row —
      drafted copy never lands unconfirmed (D-J3-12); the interim label is
      always a pass.
    """
    from .registry import sources as _sources

    fields = _field_table()
    problems: list[str] = []
    # The matrix table itself must be self-consistent: every declared field
    # has a verdict, every transform verdict names its transform.
    for name, node in fields.items():
        if str(node.get("verdict", "")) not in {v.value for v in PublishVerdict}:
            problems.append(f"matrix field {name!r} has no valid verdict")
        if (
            str(node.get("verdict", "")) == "transform"
            and not str(node.get("transform") or "").strip()
        ):
            problems.append(f"matrix field {name!r}: transform verdict with no transform")
        for sub_name, sub_node in (node.get("sub") or {}).items():
            if str(sub_node.get("verdict", "")) not in {v.value for v in PublishVerdict}:
                problems.append(f"matrix field {name}.{sub_name} has no valid verdict")
    try:
        import tomllib

        raw_rows = tomllib.loads(
            Path(str(files("connectors").joinpath("data", "sources.toml"))).read_text()
        )["sources"]
    except (OSError, KeyError) as exc:
        return [f"sources.toml unreadable for the publish matrix lint: {exc}"]

    d = directory or batch_dir()
    confirmed = confirmed_descriptions(d)
    parsed = parse_batches(d) if d.is_dir() else {}

    records = {s.id: s for s in _sources()}
    for source_id, row in raw_rows.items():
        for path, key in _row_field_keys(row):
            if not path:
                if key not in fields:
                    problems.append(
                        f"source {source_id!r}: unclassified field {key!r} — "
                        "declare its verdict in publish_matrix.toml (fail closed)"
                    )
            elif not _classified(path, key):
                problems.append(
                    f"source {source_id!r}: unclassified field "
                    f"{'.'.join(path)}.{key} — declare its verdict in "
                    "publish_matrix.toml (fail closed)"
                )
        rec = records.get(source_id)
        if rec is None:
            continue
        try:
            classify_access_method(str(row.get("access_method", "")))
        except UnmappedVocabulary as exc:
            problems.append(f"source {source_id!r}: {exc}")
        try:
            classify_auth_model(str(row.get("auth_model", "")))
        except UnmappedVocabulary as exc:
            problems.append(f"source {source_id!r}: {exc}")
        ptype = str(row.get("publisher_type", "") or "")
        if ptype and ptype not in PUBLISHER_TYPES:
            problems.append(
                f"source {source_id!r}: publisher_type {ptype!r} is not in the "
                f"closed vocabulary {sorted(PUBLISHER_TYPES)}"
            )
        otl = row.get("one_time_load")
        if otl is not None and not isinstance(otl, bool):
            problems.append(f"source {source_id!r}: one_time_load must be a boolean")
        if otl is True and "once" not in str(row.get("cadence", "")).lower():
            problems.append(
                f"source {source_id!r}: one_time_load=true but cadence "
                f"{row.get('cadence')!r} is not a once-only cadence"
            )
        desc = str(row.get("description", "") or "")
        if desc:
            want = confirmed.get(source_id)
            if want is None or sha256_text(want) != sha256_text(desc):
                staged = parsed.get(source_id)
                if staged is None:
                    problems.append(
                        f"source {source_id!r}: declares description with no "
                        "batch row — descriptions land only via a confirmed "
                        "batch (D-J3-12)"
                    )
                else:
                    problems.append(
                        f"source {source_id!r}: declares description while its "
                        f"batch row is {staged['status']!r} — only 'confirmed' "
                        "rows may land (D-J3-12 / 'description pending review' "
                        "until then)"
                    )
    return problems


__all__ = [
    "ACCESS_METHOD_VOCAB",
    "AUTH_MODEL_VOCAB",
    "BATCH_SIZE",
    "DESCRIPTION_PENDING_REVIEW",
    "NOT_RECORDED",
    "PUBLISHER_TYPES",
    "PublishVerdict",
    "UnmappedVocabulary",
    "batch_dir",
    "batch_drift",
    "batch_rows",
    "classify_access_method",
    "classify_auth_model",
    "confirmed_descriptions",
    "description_for",
    "draft_description",
    "field_verdict",
    "parse_batches",
    "publish_matrix_violations",
    "published_field",
    "render_batch",
    "sha256_text",
]
