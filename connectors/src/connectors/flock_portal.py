# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `flock_portal` connector — the Eyes on Flock portal layer (§23.4, P11.1).

This connector sources the Flock portal layer from the aggregator's public
**CC BY-SA 4.0** JSON API (`GET /api/v1/data`, §22.5, SC-18) and lands it in a
**separate CC BY-SA 4.0 compartment** (``compartments.portal``, §42.2). It NEVER
attempts capture from the vendor (``flocksafety.com``), whose every path returns a
bot-management challenge (F2.1, SIG-INGEST-035). A challenge is honoured as a
**refusal**: the shared :class:`connectors.net.PoliteFetcher` raises
:class:`~connectors.net.ChallengeEncountered` and the pipeline records a
disappearance — there is **no challenge-defeating code anywhere in this module**
(SIG-INGEST-036/037, Crawler-Conduct Rule 4).

This module owns the parts of §23.4 the framework does not provide:

* **A versioned field → predicate mapping** (data, in
  ``data/flock_portal_vocab.toml``): every aggregator field this connector writes,
  its SIG predicate, its genre, and whether the value is windowed. A predicate
  outside the allowlist is a schema error (SIG-INGEST-033 analogue); contract
  facts, device geometry, and per-search / per-plate rows are refused (§18.1).
* **Change detection keyed on the upstream snapshot field** ``data_last_updated``,
  never on SIG's fetch time (SIG-INGEST-030c). ``observed_at`` on every row is the
  upstream's own snapshot date; :func:`is_poll_due` suppresses polling faster than
  the upstream refreshes.
* **Historical back-fill from archived captures** (SIG-INGEST-030b): the connector
  is target-agnostic, so a Wayback-capture URL is just another ``discover`` target
  and its snapshot date drives ``observed_at`` exactly as a live capture would.
* **Portal existence as data** (SIG-INGEST-035, §17.6): a fetched portal emits a
  ``portal_exists = True`` claim; :func:`detect_portal_changes` turns a portal that
  drops out of a later snapshot into a ``portal_exists = False`` event **and** a
  research task, and a newly appeared portal into an event + a "no known
  deployment" task. An endpoint 404 / challenge is recorded as a first-class
  disappearance by the pipeline.
* **Sharing edges as configured access, directional, blanks-as-negatives**
  (SIG-ONTO-042/044): ``organizations_shared_with`` / ``organizations_received_from``
  become directional :class:`reconcile.sharing.SharingObservation` objects and are
  reconciled — across the whole snapshot, so asymmetry can fire — through P08.2's
  :func:`reconcile.sharing.reconcile_sharing` (SIG-RECON-034/035/036/037). Every
  single-snapshot edge carries ``valid_from_kind = 'unknown'``.
* **Snapshot diffing at the extracted-field level** (SIG-RECON-045): consecutive
  captures of one portal are reduced to :class:`reconcile.snapshot_diff.Capture`
  objects and diffed through P08.2's :func:`reconcile.snapshot_diff.diff_series`,
  yielding per-field change events with both values and both dates.
* **The SIG-INGEST-031 fallbacks, retained** as named routes (records acquisition,
  contributor capture, partner archive). Where the aggregator lacks a field for a
  portal, the connector routes to those channels instead of scraping the vendor.

Every row is stamped into the CC BY-SA 4.0 portal compartment with
``ai_training_permitted = false`` (SIG-LIC-004b), and rows are append-only
(P1–P3): no current-value columns, raw values preserved, corrections are new
assertions resolved downstream (P08.x), never overwrites.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from functools import cache
from typing import Any
from uuid import uuid4

from reconcile.sharing import (
    ACCESS_KINDS,
    SharingObservation,
    SharingReconciliation,
    reconcile_sharing,
)
from reconcile.snapshot_diff import Capture, FieldChangeEvent, diff_series

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

#: The registry source this connector runs against (§22.6 B; MIRROR + CC-BY-SA-4.0).
EYES_ON_FLOCK_SOURCE_ID = "eyes_on_flock"

