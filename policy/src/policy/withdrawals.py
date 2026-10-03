# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Publication withdrawals — the committed, engineered suppression list
(P34.19, F-337; SIG-GOV-007).

Some records must leave every public artifact even though the evidence that
produced them is real — the ``wired_shotspotter_leak`` precedent under
SIG-PUB-005 (leak-provenance refusals) is the standing example, and P34.19's
F-337 finding adds nine Atlas face-recognition rows citing the BuzzFeed News
Clearview article whose agency data came from unnamed-source internal
documents.

The list is **data, not code**
(:mod:`policy.data.publication_withdrawals`), mirrors the append-only
``publication_disposition`` registry it rides on the spine (SIG-GOV-007), and
is matched by every public-artifact layer (export writer, API read surface,
web export-mode readers). Matching is fail-closed: ``candidate_claim_ids``
suppress alongside ``claim_ids`` until a host-side rerun narrows them.
"""

from __future__ import annotations

from typing import Any

from policy._data import load_json_table

#: The data table schema this module reads.
WITHDRAWALS_SCHEMA = "sig.publication-withdrawals/1"


def publication_withdrawals() -> dict[str, Any]:
    """The full ``sig.publication-withdrawals/1`` table."""
    table = load_json_table("publication_withdrawals")
    if table.get("schema") != WITHDRAWALS_SCHEMA:
        raise ValueError(
            f"publication_withdrawals table schema {table.get('schema')!r} "
            f"!= {WITHDRAWALS_SCHEMA!r}"
        )
    return table


def withdrawal_entries() -> list[dict[str, Any]]:
    """The withdrawal entries, in table order (append-only)."""
    return list(publication_withdrawals()["withdrawals"])


def _claim_target_ids(entry: dict[str, Any]) -> set[str]:
    return set(entry.get("claim_ids", [])) | set(entry.get("candidate_claim_ids", []))


def _target_ids(entry: dict[str, Any]) -> set[str]:
    ids: set[str] = {entry["entity_id"], entry["upstream_id"]}
    ids.update(_claim_target_ids(entry))
    return ids


def withdrawn_ids() -> set[str]:
    """Every id any committed withdrawal suppresses (fail-closed)."""
    out: set[str] = set()
    for entry in withdrawal_entries():
        out.update(_target_ids(entry))
    return out


def withdrawn_claim_ids() -> set[str]:
    """The claim ids suppressed (``claim_ids`` + ``candidate_claim_ids``)."""
    out: set[str] = set()
    for entry in withdrawal_entries():
        out.update(_claim_target_ids(entry))
    return out


def withdrawn_entity_ids() -> set[str]:
    """The subject-entity ids whose claims are suppressed."""
    return {entry["entity_id"] for entry in withdrawal_entries()}


def withdrawn_upstream_ids() -> set[str]:
    """The upstream record ids (e.g. Atlas ``AOS*``) suppressed."""
    return {entry["upstream_id"] for entry in withdrawal_entries()}


def is_withdrawn(target_id: str) -> bool:
    """Whether ``target_id`` (claim, entity or upstream id) is suppressed."""
    return target_id in withdrawn_ids()


def withdrawal_for(target_id: str) -> dict[str, Any] | None:
    """The first withdrawal entry suppressing ``target_id``, or ``None``."""
    for entry in withdrawal_entries():
        if target_id in _target_ids(entry):
            return entry
    return None


def withdrawal_for_claim(claim_id: str) -> dict[str, Any] | None:
    """The first withdrawal entry suppressing claim ``claim_id``, or ``None``."""
    for entry in withdrawal_entries():
        if claim_id in _claim_target_ids(entry):
            return entry
    return None


def withdrawal_for_entity(entity_id: str) -> dict[str, Any] | None:
    """The first withdrawal entry suppressing entity ``entity_id``, or ``None``."""
    for entry in withdrawal_entries():
        if entity_id == entry["entity_id"]:
            return entry
    return None
