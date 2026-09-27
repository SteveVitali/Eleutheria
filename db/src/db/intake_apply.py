# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The reviewed-correction application bridge (P32.16a / SIG-FIND-008, ADR-135).

The restricted path that applies a *reviewed, explicitly approved* intake
proposal through the CANONICAL S1 disposition machinery — never a parallel
write. One ``apply`` transaction lands, atomically:

1. the canonical record of the outcome —
   * ``correct``: the §16.6/SIG-STORE-020 correction pair (close the old
     claim's ``sys_period`` — the only update the append-only guard permits —
     and INSERT a new claim carrying ``revises_claim`` + ``correction_reason``
     + the approving curator's ``asserted_by`` entity);
   * ``annotate``: a non-superseding claim on the same subject asserting the
     proposed predicate/value (``derived_from_claim_ids`` links the target);
   * ``suppress``: one ``publication_disposition`` row (``withhold`` or, when
     the proposal narrows it, ``restrict``) via
     :func:`db.dispositions.record_disposition`;
   * ``delete``: one ``withdraw`` disposition — the strongest NON-destructive
     gate the canonical registry offers. Byte-level deletion stays the
     separately gated two-person process (SIG-GOV-008); this bridge never
     deletes;
   * ``refuse`` never reaches the bridge — denial writes nothing canonical;
2. the ``intake.application`` applied-receipt row — ``UNIQUE(operation_id)``
   is the exactly-once barrier;
3. the ``applied`` lifecycle event — appendable only under the bridge role
   (the writer guard re-deployed by ``intake_application_bridge``).

A crash before commit leaves nothing; a crash after commit reconciles by
``operation_id`` lookup — a retry returns the committed receipt instead of
re-applying (``reconciled: true``). A concurrent loser blocks on the unique
key, then reconciles to the winner's committed row. Reporter text is never
applied: the bridge reads only the report's *structural* fields
(``claim_ids`` anchors which disputed records a proposal may target); the
asserted value comes solely from the curator-authored, approved proposal.

Runs under ``SET [LOCAL] ROLE sig_intake_bridge`` — the third least-privilege
intake role. ``PgIntakeApplicationStore.from_dsn`` sets the session role like
the receiver/reviewer stores; ``apply``/``mark_published`` also issue
``SET LOCAL ROLE`` inside their transaction so a shared privileged
connection still executes under the bridge's grants and the writer guard
sees the role.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)
from psycopg import sql
from psycopg.rows import dict_row, tuple_row
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from policy import intake as pint

from .claim_sink import content_digest
from .dispositions import DISPOSITION_TABLE, record_disposition
from .identity_guard import CURATOR_HANDLE_SCHEME, resolve_identities

__all__ = [
    "APPLYABLE_OUTCOMES",
    "BRIDGE_ACTOR_RE",
    "BRIDGE_CONNECTOR",
    "BRIDGE_ROLE",
    "IntakeApplicationStore",
    "IntakeApplyError",
    "PgIntakeApplicationStore",
    "claim_evidence_digest",
    "claim_state_digest",
    "derive_operation_id",
]

BRIDGE_ROLE = "sig_intake_bridge"
#: The ingest_run identity the bridge stamps on the claims it asserts.
BRIDGE_CONNECTOR = "sig.intake.bridge"
BRIDGE_CONNECTOR_VERSION = "intake-bridge/1"
#: Actor values are the contributor tier's pseudonymous handles (SIG-CONTRIB-006).
BRIDGE_ACTOR_RE = re.compile(r"^[a-z0-9_.-]{2,64}$")
#: Outcomes the bridge may apply; ``refuse`` is a real disposition that needs
#: no canonical write — a refusal closes through the normal reviewer event.
APPLYABLE_OUTCOMES = frozenset({"correct", "annotate", "suppress", "delete"})

_LIFECYCLE_EVENTS = frozenset(
    {
        "received",
        "triaged",
        "assigned",
        "review_requested",
        "disposition_proposed",
        "disposition_approved",
        "applied",
        "published",
        "closed",
    }
)

#: Claim value columns a proposal may populate, per predicate object_type —
#: (required, optional). ``geometry``/``value_geom`` is deliberately absent:
#: spatial corrections are outside this bridge's first scope (fail closed).
_OBJECT_VALUE_RULES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "literal": (frozenset({"value_text"}), frozenset({"unit"})),
    "quantity": (frozenset({"value_num", "value_text"}), frozenset({"unit"})),
    "money": (frozenset({"value_json", "value_text"}), frozenset({"unit"})),
    "duration": (frozenset({"value_json", "value_text"}), frozenset()),
    "interval": (frozenset({"value_json", "value_text"}), frozenset()),
    "vocab_term": (frozenset({"value_text"}), frozenset()),
    "entity_ref": (frozenset({"object_entity", "value_text"}), frozenset()),
    "document_ref": (frozenset({"value_json", "value_text"}), frozenset()),
}

