# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bounded live-capture pass for the Round-10 dossier families (P37.16a).

The ``sig.dossier-live-return-pass/1`` packets the offline dossier rows
committed (``LIVE_RETURN_PASS.json`` — ``D-P32.18-1`` / ``D-P32.19-1``, both
``prepared_not_executed``) gain an **executor**, under the plan cell's own
terms:

* **HG-03 lines** — every source a target rides (the family's ``dossier_*``
  row plus each ``existing_source``) must be green at the loader gate
  (:func:`connectors.runner.live_gate_reasons` empty). The flips are the
  operator's OP-26 execution of the prepared ``r11/sources-flips`` apply —
  this code reads the gate, it never writes it.
* **Part VIII sign** — B-42 ("Agent clears, disclosed",
  2026-10-01T04:51:39Z, ADR-185 §2): the agent screens each family against
  its drafted ADR-185 lanes and records ``preflight.status = "clear"`` on
  the queue candidates — every readout carries the verbatim disclosure
  **"cleared by agent screen, no human review"**. This module is where the
  screen lands: :func:`screen_family` evaluates the drafted lanes against
  their mechanical enforcements (the §43.4 naming gate, the Part VIII
  forbidden-token guard, extraction-time suppression) and fails closed when
  a lane has none; :func:`clear_record` emits the ``sig.part-viii-clear/1``
  record.
* **The staged pause** — capture runs touching Part VIII-screened families
  are **never pre-authorised under OM-20**: the pass executes only on the
  operator's explicit verbatim go for the capture run. Absent the go (or an
  unapplied HG-03 line) nothing fetches — the run stages, the result record
  keeps ``prepared_not_executed`` with every evaluated precondition, and the
  CLI exits ``QUEUED`` (42).

On execution the pass is deliberately small: each packet target is fetched
once through the reviewed stack (``PoliteFetcher`` + ``HttpxTransport`` +
``OcflCaptureStore`` + the registered connector for its source, the same
stages the fixture replay drives), the outcome is recorded honestly
(``captured`` / ``access_restricted`` incl. 403+challenge / ``link_rotted`` /
``unreachable`` / ``rights_refused`` / ``content_drift`` / ``too_large``), a
refusal is recorded never retried past its basis, and the rebuilt
``sig.dossier-packet/1`` binds real captures — **stand-ins are no longer
served** for any doc the pass attempted: a captured doc's records are the
connector's emit over live bytes; a refused doc keeps an honest
``capture_attempt`` record and nothing else.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]

LIVE_PASS_RESULT_SCHEMA = "sig.dossier-live-pass-result/1"
PART_VIII_CLEAR_SCHEMA = "sig.part-viii-clear/1"
SCREENS_PATH = "docs/build/reports/acquisition/PART_VIII_SCREENS.json"

#: The queued/dependency-gated exit code the leg scripts share
#: (``ops.db_logins.QUEUED`` precedent) — a paused pass is never a failure.
QUEUED = 42

#: The operator-go requirement, verbatim from the plan cell — the result
#: record carries it so the queued state is self-describing.
OPERATOR_GO_REQUIREMENT = (
    "IN-TICKET PAUSE (never pre-authorised under OM-20: capture runs touching "
    "Part VIII-screened families); explicit verbatim go for the capture run"
)

#: The B-42 disclosure every readout relying on an agent clear must carry.
AGENT_CLEAR_DISCLOSURE = "cleared by agent screen, no human review"
B42_AUTHORITY = (
    "E4-B2 / B-42 'Agent clears, disclosed' (operator answer "
    "2026-10-01T04:51:39Z, decision_catalog round 18; ADR-185 §2)"
)

# --------------------------------------------------------------------------- #
# Outcome vocabulary — honest per-target dispositions                          #
# --------------------------------------------------------------------------- #

OUTCOME_CAPTURED = "captured"
OUTCOME_ACCESS_RESTRICTED = "access_restricted"  # 401/451/403 + challenges
OUTCOME_LINK_ROTTED = "link_rotted"  # 404/410
OUTCOME_UNREACHABLE = "unreachable"  # transport-level failure
OUTCOME_RIGHTS_REFUSED = "rights_refused"  # opt-out register / reservation
OUTCOME_CONTENT_DRIFT = "content_drift"  # connector's own refusal on bytes
OUTCOME_TOO_LARGE = "too_large"  # over the family's byte bound
OUTCOME_NOT_ATTEMPTED = "not_attempted"  # gate refused — never fetched

OUTCOMES: tuple[str, ...] = (
    OUTCOME_CAPTURED,
    OUTCOME_ACCESS_RESTRICTED,
    OUTCOME_LINK_ROTTED,
    OUTCOME_UNREACHABLE,
    OUTCOME_RIGHTS_REFUSED,
    OUTCOME_CONTENT_DRIFT,
    OUTCOME_TOO_LARGE,
    OUTCOME_NOT_ATTEMPTED,
)


