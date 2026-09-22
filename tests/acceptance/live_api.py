# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Run J-1 and the Q-1…Q-13 acceptance queries against a RUNNING API (P21.4).

The §2.3 acceptance queries (SIG-CHART-009) are normally executed in-process over
the fixture graph. P21.4 adds the ``--live-api`` option: the same queries executed
against the running read API (`SIG_STAGING_API_URL`), so the first-jurisdiction run
proves the *composed* stack answers them, not just the library. The result is
written to ``docs/build/okc/acceptance_<date>.json`` — pass/fail per query.

**No green sources (ticket Notes, HG-03 skipped).** This is *not* a live fetch:
the spine holds the committed OKC slice (loaded by ``sig-ops seed``). So a query
lands in one of two states:

* ``pass`` — a query in the **fixture-backed subset** answered by the composed
  stack over the seeded slice (e.g. Q-6, the 299-vs-190 contradiction).
* ``blocked`` — a query whose carrier needs an ingested source that is not green
  on this build. It records the exact ``HG-03-pending`` command to run once a
  source is flipped. A blocked query does NOT fail the run; a fixture-subset query
  that fails DOES.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

#: The seeded OKC deployment subject (see ops/src/ops/seed.py).
DEPLOYMENT = "sig:deployment:okc-okcpd-flock"

#: The five-field carrier map (§2.1) each Qn resolves through.
_CARRIERS: dict[str, str] = {
    "Q-1": "PhysicalAsset + geometry (§11.8)",
    "Q-2": "Role edges: owns, operates (§12.4)",
    "Q-3": "Deployment → Technology (§11.5)",
    "Q-4": "Vendor, Product (§11.2, §11.4)",
    "Q-5": "Contract (§11.11)",
    "Q-6": "The distinct count predicates (§29.1)",
    "Q-7": "ConfigurationState (§11.15)",
    "Q-8": "AccessRelationship, configured (§12.5)",
    "Q-9": "UsageAggregate (§11.16)",
    "Q-10": "Reason-category aggregates (§11.16, §24.2)",
    "Q-11": "Policy, LegalInstrument (§11.13, §11.14)",
    "Q-12": "Lifecycle state machine (§13.4) + AccountabilityEvent (§11.17)",
    "Q-13": "IntegrationRelationship + access-path closure (§30.2)",
}

_QUESTIONS: dict[str, str] = {
    "Q-1": "Where is a physical surveillance device?",
    "Q-2": "Which organization owns or operates it?",
    "Q-3": "Which surveillance technology has a given agency adopted?",
    "Q-4": "Which vendor and product are involved?",
    "Q-5": "What did the deployment cost, and under what contract?",
    "Q-6": "How many devices were purchased or reported?",
    "Q-7": "What is the system configured to retain, search, or share?",
    "Q-8": "Which other organizations can access the data?",
    "Q-9": "Which organizations actually searched the data?",
    "Q-10": "For what stated reasons?",
    "Q-11": "What policies and legal restrictions govern the system?",
    "Q-12": "Has the deployment been suspended, canceled, replaced, or litigated?",
    "Q-13": "How does one deployment connect to broader networks?",
}


@dataclass
class QueryResult:
    id: str
    question: str
    carrier: str
    status: str  # "pass" | "blocked" | "fail"
    in_fixture_subset: bool
    endpoint: str = ""
    detail: str = ""
    blocker: str = ""


@dataclass
class AcceptanceReport:
    as_of: str
    api_url: str
    mode: str
    j1: dict[str, Any]
    queries: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class _Api:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")

    def get(self, path: str) -> tuple[int, Any]:
        url = f"{self.base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - local staging
                body = json.loads(resp.read().decode("utf-8"))
                return resp.status, body
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                return exc.code, None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return 0, {"error": str(exc)}


def _hg03(source: str, predicate: str) -> str:
    """The exact command to run once a source is flipped green (HG-03)."""
    return (
        f"HG-03-pending: flip a source (e.g. `sig-connectors review-status --source {source}`), "
        f"then `sig-connectors run --source {source} --mode live --sink pg --dsn $SIG_STAGING_DSN` "
        f"to ingest the {predicate!r} carrier."
    )


