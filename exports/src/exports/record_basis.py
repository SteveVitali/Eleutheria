# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The per-record quality-basis block (P37.39, R11-K13-QB-01 / L3 §5.2,
SIG-CONF-011's per-record rendering, UXR-A06).

One shared, additive normalisation turns a record's CONF-07b derivation
fields — the ``dedup`` block ``published_record`` projects verbatim
(``site_id``, ``copies[]``, ``possible_duplicates[]``, ``multi_view[]``,
``n_independent_lineages`` + its display) plus the location-check, technology
and evidence contexts — into the ONE ``sig.record-basis/1`` block every
surface renders:

* ``site_id`` + ``copies[]`` — the **copy** state (lexicon
  ``identity.COPY``): collapsed copies of the same upstream record, checked
  automatically — never an excess row;
* ``possible_duplicates[]`` — the **possible duplicate** state (lexicon
  ``identity.POSSIBLE_DUPLICATE``): listed, never merged (SIG-CONF-005);
* ``multi_view[]`` — same-layer co-located distinct records (GQ-10);
* ``n_independent_lineages`` — the **corroboration** state ("Listed by 1
  source." / "Seen independently by N sources: …");
* ``location_check`` — "Location checked: inside <Jurisdiction>." /
  "**Location conflict:** …; shown, not counted there." (the closed
  ``placement_check`` vocabulary — K4 §3.3);
* ``technology`` — "Technology: <slug>, from <Source>'s layer description."
  (a declared claim, never an inferred class);
* ``evidence`` — "Evidence: <Source>, fetched <date>; copy kept: yes/no."
  (the claim's J3 binding);
* ``checked_by`` — "Checked by automated release checks. Not reviewed by a
  person." — the honest interim state while no independent review exists
  (SIG-CONF-011's "who checked what" row reads "none").

Entry ``display`` strings are the export's own L3 §5.2 verbatim sentences —
this module never paraphrases a copy into a merge claim. A field that was
never recorded carries its named-absence reason, never a fabricated value.
This is the Python twin of ``web/src/lib/record-basis.ts`` — the same field
set, the same absence discipline (UXR-33: a divergent wording on any
surface is a defect, not a variant).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

#: The schema stamp the emitted block answers to.
SCHEMA = "sig.record-basis/1"

NOT_RECORDED = "not_recorded"
NOT_EVALUABLE = "not_evaluable"

#: The whole-block absence text — L3 §5.2's no-run state.
NO_BASIS = "no completed camera-site ER run — the fields are declared, never fabricated"

#: The checked-by line while no person outside the project has reviewed —
#: SIG-CONF-011's independent-review row reads "none".
CHECKED_BY_TEXT = "Checked by automated release checks. Not reviewed by a person."

#: ``placement_check`` values that mean "the published point sits inside the
#: recorded jurisdiction" — the rest name their own state, never a verdict
#: the check did not reach.
_INSIDE_CHECKS = frozenset({"consistent", "on_boundary"})
_CONFLICT_CHECKS = frozenset({"outside_declared", "outside_declared_country"})


def _absence(value: Any) -> str | None:
    """The reason a ``{not_recorded|not_evaluable: reason}`` object carries."""
    if isinstance(value, Mapping):
        for key in (NOT_RECORDED, NOT_EVALUABLE):
            reason = value.get(key)
            if reason:
                return str(reason)
    return None


def _entries(value: Any) -> tuple[list[dict[str, Any]], str | None]:
    """``(entries, absence)`` — a measured list (``[]`` is a measured none)
    or the field's named-absence reason."""
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [dict(e) for e in value if isinstance(e, Mapping)], None
    return [], _absence(value) or NOT_RECORDED


def location_check_text(
    placement_check: Any,
    *,
    jurisdiction_name: str | None = None,
) -> str:
    """The location-check sentence over the closed ``placement_check``
    vocabulary (K4 §3.3). ``consistent``/``on_boundary`` → the inside
    sentence; the outside-declared pair → the conflict sentence; a withheld
    or suspect point names its check; no run → the named absence."""
    check = str(placement_check or "").strip()
    place = jurisdiction_name or "the recorded jurisdiction"
    if not check:
        return "Location check: not_recorded — no placement check is recorded."
    if check in _INSIDE_CHECKS:
        return f"Location checked: inside {place}."
    if check in _CONFLICT_CHECKS:
        return (
            f"Location conflict: located outside the declared jurisdiction "
            f"({check}); shown, not counted there."
        )
    if check in ("axis_swap_suspected", "sign_flip_suspected"):
        return f"Location check: a suspect coordinate variant ({check}); the point is withheld."
    if check in (
        "no_point",
        "coordinates_conflicted",
        "point_rejected:null_island",
        "point_rejected:invalid_point",
        "outside_all_boundaries",
        "null_island",
        "invalid_point",
    ):
        return (
            f"Location check: {check} — no publishable point; "
            "the record is shown, not counted at a point."
        )
    if check == "no_location_evidence":
        return "Location check: no location evidence is recorded."
    if check in ("name_unmatched", "name_ambiguous"):
        return f"Location check: {check} — declared level only."
    return f"Location check: {check}."


def technology_text(
    technology: Any,
    status: Any = None,
    *,
    source_name: str | None = None,
) -> str:
    """The technology sentence — a declared slug with its honest basis;
    ``conflicted``/``unreported`` stay states, never a guessed class."""
    slug = str(technology or "").strip()
    state = str(status or "").strip()
    src = source_name or "the source"
    if slug:
        basis = "layer description" if state in ("", "resolved") else state
        return f"Technology: {slug}, from {src}'s {basis}."
    if state == "conflicted":
        return "Technology: conflicted declarations — no class is shown."
    if state == "unreported":
        return "Technology: unreported — the source declares no class."
    return "Technology: not_recorded."


def evidence_text(
    source_name: Any = None,
    fetched: Any = None,
    *,
    copy_kept: bool | None = None,
) -> str:
    """The evidence sentence — "Evidence: <Source>, fetched <date>; copy
    kept: yes/no." (L3 §5.2's ``binding_state`` row). A claim with no
    recorded fetch shows the named absence, never a guessed instant."""
    src = str(source_name or "").strip()
    when = str(fetched or "")[:10]
    if not src or not when:
        return "Evidence: not_recorded — no published fetch is recorded for this record."
    kept = "yes" if copy_kept is True else "no" if copy_kept is False else NOT_RECORDED
    return f"Evidence: {src}, fetched {when}; copy kept: {kept}."


def record_basis(
    dedup: Mapping[str, Any] | None,
    *,
    placement_check: Any = None,
    jurisdiction_name: str | None = None,
    technology: Any = None,
    technology_status: Any = None,
    technology_source_name: str | None = None,
    evidence_source_name: Any = None,
    evidence_fetched: Any = None,
    evidence_copy_kept: bool | None = None,
) -> dict[str, Any] | None:
    """Normalise a record's CONF-07b ``dedup`` block + the location-check,
    technology and evidence contexts into the ``sig.record-basis/1`` block.

    ``dedup`` is the projected block (``{site_id, copies, possible_duplicates,
    multi_view, n_independent_lineages, n_independent_lineages_display}``) —
    ``None`` on a pre-P35.47 export returns ``None`` (sparse — the block is
    absent, never fabricated). The dedup fields' own ``not_recorded`` /
    ``not_evaluable`` objects ride through as named absences.
    """
    if dedup is None:
        return None
    site = dedup.get("site_id")
    site_absence = _absence(site)
    copies, copies_absence = _entries(dedup.get("copies"))
    poss, poss_absence = _entries(dedup.get("possible_duplicates"))
    mv, mv_absence = _entries(dedup.get("multi_view"))
    n_lin = dedup.get("n_independent_lineages")
    n_disp = dedup.get("n_independent_lineages_display")
    lineages_absence = _absence(n_lin) or _absence(n_disp)
    lineages_text = n_disp if isinstance(n_disp, str) else None
    if lineages_text is None and isinstance(n_lin, int) and not isinstance(n_lin, bool):
        lineages_text = (
            "Listed by 1 source." if n_lin == 1 else f"Seen independently by {n_lin} sources."
        )
    return {
        "schema": SCHEMA,
        "site_id": site if isinstance(site, str) else None,
        "site_absence": site_absence,
        "copies": copies,
        "copies_absence": copies_absence,
        "possible_duplicates": poss,
        "duplicates_absence": poss_absence,
        "multi_view": mv,
        "multi_view_absence": mv_absence,
        "lineages": n_lin if isinstance(n_lin, int) and not isinstance(n_lin, bool) else None,
        "lineages_text": lineages_text,
        "lineages_absence": lineages_absence,
        "location_check": location_check_text(placement_check, jurisdiction_name=jurisdiction_name),
        "technology": technology_text(
            technology, technology_status, source_name=technology_source_name
        ),
        "evidence": evidence_text(
            evidence_source_name, evidence_fetched, copy_kept=evidence_copy_kept
        ),
        "checked_by": CHECKED_BY_TEXT,
    }


def basis_rows(basis: Mapping[str, Any]) -> list[tuple[str, str, Sequence[str]]]:
    """``(label, text, entry_displays)`` rows — the block's render order.

    ``entry_displays`` are the entries' verbatim L3 §5.2 ``display``
    sentences; the label pairs each state with its lexicon word (``copy`` /
    ``possible duplicate`` / multi-view / corroboration / location check /
    technology / evidence / checked by).
    """

    def _displays(entries: Any) -> list[str]:
        out: list[str] = []
        for e in entries or ():
            disp = str((e or {}).get("display") or "").strip()
            if disp:
                out.append(disp)
        return out

    site = basis.get("site_id")
    site_text = (
        str(site) if isinstance(site, str) else str(basis.get("site_absence") or NOT_RECORDED)
    )
    rows: list[tuple[str, str, Sequence[str]]] = [("Camera site", site_text, ())]
    for label, key, absence_key in (
        ("Copies", "copies", "copies_absence"),
        ("Possible duplicates", "possible_duplicates", "duplicates_absence"),
        ("Multi-view", "multi_view", "multi_view_absence"),
    ):
        entries = basis.get(key) or []
        absence = basis.get(absence_key)
        if absence:
            rows.append((label, f"{NOT_RECORDED} — {absence}", ()))
        elif not entries:
            rows.append((label, "none recorded", ()))
        else:
            rows.append((label, "", _displays(entries)))
    rows.append(
        (
            "Corroboration",
            str(
                basis.get("lineages_text")
                or f"{NOT_EVALUABLE} — {basis.get('lineages_absence') or NOT_RECORDED}"
            ),
            (),
        )
    )
    for label, key in (
        ("Location check", "location_check"),
        ("Technology", "technology"),
        ("Evidence", "evidence"),
        ("Checked by", "checked_by"),
    ):
        rows.append((label, str(basis.get(key) or NOT_RECORDED), ()))
    return rows


__all__ = [
    "CHECKED_BY_TEXT",
    "NO_BASIS",
    "NOT_EVALUABLE",
    "NOT_RECORDED",
    "SCHEMA",
    "basis_rows",
    "evidence_text",
    "location_check_text",
    "record_basis",
    "technology_text",
]
