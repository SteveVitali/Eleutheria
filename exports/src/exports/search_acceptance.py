# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.71 / R11-K13-SRCH-07 — the search acceptance harness
(``sig.search-acceptance/1``).

One offline leg runs the SRCH-07 acceptance battery over a built release
directory, through the same verified path the serving route uses
(``SearchEngineV2.open_release`` — SIG-SRCH-011):

* the **development benchmark** (the committed
  ``sig.search-benchmark-queries/1`` dev set) — top-3 >= 0.90 on answerable
  queries (SIG-SRCH-013);
* the **held-out benchmark** — the P36.79 sealed set, read once at
  acceptance under B-28 = b: the supplied blob is sha256-verified against
  the committed ``sig.held-out-relevance-descriptor/1`` — a mismatch is a
  hard stop, never read — top-3 >= 0.80, 0 misleading top hits;
* **index bytes** <= 150 MiB (SIG-SRCH-014) with measured latency
  percentiles reported as measured;
* the **K13 §8 journey shapes** A1 + J2 as engine-level legs (recorded
  ``agent-verified`` — never user research, P4): A1 a named place resolves
  first with its records count; J2 a ``jurisdiction=<jkey>`` request scopes
  to the key AND its descendants (the D-P36.56-1 chain-aware filter);
* the **cost block** (SIG-UI-081): a supplied billing readout is checked
  against the $300/month ceiling; absent, the block records
  ``deferred`` — the hosted billing export rides the post-promotion
  verify leg.

The report commits aggregate + per-id outcomes only: held-out rows never
carry query text, expected strings or suggestions (the seal boundary —
B-28 = b). ``--enforce`` gates the exit code on the declared thresholds;
0 misleading top hits is the spine and always fails the report verdict.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import search_benchmark as sb
from .search_query_v2 import SearchEngineV2, SearchParamsV2

ACCEPTANCE_SCHEMA = "sig.search-acceptance/1"
INDEX_BYTES_LIMIT = 150 * 1024 * 1024  # SIG-SRCH-014: <= 150 MB per release
DEV_TOP3_TARGET = 0.90  # SIG-SRCH-013
HELD_OUT_TOP3_TARGET = 0.80
COST_CEILING_USD = 300.0  # SIG-UI-081

DEFAULT_DEV_SET = Path(__file__).resolve().parent / "data" / "search_dev_queries.json"


class SearchAcceptanceError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _release_index_bytes(release_dir: Path, engine: SearchEngineV2) -> dict[str, Any]:
    """Total v2 index bytes the release carries (SIG-SRCH-014's bound)."""
    pub = engine.publication_id
    files: dict[str, int] = {}
    for p in release_dir.glob(f"releases/{pub}/search/*.sqlite"):
        files[str(p.relative_to(release_dir))] = p.stat().st_size
    for p in release_dir.glob(f"r/{pub}/c/*/*.sqlite"):
        files[str(p.relative_to(release_dir))] = p.stat().st_size
    return {"files": files, "total": sum(files.values()), "limit": INDEX_BYTES_LIMIT}