def _real_gate(sid: str) -> list[str]:
    """The real loader gate (lazy import — the connectors dep stays off the
    module's import surface for record-only callers)."""
    from connectors.runner import live_gate_reasons

    return list(live_gate_reasons(sid))


def _real_resolver(sid: str) -> Any:
    """The real registry row for ``sid`` (lazy import)."""
    from connectors.registry import get

    return get(sid)


# --------------------------------------------------------------------------- #
# Family registry (this split: the first two families; P37.16b extends it)     #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Family:
    """One dossier family's live-pass wiring (all data, no authority)."""

    key: str
    #: The family's own gated connector source row.
    source_id: str
    #: The acquisition-queue candidates the Part VIII clear lands on.
    candidates: tuple[str, ...]
    #: The ``PART_VIII_SCREENS.json`` family name the draft screen is under.
    screen_family: str
    #: The DEFERRALS obligation this pass discharges (when it executes).
    deferral: str
    #: The committed report directory the packet + artifacts live under.
    report_dir: str
    #: The committed packet's filename inside the report directory.
    pass_packet_name: str
    #: The ops module whose ``build_packet()`` composes the base packet.
    packet_module: str
    #: The packet schema's dossier id (for artifact naming).
    result_name: str = "LIVE_PASS_RESULT.json"
    clear_name: str = "PART_VIII_CLEAR.json"

    @property
    def report_path(self) -> Path:
        return _REPO / self.report_dir


FAMILIES: dict[str, Family] = {
    "okc": Family(
        key="okc",
        source_id="dossier_okc",
        candidates=("SRC-001",),
        screen_family="okc-municipal",
        deferral="D-P32.18-1",
        report_dir="docs/build/reports/p32.18-okc-dossier",
        pass_packet_name="LIVE_RETURN_PASS.json",
        packet_module="ops.dossier_packet",
    ),
    "tulsa": Family(
        key="tulsa",
        source_id="dossier_tulsa",
        candidates=("SRC-002",),
        screen_family="tulsa-municipal",
        deferral="D-P32.19-1",
        report_dir="docs/build/reports/p32.19-tulsa-dossier",
        pass_packet_name="LIVE_RETURN_PASS.json",
        packet_module="ops.tulsa_dossier_packet",
    ),
}


def family(key: str) -> Family:
    try:
        return FAMILIES[key]
    except KeyError:
        raise KeyError(
            f"unknown dossier live-pass family {key!r}; registered: {sorted(FAMILIES)}"
        ) from None


# --------------------------------------------------------------------------- #
# Packet + registry reads                                                      #
# --------------------------------------------------------------------------- #