#: The export compartment Eyes-on-Flock-derived claims land in (§42.2): the
#: CC-BY-SA-4.0 ``portal`` compartment, never the CC-BY ``sig_graph`` (SIG-LIC-004a).
CC_BY_SA_LICENSE = "CC-BY-SA-4.0"
PORTAL_COMPARTMENT = "portal"

#: The artifact-id prefix for a portal (its stable subject key is its slug).
PORTAL_ID_PREFIX = "flock_portal"

#: Research-task types this connector emits.
PORTAL_DISAPPEARED_TASK = "source_disappeared"
PORTAL_APPEARED_TASK = "flock_portal_appeared"

_DETECTOR_VERSION = "connectors.flock_portal/1"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `flock_portal` field→claim vocabulary (``data/flock_portal_vocab.toml``)."""
    return load_table("flock_portal_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def _fields() -> Mapping[str, Any]:
    return vocab()["fields"]


def _identity() -> Mapping[str, Any]:
    return vocab()["identity"]


def _sharing() -> Mapping[str, Any]:
    return vocab()["sharing"]


def fallback_routes() -> Mapping[str, Any]:
    """The three named SIG-INGEST-031 fallback routes (data-driven)."""
    return vocab().get("fallbacks", {})


def portal_id(slug: str) -> str:
    """The stable subject/artifact id for a portal keyed on its slug (§3.1)."""
    return f"{PORTAL_ID_PREFIX}:{slug}"


# --- the predicate allowlist (SIG-INGEST-033 analogue) ------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.4)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (§23.4)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §23.4 explicitly places out of scope for this connector.

    Contract facts, device geometry, and per-search / per-plate rows: named as
    data so the out-of-scope set is not a magic string. The allowlist is
    authoritative (anything outside it is refused); this is its complement.
    """
    return tuple(vocab()["forbidden_predicate_genres"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The `flock_portal` connector may write only the §23.4 predicates: contract
    facts, device geometry, and any per-search or per-plate row are refused here,
    at the ingestion boundary, not merely at resolution (SIG-INGEST-033 / §18.1).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the flock_portal connector may write only {sorted(predicate_allowlist())} "
            f"(§23.4, SIG-INGEST-033); {predicate!r} is outside the allowlist — contract "
            "facts, device geometry, and per-search/per-plate rows are refused."
        )
    return predicate


# --- change detection keyed on the upstream snapshot field (SIG-INGEST-030c) --


def snapshot_field_name() -> str:
    """The upstream field that keys change detection (SIG-INGEST-030c)."""
    return str(vocab()["snapshot_field"])


def upstream_refresh_days() -> int:
    """The upstream's own refresh cadence, in days (data, not code)."""
    return int(vocab()["upstream_refresh_days"])


def _parse_snapshot(raw: object) -> date | None:
    """Parse an upstream ``data_last_updated`` value to a date, or ``None``.

    Tolerant of the common shapes (``YYYY-MM-DD`` and ISO-8601 with time); an
    unparseable or empty value yields ``None`` rather than a guessed date
    (§3.1: no synthetic certainty).
    """
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def portal_snapshot_date(portal: Mapping[str, Any]) -> date | None:
    """One portal's upstream snapshot date, from its own ``data_last_updated``.

    This is the date used for ``observed_at`` and for change detection — the
    upstream's claim about the data's freshness, never SIG's fetch time
    (SIG-INGEST-030c).
    """
    return _parse_snapshot(portal.get(snapshot_field_name()))


def is_poll_due(
    current_snapshot: date | None,
    now: date,
    last_observed_snapshot: date | None,
) -> bool:
    """Whether SIG should poll the live API now, keyed on the snapshot (SIG-INGEST-030c).

    SIG MUST NOT poll faster than the upstream refreshes: polling adds load
    without adding information, because change is keyed on ``data_last_updated``,
    not fetch time. A poll is due only when there is no prior observation, the
    upstream's declared snapshot has advanced past the last one observed, or the
    upstream's refresh window has elapsed since that last observation. Pure and
    deterministic (no wall-clock read inside).
    """
    if last_observed_snapshot is None:
        return True
    if current_snapshot is not None and current_snapshot > last_observed_snapshot:
        return True
    earliest_next = last_observed_snapshot + timedelta(days=upstream_refresh_days())
    return now >= earliest_next


# --- parsing + the structural canary ------------------------------------------


def parse_json(data: bytes) -> dict[str, Any]:
    """Parse the Eyes on Flock JSON response into ``{summary, portals}``.

    Kept a pure function of the captured bytes (SIG-INGEST-002): the connector
    reads the archived capture back and calls this, never the network.
    """
    loaded = json.loads(data.decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Eyes on Flock response is not a JSON object")
    return loaded


def canary_findings(parsed: Mapping[str, Any]) -> list[str]:
    """Structural-drift findings for the aggregator response (SIG-PARSE-008).

    Committed fixtures (SIG-PARSE-007) pin known inputs and pass forever but
    cannot catch an upstream that quietly changes shape; the canary is the
    complement, run against a live response on a cadence. It asserts only the
    structure the parser depends on — a top-level ``portals`` array of objects
    each carrying a non-empty slug, and a ``summary`` object — and deliberately
    does NOT assert field *values*. An empty list means no drift.
    """
    findings: list[str] = []
    if "summary" not in parsed:
        findings.append("missing top-level 'summary' object")
    portals = parsed.get("portals")
    if portals is None:
        findings.append("missing top-level 'portals' array")
        return findings
    if not isinstance(portals, list):
        findings.append("'portals' is not an array")
        return findings
    slug_field = str(_identity()["slug_field"])
    for i, p in enumerate(portals):
        if not isinstance(p, Mapping):
            findings.append(f"portals[{i}] is not an object")
            continue
        if not str(p.get(slug_field, "")).strip():
            findings.append(f"portals[{i}] has an empty {slug_field!r}")
    return findings


def portal_slugs(parsed: Mapping[str, Any]) -> list[str]:
    """The ordered, de-duplicated slugs present in one response (for change detection)."""
    slug_field = str(_identity()["slug_field"])
    seen: dict[str, None] = {}
    for p in parsed.get("portals", []):
        slug = str(p.get(slug_field, "")).strip()
        if slug:
            seen.setdefault(slug, None)
    return list(seen)


# --- extraction: one raw record per portal ------------------------------------


def extract_portals(
    parsed: Mapping[str, Any], *, capture_digest: str = ""
) -> list[Mapping[str, Any]]:
    """Raw portal records with locators, preserving raw values (P2).

    Each record keeps the raw upstream portal object, its slug, its parsed
    snapshot date, and the capture digest for provenance. No typing or mapping
    happens here; that is :func:`normalize`.
    """
    slug_field = str(_identity()["slug_field"])
    portals = parsed.get("portals", [])
    if not isinstance(portals, list):
        return []
    out: list[Mapping[str, Any]] = []
    for p in portals:
        if not isinstance(p, Mapping):
            continue
        slug = str(p.get(slug_field, "")).strip()
        if not slug:
            continue
        out.append(
            {
                "record_kind": "flock_portal_raw",
                "slug": slug,
                "snapshot_date": portal_snapshot_date(p),
                "capture_digest": capture_digest,
                "raw": dict(p),
            }
        )
    return out


def _extracted_fields(portal: Mapping[str, Any]) -> dict[str, object]:
    """The upstream fields this connector maps, keyed by upstream field name.

    Only the fields named in ``vocab.fields`` are kept — the "extracted-field
    level" the snapshot diff (SIG-RECON-045) operates on. A field absent from the
    portal is absent from the returned mapping (distinct from present-and-empty).
    """
    out: dict[str, object] = {}
    for upstream_field in _fields():
        if upstream_field in portal:
            out[upstream_field] = portal[upstream_field]
    return out


# --- sharing: configured access, directional, blanks-as-negatives ------------


def _parse_org_list(value: object) -> list[str]:
    """Parse a sharing field to a list of partner names; blanks are negatives.

    An empty list, ``None``, or a blank string is a **negative** (no configured
    sharing) and returns ``[]`` — never an "unknown" edge. A list is returned
    stripped; a comma-separated string is split defensively.
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def sharing_observations_for_portal(
    portal: Mapping[str, Any], slug: str, observed_at: date
) -> list[SharingObservation]:
    """One portal's directional CONFIGURED-ACCESS observations (SIG-ONTO-042/044).

    ``organizations_shared_with`` means this portal has configured access *to* the
    partner (``slug`` → partner); ``organizations_received_from`` means a partner
    has configured access *to* this portal (partner → ``slug``). Both are single
    snapshots, so ``valid_from_kind = 'unknown'`` (SIG-RECON-036). Blank cells are
    negatives and produce no observation.
    """
    spec = _sharing()
    access_kind = str(spec["access_kind"])
    if access_kind not in ACCESS_KINDS:
        raise ValueError(f"invalid sharing access_kind {access_kind!r} in vocabulary")
    observations: list[SharingObservation] = []
    for partner in _parse_org_list(portal.get(str(spec["shared_with_field"]))):
        observations.append(
            SharingObservation(
                asserted_by=slug,
                from_org=slug,
                to_org=partner,
                access_kind=access_kind,
                observed_at=observed_at,
                from_single_snapshot=True,
            )
        )
    for partner in _parse_org_list(portal.get(str(spec["received_from_field"]))):
        observations.append(
            SharingObservation(
                asserted_by=slug,
                from_org=partner,
                to_org=slug,
                access_kind=access_kind,
                observed_at=observed_at,
                from_single_snapshot=True,
            )
        )
    return observations


def sharing_observations(portals: Iterable[Mapping[str, Any]]) -> list[SharingObservation]:
    """Every portal's sharing observations, for a single reconciliation pass.

    Feeding **all** portals' observations to :func:`reconcile.sharing.reconcile_sharing`
    at once is what lets asymmetry fire (SIG-RECON-035): A→B attested by A can be
    checked against B→A attested by B only when both are in the same call.
    """
    out: list[SharingObservation] = []
    for portal in portals:
        slug = str(portal.get(str(_identity()["slug_field"]), "")).strip()
        observed_at = portal_snapshot_date(portal)
        if not slug or observed_at is None:
            continue
        out.extend(sharing_observations_for_portal(portal, slug, observed_at))
    return out


def reconcile_portal_sharing(portals: Iterable[Mapping[str, Any]]) -> SharingReconciliation:
    """Reconcile the configured-access edges across a snapshot (via P08.2, §29.3)."""
    return reconcile_sharing(sharing_observations(portals))


# --- snapshot diffing at the extracted-field level (SIG-RECON-045) ------------


def portal_capture(portal: Mapping[str, Any], *, capture_digest: str) -> Capture:
    """Build a :class:`reconcile.snapshot_diff.Capture` for one portal snapshot."""
    slug = str(portal.get(str(_identity()["slug_field"]), "")).strip()
    snap = portal_snapshot_date(portal)
    if not slug:
        raise ValueError("portal has no slug")
    if snap is None:
        raise ValueError(f"portal {slug!r} has no parseable snapshot date")
    return Capture(
        artifact_id=portal_id(slug),
        capture_digest=capture_digest,
        captured_at=snap,
        fields=_extracted_fields(portal),
    )


def diff_portal_snapshots(captures: Sequence[Capture]) -> tuple[FieldChangeEvent, ...]:
    """Per-field change events across a chronological series of one portal's captures.

    A thin wrapper over P08.2's :func:`reconcile.snapshot_diff.diff_series`
    (SIG-RECON-045, owned there): the connector produces the captures and invokes
    that logic; it does not re-implement the diff.
    """
    return diff_series(captures)


# --- portal existence / disappearance (§17.6, SIG-INGEST-035) -----------------


def portal_exists_claim(
    slug: str, observed_at: date | None, exists: bool, *, attribution: str = ""
) -> dict[str, Any]:
    """A ``portal_exists`` claim — ``True`` on a fetched portal, ``False`` on disappearance.

    An event on the portal artifact (§17.6), kept distinct from the world event of
    a deployment ending: a portal vanishing from the aggregator is a change in the
    *transparency surface*, not proof the cameras were removed.
    """
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": portal_id(slug),
        "predicate_id": assert_predicate_allowed("portal_exists"),
        "event_class": "artifact_event",
        "value": exists,
        "raw_value": exists,
    }
    if observed_at is not None:
        row["observed_at"] = observed_at
    return _stamp(row, attribution=attribution)


def portal_disappearance_task(slug: str, *, last_seen: date | None = None) -> dict[str, Any]:
    """The research task a portal disappearance generates (§33.2, SIG-INGEST-035)."""
    note = f"Portal {slug!r} disappeared from the Eyes on Flock aggregator snapshot."
    if last_seen is not None:
        note += f" Last seen {last_seen.isoformat()}."
    return {
        "task_type": PORTAL_DISAPPEARED_TASK,
        "subject_id": portal_id(slug),
        "priority": 0.8,
        "closing_condition": (
            "the portal reappears in the aggregator OR a replacement source is "
            "registered OR the disappearance is confirmed permanent and annotated"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
        "note": note,
    }


def portal_appeared_task(slug: str, observed_at: date) -> dict[str, Any]:
    """A research task for a newly appeared portal — 'no known deployment' handling."""
    return {
        "task_type": PORTAL_APPEARED_TASK,
        "subject_id": portal_id(slug),
        "priority": 0.4,
        "closing_condition": (
            "confirm the portal corresponds to a known deployment OR annotate it as "
            "a portal with no known deployment"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
        "note": f"Portal {slug!r} appeared in the snapshot for {observed_at.isoformat()}.",
    }


def detect_portal_changes(
    previous_slugs: Iterable[str],
    current_slugs: Iterable[str],
    *,
    current_snapshot_date: date,
    previous_snapshot_date: date | None = None,
    attribution: str = "",
) -> list[dict[str, Any]]:
    """Portal appearance / disappearance events + tasks between two snapshots (SIG-INGEST-035).

    A portal present before and absent now yields a ``portal_exists = False`` event
    plus a ``source_disappeared`` task; a portal present now and absent before
    yields a ``portal_exists = True`` event plus a "no known deployment" task.
    Rows are returned sorted by slug for a deterministic feed.
    """
    previous = set(previous_slugs)
    current = set(current_slugs)
    rows: list[dict[str, Any]] = []
    for slug in sorted(current - previous):
        rows.append(portal_exists_claim(slug, current_snapshot_date, True, attribution=attribution))
        rows.append(
            _stamp(
                {
                    "record_kind": "research_task",
                    **portal_appeared_task(slug, current_snapshot_date),
                },
                attribution=attribution,
            )
        )
    for slug in sorted(previous - current):
        rows.append(
            portal_exists_claim(slug, current_snapshot_date, False, attribution=attribution)
        )
        rows.append(
            _stamp(
                {
                    "record_kind": "research_task",
                    **portal_disappearance_task(slug, last_seen=previous_snapshot_date),
                },
                attribution=attribution,
            )
        )
    return rows


# --- SIG-INGEST-031 fallbacks -------------------------------------------------


def fallback_tasks_for_gaps(
    portal: Mapping[str, Any], slug: str, *, attribution: str = ""
) -> list[dict[str, Any]]:
    """Research tasks routing to the SIG-INGEST-031 fallback channels for missing fields.

    Because the aggregator API is a single dependency, a field it does not carry
    for a portal is routed to a lawful fallback — records acquisition, contributor
    capture, or partner archive — never to a challenge-defeating crawler, which is
    NOT on the list and MUST NOT be added (SIG-INGEST-031). Records-request
    *generation* itself is P10.3; this connector only routes to it.
    """
    routes = fallback_routes()
    rows: list[dict[str, Any]] = []
    if "records_acquisition" in routes and not portal.get("data_retention"):
        rows.append(
            _fallback_task(
                "records_acquisition",
                slug,
                routes["records_acquisition"]["description"],
                priority=0.6,
                note=f"no configured_retention_days in the aggregator for {slug!r}",
                attribution=attribution,
            )
        )
    if "contributor_capture" in routes and not portal.get("prohibited_uses"):
        rows.append(
            _fallback_task(
                "contributor_capture",
                slug,
                routes["contributor_capture"]["description"],
                priority=0.5,
                note=f"no portal_stated_prohibited_use in the aggregator for {slug!r}",
                attribution=attribution,
            )
        )
    if (
        "partner_archive" in routes
        and not portal.get("organizations_shared_with")
        and not portal.get("organizations_received_from")
    ):
        rows.append(
            _fallback_task(
                "partner_archive",
                slug,
                routes["partner_archive"]["description"],
                priority=0.5,
                note=f"no configured sharing data in the aggregator for {slug!r}",
                attribution=attribution,
            )
        )
    return rows


def _fallback_task(
    task_type: str,
    slug: str,
    closing_condition: str,
    *,
    priority: float,
    note: str,
    attribution: str = "",
) -> dict[str, Any]:
    return _stamp(
        {
            "record_kind": "research_task",
            "task_type": task_type,
            "subject_id": portal_id(slug),
            "priority": priority,
            "closing_condition": closing_condition,
            "detector_version": _DETECTOR_VERSION,
            "status": "generated",
            "note": note,
        },
        attribution=attribution,
    )


# --- field-claim normalization ------------------------------------------------


def _normalized_value(raw: object) -> object:
    """The typed claim value beside the preserved raw value (P2)."""
    if isinstance(raw, bool):  # bool before int: bool is a subclass of int
        return raw
    if isinstance(raw, (int, list)):
        return raw
    if raw is None:
        return None
    return str(raw).strip()


def field_claim(
    slug: str,
    upstream_field: str,
    raw_value: object,
    observed_at: date | None,
    capture_digest: str,
    *,
    attribution: str = "",
) -> dict[str, Any] | None:
    """One field-level claim for a portal, or ``None`` when the value is absent.

    An empty/None value is negative space, not a claim (§3.1: no synthetic
    certainty). A windowed usage counter carries its window length (SIG-RECON-011).
    """
    spec = _fields()[upstream_field]
    predicate = assert_predicate_allowed(str(spec["predicate"]))
    value = _normalized_value(raw_value)
    if value is None or value == "" or value == []:
        return None
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": portal_id(slug),
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,
        "extracted_field": upstream_field,
        "capture_digest": capture_digest,
    }
    if spec.get("windowed"):
        row["windowed"] = True
        row["window_months"] = int(vocab()["window_months"])
    if observed_at is not None:
        row["observed_at"] = observed_at
    return _stamp(row, attribution=attribution)


def declared_freshness_claim(
    slug: str, portal: Mapping[str, Any], capture_digest: str, *, attribution: str = ""
) -> dict[str, Any]:
    """The portal's own declared freshness — recorded, never trusted as ``observed_at`` (§23.4)."""
    raw = portal.get(snapshot_field_name())
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": portal_id(slug),
        "predicate_id": assert_predicate_allowed("portal_last_updated_declared"),
        "value": str(raw).strip() if raw is not None else None,
        "raw_value": raw,
        "capture_digest": capture_digest,
        "note": "the portal's own claim about its freshness; never trusted as observed_at",
    }
    return _stamp(row, attribution=attribution)


def _sharing_edge_rows(
    reconciled: SharingReconciliation, *, attribution: str
) -> list[dict[str, Any]]:
    """The connector's L1 rows for the reconciled configured-access edges (§29.3).

    Only the **edges** enter the connector's deterministic claim stream. The
    asymmetry contradictions and research tasks are the §29.3 reconciler's to
    *emit* and persist (owned by P08.2, SIG-RECON-035): the connector produces the
    raw edges and invokes that logic (available on
    :meth:`FlockPortalConnector.reconcile_sharing`), but it does not fold the
    reconciler's freshly-minted (and non-deterministic) task ids into its own L1
    output, which would break the run's reproducibility fingerprint (SIG-INGEST-003).
    """
    rows: list[dict[str, Any]] = []
    for edge in reconciled.edges:
        rows.append(
            _stamp(
                {
                    "record_kind": "configured_access_edge",
                    "subject_id": portal_id(edge.from_org),
                    "predicate_id": assert_predicate_allowed("configured_sharing_partner"),
                    "from_org": edge.from_org,
                    "to_org": edge.to_org,
                    # §23.4 / SIG-RECON-034: configured access only, never observed_use.
                    "access_kind": edge.access_kind,
                    # SIG-RECON-036: a single-snapshot edge's start is UNKNOWN.
                    "valid_from_kind": edge.valid_from_kind,
                    "corroborated": edge.corroborated,
                    "observations_count": len(edge.observations),
                },
                attribution=attribution,
            )
        )
    return rows


# --- the connector ------------------------------------------------------------


@register
class FlockPortalConnector(Connector):
    """The `flock_portal` connector: the Eyes on Flock portal layer (§23.4, P11.1).

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire the
    aggregator JSON through the shared politeness layer (which honours a challenge
    as a refusal); ``parse``/``extract``/``normalize`` are pure functions of the
    capture that map each allowed upstream field to a SIG predicate, emit a
    ``portal_exists`` event and the portal's declared freshness, reconcile the
    configured-sharing edges across the whole snapshot through P08.2's §29.3
    reconciler, and route missing fields to the SIG-INGEST-031 fallbacks. Every
    row lands in the CC-BY-SA-4.0 portal compartment with ``ai_training_permitted
    = false``. Cross-capture snapshot diffing (SIG-RECON-045) and appearance /
    disappearance detection (SIG-INGEST-035) are module functions the backfill and
    change-feed drivers invoke.
    """

    name = "flock_portal"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — the live endpoint and/or archived captures.

        Targets come from ``ctx.parameters['targets']`` — each a ``{"url": ...}``.
        A Wayback-capture URL is a first-class target for historical back-fill
        (SIG-INGEST-030b): the connector treats it exactly like a live capture,
        because ``observed_at`` is keyed on the upstream snapshot field, not the
        fetch time (SIG-INGEST-030c).
        """
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only.

        Connectors hold no HTTP client of their own; the shared fetcher carries the
        descriptive UA, enforces robots + rate limits, and raises
        :class:`ChallengeEncountered` on a bot challenge — which the pipeline
        records as a disappearance (SIG-INGEST-011/013). There is no retry, no
        proxy rotation, no challenge solving here or anywhere in this connector.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- capture (inherited: the framework stores bytes content-addressed) --

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured JSON, carrying the capture digest for provenance.

        ``parse`` is the stage the :class:`CaptureRef` is available at, so the
        content-addressed digest is threaded forward here (stable for identical
        bytes, so reproducibility holds, SIG-INGEST-003).
        """
        parsed = parse_json(ctx.captures.get(capture.digest))
        return {**parsed, "_capture_digest": capture.digest}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw portal records with locators, preserving raw values (P2)."""
        return extract_portals(parsed, capture_digest=str(parsed.get("_capture_digest", "")))

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed claim rows beside preserved raw values (P2), confined to the allowlist.

        Per portal: a ``portal_exists`` event, the declared-freshness claim, and one
        claim per allowed upstream field (windowed counters carry their window).
        Once per snapshot: the configured-sharing edges reconciled across all
        portals (so asymmetry can fire), and any SIG-INGEST-031 fallback tasks. Every
        row is stamped into the CC-BY-SA-4.0 portal compartment with
        ``ai_training_permitted = false``.
        """
        attribution = _attribution(ctx)
        out: list[dict[str, Any]] = []
        portals: list[Mapping[str, Any]] = []

        for raw in raw_claims:
            slug = str(raw["slug"])
            portal = raw["raw"]
            observed_at = raw.get("snapshot_date")
            capture_digest = str(raw.get("capture_digest", ""))
            portals.append(portal)

            out.append(portal_exists_claim(slug, observed_at, True, attribution=attribution))
            out.append(
                declared_freshness_claim(slug, portal, capture_digest, attribution=attribution)
            )
            for upstream_field, raw_value in _extracted_fields(portal).items():
                claim = field_claim(
                    slug,
                    upstream_field,
                    raw_value,
                    observed_at,
                    capture_digest,
                    attribution=attribution,
                )
                if claim is not None:
                    out.append(claim)
            out.extend(fallback_tasks_for_gaps(portal, slug, attribution=attribution))

        # Reconcile sharing across the whole snapshot so §29.3 asymmetry can fire;
        # only the deterministic edges enter the claim stream (findings are P08.2's
        # to emit — see reconcile_sharing()).
        out.extend(_sharing_edge_rows(self.reconcile_sharing(portals), attribution=attribution))
        return out

    def reconcile_sharing(self, portals: Iterable[Mapping[str, Any]]) -> SharingReconciliation:
        """Invoke P08.2's §29.3 sharing-edge reconciler over a snapshot's portals.

        The full reconciliation — edges **and** the asymmetry contradictions /
        research tasks (SIG-RECON-035, owned by P08.2) — for a driver that persists
        the findings. The connector run itself streams only the edges.
        """
        return reconcile_portal_sharing(portals)

    # -- link + load --
    # link() is inherited (identity): the connector emits candidate identifiers (the
    # portal slug) and NEVER resolves entities itself; that is the identity layer.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _attribution(ctx: RunContext) -> str:
    """The Eyes on Flock required attribution string, from the source's rights record."""
    try:
        return ctx.source.rights.attribution
    except AttributeError:  # pragma: no cover - defensive; ctx.source is a SourceRecord
        return "Eyes on Flock (CC BY-SA 4.0)"


def _stamp(row: dict[str, Any], *, attribution: str = "") -> dict[str, Any]:
    """Stamp source attribution + the CC-BY-SA-4.0 portal compartment onto a row.

    Enforces the licence-compartment boundary on every row (SIG-LIC-004a): the
    ``portal`` compartment is CC-BY-SA-4.0 and MUST NOT be merged into the CC-BY
    ``sig_graph``. ``ai_training_permitted = false`` is stamped explicitly, so the
    training gate can refuse this content regardless of how the row travels
    downstream (SIG-LIC-004b).
    """
    row["source_attribution"] = attribution
    row.setdefault("source_id", EYES_ON_FLOCK_SOURCE_ID)
    row["license"] = CC_BY_SA_LICENSE
    row["compartment"] = PORTAL_COMPARTMENT
    row["ai_training_permitted"] = False
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 row needs.

    ``claim_id`` and ``sys_period`` are the two non-deterministic columns the
    reproducibility fingerprint excludes (SIG-INGEST-003), so replay is
    byte-identical modulo exactly these.
    """
    out: list[dict[str, Any]] = []
    for claim in claims:
        out.append(
            {
                **claim,
                "claim_id": str(uuid4()),
                "sys_period": f"[{datetime.now(UTC).isoformat()},)",
            }
        )
    return out


__all__ = [
    "CC_BY_SA_LICENSE",
    "EYES_ON_FLOCK_SOURCE_ID",
    "PORTAL_APPEARED_TASK",
    "PORTAL_COMPARTMENT",
    "PORTAL_DISAPPEARED_TASK",
    "PORTAL_ID_PREFIX",
    "FlockPortalConnector",
    "PredicateNotAllowed",
    "assert_predicate_allowed",
    "canary_findings",
    "declared_freshness_claim",
    "detect_portal_changes",
    "diff_portal_snapshots",
    "extract_portals",
    "fallback_routes",
    "fallback_tasks_for_gaps",
    "field_claim",
    "forbidden_predicate_genres",
    "is_poll_due",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "parse_json",
    "portal_appeared_task",
    "portal_capture",
    "portal_disappearance_task",
    "portal_exists_claim",
    "portal_id",
    "portal_slugs",
    "portal_snapshot_date",
    "predicate_allowlist",
    "reconcile_portal_sharing",
    "sharing_observations",
    "sharing_observations_for_portal",
    "snapshot_field_name",
    "upstream_refresh_days",
    "vocab",
    "vocab_version",
]
