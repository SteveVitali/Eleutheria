# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""DDL ↔ value-object alignment for the annotation layer (P21.2 deliverable 1; LD-V05).

The reconcile / inference / tasks layer is a set of pure-Python value objects that
are *aligned to* the physical annotation tables (`contradiction`, `coverage_record`,
`research_task`, `inference.derived_fact`) but — under the ACCEPTED compute-on-read
design (ADR-037/038/039/054, A5/HG-14) — are recomputed on read rather than persisted
(LD-V05, LD-D07). Persistence is deferred; these value objects stay the computation
layer.

Because they are *not* wired to the tables, nothing else forces the two shapes to stay
in step: the DDL could grow a `NOT NULL` column the value object can never fill, or a
field could be renamed/retyped, and no existing test would notice until persistence is
attempted (P21.4+). This module is that guard. For each value-object ↔ table pair it
introspects the **live** schema (`information_schema.columns`, real Docker PG — never a
mock) and asserts, field by field, that names, types and nullability agree.

The contract, per the ticket: any mismatch is fixed **only** by an additive sqitch
change (a new *nullable* column) or a dataclass alias in the mapping below — **never**
by dropping a column. Two mapping structures encode the intended persisted projection:

* ``fields`` — dataclass field → column. A rename is expressed here as an alias
  (e.g. ``Inference.value`` → ``derived_fact.value_json``); this is the "dataclass
  alias" escape hatch the ticket allows, and it is exercised below.
* ``compute_only`` — value-object fields that are intentionally **not** persisted
  (transient display scaffolding, or enforced-constant invariants), each with a
  reason. Under compute-on-read these are recomputed, not stored.
* ``unpersisted_columns`` — columns this value object does not source (DB-generated
  keys, or lifecycle columns owned by a sibling object). Each MUST be nullable or
  carry a server default, so the value object can insert a row without it — a
  ``NOT NULL`` column with no default that no field fills is a hard mismatch.