def _strip_held_out_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per-id outcomes only — no query text, no suggestion, no expected
    strings (the sealed set never lands in the committed tree)."""
    out = []
    for r in report.get("queries") or []:
        out.append(
            {
                "id": r.get("id"),
                "kind": r.get("kind"),
                "judgement": r.get("judgement"),
                "answerable": r.get("answerable"),
                "rank": r.get("rank"),
                "hit_at_k": r.get("hit_at_k"),
                "misleading_top_hit": r.get("misleading_top_hit"),
                "results_returned": r.get("results_returned"),
                "latency_ms": r.get("latency_ms"),
            }
        )
    return out


def _journey_legs(engine: SearchEngineV2) -> list[dict[str, Any]]:
    """K13 §8 A1/J2 shapes at engine level — recorded ``agent-verified``
    (P4: never user research). Each leg reports its checks and a verdict;
    an empty corpus says ``no_evidence`` rather than fabricating a pass."""
    legs: list[dict[str, Any]] = []
    # A1 — a named place resolves first with its records held.
    a1_resp = engine.search(sb.engine_params("Oklahoma City"))
    top = a1_resp.get("top") or []
    first = top[0] if top else {}
    a1_checks = {
        "top_first_is_place": bool(first) and first.get("type") == "place",
        "records_reported": bool(first.get("records", {}).get("total")),
        "top_card_name": str(first.get("name") or ""),
    }
    legs.append(
        {
            "id": "A1",
            "shape": "named place first (K13 §8 A1)",
            "checks": a1_checks,
            "verdict": (
                "pass"
                if all([a1_checks["top_first_is_place"], a1_checks["records_reported"]])
                else ("no_evidence" if not top else "fail")
            ),
        }
    )
    # J2 — jurisdiction=<jkey> scopes to the key AND its descendants.
    j2_resp = engine.search(
        SearchParamsV2(
            q_raw=None,
            q_tokens=[],
            types=None,
            filters={"jurisdiction": "iso3166-2:US-OK"},
            limit=50,
            group=None,
            cursor=None,
        )
    )
    subtree = set(engine.jurisdiction_subtree("iso3166-2:US-OK"))
    recs = [r for g in j2_resp.get("record_groups") or [] for r in g.get("results") or []]
    keys = {str(r.get("jurisdiction") or r.get("place_key") or "") for r in recs}
    # ``jurisdiction`` on the card is None for 'unreported'; the subtree
    # check reads place_key through the row's jurisdiction field only.
    in_scope = keys <= (subtree | {""})
    legs.append(
        {
            "id": "J2",
            "shape": "jurisdiction= scopes to key + descendants (D-P36.56-1)",
            "checks": {
                "records_returned": len(recs),
                "distinct_place_keys": sorted(keys - {""}),
                "all_in_subtree": in_scope,
                "subtree_size": len(subtree),
            },
            "verdict": ("pass" if recs and in_scope else ("no_evidence" if not recs else "fail")),
        }
    )
    return legs


def cost_block(billing: Mapping[str, Any] | None) -> dict[str, Any]:
    """SIG-UI-081's serving-cost readout — map sessions, tiles, search
    queries, downloads egress vs the $300/month ceiling. ``billing`` is a
    caller-supplied readout JSON; absent → ``deferred`` (the hosted billing
    export rides the post-promotion verify leg)."""
    if billing is None:
        return {
            "status": "deferred",
            "note": "no billing export supplied — the hosted readout rides the verify leg",
            "ceiling_usd": COST_CEILING_USD,
        }
    fields = {
        "map_sessions": billing.get("map_sessions"),
        "tile_requests": billing.get("tile_requests"),
        "search_queries": billing.get("search_queries"),
        "egress_gb": billing.get("egress_gb"),
        "monthly_usd": billing.get("monthly_usd"),
    }
    usd = billing.get("monthly_usd")
    verdict = "unread" if usd is None else ("within" if float(usd) <= COST_CEILING_USD else "over")
    return {
        "status": "measured",
        "ceiling_usd": COST_CEILING_USD,
        "verdict": verdict,
        **fields,
    }


def run_acceptance(
    release_dir: Path | str,
    *,
    dev_queries: Path | str | None = None,
    held_out_blob: bytes | None = None,
    descriptor: Mapping[str, Any] | None = None,
    billing: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
    posture: str = "local",
) -> dict[str, Any]:
    """Run the SRCH-07 acceptance battery over ``release_dir``.

    ``held_out_blob`` — the sealed-set bytes (emitted by the ops seal lane
    or fetched from the restricted object); sha256-verified against the
    committed descriptor — a mismatch is a hard stop, never read.
    ``posture`` names the measured posture honestly (``local`` here; the
    staging 1 vCPU posture belongs to the verify leg)."""
    release_dir = Path(release_dir)
    desc = dict(descriptor or sb.load_held_out_descriptor())
    qset = sb.load_query_set(dev_queries or DEFAULT_DEV_SET)

    t0 = time.monotonic()
    engine = SearchEngineV2.open_release(release_dir)
    try:
        dev = sb.run_release_benchmark(release_dir, qset, mode="dev", generated_at=generated_at)
        held: dict[str, Any] | None = None
        held_doc: dict[str, Any] | None = None
        if held_out_blob is not None:
            held_doc = sb.verify_held_out_blob(held_out_blob, desc)  # hard stop on mismatch
            held = sb.run_benchmark(
                lambda q: engine.search(sb.engine_params(q)),
                sb.adapt_held_out_queries(held_doc),
                mode="held-out",
                set_id=str(desc.get("set_id") or ""),
                release=dev.get("release"),
                held_out_descriptor=desc,
                generated_at=generated_at,
            )
        journeys = _journey_legs(engine)
        sizes = _release_index_bytes(release_dir, engine)
    finally:
        engine.close()
    wall_ms = round((time.monotonic() - t0) * 1000.0, 3)

    dev_sum = dev["summary"]
    held_sum = held["summary"] if held else None
    thresholds: list[dict[str, Any]] = [
        {
            "id": "dev_top3",
            "requirement": "SIG-SRCH-013",
            "target": f">= {DEV_TOP3_TARGET}",
            "measured": dev_sum["top3_success_rate"],
            "verdict": (
                "pass" if (dev_sum["top3_success_rate"] or 0) >= DEV_TOP3_TARGET else "unmet"
            ),
        },
        {
            "id": "held_out_top3",
            "requirement": "SIG-SRCH-013",
            "target": f">= {HELD_OUT_TOP3_TARGET}",
            "measured": held_sum["top3_success_rate"] if held_sum else None,
            "verdict": (
                "not_run"
                if held_sum is None
                else (
                    "pass"
                    if (held_sum["top3_success_rate"] or 0) >= HELD_OUT_TOP3_TARGET
                    else "unmet"
                )
            ),
        },
        {
            "id": "misleading_top_hits",
            "requirement": "SIG-SRCH-013",
            "target": "== 0",
            "measured": (dev_sum["misleading_top_hits"] or 0)
            + ((held_sum["misleading_top_hits"] or 0) if held_sum else 0),
            "verdict": "pass",
        },
        {
            "id": "index_bytes",
            "requirement": "SIG-SRCH-014",
            "target": f"<= {INDEX_BYTES_LIMIT}",
            "measured": sizes["total"],
            "verdict": "pass" if sizes["total"] <= INDEX_BYTES_LIMIT else "unmet",
        },
    ]
    misleading = thresholds[2]["measured"]
    thresholds[2]["verdict"] = "pass" if misleading == 0 else "fail"
    unmet = [t["id"] for t in thresholds if t["verdict"] in ("unmet", "fail")]
    report: dict[str, Any] = {
        "schema": ACCEPTANCE_SCHEMA,
        "generated_at": generated_at,
        "posture": posture,
        "release": dev.get("release"),
        "verdict": "fail" if misleading else ("unmet" if unmet else "pass"),
        "unmet": unmet,
        "wall_ms": wall_ms,
        "thresholds": thresholds,
        "dev": {"summary": dev_sum, "queries": dev.get("queries") or []},
        "held_out": (
            None
            if held is None
            else {
                "seal": {
                    "descriptor": sb.HELD_OUT_DESCRIPTOR_RELPATH,
                    "descriptor_sha256": desc.get("sha256"),
                    "set_id": desc.get("set_id"),
                    "blob_bytes": len(held_out_blob or b""),
                    "read": "verified — sha256 equals the committed descriptor",
                },
                "summary": held_sum,
                "queries": _strip_held_out_rows(held),
            }
        ),
        "index_bytes": sizes,
        "journeys": journeys,
        "cost": cost_block(billing),
    }
    return report
