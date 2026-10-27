# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P35.47 dedup publication view (SIG-CONF-005, GQ-10, ADR-153).

One shared, additive view turns the latest completed camera-site ER run's
ruleset-v3 links (dep P35.46 — read verbatim through
:func:`resolution.camera_sites_pg.read_resolved_site_runs`) into the exported
record fields every surface publishes from ONE computation:

* ``site_id`` — the shared site id the run assigned the record's cluster
  (a singleton site's id is the record's own entity id);
* ``copies[]`` — the collapsed copies nested on the canonical row
  (source, upstream id, basis C0/C1/C2 — ``"same_as"`` for a member joined by
  a recorded review decision — never an excess row per copy, F-511);
* ``possible_duplicates[]`` — the inferential/near links that are listed,
  never merged (record link, distance, reason — SIG-CONF-005);
* ``multi_view[]`` — same-layer co-located distinct records classed
  ``multi_view``, never duplicates (GQ-10);
* ``n_independent_lineages`` — the site's declared independence-class count;
* the SIG-CONF-005 count intervals (record count beside ``[lower, upper]``)
  per dossier, map/bulk surface and the national figure — computed through
  :func:`resolution.camera_sites.count_bounds`, the dep's own bound code —
  never a re-computation.

Honest absence is a first-class state: no completed run → every field emits
its ``{"not_recorded": ...}`` object; a run present → every published record
carries measured values (``copies: []`` for a no-link record is a measured
fact, never an omitted field). A dossier whose interval cannot be computed
emits ``{"not_evaluable": reason}`` — never a fabricated bound.