def _run_queries(api: _Api) -> list[QueryResult]:
    results: list[QueryResult] = []

    def q(qid: str, in_subset: bool, endpoint: str) -> QueryResult:
        return QueryResult(
            id=qid,
            question=_QUESTIONS[qid],
            carrier=_CARRIERS[qid],
            status="blocked",
            in_fixture_subset=in_subset,
            endpoint=endpoint,
        )

    # Q-6 — how many devices (the distinct count predicates): the seeded slice
    # carries the 299-vs-190 claimed_device_count contradiction. FIXTURE SUBSET.
    ep = f"/v1/resolution/{DEPLOYMENT}/claimed_device_count"
    r = q("Q-6", True, ep)
    status, body = api.get(ep)
    env = (body or {}).get("fact", {}).get("envelope", {}) if isinstance(body, dict) else {}
    considered = env.get("considered_claim_ids") or []
    rationale = json.dumps(env.get("rationale", {}))
    if status == 200 and env.get("agreement") == "CONTESTED" and len(considered) >= 2:
        r.status = "pass"
        r.detail = (
            f"resolution_status={env.get('resolution_status')}, agreement=CONTESTED, "
            f"{len(considered)} claims considered; both values retained "
            f"({'299' in rationale and '190' in rationale})."
        )
    elif status == 200:
        r.status = "fail"
        r.detail = f"expected a CONTESTED standoff; got {env.get('agreement')!r}"
    else:
        r.status = "fail"
        r.detail = f"API returned {status}: {body}"
    results.append(r)

    # Q-2 — which organization owns/operates: the seeded OKCPD org projections are
    # searchable in the composed spine. FIXTURE SUBSET.
    ep = "/v1/search?q=okc"
    r = q("Q-2", True, ep)
    status, body = api.get(ep)
    hits = (body or {}).get("results") or (body or {}).get("entities") or []
    if status == 200 and hits:
        r.status = "pass"
        r.detail = f"{len(hits)} entity(ies) match 'okc' in the composed spine."
    else:
        r.status = "fail"
        r.detail = f"API returned {status} with {len(hits)} hits"
    results.append(r)

    # The remaining carriers need an ingested source that is NOT green on this
    # build (HG-03 skipped). Each records its blocker + the command to run.
    blocked_specs = [
        ("Q-1", "osm", "PhysicalAsset geometry (public spine has no geo; osm layer export-only)"),
        ("Q-3", "atlas", "Deployment→Technology adoption edge"),
        ("Q-4", "atlas", "Vendor/Product identity"),
        ("Q-5", "records-request", "Contract cost/term"),
        ("Q-7", "portal", "ConfigurationState (retention/search/share)"),
        ("Q-8", "portal", "AccessRelationship (configured access)"),
        ("Q-9", "usage-audit", "UsageAggregate (observed searches)"),
        ("Q-10", "usage-audit", "Reason-category aggregates"),
        ("Q-11", "ops-manual", "Policy/LegalInstrument"),
        ("Q-12", "council-minutes", "Lifecycle/AccountabilityEvent"),
        ("Q-13", "network-graph", "IntegrationRelationship closure"),
    ]
    for qid, source, predicate in blocked_specs:
        r = q(qid, False, "")
        r.status = "blocked"
        r.blocker = _hg03(source, predicate)
        results.append(r)
    return results


def _run_j1(api: _Api) -> dict[str, Any]:
    """Execute J-1: the traversal over the slice, cross-checked against the API.

    The J-1 hops are the committed slice traversal (SIG-CHART-009); the running API
    is cross-checked on the traversal's contested hop — the claimed device count —
    so J-1 is proven end-to-end against the composed stack, not only in-process.
    """
    from acceptance import okc_slice as slice_mod

    graph = slice_mod.build_slice()
    hops = slice_mod.j1_traversal(graph)
    status, body = api.get(f"/v1/resolution/{DEPLOYMENT}/claimed_device_count")
    env = (body or {}).get("fact", {}).get("envelope", {}) if isinstance(body, dict) else {}
    api_contested = status == 200 and env.get("agreement") == "CONTESTED"
    return {
        "hops": [h.name for h in hops],
        "hop_count": len(hops),
        "source_families": sorted({e.source_family for h in hops for e in h.evidence}),
        "api_contested_count_hop": api_contested,
        "status": "pass" if (len(hops) == 12 and api_contested) else "partial",
    }


def run_acceptance(api_url: str) -> AcceptanceReport:
    api = _Api(api_url)
    j1 = _run_j1(api)
    queries = _run_queries(api)
    passed = [r for r in queries if r.status == "pass"]
    blocked = [r for r in queries if r.status == "blocked"]
    failed = [r for r in queries if r.status == "fail"]
    subset_failed = [r for r in queries if r.in_fixture_subset and r.status != "pass"]
    report = AcceptanceReport(
        as_of=date.today().isoformat(),
        api_url=api_url,
        mode="fixture-backed (shadow); no green sources — HG-03 skipped (not live)",
        j1=j1,
        queries=[asdict(r) for r in queries],
        summary={
            "total": len(queries),
            "passed": len(passed),
            "blocked": len(blocked),
            "failed": len(failed),
            "fixture_subset_all_pass": not subset_failed,
            "j1_status": j1["status"],
        },
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acceptance-live-api",
        description="Run J-1 + Q-1..Q-13 against the running API and write acceptance_<date>.json",
    )
    parser.add_argument("--api-url", required=True, help="SIG_STAGING_API_URL of the running API")
    parser.add_argument("--out", required=True, help="output path for acceptance_<date>.json")
    args = parser.parse_args(argv)

    report = run_acceptance(args.api_url)
    from pathlib import Path

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report.summary
    print(
        f"acceptance: {s['passed']} pass, {s['blocked']} blocked, {s['failed']} failed "
        f"(fixture subset all pass: {s['fixture_subset_all_pass']}; J-1: {s['j1_status']}) → {out}"
    )
    # The run "completes" as long as the fixture-backed subset passes and J-1 ran;
    # blocked queries are recorded, not failures (no green sources).
    return 0 if (s["fixture_subset_all_pass"] and not report.summary["failed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
