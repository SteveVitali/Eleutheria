# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ACQ-01 registry / target / cadence generator (P35.6, I8 §8 row ACQ-01).

Turns the committed Round-11 acquisition plan
(``docs/build/planning/2026-09-30-next-phase/data/acquisition_plan.csv``) into
the data rows the family tickets review and commit: ``sources.toml``
``[sources.<id>]`` rows, registry ``[[targets]]`` rows, ``ops/cadence.toml``
``[[batches]]`` rows and ``live_dispositions.toml`` rows — plus a JSON run
manifest recording every decision, skip, dedupe and pending hand-off.

The generator is **machinery only** (P35.6 AC: no live stage):

* every emitted source row lands ``ingestion_permitted = false`` with
  ``spdx = "UNDETERMINED"`` / ``redistributable = false`` — the family ticket's
  rights review and the operator's HG-03 line decide, never the seed
  (SIG-INGEST-028, SIG-LIC-004);
* nothing is fetched, deployed or scheduled — output is text for review;
* the I8 design rules are enforced as **errors**, never silent fixes:

  * **R1** — a ``widen`` row (new dataset, same publisher/portal/licence as a
    flipped source) emits a ``[[targets]]`` row under the *existing* source,
    never a second source row;
  * **R2/NEW-5** — ids are ``<prefix>_<place>_<channel>``, ≤ 40 chars, lower
    snake, never truncated mid-token; a malformed seed id is recomputed from
    the seed fields. The generator rejects an id that collides with a
    registered source/target id, that is a string prefix of another id
    (either direction — ``camreg_dc`` vs ``camreg_dc_asc`` is ambiguous
    forever), or that duplicates a dataset already registered (NEW-1);
  * **R3** — every camera-class target carries the seed's SKOS
    ``technology`` slug; an ALPR/ATE-class row without one is an error (never
    a ``traffic_camera`` guess);
  * **R4** — every target carries ``jurisdiction_scheme = "iso.3166_2"`` with
    the *full* ISO code (``US-DE``, never ``DE``); a sub-state geography is
    recorded in ``jurisdiction_place`` until PKG-06a/K4 land GEOIDs.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PLAN_DIR = REPO_ROOT / "docs/build/planning/2026-09-30-next-phase/data"
DEFAULT_PLAN = PLAN_DIR / "acquisition_plan.csv"
DEFAULT_CANDIDATES = PLAN_DIR / "candidates_consolidated.csv"
DEFAULT_PLAN_ROWS = PLAN_DIR / "round11_plan.csv"
SOURCES_TOML = REPO_ROOT / "connectors/src/connectors/data/sources.toml"
TARGET_FILES = (
    REPO_ROOT / "connectors/src/connectors/data/camera_registry_targets.toml",
    REPO_ROOT / "connectors/src/connectors/data/dot_511_targets.toml",
)

#: R2 — the per-family id prefixes. `camreg_` covers camera/ALPR/ATE layers.
R2_PREFIXES: tuple[str, ...] = (
    "camreg_",
    "dot_511_",
    "procportal_",
    "statrep_",
    "ccops_",
    "policy_",
    "grant_",
    "agenda_",
    "legis_",
)
MAX_ID_LEN = 40
_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

#: Plan-family keyword → R2 prefix, used when the seed's proposed id is absent
#: or malformed (NEW-5: recompute from the seed fields, never truncate).
_FAMILY_PREFIX: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p, re.I), pre)
    for p, pre in (
        (
            r"dot_511|camera|alpr|ate\b|traffic.?enforcement|ckan|opendatasoft|"
            r"dataeuropa|hub_search|geojson|csv_file|xlsx|ogc|wfs|django|sutra",
            "camreg_",
        ),
        (r"511", "dot_511_"),
        (r"procurement|contract|checkbook|coop", "procportal_"),
        (
            r"disclosure|statut|mandated|oig|oversight|federal|accountability|"
            r"curated_index|ai_inventory|287g|register|record",
            "statrep_",
        ),
        (r"ccops|self.?disclosure|dossier", "ccops_"),
        (r"polic", "policy_"),
        (r"grant", "grant_"),
        (r"agenda|legistar|civicweb|onbase|agendaonline", "agenda_"),
        (r"legis|bill|statute_seed", "legis_"),
    )
)

#: Registry ``kind`` values the ``dot_511`` connector can actually expand
#: today. Aggregate transports (`arcgis_outstatistics`, `socrata_aggregate`)
#: are ACQ-20's `extend:` work — a target emitted for an un-expandable kind
#: would raise inside ``registry_targets`` on a *permitted* source, so the
#: generator records those rows in the manifest as ``pending_kind`` instead of
#: writing a row that breaks the live path.
EXPANDABLE_KINDS: frozenset[str] = frozenset({"arcgis_query", "socrata_rows"})

#: §7.1 — the wave batches the CSV's `monthly@r11-<name>(<cron>)` strings name,
#: plus the Wave-D tier-2 buckets the plan leaves "assigned at ticket"
#: (`r11-tier2` placeholder → the three reviewed day-25/26/27 crons).
TIER2_BATCHES: tuple[tuple[str, str], ...] = (
    ("r11-tier2-01", "37 7 25 * *"),
    ("r11-tier2-02", "37 7 26 * *"),
    ("r11-tier2-03", "37 7 27 * *"),
)
#: §7.1 — the Round-11 batches run at the 6h per-row bound, not the legacy 36h.
R11_TASK_TIMEOUT = "6h"

#: Non-ACQ owning work items a plan `ticket` cell may name, resolved to their
#: recorded manifest owner (docs/tickets/DEFERRALS.md owner cells —
#: D-R10-SOURCES-1's live-capture legs are P37.16a/b; its prep half P34.38
#: already landed). A marker absent here is an unresolved cell, an error —
#: never an invented owner.
NON_ACQ_OWNERS: tuple[tuple[str, str], ...] = (("D-R10-SOURCES-1", "P37.16a"),)