def load_pass_packet(fam: Family, packet: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The family's committed ``sig.dossier-live-return-pass/1`` packet."""
    if packet is not None:
        out = dict(packet)
    else:
        out = json.loads((fam.report_path / fam.pass_packet_name).read_text(encoding="utf-8"))
    if out.get("schema") != "sig.dossier-live-return-pass/1":
        raise ValueError(
            f"{fam.pass_packet_name} is not a sig.dossier-live-return-pass/1 packet "
            f"(schema={out.get('schema')!r})"
        )
    return out


def family_sources(fam: Family, packet: Mapping[str, Any]) -> list[str]:
    """Every registry source a packet target rides, in packet order."""
    out: list[str] = []
    for t in packet.get("targets", []):
        sid = str(t.get("existing_source") or fam.source_id)
        if sid not in out:
            out.append(sid)
    return out


def hg03_lines(
    fam: Family,
    packet: Mapping[str, Any],
    *,
    gate: Callable[[str], list[str]] | None = None,
) -> dict[str, Any]:
    """The per-source HG-03 line state — ``applied`` only when the loader
    gate is genuinely green (the operator's flips on ``r11/sources-flips``,
    OP-26; this code reads, never writes)."""
    gate_fn = gate or _real_gate

    lines: dict[str, Any] = {}
    applied = True
    for sid in family_sources(fam, packet):
        reasons = list(gate_fn(sid))
        lines[sid] = {
            "status": "applied" if not reasons else "pending",
            "reasons": reasons,
            "note": (
                "green at the loader gate — the operator's HG-03 flip is applied"
                if not reasons
                else "refused at the loader gate — the operator's HG-03 flip "
                "(prepared on r11/sources-flips, OP-26) is not applied; the "
                "agent never flips a source"
            ),
        }
        applied = applied and not reasons
    return {"applied": applied, "lines": lines}


def part_viii_state(
    fam: Family,
    *,
    entries: list[Any] | None = None,
) -> dict[str, Any]:
    """The family's queue-candidate preflight state (B-42's ``clear``)."""
    if entries is None:
        from tasks.acquisition import build_queue

        entries = build_queue()
    by_id = {e.passport.candidate_id: e.passport for e in entries}
    out: dict[str, Any] = {}
    cleared = True
    for cid in fam.candidates:
        p = by_id.get(cid)
        status = str(p.preflight.status.value) if p is not None else "missing"
        out[cid] = {
            "status": status,
            "notes": (p.preflight.notes if p is not None else ""),
            "disclosure": AGENT_CLEAR_DISCLOSURE,
        }
        cleared = cleared and status == "clear"
    return {"cleared": cleared, "candidates": out}


# --------------------------------------------------------------------------- #
# The B-42 agent screen (ADR-185 §2)                                           #
# --------------------------------------------------------------------------- #

#: The mechanical enforcement each drafted ADR-185 lane rides. A drafted lane
#: with no enforcement never clears — the screen fails closed. Enforcements
#: are named by the machinery that applies them at claim-build time, with the
#: predicate-level guard the connector runs for EVERY claim.
LANE_ENFORCEMENTS: dict[str, dict[str, str]] = {
    "S5": {
        "lane": "officer names",
        "enforcement": (
            "the §43.4 naming gate — connectors.okc_documents."
            "assert_person_naming_permitted runs on every claim; a "
            "person-named predicate is refused by default (SIG-PUB-007/008 "
            "stands; names suppressed, never emitted)"
        ),
    },
    "S6": {
        "lane": "free-text excerpts",
        "enforcement": (
            "the SIG-PUB-014a excerpt screen — connectors.okc_documents."
            "assert_part_viii_safe scans every predicate id and verbatim raw "
            "value for the forbidden-token set before any claim is built; "
            "facts only, no free-text carry-through"
        ),
    },
    "S7": {
        "lane": "incidental private names",
        "enforcement": (
            "extraction-time suppression — the reviewed field maps emit "
            "configured fields only (no free-text carry-through), and the "
            "forbidden-token guard + naming gate refuse anything person-level "
            "that reaches claim build"
        ),
    },
    "S9": {
        "lane": "row-specific (signature blocks / family members)",
        "enforcement": (
            "the row's own screen — person-named fields are configured "
            "present_but_empty/absent or omitted from the field map, and the "
            "naming gate + forbidden-token guard refuse any that reach emit"
        ),
    },
}

_LANE_ID_RE = re.compile(r"\bS[1-9]\b")


def _draft_screen(fam: Family, screens: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The family's drafted screen from ``PART_VIII_SCREENS.json``."""
    if screens is None:
        screens = json.loads((_REPO / SCREENS_PATH).read_text(encoding="utf-8"))
    for s in screens.get("screens", []):
        if str(s.get("family")) == fam.screen_family:
            return dict(s)
    raise KeyError(
        f"no drafted Part VIII screen for family {fam.screen_family!r} in {SCREENS_PATH}"
    )


def screen_family(
    fam: Family,
    *,
    screens: Mapping[str, Any] | None = None,
    packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the family's drafted screen — the B-42 agent screen itself.

    Every drafted lane must resolve to a named mechanical enforcement that
    runs at claim build (the extraction guards are the controls — B-42 leaves
    no human check); a lane with none fails the screen closed. The verdict is
    the agent's, disclosed — never a human review.
    """
    draft = _draft_screen(fam, screens)
    preflight = draft.get("preflight") or {}
    lanes: list[dict[str, Any]] = []
    unenforced: list[str] = []
    for lane_text in preflight.get("lanes", []):
        ids = _LANE_ID_RE.findall(str(lane_text))
        enforced = bool(ids) and all(i in LANE_ENFORCEMENTS for i in ids)
        if not enforced:
            unenforced.append(str(lane_text))
        lanes.append(
            {
                "drafted": str(lane_text),
                "enforced": enforced,
                "enforcement": (
                    LANE_ENFORCEMENTS[ids[0]]["enforcement"]
                    if ids and ids[0] in LANE_ENFORCEMENTS
                    else ""
                ),
            }
        )
    # The extraction guards the lanes name must actually exist — the screen
    # verifies the controls, not just the vocabulary.
    from connectors.okc_documents import (
        assert_part_viii_safe,
        assert_person_naming_permitted,
    )

    controls_present = callable(assert_part_viii_safe) and callable(assert_person_naming_permitted)
    pkt = load_pass_packet(fam, packet)
    verdict = "clear" if (not unenforced and controls_present and lanes) else "held"
    return {
        "family": fam.screen_family,
        "verdict": verdict,
        "screener": "agent",
        "disclosure": AGENT_CLEAR_DISCLOSURE,
        "authority": B42_AUTHORITY,
        "draft": {
            "status": str(preflight.get("status", "")),
            "screener": str(preflight.get("screener", "")),
            "screened_on": str(preflight.get("screened_on", "")),
            "source": SCREENS_PATH,
        },
        "lanes": lanes,
        "unenforced_lanes": unenforced,
        "controls_verified": controls_present,
        "targets": [
            {"doc_id": str(t.get("doc_id", "")), "url": str(t.get("url", ""))}
            for t in pkt.get("targets", [])
        ],
        "notes": str(preflight.get("notes", "")),
        "held_reason": (
            ""
            if verdict == "clear"
            else "; ".join(
                part
                for part in (
                    f"lanes without a mechanical enforcement: {sorted(set(unenforced))}"
                    if unenforced
                    else "",
                    "the extraction guards are not present" if not controls_present else "",
                    "the draft names no lanes" if not lanes else "",
                )
                if part
            )
        ),
    }


def clear_record(
    fam: Family,
    *,
    screened_on: str | None = None,
    screens: Mapping[str, Any] | None = None,
    packet: Mapping[str, Any] | None = None,
    queue_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``sig.part-viii-clear/1`` record — the family's B-42 clear, disclosed."""
    screen = screen_family(fam, screens=screens, packet=packet)
    state = queue_state if queue_state is not None else part_viii_state(fam)
    on = screened_on or datetime.now(UTC).date().isoformat()
    return {
        "schema": PART_VIII_CLEAR_SCHEMA,
        "family": fam.screen_family,
        "deferral": fam.deferral,
        "candidates": list(fam.candidates),
        "status": screen["verdict"],
        "screener": "agent",
        "screened_on": on,
        "disclosure": AGENT_CLEAR_DISCLOSURE,
        "authority": B42_AUTHORITY,
        "draft": screen["draft"],
        "lanes": screen["lanes"],
        "controls_verified": screen["controls_verified"],
        "targets": screen["targets"],
        "queue_preflight": state["candidates"],
        "note": (
            "the Part VIII sign-off this family's capture run requires (E4-B2 → "
            "B-42 'Agent clears, disclosed'): the agent screened the family's "
            "drafted lanes against their mechanical enforcements and cleared "
            "it — 'cleared by agent screen, no human review' is the honest "
            "label every readout carries"
            if screen["verdict"] == "clear"
            else f"the screen held — {screen['held_reason']}; no clear recorded"
        ),
    }


def write_clear(fam: Family, out_dir: Path | None = None, **kw: Any) -> Path:
    """Emit ``PART_VIII_CLEAR.json`` into the family report dir (or ``out_dir``)."""
    record = clear_record(fam, **kw)
    out = (out_dir or fam.report_path) / fam.clear_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


# --------------------------------------------------------------------------- #
# Preconditions + the staged pause                                             #
# --------------------------------------------------------------------------- #


def preconditions(
    fam: Family,
    packet: Mapping[str, Any],
    *,
    operator_go: str | None = None,
    gate: Callable[[str], list[str]] | None = None,
    entries: list[Any] | None = None,
) -> dict[str, Any]:
    """Every leg precondition, evaluated honestly."""
    hg03 = hg03_lines(fam, packet, gate=gate)
    pv = part_viii_state(fam, entries=entries)
    go = (operator_go or "").strip()
    return {
        "hg03_lines": hg03,
        "part_viii": pv,
        "operator_go": {
            "present": bool(go),
            "verbatim": go or None,
            "requirement": OPERATOR_GO_REQUIREMENT,
        },
        "ready": bool(hg03["applied"] and pv["cleared"] and go),
    }


def _paused_reasons(pre: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    if not pre["operator_go"]["present"]:
        out.append("operator_go_absent — " + OPERATOR_GO_REQUIREMENT)
    pending = [s for s, line in pre["hg03_lines"]["lines"].items() if line["status"] != "applied"]
    if pending:
        out.append(
            "hg03_lines_pending — the operator's flips are not applied for: "
            + ", ".join(pending)
            + " (OP-26; the agent never flips a source)"
        )
    uncleared = [c for c, s in pre["part_viii"]["candidates"].items() if s["status"] != "clear"]
    if uncleared:
        out.append("part_viii_clear_missing — " + ", ".join(uncleared) + " is not recorded clear")
    return out


# --------------------------------------------------------------------------- #
# Execution — per-target fetch through the reviewed stack                      #
# --------------------------------------------------------------------------- #


def _fetcher_default() -> Any:
    """The real politeness-layer fetcher over the httpx transport (live path)."""
    from connectors.net import PoliteFetcher, RateLimiter
    from connectors.transports import HttpxTransport

    return PoliteFetcher(
        connector_name="dossier_live_pass",
        connector_version="1.0.0",
        transport=HttpxTransport(),
        rate_limiter=RateLimiter(),
    )


def _captures_default(capture_dir: Path | None) -> Any:
    """The durable OCFL capture store the live run archives through."""
    from connectors.capture_ocfl import OcflCaptureStore
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    root = capture_dir or (_REPO / ".sig" / "captures")
    return OcflCaptureStore(OcflStore(LocalFileStore(str(root))))


def _connector_for_source(source_id: str) -> Any:
    from connectors.runner import CONNECTOR_FOR_SOURCE
    from connectors.stages import registered_connectors

    name = CONNECTOR_FOR_SOURCE.get(source_id)
    if name is None:
        raise ValueError(f"no connector registered for source {source_id!r}")
    return registered_connectors()[name]()


def _outcome_row(
    target: Mapping[str, Any],
    source_id: str,
    outcome: str,
    *,
    detail: str,
    http_status: int | None = None,
    capture: Any | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "doc_id": str(target.get("doc_id") or target.get("id") or ""),
        "url": str(target.get("url") or ""),
        "source_id": source_id,
        "goal": str(target.get("goal") or ""),
        "outcome": outcome,
        "detail": detail,
    }
    if http_status is not None:
        row["http_status"] = http_status
    if capture is not None:
        row.update(
            {
                "capture_digest": capture.digest,
                "byte_size": capture.byte_size,
                "media_type": capture.media_type,
                "retrieved_at": (
                    capture.retrieved_at.isoformat()
                    if getattr(capture, "retrieved_at", None) is not None
                    else None
                ),
                "ocfl_object_id": getattr(capture, "ocfl_object_id", None),
                "ocfl_version": getattr(capture, "ocfl_version", None),
            }
        )
    if records is not None:
        row["emitted_records"] = len(records)
    return row


def _byte_cap(fam: Family, target: Mapping[str, Any]) -> int | None:
    """The family's document byte bound (a per-target override wins — E4-B4's
    pattern), else the adapter vocabulary's ``max_document_bytes``."""
    for key in ("byte_bound", "max_document_bytes"):
        if target.get(key) is not None:
            return int(target[key])
    if str(target.get("kind")) == "clause_fields":
        from connectors.dossier_documents import resource_bounds

        bound = resource_bounds().get("max_document_bytes")
        return int(bound) if bound is not None else None
    return None


def _run_connector_target(
    fam: Family,
    target: Mapping[str, Any],
    source_id: str,
    row: Mapping[str, Any],
    *,
    fetcher: Any,
    captures: Any,
    source_resolver: Callable[[str], Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Drive the registered connector over one reviewed live-target row.

    Returns ``(outcome_row, emitted_records)`` — the outcome row for the
    result record and the connector's emit over the captured bytes (empty on
    every non-captured disposition)."""
    from connectors.pipeline import run
    from connectors.stages import InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    connector = _connector_for_source(source_id)
    ctx = RunContext(
        source=source_resolver(source_id),
        run=IngestRun(
            connector.name,
            getattr(connector, "version", "1.0.0"),
            f"dossier-live-pass:{fam.key}",
            "r1",
            "v1",
            (),
        ),
        fetcher=fetcher,
        captures=captures,
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [dict(row)]},
    )
    try:
        report = run(connector, ctx)
    except Exception as exc:
        from connectors.stages import ContentDrift

        if isinstance(exc, ContentDrift):
            # A drifted seed capture is recorded, never a crash that
            # abandons the packet's remaining targets.
            return (
                _outcome_row(
                    target,
                    source_id,
                    OUTCOME_CONTENT_DRIFT,
                    detail=f"connector refused the captured bytes: {exc}",
                ),
                [],
            )
        raise
    url = str(target.get("url") or "")
    # Outcome precedence: refusal > disappearance > drift > too_large > captured.
    for r in report.refusals:
        return (
            _outcome_row(
                target,
                source_id,
                OUTCOME_RIGHTS_REFUSED,
                detail=f"{r.get('refusal')}: {r.get('detail')}",
            ),
            [],
        )
    for d in report.disappearances:
        status = d.event.failing_status
        outcome = {
            "link_rotted": OUTCOME_LINK_ROTTED,
            "access_restricted": OUTCOME_ACCESS_RESTRICTED,
            "unreachable": OUTCOME_UNREACHABLE,
        }.get(status, OUTCOME_ACCESS_RESTRICTED)
        return (
            _outcome_row(
                target,
                source_id,
                outcome,
                detail=f"fetch outcome {status!r} recorded by the pipeline"
                + (
                    f" (challenge http_status={report.last_challenge_status})"
                    if report.last_challenge_status
                    else ""
                ),
                http_status=report.last_challenge_status,
            ),
            [],
        )
    cap = next((c for c in report.captures if c.source_uri == url), None) or (
        report.captures[0] if report.captures else None
    )
    bound = _byte_cap(fam, target)
    if cap is not None and bound is not None and cap.byte_size > bound:
        return (
            _outcome_row(
                target,
                source_id,
                OUTCOME_TOO_LARGE,
                detail=(
                    f"captured {cap.byte_size} bytes exceeds the family bound "
                    f"{bound} — recorded, never parsed"
                ),
                capture=cap,
            ),
            [],
        )
    if report.drifted:
        drift = report.drifted[0]
        return (
            _outcome_row(
                target,
                source_id,
                OUTCOME_CONTENT_DRIFT,
                detail=f"connector refused the captured bytes: {drift.get('reason', drift)}",
                capture=cap,
            ),
            [],
        )
    if cap is None:
        return (
            _outcome_row(
                target,
                source_id,
                OUTCOME_UNREACHABLE,
                detail="the run produced no capture and no recorded disposition",
            ),
            [],
        )
    return (
        _outcome_row(
            target,
            source_id,
            OUTCOME_CAPTURED,
            detail="fetched + archived + emitted through the reviewed connector",
            capture=cap,
            records=report.claims,
        ),
        [dict(r) for r in report.claims],
    )


def _fetch_only_target(
    fam: Family,
    target: Mapping[str, Any],
    source_id: str,
    *,
    fetcher: Any,
    captures: Any,
) -> dict[str, Any]:
    """A reviewed lead with no connector field map: fetch + archive + the
    honest outcome — no claim is minted off an unreviewed parse."""
    from connectors.disappearance import failing_status_for_error, failing_status_for_http
    from connectors.net import (
        ChallengeEncountered,
        HostOptOut,
        ReservationRefused,
        RobotsDisallowed,
        RobotsUnretrievable,
    )

    url = str(target.get("url") or "")
    try:
        result = fetcher.fetch(url)
    except (HostOptOut, ReservationRefused, RobotsDisallowed, RobotsUnretrievable) as exc:
        return _outcome_row(
            target,
            source_id,
            OUTCOME_RIGHTS_REFUSED,
            detail=f"{type(exc).__name__}: {exc}",
        )
    except ChallengeEncountered as exc:
        return _outcome_row(
            target,
            source_id,
            OUTCOME_ACCESS_RESTRICTED,
            detail=f"challenge recorded, never defeated (SIG-INGEST-013): {exc}",
            http_status=getattr(exc, "status", None),
        )
    except Exception as exc:
        status = failing_status_for_error(exc)
        if status is None:
            raise
        return _outcome_row(
            target,
            source_id,
            "unreachable" if status == "unreachable" else OUTCOME_ACCESS_RESTRICTED,
            detail=f"transport outcome {status!r}: {type(exc).__name__}: {exc}",
        )
    failing = failing_status_for_http(result.status)
    if failing is not None:
        return _outcome_row(
            target,
            source_id,
            OUTCOME_LINK_ROTTED if failing == "link_rotted" else OUTCOME_ACCESS_RESTRICTED,
            detail=f"http {result.status} recorded ({failing})",
            http_status=result.status,
        )
    stored = captures.put(
        result.body,
        media_type=result.media_type,
        source_uri=result.url,
        retrieved_at=result.retrieved_at,
    )
    bound = _byte_cap(fam, target)
    if bound is not None and stored.byte_size > bound:
        return _outcome_row(
            target,
            source_id,
            OUTCOME_TOO_LARGE,
            detail=(
                f"captured {stored.byte_size} bytes exceeds the family bound "
                f"{bound} — archived, never parsed"
            ),
            capture=stored,
        )
    return _outcome_row(
        target,
        source_id,
        OUTCOME_CAPTURED,
        detail="fetched + archived (reviewed lead — capture + outcome only, no parse)",
        capture=stored,
    )


def execute(
    fam: Family,
    packet: Mapping[str, Any],
    *,
    fetcher: Any,
    captures: Any,
    gate: Callable[[str], list[str]] | None = None,
    source_resolver: Callable[[str], Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Execute the packet's targets — one fetch each, honest outcomes.

    Returns ``(outcome_rows, emitted)`` where ``emitted`` maps a captured
    doc_id to the connector's emit over the live bytes. Fail-closed at two
    levels: a source whose gate is not green yields a ``not_attempted``
    outcome for every target riding it (never a fetch), and a target with no
    reviewed ``live_targets.toml`` row rides the fetch-only path (capture +
    outcome, no claim minted off an unreviewed parse).
    """
    gate_fn = gate or _real_gate
    resolver = source_resolver or _real_resolver

    from connectors.live_targets import live_targets

    gate_cache: dict[str, list[str]] = {}

    def _gate(sid: str) -> list[str]:
        if sid not in gate_cache:
            gate_cache[sid] = list(gate_fn(sid))
        return gate_cache[sid]

    target_rows: dict[str, dict[str, Any]] = {}
    for sid in family_sources(fam, packet):
        for lt_row in live_targets(sid):
            key = str(lt_row.get("doc_id") or lt_row.get("id") or "")
            target_rows[f"{sid}:{key}"] = dict(lt_row)
            target_rows[f"{sid}:{lt_row.get('url')}"] = dict(lt_row)

    outcomes: list[dict[str, Any]] = []
    emitted: dict[str, list[dict[str, Any]]] = {}
    for target in packet.get("targets", []):
        source_id = str(target.get("existing_source") or fam.source_id)
        reasons = _gate(source_id)
        if reasons:
            outcomes.append(
                _outcome_row(
                    target,
                    source_id,
                    OUTCOME_NOT_ATTEMPTED,
                    detail=(
                        f"source {source_id!r} is not green at the loader gate "
                        f"({' ; '.join(reasons)}) — the HG-03 line is the "
                        "operator's, never bypassed"
                    ),
                )
            )
            continue
        doc_id = str(target.get("doc_id") or target.get("id") or "")
        trow = target_rows.get(f"{source_id}:{doc_id}") or target_rows.get(
            f"{source_id}:{target.get('url')}"
        )
        out: dict[str, Any]
        if trow is None:
            out = _fetch_only_target(fam, target, source_id, fetcher=fetcher, captures=captures)
            records: list[dict[str, Any]] = []
        else:
            out, records = _run_connector_target(
                fam,
                target,
                source_id,
                trow,
                fetcher=fetcher,
                captures=captures,
                source_resolver=resolver,
            )
        outcomes.append(out)
        if records:
            # The packet keeps only the reproducible record payload — the
            # connector-transient ids (claim_id / sys_period) are stripped,
            # the same additive mark the replay path applies (P34.22b).
            emitted[doc_id] = [
                {k: v for k, v in r.items() if k not in ("claim_id", "sys_period")} for r in records
            ]
    return outcomes, emitted


# --------------------------------------------------------------------------- #
# Packet rebuild — stand-ins are no longer served                              #
# --------------------------------------------------------------------------- #

#: Packet record kinds that bind a document's bytes.
_EVIDENCE_KINDS = frozenset({"evidence_artifact"})


def _live_artifact(fam: Family, outcome: Mapping[str, Any]) -> dict[str, Any]:
    """The ``evidence_artifact`` row for a captured doc — real bytes, real
    retrieval stamp, no stand-in/transcription marker (the ``live_capture``
    acquisition label derives honestly)."""
    return {
        "record_kind": "evidence_artifact",
        "connector": "ops.dossier_live_pass",
        "document_id": outcome["doc_id"],
        "source_id": outcome["source_id"],
        "source_uri": outcome["url"],
        "capture_digest": outcome["capture_digest"],
        "byte_size": outcome["byte_size"],
        "media_type": outcome["media_type"],
        "retrieved_at": outcome["retrieved_at"],
        "retrieved_date": str(outcome["retrieved_at"] or "")[:10],
        "method": "http_fetch",
        "access_mode": "live_capture",
        "capture_kind": "live_capture",
        "sensitivity_class": "C1",
        "note": (
            "live capture archived through the reviewed stack "
            "(dossier-live-pass); the digest binds the real fetched bytes"
        ),
    }


def _attempt_record(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """The honest ``capture_attempt`` record a refused/failed doc keeps —
    no stand-in bytes are ever served for a doc the pass attempted."""
    return {
        "record_kind": "capture_attempt",
        "connector": "ops.dossier_live_pass",
        "document_id": outcome["doc_id"],
        "source_id": outcome["source_id"],
        "source_uri": outcome["url"],
        "outcome": outcome["outcome"],
        "detail": outcome["detail"],
        "http_status": outcome.get("http_status"),
        "note": (
            "the live pass attempted this doc and recorded the honest "
            "outcome — the prior committed stand-in is withdrawn from the "
            "rebuilt packet and is never presented as a capture"
        ),
    }


def rebuild_packet(
    fam: Family,
    base: Mapping[str, Any],
    outcomes: list[dict[str, Any]],
    *,
    emitted: Mapping[str, list[dict[str, Any]]] | None = None,
    rebuilt_at: str | None = None,
) -> dict[str, Any]:
    """Rebuild ``sig.dossier-packet/1`` binding the pass's real captures.

    Every record bound to an attempted doc (by ``document_id``) is replaced:
    a captured doc gains its live ``evidence_artifact`` + the connector's
    emit over live bytes; a refused doc keeps only the ``capture_attempt``
    record. Records for docs the pass did not attempt (authored journalism,
    evidence-pack fixtures — honestly labelled committed material, never a
    stand-in for a live target) are carried verbatim.
    """
    attempted = {o["doc_id"]: o for o in outcomes}
    records: list[dict[str, Any]] = []
    for rec in base.get("records", []):
        doc_id = str(rec.get("document_id") or "")
        if doc_id in attempted:
            continue  # replaced below — a stand-in never survives its pass
        records.append(dict(rec))
    for o in outcomes:
        if o["outcome"] == OUTCOME_CAPTURED:
            records.append(_live_artifact(fam, o))
            records.extend(dict(r) for r in (emitted or {}).get(o["doc_id"], []))
        else:
            records.append(_attempt_record(o))
    out = dict(base)
    out["records"] = records
    stamp = rebuilt_at or datetime.now(UTC).isoformat()
    out["capture"] = {
        **dict(base.get("capture") or {}),
        "kind": "live_pass",
        "live_verification": True,
        "anchor": stamp,
        "live_pass": {
            "schema": LIVE_PASS_RESULT_SCHEMA,
            "deferral": fam.deferral,
            "executed_at": stamp,
            "outcomes": {o["doc_id"]: o["outcome"] for o in outcomes},
        },
    }
    return out


# --------------------------------------------------------------------------- #
# The result record + the run                                                  #
# --------------------------------------------------------------------------- #


def result_record(
    fam: Family,
    packet: Mapping[str, Any],
    pre: Mapping[str, Any],
    *,
    status: str,
    outcomes: list[dict[str, Any]] | None = None,
    evaluated_at: str | None = None,
    go_recorded_by: str | None = None,
) -> dict[str, Any]:
    """The ``sig.dossier-live-pass-result/1`` record — executed or queued."""
    return {
        "schema": LIVE_PASS_RESULT_SCHEMA,
        "packet_id": str(packet.get("packet_id", "")),
        "family": fam.key,
        "deferral": fam.deferral,
        "status": status,
        "evaluated_at": evaluated_at or datetime.now(UTC).isoformat(),
        "operator_go_requirement": OPERATOR_GO_REQUIREMENT,
        "operator_go": pre["operator_go"],
        "go_recorded_by": go_recorded_by,
        "preconditions": {
            "hg03_lines": pre["hg03_lines"],
            "part_viii": pre["part_viii"],
        },
        "paused_reasons": [] if status == "executed" else _paused_reasons(pre),
        "targets": outcomes
        or [
            {
                "doc_id": str(t.get("doc_id", "")),
                "url": str(t.get("url", "")),
                "source_id": str(t.get("existing_source") or fam.source_id),
                "outcome": OUTCOME_NOT_ATTEMPTED,
            }
            for t in packet.get("targets", [])
        ],
        "non_goals": list(packet.get("non_goals", [])),
        "note": (
            "no capture ran — the leg is staged, never executed; the committed "
            "stand-ins stay the honest posture and nothing here is a live "
            "capture"
            if status != "executed"
            else "the pass executed under the operator's recorded verbatim go; "
            "each target's outcome is honest — a refusal is recorded, never "
            "retried past its basis"
        ),
    }


def run_pass(
    fam: Family,
    *,
    operator_go: str | None = None,
    out_dir: Path | None = None,
    capture_dir: Path | None = None,
    fetcher: Any | None = None,
    captures: Any | None = None,
    gate: Callable[[str], list[str]] | None = None,
    source_resolver: Callable[[str], Any] | None = None,
    entries: list[Any] | None = None,
    go_recorded_by: str | None = None,
    evaluated_at: str | None = None,
    packet: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Run (or stage) the family's live pass.

    Returns ``(result_record, exit_code)``: ``0`` executed, ``QUEUED`` (42)
    staged — the staged pause is the default; nothing fetches without the
    operator's verbatim go AND every HG-03 line applied AND the Part VIII
    clear recorded.
    """
    pkt = load_pass_packet(fam, packet)
    pre = preconditions(fam, pkt, operator_go=operator_go, gate=gate, entries=entries)
    dest = out_dir or fam.report_path
    dest.mkdir(parents=True, exist_ok=True)
    if not pre["ready"]:
        record = result_record(
            fam,
            pkt,
            pre,
            status="prepared_not_executed",
            evaluated_at=evaluated_at,
        )
        (dest / fam.result_name).write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return record, QUEUED

    fetcher = fetcher if fetcher is not None else _fetcher_default()
    captures = captures if captures is not None else _captures_default(capture_dir)
    outcomes, emitted = execute(
        fam,
        pkt,
        fetcher=fetcher,
        captures=captures,
        gate=gate,
        source_resolver=source_resolver,
    )
    # Rebuild the packet binding the real captures — stand-ins are no longer
    # served for any doc the pass attempted.
    import importlib

    base = importlib.import_module(fam.packet_module).build_packet()
    rebuilt = rebuild_packet(fam, base, outcomes, emitted=emitted, rebuilt_at=evaluated_at)
    record = result_record(
        fam,
        pkt,
        pre,
        status="executed",
        outcomes=outcomes,
        evaluated_at=evaluated_at,
        go_recorded_by=go_recorded_by,
    )
    record["rebuilt_packet"] = {
        "records": len(rebuilt["records"]),
        "note": "the rebuilt sig.dossier-packet/1 — stand-ins no longer served",
    }
    (dest / fam.result_name).write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return record, 0


__all__ = [
    "AGENT_CLEAR_DISCLOSURE",
    "B42_AUTHORITY",
    "FAMILIES",
    "LANE_ENFORCEMENTS",
    "LIVE_PASS_RESULT_SCHEMA",
    "OPERATOR_GO_REQUIREMENT",
    "OUTCOMES",
    "OUTCOME_ACCESS_RESTRICTED",
    "OUTCOME_CAPTURED",
    "OUTCOME_CONTENT_DRIFT",
    "OUTCOME_LINK_ROTTED",
    "OUTCOME_NOT_ATTEMPTED",
    "OUTCOME_RIGHTS_REFUSED",
    "OUTCOME_TOO_LARGE",
    "OUTCOME_UNREACHABLE",
    "PART_VIII_CLEAR_SCHEMA",
    "QUEUED",
    "Family",
    "clear_record",
    "execute",
    "family",
    "family_sources",
    "hg03_lines",
    "load_pass_packet",
    "part_viii_state",
    "preconditions",
    "rebuild_packet",
    "result_record",
    "run_pass",
    "screen_family",
    "write_clear",
]
