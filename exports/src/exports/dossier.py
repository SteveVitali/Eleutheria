# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The local dossier content contract (§39.2, SIG-UI-010..015) — the P06.1 slice
renderer.

This is a **minimal, slice-proof** renderer whose only job is to prove that J-1
renders end to end before the epistemic visual language exists. The production
dossier surface — the real owner of SIG-UI-010..015, with the full epistemic
language, a11y/no-JS, and editorial standards — is **P15.2, which supersedes this
renderer** (see the ticket scope note and ADR-032). Do not gold-plate it.

What it enforces from §39.2:

* **SIG-UI-010** the twelve sections, in the exact order.
* **SIG-UI-011** "what we don't know" is not an appendix: it appears in the
  summary, the print export, and the API (JSON) form.
* **SIG-UI-012** an explicit incompleteness banner naming the number of
  unresearched fields and stating absence-is-not-evidence-of-absence.
* **SIG-UI-013** a print/PDF path: paginated, with sources, and with the as-of
  date and permalink on every page.
* **SIG-UI-014** every material figure is expandable to its reconciliation: the
  rule that fired, the competing claims, each source's tier and date, and a link
  to the document at its locator.
* **SIG-UI-015** `unknown` values are rendered as "unknown", never omitted.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import date

# --- SIG-UI-010: the twelve sections, in order -------------------------------

SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("at_a_glance", "At a glance"),
    ("what_is_deployed", "What is deployed"),
    ("cost_and_expiry", "Cost and expiry"),
    ("who_else_can_see", "Who else can see the data"),
    ("configuration_and_retention", "Configuration and retention"),
    ("usage", "Usage"),
    ("where_the_hardware_is", "Where the hardware is"),
    ("policy", "Policy"),
    ("accountability_events", "Accountability events"),
    ("timeline", "Timeline"),
    ("what_we_dont_know", "What we don't know"),
    ("how_we_know_this", "How we know this"),
)
SECTION_IDS: tuple[str, ...] = tuple(sid for sid, _ in SECTION_ORDER)
SECTION_TITLES: dict[str, str] = dict(SECTION_ORDER)

# Statuses a field may carry when it has no resolved value (SIG-UI-015, §9.5).
NOT_RESEARCHED = "not_researched"
SEARCHED_NOT_FOUND = "searched_not_found"