_BATCH_RE = re.compile(r"^(?P<cad>\w+)@(?P<name>[\w-]+?)(?:\((?P<cron>[^)]+)\))?\s*$")
_EXISTING_JOB_RE = re.compile(r"^(?P<cad>\w+)@(?P<name>[\w-]+)$")
_ALNUM = re.compile(r"[^a-z0-9]+")


class GenerationError(Exception):
    """A plan/seed row the R1–R4 rules refuse; carried to the manifest."""


def _slug(text: str) -> str:
    """Lower-snake slug of arbitrary seed text (never truncated mid-token)."""
    return _ALNUM.sub("_", text.lower()).strip("_")


def _tokens(text: str) -> list[str]:
    return [t for t in _slug(text).split("_") if t]


def family_prefix(family: str) -> str:
    """The R2 prefix a plan family generates under."""
    for pattern, prefix in _FAMILY_PREFIX:
        if pattern.search(family):
            return prefix
    return "camreg_"  # acquisition rows are camera-class unless named otherwise


def normalize_id(proposed: str, *, family: str, geography: str, name: str) -> str:
    """R2/NEW-5 — normalize a permanent id; recompute malformed seeds.

    ``proposed`` is the seed's ``proposed_source_id``. A well-formed proposal
    is kept as-is; a malformed or oversized one is recomputed as
    ``<family_prefix><place>_<channel>`` from the seed's geography and name —
    whole tokens only, never a mid-token cut. Raises :class:`GenerationError`
    when no ≤ 40-char id survives.
    """
    candidate = _slug(proposed)
    if (
        not _ID_RE.match(candidate)
        or len(candidate) > MAX_ID_LEN
        or not any(candidate.startswith(p) for p in R2_PREFIXES)
    ):
        prefix = family_prefix(family)
        place = _tokens(geography.split(":")[0].lower().replace("us-", "").replace("-", "_"))
        # The sub-state place ("US-CA:San Diego" → "san","diego") is part of
        # the identity's stable half — without it two councils in one state
        # recompute to the same id (the NEW-1 ambiguity the recompute exists
        # to break).
        if ":" in geography:
            place += _tokens(geography.split(":", 1)[1])
        channel = _tokens(name)
        parts = list(dict.fromkeys([*place, *channel]))  # dedupe, keep order
        # Drop channel tokens (rightmost) until the id fits — the prefix and
        # place are the identity's stable part, the channel is descriptive.
        while parts and len(prefix) + len("_".join(parts)) > MAX_ID_LEN:
            parts.pop()
        candidate = prefix + "_".join(parts)
    if not _ID_RE.match(candidate):
        raise GenerationError(
            f"cannot derive a lower-snake id from {proposed!r} (family {family!r})"
        )
    if len(candidate) > MAX_ID_LEN:
        raise GenerationError(f"no ≤{MAX_ID_LEN}-char id derivable from {proposed!r}")
    if not any(candidate.startswith(p) for p in R2_PREFIXES):
        raise GenerationError(f"id {candidate!r} carries no R2 family prefix ({R2_PREFIXES})")
    return candidate


def check_id_collisions(emitted: Iterable[str], *, existing: Iterable[str]) -> list[str]:
    """R2 — every collision/prefix relation, as human-readable error strings."""
    ids = sorted(set(emitted))
    have = set(existing)
    errors: list[str] = []
    for i, a in enumerate(ids):
        if a in have:
            errors.append(f"id {a!r} collides with a registered source/target id (NEW-1)")
        for b in ids[i + 1 :]:
            if b.startswith(a + "_") or a.startswith(b + "_"):
                errors.append(f"ids {a!r} and {b!r} stand in a prefix relation (ambiguous)")
    for a in ids:
        if a not in have:
            for b in sorted(have):
                if b.startswith(a + "_") or a.startswith(b + "_"):
                    errors.append(f"id {a!r} stands in a prefix relation with registered id {b!r}")
                    break
    return errors


def _plan_ticket(plan_row: Mapping[str, str], family: str = "") -> str:
    """The `ACQ-NN` unit id a plan row routes to ("" if none).

    `ACQ-23` was split a/b in the manifest (`R11-ACQ-23a` → P37.69a
    international portals, `R11-ACQ-23b` → P37.69b OGC WFS); the plan cell
    still says the un-split `ACQ-23`, so the family decides — `ogc`/`wfs`
    routes to `ACQ-23b`, everything else to `ACQ-23a`.
    """
    m = re.search(r"ACQ-\d+", plan_row.get("ticket") or "")
    if not m:
        return ""
    acq = m.group(0)
    if acq == "ACQ-23":
        return "ACQ-23b" if re.search(r"ogc|wfs", family, re.I) else "ACQ-23a"
    return acq


def _class_tickets(plan_rows_csv: Path) -> dict[str, str]:
    """`ACQ-08` → `P36.4` from `round11_plan.csv` (`cat_ids` `R11-ACQ-08`).

    Only rows whose `id` is a manifest ticket (`P<phase>.<n>`) count — the
    plan also carries `moved`/`later` bookkeeping rows whose `id` IS the
    `R11-ACQ-*` token itself (e.g. the `R11-ACQ-23a` → `P37.69a` move), and
    mapping a class to a non-ticket id is a bogus `class_ticket`."""
    out: dict[str, str] = {}
    if not plan_rows_csv.exists():
        return out
    with plan_rows_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            ticket = row["id"].strip()
            if not re.match(r"^P\d+\.\d+", ticket):
                continue
            for cat in (row.get("cat_ids") or "").split(";"):
                cat = cat.strip()
                if cat.startswith("R11-ACQ-"):
                    out[cat.removeprefix("R11-")] = ticket
    return out


