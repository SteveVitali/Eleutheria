# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.49 (TX-06, SIG-TRANSP-010, J3 §7.3) — the curated known-issues half of
the issues log.

``known_issues.toml`` (committed, ``exports/src/exports/data/``) records
human-curated per-source issues — the classes a reviewer asserted, keyed by
source, append-only (a resolved issue is a new ``status = "closed"`` row
state + ``closed_at`` + ``correction_ref``; nothing is edited away). The
module validates the file fail-closed and shapes each entry into the
``sig.source-issue/1`` row that lands in ``transparency/issues.jsonl``
beside the auto-detected instances.

D-J3-12 [B-2] = OD-07 a — carried verbatim: the public text is
agent-drafted until the operator confirms the batch verbatim. An entry
whose ``text_state`` is ``pending_review`` publishes class + dates only —
its drafted ``text`` never reaches a public artifact.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KNOWN_ISSUES_SCHEMA = "sig.known-issues/1"

#: The committed curated registry (packaged data file — the registry of
#: record for this artifact class, the quality_checks.toml pattern).
KNOWN_ISSUES_DATA = Path(__file__).resolve().parent / "data" / "known_issues.toml"

#: The curated issue classes (J3 §7.3's named examples + the ADR-210
#: geometry-defect vocabulary). A class absent here refuses the emit —
#: vocabulary growth is a file edit, never a fallback.
CURATED_ISSUE_CLASSES: frozenset[str] = frozenset(
    {
        "axis_swap",
        "null_island",
        "sign_flip",
        "wrong_jurisdiction",
        "jurisdiction_code_collision",
        "misattribution",
        "terms_conflict",
        "untyped_technology",
        "data_defect",
    }
)

#: ``text_state`` vocabulary — D-J3-12's two postures.
TEXT_STATES: frozenset[str] = frozenset({"pending_review", "confirmed"})

#: ``status`` vocabulary — the log is append-only; a resolved issue is a
#: ``closed`` row state, never a removed row.
ISSUE_STATUSES: frozenset[str] = frozenset({"open", "closed"})


class KnownIssuesError(ValueError):
    """A ``known_issues.toml`` row or the file itself failed its contract."""


def _dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _err(where: str, msg: str) -> KnownIssuesError:
    return KnownIssuesError(f"{where}: {msg}")


def _validate_entry(raw: Mapping[str, Any], where: str) -> dict[str, Any]:
    """One ``[[issue]]`` row → the validated entry (fail closed — a field
    that fails its contract refuses the whole file)."""
    source_id = raw.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise _err(where, "source_id must be a non-empty string")
    cls = raw.get("issue_class")
    if cls not in CURATED_ISSUE_CLASSES:
        raise _err(
            where,
            f"issue_class {cls!r} is not in the curated vocabulary {sorted(CURATED_ISSUE_CLASSES)}",
        )
    opened = _dt(raw.get("opened_at"))
    if opened is None:
        raise _err(where, "opened_at must be an ISO-8601 instant")
    status = raw.get("status")
    if status not in ISSUE_STATUSES:
        raise _err(where, f"status {status!r} — expected one of {sorted(ISSUE_STATUSES)}")
    closed = _dt(raw.get("closed_at")) if raw.get("closed_at") is not None else None
    if status == "closed" and closed is None:
        raise _err(where, "closed_at is required when status is closed")
    if status == "open" and raw.get("closed_at") is not None:
        raise _err(where, "closed_at is recorded only on a closed row")
    if closed is not None and closed < opened:
        raise _err(where, "closed_at precedes opened_at")
    text_state = raw.get("text_state")
    if text_state not in TEXT_STATES:
        raise _err(where, f"text_state {text_state!r} — expected one of {sorted(TEXT_STATES)}")
    text = raw.get("text")
    if text is not None and not isinstance(text, str):
        raise _err(where, "text must be a string or absent")
    if text_state == "confirmed" and not (isinstance(text, str) and text.strip()):
        raise _err(where, "a confirmed row needs its operator-confirmed text")
    ref = raw.get("correction_ref")
    if ref is not None and not isinstance(ref, str):
        raise _err(where, "correction_ref must be a string or absent")
    issue_id = raw.get("issue_id")
    if issue_id is not None and not isinstance(issue_id, str):
        raise _err(where, "issue_id must be a string or absent")
    return {
        "issue_id": issue_id or f"ki:{source_id}:{cls}:{opened.astimezone(UTC).date().isoformat()}",
        "source_id": source_id,
        "issue_class": cls,
        "opened_at": _iso(opened),
        "status": status,
        "closed_at": _iso(closed),
        "correction_ref": ref,
        "text": text,
        "text_state": text_state,
    }


def load_known_issues(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Parse + validate ``known_issues.toml`` → the entry list, ordered
    (source_id, opened_at, issue_id). Fail closed: a malformed file or row
    refuses the whole emit."""
    p = Path(path) if path is not None else KNOWN_ISSUES_DATA
    doc = tomllib.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != KNOWN_ISSUES_SCHEMA:
        raise _err(str(p), f"schema is not {KNOWN_ISSUES_SCHEMA}")
    rows = doc.get("issue")
    if not isinstance(rows, list):
        raise _err(str(p), "[[issue]] rows must be a list")
    out = [
        _validate_entry(r if isinstance(r, Mapping) else {}, f"{p}:issue[{i}]")
        for i, r in enumerate(rows)
    ]
    ids = [e["issue_id"] for e in out]
    if len(ids) != len(set(ids)):
        raise _err(str(p), "duplicate issue_id")
    out.sort(key=lambda e: (e["source_id"], e["opened_at"] or "", e["issue_id"]))
    return out


def curated_issue_records(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Entries → ``sig.source-issue/1`` rows (``kind = "curated"``; the
    pending-review scrub drops unconfirmed text — D-J3-12)."""
    out: list[dict[str, Any]] = []
    for e in entries:
        confirmed = e.get("text_state") == "confirmed"
        out.append(
            {
                "schema": "sig.source-issue/1",
                "issue_id": str(e["issue_id"]),
                "source_id": str(e["source_id"]),
                "issue_class": str(e["issue_class"]),
                "opened_at": e["opened_at"],
                "last_seen_at": e["closed_at"] or e["opened_at"],
                "closed_at": e["closed_at"],
                "count": None,
                "basis": "known_issues.toml",
                "kind": "curated",
                "text": str(e["text"]) if confirmed and e.get("text") else None,
                "text_state": str(e["text_state"]),
                "correction_ref": e.get("correction_ref"),
            }
        )
    return out
