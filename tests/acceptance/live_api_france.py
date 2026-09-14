# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""France's own acceptance queries — the second jurisdiction (P24.6, JURIS.2 / GL-JURIS-01).

`run_france.sh` runs these against the *running* staging stack after seeding the
France slice (commune de Gex, département de l'Ain — vidéoprotection). They are
the second jurisdiction's own questions, not a relabelled copy of the OKC Q-1..13
(D7: the second jurisdiction is the design's proof, not a copy): authorization by
published **arrêté préfectoral**, procurement by **DECP national open data**, the
records regime **fr.cada**, and the Part VIII / FR-GDPR publication gate.

* FR-1 — "La vidéoprotection est-elle autorisée ?" → ``authorization_state``
  resolves to ``authorized`` (the arrêté is the dated authorization, not a contract).
* FR-2 — "Sous quel régime juridique ?" → ``statutory_citation`` names the Code
  de la sécurité intérieure.
* FR-3 — "Le déploiement est-il attesté ?" → ``deployment_exists``.
* FR-4 — "Quel marché public a été notifié ?" → ``contract_value`` on the DECP
  marché subject (the claim sits in the spine even though its UNDETERMINED rights
  keep its content out of the published export — §42 fail-closed, exercised not
  bypassed).
* FR-5 — "Quelle organisation opère le système ?" → ``/v1/search`` finds the
  police-municipale projections seeded for the ER step.
* FR-6 — "Quelle technologie ?" → ``implements_technology``.
* FR-7 — Part VIII: the exported ``web/dossiers.json`` flags the signing-officer
  row ``isPublicEmployeeName`` + ``originJurisdiction: "FR"`` and the FR adapter
  withholds it under FR-GDPR (SIG-PUB-017 — contrast: the US dossier publishes
  the equivalent name).

Queries whose carriers need a *live* source are recorded ``blocked`` with the
exact gate (HG-03 flip / HG-04 outreach) and the command to run — never fabricated
green. The fixture subset must pass for the run to complete.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# The France slice subjects (seeded by `sig-ops seed --jurisdiction france`).
DEPLOYMENT = "sig:deployment:france-gex-videoprotection"
CONTRACT = "contract:france:decp-2025kazvs0000000"
DOSSIER_SLUG = "gex-videoprotection"

_QUESTIONS: dict[str, str] = {
    "FR-1": "La vidéoprotection est-elle autorisée ?",
    "FR-2": "Sous quel régime juridique ?",
    "FR-3": "Le déploiement est-il attesté ?",
    "FR-4": "Quel marché public a été notifié ?",
    "FR-5": "Quelle organisation opère le système ?",
    "FR-6": "Quelle technologie est mise en œuvre ?",
    "FR-7": "Le nom de l'agent public signataire est-il retenu (RGPD/Part VIII) ?",
    "FR-8": "Les arrêtés au-delà du jeu d'essai (corpus RAA complet) ?",
    "FR-9": "Le registre CADA au-delà du jeu d'essai (Ma Dada) ?",
    "FR-10": "La couche OSM des caméras pour la commune ?",
}

_CARRIERS: dict[str, str] = {
    "FR-1": "LegalInstrument → authorization_state (arrêté préfectoral)",
    "FR-2": "statutory_citation (Code de la sécurité intérieure)",
    "FR-3": "deployment_exists",
    "FR-4": "Contract → contract_value (marché DECP)",
    "FR-5": "Organization (police municipale de Gex)",
    "FR-6": "implements_technology (camera-fixed-cctv)",
    "FR-7": "published dossier (publication gate, SIG-PUB-017)",
    "FR-8": "prefectoral_order corpus (raa_prefectures)",
    "FR-9": "records_request register (madada)",
    "FR-10": "PhysicalAsset geometry (OSM/ODbL layer)",
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
    jurisdiction: str
    mode: str
    traversal: dict[str, Any]
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
        f"HG-03-pending: flip the source (e.g. `sig-connectors review-status --source {source}`), "
        f"then `sig-connectors run --source {source} --mode live --sink pg --dsn $SIG_STAGING_DSN` "
        f"to ingest the {predicate!r} carrier."
    )


def _resolved_value(api: _Api, subject: str, predicate: str) -> tuple[int, Any, dict[str, Any]]:
    """GET the resolution envelope for one (subject, predicate); return (status, value, env)."""
    status, body = api.get(f"/v1/resolution/{subject}/{predicate}")
    env = (body or {}).get("fact", {}).get("envelope", {}) if isinstance(body, dict) else {}
    return status, env.get("value"), env


def _resolution_query(
    api: _Api,
    qid: str,
    subject: str,
    predicate: str,
    expect: Any,
) -> QueryResult:
    """One France resolution query: the envelope must exist and carry ``expect``."""
    endpoint = f"/v1/resolution/{subject}/{predicate}"
    r = QueryResult(
        id=qid,
        question=_QUESTIONS[qid],
        carrier=_CARRIERS[qid],
        status="blocked",
        in_fixture_subset=True,
        endpoint=endpoint,
    )
    status, value, env = _resolved_value(api, subject, predicate)
    if status != 200:
        r.status = "fail"
        r.detail = f"API returned {status} for {endpoint}"
        return r
    if value == expect:
        r.status = "pass"
        r.detail = (
            f"resolution_status={env.get('resolution_status')}, value={value!r}, "
            f"considered={len(env.get('considered_claim_ids') or [])} claim(s)."
        )
        return r
    r.status = "fail"
    r.detail = f"expected {expect!r}; got {value!r} (agreement={env.get('agreement')!r})"
    return r


def _run_queries(api: _Api, export_dir: Path | None) -> list[QueryResult]:
    results: list[QueryResult] = []

    # FR-1..FR-4 + FR-6 — resolution envelopes over the seeded France slice.
    # FIXTURE SUBSET (must pass).
    results.append(_resolution_query(api, "FR-1", DEPLOYMENT, "authorization_state", "authorized"))
    results.append(
        _resolution_query(
            api,
            "FR-2",
            DEPLOYMENT,
            "statutory_citation",
            "Code de la sécurité intérieure, art. L251-1 à L255-1",
        )
    )
    results.append(_resolution_query(api, "FR-3", DEPLOYMENT, "deployment_exists", True))
    results.append(_resolution_query(api, "FR-4", CONTRACT, "contract_value", 50754))
    results.append(
        _resolution_query(api, "FR-6", DEPLOYMENT, "implements_technology", "camera-fixed-cctv")
    )

    # FR-5 — the organization carrier: the seeded police-municipale projections
    # are searchable in the composed spine. FIXTURE SUBSET.
    ep = "/v1/search?q=france"
    r = QueryResult(
        id="FR-5",
        question=_QUESTIONS["FR-5"],
        carrier=_CARRIERS["FR-5"],
        status="blocked",
        in_fixture_subset=True,
        endpoint=ep,
    )
    status, body = api.get(ep)
    hits = (body or {}).get("results") or []
    if status == 200 and hits:
        r.status = "pass"
        r.detail = f"{len(hits)} entity(ies) match 'france' in the composed spine."
    else:
        r.status = "fail"
        r.detail = f"API returned {status} with {len(hits)} hits"
    results.append(r)

    # FR-7 — Part VIII on the published dossier: the export's dossiers.json flags
    # the officer-name row for FR-GDPR withholding, and the FR adapter refuses it.
    # FIXTURE SUBSET (checked on the export bytes, not a live call).
    r = QueryResult(
        id="FR-7",
        question=_QUESTIONS["FR-7"],
        carrier=_CARRIERS["FR-7"],
        status="blocked",
        in_fixture_subset=True,
        endpoint=str(export_dir / "web" / "dossiers.json") if export_dir else "",
    )
    if export_dir is None:
        r.status = "fail"
        r.detail = "no export dir supplied — the publication-gate check needs the export bytes"
    else:
        dossiers_path = export_dir / "web" / "dossiers.json"
        if not dossiers_path.exists():
            r.status = "fail"
            r.detail = f"missing {dossiers_path} (run sig-exports build --jurisdiction france)"
        else:
            dossiers = json.loads(dossiers_path.read_text(encoding="utf-8"))
            dossier = next((d for d in dossiers if d.get("slug") == DOSSIER_SLUG), None)
            if dossier is None:
                r.status = "fail"
                r.detail = f"no dossier with slug {DOSSIER_SLUG!r} in {dossiers_path}"
            else:
                name_rows = [
                    row
                    for section in dossier.get("sections", [])
                    for row in section.get("rows", [])
                    if row.get("isPublicEmployeeName")
                ]
                from policy.jurisdiction import adapter_publication_permitted, get

                adapter = get("FR")
                withheld = all(
                    row.get("originJurisdiction") == "FR"
                    and not adapter_publication_permitted(
                        adapter, "FR", is_public_employee_name=True
                    )
                    for row in name_rows
                )
                if name_rows and withheld:
                    r.status = "pass"
                    r.detail = (
                        f"{len(name_rows)} public-employee-name row(s) flagged for "
                        "FR-GDPR withholding (SIG-PUB-017); "
                        "adapter_publication_permitted(FR)=False."
                    )
                else:
                    r.status = "fail"
                    r.detail = (
                        "the dossier carries no FR-flagged public-employee-name row, or the "
                        "FR adapter would publish it — the FR-GDPR withholding is missing"
                    )
    results.append(r)

    # Blocked carriers — a live source is required; the gate is HG-03/HG-04.
    blocked_specs = [
        ("FR-8", "raa_prefectures", "prefectoral_order corpus beyond the committed fixture"),
        ("FR-9", "madada", "records-request register (compact gate: not_contacted)"),
        ("FR-10", "osm_overpass", "OSM camera layer for the commune (no geo slice imported)"),
    ]
    for qid, source, predicate in blocked_specs:
        r = QueryResult(
            id=qid,
            question=_QUESTIONS[qid],
            carrier=_CARRIERS[qid],
            status="blocked",
            in_fixture_subset=False,
            blocker=_hg03(source, predicate),
        )
        results.append(r)
    return results


def _run_traversal(api: _Api) -> dict[str, Any]:
    """The France fact→page walk: arrêté → deployment → published dossier.

    The second jurisdiction's equivalent of the J-1 traversal: the arrêté is the
    dated authorization (FR-1/FR-2), the marché is its procurement record (FR-4),
    and the dossier carries them to the published page (FR-7). Cross-checked
    against the running API, not only in-process.
    """
    hops = {
        "arrete_prefectoral": _resolved_value(api, DEPLOYMENT, "authorization_state"),
        "legal_regime": _resolved_value(api, DEPLOYMENT, "statutory_citation"),
        "marche_decp": _resolved_value(api, CONTRACT, "contract_value"),
    }
    ok = all(status == 200 for status, _, _ in hops.values())
    return {
        "hops": {name: {"status": s, "value": v} for name, (s, v, _) in hops.items()},
        "status": "pass" if ok else "partial",
    }


def run_acceptance(api_url: str, export_dir: Path | None = None) -> AcceptanceReport:
    api = _Api(api_url)
    traversal = _run_traversal(api)
    queries = _run_queries(api, export_dir)
    passed = [r for r in queries if r.status == "pass"]
    blocked = [r for r in queries if r.status == "blocked"]
    failed = [r for r in queries if r.status == "fail"]
    subset_failed = [r for r in queries if r.in_fixture_subset and r.status != "pass"]
    return AcceptanceReport(
        as_of=date.today().isoformat(),
        api_url=api_url,
        jurisdiction="france",
        mode="fixture-backed (shadow); no green sources — HG-03/HG-04 pending (not live)",
        traversal=traversal,
        queries=[asdict(r) for r in queries],
        summary={
            "total": len(queries),
            "passed": len(passed),
            "blocked": len(blocked),
            "failed": len(failed),
            "fixture_subset_all_pass": not subset_failed,
            "traversal_status": traversal["status"],
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acceptance-live-api-france",
        description="Run the France (JURIS.2) acceptance queries against the running API "
        "and write acceptance_<date>.json",
    )
    parser.add_argument("--api-url", required=True, help="SIG_STAGING_API_URL of the running API")
    parser.add_argument("--out", required=True, help="output path for acceptance_<date>.json")
    parser.add_argument(
        "--export-dir",
        default=None,
        help="the france export dir (for the Part VIII dossier check; default exports/out/france)",
    )
    args = parser.parse_args(argv)

    export_dir = Path(args.export_dir) if args.export_dir else Path("exports/out/france")
    report = run_acceptance(args.api_url, export_dir=export_dir)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report.summary
    print(
        f"acceptance(france): {s['passed']} pass, {s['blocked']} blocked, {s['failed']} failed "
        f"(fixture subset all pass: {s['fixture_subset_all_pass']}; traversal: "
        f"{s['traversal_status']}) → {out}"
    )
    # The run "completes" as long as the fixture-backed subset passes; blocked
    # queries are recorded, not failures (no green sources — HG-03/04 pending).
    return 0 if (s["fixture_subset_all_pass"] and not s["failed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