def _existing_ids() -> tuple[set[str], set[str], set[str], dict[str, str], dict[str, Any]]:
    """Registered state: source ids, target ids, layer urls, url→source owner,
    and the committed ``[sources.*]`` table (for convergence checks)."""
    source_table = tomllib.loads(SOURCES_TOML.read_text()).get("sources", {})
    source_ids = set(source_table)
    target_ids: set[str] = set()
    layer_urls: set[str] = set()
    layer_owners: dict[str, str] = {}
    for path in TARGET_FILES:
        if not path.exists():
            continue
        doc = tomllib.loads(path.read_text())
        for row in doc.get("targets", []):
            if row.get("id"):
                target_ids.add(str(row["id"]))
            for key in ("layer_url", "url"):
                if row.get(key):
                    layer_urls.add(str(row[key]).rstrip("/"))
                    layer_owners[str(row[key]).rstrip("/")] = str(row.get("source_id") or "")
    return source_ids, target_ids, layer_urls, layer_owners, source_table


def _is_own_generated_row(row: Mapping[str, Any]) -> bool:
    """True when a committed ``[sources.<id>]`` row is an ACQ-01 emission —
    the provenance marker the generator stamps in ``notes`` — making a
    re-run's identical proposal *converged*, never a NEW-1 collision."""
    return (
        "R11-ACQ-01 generated row" in str(row.get("notes") or "")
        and row.get("ingestion_permitted") is False
    )


def _candidate_rows(candidates_csv: Path) -> dict[str, dict[str, str]]:
    """`cand_id` → candidate row (``cand_ids_merged`` may hold several)."""
    out: dict[str, dict[str, str]] = {}
    with candidates_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            for cid in re.split(r"[;,]", row.get("cand_ids_merged") or ""):
                cid = cid.strip()
                if cid:
                    out.setdefault(cid, row)
    return out


def _geo_state(geographies: str) -> tuple[str, str]:
    """(iso.3166_2 code, sub-state place name) from `US-IL:Cook County`."""
    geo = (geographies or "").strip()
    place = ""
    if ":" in geo:
        geo, place = geo.split(":", 1)
        place = place.strip()
    return geo.strip(), place


def _technology_slug(candidate: Mapping[str, str]) -> str:
    """R3 — the seed's primary SKOS technology slug, "" when absent."""
    concepts = candidate.get("ontology_concepts") or ""
    first = concepts.split(";")[0].strip()
    return first.split("(")[0].strip() if first else ""


def _target_kind(family: str) -> str:
    """The registry `kind` a plan family maps to, or "" for non-layer rows.

    Only a plain ``dot_511(<transport>)`` family produces a registry
    ``[[targets]]`` row — `extend:`/`new:` families are transports the
    connector does not carry yet, and every other family (documents, index
    vocab, tenant tables) registers under the family ticket's own data files.
    """
    if not family or family.startswith(("extend:", "new:")):
        return ""
    m = re.match(r"dot_511\(([^)]+)\)", family)
    if not m:
        return ""
    inner = m.group(1).lower().split()[0].rstrip(":")
    if inner in EXPANDABLE_KINDS:
        return inner
    return "pending:" + inner  # ACQ-20 aggregate transports — manifest only


def _rights_lane_posture(candidate: Mapping[str, str]) -> tuple[str, str]:
    """(compact_status, custody_posture) from the seed's rights lanes."""
    lane = (candidate.get("i7_rights_lane") or "").lower()
    raw = (candidate.get("i7_raw_lane_j4") or "").lower()
    compact = "public_terms_only" if (lane or candidate.get("licence_guess")) else "not_contacted"
    custody = "MIRROR" if "raw-ok" in raw else "DERIVE"
    return compact, custody


def _source_kind(candidate: Mapping[str, str], family: str) -> str:
    pub = (candidate.get("publisher_type") or "").lower()
    if "disclosure" in family or "ccops" in family:
        return "government_mandated_disclosure"
    if "gov" in pub or "municipal" in pub or "agency" in pub:
        return "government_portal"
    if "vendor" in pub:
        return "vendor_site"
    if "academ" in pub or "research" in pub:
        return "academic"
    if "nonprofit" in pub or "civil" in pub or "community" in pub:
        return "community"
    return "government_portal"


def _toml_str(value: Any) -> str:
    return json.dumps(str(value))


def _toml_array(items: Iterable[str]) -> str:
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