#: Column → INSERT cast fragment for the correction claim insert (typed params
#: avoid unknown-type binding surprises; mirrors the sink's casts).
_CLAIM_CASTS: dict[str, str] = {
    "subject_id": "%s::uuid",
    "predicate_id": "%s",
    "object_entity": "%s::uuid",
    "object_type": "%s",
    "value_kind": "%s::value_kind",
    "value_text": "%s",
    "value_num": "%s",
    "value_bool": "%s",
    "value_json": "%s",
    "unit": "%s",
    "value_geom": "%s::geometry",
    "raw_value": "%s",
    "raw_context": "%s",
    "normalization_id": "%s",
    "normalization_version": "%s",
    "valid_period": "%s::tstzrange",
    "valid_edtf": "%s",
    "valid_from_kind": "%s",
    "valid_to_kind": "%s",
    "observed_at": "%s",
    "observed_edtf": "%s",
    "observed_at_kind": "%s",
    "observed_unknown_reason": "%s",
    "source_reliability": "%s",
    "reliability_provisional": "%s",
    "claim_directness": "%s",
    "artifact_integrity": "%s",
    "legacy_source_tier": "%s",
    "claim_polarity": "%s",
    "rank": "%s::claim_rank",
    "review_status": "%s::review_status",
    "extraction_id": "%s::uuid",
    "asserted_by": "%s::uuid",
    "assertion_rationale": "%s",
    "derived_from_claim_ids": "%s::uuid[]",
    "revises_claim": "%s::uuid",
    "retraction_of": "%s::uuid",
    "correction_reason": "%s",
    "ingest_run_id": "%s::uuid",
    "rights_id": "%s::uuid",
    "sensitivity_tier": "%s::smallint",
    "content_digest": "%s",
    "assertion_map_id": "%s",
    "assertion_map_basis": "%s",
}


class IntakeApplyError(Exception):
    """A refused application — no graph mutation, ever.

    ``code`` is a bounded, safe reason the API may echo; raw payload content
    is never part of it.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IntakeApplicationStore(Protocol):
    """The bridge's data contract (PG + the in-memory test double)."""

    def apply(
        self, receipt_id: str, *, actor: str, operation_id: str | None = None
    ) -> dict[str, Any]:
        """Apply the currently-approved proposal; idempotent by operation_id."""
        ...

    def mark_published(
        self,
        receipt_id: str,
        *,
        actor: str,
        publication_id: str | None = None,
        correction_ref: str | None = None,
        tombstone: str | None = None,
    ) -> dict[str, Any]:
        """Record the post-publication linkage (release identity or tombstone)."""
        ...

    def application(self, receipt_id: str) -> dict[str, Any] | None:
        """The applied receipt for a report, else ``None``."""
        ...

    def close(self) -> None: ...


# --------------------------------------------------------------------------- #
# Shared fingerprints — the SAME definitions the proposal-building tooling must
# use, so the apply-time recompute proves the record the reviewer saw is the
# record still on the spine.
# --------------------------------------------------------------------------- #
def claim_state_digest(claim_row: dict[str, Any]) -> str:
    """The proposal's ``claim_digest``: the content digest over the claim row's
    deterministic payload (``claim_id``/``sys_period``/``recorded_at``
    excluded — the same rule as :func:`db.claim_sink.content_digest`)."""
    return content_digest(claim_row)


def claim_evidence_digest(rows: Any) -> str:
    """The proposal's ``evidence_digest``: sha256 over the ordered
    ``claim_evidence`` binding set ``(capture_id, role, binding_status)`` —
    any bind drift changes it."""
    items: list[tuple[str, str, str]] = []
    for r in rows:
        if isinstance(r, dict):
            items.append(
                (
                    str(r["capture_id"]),
                    str(r["role"]),
                    "" if r.get("binding_status") is None else str(r["binding_status"]),
                )
            )
        else:
            items.append(
                (
                    str(r[0]),
                    str(r[1]),
                    "" if len(r) < 3 or r[2] is None else str(r[2]),
                )
            )
    items.sort()
    return hashlib.sha256(json.dumps(items, separators=(",", ":")).encode("utf-8")).hexdigest()


def derive_operation_id(report_id: str, approval_seq: int, outcome: str) -> str:
    """The deterministic operation id — the same approval on the same report
    re-derives the same key after any restart, so a retried apply reconciles
    instead of re-applying."""
    op = uuid.uuid5(uuid.NAMESPACE_URL, f"sig-intake-apply:{report_id}:{approval_seq}:{outcome}")
    return f"op-{op}"


def _evidence_rows(conn: Any, claim_id: str) -> list[Any]:
    # Rows go to claim_evidence_digest verbatim — it reads dict rows by name
    # and tuple rows positionally in exactly this SELECT order.
    return list(
        conn.execute(
            "SELECT capture_id::text, role, binding_status FROM claim_evidence"
            " WHERE claim_id = %s::uuid ORDER BY capture_id, role",
            (claim_id,),
        ).fetchall()
    )


def _parse_ts(value: Any) -> datetime:
    ts = datetime.fromisoformat(str(value))
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


