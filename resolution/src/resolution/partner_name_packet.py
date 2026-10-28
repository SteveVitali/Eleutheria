# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The OP-15 disposition packet generator for the partner-name audit (P35.21).

`partner-name-audit` measures the legacy ``sig.org.name`` key set
(:func:`resolution.partner_name_audit.name_scope_report`); this module turns
that read-only report into the committed **disposition packet** the operator's
OP-15 sitting consumes (``D-P32.3-1`` — sized here, decided never here).

What the packet carries, and what it deliberately does not:

* **N, honestly measured** — ``legacy_keys`` and the per-option blast radii,
  each with the query and the report digest it was counted from
  (SIG-ENG-042: a measured count, never a sampled guess). A report with zero
  legacy keys is a *vacuous* result for this run — the generator refuses it
  (``PartnerNamePacketError``) unless ``allow_empty`` is an explicit,
  recorded choice.
* **The OP-15 groupings** — ``keep`` (single-source keys whose union was
  harmless), ``split`` (multi-source keys and the ``sig.org.name_scoped``
  candidates they decompose into) and ``same_as`` (marked *not sized* by this
  query: the report carries no strong-identifier joinability — an honest
  null, never an invented count).
* **Part VIII (§0.7):** the packet lists key ids and counts only — per-key
  rows are ``entity_id`` + ``name_key_sha256`` (the join digest back to the
  private audit JSON) + counts. No registrant name, label, or free text ever
  leaves the report on its way into a committed artifact.
* **Bounds and provenance** — the verbatim provenance query, its sha256, the
  sha256 of the report JSON consumed, and the ``date -u`` bounds the runner
  recorded around the read.

Two shapes:

* :func:`build_packet` — the *measured* packet over a real report.
* :func:`build_queued_packet` — the ``prepared_not_executed`` packet an OM-19
  queued run commits: the same query + digest surface, ``n: null``,
  ``measured: null`` — nothing is fabricated as counted.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .partner_name_audit import _REPORT_SQL

__all__ = [
    "KEYS_COLUMNS",
    "OBLIGATION_ID",
    "PACKET_SCHEMA",
    "PartnerNamePacketError",
    "build_packet",
    "build_queued_packet",
    "keys_csv",
    "load_report",
    "packet_sha256",
    "query_sha256",
    "render_markdown",
    "report_sha256",
    "write_packet",
]

#: The committed record type of the disposition packet.
PACKET_SCHEMA = "sig.partner-name-disposition-packet/1"

#: The deferral this packet sizes (it stays OPEN — sized, never decided).
OBLIGATION_ID = "D-P32.3-1"

#: The per-key CSV columns — ids + digests + counts only (Part VIII).
KEYS_COLUMNS = ("entity_id", "name_key_sha256", "source_count", "split_count")

#: How a queued run marks its packet — same surface, nothing counted.
STATUS_MEASURED = "measured"
STATUS_QUEUED = "prepared_not_executed"


class PartnerNamePacketError(ValueError):
    """A packet that cannot be honestly built (vacuous or malformed input)."""