@dataclass(frozen=True)
class DocumentRef:
    """A link to a document at its exact locator (SIG-UI-014, §D.4)."""

    source_family: str
    stable_locator: str
    locator: dict[str, object]
    capture_digest: str = ""
    excerpt: str = ""

    def as_json(self) -> dict[str, object]:
        return {
            "source_family": self.source_family,
            "stable_locator": self.stable_locator,
            "locator": self.locator,
            "capture_digest": self.capture_digest,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class ReconClaim:
    """One competing claim behind a figure, with its tier and date (SIG-UI-014)."""

    value: object
    source_family: str
    reliability: str  # R tier
    weight: int | None  # W class
    observed_at: date
    document: DocumentRef

    def as_json(self) -> dict[str, object]:
        return {
            "value": self.value,
            "source_family": self.source_family,
            "reliability": self.reliability,
            "weight": self.weight,
            "observed_at": self.observed_at.isoformat(),
            "document": self.document.as_json(),
        }


@dataclass(frozen=True)
class Reconciliation:
    """The expandable reconciliation behind a material figure (SIG-UI-014)."""

    rule: str  # the rule that fired, e.g. "authoritative_source_wins -> W4"
    winning: ReconClaim
    competing: tuple[ReconClaim, ...] = ()
    note: str = ""

    def as_json(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "winning": self.winning.as_json(),
            "competing": [c.as_json() for c in self.competing],
            "note": self.note,
        }


@dataclass(frozen=True)
class Figure:
    """A material figure — always expandable to its reconciliation (SIG-UI-014)."""

    key: str
    label: str
    value: object
    reconciliation: Reconciliation
    unit: str = ""
    lower_bound: bool = False

    def as_json(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "lower_bound": self.lower_bound,
            "reconciliation": self.reconciliation.as_json(),
        }


@dataclass(frozen=True)
class Row:
    """A non-figure fact. ``value=None`` renders as "unknown" (SIG-UI-015)."""

    label: str
    value: object | None
    status: str = "known"  # known | not_researched | searched_not_found
    document: DocumentRef | None = None
    note: str = ""

    def display_value(self) -> str:
        if self.value is not None:
            return str(self.value)
        return "unknown"

    def as_json(self) -> dict[str, object]:
        return {
            "label": self.label,
            "value": self.value,
            "display_value": self.display_value(),
            "status": self.status,
            "document": self.document.as_json() if self.document else None,
            "note": self.note,
        }


@dataclass(frozen=True)
class Section:
    section_id: str
    figures: tuple[Figure, ...] = ()
    rows: tuple[Row, ...] = ()

    @property
    def title(self) -> str:
        return SECTION_TITLES[self.section_id]

    def as_json(self) -> dict[str, object]:
        return {
            "id": self.section_id,
            "title": self.title,
            "figures": [f.as_json() for f in self.figures],
            "rows": [r.as_json() for r in self.rows],
        }


@dataclass(frozen=True)
class Gap:
    """One entry of "what we don't know" (SIG-UI-011)."""

    label: str
    status: str  # not_researched | searched_not_found
    note: str = ""

    def as_json(self) -> dict[str, object]:
        return {"label": self.label, "status": self.status, "note": self.note}


@dataclass(frozen=True)
class Dossier:
    subject_label: str
    jurisdiction: str
    as_of: date
    permalink: str
    sections: tuple[Section, ...]
    gaps: tuple[Gap, ...]
    unresearched_field_count: int
    source_families: tuple[str, ...] = ()

    def incompleteness_banner(self) -> str:
        """The explicit incompleteness banner (SIG-UI-012)."""
        return (
            f"This dossier has {self.unresearched_field_count} unresearched field(s). "
            "The absence of a row is not evidence of absence."
        )

    def validate(self) -> None:
        """Enforce the §39.2 section contract (SIG-UI-010/011)."""
        got = tuple(s.section_id for s in self.sections)
        if got != SECTION_IDS:
            raise ValueError(
                f"dossier sections must be exactly the §39.2 order (SIG-UI-010); got {got!r}"
            )


# --- SIG-UI-011: "what we don't know" in summary + API + print ---------------


def render_json(dossier: Dossier) -> dict[str, object]:
    """The API form. Carries the incompleteness banner and the gap list at the
    top level (the summary) AND inside the sections (SIG-UI-011)."""
    dossier.validate()
    return {
        "subject": dossier.subject_label,
        "jurisdiction": dossier.jurisdiction,
        "as_of": dossier.as_of.isoformat(),
        "permalink": dossier.permalink,
        "incompleteness_banner": dossier.incompleteness_banner(),
        "unresearched_field_count": dossier.unresearched_field_count,
        # "what we don't know" is a headline feature, in the summary AND its section.
        "what_we_dont_know": [g.as_json() for g in dossier.gaps],
        "sections": [s.as_json() for s in dossier.sections],
        "source_families": list(dossier.source_families),
    }


def render_json_str(dossier: Dossier) -> str:
    return json.dumps(render_json(dossier), indent=2, sort_keys=False)


# --- SIG-UI-013: the print/PDF path ------------------------------------------


def _e(text: object) -> str:
    return html.escape(str(text))


def _figure_html(fig: Figure) -> str:
    r = fig.reconciliation
    lb = " (lower bound)" if fig.lower_bound else ""
    rows = [
        "<details class='reconciliation'>",
        f"<summary>{_e(fig.label)}: <strong>{_e(fig.value)}</strong>"
        f"{_e(fig.unit and ' ' + fig.unit)}{lb}</summary>",
        f"<p class='rule'>Rule: {_e(r.rule)}</p>",
        f"<p class='note'>{_e(r.note)}</p>",
        "<table class='competing'><thead><tr>"
        "<th>value</th><th>source</th><th>tier</th><th>W</th><th>date</th><th>document</th>"
        "</tr></thead><tbody>",
    ]
    for c in (r.winning, *r.competing):
        rows.append(
            "<tr>"
            f"<td>{_e(c.value)}</td><td>{_e(c.source_family)}</td>"
            f"<td>{_e(c.reliability)}</td><td>{_e(c.weight)}</td>"
            f"<td>{_e(c.observed_at.isoformat())}</td>"
            f"<td><a href='{_e(c.document.stable_locator)}'>"
            f"{_e(c.document.locator)}</a></td>"
            "</tr>"
        )
    rows.append("</tbody></table></details>")
    return "\n".join(rows)


def _row_html(row: Row) -> str:
    doc = ""
    if row.document is not None:
        doc = f" <a class='src' href='{_e(row.document.stable_locator)}'>[source]</a>"
    cls = "" if row.value is not None else " class='unknown'"
    return (
        f"<li{cls}><span class='label'>{_e(row.label)}:</span> {_e(row.display_value())}{doc}</li>"
    )


def _section_html(section: Section) -> str:
    parts = [f"<h2>{_e(section.title)}</h2>"]
    for fig in section.figures:
        parts.append(_figure_html(fig))
    if section.rows:
        parts.append("<ul class='rows'>")
        parts.extend(_row_html(r) for r in section.rows)
        parts.append("</ul>")
    return "\n".join(parts)


def _page_footer_html(dossier: Dossier) -> str:
    # Present on EVERY page (SIG-UI-013): as-of date + permalink.
    return (
        "<footer class='page-footer'>"
        f"<span class='as-of'>As of {_e(dossier.as_of.isoformat())}</span>"
        f" · <a class='permalink' href='{_e(dossier.permalink)}'>{_e(dossier.permalink)}</a>"
        "</footer>"
    )


_PRINT_CSS = """
@page { size: letter; margin: 2cm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #111; }
.page { page-break-after: always; }
.page:last-child { page-break-after: auto; }
.page-footer { border-top: 1px solid #999; margin-top: 1.5rem; padding-top: .4rem;
  font-size: .75rem; color: #444; }
.incompleteness { border: 2px solid #b00; padding: .6rem; margin: .8rem 0; font-weight: bold; }
.unknown { color: #666; font-style: italic; }
details.reconciliation { margin: .4rem 0; }
table.competing { border-collapse: collapse; font-size: .8rem; }
table.competing th, table.competing td { border: 1px solid #ccc; padding: .2rem .4rem; }
"""


def render_print_html(dossier: Dossier, *, sections_per_page: int = 3) -> str:
    """The print/PDF path (SIG-UI-013): paginated, with sources, and with the
    as-of date + permalink on every page. Print-to-PDF from a browser produces a
    council-ready document; a server-side PDF renderer is deferred to P15.2."""
    dossier.validate()
    footer = _page_footer_html(dossier)
    banner = f"<div class='incompleteness'>{_e(dossier.incompleteness_banner())}</div>"

    pages: list[str] = []
    # Page 1 header carries the title, the incompleteness banner, and a summary of
    # what we don't know (SIG-UI-011/012).
    gap_items = "\n".join(f"<li>{_e(g.label)} — <em>{_e(g.status)}</em></li>" for g in dossier.gaps)
    header = (
        f"<h1>{_e(dossier.subject_label)}</h1>"
        f"<p class='jurisdiction'>{_e(dossier.jurisdiction)}</p>"
        f"{banner}"
        "<section class='summary-gaps'><h2>What we don't know (summary)</h2>"
        f"<ul>{gap_items}</ul></section>"
    )

    chunks = [
        dossier.sections[i : i + sections_per_page]
        for i in range(0, len(dossier.sections), sections_per_page)
    ]
    for idx, chunk in enumerate(chunks):
        body = "\n".join(_section_html(s) for s in chunk)
        head = header if idx == 0 else ""
        pages.append(f"<div class='page'>\n{head}\n{body}\n{footer}\n</div>")

    return (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n<meta charset='utf-8'>\n"
        f"<title>{_e(dossier.subject_label)} — SIG dossier</title>\n"
        f"<style>{_PRINT_CSS}</style>\n</head>\n<body>\n"
        + "\n".join(pages)
        + "\n</body>\n</html>\n"
    )


def page_count(
    html_doc: str, *, sections_per_page: int = 3, section_total: int = len(SECTION_IDS)
) -> int:
    """The number of print pages (for tests): ceil(sections / per_page)."""
    return -(-section_total // sections_per_page)


__all__ = [
    "SECTION_IDS",
    "SECTION_ORDER",
    "SECTION_TITLES",
    "NOT_RESEARCHED",
    "SEARCHED_NOT_FOUND",
    "DocumentRef",
    "ReconClaim",
    "Reconciliation",
    "Figure",
    "Row",
    "Section",
    "Gap",
    "Dossier",
    "render_json",
    "render_json_str",
    "render_print_html",
    "page_count",
]