The display strings below are L3 §5.2 verbatim — they live in the emitted
JSON so no page can paraphrase a copy into a merge claim ("checked
automatically"; "not merged"; never "verified"/"certified").
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inference.marking import mark_inferred
from resolution.camera_sites import count_bounds

#: The schema stamp this module's emitted field shapes answer to.
SCHEMA = "sig.dedup-view/1"

#: The honest no-run state the exported fields carry when no completed
#: camera-site ER run exists (a field is never omitted, never fabricated).
NOT_RECORDED_NO_RUN = "no completed camera-site ER run — the fields are declared, never fabricated"


#: L3 §5.2 — the binding display contract, verbatim in the emitted JSON.
def display_copy(source_name: str, upstream_id: str | None) -> str:
    """The copies[] entry display — the L3 §5.2 clause verbatim."""
    if upstream_id:
        return (
            f"Also published by {source_name} (a copy of the same upstream "
            f"record, id {upstream_id}, checked automatically)."
        )
    return (
        f"Also published by {source_name} (a copy of the same upstream "
        "record, checked automatically)."
    )


def display_possible_duplicate(source_name: str, distance_m: float) -> str:
    """The possible_duplicates[] entry display — L3 §5.2 verbatim."""
    return (
        f"Possible duplicate: {source_name} lists a camera {distance_m:g} m away. "
        "SIG has not merged them because it cannot prove they are the same device."
    )


def display_multi_view(source_name: str, distance_m: float) -> str:
    """The multi_view[] entry display — same-layer co-located distinct records
    classed ``multi_view``, never duplicates (GQ-10)."""
    return (
        f"Multi-view: {source_name} lists another distinct camera record "
        f"{distance_m:g} m away — same-layer records are classed multi-view, not duplicates."
    )


def display_lineages(class_names: Sequence[str]) -> str:
    """The n_independent_lineages display — L3 §5.2 verbatim."""
    if len(class_names) == 1:
        return "Listed by 1 source."
    return f"Seen independently by {len(class_names)} sources: {', '.join(class_names)}."


def display_count_interval(records: int, lower: int, upper: int) -> str:
    """The dossier-count interval display — L3 §5.2 verbatim."""
    return (
        f"{records} camera records · between {lower} and {upper} listed cameras "
        "([why a range?](/quality/#duplicates))"
    )


#: The collapse-tier basis labels a copies[] entry may carry. A member joined
#: by a recorded review decision (``same_as``) is never labelled C0/C1/C2 —
#: it carries its own honest basis.
COPY_BASES = ("C0", "C1", "C2", "same_as")


@dataclass(frozen=True)
class DedupView:
    """The one shared record/site view every surface reads (one computation)."""

    run_key: str
    declared_distance_m: float
    #: member subject -> its site id (the cluster root; singletons map to
    #: themselves). Members = published records the view covers.
    member_site: dict[str, str]
    #: site id -> its members sorted (>= 1).
    site_members: dict[str, tuple[str, ...]]
    #: member -> its record's source id (the minting/coordinate source).
    member_source: dict[str, str]
    #: site id -> the derivation-preferred canonical member (the member that
    #: is ``left`` (origin) and never ``right`` (republish) across the
    #: cluster's derived_from links; else the smallest member id).
    preferred: dict[str, str]
    #: site id -> copies[] entries (every member but the canonical — a member
    #: is listed whether or not its own slice emitted; the derivation fact
    #: stands regardless of the copy's licence slice).
    copies: dict[str, tuple[dict[str, Any], ...]]
    #: site id -> possible_duplicates[] entries (cross-layer links).
    possible: dict[str, tuple[dict[str, Any], ...]]
    #: site id -> multi_view[] entries (same-layer links).
    multi_view: dict[str, tuple[dict[str, Any], ...]]
    #: site id -> the site's declared independence-class count (None when the
    #: ``claim_lineage`` read is absent — the pre-P35.25 spine, an honest
    #: ``not_evaluable`` state never coerced into a count).
    n_lineages: dict[str, int] | None
    #: site id -> the sorted distinct class names behind n_lineages.
    lineage_names: dict[str, tuple[str, ...]]
    #: The not_evaluable reason carried when the lineage read is absent.
    lineage_not_evaluable: str | None = None
    #: The run's applied (collapse/same_as) edges restricted to published
    #: members — the interval's upper-bound edge set.
    applied_edges: tuple[tuple[str, str], ...] = ()
    #: The run's possible-duplicate edges within the declared distance,
    #: restricted to published members — the lower-bound edge set.
    possible_edges: tuple[tuple[str, str], ...] = ()

    def bounds(self, member_subset: Iterable[str]) -> dict[str, int]:
        """The dep's bound computation verbatim over ``member_subset``."""
        return count_bounds(
            self.member_site.keys(),
            self.applied_edges,
            self.possible_edges,
            set(member_subset),
        )

    def record_fields(self, member: str) -> dict[str, Any]:
        """The exported dedup fields for a published (canonical-row) member."""
        site = self.member_site.get(member, member)
        n_lin: Any
        n_display: Any
        if self.n_lineages is None:
            n_lin = {"not_evaluable": self.lineage_not_evaluable}
            n_display = {"not_evaluable": self.lineage_not_evaluable}
        else:
            n_lin = int(self.n_lineages.get(site, 1))
            n_display = display_lineages(self.lineage_names.get(site, (member,)))
        return {
            "site_id": site,
            "copies": [dict(e) for e in self.copies.get(site, ())],
            # P36.14 (SIG-RECON-052): possible_duplicates are the inferential
            # ER links — never merged, marked L4 — and multi_view entries are
            # the engine's derived same-layer classification. Each emitted
            # entry carries the typed ``inferred``/``layer`` marker; the
            # mechanically-verified copies (``same_as`` review decisions and
            # C-tier shared-upstream checks) are recorded/mechanical, not L4,
            # and stay unmarked.
            "possible_duplicates": [mark_inferred(dict(e)) for e in self.possible.get(site, ())],
            "multi_view": [mark_inferred(dict(e)) for e in self.multi_view.get(site, ())],
            "n_independent_lineages": n_lin,
            "n_independent_lineages_display": n_display,
        }


def not_recorded_fields(reason: str = NOT_RECORDED_NO_RUN) -> dict[str, Any]:
    """The honest absence states every exported field carries with no run."""
    return {
        "site_id": {"not_recorded": reason},
        "copies": {"not_recorded": reason},
        "possible_duplicates": {"not_recorded": reason},
        "multi_view": {"not_recorded": reason},
        "n_independent_lineages": {"not_recorded": reason},
        "n_independent_lineages_display": {"not_recorded": reason},
    }


def _source_display(source_id: str, source_names: Mapping[str, str]) -> str:
    return str(source_names.get(source_id) or source_id or "(unattributed)")


def build_dedup_view(
    runs: Sequence[Mapping[str, Any]],
    *,
    member_records: Mapping[str, str],
    member_lineages: Mapping[str, Sequence[str]] | None,
    source_names: Mapping[str, str],
) -> DedupView | None:
    """Build the shared dedup view from the latest run's links.

    ``runs`` — ``read_resolved_site_runs`` output (``[]``/missing ``links``
    → ``None``; the surfaces then publish the ``not_recorded`` states, never
    a fabricated link set). ``member_records`` — published member subject →
    its source id. ``member_lineages`` — member subject -> the distinct
    declared independence classes among its claims (empty = undeclared — the
    member then counts as its own singleton class, never silently zero);
    ``None`` when the ``claim_lineage`` read is absent entirely (pre-P35.25
    spine) — ``n_independent_lineages`` then emits the honest
    ``not_evaluable`` object rather than a fabricated count.
    ``source_names`` — registry display names for the L3 §5.2 strings.
    """
    if not runs:
        return None
    run = runs[0]
    links = list(run.get("links") or [])
    if not links:
        return None
    declared_distance_m = float(
        ((run.get("summary") or {}).get("count_intervals") or {}).get("declared_distance_m", 25.0)
    )
    members = set(member_records)

    # --- collect the run's links restricted to published members ------------
    applied: list[tuple[str, str]] = []
    possible: list[tuple[str, str]] = []
    possible_rows: list[Mapping[str, Any]] = []
    derived_rows: dict[str, Mapping[str, Any]] = {}  # republish member -> its link
    group_roots: list[tuple[str, str]] = []  # (member, recorded C0 group root)
    member_source: dict[str, str] = {}
    for link in links:
        left, right = str(link.get("left") or ""), str(link.get("right") or "")
        ev = link.get("evidence") or {}
        srcs = [str(s) for s in (ev.get("sources") or [])]
        if len(srcs) >= 2:
            member_source.setdefault(left, srcs[0])
            member_source.setdefault(right, srcs[1])
        if left not in members or right not in members:
            continue  # a withheld/unpublished endpoint never leaks through a link
        rel = str(link.get("relation_type") or "")
        disp = str(link.get("disposition") or "")
        if rel in ("derived_from", "same_as") and disp in ("auto_write", "human_accept"):
            applied.append((left, right))
            if rel == "derived_from":
                # C1 names the republish member ``right`` (the original is
                # ``left``); C0's recorded ``duplicate_group_root`` names the
                # canonical directly. Both are the dep's own designations —
                # read verbatim, never re-derived.
                if right not in derived_rows:
                    derived_rows[right] = link
                root = ev.get("duplicate_group_root")
                if root:
                    group_roots.append((left, str(root)))
                    group_roots.append((right, str(root)))
        elif rel == "possible_duplicate" and disp in ("proposed", "refused"):
            possible_rows.append(link)
            dist = ev.get("distance_m")
            if isinstance(dist, int | float) and float(dist) <= declared_distance_m:
                possible.append((left, right))

    # --- cluster the published members over the applied edges ---------------
    parent: dict[str, str] = {m: m for m in members}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for left, right in applied:
        a, b = find(left), find(right)
        if a != b:
            lo, hi = sorted((a, b))
            parent[hi] = lo
    site_members: dict[str, list[str]] = {}
    for m in members:
        site_members.setdefault(find(m), []).append(m)
    member_site = {m: find(m) for m in members}
    # Site ids are re-derived over the PUBLISHED member set — the dep's
    # ``_clusters_from_edges`` root is the smallest member id, so a cluster
    # whose recorded root is published re-derives the run's exact ``site_id``;
    # when the recorded root was withheld the smallest published member
    # stands — a withheld record's id never leaks through a site id.

    # --- canonical member per site (derivation order) -----------------------
    rights_in_site: dict[str, set[str]] = {}
    lefts_in_site: dict[str, set[str]] = {}
    for left, right in applied:
        site = member_site[left]
        rights_in_site.setdefault(site, set()).add(right)
        lefts_in_site.setdefault(site, set()).add(left)
    root_hints: dict[str, set[str]] = {}
    for member, root in group_roots:
        if member in member_site and root in members:
            root_hints.setdefault(member_site[member], set()).add(root)
    preferred: dict[str, str] = {}
    for site, ms in site_members.items():
        hints = [m for m in ms if m in root_hints.get(site, set())]
        if hints:
            preferred[site] = min(hints)
            continue
        roots = [
            m
            for m in ms
            if m in lefts_in_site.get(site, set()) and m not in rights_in_site.get(site, set())
        ]
        preferred[site] = min(roots) if roots else min(ms)

    # --- per-site fields -----------------------------------------------------
    copies: dict[str, tuple[dict[str, Any], ...]] = {}
    poss: dict[str, tuple[dict[str, Any], ...]] = {}
    mv: dict[str, tuple[dict[str, Any], ...]] = {}
    n_lin: dict[str, int] = {}
    lin_names: dict[str, tuple[str, ...]] = {}

    def _src(m: str) -> str:
        return str(member_source.get(m) or member_records.get(m) or "")

    for site, ms in site_members.items():
        canon = preferred[site]
        entries: list[dict[str, Any]] = []
        for m in sorted(x for x in ms if x != canon):
            link = derived_rows.get(m)
            if link is not None:
                ev = link.get("evidence") or {}
                tier = link.get("tier")
                basis = (
                    f"C{int(tier)}" if tier is not None and int(tier) in (0, 1, 2) else "same_as"
                )
                upstream = ev.get("shared_upstream_ref")
                entries.append(
                    {
                        "record": m,
                        "source": _src(m),
                        "source_name": _source_display(_src(m), source_names),
                        "upstream_id": str(upstream) if upstream else None,
                        "basis": basis,
                        "basis_text": str(ev.get("basis") or ""),
                        "display": display_copy(
                            _source_display(_src(m), source_names),
                            str(upstream) if upstream else None,
                        ),
                    }
                )
            else:
                # Joined by a recorded review decision (same_as), never a C-tier.
                entries.append(
                    {
                        "record": m,
                        "source": _src(m),
                        "source_name": _source_display(_src(m), source_names),
                        "upstream_id": None,
                        "basis": "same_as",
                        "basis_text": "same device by a recorded review decision",
                        "display": (
                            f"Also listed by {_source_display(_src(m), source_names)} "
                            "(same device by a recorded review decision)."
                        ),
                    }
                )
        if entries:
            copies[site] = tuple(entries)

        if member_lineages is None:
            continue  # n_lineages stays unset → the honest not_evaluable state
        classes: set[str] = set()
        names: set[str] = set()
        for m in ms:
            m_classes = [str(c) for c in (member_lineages.get(m) or ()) if c]
            if m_classes:
                classes.update(m_classes)
                names.update(_source_display(c, source_names) for c in m_classes)
            else:
                classes.add(f"undeclared:{m}")
                names.add(_source_display(_src(m), source_names))
        n_lin[site] = len(classes)
        lin_names[site] = tuple(sorted(names))

    for link in possible_rows:
        left, right = str(link["left"]), str(link["right"])
        ev = link.get("evidence") or {}
        dist = ev.get("distance_m")
        dist_f = float(dist) if isinstance(dist, int | float) else 0.0
        reason = str(ev.get("possible_duplicate_reason") or ev.get("basis") or "")
        lsite, rsite = member_site[left], member_site[right]
        lsrc, rsrc = _src(left), _src(right)
        if lsrc and rsrc and lsrc == rsrc:
            for site, other, _other_src in (
                (lsite, right, rsrc),
                (rsite, left, lsrc),
            ):
                mv.setdefault(site, ())
                mv[site] += (
                    {
                        "record": other,
                        "site_id": member_site[other],
                        "distance_m": dist_f,
                        "display": display_multi_view(
                            _source_display(_src(other), source_names), dist_f
                        ),
                    },
                )
            continue
        for site, other, other_src, other_site in (
            (lsite, right, rsrc, rsite),
            (rsite, left, lsrc, lsite),
        ):
            poss.setdefault(site, ())
            poss[site] += (
                {
                    "record": other,
                    "site_id": other_site,
                    "source": other_src,
                    "source_name": _source_display(other_src, source_names),
                    "distance_m": dist_f,
                    "reason": reason,
                    "display": display_possible_duplicate(
                        _source_display(other_src, source_names), dist_f
                    ),
                },
            )

    return DedupView(
        run_key=str(run.get("run_key") or ""),
        declared_distance_m=declared_distance_m,
        member_site={m: member_site[m] for m in sorted(member_site)},
        site_members={s: tuple(ms) for s, ms in sorted(site_members.items())},
        member_source={m: _src(m) for m in sorted(member_records)},
        preferred=preferred,
        copies={s: copies[s] for s in sorted(copies)},
        possible={s: poss[s] for s in sorted(poss)},
        multi_view={s: mv[s] for s in sorted(mv)},
        n_lineages=(n_lin if member_lineages is not None else None),
        lineage_names=lin_names,
        lineage_not_evaluable=(
            None if member_lineages is not None else "claim_lineage read absent (pre-P35.25 spine)"
        ),
        applied_edges=tuple(sorted(set(applied))),
        possible_edges=tuple(sorted(set(possible))),
    )


def interval_block(
    view: DedupView | None,
    member_subset: Iterable[str],
    *,
    records: int | None = None,
) -> dict[str, Any]:
    """The emitted interval block: record count beside [lower, upper].

    ``member_subset`` = the member subjects the count covers (a dossier's
    members, a compartment's members, the national set). ``records`` = the
    published record count beside the range — the member count when not
    given. With no view the block carries the honest ``not_evaluable`` state.
    """
    subset = {m for m in member_subset}
    rec = len(subset) if records is None else int(records)
    if view is None:
        return {
            "records": rec,
            "not_evaluable": NOT_RECORDED_NO_RUN,
        }
    b = view.bounds(subset)
    return {
        "records": rec,
        "lower": b["lower"],
        "upper": b["upper"],
        "declared_distance_m": view.declared_distance_m,
        "display": display_count_interval(rec, b["lower"], b["upper"]),
    }


def dossier_inflation(
    view: DedupView | None,
    member_subset: Iterable[str],
    published_rows: int,
) -> dict[str, Any]:
    """The measured GQ-10 dossier inflation against lineage roots.

    ``published_rows`` = the site rows the dossier's emitted rows carry;
    the denominator = the interval's upper bound over the dossier's member
    records — the collapse-by-lineage count ("lineage roots"). The measured
    ratio is published as measured (the registry's ≤ 1.02× is the ratchet
    target; a miss is recorded and surfaced, never smoothed).
    """
    if view is None:
        return {"published_rows": int(published_rows), "not_evaluable": NOT_RECORDED_NO_RUN}
    b = view.bounds(member_subset)
    measured = (float(published_rows) / b["upper"]) if b["upper"] else None
    return {
        "published_rows": int(published_rows),
        "lineage_roots": b["upper"],
        "measured": measured,
        "ratchet_target": "<= 1.02",
    }