def query_sha256() -> str:
    """sha256 of the verbatim provenance query the counts come from."""
    return hashlib.sha256(_REPORT_SQL.encode("utf-8")).hexdigest()


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def report_sha256(report: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of the audit report the packet consumed."""
    return hashlib.sha256(_canonical(report)).hexdigest()


def packet_sha256(packet: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of an emitted packet (integrity anchor)."""
    return hashlib.sha256(_canonical(packet)).hexdigest()


def _key_sha256(name_key: str) -> str:
    """The Part VIII-safe join id for one legacy key — a digest, never the name."""
    return hashlib.sha256(name_key.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a ``partner-name-audit`` JSON report; refuse a malformed one."""
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PartnerNamePacketError(f"cannot read audit report {path}: {exc}") from exc
    if not isinstance(report, dict):
        raise PartnerNamePacketError(f"audit report {path} is not a JSON object")
    if not isinstance(report.get("legacy_keys"), int):
        raise PartnerNamePacketError(
            f"audit report {path} has no integer 'legacy_keys' — "
            "it is not a partner-name-audit report"
        )
    if not isinstance(report.get("impacts"), list):
        raise PartnerNamePacketError(
            f"audit report {path} has no 'impacts' list — it is not a partner-name-audit report"
        )
    return report


def _impact_key_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-key packet rows — ids + digests + counts only (Part VIII)."""
    rows = []
    for impact in report["impacts"]:
        name_key = str(impact.get("name_key") or "")
        sources = impact.get("sources") or []
        proposed = impact.get("proposed_scoped_keys") or []
        split = impact.get("split_count")
        rows.append(
            {
                "entity_id": str(impact.get("entity_id") or ""),
                "name_key_sha256": _key_sha256(name_key),
                "source_count": len(sources),
                "split_count": int(split) if isinstance(split, int) else max(len(proposed), 1),
            }
        )
    rows.sort(key=lambda r: (r["entity_id"], r["name_key_sha256"]))
    return rows


def build_packet(
    report: dict[str, Any],
    *,
    spine: str,
    started_at: str,
    finished_at: str,
    generated_at: str | None = None,
    allow_empty: bool = False,
) -> dict[str, Any]:
    """The measured OP-15 disposition packet over a real audit report.

    ``started_at``/``finished_at`` are the ``date -u`` bounds the runner
    recorded around the hosted read. ``allow_empty`` is the recorded escape
    for a spine that genuinely carries zero legacy keys — without it an
    empty result fails loud (SIG-ENG-042: a measured-nothing run never
    reports success).
    """
    n = report.get("legacy_keys")
    if not isinstance(n, int):
        raise PartnerNamePacketError("audit report carries no integer 'legacy_keys'")
    if n <= 0 and not allow_empty:
        raise PartnerNamePacketError(
            "partner-name-audit returned 0 legacy sig.org.name keys — the "
            "packet refuses a vacuous N (SIG-ENG-042): re-check the spine and "
            "query, or pass --allow-empty as a recorded operator choice"
        )
    impacts = report.get("impacts") or []
    if n != len(impacts):
        raise PartnerNamePacketError(
            f"audit report is inconsistent: legacy_keys={n} but "
            f"{len(impacts)} impact rows — never smooth a count"
        )

    rows = _impact_key_rows(report)
    split_histogram: dict[str, int] = {}
    distinct_sources: set[str] = set()
    scoped_candidates = 0
    for impact in impacts:
        sources = [str(s) for s in (impact.get("sources") or [])]
        distinct_sources.update(sources)
        proposed = impact.get("proposed_scoped_keys") or []
        split = impact.get("split_count")
        split_n = int(split) if isinstance(split, int) else max(len(proposed), 1)
        split_histogram[str(split_n)] = split_histogram.get(str(split_n), 0) + 1
        scoped_candidates += len(proposed)

    keep_keys = sum(1 for r in rows if r["split_count"] == 1)
    split_keys = sum(1 for r in rows if r["split_count"] > 1)
    return {
        "record_type": PACKET_SCHEMA,
        "status": STATUS_MEASURED,
        "generated_at": generated_at or _utc_now(),
        "obligation": OBLIGATION_ID,
        "scheme": report.get("scheme", "sig.org.name"),
        "spine": spine,
        "dry_run": True,
        "run_bounds": {"started_at": started_at, "finished_at": finished_at},
        "query": {
            "sql": _REPORT_SQL,
            "sha256": query_sha256(),
            "note": (
                "the verbatim provenance SELECT of "
                "resolution.partner_name_audit.name_scope_report — every "
                "count in this packet derives from exactly this query"
            ),
        },
        "report_sha256": report_sha256(report),
        "n": n,
        "measured": {
            "legacy_keys": n,
            "split_keys": split_keys,
            "scoped_candidates_total": scoped_candidates,
            "distinct_asserting_sources": len(distinct_sources),
            "split_count_histogram": dict(sorted(split_histogram.items())),
        },
        "option_blast_radii": {
            "keep": {
                "keys": keep_keys,
                "basis": (
                    "split_count == 1 — single-source keys whose global union "
                    "was harmless (the 'keep the entity' OP-15 option)"
                ),
            },
            "split": {
                "keys": split_keys,
                "scoped_candidates": scoped_candidates,
                "basis": (
                    "split_count > 1 — multi-source keys; each decomposes "
                    "into its reported sig.org.name_scoped candidates (the "
                    "auto-union exposure the OP-15 'split' option reviews)"
                ),
            },
            "same_as": {
                "sized": False,
                "keys": None,
                "basis": (
                    "not sized by this query — the audit report carries no "
                    "strong-identifier joinability; the 'same_as' OP-15 "
                    "option needs a strong-id census the packet honestly "
                    "does not claim"
                ),
            },
        },
        "keys": rows,
        "notes": [
            "counts key ids only — per-key rows are entity_id + "
            "name_key_sha256 + counts; no registrant name or label leaves "
            "the audit report (Part VIII)",
            "this row measures; it never decides — every disposition is the "
            "operator's (OP-15), and D-P32.3-1 stays OPEN until they land",
        ],
    }


def build_queued_packet(
    *,
    spine: str,
    planned_at: str,
    reason: str,
    rerun: str,
) -> dict[str, Any]:
    """The ``prepared_not_executed`` packet a queued (OM-19) run commits.

    Same query + digest surface as the measured packet; ``n`` and
    ``measured`` are ``null`` — an absent hosted read is recorded, never
    fabricated as counted.
    """
    return {
        "record_type": PACKET_SCHEMA,
        "status": STATUS_QUEUED,
        "generated_at": planned_at,
        "obligation": OBLIGATION_ID,
        "scheme": "sig.org.name",
        "spine": spine,
        "dry_run": True,
        "run_bounds": {"started_at": None, "finished_at": None},
        "planned_at": planned_at,
        "queue": {
            "reason": reason,
            "rerun": rerun,
            "env_required": [
                "SIG_GCP_PROJECT",
                "ADC (gcloud auth application-default)",
                "SIG_PARTNER_AUDIT_DSN",
                "cloud-sql-proxy on PATH",
            ],
        },
        "query": {
            "sql": _REPORT_SQL,
            "sha256": query_sha256(),
            "note": (
                "the verbatim provenance SELECT of "
                "resolution.partner_name_audit.name_scope_report — the same "
                "query the re-run counts from; its digest is computed now so "
                "the queued packet already pins what will be measured"
            ),
        },
        "report_sha256": None,
        "n": None,
        "measured": None,
        "option_blast_radii": {
            "keep": {"keys": None, "basis": "split_count == 1 — sized at the re-run"},
            "split": {
                "keys": None,
                "scoped_candidates": None,
                "basis": "split_count > 1 — sized at the re-run",
            },
            "same_as": {
                "sized": False,
                "keys": None,
                "basis": (
                    "not sized by this query — a strong-id census is owed "
                    "separately; the packet claims no count"
                ),
            },
        },
        "keys": [],
        "notes": [
            "queued run — nothing was measured; n and measured are null, never a fabricated count",
            "counts key ids only — per-key rows are entity_id + "
            "name_key_sha256 + counts; no registrant name or label leaves "
            "the audit report (Part VIII)",
            "this row measures; it never decides — every disposition is the "
            "operator's (OP-15), and D-P32.3-1 stays OPEN until they land",
        ],
    }


def keys_csv(packet: dict[str, Any]) -> str:
    """The per-key CSV — ``entity_id``, ``name_key_sha256``, counts only."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(KEYS_COLUMNS)
    for row in packet["keys"]:
        writer.writerow([row[c] for c in KEYS_COLUMNS])
    return buf.getvalue()


def render_markdown(packet: dict[str, Any]) -> str:
    """The committed PACKET.md — counts, groupings, query + digest, bounds."""
    measured = packet["status"] == STATUS_MEASURED
    lines = [
        "# P35.21 — partner-name disposition packet (D-P32.3-1)",
        "",
        f"**Status:** `{packet['status']}` — "
        + (
            f"measured over `{packet['spine']}`, read-only."
            if measured
            else "the hosted read-only audit is QUEUED; nothing was "
            "measured and no count is claimed."
        ),
        "",
        f"- **Obligation:** `{packet['obligation']}` (sizes the engineering "
        "half; stays OPEN — the operator's OP-15 dispositions decide)",
        f"- **Spine:** `{packet['spine']}` · **Scheme:** `{packet['scheme']}` "
        f"· **Dry run:** `{str(packet['dry_run']).lower()}`",
        f"- **Generated:** {packet['generated_at']} (`date -u`)",
        "- **Query sha256:** `" + packet["query"]["sha256"] + "`",
        "- **Report sha256:** `" + str(packet["report_sha256"]) + "`"
        if measured
        else "- **Report sha256:** `null` — no report exists yet",
        "- **Run bounds (`date -u`):** "
        f"{packet['run_bounds']['started_at']} → "
        f"{packet['run_bounds']['finished_at']}",
    ]
    if measured:
        m = packet["measured"]
        lines += [
            "",
            "## N",
            "",
            f"**`legacy_keys` = {packet['n']}** — counted, never sampled (SIG-ENG-042).",
            "",
            "| measure | count |",
            "|---|---|",
            f"| legacy `sig.org.name` keys (N) | {m['legacy_keys']} |",
            f"| keys splitting into >1 scoped candidate | {m['split_keys']} |",
            f"| `sig.org.name_scoped` candidates total | {m['scoped_candidates_total']} |",
            f"| distinct asserting sources observed | {m['distinct_asserting_sources']} |",
            "",
            "## OP-15 option blast radii",
            "",
            "| option | keys | scoped candidates | basis |",
            "|---|---|---|---|",
            f"| keep | {packet['option_blast_radii']['keep']['keys']} | — | "
            "single-source keys (harmless union) |",
            f"| split | {packet['option_blast_radii']['split']['keys']} | "
            f"{packet['option_blast_radii']['split']['scoped_candidates']} | "
            "multi-source keys (the auto-union exposure) |",
            "| same_as | *not sized* | — | this query carries no strong-id "
            "joinability — no count claimed |",
            "",
            "## Split-count histogram",
            "",
            "| keys decomposing into N scoped candidates | key count |",
            "|---|---|",
        ]
        for split, count in packet["measured"]["split_count_histogram"].items():
            lines.append(f"| {split} | {count} |")
    else:
        lines += [
            "",
            "## Queued run — the re-run measures",
            "",
            f"- **Reason:** {packet['queue']['reason']}",
            f"- **Planned at:** {packet['planned_at']} (`date -u`)",
            "- **Re-run (verbatim):**",
            "",
            "```",
            packet["queue"]["rerun"],
            "```",
            "",
            "- **Environment required:** "
            + ", ".join(f"`{v}`" for v in packet["queue"]["env_required"]),
            "",
            "N, the per-option blast radii and the per-key rows are `null`/`[]` —"
            " an absent hosted read is recorded, never fabricated.",
        ]
    lines += [
        "",
        "## The provenance query (verbatim)",
        "",
        "```sql",
        packet["query"]["sql"].strip("\n"),
        "```",
        "",
        "## Part VIII",
        "",
        "Key ids and counts only: per-key rows (`keys.csv`, `packet.json`) are "
        "`entity_id` + `name_key_sha256` + counts. No registrant name, label "
        "or free text leaves the audit report into a committed artifact — the "
        "full report JSON (which names keys) stays in the gitignored "
        "`docs/build/logs/` tree.",
        "",
        "*This packet measures; it never decides. Every disposition of a "
        "legacy key is the operator's OP-15 decision, recorded on its own "
        "line — `D-P32.3-1` stays OPEN until those land.*",
        "",
    ]
    return "\n".join(lines)


def write_packet(
    packet: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    """Emit the committed packet artifacts under ``out_dir``.

    ``packet.json`` — the machine record (+ its sha256 beside it);
    ``PACKET.md`` — the human record; ``keys.csv`` — the per-key rows
    (emitted only for a measured packet).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "packet.json"
    text = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    sha_path = out / "packet.sha256"
    sha_path.write_text(f"{packet_sha256(packet)}  packet.json\n", encoding="utf-8")
    md_path = out / "PACKET.md"
    md_path.write_text(render_markdown(packet), encoding="utf-8")
    paths = {"packet": json_path, "sha256": sha_path, "markdown": md_path}
    if packet["status"] == STATUS_MEASURED:
        csv_path = out / "keys.csv"
        csv_path.write_text(keys_csv(packet), encoding="utf-8")
        paths["keys"] = csv_path
    return paths