Both maps are exhaustive: a *new* field or column that no map classifies fails the
drift guard, forcing a deliberate decision rather than silent divergence.
"""

from __future__ import annotations

import types
import typing
from collections.abc import Sequence
from dataclasses import fields, is_dataclass
from datetime import datetime

import pytest
from inference.coverage import CoverageRecord
from reconcile.model import Contradiction, Inference, ResearchTask


class Pair:
    """One value-object ↔ table alignment contract (see module docstring)."""

    def __init__(
        self,
        *,
        name: str,
        value_type: type,
        table_schema: str,
        table: str,
        fields: dict[str, str],
        compute_only: dict[str, str],
        unpersisted_columns: dict[str, str],
    ) -> None:
        self.name = name
        self.value_type = value_type
        self.table_schema = table_schema
        self.table = table
        self.fields = fields
        self.compute_only = compute_only
        self.unpersisted_columns = unpersisted_columns


# --- the persisted-projection contracts --------------------------------------
#
# Under the ACCEPTED compute-on-read verdict (ADR-037/038/039/054) NO field is
# persisted today; these maps describe the projection a future persistence ticket
# (P21.4+) must honour, and guard it against drift now. Adding a nullable column
# for a currently ``compute_only`` field is an additive change at that time — the
# ADRs' (evaluated, not-fired) revisit triggers cover it.

PAIRS: list[Pair] = [
    Pair(
        name="contradiction",
        value_type=Contradiction,
        table_schema="public",
        table="contradiction",
        fields={
            "contradiction_id": "contradiction_id",
            "subject_id": "subject_id",
            "predicate_id": "predicate_id",
            "contradiction_type": "contradiction_type",
            "claim_ids": "claim_ids",
            "severity": "severity",
            "status": "status",
            "resolution_note": "resolution_note",
            "resolved_by": "resolved_by",
            "resolved_at": "resolved_at",
            "research_task_ids": "research_task_ids",
        },
        compute_only={
            "claim_values": "disagreeing values as seen at detection — displayable "
            "before the contradiction is linked to persisted claim rows (model.py); "
            "not persisted under compute-on-read",
            "evidence": "detached evidence tuple for pre-persistence display; the "
            "persisted linkage is claim_ids",
            "note": "human description recomputed on read; a nullable `note` column is "
            "the additive step when persistence lands (ADR-037 revisit trigger)",
        },
        unpersisted_columns={},
    ),
    Pair(
        name="coverage_record",
        value_type=CoverageRecord,
        table_schema="public",
        table="coverage_record",
        fields={
            "predicate_id": "predicate_id",
            "absence_kind": "absence_kind",
            "subject_id": "subject_id",
            "subject_class": "subject_class",
            "jurisdiction_id": "jurisdiction_id",
            "sources_searched": "sources_searched",
            "searched_at": "searched_at",
            "searched_by": "searched_by",
            "search_method": "search_method",
        },
        compute_only={},
        unpersisted_columns={
            "coverage_id": "uuid primary key, server-generated (uuidv7 default)",
        },
    ),
    Pair(
        name="research_task",
        value_type=ResearchTask,
        table_schema="public",
        table="research_task",
        fields={
            "task_id": "task_id",
            "task_type": "task_type",
            "subject_id": "subject_id",
            "closing_condition": "closing_condition",
            "detector_version": "detector_version",
            "priority": "priority",
            "jurisdiction_id": "jurisdiction_id",
            "status": "status",
        },
        compute_only={
            "note": "free-text note recomputed on read; a nullable `note` column is the "
            "additive step when persistence lands (ADR-039 revisit trigger)",
        },
        unpersisted_columns={
            "disposition": "§33.4 lifecycle column, nullable; set by the task engine "
            "(tasks.lifecycle.ResearchTask) when persistence lands (deferred)",
            "claimed_by": "claim lifecycle column, nullable (deferred persistence)",
            "claimed_at": "claim lifecycle column, nullable (deferred persistence)",
            "claim_expires_at": "claim lifecycle column, nullable (deferred persistence)",
            "generated_at": "server default clock_timestamp()",
        },
    ),
    Pair(
        name="inference.derived_fact",
        value_type=Inference,
        table_schema="inference",
        table="derived_fact",
        fields={
            "subject_id": "subject_id",
            "predicate_id": "predicate_id",
            # dataclass alias: the value object names it `value`, the column is
            # `value_json` (jsonb). This is the ticket's "dataclass alias" fix for a
            # name mismatch — no column is renamed or dropped.
            "value": "value_json",
            "derivation_rule": "derivation_rule",
            "rule_version": "rule_version",
            "input_claim_ids": "input_claim_ids",
            "confidence": "confidence",
            "derived_at": "derived_at",
        },
        compute_only={
            "rationale": "human derivation rationale, recomputed on read (deferred persistence)",
            "alternatives": "ambiguity-preserving alternatives kept visible in the value "
            "object (§3.1); a nullable column is the additive step when persistence lands",
            "layer": "enforced constant 'L4' (init=False invariant, SIG-RECON-031)",
            "pushable_to_osm": "enforced constant False (init=False invariant, SIG-RECON-031)",
        },
        unpersisted_columns={
            "derived_id": "uuid primary key, server-generated (uuidv7 default)",
        },
    ),
]


# --- introspection helpers ----------------------------------------------------


def _live_columns(conn: object, schema: str, table: str) -> dict[str, dict[str, object]]:
    rows = conn.execute(
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name=%s",
        (schema, table),
    ).fetchall()
    return {
        name: {
            "data_type": data_type,
            "nullable": is_nullable == "YES",
            "has_default": default is not None,
        }
        for (name, data_type, is_nullable, default) in rows
    }


def _resolved_hints(value_type: type) -> dict[str, object]:
    # get_type_hints resolves the `from __future__ import annotations` strings.
    return typing.get_type_hints(value_type)


def _is_optional(hint: object) -> bool:
    """Whether the annotation permits ``None`` (``X | None`` / ``Optional[X]``)."""
    origin = typing.get_origin(hint)
    if origin is typing.Union or origin is types.UnionType:
        return type(None) in typing.get_args(hint)
    return False


def _non_none_arg(hint: object) -> object:
    if _is_optional(hint):
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        return args[0] if len(args) == 1 else hint
    return hint


def _base_kind(hint: object) -> object:
    """Reduce a (possibly generic/optional) annotation to a comparison kind."""
    hint = _non_none_arg(hint)
    origin = typing.get_origin(hint)
    if origin in (tuple, list) or origin is Sequence:
        return "sequence"
    if hint in (object, typing.Any) or origin is dict:
        return "json"
    return hint


def _type_is_compatible(hint: object, sql_type: str) -> bool:
    kind = _base_kind(hint)
    if sql_type == "ARRAY":
        return kind == "sequence"
    if sql_type in ("uuid", "text", "character varying"):
        return kind is str
    if sql_type == "numeric":
        return kind in (int, float)
    if sql_type in ("integer", "bigint", "smallint"):
        return kind is int
    if sql_type == "boolean":
        return kind is bool
    if sql_type in ("timestamp with time zone", "timestamp without time zone", "date"):
        return kind is datetime
    if sql_type in ("jsonb", "json"):
        return kind == "json"
    return False


def _field_can_be_none(hint: object) -> bool:
    """A field may hold ``None`` if its annotation is optional (defaults follow the
    annotation here — every ``None`` default is typed ``X | None``)."""
    return _is_optional(hint)


# --- the alignment tests ------------------------------------------------------


@pytest.mark.parametrize("pair", PAIRS, ids=[p.name for p in PAIRS])
def test_annotation_layer_ddl_matches_value_object(conn: object, pair: Pair) -> None:
    """0 mismatches between each value object and its live annotation table."""
    assert is_dataclass(pair.value_type), f"{pair.name}: value type must be a dataclass"

    columns = _live_columns(conn, pair.table_schema, pair.table)
    assert columns, (
        f"{pair.name}: no columns found for {pair.table_schema}.{pair.table} — the "
        "sqitch plan did not deploy the annotation tables"
    )
    hints = _resolved_hints(pair.value_type)
    field_names = {f.name for f in fields(pair.value_type)}

    mismatches: list[str] = []

    # (A) field drift guard: every dataclass field is either mapped or compute-only.
    unclassified_fields = field_names - set(pair.fields) - set(pair.compute_only)
    for name in sorted(unclassified_fields):
        mismatches.append(
            f"field {name!r} is neither mapped to a column nor declared compute_only "
            "(new field? classify it — add a nullable column or a compute_only reason)"
        )

    # (B) column drift guard: every live column is mapped or explicitly unpersisted.
    mapped_columns = set(pair.fields.values())
    classified_columns = mapped_columns | set(pair.unpersisted_columns)
    for col in sorted(set(columns) - classified_columns):
        mismatches.append(
            f"column {col!r} is neither mapped from a field nor declared unpersisted "
            "(new column? map it or declare it nullable/defaulted — never drop it)"
        )

    # (C) referential sanity: every mapped/declared column actually exists; the two
    # column sets do not overlap.
    for field_name, col in pair.fields.items():
        if col not in columns:
            mismatches.append(f"field {field_name!r} maps to missing column {col!r}")
    for col in pair.unpersisted_columns:
        if col not in columns:
            mismatches.append(f"unpersisted column {col!r} does not exist")
    for col in mapped_columns & set(pair.unpersisted_columns):
        mismatches.append(f"column {col!r} is both mapped and declared unpersisted")

    # (D) an unpersisted column must be omissible: nullable or server-defaulted.
    for col, reason in pair.unpersisted_columns.items():
        meta = columns.get(col)
        if meta and not (meta["nullable"] or meta["has_default"]):
            mismatches.append(
                f"column {col!r} is NOT NULL with no default but no field fills it "
                f"(declared unpersisted: {reason}) — this row could never be inserted"
            )

    # (E) + (F) type and nullability agreement on every mapped field ↔ column.
    for field_name, col in pair.fields.items():
        meta = columns.get(col)
        if meta is None:
            continue  # already reported in (C)
        hint = hints.get(field_name, object)
        sql_type = str(meta["data_type"])
        if not _type_is_compatible(hint, sql_type):
            mismatches.append(f"type mismatch {field_name!r} ({hint!r}) ↔ {col!r} ({sql_type})")
        can_be_none = _field_can_be_none(hint)
        # A field that may be None must map to a nullable column, or the None could
        # not be stored.
        if can_be_none and not meta["nullable"]:
            mismatches.append(
                f"nullability mismatch: field {field_name!r} may be None but column "
                f"{col!r} is NOT NULL"
            )
        # A NOT NULL column with no default must be fed by a field that can never be
        # None (required, or defaulted to a non-None value).
        if not meta["nullable"] and not meta["has_default"]:
            if can_be_none:
                mismatches.append(
                    f"nullability mismatch: column {col!r} is NOT NULL with no default "
                    f"but field {field_name!r} may be None"
                )
            # else: a required non-optional field, or one defaulted to a non-None
            # value (e.g. severity="notable", confidence="probable"), is fine.

    assert mismatches == [], (
        f"{pair.name}: {len(mismatches)} DDL↔dataclass mismatch(es):\n  " + "\n  ".join(mismatches)
    )