@dataclass
class Generation:
    """Everything one generator run produced."""

    sources: list[dict[str, Any]] = field(default_factory=list)
    targets: list[dict[str, Any]] = field(default_factory=list)
    batches: dict[str, dict[str, Any]] = field(default_factory=dict)
    dispositions: dict[str, dict[str, str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)

    def ok(self) -> bool:
        return not self.errors


def _emit_source(
    gen: Generation,
    *,
    plan_row: Mapping[str, str],
    cand: Mapping[str, str],
    source_id: str,
    class_ticket: str,
) -> None:
    """One fail-closed `[sources.<id>]` row (R2 id; never permitted)."""
    compact, custody = _rights_lane_posture(cand)
    name = cand.get("proposed_name") or cand.get("name") or source_id
    pub = cand.get("proposed_publisher") or cand.get("publisher") or ""
    licence = cand.get("proposed_licence") or cand.get("licence_guess") or ""
    geo, place = _geo_state(cand.get("geographies") or "")
    notes = (
        f"R11-ACQ-01 generated row (plan {plan_row['plan_id']}, cand "
        f"{','.join(_cand_ids(plan_row))}, family {plan_row['family']!r}, "
        f"ticket {plan_row.get('ticket', '')}, class ticket {class_ticket or 'unresolved'}). "
        f"STAYS GATED: "
        f"ingestion_permitted=false pending the operator's HG-03 line "
        f"({plan_row.get('rights_batch', '')}); rights UNDETERMINED — licence "
        f"lead {licence!r} is seed evidence for the family ticket's rights "
        f"review, not a resolved record. Proposed id {cand.get('proposed_source_id')!r}."
    )
    row: dict[str, Any] = {
        "name": name,
        "source_kind": _source_kind(cand, plan_row["family"]),
        "homepage_url": cand.get("url", ""),
        "default_tier": "R1" if "gov" in (cand.get("publisher_type") or "").lower() else "R4",
        "custody_posture": custody,
        "compact_status": compact,
        "robots_policy": "honor",
        "access_method": (
            (cand.get("i7_access_mode") or cand.get("format_access") or "")
            + " — registration prepared by ACQ-01; family ticket wires the connector map"
        ).strip(" —"),
        "auth_model": "none",
        "cadence": cand.get("proposed_cadence") or cand.get("i7_cadence") or "",
        "ingestion_permitted": False,
        "reliability_provisional": True,
        "verified": False,
        "notes": notes,
        "rights": {"spdx": "UNDETERMINED", "redistributable": False},
    }
    if pub:
        row["publisher"] = pub
    if geo:
        row["jurisdiction_scheme"] = "iso.3166_2"
        row["jurisdiction"] = geo
    if place:
        row["jurisdiction_place"] = place
    gen.sources.append({"id": source_id, "row": row})


def _emit_target(
    gen: Generation,
    *,
    plan_row: Mapping[str, str],
    cand: Mapping[str, str],
    source_id: str,
    existing_target_ids: set[str],
    existing_layer_urls: set[str],
    existing_layer_owners: dict[str, str],
    emitted_target_ids: set[str],
) -> None:
    """One registry `[[targets]]` row — widen rows land under the EXISTING source (R1)."""
    kind = _target_kind(plan_row["family"])
    geo, place = _geo_state(cand.get("geographies") or "")
    layer_url = (cand.get("url") or "").rstrip("/")
    if layer_url and layer_url in existing_layer_urls:
        owner = existing_layer_owners.get(layer_url, "")
        if owner == source_id:
            gen.notes.append(
                f"{plan_row['plan_id']}: target {layer_url} already registered "
                f"under {source_id} (converged — an earlier ACQ-01 emission)"
            )
        else:
            gen.errors.append(
                f"{plan_row['plan_id']}: dataset {layer_url} is already registered "
                f"as a target under {owner!r} (NEW-1 dedupe) — no second row"
            )
        return
    if kind.startswith("pending:"):
        gen.notes.append(
            f"{plan_row['plan_id']}: {source_id} target held — kind "
            f"{kind.removeprefix('pending:')!r} lands with ACQ-20's extend transport; "
            "emitted to the manifest pending list, never a broken [[targets]] row"
        )
        gen.manifest.setdefault("pending_kind", []).append(
            {
                "plan_id": plan_row["plan_id"],
                "source_id": source_id,
                "kind": kind.removeprefix("pending:"),
                "layer_url": layer_url,
            }
        )
        return
    if not kind:
        return  # non-layer family (documents, indexes) — family vocab owns targets
    slug = _slug(cand.get("proposed_name") or cand.get("name") or "")
    target_id = slug or f"{source_id}_target"
    while len(target_id) > 100 and "_" in target_id:
        target_id = target_id.rsplit("_", 1)[0]  # drop whole tokens only
    if target_id in existing_target_ids or target_id in emitted_target_ids:
        gen.errors.append(
            f"{plan_row['plan_id']}: computed target id {target_id!r} already registered"
        )
        return
    emitted_target_ids.add(target_id)
    tech = _technology_slug(cand)
    row: dict[str, Any] = {
        "id": target_id,
        "source_id": source_id,
        "kind": kind,
        "platform": "arcgis" if kind == "arcgis_query" else "socrata",
        "url": layer_url,
        "layer_url": layer_url,
        "agency": cand.get("proposed_publisher") or cand.get("publisher") or "",
        "state": geo or "",
        "jurisdiction_scheme": "iso.3166_2",
        "observed_count": 0,
        "enum_source": f"r11-acq-01:{plan_row['plan_id']}",
        "notes": (
            f"ACQ-01 generated target (plan {plan_row['plan_id']}, cand "
            f"{','.join(_cand_ids(plan_row))}). observed_count/out_fields/"
            f"object_id_field pinned at the family ticket's registration review; "
            f"licence lead "
            f"{cand.get('proposed_licence') or cand.get('licence_guess') or 'UNDETERMINED'}."
        ),
    }
    if place:
        row["jurisdiction_place"] = place
    if tech:
        row["technology"] = tech
    elif re.search(r"alpr|ate\b|camera", plan_row["family"], re.I):
        gen.errors.append(
            f"{plan_row['plan_id']}: camera-class target {target_id!r} carries no "
            "SKOS technology slug — R3 refuses a traffic_camera default (PKG-07)"
        )
        return
    # F-330: the emitted row is clean by construction (no observed/out fields
    # yet), but run the denylist over whatever the row does carry — the check
    # bites the moment a review adds fields.
    from connectors.field_denylist import assert_target_fields_clean

    assert_target_fields_clean(row)
    gen.targets.append(row)


def _cand_ids(plan_row: Mapping[str, str]) -> list[str]:
    return [c.strip() for c in re.split(r"[;,+]", plan_row.get("cand_ids") or "") if c.strip()]


def _cadence_route(gen: Generation, plan_row: Mapping[str, str], source_id: str | None) -> None:
    """Route one row's `cadence` cell: batch member, existing-job coverage, or pending."""
    cad = (plan_row.get("cadence") or "").strip()
    batch = _BATCH_RE.match(cad)
    if batch and batch.group("name").startswith("r11-"):
        name = batch.group("name")
        cron = (batch.group("cron") or "").strip()
        entry = gen.batches.setdefault(
            name,
            {
                "id": name,
                "cadence": batch.group("cad"),
                "cron": "",
                "job": f"sig-ingest-{name}",
                "scheduler": f"sig-sched-{name}",
                "task_timeout": R11_TASK_TIMEOUT,
                "members": [],
                "note": f"Round-11 batch {name} (I8 §7.1; ACQ-01 generated; created --paused, R6).",
            },
        )
        if cron:
            if entry["cron"] and entry["cron"] != cron:
                gen.errors.append(
                    f"batch {name} declares conflicting crons {entry['cron']!r} vs {cron!r}"
                )
            else:
                entry["cron"] = cron
        if source_id:
            entry["members"].append(source_id)
        return
    if "r11-tier2" in cad:
        gen.manifest.setdefault("tier2_members", []).append(
            {"plan_id": plan_row["plan_id"], "source_id": source_id}
        )
        return
    if source_id is None:
        gen.notes.append(f"{plan_row['plan_id']}: widen row covered by existing schedule — {cad}")
        return
    if cad.startswith("existing ") or cad.startswith("n/a") or cad.startswith("once") or not cad:
        gen.notes.append(
            f"{plan_row['plan_id']}: {source_id} cadence cell {cad!r} — no cadence row "
            "emitted; the family ticket assigns one (never silently scheduled)"
        )
        return
    job = _EXISTING_JOB_RE.match(cad)
    if job:
        gen.errors.append(
            f"{plan_row['plan_id']}: {source_id} names existing job {job.group('name')!r} — "
            "a new source cannot ride a per-source job; assign a batch (R6)"
        )
        return
    gen.errors.append(f"{plan_row['plan_id']}: unrecognised cadence cell {cad!r}")


def _widen_covering_source(
    plan_row: Mapping[str, str], cand: Mapping[str, str], source_ids: set[str]
) -> str:
    """R1 — the existing flipped source a `widen` row lands under.

    Resolution order, all from committed data:

    1. the `cadence` cell's named job/batch — `existing sig-sched-<sid>`,
       `existing camreg-batch-NN (cron) of <sid>`, `monthly@<sid>` (legistar,
       usaspending, osm_overpass), `monthly@sig-sched-<sid>(cron)`;
    2. the candidate's `registry_match` — `related:<sid>`, `duplicate:<sid>`,
       `same-as:<sid>`, with each R2 prefix tried for a bare id
       (`concord_ca` → `camreg_concord_ca`).

    Returns "" when nothing resolves — the caller decides whether that's an
    error (a layer family needs a real source) or a note (vocab-table widens
    are owned by the family ticket's data files).
    """
    cad = (plan_row.get("cadence") or "").strip()
    m = re.search(
        r"(?:existing sig-sched-|existing \S+ .*? of |monthly@sig-sched-|monthly@)([\w-]+)",
        cad,
    )
    if m:
        name = m.group(1)
        for base in (name, name.replace("-", "_")):
            for cand_id in (base, *(f"{p}{base}" for p in R2_PREFIXES)):
                if cand_id in source_ids:
                    return cand_id
    match = cand.get("registry_match") or ""
    m = re.search(r"(?:related|duplicate|same[-_]?as)[:=]\s*([\w-]+)", match)
    if m:
        name = m.group(1)
        for base in (name, name.replace("-", "_")):
            for cand_id in (base, *(f"{p}{base}" for p in R2_PREFIXES)):
                if cand_id in source_ids:
                    return cand_id
    return ""


def _declared_same_source(cand: Mapping[str, str], source_ids: set[str]) -> str:
    """The registered source the seed *declares identical* — ``same-as:``/
    ``duplicate:`` only (``related:`` is affinity, never identity). A plan
    ``new-row`` whose seed already knows it is the registered row
    (`same-as:ccops_boston`, rights_batch "existing gated registry rows
    (flip)") is R1 dedupe evidence, not a NEW-1 collision."""
    match = cand.get("registry_match") or ""
    m = re.search(r"(?:duplicate|same[-_]?as)[:=]\s*([\w-]+)", match)
    if not m:
        return ""
    name = m.group(1)
    for base in (name, name.replace("-", "_")):
        for cand_id in (base, *(f"{p}{base}" for p in R2_PREFIXES)):
            if cand_id in source_ids:
                return cand_id
    return ""


def _url_root(url: str) -> str:
    """The service root of a layer URL (``.../MapServer/22`` →
    ``.../MapServer``) — two layers on one service document are one channel."""
    url = url.rstrip("/")
    return url[: url.rfind("/")] if "/" in url else url


def _same_channel(a: Mapping[str, str], b: Mapping[str, str]) -> bool:
    """R1 same publisher+channel evidence: identical URLs or identical
    service roots (two layers on one MapServer/FeatureServer — e.g. the two
    WVDOT Assets layers — are one channel's datasets)."""
    au, bu = (a.get("url") or "").rstrip("/"), (b.get("url") or "").rstrip("/")
    if au and au == bu:
        return True
    if au and bu and _url_root(au) == _url_root(bu):
        return True
    return False


def _dedupe_under(
    gen: Generation,
    *,
    plan_row: Mapping[str, str],
    cand: Mapping[str, str],
    proposed: str,
    under: str,
    target_ids: set[str],
    layer_urls: set[str],
    layer_owners: dict[str, str],
    emitted_target_ids: set[str],
    why: str,
) -> None:
    """R1 dedupe — `proposed` lands under registered/emitted source `under`
    as a target (layer families) or a manifest note (non-layer families)."""
    kind = _target_kind(plan_row["family"])
    if kind:
        gen.notes.append(
            f"{plan_row['plan_id']}: {proposed} deduped under existing source "
            f"{under} (R1 — one row per publisher+channel; emitted as a target)"
        )
        _emit_target(
            gen,
            plan_row=plan_row,
            cand=cand,
            source_id=under,
            existing_target_ids=target_ids,
            existing_layer_urls=layer_urls,
            existing_layer_owners=layer_owners,
            emitted_target_ids=emitted_target_ids,
        )
    else:
        gen.notes.append(
            f"{plan_row['plan_id']}: {proposed} deduped under existing source "
            f"{under} (R1) — non-layer family; family ticket's tables carry it"
        )
    gen.manifest.setdefault("deduped", []).append(
        {"plan_id": plan_row["plan_id"], "proposed_source_id": proposed, "under": under, "why": why}
    )
    _cadence_route(gen, plan_row, None)


def _assign_tier2(gen: Generation) -> None:
    """§7.1 — the Wave-D `r11-tier2` placeholder becomes three reviewed batches."""
    members = gen.manifest.pop("tier2_members", [])
    if not members:
        return
    ids = [m["source_id"] for m in members if m["source_id"]]
    n = len(TIER2_BATCHES)
    per = -(-len(ids) // n) if ids else 0
    for i, (name, cron) in enumerate(TIER2_BATCHES):
        chunk = ids[i * per : (i + 1) * per]
        gen.batches[name] = {
            "id": name,
            "cadence": "monthly",
            "cron": cron,
            "job": f"sig-ingest-{name}",
            "scheduler": f"sig-sched-{name}",
            "task_timeout": R11_TASK_TIMEOUT,
            "members": chunk,
            "note": (
                f"Round-11 Wave-D batch {name} (I8 §7.1 days 25–27 07:37Z; "
                "members assigned deterministically by ACQ-01 — ACQ-27 may re-balance)."
            ),
        }


def generate(
    *,
    plan_csv: Path = DEFAULT_PLAN,
    candidates_csv: Path = DEFAULT_CANDIDATES,
    plan_rows_csv: Path = DEFAULT_PLAN_ROWS,
    only_rows: frozenset[str] = frozenset(),
    only_families: tuple[str, ...] = (),
) -> Generation:
    """Run the generator; the returned :class:`Generation` carries every row."""
    gen = Generation()
    candidates = _candidate_rows(candidates_csv)
    class_tickets = _class_tickets(plan_rows_csv)
    source_ids, target_ids, layer_urls, layer_owners, source_table = _existing_ids()
    emitted_ids: set[str] = set()
    converged_ids: set[str] = set()
    emitted_cands: dict[str, Mapping[str, str]] = {}
    emitted_target_ids: set[str] = set()

    with plan_csv.open(newline="") as fh:
        plan = [r for r in csv.DictReader(fh) if r.get("action") != "defer"]

    for row in plan:
        if only_rows and row["plan_id"] not in only_rows:
            continue
        if only_families and not any(f in row["family"] for f in only_families):
            continue
        cands = _cand_ids(row)
        cand = next((candidates[c] for c in cands if c in candidates), None)
        if cand is None:
            gen.errors.append(f"{row['plan_id']}: no candidate row for cand_ids {cands} (R4 join)")
            continue
        acq = _plan_ticket(row, row["family"])
        class_ticket = class_tickets.get(acq, "")
        widen = row["action"] == "widen"

        if widen:
            existing_source = _widen_covering_source(row, cand, source_ids)
            kind = _target_kind(row["family"])
            if not existing_source:
                # Non-layer widens (vocab/tenant/index tables) are owned by the
                # family ticket's data files — a note, never a fabricated
                # source row. A *layer* widen with no resolvable source is an
                # R1 refusal.
                if kind:
                    gen.errors.append(
                        f"{row['plan_id']}: widen row names registry_match "
                        f"{(cand.get('registry_match') or '')!r} / cadence "
                        f"{row.get('cadence')!r} — no existing source resolves it "
                        "(R1 refuses a new row)"
                    )
                else:
                    gen.notes.append(
                        f"{row['plan_id']}: config widen under "
                        f"{(cand.get('registry_match') or row.get('cadence'))!r} — "
                        "vocab/target table owned by the family ticket"
                    )
                _cadence_route(gen, row, None)
                continue
            if kind:
                _emit_target(
                    gen,
                    plan_row=row,
                    cand=cand,
                    source_id=existing_source,
                    existing_target_ids=target_ids,
                    existing_layer_urls=layer_urls,
                    existing_layer_owners=layer_owners,
                    emitted_target_ids=emitted_target_ids,
                )
            else:
                gen.notes.append(
                    f"{row['plan_id']}: widen under {existing_source} — non-layer "
                    "family; the family ticket's vocab/target rows carry it"
                )
            _cadence_route(gen, row, None)
            continue

        # new-row / new-connector — a permanent source id (R2, NEW-5).
        try:
            source_id = normalize_id(
                cand.get("proposed_source_id") or "",
                family=row["family"],
                geography=(cand.get("geographies") or ""),
                name=cand.get("proposed_name") or cand.get("name") or row["plan_id"],
            )
        except GenerationError as exc:
            gen.errors.append(f"{row['plan_id']}: {exc}")
            continue
        # R1 dedupe, strongest evidence first:
        # (a) the seed declares itself identical to a registered source
        #     (`same-as:ccops_boston` — a "flip existing row" batch carried as
        #     new-row). It becomes a target/merge under that source, never a
        #     second row or a NEW-1 collision.
        declared = _declared_same_source(cand, source_ids)
        if declared:
            _dedupe_under(
                gen,
                plan_row=row,
                cand=cand,
                proposed=source_id,
                under=declared,
                target_ids=target_ids,
                layer_urls=layer_urls,
                layer_owners=layer_owners,
                emitted_target_ids=emitted_target_ids,
                why="declared same-as/duplicate",
            )
            continue
        # (b) a proposed *new* source whose id sits under a registered source
        #     (`camreg_bellevue_wa_speed_safety_cameras` ⊃ `camreg_bellevue_wa`)
        #     is the same publisher + channel — a target under that source.
        parent = next((s for s in sorted(source_ids) if source_id.startswith(s + "_")), None)
        if parent is not None and source_id not in source_ids:
            _dedupe_under(
                gen,
                plan_row=row,
                cand=cand,
                proposed=source_id,
                under=parent,
                target_ids=target_ids,
                layer_urls=layer_urls,
                layer_owners=layer_owners,
                emitted_target_ids=emitted_target_ids,
                why="id under registered source",
            )
            continue
        # (b2) an exact match on a registered id: an ACQ-01 row this generator
        #     emitted before (re-run convergence — the manifest records it,
        #     never an error and never a re-emit); anything else is a NEW-1
        #     collision with a foreign row.
        if source_id in source_ids:
            if _is_own_generated_row(source_table.get(source_id, {})):
                gen.notes.append(
                    f"{row['plan_id']}: {source_id} already registered by an "
                    "earlier ACQ-01 emission (converged — idempotent re-run)"
                )
                gen.manifest.setdefault("converged", []).append(
                    {"plan_id": row["plan_id"], "source_id": source_id}
                )
                converged_ids.add(source_id)
                emitted_ids.add(source_id)
                emitted_cands[source_id] = cand
                _cadence_route(gen, row, source_id)
            else:
                gen.errors.append(
                    f"{row['plan_id']}: id {source_id!r} collides with a "
                    "registered source/target id (NEW-1)"
                )
            continue
        # (c) a collision/prefix relation with an id emitted earlier this run:
        #     same channel (one service document, e.g. the two WVDOT Assets
        #     layers) → R1 dedupe under it; a different publisher → the `_2`/
        #     `_in` seed suffix is a list artifact, not a permanent id —
        #     recompute from geography+name (NEW-5). A recompute that still
        #     conflicts is an error, never a silent rename.
        conflict = next(
            (
                e
                for e in sorted(emitted_ids)
                if source_id == e or source_id.startswith(e + "_") or e.startswith(source_id + "_")
            ),
            None,
        )
        if conflict is not None:
            if _same_channel(cand, emitted_cands.get(conflict, {})):
                _dedupe_under(
                    gen,
                    plan_row=row,
                    cand=cand,
                    proposed=source_id,
                    under=conflict,
                    target_ids=target_ids,
                    layer_urls=layer_urls,
                    layer_owners=layer_owners,
                    emitted_target_ids=emitted_target_ids,
                    why="same publisher+channel (service document)",
                )
                continue
            try:
                recomputed = normalize_id(
                    "",
                    family=row["family"],
                    geography=(cand.get("geographies") or ""),
                    name=cand.get("proposed_name") or cand.get("name") or row["plan_id"],
                )
            except GenerationError as exc:
                gen.errors.append(f"{row['plan_id']}: {exc}")
                continue
            still = next(
                (
                    e
                    for e in sorted(emitted_ids | source_ids | target_ids)
                    if recomputed == e
                    or recomputed.startswith(e + "_")
                    or e.startswith(recomputed + "_")
                ),
                None,
            )
            if still is not None:
                gen.errors.append(
                    f"{row['plan_id']}: id {source_id!r} conflicts with {conflict!r} "
                    f"and the recomputed {recomputed!r} still conflicts with {still!r} "
                    "— a distinct permanent id needs a reviewed name (NEW-1)"
                )
                continue
            gen.notes.append(
                f"{row['plan_id']}: seed id {source_id!r} conflicted with emitted "
                f"{conflict!r}; recomputed {recomputed!r} (NEW-5 — the `_2`/`_in` "
                "suffix was a list artifact, not a permanent id)"
            )
            source_id = recomputed
        emitted_ids.add(source_id)
        emitted_cands[source_id] = cand
        _emit_source(gen, plan_row=row, cand=cand, source_id=source_id, class_ticket=class_ticket)
        _emit_target(
            gen,
            plan_row=row,
            cand=cand,
            source_id=source_id,
            existing_target_ids=target_ids,
            existing_layer_urls=layer_urls,
            existing_layer_owners=layer_owners,
            emitted_target_ids=emitted_target_ids,
        )
        _cadence_route(gen, row, source_id)
        # Every new source is connector-mapped later (family ticket) or carries
        # a `promote` disposition naming the class ticket — never unscoped.
        # A ticket cell that names a non-ACQ owning work item (`G2-step5(E4
        # D-R10-SOURCES-1 dossier captures)`) is *routing evidence*, just not
        # an ACQ class ticket: the row registers gated and the manifest names
        # its owner — never an emitted `promote` with a bogus class_ticket,
        # and only a truly blank cell is an error.
        ticket = class_ticket
        if not ticket:
            cell = (row.get("ticket") or "").strip()
            if not cell:
                gen.errors.append(
                    f"{row['plan_id']}: blank ticket cell — no ACQ class and no "
                    "owning work item named; the row cannot register unscoped"
                )
            elif acq:
                # The cell names an ACQ class that resolves to no manifest
                # ticket — a plan inconsistency, never owned_elsewhere.
                gen.errors.append(
                    f"{row['plan_id']}: ticket cell {cell!r} names {acq} which "
                    "resolves to no manifest ticket (round11_plan.csv)"
                )
            else:
                owner = next((t for marker, t in NON_ACQ_OWNERS if marker in cell), "")
                if not owner:
                    gen.errors.append(
                        f"{row['plan_id']}: ticket cell {cell!r} names a "
                        "non-ACQ work item the generator has no recorded "
                        "manifest owner for (NON_ACQ_OWNERS) — add the "
                        "routing, never invent one"
                    )
                else:
                    gen.dispositions[source_id] = {
                        "disposition": "promote",
                        "class_ticket": owner,
                    }
                    gen.manifest.setdefault("owned_elsewhere", []).append(
                        {
                            "plan_id": row["plan_id"],
                            "source_id": source_id,
                            "owner_cell": cell,
                            "class_ticket": owner,
                        }
                    )
                    gen.notes.append(
                        f"{row['plan_id']}: ticket cell {cell!r} names a "
                        f"non-ACQ owning work item — row registered gated; "
                        f"owner resolves to {owner} (recorded manifest owner)"
                    )
            ticket = ""
        else:
            gen.dispositions[source_id] = {
                "disposition": "promote",
                "class_ticket": ticket,
            }
        gen.manifest.setdefault("rows", []).append(
            {
                "plan_id": row["plan_id"],
                "action": row["action"],
                "source_id": source_id,
                "family": row["family"],
                "class_ticket": ticket,
                "cand_ids": cands,
            }
        )

    _assign_tier2(gen)
    # Converged ids are ours — an idempotent re-run is not a NEW-1 violation.
    # They stay in `existing` (a new id must not prefix-collide with them) and
    # leave `emitted` (their own exact match is the convergence).
    gen.errors.extend(
        check_id_collisions(emitted_ids - converged_ids, existing=source_ids | target_ids)
    )
    gen.manifest["emitted_ids"] = sorted(emitted_ids)
    gen.manifest["batches"] = {k: v["members"] for k, v in sorted(gen.batches.items())}
    gen.manifest["errors"] = list(gen.errors)
    gen.manifest["notes"] = list(gen.notes)
    return gen


# --- TOML emission ------------------------------------------------------------


def sources_toml(gen: Generation) -> str:
    out: list[str] = []
    for item in gen.sources:
        sid, row = item["id"], item["row"]
        out.append(f"[sources.{sid}]")
        for key, value in row.items():
            if key == "rights":
                continue
            if isinstance(value, bool):
                out.append(f"{key} = {str(value).lower()}")
            else:
                out.append(f"{key} = {_toml_str(value)}")
        out.append(f"[sources.{sid}.rights]")
        for key, value in row["rights"].items():
            if isinstance(value, bool):
                out.append(f"{key} = {str(value).lower()}")
            else:
                out.append(f"{key} = {_toml_str(value)}")
        out.append("")
    return "\n".join(out)


def targets_toml(gen: Generation) -> str:
    out: list[str] = []
    for row in gen.targets:
        out.append("[[targets]]")
        for key, value in row.items():
            if isinstance(value, bool):
                out.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, int):
                out.append(f"{key} = {value}")
            elif isinstance(value, (list, tuple)):
                out.append(f"{key} = {_toml_array(value)}")
            else:
                out.append(f"{key} = {_toml_str(value)}")
        out.append("")
    return "\n".join(out)


def cadence_toml(gen: Generation) -> str:
    out: list[str] = []
    for name in sorted(gen.batches):
        b = gen.batches[name]
        out.append("[[batches]]")
        out.append(f"id = {_toml_str(b['id'])}")
        out.append(f"cadence = {_toml_str(b['cadence'])}")
        out.append(f"cron = {_toml_str(b['cron'])}")
        out.append(f"job = {_toml_str(b['job'])}")
        out.append(f"scheduler = {_toml_str(b['scheduler'])}")
        out.append(f"task_timeout = {_toml_str(b['task_timeout'])}")
        out.append(f"members = {_toml_array(b['members'])}")
        out.append(f"note = {_toml_str(b['note'])}")
        out.append("")
    return "\n".join(out)


def dispositions_toml(gen: Generation) -> str:
    out: list[str] = []
    for sid in sorted(gen.dispositions):
        d = gen.dispositions[sid]
        out.append(f"[sources.{sid}]")
        out.append(f"disposition = {_toml_str(d['disposition'])}")
        if d.get("class_ticket"):
            out.append(f"class_ticket = {_toml_str(d['class_ticket'])}")
        out.append("")
    return "\n".join(out)


def manifest_json(gen: Generation) -> str:
    doc = {
        "schema": "sig.acq-gen-manifest/1",
        "sources": len(gen.sources),
        "targets": len(gen.targets),
        "batches": {k: len(v["members"]) for k, v in sorted(gen.batches.items())},
        "dispositions": len(gen.dispositions),
        "ok": gen.ok(),
        **gen.manifest,
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="sig-ops acq-generate",
        description=(
            "ACQ-01 generator — Round-11 plan CSV → registry/target/cadence/"
            "disposition rows (P35.6). Emits text for review; writes nothing "
            "live and flips nothing."
        ),
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--plan-rows", type=Path, default=DEFAULT_PLAN_ROWS)
    parser.add_argument("--row", action="append", default=[], help="plan_id filter (repeatable)")
    parser.add_argument("--family", action="append", default=[], help="family substring filter")
    parser.add_argument("--emit-sources", type=Path)
    parser.add_argument("--emit-targets", type=Path)
    parser.add_argument("--emit-cadence", type=Path)
    parser.add_argument("--emit-dispositions", type=Path)
    parser.add_argument("--emit-manifest", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="dry run — print the summary, exit 1 on errors",
    )
    args = parser.parse_args(argv)

    gen = generate(
        plan_csv=args.plan,
        candidates_csv=args.candidates,
        plan_rows_csv=args.plan_rows,
        only_rows=frozenset(args.row),
        only_families=tuple(args.family),
    )
    outputs = {
        args.emit_sources: sources_toml,
        args.emit_targets: targets_toml,
        args.emit_cadence: cadence_toml,
        args.emit_dispositions: dispositions_toml,
        args.emit_manifest: manifest_json,
    }
    for path, render in outputs.items():
        if path is not None:
            path.write_text(render(gen))
            print(f"wrote {path}")
    print(
        f"acq-generate: {len(gen.sources)} sources, {len(gen.targets)} targets, "
        f"{len(gen.batches)} batches, {len(gen.dispositions)} dispositions, "
        f"{len(gen.errors)} errors"
    )
    for note in gen.notes:
        print(f"  note: {note}")
    for err in gen.errors:
        print(f"  ERROR: {err}", file=sys.stderr)
    return 0 if gen.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "Generation",
    "GenerationError",
    "check_id_collisions",
    "generate",
    "normalize_id",
    "sources_toml",
    "targets_toml",
    "cadence_toml",
    "dispositions_toml",
    "manifest_json",
]