def _raw_literal(value: dict[str, Any]) -> str:
    """The claim's ``raw_value`` — the source-literal string the reviewer
    asserted. ``value_text`` is required by every bridged object type today,
    but if the rules ever admit a text-less shape the stored literal is still
    honest (typed scalar → str; structured → compact JSON), never a KeyError
    or a fabricated string."""
    for key in ("value_text", "value_num", "value_bool", "object_entity"):
        v = value.get(key)
        if v is not None:
            return v if isinstance(v, str) else str(v)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class PgIntakeApplicationStore:
    """The bridge store — least-privilege canonical writer (``sig_intake_bridge``)."""

    def __init__(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self._conn = conn

    @classmethod
    def from_dsn(cls, dsn: str) -> PgIntakeApplicationStore:
        conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(BRIDGE_ROLE)))
        return cls(conn)

    # -- helpers ------------------------------------------------------------ #
    @staticmethod
    def _check_actor(actor: str) -> None:
        if BRIDGE_ACTOR_RE.fullmatch(actor or "") is None:
            raise IntakeApplyError("bad_actor", "an attributable curator handle is required")

    def _report_for_update(
        self, receipt_id: str, *, allow_expunged: bool = False
    ) -> dict[str, Any]:
        # Serialize concurrent applies (and publish-linkage) on one report:
        # the loser waits on the advisory lock, then its subsequent reads see
        # the winner's committed application row and reconcile instead of
        # re-applying. A `SELECT … FOR UPDATE` would be wrong twice over —
        # the bridge role deliberately has NO UPDATE grant on the immutable
        # report table, and the advisory lock serializes apply+publish
        # together (two FOR UPDATE waits would not interlock with publish).
        self._conn.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"sig-intake-apply:{receipt_id}",),
        )
        row = self._conn.execute(
            "SELECT report_id, receipt_id, category, claim_ids, expunged_at"
            " FROM intake.report WHERE receipt_id = %s",
            (receipt_id,),
        ).fetchone()
        if row is None:
            raise IntakeApplyError("unknown_receipt", "unknown receipt")
        if row["expunged_at"] is not None and not allow_expunged:
            raise IntakeApplyError("report_expunged", "the report's payloads were expunged")
        return dict(row)

    def _events(self, report_id: str) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT event_seq, event, actor, at, detail FROM intake.event"
                " WHERE report_id = %s ORDER BY event_seq",
                (report_id,),
            ).fetchall()
        ]

    @staticmethod
    def _latest_lifecycle(events: list[dict[str, Any]]) -> dict[str, Any] | None:
        for e in reversed(events):
            if e["event"] in _LIFECYCLE_EVENTS:
                return e
        return None

    def _approval(
        self, report: dict[str, Any], events: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Validate the explicit-approval authority record; returns
        (approval event, proposal event, outcome)."""
        latest = self._latest_lifecycle(events)
        if latest is None or latest["event"] != "disposition_approved":
            raise IntakeApplyError(
                "no_current_approval",
                "the latest lifecycle event is not an approval — "
                "explicit approval is required before applying",
            )
        approval = latest
        detail = approval["detail"] or {}
        outcome = str(detail.get("outcome") or "")
        if outcome not in APPLYABLE_OUTCOMES:
            raise IntakeApplyError(
                "outcome_not_appliable",
                f"outcome {outcome!r} does not apply through the bridge "
                "(a refusal closes through the reviewer event path — "
                "denial never mutates the graph)",
            )
        seq = detail.get("approves_seq")
        proposal = next(
            (
                e
                for e in events
                if seq is not None
                and int(e["event_seq"]) == int(seq)
                and e["event"] == "disposition_proposed"
            ),
            None,
        )
        if proposal is None:
            raise IntakeApplyError(
                "approval_without_proposal",
                "the approval does not name a live disposition_proposed",
            )
        p_outcome = str((proposal["detail"] or {}).get("outcome") or "")
        if p_outcome != outcome:
            raise IntakeApplyError(
                "outcome_mismatch",
                "the approved outcome does not match the proposal's",
            )
        if not isinstance((proposal["detail"] or {}).get("proposal"), dict):
            raise IntakeApplyError(
                "proposal_missing", "the approved proposal carries no proposal payload"
            )
        return approval, proposal, outcome

    def _reconcile(
        self, report_id: str, approval_seq: int, outcome: str, operation_id: str
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT application_id, report_id, operation_id, approval_seq,"
            " proposal_seq, outcome, approved_by, applied_by, target_kind,"
            " target_claim_id, target_id, result_claim_id, disposition_id,"
            " ingest_run_id, detail, applied_at"
            " FROM intake.application WHERE operation_id = %s",
            (operation_id,),
        ).fetchone()
        if row is None:
            return None
        app = dict(row)
        if (
            str(app["report_id"]) != report_id
            or int(app["approval_seq"]) != int(approval_seq)
            or app["outcome"] != outcome
        ):
            raise IntakeApplyError(
                "operation_id_conflict",
                "operation_id already names a different application — reconcile, never overwrite",
            )
        return app

    def _mint_run(
        self,
        report: dict[str, Any],
        outcome: str,
        approval_seq: int,
        proposal_seq: int,
        operation_id: str,
        vocab_version: str,
        input_digests: list[str],
    ) -> str:
        env = {k: v for k in ("TZ", "LC_ALL") if (v := os.environ.get(k))}
        row = self._conn.execute(
            "INSERT INTO ingest_run(connector_name, connector_version, code_commit,"
            " ruleset_version, vocab_version, parameters, environment, input_digests,"
            " status, finished_at) "
            "VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::text[],'succeeded',clock_timestamp())"
            " RETURNING run_id::text",
            (
                BRIDGE_CONNECTOR,
                BRIDGE_CONNECTOR_VERSION,
                os.environ.get("SIG_CODE_COMMIT", "unknown"),
                pint.contract_version(),
                vocab_version,
                json.dumps(
                    {
                        "operation_id": operation_id,
                        "report_id": str(report["report_id"]),
                        "receipt_id": report["receipt_id"],
                        "category": report["category"],
                        "approval_seq": int(approval_seq),
                        "proposal_seq": int(proposal_seq),
                        "outcome": outcome,
                    }
                ),
                json.dumps(env),
                [d for d in input_digests if d],
            ),
        ).fetchone()
        assert row is not None
        return str(row["run_id"])

    def _curator_entity(self, handle: str) -> str:
        """The approving curator's ONE person entity (§11.3 attributable
        curators) — minted/adopted under the ADR-110 guard, never a
        check-then-insert race. The guard reads rows positionally, so it runs
        on a tuple-row cursor over the SAME connection/transaction."""
        with self._conn.cursor(row_factory=tuple_row) as cur:
            res = resolve_identities(cur, CURATOR_HANDLE_SCHEME, [handle], entity_type="person")
        return res.entity_by_value[handle]

    def _predicate_row(self, predicate_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT predicate_id, object_type, vocab_version FROM vocab_predicate"
            " WHERE predicate_id = %s AND deprecated_at IS NULL",
            (predicate_id,),
        ).fetchone()
        if row is None:
            raise IntakeApplyError(
                "unknown_predicate",
                f"predicate {predicate_id!r} is not live in the registry",
            )
        return dict(row)

    # -- the correction path (correct | annotate) --------------------------- #
    def _claim_for_target(self, report: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        claim_id = str(proposal["target_id"]).lower()
        cited = {str(c).lower() for c in (report["claim_ids"] or [])}
        if claim_id not in cited:
            raise IntakeApplyError(
                "target_not_reported",
                "the proposal targets a claim the report did not dispute — "
                "the bridge applies only what the reporter flagged",
            )
        row = self._conn.execute(
            "SELECT * FROM claim WHERE claim_id = %s::uuid", (claim_id,)
        ).fetchone()
        if row is None:
            raise IntakeApplyError("target_missing", "the target claim does not exist")
        claim = dict(row)
        if not claim["sys_period"].upper_inf:
            raise IntakeApplyError(
                "stale_record",
                "the target claim's belief window is already closed — "
                "a correction may not revise superseded history",
            )
        # The reviewer pinned the row state they reviewed; the recompute must
        # agree byte-for-byte or the proposal is stale/changed.
        if claim_state_digest(claim) != proposal["claim_digest"]:
            raise IntakeApplyError(
                "record_changed",
                "the claim no longer matches the reviewed fingerprint",
            )
        if (
            claim_evidence_digest(_evidence_rows(self._conn, claim_id))
            != proposal["evidence_digest"]
        ):
            raise IntakeApplyError(
                "evidence_changed",
                "the claim's bound evidence changed since the proposal",
            )
        if int(claim["sensitivity_tier"]) != 0:
            raise IntakeApplyError(
                "restricted_target",
                "the bridge's public lane corrects only tier-0 claims — "
                "a restricted claim needs its own gated path",
            )
        # Current rights policy: the inherited rights record must still permit
        # public representation — a correction never upgrades a rights posture.
        rights = self._conn.execute(
            "SELECT redistributable FROM rights_record WHERE rights_id = %s::uuid",
            (str(claim["rights_id"]),),
        ).fetchone()
        if rights is None or str(rights["redistributable"]) != "yes":
            raise IntakeApplyError(
                "rights_denied",
                "the target's rights record does not permit public "
                "representation — correcting it is a gated rights decision",
            )
        # Current disposition policy: a claim already denied is outside the
        # bridge's public correction lane (dict_row-safe direct read).
        denying = self._conn.execute(
            "SELECT disposition::text AS d FROM publication_disposition"
            " WHERE target_kind = 'claim' AND target_id = %s"
            "   AND decided_at <= clock_timestamp()"
            " ORDER BY decided_at DESC, disposition_seq DESC LIMIT 1",
            (claim_id,),
        ).fetchone()
        if denying is not None and str(denying["d"]) in {
            "withhold",
            "restrict",
            "withdraw",
        }:
            raise IntakeApplyError(
                "target_denied",
                "the target is under a current denying disposition — "
                "correcting withdrawn material is a separate gated workflow",
            )
        return claim

    def _value_columns(self, object_type: str, value: dict[str, Any]) -> dict[str, Any]:
        rules = _OBJECT_VALUE_RULES.get(object_type)
        if rules is None:
            raise IntakeApplyError(
                "unsupported_value_type",
                f"object_type {object_type!r} corrections are outside the bridge's scope",
            )
        required, optional = rules
        present = {k for k, v in value.items() if v is not None}
        if not required <= present:
            raise IntakeApplyError(
                "value_shape_mismatch",
                f"object_type {object_type!r} requires value columns {sorted(required)}",
            )
        extra = present - (required | optional)
        if extra:
            raise IntakeApplyError(
                "value_shape_mismatch",
                f"object_type {object_type!r} does not admit {sorted(extra)}",
            )
        return {k: value[k] for k in present}

    @staticmethod
    def _screen_value(value: dict[str, Any]) -> None:
        for key, val in value.items():
            if isinstance(val, str) and pint.screen_part_viii(val) is not None:
                raise IntakeApplyError(
                    "unsafe_payload",
                    "the proposed value matches the Part VIII refusal screen",
                )
            if key == "value_json" and pint.screen_part_viii(json.dumps(val)) is not None:
                raise IntakeApplyError(
                    "unsafe_payload",
                    "the proposed value matches the Part VIII refusal screen",
                )

    def _insert_correction_claim(
        self,
        *,
        old: dict[str, Any],
        outcome: str,
        proposal: dict[str, Any],
        predicate_id: str,
        object_type: str,
        value: dict[str, Any],
        asserted_by: str,
        rationale: str,
        run_id: str,
    ) -> str:
        """The §16.6 new-assertion row — inherits the old claim's whole
        epistemic/rights/sensitivity posture; the correction changes only what
        the approved proposal names. For `annotate` the predicate/object shape
        comes from the proposal, never silently from the target."""
        scope = proposal.get("scope") or {}
        valid_period = old["valid_period"]
        if scope.get("valid_from") is not None or scope.get("valid_to") is not None:
            valid_period = Range(
                _parse_ts(scope["valid_from"]) if scope.get("valid_from") else None,
                _parse_ts(scope["valid_to"]) if scope.get("valid_to") else None,
                bounds="[)",
            )
        observed_at = old["observed_at"]
        if scope.get("observed_at") is not None:
            observed_at = _parse_ts(scope["observed_at"])
        raw_context = old["raw_context"]
        if scope.get("raw_context") is not None:
            raw_context = scope["raw_context"]
        inherit = outcome == "correct"

        # Plain-JSON payload (no Jsonb wrappers) so the stored content_digest
        # is a deterministic sha256 over the assertion — never a repr.
        payload: dict[str, Any] = {
            "subject_id": str(old["subject_id"]),
            "predicate_id": predicate_id,
            "object_entity": value.get("object_entity")
            or (str(old["object_entity"]) if inherit and old["object_entity"] else None),
            "object_type": object_type,
            "value_kind": "value",
            "value_text": value.get("value_text"),
            "value_num": value.get("value_num"),
            "value_bool": value.get("value_bool"),
            "value_json": value.get("value_json"),
            "unit": value.get("unit") or (old["unit"] if inherit else None),
            "value_geom": old["value_geom"] if inherit else None,
            "raw_value": _raw_literal(value),
            "raw_context": raw_context,
            "normalization_id": old["normalization_id"] if inherit else None,
            "normalization_version": old["normalization_version"] if inherit else None,
            "valid_period": valid_period,
            "valid_edtf": old["valid_edtf"],
            "valid_from_kind": old["valid_from_kind"],
            "valid_to_kind": old["valid_to_kind"],
            "observed_at": observed_at,
            "observed_edtf": old["observed_edtf"],
            "observed_at_kind": old["observed_at_kind"],
            "observed_unknown_reason": old["observed_unknown_reason"],
            "source_reliability": old["source_reliability"],
            "reliability_provisional": old["reliability_provisional"],
            "claim_directness": old["claim_directness"],
            "artifact_integrity": old["artifact_integrity"],
            "legacy_source_tier": old["legacy_source_tier"],
            "claim_polarity": old["claim_polarity"],
            "rank": old["rank"],
            "review_status": old["review_status"],
            "extraction_id": None,  # human-asserted origin — the asserted_by path
            "asserted_by": asserted_by,
            "assertion_rationale": rationale,
            "derived_from_claim_ids": (
                [str(old["claim_id"])] if outcome == "annotate" else old["derived_from_claim_ids"]
            ),
            "revises_claim": str(old["claim_id"]) if outcome == "correct" else None,
            "retraction_of": None,
            "correction_reason": (
                str(proposal.get("correction_reason") or rationale)
                if outcome == "correct"
                else (
                    str(proposal["correction_reason"])
                    if proposal.get("correction_reason") is not None
                    else None
                )
            ),
            "ingest_run_id": run_id,
            "rights_id": str(old["rights_id"]),
            "sensitivity_tier": int(old["sensitivity_tier"]),
            "assertion_map_id": None,
            "assertion_map_basis": None,
        }
        payload["content_digest"] = claim_state_digest(payload)
        cols = list(payload)
        params = []
        for c in cols:
            v = payload[c]
            if c in ("value_json", "raw_context") and v is not None:
                v = Jsonb(v)
            params.append(v)
        row = self._conn.execute(
            f"INSERT INTO claim({', '.join(cols)}) "
            f"VALUES ({', '.join(_CLAIM_CASTS[c] for c in cols)})"
            " RETURNING claim_id::text",
            tuple(params),
        ).fetchone()
        assert row is not None
        return str(row["claim_id"])

    def _rebind_evidence(self, old_claim_id: str, new_claim_id: str) -> int:
        """Re-bind the SAME captures to the new assertion — the corrected
        reading stands on the same evidence; each binding's own provenance
        (extraction version, binding instant, status) is preserved."""
        cur = self._conn.execute(
            "INSERT INTO claim_evidence"
            "(claim_id, capture_id, extraction_id, role, locator, excerpt,"
            " weight_note, extraction_config_digest, extractor_version,"
            " binding_status, bound_at) "
            "SELECT %s::uuid, capture_id, extraction_id, role, locator, excerpt,"
            " weight_note, extraction_config_digest, extractor_version,"
            " binding_status, bound_at "
            "FROM claim_evidence WHERE claim_id = %s::uuid",
            (new_claim_id, old_claim_id),
        )
        return cur.rowcount or 0

    def _apply_correction(
        self,
        report: dict[str, Any],
        outcome: str,
        proposal: dict[str, Any],
        approval: dict[str, Any],
        proposal_seq: int,
        operation_id: str,
    ) -> tuple[str, str, str]:
        """Validate then write the correction/annotation claim pair."""
        old = self._claim_for_target(report, proposal)
        pred = self._predicate_row(str(proposal.get("predicate_id") or old["predicate_id"]))
        if outcome == "correct" and pred["predicate_id"] != old["predicate_id"]:
            raise IntakeApplyError(
                "predicate_mismatch",
                "a correct outcome keeps the disputed claim's predicate",
            )
        # `correct` validates the value against the claim's own object_type;
        # `annotate` against the *proposed* predicate's object_type (an
        # annotation may carry a different predicate than its target's).
        object_type = str(old["object_type"]) if outcome == "correct" else str(pred["object_type"])
        insert_predicate = pred["predicate_id"]
        value = self._value_columns(object_type, proposal["value"])
        self._screen_value(value)
        # The approving curator asserts the correction (§11.3 attributable
        # curator), never the reporter's free text.
        approver = str(approval["actor"])
        curator_entity = self._curator_entity(approver)
        reason = str((approval["detail"] or {}).get("reason") or "intake correction")
        run_id = self._mint_run(
            report,
            outcome,
            int(approval["event_seq"]),
            proposal_seq,
            operation_id,
            str(pred["vocab_version"]),
            [proposal.get("claim_digest") or "", proposal.get("evidence_digest") or ""],
        )
        if outcome == "correct":
            # §16.6 step 1 — close prior belief (the only permitted UPDATE;
            # a concurrent close makes this a no-row update → stale, not double).
            closed = self._conn.execute(
                "UPDATE claim SET sys_period = tstzrange(lower(sys_period),"
                " clock_timestamp(), '[)') WHERE claim_id = %s::uuid"
                " AND upper_inf(sys_period)",
                (str(old["claim_id"]),),
            ).rowcount
            if closed != 1:
                raise IntakeApplyError(
                    "stale_record",
                    "the target claim closed concurrently — reconcile, never re-close",
                )
        new_claim_id = self._insert_correction_claim(
            old=old,
            outcome=outcome,
            proposal=proposal,
            predicate_id=insert_predicate,
            object_type=object_type,
            value=value,
            asserted_by=curator_entity,
            rationale=reason,
            run_id=run_id,
        )
        self._rebind_evidence(str(old["claim_id"]), new_claim_id)
        return new_claim_id, str(old["claim_id"]), run_id

    # -- the suppression path (suppress | delete) --------------------------- #
    def _apply_suppression(
        self,
        report: dict[str, Any],
        outcome: str,
        proposal: dict[str, Any],
        approval: dict[str, Any],
    ) -> tuple[str, str | None, str | None]:
        kind = str(proposal["target_kind"])
        target_id = str(proposal["target_id"])
        cited = {str(c).lower() for c in (report["claim_ids"] or [])}
        target_claim_id: str | None = None
        if kind == "claim":
            if target_id.lower() not in cited:
                raise IntakeApplyError(
                    "target_not_reported",
                    "the suppression targets a claim the report did not flag",
                )
            row = self._conn.execute(
                "SELECT * FROM claim WHERE claim_id = %s::uuid", (target_id,)
            ).fetchone()
            if row is None:
                raise IntakeApplyError("target_missing", "the target claim does not exist")
            claim = dict(row)
            target_claim_id = target_id
            # Optional staleness pins — recorded by the reviewer, verified now.
            if (
                proposal.get("claim_digest")
                and claim_state_digest(claim) != proposal["claim_digest"]
            ):
                raise IntakeApplyError("record_changed", "claim fingerprint drifted")
            if (
                proposal.get("evidence_digest")
                and claim_evidence_digest(_evidence_rows(self._conn, target_id))
                != proposal["evidence_digest"]
            ):
                raise IntakeApplyError("evidence_changed", "evidence bindings drifted")
        elif kind == "entity":
            exists = self._conn.execute(
                "SELECT 1 FROM entity WHERE entity_id = %s::uuid", (target_id,)
            ).fetchone()
            if exists is None:
                raise IntakeApplyError("target_missing", "the target entity does not exist")
        # artifact/release_artifact targets have no spine row — the namespace /
        # key shape is validated at proposal time; the disposition row is the
        # gate every access path honours.

        disposition = (
            Disposition.WITHDRAW
            if outcome == "delete"
            else Disposition(str(proposal.get("disposition") or "withhold"))
        )
        reason_category = ReasonCategory(str(proposal["reason_category"]))
        approver = str(approval["actor"])
        reason = str((approval["detail"] or {}).get("reason") or outcome)
        latest = self._conn.execute(
            f"SELECT disposition_id::text FROM {DISPOSITION_TABLE}"
            " WHERE target_kind = %s AND target_id = %s"
            " ORDER BY decided_at DESC, disposition_seq DESC LIMIT 1",
            (kind, target_id),
        ).fetchone()
        record = new_disposition(
            target_kind=TargetKind(kind),
            target_id=target_id,
            disposition=disposition,
            reason_category=reason_category,
            authority=f"intake:approval:{approval['event_seq']}",
            decided_by=approver,
            rationale=reason,
            supersedes=None if latest is None else str(latest["disposition_id"]),
        )
        disposition_id = record_disposition(self._conn, record)
        return disposition_id, (target_id if kind != "claim" else None), target_claim_id

    # -- public contract ---------------------------------------------------- #
    def apply(
        self, receipt_id: str, *, actor: str, operation_id: str | None = None
    ) -> dict[str, Any]:
        """Apply the currently-approved proposal — atomic, idempotent.

        Returns the applied receipt. A retry (after a crash or an uncertain
        commit) reconciles by ``operation_id`` and returns the committed row —
        ``reconciled`` distinguishes replay from fresh application.
        """
        self._check_actor(actor)
        op_id = operation_id
        try:
            with self._conn.transaction():
                self._conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(BRIDGE_ROLE)))
                report = self._report_for_update(receipt_id)
                report_id = str(report["report_id"])
                events = self._events(report_id)
                latest = self._latest_lifecycle(events)
                # Retry-after-commit: the apply transaction writes the
                # application row AND the `applied` lifecycle event
                # atomically, so an `applied`-latest report has exactly one
                # outstanding operation — reconcile to its committed receipt.
                # (A superseded approval goes through re-proposal → re-approval
                # → `disposition_approved` again and derives a NEW
                # operation_id, so it never reaches this branch.)
                if latest is not None and latest["event"] == "applied":
                    app_row = self._conn.execute(
                        "SELECT application_id, report_id, operation_id, approval_seq,"
                        " proposal_seq, outcome, approved_by, applied_by, target_kind,"
                        " target_claim_id, target_id, result_claim_id, disposition_id,"
                        " ingest_run_id, detail, applied_at"
                        " FROM intake.application WHERE report_id = %s"
                        " ORDER BY applied_at DESC, application_id DESC LIMIT 1",
                        (report_id,),
                    ).fetchone()
                    if app_row is not None:
                        if op_id is not None and op_id != app_row["operation_id"]:
                            raise IntakeApplyError(
                                "operation_id_conflict",
                                "operation_id names a different application — "
                                "reconcile, never overwrite",
                            )
                        return self._result(receipt_id, dict(app_row), reconciled=True)

                approval, proposal_event, outcome = self._approval(report, events)
                if op_id is None:
                    op_id = derive_operation_id(report_id, int(approval["event_seq"]), outcome)
                if re.fullmatch(r"[A-Za-z0-9_:.=-]{8,128}", op_id) is None:
                    raise IntakeApplyError(
                        "bad_operation_id", "operation_id must be an 8–128 char token"
                    )
                # A committed application under THIS operation id is a retry
                # (caller-supplied id or a still-unflushed earlier commit);
                # an id naming a DIFFERENT report/approval/outcome conflicts.
                prior = self._reconcile(report_id, int(approval["event_seq"]), outcome, op_id)
                if prior is not None:
                    return self._result(receipt_id, prior, reconciled=True)
                try:
                    proposal = pint.validate_proposal(
                        outcome, (proposal_event["detail"] or {})["proposal"]
                    )
                except pint.IntakeFieldError as exc:
                    raise IntakeApplyError(
                        "invalid_proposal",
                        f"the stored proposal fails validation ({exc})",
                    ) from exc

                result_claim_id: str | None = None
                disposition_id: str | None = None
                target_claim_id: str | None = None
                target_id: str | None = None
                run_id: str | None = None
                if outcome in ("correct", "annotate"):
                    result_claim_id, target_claim_id, run_id = self._apply_correction(
                        report,
                        outcome,
                        proposal,
                        approval,
                        int(proposal_event["event_seq"]),
                        op_id,
                    )
                else:
                    disposition_id, target_id, target_claim_id = self._apply_suppression(
                        report, outcome, proposal, approval
                    )

                app_row = self._conn.execute(
                    "INSERT INTO intake.application"
                    "(report_id, operation_id, approval_seq, proposal_seq,"
                    " outcome, approved_by, applied_by, target_kind,"
                    " target_claim_id, target_id, result_claim_id,"
                    " disposition_id, ingest_run_id, detail) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::uuid,%s,"
                    "%s::uuid,%s::uuid,%s::uuid,%s::jsonb)"
                    " RETURNING application_id, report_id, operation_id,"
                    " approval_seq, proposal_seq, outcome, approved_by,"
                    " applied_by, target_kind, target_claim_id, target_id,"
                    " result_claim_id, disposition_id, ingest_run_id, detail,"
                    " applied_at",
                    (
                        str(report["report_id"]),
                        op_id,
                        int(approval["event_seq"]),
                        int(proposal_event["event_seq"]),
                        outcome,
                        str(approval["actor"]),
                        actor,
                        str(proposal["target_kind"]),
                        target_claim_id,
                        target_id or str(proposal["target_id"]),
                        result_claim_id,
                        disposition_id,
                        run_id,
                        json.dumps(
                            {
                                "claim_digest": proposal.get("claim_digest"),
                                "evidence_digest": proposal.get("evidence_digest"),
                                "predicate_id": proposal.get("predicate_id"),
                            }
                        ),
                    ),
                ).fetchone()
                assert app_row is not None
                app = dict(app_row)
                detail = {
                    "application_id": str(app["application_id"]),
                    "operation_id": op_id,
                    "outcome": outcome,
                    "approval_seq": int(approval["event_seq"]),
                    "target_kind": str(proposal["target_kind"]),
                    "target_id": target_id or str(proposal["target_id"]),
                    "result_claim_id": result_claim_id,
                    "disposition_id": disposition_id,
                }
                self._conn.execute(
                    "INSERT INTO intake.event (report_id, event, actor, detail)"
                    " VALUES (%s,'applied',%s,%s::jsonb)",
                    (str(report["report_id"]), actor, json.dumps(detail)),
                )
                return self._result(receipt_id, app, reconciled=False)
        except psycopg.errors.UniqueViolation:
            # A concurrent apply committed first — reconcile by operation_id
            # instead of erroring (the AC's uncertain-transaction case).
            if op_id is not None:
                row = self._conn.execute(
                    "SELECT application_id, report_id, operation_id, approval_seq,"
                    " proposal_seq, outcome, approved_by, applied_by, target_kind,"
                    " target_claim_id, target_id, result_claim_id, disposition_id,"
                    " ingest_run_id, detail, applied_at"
                    " FROM intake.application WHERE operation_id = %s",
                    (op_id,),
                ).fetchone()
                if row is not None:
                    return self._result(receipt_id, dict(row), reconciled=True)
            raise

    def mark_published(
        self,
        receipt_id: str,
        *,
        actor: str,
        publication_id: str | None = None,
        correction_ref: str | None = None,
        tombstone: str | None = None,
    ) -> dict[str, Any]:
        """Append the `published` event linking the applied correction to its
        release identity / public corrections-log pointer (or a safe tombstone).
        Idempotent: a repeat on an already-published report returns the
        existing event. A report whose payloads were already expunged may
        still be linked — the linkage is metadata, not payload."""
        self._check_actor(actor)
        linkage: dict[str, str] = {}
        if publication_id is not None or correction_ref is not None or tombstone is not None:
            try:
                linkage = pint.validate_publish_linkage(
                    publication_id=publication_id,
                    correction_ref=correction_ref,
                    tombstone=tombstone,
                )
            except pint.IntakeFieldError as exc:
                raise IntakeApplyError("invalid_linkage", str(exc)) from exc
        with self._conn.transaction():
            self._conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(BRIDGE_ROLE)))
            report = self._report_for_update(receipt_id, allow_expunged=True)
            events = self._events(str(report["report_id"]))
            latest = self._latest_lifecycle(events)
            if latest is not None and latest["event"] == "published":
                return {
                    "receipt_id": receipt_id,
                    "event": "published",
                    "event_seq": int(latest["event_seq"]),
                    "detail": latest["detail"],
                    "reconciled": True,
                }
            if latest is None or latest["event"] != "applied":
                raise IntakeApplyError(
                    "not_applied",
                    "publication linkage requires an applied report — "
                    "nothing was published through this bridge yet",
                )
            app = self._conn.execute(
                "SELECT application_id, operation_id, result_claim_id, disposition_id"
                " FROM intake.application WHERE report_id = %s"
                " ORDER BY applied_at DESC, application_id DESC LIMIT 1",
                (str(report["report_id"]),),
            ).fetchone()
            if app is None:  # pragma: no cover — an applied event implies the row
                raise IntakeApplyError("no_application", "no applied receipt exists")
            detail: dict[str, Any] = {
                "application_id": str(app["application_id"]),
                "operation_id": str(app["operation_id"]),
            }
            detail.update(linkage)
            # The corrections-log pointer defaults to the applied result — the
            # public corrections entry IS the new claim / the disposition.
            if "correction_ref" not in detail:
                detail["correction_ref"] = str(app["result_claim_id"] or app["disposition_id"])
            if "publication_id" not in detail and "tombstone" not in detail:
                detail["tombstone"] = "release identity not yet linked"
            row = self._conn.execute(
                "INSERT INTO intake.event (report_id, event, actor, detail)"
                " VALUES (%s,'published',%s,%s::jsonb) RETURNING event_seq",
                (str(report["report_id"]), actor, json.dumps(detail)),
            ).fetchone()
            assert row is not None
            return {
                "receipt_id": receipt_id,
                "event": "published",
                "event_seq": int(row["event_seq"]),
                "detail": detail,
                "reconciled": False,
            }

    def application(self, receipt_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT a.application_id, a.report_id, a.operation_id, a.approval_seq,"
            " a.proposal_seq, a.outcome, a.approved_by, a.applied_by,"
            " a.target_kind, a.target_claim_id, a.target_id, a.result_claim_id,"
            " a.disposition_id, a.ingest_run_id, a.detail, a.applied_at"
            " FROM intake.application a JOIN intake.report r"
            "   ON r.report_id = a.report_id WHERE r.receipt_id = %s",
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_out(dict(row))

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _result(receipt_id: str, app: dict[str, Any], *, reconciled: bool) -> dict[str, Any]:
        out = _row_out(app)
        out["receipt_id"] = receipt_id
        out["applied"] = True
        out["reconciled"] = reconciled
        return out


def _row_out(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key, val in list(out.items()):
        if isinstance(val, uuid.UUID):
            out[key] = str(val)
        elif isinstance(val, datetime):
            out[key] = val.isoformat()
    return out
