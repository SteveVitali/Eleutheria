#!/usr/bin/env python3
"""SEED-13a (Round-11 Stage B, T3): Round-11 manifest chain block, `Kind: skeleton` contracts and the contract map.

Inputs (read-only; all committed):
  PD/data/round11_plan.csv          authoritative rows (chain rows 201-510 = sub_round 11A/11B/11C/11D/11D-tail)
  PD/data/ticket_catalog.csv        catalog scope / acceptance sketch / source refs per row
  PD/stageB/T1_id_map.csv           draft requirement id -> final id (SEED-12a)
  docs/research/_meta/spec_src/*.md requirement definitions (section of each id) and the Part XII Owner/Also lines

Outputs:
  skeletons        docs/tickets/<row>_<id>__<slug>.md, `Kind: skeleton`, for every chain row. A file that exists and is
                   not a skeleton (a full contract written later, e.g. by SEED-13b/c/d or a PLAN row) is never touched.
  map              PD/stageB/T3_contract_map.csv (row, id, file, kind, ... notes) incl. rows 184-187.
  manifest-block   prints the Round-11 chain block (banners + tables) for docs/tickets/00_MANIFEST.md.
  insert-manifest  inserts that block once, immediately before '## Phase gates & special points' (refuses if a
                   Round-11 banner already exists; removes nothing).
  check            verifies manifest rows, files, headers and the map against the CSV (exit 1 on any error).

PD = docs/build/planning/2026-09-30-next-phase. Stdlib only. Deterministic: the same inputs give the same bytes, except the
generation date (`--date`, default `date -u +%F` at run time) written into the skeleton comment line.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import pathlib
import re
import sys

PD = pathlib.Path(__file__).resolve().parents[2]
REPO = PD.parents[3]
TICKETS = REPO / "docs" / "tickets"
MANIFEST = TICKETS / "00_MANIFEST.md"
SPEC_SRC = REPO / "docs" / "research" / "_meta" / "spec_src"
PLAN_CSV = PD / "data" / "round11_plan.csv"
CAT_CSV = PD / "data" / "ticket_catalog.csv"
IDMAP_CSV = PD / "stageB" / "T1_id_map.csv"
MAP_OUT = PD / "stageB" / "T3_contract_map.csv"
PD_REL = "docs/build/planning/2026-09-30-next-phase"
HARNESS = "devin-desktop/swe-2-high/subagent"
TOTAL = 510
CHAIN_SUBS = ("11A", "11B", "11C", "11D", "11D-tail")
# The validator's nextTicket rule skips a chain row whose text matches this (scripts/docs/check-build-memory.sh,
# "deferred/superseded/unused ... skipped"); a live Round-11 row must never match it.
SKIP_RE = re.compile(r"superseded|deferred|unused|skipped|withdrawn|dropped", re.I)

# ── banners: the five sub-round names (plan Appendix A T3) and one boundary after each acquisition wave's activation
#    row, so the per-wave digest ("after the last row under a chain-table banner") has a boundary (T0c note).
BANNERS = [
    (201, 260, 'P34 11A "Safe, honest, truthful"', "rows 201–260, to GATE-G4"),
    (261, 271, 'P35 11B "Correct and traceable"', "part 1, to the Wave A activation (rows 261–271)"),
    (272, 290, 'P35 11B "Correct and traceable"', "part 2, typing and Wave B to its activation (rows 272–290)"),
    (291, 343, 'P35 11B "Correct and traceable"', "part 3, to GATE-G5 (rows 291–343)"),
    (344, 345, 'P36 11C "Explorable core"', "part 1, Wave C (rows 344–345)"),
    (346, 420, 'P36 11C "Explorable core"', "part 2, to GATE-G6 (rows 346–420)"),
    (421, 481, 'P37 11D "Explored and proven"', "part 1, to the Wave D activation (rows 421–481)"),
    (482, 500, 'P37 11D "Explored and proven"', "part 2, to the CAP-01 journeys (rows 482–500)"),
    (501, 510, "P38 tail", "rows 501–510, to GATE-ANNOUNCE"),
]

THEME_SECTION = {
    "R11-SAFETY-HONESTY": "§5.1",
    "R11-MEMORY-TRUTH": "§5.2",
    "R11-CI-TOOLCHAIN": "§5.3",
    "R11-DATA-CORRECTNESS": "§5.4",
    "R11-SOURCES": "§5.5",
    "R11-TRANSPARENCY": "§5.6",
    "R11-UX-CORE": "§5.7",
    "R11-UX-EXPLORE": "§5.7",
    "R11-RELEASE-OPS": "§5.8",
    "R11-R10-ACTIVATION": "§5.9",
    "R11-GOVERNANCE-RECORDS": "§5.10",
    "R11-DEBT": "§5.11",
}
# rows with no catalog entry ("NEW (S2)" / "NEW (S4c)"): their plan home
NEW_ROW_HOME = {
    "P34.50": "§5.1; §10.2 (OP-09)",
    "PLAN-11B": "§8.5; §6.2 (SIG-TRANSP)",
    "PLAN-11C": "§8.5; §6.2 (K13 UX set)",
    "PLAN-11D": "§8.5",
    "P34.48": "§6.6",
    "P34.49": "§5.1",
    "P34.47": "§13.1",
    "P35.64": "§13.1",
    "P36.73": "§13.1",
    "GATE-G4": "§8.3",
    "GATE-G5": "§8.3",
    "GATE-G6": "§8.3",
    "P35.67": "§5.8; §10.2",
    "P35.66": "§5.1",
    "P35.65": "§5.6",
    "P38.1a": "§13.2; §13.4",
    "P38.1b": "§13.2; §13.4",
    "P38.2": "§13.4",
    "GATE-ACCEPT-R11": "§13.4",
    "P38.3a": "§13.4",
    "P38.3b": "§13.4",
    "P38.3c": "§13.4; §12",
    "P38.4": "§13.4",
    "P38.5": "§13.5",
    "GATE-ANNOUNCE": "§13.5",
}

# Slug overrides (kebab, <= ~50 chars). The automatic rule reads the title; these fix titles whose first words are a
# code or would read badly. A slug, once written to the manifest, binds to its id for good (BM-MANIFEST-03).
SLUG = {
    "P34.1": "toolchain-pin-and-ci-hygiene",
    "P34.2": "recorded-ci-verifier-and-flake-policy",
    "P35.38a": "crawler-ua-contact-and-explanation-page",
    "P34.3": "ops-data-protection",
    "P34.4": "alerts-that-reach-a-human",
    "P34.5": "cost-guard-budget-alert-billing-export",
    "P34.6": "restore-drill-and-logical-export",
    "P34.50": "dns-cutover-runbook-and-zone-inventory",
    "P34.7": "append-only-checker-full-modes",
    "P34.8": "obligation-events-repair",
    "P34.9": "ledger-contract-validator-no-vacuous-pass",
    "P34.10": "one-allow-listed-publish-path",
    "P34.11": "honest-home-dossier-coverage-copy",
    "P34.12": "research-queue-truth-fixes",
    "P34.13": "chrome-format-accessibility-quick-fixes",
    "P34.14": "jurisdiction-display-names-interim",
    "P34.15": "map-network-search-island-honesty",
    "P34.16": "public-repo-honesty-corrections",
    "P34.19": "express-terms-disclosure",
    "P34.17": "web-honesty-wave-and-republish-1",
    "P34.18": "personal-handle-source-id-rename",
    "P34.20": "watch-and-evidence-empty-state-truth",
    "P34.21a": "attribution-gate-sink-rights-and-backfill",
    "P34.21b": "attribution-re-export-and-republish-2",
    "P34.22a": "date-truth-release-constants-future-date-test",
    "P34.22b": "date-truth-fixtures-and-sources-dates",
    "P34.23": "versioning-discipline-one-version-source",
    "P34.24a": "sqitch-hygiene-and-round-trip-ci",
    "P34.25": "api-honesty-code",
    "P34.24b": "sqitch-l44-52-clone-rehearsal",
    "P34.26": "adr-124-allow-dispositions",
    "P34.27": "remaining-append-only-restorations",
    "P34.28": "readout-authorship-and-signed-gate-check",
    "P34.29": "return-pass-generator-and-projection-fixes",
    "P34.30": "memory-cutover-disposition-and-transition-rule",
    "P34.31": "living-record-test-lint",
    "P34.32": "adr-index-generator-and-trigger-register",
    "P34.33": "round-close-record-checks",
    "PLAN-11B": "contracts-for-11b-and-transp-family",
    "P34.48": "re-verdict-61-boilerplate-coverage-rows",
    "P34.34a": "release-archive-link-depth-and-crawl",
    "P34.34b": "export-mode-ci-build-and-island-budgets",
    "P34.35": "research-dossier-disclosure",
    "P34.36": "release-search-states",
    "P34.37": "intake-defects-and-moderation-hardening",
    "P34.38": "sources-pilot-prep-and-registry-rows",
    "P34.39a": "osm-replay-read-back",
    "P34.39b": "first-fire-read-backs",
    "P34.40": "serving-topology-dark",
    "P34.41": "withdrawal-barrier-bytes",
    "P34.42a": "least-privilege-service-identities",
    "P34.42b": "least-privilege-job-identities-remove-editor",
    "P34.43": "execution-host-and-least-privilege-db-logins",
    "P34.49": "part-viii-at-rest-audit",
    "P34.44a": "quality-check-registry-and-ratchet-engine",
    "P34.44b": "quality-baseline-run-and-nightly-probe",
    "P34.45": "honest-evaluation-posture",
    "P34.46": "round10-schema-allows-and-api-roll",
    "P34.47": "sub-round-11a-acceptance",
    "GATE-G4": "11a-check-in",
    "P35.57": "api-release-parity",
    "P35.5": "zero-egress-distribution-host",
    "P35.67": "post-dns-cutover-probe",
    "P35.1a": "scheduler-of-record-live-diff-cron-lint",
    "P36.1a": "opt-out-register-and-reservation-refusal",
    "P35.6": "acquisition-plumbing-and-verification-harness",
    "P35.7": "registry-and-tenant-label-corrections",
    "P35.8": "legistar-matter-pass-and-agenda-vocabulary",
    "P35.9": "usaspending-crol-vocabulary-and-filters",
    "P35.10": "state-alpr-statute-seed-2026",
    "P35.11": "wave-a-activation",
    "P35.14a": "vocabulary-conformance-closed-vocabulary",
    "P35.14b": "entity-typing-and-hosted-check-constraint",
    "P35.15a": "technology-typing-slug-and-facets",
    "P35.15b": "technology-backfill",
    "P36.3": "ate-technology-concept",
    "P36.4": "official-camera-layers",
    "P36.5": "agency-alpr-flock-layers",
    "P36.6": "automated-traffic-enforcement-layers",
    "P36.7": "procurement-and-programme-registers",
    "P36.8": "statutory-disclosures-alpr-regimes",
    "P36.9a": "statutory-disclosures-uav-frt",
    "P36.9b": "statutory-disclosures-css-interception-ate-dhs",
    "P36.10": "ccops-reports-and-police-policies",
    "P36.11": "grant-council-procurement-documents-bills",
    "P35.28": "officer-naming-gate-default-deny",
    "P36.15": "redaction-pipeline",
    "P35.66": "residential-demotion",
    "P36.74": "flock-portal-connector-probe-only",
    "P36.12": "wave-b-activation",
    "P35.1b": "fleet-hygiene",
    "P35.3": "production-truth-probes-and-sentinel-scan",
    "P35.4": "ops-runbook",
    "P35.12": "release-identity-v2-and-clock-guards",
    "P35.13": "provenance-stamp-release-json-headers",
    "P35.16": "geometry-defects-at-ingest",
    "P35.17": "jurisdiction-registry-and-boundary-pack",
    "P35.18": "declared-jurisdiction-scheme",
    "P35.19": "placement-engine",
    "P35.20a": "per-dossier-provenance-unclamped-coverage",
    "P35.20b": "freshness-classes-and-map-table-suppression",
    "P35.22": "truthful-claim-identity",
    "P35.24": "truthful-subject-keys-and-re-keying",
    "P35.25": "declared-lineage-namespaces-independence",
    "P35.26": "roles-and-time-backend",
    "P35.27": "resolver-input-truth",
    "P35.29": "shared-labels-slugs-hashes",
    "P35.30": "network-labels-dates-evidence",
    "P35.31": "transparency-scrub-and-publish-secret-gate",
    "P35.32": "ingest-run-report",
    "P35.33": "run-capture-issue-export",
    "P35.34": "run-telemetry-and-binding-version-test",
    "P35.35": "registry-lanes-and-source-metadata-export",
    "P35.65": "withbase-helper-and-containment-check",
    "P35.36": "statements-files-and-provenance-panel",
    "P35.37": "figure-to-evidence-pointers",
    "P35.38b": "iri-base-and-provenance-identity",
    "P35.39": "data-dictionary-and-metadata",
    "P35.40": "source-universe-lifecycle-and-counts",
    "P35.41": "freshness-semantics-v2",
    "P35.42": "citation-block-and-release-id",
    "P35.43": "watch-producer-v1",
    "P35.44": "dossier-contribution-export",
    "P35.45": "dossiers-at-every-level-unplaced-report",
    "P35.46": "derivation-collapse-and-possible-duplicates",
    "P35.47": "publish-the-dedup",
    "P35.48": "agent-review-lane",
    "P35.50": "page-type-registry-and-route-discovery",
    "P35.51": "page-budgets-lhci-national-fixture",
    "P35.52": "tile-retention-and-verifier",
    "P35.53": "release-pipeline-and-staging-origins",
    "P35.54": "config-generations-metadata-only-promotion",
    "P35.55": "rollback-withdrawal-purge-runbook",
    "P35.56": "verification-suite-a",
    "P35.58": "verification-suite-b-and-auto-rollback",
    "P35.59": "dark-cutover-to-release-layout",
    "P35.60": "release-classifier-standing-go-readout",
    "P35.61": "round10-live-pass-audit-apply-freeze",
    "P35.62": "round10-production-candidate",
    "PLAN-11C": "contracts-for-11c-and-k13-families",
    "P35.63": "first-model-release-to-production",
    "P35.64": "sub-round-11b-acceptance",
    "GATE-G5": "11b-check-in",
    "P37.1": "osm-camera-site-origin",
    "P37.2": "wave-c-osm-national-alpr-layer",
    "P35.2": "alerting-as-code-and-escalation",
    "P35.21": "partner-name-audit-run",
    "P35.23": "real-data-regression-corpus",
    "P36.1b": "crawler-conduct-text-and-robots-field",
    "P36.2": "rights-flip-decline-batch-and-terms-capture",
    "P36.76": "axon-connect-connector",
    "P36.77": "documentcloud-muckrock-connector",
    "P36.78": "sourcewell-omnia-contract-pages",
    "P36.13": "api-rate-limits",
    "P36.14": "inference-l4-marker",
    "P36.16": "design-tokens-v2",
    "P36.17": "lexicon-and-copy-system",
    "P36.18": "layout-and-chrome",
    "P36.19": "csp-hsts-permissions-policy",
    "P36.20": "enhancement-kit-behaviour",
    "P36.21": "workspace-state-cite-this-view-facets",
    "P36.22": "component-kit-a",
    "P36.23": "component-kit-b",
    "P36.24": "copy-lints-in-ci",
    "P36.25": "brand",
    "P36.26": "print-v2",
    "P36.27": "static-figure-kit-geography",
    "P36.28": "static-figure-kit-graphs-charts-legends",
    "P36.29": "entity-url-keys-and-slug-history",
    "P36.30": "procurement-relevance-rule",
    "P36.79": "held-out-search-relevance-set",
    "P36.31": "search-index-v2-builder",
    "P36.32": "query-engine-v2-and-benchmark",
    "P36.33": "basemap-pipeline-and-host",
    "P36.34": "grouped-dossier-index-and-navigation",
    "P36.35": "migration-and-redirect-generator",
    "P36.36": "no-js-map-baseline-and-site-lists",
    "P36.37": "map-app-shell",
    "P36.38": "search-api-serving-v2",
    "P36.39": "no-js-search-results-page",
    "P36.40": "typeahead-header-element-search-rewrite",
    "P36.41": "entity-data-contract-a",
    "P36.42a": "entity-pages-a-template-and-organizations-hub",
    "P36.42b": "entity-pages-a-ego-timeline-map-print",
    "P36.75": "flock-share-lists-configured-access",
    "P36.43": "status-lane",
    "P36.44": "release-cadence-automation",
    "P36.45": "registry-publish-matrix",
    "P36.46": "execution-keyed-ingestion-history",
    "P36.47": "source-page-a",
    "P36.48": "sources-table",
    "P36.49": "known-issues-and-issues-log",
    "P36.50": "downloads-center",
    "P36.51": "evidence-anchors-and-view-original",
    "P36.52": "dossier-sources-explorer",
    "P36.53": "per-dossier-downloads",
    "P36.54": "dossier-map-and-locator-figures",
    "P36.55": "dossier-template-v2",
    "P36.56": "scoped-search-forms",
    "P36.57": "explore-bar-and-scoped-search",
    "P36.58": "task-export-v2",
    "P36.59": "watch-pages-and-item-pages",
    "P36.60": "evidence-hub-and-artifact-pages",
    "P36.61": "queue-hub-facets-cards",
    "P36.62": "task-and-campaign-pages",
    "P36.63": "records-request-drafts",
    "P36.64": "home-about-how-it-works-methodology",
    "P36.65": "onboarding-content",
    "P36.66a": "withbase-sweep",
    "P36.66b": "site-snapshots-and-edge-selectors",
    "P36.67": "changelog-record-id-diffs-changes-api",
    "P36.68": "per-source-extracts-and-version-index",
    "P36.69": "source-page-b",
    "P36.71": "search-acceptance-and-activation",
    "P36.72a": "core-surfaces-crawl-parity-number-truth",
    "P36.72b": "core-surfaces-walkthroughs-and-promotion",
    "P36.70": "second-release-acceptance",
    "PLAN-11D": "contracts-for-11d-and-tail",
    "P36.73": "sub-round-11c-acceptance",
    "GATE-G6": "11c-check-in",
    "P37.3": "evidence-store-hardening",
    "P37.4a": "security-baseline-scan-sbom-signing",
    "P37.4b": "security-baseline-restricted-access-audit-logs",
    "P37.5a": "ingestion-hardening-unwired-function-scan",
    "P37.5b": "manual-acquisition-and-disappearance-events",
    "P37.6": "registry-rights-record-hygiene",
    "P37.7": "public-editorial-decision-log",
    "P37.8": "legal-demand-posture-and-counts",
    "P37.71": "single-operator-deletion-and-purge-function",
    "P37.9": "lifecycle-into-dossier-timeline",
    "P37.10": "asset-promotion-gate",
    "P37.11": "sam-gov-sweep-resume",
    "P37.12": "keyed-us-511-wiring",
    "P37.70": "keyed-au-traffic-camera-apis",
    "P37.13": "registry-completeness-and-discovery-sweep",
    "P37.14": "statute-seeded-records-leads",
    "P37.15": "scheduled-parser-canary",
    "P37.16a": "dossier-live-captures-first-two-families",
    "P37.16b": "dossier-live-captures-last-two-families",
    "P37.17": "tile-properties-v2-and-map-dictionary",
    "P37.18": "map-filters-in-view-list-keyboard",
    "P37.72": "my-location-map-pan-control",
    "P37.19": "map-place-search",
    "P37.20": "release-pinned-bbox-api",
    "P37.21": "access-closures-and-degree-only-facts",
    "P37.22": "entity-data-contract-b",
    "P37.23": "entity-pages-b",
    "P37.24": "overview-builder-a",
    "P37.25": "overview-builder-b",
    "P37.26": "graph-explorer-a",
    "P37.27": "graph-explorer-b",
    "P37.28": "dossier-network-figures",
    "P37.29": "in-place-map-on-dossiers",
    "P37.30": "evidence-recommender-repair",
    "P37.31": "dated-decision-predicates",
    "P37.32": "contract-expiring-detector",
    "P37.33": "watch-lane-and-cadence",
    "P37.34": "watch-feeds-v2",
    "P37.35": "detector-routing-and-mapping-campaigns",
    "P37.36": "raw-archive",
    "P37.37": "claim-viewer-v2-and-capture-diff",
    "P37.38": "disagreements-browser",
    "P37.39": "quality-basis-on-ux-surfaces",
    "P37.40": "changes-page-and-feeds",
    "P37.41": "source-changelog",
    "P37.42": "api-parity",
    "P37.43": "search-result-export",
    "P37.44": "mechanical-evaluation-report",
    "P37.45": "public-quality-page-and-basis-fields",
    "P37.46a": "organisation-crosswalk-intake",
    "P37.46b": "organisation-cascade-materializer",
    "P37.47": "tier-2-reuse-wave",
    "P37.48": "aggregate-lanes",
    "P37.49": "federal-datasets-family",
    "P37.50": "agenda-platforms-v2",
    "P37.51": "puerto-rico-sutra-ocpr",
    "P37.52": "document-list-pages",
    "P37.53": "programme-level-lane",
    "P37.69a": "international-open-data-portals",
    "P37.69b": "ogc-wfs-family",
    "P37.54": "wave-d-activation",
    "P37.55": "archival-deposits",
    "P37.56": "wacz-capture-html-sources",
    "P37.57a": "projection-rebuild-ci-layer-direction-test",
    "P37.57b": "whole-graph-audits",
    "P37.58": "schema-conformance-generated-vs-deployed",
    "P37.59": "intake-operation-dark",
    "P37.60": "visual-regression-and-operator-gallery",
    "P37.61": "t1-table-and-filter-enhancements",
    "P37.62": "contribution-path-wiring",
    "P37.63": "map-acceptance-and-republish",
    "P37.64": "entity-graph-dossier-figure-acceptance",
    "P37.65a": "final-release-cut-crawl-scrub-audit",
    "P37.65b": "final-readout-and-promotion",
    "P37.66": "coverage-outcome-and-acquisition-closeout",
    "P37.67": "stream-l-re-measure",
    "P37.68a": "ux-capstone-advocate-journeys",
    "P37.68b": "ux-capstone-journalist-journeys",
    "P37.68c": "ux-capstone-organizer-journeys",
    "P37.68d": "ux-capstone-per-ask-checks-and-walkthrough-packet",
    "P38.1a": "round11-gap-analysis-11a-11b",
    "P38.1b": "round11-gap-analysis-11c-11d-and-composed-verification",
    "P38.2": "round11-gap-closure-and-acceptance-packet",
    "GATE-ACCEPT-R11": "round11-acceptance",
    "P38.3a": "round11-backlog-and-operational-readiness",
    "P38.3b": "round11-spec-reconciliation",
    "P38.3c": "round11-integration-plan",
    "P38.4": "round11-docs-refresh",
    "P38.5": "announce-readiness-review",
    "GATE-ANNOUNCE": "announce-decision",
}

# Stage-B carry items (PD/stageB/CARRY.md) and agent decisions that land in a specific skeleton. Each is a header bullet
# in the skeleton and a note in the contract map.
CARRY = {
    "P34.8": [
        "CF-03 (T2-α): the token-transition queue is `docs/build/reports/memory-repair/pending_transitions.csv` (columns "
        "are SEED-04's design, labelled); this row's obligation-event repair drains it.",
        "β: the wrong dates in `docs/build/reports/obligations/MIGRATION.md` L55–57 are corrected here by an appended, "
        "dated correction (ADR-146), never by rewriting the lines.",
    ],
    "P34.16": [
        "SEED-11b / TS-09: a past 'counsel' determination is written as **the operator's own determination (no counsel)** "
        "(ADR-167; OM-08) — not 'operator-reported' as catalog R11-GOV-01 words it.",
        "SEED-11b / WV-01 vs C-5: the legal-home disclosure (ADR-165) must not name or describe the operator beyond the "
        "adopted WV-01 sentence, and never as a 'who runs SIG' placeholder, until the operator writes that text (C-5 "
        "'Omit until I write it', 2026-10-01T04:56:11Z); wording confirmed verbatim in a copy batch (B-2).",
    ],
    "P34.17": [
        "SEED-11b / WV-01 vs C-5: the site's legal-home disclosure (ADR-165 §2) names no person and is not a 'who runs "
        "SIG' section (C-5 'Omit until I write it', 2026-10-01T04:56:11Z); its exact wording and placement are confirmed "
        "verbatim in copy batch #1 (B-2). Agent reading (labelled, ADR-165): a terms-page sentence satisfies WV-01.",
    ],
    "P36.64": [
        "C-5 (2026-10-01T04:56:11Z) 'Omit until I write it': no 'who runs SIG' section or placeholder ships until the "
        "operator writes it; the WV-01 legal-home disclosure stays where copy batch #1 placed it (ADR-165).",
    ],
    "P34.22a": [
        "β: parametrise the `p-17b713` release pin in `release_publish_verify.py` (the `p-17b713` supersession record, "
        "SEED-08; B-4).",
    ],
    "P35.34": [
        "SEED-12b: SIG-INGEST-004's binding-level-version amendment was withheld (it weakens a MUST, G.7.5); the MUST "
        "stands — this row adds the versions to the logical identity or records the gap as owed (DEFERRALS row).",
    ],
    "P35.14a": [
        "SEED-12b (agent assignment at T3, labelled): SIG-ONTO-060's scope list was not amended (G.7.5); this row reads "
        "the realised enum and writes the amendment proposal (operator words needed if it relaxes the closed list).",
    ],
    "P36.2": [
        "Folded here at T3 (carry SEED-11c; Q-E2-13 option c, adopted via A-4 'Adopt disclosed posture (Recommended)', "
        "2026-10-01T04:03:25Z; ADR-169 'Not decided here'): **re-decide the out-of-rule and counsel-flagged rights rows** "
        "— `camreg_und_001`, `camreg_calgary_ab`, `camreg_lexington_ky` (indemnify-and-defend terms) and the Maryland iMAP "
        "terms rows (`dot_511_md`, whose notes name the iMAP terms, and its open-data mirror `camreg_md_opendata`; "
        "agent identification from `sources.toml`, labelled) — under ADR-169's guardrails: capture terms verbatim, write one E4-style line per source, and put an HG-03 "
        "line to the operator for each (keep under the operator-accepted basis, or decline); the operator executes any "
        "flip (OP-26); lines ride the GATE-G6 packet at the latest (S6R-28). Until then the rows stay published under "
        "ADR-169's withdrawal-on-objection guardrail. PLAN-11C splits this row at its sizing review if it no longer "
        "fits (plan §8.5 already watches P36.2).",
    ],
    "P36.77": [
        "SEED-12b: outreach obligations SIG-CHART-033, SIG-INGEST-029/030a and SIG-CONTRIB-012 stay owed later-phase "
        "(ADR-171; trigger LATER-04); this connector leaves them unmet and they are listed on the GATE-ANNOUNCE unmet "
        "list.",
    ],
    "GATE-ANNOUNCE": [
        "SEED-12b: list SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012 (outreach, owed later-phase, ADR-171) on the "
        "'spec MUSTs unmet at launch' list.",
        "Waits for REVIEW-R11 (the closing Claude Code review; not a chain row): answered only when each REVIEW-R11 "
        "S0/S1 finding is fixed or dispositioned by the operator (S6-F3, 2026-10-01T06:05:22Z).",
        "Re-anchoring rule (plan §8.3, S6R-19): REVIEW-R11 fix rows are appended after row 510 by `decompose-spec "
        "mode=extend`, then a new GATE-ANNOUNCE row after the last of them; this row then receives the appended token "
        "`superseded-by(row <n>)`.",
    ],
    "PLAN-11B": [
        "SEED-12a: append the SIG-TRANSP family to spec §56.8's plan and register its prefix in §0.3 (append-only "
        "`spec_src` change, rebuilt by BUILD.sh).",
        "SEED-12a owners to re-confirm when writing the 11B contracts (T3 confirmed them at skeleton level): "
        "SIG-SEC-008 → P35.1a/b, SIG-SEC-009 → P35.4, SIG-CONF-010 → P35.60.",
        "Plan §8.1 re-split rule: four 11B rows already look oversized (P35.1b, P35.61, P35.63, P36.12); if the "
        "sizing review pushes 11B past 85 engineering rows or 75 runs, add GATE-G4b at the Wave-B activation boundary "
        "(after row 290, where the manifest already has a banner boundary) by `decompose-spec mode=extend`.",
    ],
    "PLAN-11C": [
        "SEED-12a: append the K13 UX families (or fold them into SIG-UI) and register any new prefix in §0.3.",
        "SEED-12a owner to re-confirm: SIG-OPS-007 → P35.2 (T3 confirmed it at skeleton level).",
        "P36.2 now also carries the out-of-rule rights re-decision (T3 fold; see its skeleton) — size it at the "
        "Phase-4 review.",
    ],
}

# Scope additions decided at T3 (appended to the one-line scope; recorded in the contract map).
SCOPE_ADD = {
    "P36.2": " + re-decision of the out-of-rule and counsel-flagged rights rows under ADR-169's guardrails (T3 fold; "
             "HG-03 lines to the operator)",
}

# Requirement ids a carry item adds to a skeleton's REQ coverage (cited, not owned).
CARRY_IDS = {
    "P36.2": ["SIG-LIC-004", "SIG-LIC-009"],
    "P34.16": ["SIG-GOV-012", "SIG-GOV-013"],
    "P34.17": ["SIG-GOV-012", "SIG-GOV-013"],
    "P36.77": ["SIG-CHART-033", "SIG-INGEST-029", "SIG-INGEST-030a", "SIG-CONTRIB-012"],
    "GATE-ANNOUNCE": ["SIG-CHART-033", "SIG-INGEST-029", "SIG-INGEST-030a", "SIG-CONTRIB-012"],
    "P35.14a": ["SIG-ONTO-060"],
}

SKELETON_AUTHOR_11A = [(201, 220, "SEED-13b"), (221, 240, "SEED-13c"), (241, 260, "SEED-13d")]

ID_RE_TOKEN = re.compile(r"\b(SIG-[A-Z]+-[0-9]{3}[a-z]?(?:/[0-9]{3}[a-z]?|/[a-z]\b)*)")
SPEC_ID = re.compile(r"SIG-[A-Z]+-[0-9]{3}[a-z]?")
WRONG_ID = {"SIG-CONTRIB-030a": "SIG-INGEST-030a"}  # plan §6.3 typo (carry SEED-11c; spec G.7 R11-A15)
DRAFT_RE = re.compile(r"\b(DRAFT-(?:MEM|ENG|OPS)-[0-9]+|SIG-REL-D[0-9]{2}|SIG-CONF-D[0-9]{2})\b")
LATER_DRAFT_RE = re.compile(r"\b(SIG-TRANSP-D[0-9]{2}(?:[-–…]+D?[0-9]{2})?|UXR-A?[0-9]{2}|SIG-(?:UI|SRCH|JUR|DSRC|WATCH|EVUI|RQ|EXPORT|GEO)-D[A-Z]*[0-9]{2})\b")


def read_csv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load() -> dict:
    rows = read_csv(PLAN_CSV)
    chain = [r for r in rows if r["sub_round"] in CHAIN_SUBS]
    cat = {c["cat_id"]: c for c in read_csv(CAT_CSV)}
    idmap = {}
    for m in read_csv(IDMAP_CSV):
        fin = m["final_id"].strip()
        if SPEC_ID.fullmatch(fin):
            idmap[m["draft_id"].split(" ")[0].strip()] = fin
    # spec ids -> section; §56 owner/also
    sec_of: dict[str, str] = {}
    owner: dict[str, str] = {}
    also: dict[str, list[str]] = {}
    for f in sorted(SPEC_SRC.glob("*.md")):
        cur = ""
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            h = re.match(r"^#{2,4}\s+(?:Appendix\s+)?([0-9]+[A-Za-z]?(?:\.[0-9]+[a-z]?)*|[A-G](?:\.[0-9]+)*)\.?\s", line)
            if h:
                cur = h.group(1)
            ap = re.match(r"^#\s+Appendix\s+([A-G])\b", line)
            if ap:
                cur = ap.group(1)
            for m in re.finditer(r"\*\*(SIG-[A-Z]+-[0-9]{3}[a-z]?)\b", line):
                sec_of.setdefault(m.group(1), cur)
            if f.name.startswith("96c_"):
                d = re.match(r"^\*\*(SIG-[A-Z]+-[0-9]{3}[a-z]?) \(", line)
                if d:
                    rid = d.group(1)
                    o = re.search(r"Owner: (.+?)\.(?:\s|$)", line)
                    a = re.search(r"Also: (.+?)\.(?:\s|$)", line)
                    if o:
                        owner[rid] = o.group(1)
                    if a:
                        also[rid] = a.group(1)
    for f in sorted(SPEC_SRC.glob("*.md")):  # ids referenced but defined in a table or plain text
        for m in SPEC_ID.finditer(f.read_text(encoding="utf-8")):
            sec_of.setdefault(m.group(0), "")
    return {"rows": rows, "chain": chain, "cat": cat, "idmap": idmap, "sec_of": sec_of, "owner": owner, "also": also}


def expand_owner_ids(text: str) -> list[str]:
    """'P35.1a/b (x)' -> ['P35.1a','P35.1b']; 'P34.47 and P38.1a/b' -> [...]"""
    out: list[str] = []
    for m in re.finditer(r"\b((?:P[0-9]{2}\.[0-9]+|SEED-[0-9]{2}|PLAN-11[BCD]))([a-z])?((?:/[a-z])*)", text):
        base, first, rest = m.group(1), m.group(2) or "", m.group(3) or ""
        out.append(base + first)
        for s in re.findall(r"/([a-z])", rest):
            out.append(base + s)
    return out


def expand_ids(text: str) -> list[str]:
    out: list[str] = []
    for m in ID_RE_TOKEN.finditer(text):
        tok = m.group(1)
        parts = tok.split("/")
        head = parts[0]
        fam = head.rsplit("-", 1)[0]
        num = re.match(r"([0-9]{3})", head.rsplit("-", 1)[1]).group(1)
        out.append(head)
        for p in parts[1:]:
            if re.fullmatch(r"[0-9]{3}[a-z]?", p):
                out.append(f"{fam}-{p}")
            elif re.fullmatch(r"[a-z]", p):
                out.append(f"{fam}-{num}{p}")
    # bare family-NNN forms used in the plan (PUB-007, INGEST-025a/b/c, RECON-039/040)
    fams = "CHART|EPIS|IDENT|ONTO|STORE|EVID|GEO|INGEST|RECON|METRIC|TRUST|FIND|DOS|ACQ|EXPORT|UI|LIC|PUB|SEC|GOV|ENG|EVAL|MEM|OPS|REL|CONF|TEMP|ENT|REL|VOC|ANALYTICS|PROV|CONTRIB|RES|RQ|API"
    for m in re.finditer(rf"(?<![A-Z-])({fams})-([0-9]{{3}}[a-z]?)((?:/[0-9]{{3}}[a-z]?|/[a-z]\b)*)", text):
        fam, head, rest = m.group(1), m.group(2), m.group(3) or ""
        out.append(f"SIG-{fam}-{head}")
        num = head[:3]
        for p in rest.split("/")[1:]:
            if re.fullmatch(r"[0-9]{3}[a-z]?", p):
                out.append(f"SIG-{fam}-{p}")
            elif re.fullmatch(r"[a-z]", p):
                out.append(f"SIG-{fam}-{num}{p}")
    return [WRONG_ID.get(x, x) for x in out]


def req_ids(D: dict, r: dict) -> dict[str, list[str]]:
    rid = r["id"]
    own = sorted([k for k, v in D["owner"].items() if rid in expand_owner_ids(v)], key=idkey)
    als = sorted([k for k, v in D["also"].items() if rid in expand_owner_ids(v)], key=idkey)
    c = D["cat"].get(r["cat_ids"].strip(), {})
    text = " ".join([r["title"], r["notes"], r["operator_gate"], r["live_stage"], r["window_constraints"],
                     c.get("title", ""), c.get("scope", ""), c.get("acceptance_sketch", ""), c.get("operator_gate", "")])
    cited = set(expand_ids(text)) | set(CARRY_IDS.get(rid, []))
    drafts = []
    for m in DRAFT_RE.finditer(text):
        fin = D["idmap"].get(m.group(1))
        if fin:
            cited.add(fin)
        else:
            drafts.append(m.group(1))
    later = sorted(set(m.group(1) for m in LATER_DRAFT_RE.finditer(text)))
    unknown = sorted(x for x in cited if x not in D["sec_of"])
    cited = sorted((x for x in cited if x in D["sec_of"] and x not in own and x not in als), key=idkey)
    return {"owner": own, "also": als, "cited": cited, "later": later, "unknown": unknown, "unmapped": drafts}


def idkey(x: str):
    m = re.match(r"SIG-([A-Z]+)-([0-9]{3})([a-z]?)", x)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (x, 0, "")


def slug(r: dict) -> str:
    if r["id"] in SLUG:
        return SLUG[r["id"]]
    t = re.sub(r"\(.*?\)", " ", r["title"].split(" — ")[0])
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return "-".join(t.split("-")[:6])


def fname(r: dict) -> str:
    return f"{int(r['row'])}_{r['id']}__{slug(r)}.md"


def runs(x: str) -> str:
    try:
        return f"{float(x):.1f}"
    except ValueError:
        return x or "—"


def deps(r: dict) -> list[str]:
    return [t.strip() for t in r["depends_on"].split(";") if t.strip()]


def author(r: dict) -> tuple[str, str]:
    """(who completes this skeleton, the banner sentence)"""
    n = int(r["row"])
    s = r["sub_round"]
    if s == "11A":
        who = next(a for lo, hi, a in SKELETON_AUTHOR_11A if lo <= n <= hi)
        return who, (f"the full contract is written by Stage-B unit **{who}** (plan Appendix A T3: full contracts for the "
                     "60 11A rows, token-counted against the 256k window) before GATE-B")
    if s == "11B":
        return "PLAN-11B (row 239)", ("the body is written by **PLAN-11B** (row 239, `decompose-spec mode=extend` "
                                      "against `data/round11_plan.csv`) before row 261 is dispatched")
    if s == "11C":
        return "PLAN-11C (row 340)", ("the body is written by **PLAN-11C** (row 340, `decompose-spec mode=extend`) "
                                      "before row 344 is dispatched")
    return "PLAN-11D (row 418)", ("the body is written by **PLAN-11D** (row 418, `decompose-spec mode=extend`; 11D "
                                  "and tail contracts) before row 421 is dispatched")


def answers(g: str) -> list[str]:
    toks = re.findall(r"\b(A-[0-9]+[a-z]?|B-[0-9]+|C-[0-9]+|S5-[0-9]|S6-F[0-9]|S6R-[0-9]+|SB-[0-9]|WV-[0-9]+|D2-[0-9]+)\b", g)
    seen: list[str] = []
    for t in toks:
        if t not in seen:
            seen.append(t)
    return seen


def om20(r: dict) -> str:
    g = r["operator_gate"]
    if r["kind"] == "gate":
        return "not an OM-20 row (gate marker)"
    if "OM-20 PRE-AUTHORISED" in g:
        return ("pre-authorised — on the 11A list the operator approved verbatim at GATE-P (S5-3, 2026-10-01T04:28:49Z); "
                "expires: GATE-G4; voided-by: a red probe, a failed restore point or a production read that contradicts "
                "a record")
    if "not on the 11A OM-20 list" in g:
        return "named mutation not on the 11A OM-20 list (S5-3): in-ticket verbatim go"
    m = re.search(r"OM-20: pre-authorised only if the (GATE-G[0-9])", g)
    if m:
        return (f"OM-20 row: pre-authorised only if the {m.group(1)} list the operator approves verbatim names this row "
                "(expiry at the next GATE); otherwise an in-ticket pause")
    if "never pre-authorised" in g or "IN-TICKET PAUSE" in g:
        return "never pre-authorised (in-ticket go or pause; see Gate status)"
    return "not an OM-20 row"


def gate_cell(r: dict) -> str:
    g = r["operator_gate"]
    k = r["kind"]
    if k == "gate":
        s = "operator check-in (S5-2 packet): verbatim lines; silence = pause (OM-18); never guessed past"
        if r["id"] == "GATE-ANNOUNCE":
            s += "; waits for REVIEW-R11's S0/S1 findings to be fixed or dispositioned (S6-F3)"
        if r["id"] == "GATE-ACCEPT-R11":
            s = "operator signs the accepted-deviations list verbatim; never guessed past"
        return s
    if g.strip() == "none":
        return "none"
    if g.startswith("none ("):
        return g
    parts: list[str] = []
    if "OM-20 PRE-AUTHORISED" in g:
        parts.append("OM-20 pre-authorised (S5-3; expires GATE-G4)")
    if "not on the 11A OM-20 list" in g:
        parts.append("in-ticket verbatim go (not on the S5-3 list)")
    m = re.search(r"OM-20: pre-authorised only if the (GATE-G[0-9])", g)
    if m:
        parts.append(f"OM-20 if the {m.group(1)} list names it, else in-ticket pause")
    for seg in g.split(" · "):
        if ("IN-TICKET PAUSE" not in seg or "NOT pre-authorised = IN-TICKET PAUSE" in seg or "not on the 11A" in seg
                or "ING-GO-" in seg):
            continue
        if re.search(r"\bif\b.*IN-TICKET PAUSE", seg) and not seg.startswith("IN-TICKET"):
            parts.append("conditional in-ticket pause")
            continue
        rest = seg.split("IN-TICKET PAUSE", 1)[1].lstrip(" :")
        if rest.startswith("("):  # balanced parenthesis
            depth, end = 0, len(rest)
            for i, ch in enumerate(rest):
                depth += {"(": 1, ")": -1}.get(ch, 0)
                if depth == 0:
                    end = i
                    break
            why = rest[1:end]
            if not re.sub(r"^never pre-authori[sz]ed(?: under OM-20)?:?\s*", "", why.strip()):
                why = re.split(r"[;(]", rest[end + 1 :].lstrip(" :"), maxsplit=1)[0]
        else:
            why = re.split(r"[;(]", rest, maxsplit=1)[0]
        why = re.sub(r"^never pre-authori[sz]ed(?: under OM-20)?:?\s*", "", why.strip()).rstrip(" ,.")
        parts.append("in-ticket pause, never pre-authorised" + (f" ({why[:100]})" if why else ""))
    gos = sorted(set(re.findall(r"\bING-GO-[A-D]\b", g)))
    for go in gos:
        parts.append(f"{go} verbatim at the GATE, else in-ticket pause")
    if re.search(r"\bHG-03\b|\bOP-26\b", g):
        parts.append("HG-03 lines executed by the operator (OP-26)")
    if "copy batch" in g or "confirmed verbatim" in g:
        parts.append("copy confirmed verbatim (B-2)")
    if not parts:
        short = g.strip()
        parts.append(short if len(short) <= 70 and not SKIP_RE.search(short) and not answers(short)
                     else "GATE-P answers recorded; no pause")
    a = answers(g)
    if a:
        parts.append("answers: " + ", ".join(a))
    out = " · ".join(dict.fromkeys(parts))
    return out


def scope_cell(r: dict) -> str:
    t = re.sub(rf"^{re.escape(r['id'])}(?: —|:)\s*", "", r["title"])
    if r["id"] == "P34.32":  # the title's word trips the validator's skip rule; same meaning
        t = t.replace("superseded status", "supersession status lines")
    d = deps(r)
    lead = {"gate": f"**[marker `{r['id']}`]**", "plan": "**[PLAN]**"}.get(r["kind"], f"**{r['sub_round']}**")
    s = f"{lead} — {t}"
    s += f"; depends {', '.join(d)}" if d else "; depends nothing (chain order)"
    s += f"; {runs(r['est_runs'])} run" + ("" if runs(r["est_runs"]) in ("0.5", "1.0", "0.0") else "s")
    if r["live_legs"].strip():
        s += f"; live legs: {r['live_legs'].strip()}"
    return s.replace("|", "\\|")


def manifest_block(D: dict) -> str:
    chain = D["chain"]
    by_row = {int(r["row"]): r for r in chain}
    out: list[str] = []
    for lo, hi, name, part in BANNERS:
        out.append(f"### Round 11 — {name} · {part}")
        out.append("")
        out.append("| # | Ticket file | Phase | Kind | Lane | Scope | Gate |")
        out.append("|---|---|---|---|---|---|---|")
        for n in range(lo, hi + 1):
            r = by_row[n]
            lane = "A" if r["kind"] == "gate" else "C"
            out.append(f"| {n} | `{fname(r)}` | {r['phase'][1:]} | {r['kind']} | {lane} | {scope_cell(r)} | "
                       f"{gate_cell(r).replace('|', chr(92) + '|')} |")
        out.append("")
    return "\n".join(out)


def spec_sections(D: dict, ids: list[str]) -> list[str]:
    secs: dict[str, list[str]] = {}
    for i in ids:
        s = D["sec_of"].get(i, "")
        secs.setdefault(s or "?", []).append(i)
    def k(s: str):
        return [int(x) if x.isdigit() else x for x in re.split(r"[.]", re.sub(r"[a-z]$", "", s))] if s != "?" else [999]
    out = []
    for s in sorted(secs, key=lambda x: (k(x) if all(p.isdigit() for p in re.sub(r'[a-z]', '', x).split('.') if p) else [998], x)):
        label = f"§{s}" if s and s != "?" and s[0].isdigit() else (f"Appendix {s}" if s != "?" else "(section not resolved)")
        out.append(f"- {label} — {', '.join(secs[s])}")
    return out


def skeleton(D: dict, r: dict, date: str) -> str:
    n = int(r["row"])
    who, banner = author(r)
    c = D["cat"].get(r["cat_ids"].strip(), {})
    theme = c.get("theme", "")
    home = THEME_SECTION.get(theme, NEW_ROW_HOME.get(r["id"], "§8"))
    rq = req_ids(D, r)
    d = deps(r)
    L: list[str] = []
    L.append(f"<!-- Kind: skeleton. Generated {date} by {PD_REL}/tools/s13/gen_t3.py (SEED-13a, Round-11 Stage B T3) "
             f"from data/round11_plan.csv row {n}; planning is not execution evidence. -->")
    title = re.sub(rf"^{re.escape(r['id'])}(?: —|:)\s*", "", r["title"])
    L.append(f"# {r['id']} — {title}")
    L.append("")
    L.append(f"- **Sequence:** {n} of {TOTAL} · **Phase:** Round 11 / {r['phase']} (sub-round {r['sub_round']}) · "
             "**Kind:** skeleton")
    L.append(f"- **Row kind (manifest):** {r['kind']}")
    L.append(f"- **Harness:** {HARNESS}")
    L.append("- **base_branch:** current checkout")
    L.append(f"- **Depends on:** {', '.join(d) if d else 'nothing (chain order)'}")
    L.append(f"- **Gate status (GATE-P answer as recorded in the plan row):** {r['operator_gate'] or 'none'}")
    L.append(f"- **OM-20 status:** {om20(r)}")
    L.append(f"- **Live stage:** {r['live_stage'] or 'none'}")
    L.append(f"- **Live window (plan `window_constraints`):** {r['window_constraints'] or 'none'}")
    L.append(f"- **Live legs:** {r['live_legs'].strip() or 'none'} (leg runs: {r['leg_runs'] or '0'})")
    L.append(f"- **Est. runs:** {runs(r['est_runs'])}")
    L.append(f"- **Completed by:** {who}")
    cat_line = r["cat_ids"].strip()
    L.append(f"- **Catalog:** {cat_line}" + (f" · theme {theme}" if theme else "") + f" · plan {home}")
    if c.get("source_refs"):
        L.append(f"- **Plan inputs (catalog source_refs; paths under `{PD_REL}/`):** {c['source_refs']}")
    if c.get("acceptance_sketch"):
        L.append(f"- **Acceptance sketch (catalog):** {c['acceptance_sketch']}")
    L.append(f"- **Plan row notes:** `{PD_REL}/data/round11_plan.csv` row {n} (`notes` column)")
    for note in CARRY.get(r["id"], []):
        L.append(f"- **Carried in at T3:** {note}")
    L.append("")
    L.append(f"> Skeleton only — {banner}. Do not implement this file until then; it carries no run line. "
             "The rewrite keeps this file name (the manifest row binds it).")
    if r["kind"] == "gate":
        L.append("")
        L.append("> Milestone gate — not an `implement-spec` input; never guessed past. An operator or authorized human "
                 "record supplies the decision; an agent must not sign or assume silence is approval.")
    L.append("")
    L.append("## Scope (one line)")
    L.append(r["title"] + SCOPE_ADD.get(r["id"], ""))
    L.append("")
    L.append("## Spec §§")
    allids = rq["owner"] + rq["also"] + rq["cited"]
    if allids:
        L.extend(spec_sections(D, allids))
    else:
        L.append(f"- None cited by the plan row or catalog; the contract author cites the sections (plan {home}).")
    if rq["later"]:
        L.append(f"- Draft ids not yet in the spec (appended by PLAN-11B / PLAN-11C): {', '.join(rq['later'])}")
    L.append("")
    L.append("## REQ coverage")
    if rq["owner"]:
        L.append(f"- Owner (spec §56 `Owner:`): {', '.join(rq['owner'])}")
    if rq["also"]:
        L.append(f"- Also (spec §56 `Also:`; extends the owner's work, does not own): {', '.join(rq['also'])}")
    if rq["cited"]:
        L.append(f"- Cited by the plan row / catalog / a T3 carry item (final ids per `stageB/T1_id_map.csv`): "
                 f"{', '.join(rq['cited'])}")
    if rq["later"]:
        L.append(f"- Later-family drafts (no final id yet): {', '.join(rq['later'])}")
    if not (rq["owner"] or rq["also"] or rq["cited"] or rq["later"]):
        L.append("- None named yet; the contract author maps the row's scope to requirement ids.")
    L.append("")
    return "\n".join(L)


def is_skeleton(p: pathlib.Path) -> bool:
    try:
        return bool(re.search(r"\*\*Kind:\*\*\s*skeleton", p.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return True


def cmd_skeletons(D: dict, date: str) -> int:
    wrote = kept = 0
    for r in D["chain"]:
        p = TICKETS / fname(r)
        if p.exists() and not is_skeleton(p):
            kept += 1
            continue
        p.write_text(skeleton(D, r, date), encoding="utf-8")
        wrote += 1
    print(f"skeletons: wrote {wrote}, kept {kept} non-skeleton contract(s)")
    return 0


def cmd_map(D: dict) -> int:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["row", "id", "file", "kind", "contract_kind", "sub_round", "phase", "banner", "completed_by", "est_runs",
                "om20_status", "req_owner", "req_also", "req_cited", "notes"])
    old = {r["id"]: r for r in D["rows"] if r["kind"] == "marker"}
    marker_files = {f.name.split("_", 1)[1].split("__")[0]: f.name for f in TICKETS.glob("18[4-7]_*.md")}
    for rid, tok in (("HUMAN-H4", "superseded-by(T-EVAL-IND segment: EV1, HUMAN-H6, HUMAN-H7)"),
                     ("P32.22a", "superseded-by(T-EVAL-IND segment: EV-F)"),
                     ("HUMAN-H5", "superseded-by(T-EVAL-IND segment: HUMAN-H8)"),
                     ("P32.23", "superseded-by(CONF-02 = P34.45, CONF-09 = P37.44; decision leg: T-EVAL-IND segment "
                                "EV-D, EV-R)")):
        r = old[rid]
        w.writerow([r["row"], rid, marker_files.get(rid, ""), "marker (Round 10)", "existing contract; note appended",
                    "R10 (superseded)", "P32", "Round 10 (six-stream block)", "—", "0", "not dispatched", "", "", "",
                    f"Superseded — not executed (ADR-152; L3 §6.3); gate-cell token {tok}"])
    for r in D["chain"]:
        n = int(r["row"])
        b = next(f"{name} · {part}" for lo, hi, name, part in BANNERS if lo <= n <= hi)
        rq = req_ids(D, r)
        notes = " | ".join(CARRY.get(r["id"], []))
        if rq["unknown"]:
            notes = (notes + " | " if notes else "") + "ids named in the plan text but not in the spec: " + ", ".join(rq["unknown"])
        w.writerow([n, r["id"], fname(r), r["kind"], "skeleton", r["sub_round"], r["phase"], b, author(r)[0],
                    runs(r["est_runs"]), om20(r), " ".join(rq["owner"]), " ".join(rq["also"]), " ".join(rq["cited"]),
                    notes])
    MAP_OUT.write_text(buf.getvalue(), encoding="utf-8")
    print(f"map: {MAP_OUT.relative_to(REPO)} ({len(D['chain']) + 4} rows)")
    return 0


def cmd_insert(D: dict) -> int:
    text = MANIFEST.read_text(encoding="utf-8")
    if re.search(r"^### Round 11 — ", text, re.M):
        print("insert-manifest: a '### Round 11' banner already exists; nothing inserted", file=sys.stderr)
        return 1
    anchor = "\n## Phase gates & special points\n"
    if text.count(anchor) != 1:
        print("insert-manifest: anchor not found exactly once", file=sys.stderr)
        return 1
    block = manifest_block(D)
    MANIFEST.write_text(text.replace(anchor, "\n" + block + "\n" + anchor.lstrip("\n"), 1), encoding="utf-8")
    print("insert-manifest: inserted", len(re.findall(r"^\| [0-9]{3} \|", block, re.M)), "chain rows under",
          len(BANNERS), "banners")
    return 0


def cmd_check(D: dict) -> int:
    errs: list[str] = []
    text = MANIFEST.read_text(encoding="utf-8")
    rows = []
    inchain = False
    banner = ""
    for line in text.splitlines():
        if re.match(r"^##\s+The chain", line):
            inchain = True
            continue
        if inchain and re.match(r"^##\s", line):
            inchain = False
        if inchain and line.startswith("###"):
            banner = line
            continue
        if inchain and line.startswith("|") and re.search(r"`[0-9]{3}_", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0].isdigit() and int(cells[0]) >= 201:
                rows.append((int(cells[0]), cells[1].strip("`"), banner, line))
    want = [(int(r["row"]), fname(r)) for r in D["chain"]]
    got = [(n, f) for n, f, _, _ in rows[: len(want)]]
    if got != want:
        errs.append(f"manifest rows 201-510 differ from the CSV order/files (first difference: "
                    f"{next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want)))})")
    for n, f, banner, line in rows:
        if not re.match(r"^###\s+Round\s+11\b", banner):
            errs.append(f"row {n} is not under a '### Round 11' banner")
        if SKIP_RE.search(line) and n <= 510:
            errs.append(f"row {n} matches the validator's skip words ({SKIP_RE.search(line).group(0)})")
        if not (TICKETS / f).exists():
            errs.append(f"row {n}: file {f} missing")
    for r in D["chain"]:
        p = TICKETS / fname(r)
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        if not t.splitlines()[1 if t.startswith("<!--") else 0].startswith(f"# {r['id']} — "):
            errs.append(f"{p.name}: title line does not start with '# {r['id']} — '")
        if f"**Harness:** {HARNESS}" not in t:
            errs.append(f"{p.name}: no Harness header")
        sk = is_skeleton(p)
        if sk and re.search(r"Run:.*implement-spec", t):
            errs.append(f"{p.name}: skeleton carries a run line")
    for f in TICKETS.glob("[2-5][0-9][0-9]_*.md"):
        if int(f.name.split("_")[0][:3]) >= 201 and f.name not in {fname(r) for r in D["chain"]}:
            errs.append(f"stray Round-11 file {f.name}")
    if MAP_OUT.exists():
        m = read_csv(MAP_OUT)
        mm = {x["id"]: x["file"] for x in m}
        for r in D["chain"]:
            if mm.get(r["id"]) != fname(r):
                errs.append(f"map: {r['id']} file {mm.get(r['id'])} != {fname(r)}")
    else:
        errs.append("map missing")
    # every §56 owner resolves to a chain row or a seed unit
    ids = {r["id"] for r in D["rows"]}
    for k, v in D["owner"].items():
        for o in expand_owner_ids(v):
            if o not in ids:
                errs.append(f"§56 {k}: owner {o} is not a plan row")
    for e in errs:
        print("ERROR", e)
    print(f"check: {len(rows)} Round-11 manifest rows, {len(D['chain'])} plan rows, errors {len(errs)}")
    return 1 if errs else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["skeletons", "map", "manifest-block", "insert-manifest", "check", "dump"])
    ap.add_argument("--date", default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"))
    a = ap.parse_args()
    D = load()
    if a.cmd == "skeletons":
        return cmd_skeletons(D, a.date)
    if a.cmd == "map":
        return cmd_map(D)
    if a.cmd == "manifest-block":
        print(manifest_block(D))
        return 0
    if a.cmd == "insert-manifest":
        return cmd_insert(D)
    if a.cmd == "check":
        return cmd_check(D)
    for r in D["chain"]:  # dump: one line per row for review
        rq = req_ids(D, r)
        print(r["row"], fname(r), "|", gate_cell(r), "|", "O:", " ".join(rq["owner"]), "A:", " ".join(rq["also"]),
              "C:", " ".join(rq["cited"]), "L:", " ".join(rq["later"]), "U:", " ".join(rq["unknown"]),
              "D:", " ".join(rq["unmapped"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
