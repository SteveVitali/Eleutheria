# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `ops` stage (SIG-ENG-013, P21.4, ADR-066).

`sig-ops` is the SIG **runtime composition** command: it stands the whole system
up as a service on one small machine (SIG-STORE-003, the zero-cost posture), not a
test suite. The stateful piece — the PG18+PostGIS claim spine with the real sqitch
plan deployed on start — lives in ``ops/docker-compose.yml``; the read API
(uvicorn) and the static server for ``web/dist`` are launched here as host
processes (the HG-12 local-staging default: uvicorn + a static file server), so
they run the host toolchain at HEAD without baking a platform-specific image.

Sub-commands (P21.4 deliverable 1):

* ``up --jurisdiction okc`` — bring up PG (+ sqitch deploy), then start the API and
  the static server; wait until all three answer.
* ``status`` — report PG / API / static health (exit non-zero if any is down).
* ``down`` — stop the API + static host processes and tear down the compose
  project (``down -v``), leaving **no containers** and no stray processes.
* ``seed --jurisdiction okc`` — load the Oklahoma City slice claims into the spine
  (the 299-vs-190 ``claimed_device_count`` contradiction and its neighbours),
  append-only, via ``db.claim_sink.PgClaimSink``.

Staging endpoints default to local and are overridable by env (HG-12):
``SIG_STAGING_DSN``, ``SIG_STAGING_API_URL``, ``SIG_STAGING_STATIC_URL``.

Observability & alerting sub-commands (OBS.1 / GL-OBS-01, ADR-077):

* ``egress-report --alert`` — INFRA.1's egress alarm wired to the notifier seam:
  a warn/alarm threshold breach fires a *recorded* alert (append-only ledger).
* ``keepalive-check`` — verify the dormant-scheduler keepalive (workflow intact +
  real degraded rebuild); a failure fires a recorded ``critical`` alert.
* ``probe [--alert]`` — measure the stack (ok/latency per service) into the
  bounded probe log; ``--alert`` records an alert per DOWN service.
* ``alerts`` — read the recorded-alert ledger; ``dashboard`` — render the
  markdown readout (health, uptime vs error budget, egress, keepalive, alerts).

State files live under ``.sig/ops/`` (gitignored), env-overridable:
``SIG_ALERT_LOG`` / ``SIG_PROBE_LOG``. Notifier: ``SIG_ALERT_WEBHOOK_URL`` +
``SIG_ALERT_WEBHOOK_TOKEN`` (env-only, HG-09); absent → ledger + log line only.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gcs import GcsBucket
    from .scheduled import CadenceConfig

from . import __version__
from .alerts import Alert
from .observe import ObservabilityConfig
from .observe import http_ok as _http_ok
from .observe import pg_ready as _pg_ready

#: Repo root: ops/src/ops/cli.py -> parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"
#: Gitignored runtime state (pids, ports) so a worktree's stack is self-describing.
_STATE_DIR = _REPO_ROOT / ".sig" / "ops"
_STATE_FILE = _STATE_DIR / "state.json"
_COMPOSE_PROJECT = "sig"


# --- staging endpoint defaults (HG-12: local staging is acceptable) -----------


def _pg_port() -> str:
    return os.environ.get("SIG_PG_PORT", "5432")


def default_dsn() -> str:
    user = os.environ.get("SIG_PG_USER", "sig")
    password = os.environ.get("SIG_PG_PASSWORD", "sig")
    db = os.environ.get("SIG_PG_DB", "sig")
    return os.environ.get(
        "SIG_STAGING_DSN",
        f"postgresql://{user}:{password}@127.0.0.1:{_pg_port()}/{db}",
    )


def _api_host_port() -> tuple[str, int]:
    return os.environ.get("SIG_API_HOST", "127.0.0.1"), int(os.environ.get("SIG_API_PORT", "8000"))


def default_api_url() -> str:
    host, port = _api_host_port()
    return os.environ.get("SIG_STAGING_API_URL", f"http://{host}:{port}")


def _static_host_port() -> tuple[str, int]:
    return (
        os.environ.get("SIG_STATIC_HOST", "127.0.0.1"),
        int(os.environ.get("SIG_STATIC_PORT", "4321")),
    )


def default_static_url() -> str:
    host, port = _static_host_port()
    return os.environ.get("SIG_STAGING_STATIC_URL", f"http://{host}:{port}")


def _curation_host_port() -> tuple[str, int]:
    # Bound to loopback by default: the curation surface is authenticated and MUST
    # NOT be world-reachable (P21.6, ADR-068, Part VIII §0.7, RISK-P21-10).
    return (
        os.environ.get("SIG_CURATION_HOST", "127.0.0.1"),
        int(os.environ.get("SIG_CURATION_PORT", "8001")),
    )


def default_curation_url() -> str:
    host, port = _curation_host_port()
    return os.environ.get("SIG_STAGING_CURATION_URL", f"http://{host}:{port}")


# --- parser -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `ops` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-ops",
        description="SIG runtime composition (P21.4): compose the PG spine + API + static site.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    up = sub.add_parser("up", help="bring up PG (+ sqitch deploy), the API, and the static server")
    up.add_argument("--jurisdiction", default="okc", help="jurisdiction slug (default okc)")
    up.add_argument("--seed", action="store_true", help="also seed the jurisdiction after up")
    up.add_argument(
        "--no-static",
        action="store_true",
        help="skip the static server (e.g. web/dist not built yet)",
    )

    sub.add_parser("status", help="report PG / API / static health (non-zero if any is down)")
    sub.add_parser("down", help="stop the API + static processes and tear down the compose project")

    seed = sub.add_parser("seed", help="load a jurisdiction's slice claims into the spine")
    seed.add_argument("--jurisdiction", default="okc", help="jurisdiction slug (default okc)")
    seed.add_argument("--dsn", default=None, help="PostgreSQL DSN (default: SIG_STAGING_DSN/local)")

    dpkt = sub.add_parser(
        "dossier-packet",
        help="P32.18 (SIG-DOS-003, ADR-137): emit the reviewed Oklahoma City "
        "dossier evidence set — the sig.dossier-packet/1 (fixture replay over the "
        "three dossier documents + the shadow-document + P06.1 evidence packs), "
        "the composed dossier + portfolio + print HTML, the authored "
        "sig.seed-correction-packet/1, the evidence pack, and the bounded live "
        "RETURN PASS packet (D-P32.18-1). Offline only: no fetch, no rights flip",
    )
    dpkt.add_argument(
        "--out", required=True, help="output directory for the committed artifact set"
    )

    tpkt = sub.add_parser(
        "dossier-packet-tulsa",
        help="P32.19 (SIG-DOS-004, ADR-138): emit the reviewed Tulsa dossier "
        "evidence set — the sig.dossier-packet/1 (fixture replay over the three "
        "dossier documents: TPD policies 113C/113E + the MOU template), the "
        "composed dossier + portfolio + print HTML, the drafted follow-up/"
        "request queue (drafted, never sent), the evidence pack, and the "
        "bounded live RETURN PASS packet (D-P32.19-1). Offline only: no fetch, "
        "no rights flip, no request sent",
    )
    tpkt.add_argument(
        "--out", required=True, help="output directory for the committed artifact set"
    )

    spkt = sub.add_parser(
        "dossier-packet-san-diego",
        help="P32.20 (SIG-DOS-005, ADR-139): emit the San Diego dossier "
        "evidence set — the sig.dossier-packet/1 (fixture replay over the four "
        "dossier documents: the 2025 Vigilant ASR, the Ubicquia/Flock "
        "agreement, and the technology + PAB indexes), the composed dossier + "
        "portfolio + print HTML, the drafted follow-up/request queue "
        "(drafted, never sent), the metadata-only Part VIII preflight for "
        "SRC-027, the evidence pack, and the bounded live RETURN PASS packet "
        "(D-P32.20-1). Offline only: no fetch, no rights flip, no request "
        "sent, no workbook transport",
    )
    spkt.add_argument(
        "--out", required=True, help="output directory for the committed artifact set"
    )

    seedfix = sub.add_parser(
        "seed-correct",
        help="P32.18: apply the authored OKC seed-correction packet to a spine "
        "holding the legacy (pre-P32.3) rows — §16.6 belief closure on each "
        "target + appended corrected claims carrying revises_claim + "
        "correction_reason (append-only; never deletes or mutates history)",
    )
    seedfix.add_argument("--dsn", default=None, help="PostgreSQL DSN (else SIG_STAGING_DSN/local)")
    seedfix.add_argument(
        "--packet",
        default=None,
        help="a sig.seed-correction-packet/1 JSON file (default: the authored OKC packet)",
    )
    seedfix.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve the packet's targets and report what would change — no writes",
    )

    egress = sub.add_parser(
        "egress-report",
        help="check monthly egress against the ops/config.toml budget (§38.5, RISK-P21-09)",
    )
    egress.add_argument(
        "--config", default=None, help="ops/config.toml path (default: ops/config.toml)"
    )
    egress.add_argument(
        "--usage-gb",
        type=float,
        default=None,
        help="observed monthly egress (GB); omit when no live usage API (gate pending: HG-07).",
    )
    egress.add_argument(
        "--alert",
        action="store_true",
        help="fire a RECORDED alert via the notifier seam when the threshold is breached "
        "(warn/alarm); the alert is appended to the ledger and sent to env-configured "
        "notifiers (OBS.1, ADR-077).",
    )

    swh = sub.add_parser(
        "swh-save", help="build a Software Heritage save-code-now request (SIG-GOV-022/023/024)"
    )
    swh.add_argument("--repo-url", default=None, help="the public repository origin URL to save.")
    swh.add_argument("--visit-type", default="git", help="SWH visit type (default: git).")
    swh.add_argument(
        "--now",
        action="store_true",
        help="actually submit to Software Heritage (default: print the request only, untriggered).",
    )

    degraded = sub.add_parser(
        "degraded",
        help="build the fully static site with NO API (degraded-but-alive, SIG-GOV-021)",
    )
    degraded.add_argument(
        "--data-source",
        default="fixtures",
        choices=["fixtures", "export"],
        help="fixtures (committed typed fixtures) or export (last committed export snapshot).",
    )
    degraded.add_argument("--export-dir", default=None, help="export snapshot dir (export mode).")

    deploy = sub.add_parser(
        "deploy",
        help="deploy the API image + static/exports to a hosted target (P24.1, GL-DEPLOY-01)",
    )
    deploy.add_argument(
        "--target",
        default="gcp",
        choices=["gcp"],
        help="hosted target (only 'gcp' is supported; GL-GATE-04).",
    )
    deploy.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and exit 0 without pushing (forced when no ADC is present).",
    )
    deploy.add_argument(
        "--prepare-only",
        action="store_true",
        help="build web/dist from the real national export (SIG_DATA_SOURCE=export, fail-loud "
        "if absent) + partition the bundle into exports/out/{public,restricted} + PROVE the "
        "public compartment carries no ODbL/share-alike/UNDETERMINED byte (§42). Network-free; "
        "no push. Publication runs through `sig-ops publish-web` (P34.10) — hand-typed "
        "bucket syncs are forbidden (SIG-OPS-004).",
    )
    deploy.add_argument(
        "--export-dir",
        default=None,
        help="the national export the public build reads (default: SIG_EXPORT_DIR / "
        "exports/out/national). NEVER a fixtures fall-back for the public build.",
    )

    pub = sub.add_parser(
        "publish-web",
        help="the ONE repository-owned publish path for the public surface "
        "(P34.10, SIG-OPS-003/004): assert the built tree against "
        "ops/public_routes.toml + the internal/demo markers, write "
        ".sig-release.json, run ONE sync that never deletes the release "
        "namespaces (r/, releases/, entity/, conf/), then prove the denied "
        "routes absent on every public origin. Dry-run by default; --apply "
        "performs the sync + post-sync probes. Hand-typed bucket syncs are "
        "forbidden — this command is the path.",
    )
    pub.add_argument(
        "--dist",
        default=None,
        help="the built site tree to publish (default: web/dist — built by "
        "`npm --prefix web run build`, which never emits internal routes "
        "without SIG_BUILD_INTERNAL=1).",
    )
    pub.add_argument(
        "--export-dir",
        default=None,
        help="when given, run the full prepare first: build web/dist from this "
        "real export (SIG_DATA_SOURCE=export, never fixtures) and partition it "
        "into exports/out/{public,restricted} — the public tree then publishes "
        "through this same command.",
    )
    pub.add_argument(
        "--release-tree",
        default=None,
        help="a staged release tree (e.g. <registry>/staged) to publish to the "
        "web bucket in the same run — append-only, its top-level entries must "
        "be release namespaces (r/, releases/, entity/, conf/, …).",
    )
    pub.add_argument(
        "--public-tree",
        default=None,
        help="the partitioned public compartment tree (default: "
        "exports/out/public when --export-dir ran the prepare).",
    )
    pub.add_argument(
        "--bucket",
        default=None,
        help="the site bucket (default: SIG_WEB_BUCKET, else "
        "{SIG_GCP_PROJECT}-sig-web). Required for --apply.",
    )
    pub.add_argument(
        "--public-bucket",
        default=None,
        help="the public compartment bucket for --public-tree (default: "
        "SIG_PUBLIC_BUCKET, else {SIG_GCP_PROJECT}-sig-public).",
    )
    pub.add_argument(
        "--allowlist",
        default=None,
        help="ops/public_routes.toml path (default: the committed file / SIG_PUBLIC_ROUTES).",
    )
    pub.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path — its http-absent targets are the post-sync "
        "verify (default: the packaged file / SIG_OPS_CADENCE).",
    )
    pub.add_argument(
        "--release-id",
        default=None,
        help="the publish release id written to .sig-release.json (default: web-<utc>-<commit>).",
    )
    pub.add_argument(
        "--apply",
        action="store_true",
        help="perform the sync + post-sync absence probes. Without it this is a "
        "dry-run: assertions + release record + the printed sync plan only.",
    )

    rprobe = sub.add_parser(
        "republish-probe",
        help="P34.21b: the republish-#2 pre-flight probe — emits a "
        "sig.probe-run/1 record (absence probes over the denied routes, the "
        "count-only handle crawl over the trees the republish will serve + a "
        "downloaded sig-public listing, a tile sample, and the attribution "
        "sample proving required rows carry holder + terms_url). The leg "
        "requires the record's generated_at to be no older than 24 hours; "
        "legs it cannot run are 'skipped', never fabricated. Read-only.",
    )
    rprobe.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path — its http-absent targets are the absence "
        "leg (default: the packaged file / SIG_OPS_CADENCE).",
    )
    rprobe.add_argument(
        "--export-dir",
        action="append",
        default=[],
        help="an export tree the republish will serve — handle-crawled (repeatable).",
    )
    rprobe.add_argument(
        "--tiles-dir",
        action="append",
        default=[],
        help="a tiles tree to handle-crawl (repeatable).",
    )
    rprobe.add_argument(
        "--build-dir",
        action="append",
        default=[],
        help="a built site tree to handle-crawl (repeatable).",
    )
    rprobe.add_argument(
        "--bucket-listing",
        default=None,
        help="a downloaded `gcloud storage ls` capture of sig-public — counted "
        "objects + count-only handle scan.",
    )
    rprobe.add_argument(
        "--tile-url",
        action="append",
        default=[],
        help="a tile URL to ranged-GET (repeatable; the tile sample leg).",
    )
    rprobe.add_argument(
        "--public-dir",
        default=None,
        help="the partitioned public export root — the attribution sample scans "
        "its *.jsonl rows for holder + terms_url.",
    )
    rprobe.add_argument(
        "--handle-list",
        default=None,
        help="the C3 personal-handle list (gitignored; absent → the crawl leg "
        "reports 'skipped', never a fake pass).",
    )
    rprobe.add_argument(
        "--dist",
        default=None,
        help="the built site tree — its .sig-release.json supplies the "
        "release/export identifiers in the record.",
    )
    rprobe.add_argument(
        "--out",
        default=None,
        help="write the sig.probe-run/1 record here (default: stdout).",
    )

    drill = sub.add_parser(
        "backup-drill",
        help="dump the compose PG and restore into a fresh DB, asserting the graph reproduces",
    )
    drill.add_argument(
        "--dsn", default=None, help="source PostgreSQL DSN (default: SIG_STAGING_DSN/local)"
    )
    drill.add_argument(
        "--target-db", default="sig_restore", help="fresh database name to restore into"
    )
    csdrill = sub.add_parser(
        "cloudsql-drill",
        help="P34.6: at-T append-only parity between two Cloud SQL instances "
        "(the restore drill's verification half; DSNs arrive via "
        "SIG_DRILL_DSN_SOURCE / SIG_DRILL_DSN_CLONE env, never argv)",
    )
    csdrill.add_argument("--at", required=True, help="restore point T (ISO-8601 UTC)")
    csdrill.add_argument(
        "--clone-instance",
        required=True,
        help="the drill instance name — must match sig-pg-drill(-b)?-<stamp> "
        "(sig-pg is refused outright)",
    )
    csdrill.add_argument(
        "--clone-started-at",
        default=None,
        help="when the clone op was submitted (ISO-8601 UTC; for the RTO field)",
    )
    csdrill.add_argument(
        "--out",
        default=None,
        help="write the drill record JSON here (default: stdout only)",
    )

    # --- OBS.1 / GL-OBS-01: observability & alerting (ADR-077) ------------------
    keepalive = sub.add_parser(
        "keepalive-check",
        help="verify the dormant-scheduler keepalive (workflow intact + degraded rebuild); "
        "a failure fires a RECORDED alert (SIG-GOV-021, RISK-P0-12)",
    )
    keepalive.add_argument(
        "--data-source",
        default="fixtures",
        choices=["fixtures", "export"],
        help="fixtures (committed typed fixtures) or export (last committed export snapshot).",
    )
    keepalive.add_argument("--export-dir", default=None, help="export snapshot dir (export mode).")

    probe = sub.add_parser(
        "probe",
        help="probe the live stack (PG/API/curation/static), append to the bounded "
        "metrics log, and print the results",
    )
    probe.add_argument(
        "--alert",
        action="store_true",
        help="fire a RECORDED alert for each service that is DOWN.",
    )
    probe.add_argument(
        "--config", default=None, help="ops/config.toml path (default: ops/config.toml)"
    )

    # --- P26.1 / OPS.2: scheduled live operations (probes + reingestion) ------
    hosted = sub.add_parser(
        "probe-hosted",
        help="sweep the HOSTED targets recorded in ops/cadence.toml (read API, "
        "sig-web, public export objects, Cloud SQL), append the sweep as a "
        "per-run object under gs://…-sig-restricted/ops/probes/ (WORM)",
    )
    hosted.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path (default: the packaged file / SIG_OPS_CADENCE)",
    )
    hosted.add_argument(
        "--gcs-bucket",
        default=None,
        help="bucket for the sweep object (default: SIG_OPS_GCS_BUCKET; "
        "unset = local probe log only, no upload)",
    )
    hosted.add_argument(
        "--extra-target",
        action="append",
        default=[],
        metavar="NAME=URL",
        help="probe an extra ad-hoc http target (repeatable; e.g. a "
        "deliberately-bad URL for a forced-failure drill)",
    )
    hosted.add_argument(
        "--alert",
        action="store_true",
        help="fire a RECORDED alert for each target that is DOWN (through the "
        "env-configured notifiers — the sig-alerts receiver in deployment).",
    )

    history = sub.add_parser(
        "probe-history",
        help="fold the stored sweep objects (gs://…/ops/probes/) into a "
        "per-target uptime summary: count, latest state, last-N p95",
    )
    history.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path (for the probe prefix; default packaged)",
    )
    history.add_argument(
        "--gcs-bucket",
        default=None,
        help="bucket holding the sweeps (default: SIG_OPS_GCS_BUCKET)",
    )
    history.add_argument(
        "--local",
        default=None,
        help="read a local JSONL probe log instead of GCS (offline path)",
    )
    history.add_argument(
        "--last",
        type=int,
        default=20,
        help="latency window per target for the p95 (default: last 20 probes)",
    )

    ingest = sub.add_parser(
        "scheduled-ingest",
        help="run one source live through the gated connector and append the run "
        "row (source/mode/outcome/claims/capture digests/refusal) under "
        "gs://…-sig-restricted/ops/runs/ — the scheduled-reingestion audit trail",
    )
    ingest.add_argument("--source", default=None, help="source id (live-gated)")
    ingest.add_argument(
        "--batch",
        default=None,
        help="cadence.toml [[batches]] id — runs every member source in order, "
        "appending one ops/runs row per member (P26.16 GL-GATE-07 batches)",
    )
    ingest.add_argument(
        "--sink",
        default="pg",
        choices=("memory", "pg"),
        help="claim sink (default pg — the hosted spine)",
    )
    ingest.add_argument("--dsn", default=None, help="PostgreSQL DSN for --sink pg")
    ingest.add_argument(
        "--gcs-bucket",
        default=None,
        help="bucket for the run row (default: SIG_OPS_GCS_BUCKET; unset = local mirror only)",
    )
    ingest.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path (for the runs prefix; default packaged)",
    )
    ingest.add_argument(
        "--commit-chunk-size",
        type=int,
        default=None,
        help="PG sink: claims committed per transaction (default: $SIG_COMMIT_CHUNK_SIZE "
        "else the sink default; a very-large source commits progressively) — P26.18",
    )
    ingest.add_argument(
        "--logical-run",
        default=None,
        help="P31.4: pin the logical-run (resume) key; default = the source's cadence "
        "window, <source>@<last cron fire> (a re-execution in the window resumes)",
    )
    ingest.add_argument(
        "--no-resume",
        action="store_true",
        help="P31.4: never resume (no logical-run key, no capture marks)",
    )
    ingest.add_argument(
        "--target-limit",
        type=int,
        default=None,
        help="P31.4: bound the run to its first N fetch targets (a measured slice; "
        "the completion is recorded partial)",
    )

    replay = sub.add_parser(
        "replay-ingest",
        help="P31.6 / ADR-113: the asserting replay — re-run a source's PERSISTED "
        "captures (ingest_run_capture digests resolved from the mounted OCFL "
        "capture store) through the post-capture stages and assert the new claim "
        "set as a fresh is_replay ingest_run. Never fetches: a digest absent from "
        "the store is reported missing and skipped",
    )
    replay.add_argument("--source", required=True, help="source id to replay")
    replay.add_argument(
        "--run-id",
        action="append",
        default=None,
        help="replay only these ingest_run ids' capture marks (repeatable; "
        "default: every non-replay run of the source's logical-run prefix)",
    )
    replay.add_argument(
        "--replay-key",
        default=None,
        help="the replay run's logical_run key scoping its lineage marks "
        "(default <source>@replay-p31-6)",
    )
    replay.add_argument(
        "--dsn", default=None, help="PostgreSQL DSN (else SIG_STAGING_DSN / SIG_PG_* parts)"
    )
    replay.add_argument(
        "--gcs-bucket",
        default=None,
        help="bucket for the run row (default: SIG_OPS_GCS_BUCKET; unset = local mirror only)",
    )
    replay.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path (for the runs prefix; default packaged)",
    )
    replay.add_argument(
        "--commit-chunk-size",
        type=int,
        default=None,
        help="PG sink: claims committed per transaction (default: $SIG_COMMIT_CHUNK_SIZE "
        "else the sink default)",
    )

    sink_bench = sub.add_parser(
        "sink-bench",
        help="P31.3 (ADR-110): fetch ONE green source once through the gated live "
        "connector, then time N PgClaimSink passes over its real records: claims/min and "
        "round trips per claim. Pass 1 lands any upstream change; later passes are +0 "
        "(the idempotency proof). Each pass is a real, completed ingest execution",
    )
    sink_bench.add_argument("--source", required=True, help="source id (live-gated)")
    sink_bench.add_argument("--dsn", default=None, help="PostgreSQL DSN (else SIG_PG_* parts)")
    sink_bench.add_argument("--passes", type=int, default=2, help="timed PG passes (>= 1)")
    sink_bench.add_argument("--commit-chunk-size", type=int, default=None)
    sink_bench.add_argument(
        "--code-commit", default="sink-bench", help="recorded on each pass's ingest_run"
    )

    roll = sub.add_parser(
        "roll-jobs",
        help="P31.4 (ADR-111): roll Cloud Run jobs onto an image BY PINNED DIGEST (never "
        ":latest): resolve the image, plan each job's before/after digest, mount the GCS "
        "capture store on scheduled-ingest jobs, apply with `gcloud run jobs update` (all "
        "other job settings preserved) and verify. Plan-only unless --apply",
    )
    roll.add_argument("--image", required=True, help="image ref: a SHA tag or @sha256 digest")
    roll.add_argument(
        "--job",
        action="append",
        default=[],
        help="a job to roll (repeatable); default: every cadence.toml job + the probe job",
    )
    roll.add_argument("--exclude", action="append", default=[], help="a job to leave as is")
    roll.add_argument(
        "--capture-bucket",
        default=None,
        help="mount this bucket as the capture store on scheduled-ingest jobs "
        "(default: SIG_OPS_GCS_BUCKET; pass '' to skip)",
    )
    roll.add_argument("--project", default=None, help="GCP project (default: SIG_GCP_PROJECT)")
    roll.add_argument("--region", default=None, help="region (default: SIG_GCP_REGION)")
    roll.add_argument("--cadence", default=None, help="ops/cadence.toml path")
    roll.add_argument("--record", default=None, help="write the before/after JSON record here")
    roll.add_argument("--apply", action="store_true", help="apply (default: plan only)")
    roll.add_argument(
        "--allow-unresolved-rollback",
        action="store_true",
        help="apply even when a job's current image cannot be resolved to a digest",
    )

    backfill = sub.add_parser(
        "backfill-run-completions",
        help="P31.2 (ADR-109): append ingest_run_completion rows for the WORM "
        "ops/runs rows that prove an execution finished (labelled backfilled_from; "
        "unmatched rows are reported, never guessed; a re-run is +0)",
    )
    backfill.add_argument("--dsn", default=None, help="PostgreSQL DSN (else SIG_PG_* parts)")
    backfill.add_argument(
        "--role", default=None, help="role to SET ROLE to (hosted: sig_materialize)"
    )
    backfill.add_argument(
        "--gcs-bucket",
        default=None,
        help="the restricted bucket holding ops/runs (default: SIG_OPS_GCS_BUCKET)",
    )
    backfill.add_argument(
        "--prefix", default=None, help="run-row prefix (default: cadence.toml [runs])"
    )
    backfill.add_argument("--cadence", default=None, help="ops/cadence.toml path")
    backfill.add_argument(
        "--dry-run", action="store_true", help="plan + count only; append nothing"
    )

    cadence_cmd = sub.add_parser(
        "cadence",
        help="print the resolved scheduled-ops table from ops/cadence.toml "
        "(probe sweep + per-source cadence/cron/job/scheduler)",
    )
    cadence_cmd.add_argument(
        "--cadence",
        default=None,
        help="ops/cadence.toml path (default: the packaged file / SIG_OPS_CADENCE)",
    )
    cadence_cmd.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any loadable source with live targets lacks a cadence row",
    )

    alerts = sub.add_parser(
        "alerts", help="list the recorded alerts (the append-only alert ledger)"
    )
    alerts.add_argument(
        "--config", default=None, help="ops/config.toml path (default: ops/config.toml)"
    )
    alerts.add_argument("--limit", type=int, default=0, help="show only the last N alerts")
    alerts.add_argument(
        "--prune",
        action="store_true",
        help="apply the [observability] retention policy to the ledger first.",
    )

    alert_cmd = sub.add_parser(
        "alert",
        help="record + notify an alert (used by workflow failure steps, e.g. keepalive)",
    )
    alert_cmd.add_argument("--kind", required=True, help="alert kind (e.g. keepalive)")
    alert_cmd.add_argument("--severity", default="critical", choices=["warn", "alarm", "critical"])
    alert_cmd.add_argument("--message", required=True, help="human-readable alert text")

    mdefs = sub.add_parser(
        "monitoring-defs",
        help="P34.4 (QA-3/QA-4/QA-5): the committed Cloud Monitoring alert set in "
        "ops/monitoring/*.json — list the definitions, verify them against the live "
        "project (or a --from-state capture), or render a policy body for "
        "`gcloud monitoring policies create|update --policy-from-file`",
    )
    msub = mdefs.add_subparsers(dest="monitoring_defs_command")
    mverify = msub.add_parser(
        "verify",
        help="read-only diff: OK/DRIFT/MISSING per declared resource + EXTRA for "
        "undeclared live ones; exit 1 on any non-OK (P35.3-probe shape)",
    )
    mverify.add_argument("--defs", default=None, help="definitions dir (default: ops/monitoring)")
    mvsrc = mverify.add_mutually_exclusive_group(required=True)
    mvsrc.add_argument("--live", action="store_true", help="read the live project (gcloud * list)")
    mvsrc.add_argument(
        "--from-state",
        default=None,
        help="a capture dir with channels.json + uptime-checks.json + alert-policies.json",
    )
    mverify.add_argument("--project", default=None, help="GCP project (default: SIG_GCP_PROJECT)")
    mlist = msub.add_parser("list", help="print the declared resources (offline)")
    mlist.add_argument("--defs", default=None, help="definitions dir (default: ops/monitoring)")
    mrender = msub.add_parser(
        "render",
        help="print a policy def's REST body (project substituted) — the "
        "--policy-from-file payload",
    )
    mrender.add_argument("--defs", default=None, help="definitions dir (default: ops/monitoring)")
    mrender.add_argument(
        "--slug", required=True, help="file stem, e.g. alert-policy.tls-cert-expiry"
    )
    mrender.add_argument("--project", default=None, help="GCP project (default: SIG_GCP_PROJECT)")

    dash = sub.add_parser(
        "dashboard",
        help="render the observability readout (markdown) from the recorded state",
    )
    dash.add_argument(
        "--config", default=None, help="ops/config.toml path (default: ops/config.toml)"
    )
    dash.add_argument(
        "--out", default=None, help="write the readout to this file instead of stdout"
    )
    dash.add_argument(
        "--usage-gb",
        type=float,
        default=None,
        help="observed monthly egress (GB) for the egress-budget row (omit = gate pending).",
    )
    dash.add_argument(
        "--verify-keepalive",
        action="store_true",
        help="also run the keepalive verification into the readout (runs the degraded build).",
    )

    audit = sub.add_parser(
        "evidence-audit",
        help="P32.6 (SIG-TRUST-007, ADR-125): the offline, read-only, reproducible "
        "legacy-evidence audit. Loads the spine's claim→evidence lineage through a "
        "READ-ONLY session (--dsn) or a committed input dump (--input-json), verifies "
        "recorded capture bytes at their pinned OCFL version (--capture-dir), samples "
        "deterministically by the recorded seed, and writes audit_report.json + "
        "AUDIT_REPORT.md. Never fetches, never writes the spine",
    )
    src = audit.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--dsn",
        default=None,
        help="PostgreSQL DSN; connected with default_transaction_read_only=on "
        "(else SIG_STAGING_DSN / SIG_PG_* parts)",
    )
    src.add_argument(
        "--input-json",
        default=None,
        help="a previously dumped audit input (db.evidence_audit.dump_rows shape) — "
        "the fully offline/fixture path",
    )
    audit.add_argument(
        "--capture-dir",
        default=None,
        help="the OCFL capture root to probe (mounted gcsfuse path or a fixture dir); "
        "absent → every byte check reports 'unverified', never 'missing'",
    )
    audit.add_argument("--seed", required=True, help="the sampling seed (recorded)")
    audit.add_argument(
        "--sample",
        type=int,
        default=400,
        help="probability-sample size across strata (default 400; ≥ corpus ⇒ census)",
    )
    audit.add_argument(
        "--roll-boundary",
        default=None,
        help="persistent-capture-roll timestamp (default: the 2026-09-25 roll)",
    )
    audit.add_argument(
        "--byte-budget",
        type=int,
        default=None,
        help="max capture bytes read (default: the 2 GiB pilot ceiling)",
    )
    audit.add_argument(
        "--targeted",
        default=None,
        help="file of claim ids for the separately-reported targeted set",
    )
    audit.add_argument(
        "--adjudications",
        default=None,
        help="JSON {claim_id: established|not_established|unresolved} — the "
        "adjudicator instrument's verdicts for the semantic metrics",
    )
    audit.add_argument(
        "--claim-ids",
        default=None,
        help="file of claim ids selecting a bounded population (default: the corpus)",
    )
    audit.add_argument(
        "--dump-input",
        default=None,
        help="also write the loader's input rows here (the reproducible input of record)",
    )
    audit.add_argument(
        "--out",
        required=True,
        help="output directory for audit_report.json + AUDIT_REPORT.md",
    )

    rplan = sub.add_parser(
        "recovery-plan",
        help="P32.6 (SIG-TRUST-007, ADR-125): the bounded, dry-run-only recovery "
        "planner. Reads an evidence-audit report, emits append-only action proposals "
        "(typed re-bindings, adjudicator-specified repairs, withhold dispositions) "
        "with zero writes for ambiguous lineage, unrecoverable preserved, batches "
        "honouring the S1 bounds, and the live return-pass packet. Never writes the spine",
    )
    rplan.add_argument("--audit", required=True, help="an audit_report.json to plan over")
    rplan.add_argument(
        "--applied",
        default=None,
        help="file of action digests already applied (the resume marker → +0 re-plan)",
    )
    rplan.add_argument(
        "--repairs",
        default=None,
        help="JSON {claim_id: {revised_fields, basis, locator}} — adjudicator repairs",
    )
    rplan.add_argument(
        "--no-withhold-unverifiable",
        action="store_true",
        help="do not propose pending_publication_review dispositions for public "
        "unverifiable claims",
    )
    rplan.add_argument(
        "--free-storage-bytes",
        type=int,
        default=None,
        help="projected free space on the target store (headroom rules evaluated)",
    )

    rserve = sub.add_parser(
        "release-serve",
        help="P32.13 (SIG-FIND-001/002, ADR-132): the release-serving barrier — "
        "apply the current withdrawal registry to a staged public tree and check "
        "route access BEFORE origin/CDN (offline staging only; GATE-G3 owns publish)",
    )
    rsrv = rserve.add_subparsers(dest="serve_command", required=True)
    rsrv_apply = rsrv.add_parser(
        "apply", help="re-apply withdrawals to a staged tree + regenerate the nginx deny map"
    )
    rsrv_apply.add_argument("--registry", required=True)
    rsrv_apply.add_argument("--staged", required=True)
    rsrv_check = rsrv.add_parser(
        "check", help="the pure route access check under current dispositions"
    )
    rsrv_check.add_argument("--registry", required=True)
    rsrv_check.add_argument("--route", required=True)

    rroute = sub.add_parser(
        "renamed-routes",
        help="P34.18 / ADR-178: generate conf/renamed_sources.conf — the nginx "
        "exact-match barrier that serves the neutral N-5 page on retired "
        "identifier routes (never a redirect that would repeat a handle)",
    )
    rroute.add_argument(
        "--out",
        required=True,
        help="output conf path (e.g. <staged>/conf/renamed_sources.conf)",
    )
    rroute.add_argument("--dry-run", action="store_true", help="count rules only; write nothing")
    rplan.add_argument(
        "--out",
        required=True,
        help="output directory for recovery_plan.json + the live return-pass packet",
    )

    rapply = sub.add_parser(
        "recovery-apply",
        help="P32.22 (SIG-TRUST-008, ADR-141): the bounded recovery apply — "
        "reconciles the dry-run plan against the audit it was built over, "
        "executes ONLY the selected proposed actions under the sig_recovery "
        "role (per-action atomic receipt = exactly-once across restart), "
        "re-verifies bind bytes at the pinned occurrence (never fetches), "
        "records before/after inventories + resource use + a +0 rerun, and "
        "optionally rematerializes in dependency order. --apply is required "
        "to write; without it the command reconciles and reports only",
    )
    rapply.add_argument(
        "--dsn", default=None, help="writable PostgreSQL DSN (else SIG_STAGING_DSN/local)"
    )
    rapply.add_argument("--plan", required=True, help="the recovery_plan.json to apply")
    rapply.add_argument(
        "--audit", required=True, help="the audit_report.json the plan was built over"
    )
    rapply.add_argument(
        "--apply",
        action="store_true",
        help="execute the selected scope (without it the command reconciles and "
        "reports the scope only — zero writes)",
    )
    rapply.add_argument(
        "--execution-id", default=None, help="recorded execution id (required with --apply)"
    )
    rapply.add_argument(
        "--authority",
        default=None,
        help="the operator authorization stamped on receipts + dispositions "
        "(required with --apply — the plan's placeholder never lands)",
    )
    rapply.add_argument(
        "--decided-by", default=None, help="the deciding operator handle (dispositions)"
    )
    rapply.add_argument(
        "--adjudicator", default=None, help="the adjudicator handle (repair asserted_by)"
    )
    rapply.add_argument(
        "--capture-dir",
        default=None,
        help="the OCFL capture root bind actions re-verify against (required "
        "when the selection contains bind_verified_capture actions)",
    )
    rapply.add_argument(
        "--batches", default=None, help="comma list of batch ids selecting the scope"
    )
    rapply.add_argument(
        "--kinds", default=None, help="comma list of action kinds selecting the scope"
    )
    rapply.add_argument("--claims", default=None, help="file of claim ids selecting the scope")
    rapply.add_argument(
        "--max-actions", type=int, default=None, help="abort threshold on selected actions"
    )
    rapply.add_argument(
        "--role",
        default="sig_recovery",
        help="the least-privilege applier role (default sig_recovery; empty to "
        "run under the session login — tests only)",
    )
    rapply.add_argument(
        "--verify-rerun", action="store_true", help="verify a +0 rerun over the receipts"
    )
    rapply.add_argument(
        "--rematerialize",
        action="store_true",
        help="rematerialize the read surface in dependency order after the apply",
    )
    rapply.add_argument(
        "--out", default=None, help="output directory for APPLY_REPORT.json/.md + the live packet"
    )

    rfreeze = sub.add_parser(
        "recovery-freeze",
        help="P32.22 (SIG-TRUST-008, ADR-141): freeze the unpublished "
        "repaired-input snapshot + audit preview — the HUMAN-H4 frame. Re-runs "
        "the audit over the SAME population on the repaired spine and freezes "
        "the result as sig.repaired-snapshot/1 (explicitly provisional; NOT a "
        "release candidate — P32.23a owns that). Never a public pointer",
    )
    rfreeze.add_argument("--dsn", default=None, help="PostgreSQL DSN (read-only session)")
    rfreeze.add_argument(
        "--apply-report", required=True, help="the APPLY_REPORT.json from recovery-apply"
    )
    rfreeze.add_argument("--plan", required=True, help="the recovery_plan.json the apply executed")
    rfreeze.add_argument(
        "--audit", required=True, help="the audit_report.json the plan was built over"
    )
    rfreeze.add_argument(
        "--capture-dir", default=None, help="the OCFL capture root for the post-apply audit"
    )
    rfreeze.add_argument(
        "--seed", default=None, help="the recorded sampling seed (default: the audit's)"
    )
    rfreeze.add_argument(
        "--sample", type=int, default=None, help="sample size (default: the audit's)"
    )
    rfreeze.add_argument("--targeted", default=None, help="file of claim ids (targeted set)")
    rfreeze.add_argument("--adjudications", default=None, help="adjudicator verdicts JSON")
    rfreeze.add_argument("--sqitch-head", default=None, help="recorded schema identity")
    rfreeze.add_argument(
        "--out",
        required=True,
        help="output directory for REPAIRED_SNAPSHOT.json + AUDIT_PREVIEW.md",
    )

    rseed = sub.add_parser(
        "recovery-fixture-seed",
        help="P32.22 (SIG-TRUST-008): seed a REAL deployed spine from the P32.6 "
        "audit fixture (fixture_spine.json + capture_root) with deterministic "
        "uuid5 id mapping — the test/fixture stage for the bounded apply. "
        "Append-only ON CONFLICT DO NOTHING; writes the id map + remapped "
        "targeted/adjudications files",
    )
    rseed.add_argument(
        "--dsn", default=None, help="writable PostgreSQL DSN (a deployed TEST spine)"
    )
    rseed.add_argument(
        "--fixture",
        default="docs/build/reports/p32.6-legacy-evidence",
        help="the fixture packet directory (fixture_spine.json + capture_root)",
    )
    rseed.add_argument(
        "--out", default=None, help="write id_map.json + remapped targeted/adjudications here"
    )

    rcand = sub.add_parser(
        "release-candidate",
        help="P32.23a (SIG-TRUST-010, ADR-142): build the ONE unpublished "
        "release candidate from the frozen repaired-input snapshot. The S3 "
        "human-evaluation spine is deferred (2026-10-19, no final decision) — "
        "the candidate runs under the PROVISIONAL ruleset with the deferral "
        "disclosed everywhere, verifies the frozen population frame "
        "fail-closed, rematerializes in dependency order + proves +0, exports "
        "all compartments and stages the release namespace WITHOUT activation "
        "(latest.json stays byte-identical), and emits the manifest + "
        "disclosure + rollback packet + the open live return-pass",
    )
    rcand.add_argument(
        "--dsn", default=None, help="writable PostgreSQL DSN (else SIG_STAGING_DSN/local)"
    )
    rcand.add_argument(
        "--snapshot",
        required=True,
        help="the frozen sig.repaired-snapshot/1 (REPAIRED_SNAPSHOT.json) to pin",
    )
    rcand.add_argument("--plan", default=None, help="the recovery_plan.json the apply executed")
    rcand.add_argument(
        "--audit", default=None, help="the post-apply audit_report.json (recorded input)"
    )
    rcand.add_argument(
        "--apply-report",
        default=None,
        help="the APPLY_REPORT.json (recorded change/suppression counts)",
    )
    rcand.add_argument(
        "--shadow",
        default=None,
        help="a recorded sig.provisional-vs-shadow/1 to pin instead of re-reading "
        "the installed eval-confidence/1 posture",
    )
    rcand.add_argument(
        "--as-of",
        default=None,
        help="the export as-of cut (default: the snapshot watermark date)",
    )
    rcand.add_argument(
        "--registry",
        default=None,
        help="the served release registry dir — its latest.json is read before "
        "and after staging and must stay byte-identical (never written)",
    )
    rcand.add_argument(
        "--role",
        default=None,
        help="the materializer role (default: the session login)",
    )
    rcand.add_argument(
        "--dossier-packet",
        action="append",
        default=[],
        help="a committed sig.dossier-packet/1 to compose into the dossier answers (repeatable)",
    )
    rcand.add_argument(
        "--sqitch-head", default=None, help="recorded schema identity for the run row"
    )
    rcand.add_argument(
        "--out",
        required=True,
        help="the candidate packet directory (export/, release/, manifest, "
        "disclosure, rollback packet, return-pass)",
    )

    jv = sub.add_parser(
        "journey-verify",
        help="P32.24 (SIG-FIND-007, ADR-143): run the public-investigation "
        "acceptance portfolio — verifies the P32.23a candidate packet's "
        "digests/identity/deferral posture (read-only), then runs the three "
        "documented journeys over ONE staged acceptance release it builds + "
        "stages itself (never the published registry): A discover-inspect-"
        "trace across three dossiers, B typed relationship traversal, the "
        "withdrawal barrier, and the no-JS/print/citation walkthroughs. "
        "Offline only; the intake journey is Docker-gated (journey-intake / "
        "tests/db) and marked verified_by_test here. Exit 1 on any material "
        "failure — the report names an owner + landing per failed check",
    )
    jv.add_argument(
        "--candidate",
        default="docs/build/reports/p32.23a-release-candidate",
        help="the committed P32.23a candidate packet directory (default: the landed packet)",
    )
    jv.add_argument(
        "--out",
        required=True,
        help="the acceptance report directory — JOURNEY_PORTFOLIO.json/.md, "
        "the corpus export + staged release + staged registry evidence",
    )
    jv.add_argument(
        "--intake-proof",
        default=None,
        help="a sig.journey-intake-proof/1 (from journey-intake) to fold into "
        "the journey-C checks; absent → they stay honestly verified_by_test",
    )
    jv.add_argument(
        "--renderer",
        default="p32.24",
        help="the recorded renderer revision (default: p32.24)",
    )

    rpub = sub.add_parser(
        "release-publish",
        help="P32.25 (SIG-TRUST-009, ADR-144): publish and verify the "
        "GATE-G3-accepted release with rollback — in the BOUNDED staging "
        "namespace only. Preflight-pins the committed candidate packet to "
        "the signed inputs, activates it atomically in a fresh registry "
        "(validate-first, latest-pointer-last), verifies unauthenticated "
        "reads/citations/withdrawal/disclosure/intake-unavailable over the "
        "staged surface, rehearses prior-release + no-prior-pointer + "
        "failed-deploy rollback in labelled scratch registries, and emits "
        "PUBLISH_PROOF + the prepared-not-executed live return pass. "
        "Offline only — NO production serve, no synthetic submission, no "
        "gate tick. Exit 1 on any failed check",
    )
    rpub.add_argument(
        "--candidate",
        default="docs/build/reports/p32.23a-release-candidate",
        help="the committed P32.23a candidate packet directory (default: the landed packet)",
    )
    rpub.add_argument(
        "--out",
        required=True,
        help="the report directory — PUBLISH_PROOF.json/.md, staging_registry/, "
        "rehearsal/, ROLLBACK_REHEARSAL, LIVE_RETURN_PASS",
    )
    rpub.add_argument(
        "--prior-export",
        default="docs/build/reports/p32.24-investigation-journey-verification/corpus_export",
        help="the export the rehearsal's stand-in 'prior release' is rebuilt "
        "from (default: the committed P32.24 acceptance-corpus export)",
    )
    rpub.add_argument(
        "--gate-readout",
        default="docs/build/readouts/GATE-G3.md",
        help="the signed gate readout carrying the publish authority",
    )

    cv = sub.add_parser(
        "composed-verify",
        help="P33.2 (sig.composed-verification/1): drive the composed "
        "Round-10 path over ONE fixture on a real PG spine — capture→claim "
        "(the eight-stage connector pipeline + actual-capture bindings), "
        "temporal/role resolution (pure model vs the SQL twin), eligible "
        "release (materialize→export→build_release→activate with licence "
        "compartments + disposition/licensing exclusions), search/record "
        "(released FTS5 index + serving barrier), and the P32.16→P32.16a "
        "correction chain on a claim THIS release published. Offline only; "
        "needs a writable TEST DSN (sqitch-deployed). Exit 1 on any failed "
        "check — a missing/unusable DSN is a failure, never a silent green",
    )
    cv.add_argument(
        "--dsn",
        default=None,
        help="writable PostgreSQL DSN of the TEST spine (else SIG_STAGING_DSN/local)",
    )
    cv.add_argument(
        "--out",
        required=True,
        help="the report directory — COMPOSED_VERIFICATION.json/.md plus the "
        "export/, release/ and registry/ trees it built",
    )
    cv.add_argument(
        "--renderer",
        default="p33.2",
        help="the recorded renderer revision (default: p33.2)",
    )

    ji = sub.add_parser(
        "journey-intake",
        help="P32.24 (SIG-FIND-007, journey C): execute the durable "
        "receipt→moderation→canonical-correction journey end-to-end on a REAL "
        "PG spine — submit, restart-survival, authorized moderation, the "
        "exactly-once correct apply, publish linkage, and a live "
        "receiver-role canonical-write refusal. Emits "
        "sig.journey-intake-proof/1 JSON",
    )
    ji.add_argument(
        "--dsn",
        default=None,
        help="writable PostgreSQL DSN (else SIG_STAGING_DSN/local) — a TEST spine",
    )
    ji.add_argument(
        "--publication",
        default=None,
        help="the immutable publication id the report cites (required)",
    )
    ji.add_argument(
        "--record",
        default=None,
        help="the cited record_key (default: the acceptance corpus record)",
    )
    ji.add_argument(
        "--key",
        default=None,
        help="deterministic report key (default: a fresh nonce)",
    )
    ji.add_argument(
        "--out",
        default=None,
        help="write the proof JSON here (default: stdout)",
    )
    return parser


# --- state --------------------------------------------------------------------


def _read_state() -> dict[str, object]:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())  # type: ignore[no-any-return]
        except (ValueError, OSError):
            return {}
    return {}


def _write_state(state: dict[str, object]) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


# --- helpers ------------------------------------------------------------------


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["docker", "compose", "-p", _COMPOSE_PROJECT, "-f", str(_COMPOSE_FILE), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=str(_REPO_ROOT))


def _wait(predicate: object, *, label: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    check = predicate  # callable
    while time.time() < deadline:
        if check():  # type: ignore[operator]
            return True
        time.sleep(1.0)
    print(f"  timed out waiting for {label}")
    return False


# --- up -----------------------------------------------------------------------


def _cmd_up(args: argparse.Namespace) -> int:
    dsn = default_dsn()
    print("sig-ops up: composing the SIG runtime (PG spine + API + static)")

    # 1. PG spine + sqitch deploy (containers).
    print("  → docker compose up -d (PG18+PostGIS, sqitch deploy)")
    try:
        _compose("up", "-d", "--wait", "db")
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout)
        print("  docker compose failed to start the DB — is the Docker daemon running?")
        return 1
    if not _wait(lambda: _pg_ready(dsn), label="PostgreSQL"):
        return 1
    # sqitch is a one-shot deploy that exits 0; run it to completion.
    print("  → sqitch deploy db/sqitch.plan")
    deploy = _compose("run", "--rm", "sqitch", check=False)
    if deploy.returncode != 0:
        # sqitch exits non-zero if there is nothing to deploy on some versions; treat
        # "Nothing to deploy" as success but surface any real error.
        combined = (deploy.stdout or "") + (deploy.stderr or "")
        if "Nothing to deploy" not in combined:
            print(combined)
            print("  sqitch deploy failed")
            return 1

    state = _read_state()
    state["dsn"] = dsn

    # 2. API (uvicorn) as a host process over the PG spine.
    api_host, api_port = _api_host_port()
    print(f"  → sig-api serve --dsn <staging> on {api_host}:{api_port}")
    api_log = _STATE_DIR / "api.log"
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    api_proc = subprocess.Popen(
        ["sig-api", "serve", "--host", api_host, "--port", str(api_port), "--dsn", dsn],
        stdout=api_log.open("w"),
        stderr=subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
        start_new_session=True,
    )
    state["api_pid"] = api_proc.pid
    state["api_url"] = default_api_url()

    # 2b. The AUTHENTICATED curation service (P21.6, ADR-068) as a SEPARATE host
    # process, bound to loopback and gated on SIG_CURATION_ENABLED=1 (RISK-P21-10,
    # Part VIII §0.7). It is never the public read API and never world-reachable.
    cur_host, cur_port = _curation_host_port()
    print(f"  → sig-api serve-curation on {cur_host}:{cur_port} (authenticated, non-public)")
    curation_log = _STATE_DIR / "curation.log"
    curation_env = {**os.environ, "SIG_CURATION_ENABLED": "1"}
    curation_proc = subprocess.Popen(
        ["sig-api", "serve-curation", "--host", cur_host, "--port", str(cur_port)],
        stdout=curation_log.open("w"),
        stderr=subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
        env=curation_env,
        start_new_session=True,
    )
    state["curation_pid"] = curation_proc.pid
    state["curation_url"] = default_curation_url()

    # 3. Static server for web/dist as a host process.
    if not args.no_static:
        static_host, static_port = _static_host_port()
        dist = _REPO_ROOT / "web" / "dist"
        if not dist.exists():
            print(f"  ! web/dist not found ({dist}); run the web build first. Skipping static.")
        else:
            print(f"  → static server for web/dist on {static_host}:{static_port}")
            static_log = _STATE_DIR / "static.log"
            static_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "http.server",
                    str(static_port),
                    "--bind",
                    static_host,
                    "--directory",
                    str(dist),
                ],
                stdout=static_log.open("w"),
                stderr=subprocess.STDOUT,
                cwd=str(_REPO_ROOT),
                start_new_session=True,
            )
            state["static_pid"] = static_proc.pid
            state["static_url"] = default_static_url()
    _write_state(state)

    ok_api = _wait(lambda: _http_ok(default_api_url() + "/"), label="API", timeout=45)
    ok_curation = _wait(
        lambda: _http_ok(default_curation_url() + "/"), label="curation", timeout=45
    )
    if not ok_curation:
        print("  ! curation service did not become healthy (see .sig/ops/curation.log)")
    ok_static = True
    if not args.no_static and "static_pid" in state:
        ok_static = _wait(lambda: _http_ok(default_static_url()), label="static", timeout=30)

    if args.seed:
        _cmd_seed(argparse.Namespace(jurisdiction=args.jurisdiction, dsn=dsn))

    if ok_api and ok_static and ok_curation:
        print("sig-ops up: OK — run `sig-ops status` to confirm.")
        return 0
    print("sig-ops up: one or more services did not become healthy (see `sig-ops status`).")
    return 1


# --- status -------------------------------------------------------------------


def _cmd_status(_args: argparse.Namespace) -> int:
    state = _read_state()
    dsn = str(state.get("dsn") or default_dsn())
    api_url = str(state.get("api_url") or default_api_url())
    static_url = str(state.get("static_url") or default_static_url())
    curation_url = str(state.get("curation_url") or default_curation_url())

    pg = _pg_ready(dsn)
    api = _http_ok(api_url + "/")
    curation = _http_ok(curation_url + "/")
    # A static file server has no health route; the root listing is the signal.
    static = _http_ok(static_url)

    def mark(ok: bool) -> str:
        return "healthy" if ok else "DOWN"

    print(f"PG        ({dsn}): {mark(pg)}")
    print(f"API       ({api_url}): {mark(api)}")
    # The curation service is reported SEPARATELY: it is a distinct, authenticated,
    # non-public process (P21.6, ADR-068), never folded into the public API line.
    print(f"curation  ({curation_url}): {mark(curation)}  [authenticated, non-public]")
    print(f"static    ({static_url}): {mark(static)}")
    return 0 if (pg and api and static and curation) else 1


# --- down ---------------------------------------------------------------------


def _kill_pid(pid: object) -> None:
    if not isinstance(pid, int):
        return
    try:
        # start_new_session=True => the child leads its own process group.
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass


def _cmd_down(_args: argparse.Namespace) -> int:
    print("sig-ops down: tearing down the SIG runtime")
    state = _read_state()
    for key in ("api_pid", "curation_pid", "static_pid"):
        _kill_pid(state.get(key))
    print("  → docker compose down -v")
    try:
        _compose("down", "-v", check=False)
    except FileNotFoundError:
        print("  docker not found on PATH")
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()
    print("sig-ops down: OK — no SIG containers or host processes remain.")
    return 0


# --- seed ---------------------------------------------------------------------


def _cmd_seed(args: argparse.Namespace) -> int:
    from .seed import seed_jurisdiction, seedable_jurisdictions

    dsn = args.dsn or default_dsn()
    if args.jurisdiction not in seedable_jurisdictions():
        print(
            f"no slice for jurisdiction {args.jurisdiction!r}; seedable: "
            f"{', '.join(seedable_jurisdictions())}"
        )
        return 2
    report = seed_jurisdiction(dsn, jurisdiction=args.jurisdiction)
    print(
        f"seeded jurisdiction {args.jurisdiction!r}: {report['inserted']} claim(s) inserted, "
        f"{report['duplicates']} duplicate(s), {report['entities']} entity(ies)"
    )
    return 0


def _cmd_dossier_packet(args: argparse.Namespace) -> int:
    from .dossier_packet import write

    written = write(Path(args.out))
    for key, path in written.items():
        print(f"  {key}: {path}")
    return 0


def _cmd_dossier_packet_tulsa(args: argparse.Namespace) -> int:
    from .tulsa_dossier_packet import write

    written = write(Path(args.out))
    for key, path in written.items():
        print(f"  {key}: {path}")
    return 0


def _cmd_dossier_packet_san_diego(args: argparse.Namespace) -> int:
    from .san_diego_dossier_packet import write

    written = write(Path(args.out))
    for key, path in written.items():
        print(f"  {key}: {path}")
    return 0


def _cmd_seed_correct(args: argparse.Namespace) -> int:
    import json as _json

    from .seed_correction import apply_packet, correction_packet

    packet = _json.loads(Path(args.packet).read_text()) if args.packet else correction_packet()
    report = apply_packet(args.dsn or default_dsn(), packet, dry_run=args.dry_run)
    print(_json.dumps(report, indent=2, sort_keys=True, default=str))
    errors = [c for c in report["corrections"] if c.get("outcome") == "error"]
    return 1 if errors else 0


# --- OBS.1 helpers (alert ledger + probe log live under .sig/ops/, env-overridable) ---


def _alert_ledger_path() -> Path:
    return Path(os.environ.get("SIG_ALERT_LOG", str(_STATE_DIR / "alerts.jsonl")))


def _probe_log_path() -> Path:
    return Path(os.environ.get("SIG_PROBE_LOG", str(_STATE_DIR / "probes.jsonl")))


def _fire_alert(
    kind: str, severity: str, message: str, *, detail: dict[str, object] | None = None
) -> Alert:
    """Record an alert in the ledger, then notify every env-configured sink (ADR-077)."""
    from .alerts import AlertLedger, fire, notifiers_from_env

    alert = Alert.create(kind, severity, message, detail=detail)
    fire(alert, ledger=AlertLedger(_alert_ledger_path()), notifiers=notifiers_from_env())
    return alert


def _observability_config(config_arg: str | Path | None) -> ObservabilityConfig:
    """Resolve ``ops/config.toml`` → observability config.

    Candidates: explicit arg → ``$SIG_OPS_CONFIG`` → the file next to
    ``docker-compose.yml`` (repo checkout) → ``./ops/config.toml`` under the CWD
    (the image's ``WORKDIR /app`` layout). When no file exists at all the
    documented ``ObservabilityConfig()`` defaults are used (an explicit arg that
    does not exist still raises — fail closed on a typo, not silently default).
    """
    candidates: list[Path] = []
    if config_arg:
        candidates.append(Path(config_arg))
    env_path = os.environ.get("SIG_OPS_CONFIG", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates += [_COMPOSE_FILE.parent / "config.toml", Path.cwd() / "ops" / "config.toml"]
    resolved = next((c for c in candidates if c.is_file()), None)
    if resolved is None:
        return ObservabilityConfig.from_toml(candidates[0]) if config_arg else ObservabilityConfig()
    return ObservabilityConfig.from_toml(resolved)


def _cmd_egress_report(args: argparse.Namespace) -> int:
    from .egress import EgressConfig, build_report, exit_code_for

    config_path = args.config or (_COMPOSE_FILE.parent / "config.toml")
    config = EgressConfig.from_toml(config_path)
    report = build_report(config, args.usage_gb)
    print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    if report.gate_pending:
        print(
            "gate pending: HG-07 — no live object-store usage API (no credentials); "
            f"budget threshold {config.monthly_budget_gb} GB documented, not measured "
            "(RISK-P21-09).",
            file=sys.stderr,
        )
    # Wire INFRA.1's alarm to the notifier seam (OBS.1): a warn/alarm threshold
    # breach fires a RECORDED alert. The breach decision stays in ops.egress —
    # this consumes it, it does not re-implement it.
    if args.alert and report.level in ("warn", "alarm"):
        _fire_alert(
            "egress-budget",
            report.level,
            f"egress threshold breached: {report.usage_gb} GB of "
            f"{report.budget_gb} GB ({report.level})",
            detail=report.as_json(),
        )
    return exit_code_for(report)


def _cmd_swh_save(args: argparse.Namespace) -> int:
    from .swh import build_save_request, submit

    repo_url = args.repo_url or os.environ.get("SIG_REPO_URL")
    if not repo_url:
        print(
            "gate pending: no public repository URL to save (pass --repo-url or set "
            "SIG_REPO_URL). Software Heritage save NOT triggered this run.",
            file=sys.stderr,
        )
        return 4
    token = os.environ.get("SIG_SWH_TOKEN")
    request = build_save_request(repo_url, visit_type=args.visit_type, token=token)
    if not args.now:
        print(json.dumps(request.as_json(), indent=2, sort_keys=True))
        print(
            "(untriggered — re-run with --now to submit to Software Heritage; "
            "no token is needed for a public repo)",
            file=sys.stderr,
        )
        return 0
    result = submit(request)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_degraded(args: argparse.Namespace) -> int:
    from .degraded import DegradedBuildError, build_static_site

    print("sig-ops degraded: building the fully static site (NO API; last-export banner)")
    try:
        dist = build_static_site(
            repo_root=_REPO_ROOT,
            data_source=args.data_source,
            export_dir=args.export_dir,
        )
    except DegradedBuildError as exc:
        print(str(exc), file=sys.stderr)
        print("sig-ops degraded: FAILED — the site could not be rebuilt.", file=sys.stderr)
        return 1
    print(f"sig-ops degraded: OK — static site at {dist} (cost = $0 beyond the static host).")
    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    from .deploy import adc_present, plan_for

    if getattr(args, "prepare_only", False):
        return _cmd_deploy_prepare(args)

    plan = plan_for(args.target)
    # In this isolated context there are no Application Default Credentials, so the
    # command runs in plan mode regardless: it prints the plan and exits 0 without
    # opening the network. The real push/sync is gate-pending (HG-12 / D-ACCT.1-1).
    forced = args.dry_run or not adc_present()
    plan = plan.__class__(
        target=plan.target,
        project=plan.project,
        region=plan.region,
        steps=plan.steps,
        dry_run=forced,
        adc_present=plan.adc_present,
    )
    for line in plan.as_lines():
        print(line)
    if forced and not plan.adc_present:
        print(
            "gate pending: HG-12 / D-ACCT.1-1 — no Application Default Credentials; "
            "plan printed, nothing pushed. Export ADC + SIG_GCP_PROJECT and re-run "
            "without --dry-run to apply.",
            file=sys.stderr,
        )
    elif forced:
        print(
            "dry-run: plan printed, nothing pushed. Re-run without --dry-run to apply "
            "(the real push/sync is the operator-gated RETURN PASS action, D-DEPLOY.1-1).",
            file=sys.stderr,
        )
    return 0


def _cmd_deploy_prepare(args: argparse.Namespace) -> int:
    """Build + partition + prove-clean the public surface locally (P27.8; network-free)."""
    from pathlib import Path

    from .publish import PublishError, run_public_prepare

    export_dir = Path(args.export_dir).resolve() if args.export_dir else None
    print("sig-ops deploy --prepare-only: building the public surface from the real export")
    try:
        result = run_public_prepare(repo_root=_REPO_ROOT, export_dir=export_dir)
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        print(
            "sig-ops deploy --prepare-only: FAILED — the public surface was NOT produced "
            "(no fixtures fall-back, no restricted byte published).",
            file=sys.stderr,
        )
        return 1
    for line in result.as_lines():
        print(f"  {line}")
    print(
        "  built-from watermark: "
        + json.dumps(result.partition.watermark, sort_keys=True, default=str)
    )
    print(
        "sig-ops deploy --prepare-only: OK — web/dist + exports/out/public ready; publish "
        "them with `sig-ops publish-web` (P34.10 — the one repository-owned publish "
        "path; hand-typed bucket syncs are forbidden, SIG-OPS-004)."
    )
    return 0


def _cmd_publish_web(args: argparse.Namespace) -> int:
    """The one allow-listed publish path (P34.10; SIG-OPS-003/004)."""
    from .gcs import GcsBucket, GcsError
    from .observe import ProbeResult
    from .publish import PublishError, run_public_prepare, run_publish_web
    from .scheduled import load_cadence, probe_hosted, resolve_targets

    dist = Path(args.dist).resolve() if args.dist else _REPO_ROOT / "web" / "dist"
    public_tree: Path | None = None
    data_release: str | None = None
    if args.export_dir:
        # The full prepare leg: export-mode build + partition + clean proof —
        # the publish then rides on the tree this command itself produced.
        try:
            prepare = run_public_prepare(
                repo_root=_REPO_ROOT, export_dir=Path(args.export_dir).resolve()
            )
        except PublishError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        for line in prepare.as_lines():
            print(f"  {line}")
        dist = prepare.dist
        public_tree = prepare.partition.public_root
        # the export's own release id rides the site release record — the
        # provenance link from a published page back to the data build.
        data_release = prepare.partition.watermark.get("release_id")
    if args.public_tree:
        public_tree = Path(args.public_tree).resolve()

    project = os.environ.get("SIG_GCP_PROJECT", "").strip()
    bucket_name = (
        args.bucket
        or os.environ.get("SIG_WEB_BUCKET", "").strip()
        or (f"{project}-sig-web" if project else "")
    )
    public_bucket_name = (
        args.public_bucket
        or os.environ.get("SIG_PUBLIC_BUCKET", "").strip()
        or (f"{project}-sig-public" if project else "")
    )
    bucket = GcsBucket(bucket_name) if bucket_name else None
    public_bucket = GcsBucket(public_bucket_name) if public_bucket_name else None
    if args.apply and bucket is None:
        print(
            "publish-web --apply: no destination bucket — set --bucket, "
            "SIG_WEB_BUCKET or SIG_GCP_PROJECT (nothing was synced)",
            file=sys.stderr,
        )
        return 2
    if args.apply and public_tree is not None and public_bucket is None:
        print(
            "publish-web --apply: --public-tree needs a compartment bucket — set "
            "--public-bucket, SIG_PUBLIC_BUCKET or SIG_GCP_PROJECT",
            file=sys.stderr,
        )
        return 2

    def absent_verify() -> list[ProbeResult]:
        # the post-sync proof (SIG-OPS-003): cadence http-absent targets
        cadence = load_cadence(args.cadence)
        specs = {s.name: s for s in cadence.probe_targets}
        resolved, skipped = resolve_targets(cadence)
        targets = [
            (name, specs[name].kind, url)
            for name, url in resolved
            if specs[name].kind == "http-absent"
        ]
        for name in skipped:
            if specs.get(name) is not None and specs[name].kind == "http-absent":
                print(
                    f"  ! absent-probe target {name!r} skipped — URL not resolvable "
                    "(that origin's absence goes unproven this run)",
                    file=sys.stderr,
                )
        return probe_hosted(targets)

    try:
        result = run_publish_web(
            dist=dist,
            apply=args.apply,
            bucket=bucket,
            allowlist_path=args.allowlist,
            release_tree=Path(args.release_tree).resolve() if args.release_tree else None,
            export_tree=public_tree,
            export_bucket=public_bucket,
            release_id=args.release_id,
            data_release=data_release,
            absent_verify=absent_verify if args.apply else None,
        )
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        print("sig-ops publish-web: REFUSED — nothing was published.", file=sys.stderr)
        return 3
    except GcsError as exc:
        print(f"sig-ops publish-web: bucket operation failed: {exc}", file=sys.stderr)
        return 7
    for line in result.as_lines():
        print(line)
    if not args.apply:
        print(
            "dry-run: assertions green, release record written, sync plan above; "
            "re-run with --apply to sync + probe (the first --apply is P34.17's "
            "gated leg).",
            file=sys.stderr,
        )
    return 0


def _cmd_republish_probe(args: argparse.Namespace) -> int:
    """P34.21b: emit the sig.probe-run/1 pre-republish probe record."""
    from .republish_probe import (
        DEFAULT_HANDLE_LIST,
        read_release_record,
        run_republish_probe,
    )

    dist = Path(args.dist).resolve() if args.dist else None
    handle_list = Path(args.handle_list).resolve() if args.handle_list else DEFAULT_HANDLE_LIST
    record = run_republish_probe(
        cadence_path=args.cadence,
        handle_list=handle_list,
        export_dirs=[Path(d).resolve() for d in args.export_dir],
        tiles_dirs=[Path(d).resolve() for d in args.tiles_dir],
        build_dirs=[Path(d).resolve() for d in args.build_dir],
        bucket_listing=Path(args.bucket_listing).resolve() if args.bucket_listing else None,
        tile_urls=list(args.tile_url),
        public_dir=Path(args.public_dir).resolve() if args.public_dir else None,
        release=read_release_record(dist),
    )
    text = json.dumps(record, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"sig-ops republish-probe: record -> {args.out}")
    else:
        print(text)
    print(
        f"sig-ops republish-probe: overall={record['overall']} "
        f"generated_at={record['generated_at']} — a republish leg needs this "
        "record no older than 24h (P34.21b L2).",
        file=sys.stderr,
    )
    return 0 if record["overall"] != "fail" else 1


def _cmd_backup_drill(args: argparse.Namespace) -> int:
    from .backup import DrillError, restore_drill

    dsn = args.dsn or default_dsn()
    admin_dsn = dsn  # connect to the source DB to (re)create the fresh target DB
    print(f"sig-ops backup-drill: pg_dump {dsn} → restore into fresh {args.target_db!r}")
    try:
        report = restore_drill(source_dsn=dsn, admin_dsn=admin_dsn, target_dbname=args.target_db)
    except DrillError as exc:
        print(f"sig-ops backup-drill: FAILED — {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    if not report.reproduced:
        print(
            "sig-ops backup-drill: FAILED — the restored graph did not reproduce.",
            file=sys.stderr,
        )
        return 1
    print("sig-ops backup-drill: OK — the restored graph reproduces the source cardinality.")
    return 0


def _cmd_cloudsql_drill(args: argparse.Namespace) -> int:
    """P34.6: run the at-T parity comparison and emit the drill record."""
    import os
    from datetime import UTC, datetime

    from .cloudsql_drill import DrillNameError, assert_drill_name, drill_parity

    try:
        clone_instance = assert_drill_name(args.clone_instance)
    except DrillNameError as exc:
        print(f"sig-ops cloudsql-drill: REFUSED — {exc}", file=sys.stderr)
        return 42
    source_dsn = os.environ.get("SIG_DRILL_DSN_SOURCE", "").strip()
    clone_dsn = os.environ.get("SIG_DRILL_DSN_CLONE", "").strip()
    if not source_dsn or not clone_dsn:
        print(
            "sig-ops cloudsql-drill: SIG_DRILL_DSN_SOURCE and SIG_DRILL_DSN_CLONE "
            "must be set (env only — a DSN on argv leaks into the process list).",
            file=sys.stderr,
        )
        return 2
    try:
        at = datetime.fromisoformat(args.at.replace("Z", "+00:00"))
        started = (
            datetime.fromisoformat(args.clone_started_at.replace("Z", "+00:00"))
            if args.clone_started_at
            else None
        )
    except ValueError as exc:
        print(f"sig-ops cloudsql-drill: bad timestamp — {exc}", file=sys.stderr)
        return 2
    record = drill_parity(
        source_dsn=source_dsn,
        clone_dsn=clone_dsn,
        at=at,
        clone_instance=clone_instance,
        clone_started_at=started,
        verified_at=datetime.now(UTC),
    )
    payload = record.as_json()
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops cloudsql-drill: record -> {args.out}")
    if not record.reproduced:
        print(
            "sig-ops cloudsql-drill: FAILED — the clone does not reproduce the "
            "source at T (see the per-table rows / watermark / sqitch fields).",
            file=sys.stderr,
        )
        return 1
    print("sig-ops cloudsql-drill: OK — exact append-only parity at the restore point.")
    return 0


def _cmd_keepalive_check(args: argparse.Namespace) -> int:
    from .alerts import alert_exit_code
    from .observe import verify_keepalive

    result = verify_keepalive(
        repo_root=_REPO_ROOT,
        data_source=args.data_source,
        export_dir=args.export_dir,
    )
    print(json.dumps(result.as_json(), indent=2, sort_keys=True))
    if result.ok:
        print("sig-ops keepalive-check: OK — the dormant-scheduler keepalive verifies.")
        return 0
    fired = _fire_alert(
        "keepalive",
        "critical",
        "keepalive verification FAILED — the degraded rebuild or its scheduler "
        "wiring is broken (SIG-GOV-021, RISK-P0-12)",
        detail=result.as_json(),
    )
    print(
        "sig-ops keepalive-check: FAILED — recorded alert fired (kind=keepalive).",
        file=sys.stderr,
    )
    return alert_exit_code(fired)


def _cmd_probe(args: argparse.Namespace) -> int:
    from .alerts import alert_exit_code
    from .observe import ProbeLog, probe_stack, prune_jsonl

    config = _observability_config(args.config)
    results = probe_stack(
        dsn=default_dsn(),
        api_url=default_api_url(),
        static_url=default_static_url(),
        curation_url=default_curation_url(),
    )
    log = ProbeLog(_probe_log_path())
    for result in results:
        log.append(result)
    dropped = prune_jsonl(log.path, config.retention())
    for result in results:
        print(json.dumps(result.as_json(), sort_keys=True))
    if dropped:
        print(f"  (retention: pruned {dropped} probe rows)", file=sys.stderr)
    down = [r for r in results if not r.ok]
    if down and args.alert:
        fired = None
        for result in down:
            fired = _fire_alert(
                "probe",
                "critical",
                f"service {result.service} is DOWN ({result.detail or 'unreachable'})",
                detail=result.as_json(),
            )
        return alert_exit_code(fired)
    return 0 if not down else 1


# --- P26.1 / OPS.2: scheduled live operations ---------------------------------


def _gcs_bucket(bucket_arg: str | None) -> GcsBucket | None:
    """The configured restricted-bucket handle, or None when unconfigured."""
    from .gcs import GcsBucket

    name = bucket_arg or os.environ.get("SIG_OPS_GCS_BUCKET", "").strip()
    return GcsBucket(name) if name else None


def _cmd_probe_hosted(args: argparse.Namespace) -> int:
    from .alerts import alert_exit_code
    from .gcs import GcsError
    from .observe import ProbeLog, prune_jsonl
    from .scheduled import load_cadence, probe_hosted, resolve_targets, upload_sweep

    config = _observability_config(None)
    cadence = load_cadence(args.cadence)
    specs = {s.name: s for s in cadence.probe_targets}
    resolved, skipped = resolve_targets(cadence)
    targets: list[tuple[str, str, str]] = [(name, specs[name].kind, url) for name, url in resolved]
    for extra in args.extra_target:
        if "=" not in extra:
            print(f"--extra-target must be NAME=URL (got {extra!r})", file=sys.stderr)
            return 2
        name, url = extra.split("=", 1)
        targets.append((name.strip(), "http", url.strip()))
    for name in skipped:
        print(
            f"  ! probe target {name!r} skipped — URL not resolvable (env unset)",
            file=sys.stderr,
        )
    if not targets:
        print("probe-hosted: no targets resolved — nothing probed (config gap)", file=sys.stderr)
        return 2

    results = probe_hosted(targets)
    # Local bounded log (the OBS.1 shape) — always, even before any upload.
    log = ProbeLog(_probe_log_path())
    for result in results:
        log.append(result)
    dropped = prune_jsonl(log.path, config.retention())
    for result in results:
        print(json.dumps(result.as_json(), sort_keys=True))
    if dropped:
        print(f"  (retention: pruned {dropped} probe rows)", file=sys.stderr)

    # The durable record: one new timestamped object per sweep (WORM).
    gcs = _gcs_bucket(args.gcs_bucket)
    if gcs is None:
        print(
            "  ! no GCS bucket configured (--gcs-bucket / SIG_OPS_GCS_BUCKET) — "
            "sweep recorded locally only",
            file=sys.stderr,
        )
    else:
        try:
            name = upload_sweep(gcs, cadence.probe_gcs_prefix, results, results[0].ts)
            print(f"  sweep stored: gs://{gcs.bucket}/{name}")
        except GcsError as exc:
            print(f"  ! sweep upload FAILED (recorded locally): {exc}", file=sys.stderr)
            return 7
    down = [r for r in results if not r.ok]
    if down and args.alert:
        kinds = {name: kind for name, kind, _url in targets}
        fired = None
        for result in down:
            if kinds.get(result.service) == "http-absent":
                # P34.10: a failed absence probe means the denied route is
                # PRESENT (or the origin unreachable) — word it accordingly.
                message = (
                    f"denied route probe {result.service} is RED on a public origin "
                    f"({result.detail or 'route present'})"
                )
            else:
                message = (
                    f"hosted target {result.service} is DOWN ({result.detail or 'unreachable'})"
                )
            fired = _fire_alert("probe-hosted", "critical", message, detail=result.as_json())
        return alert_exit_code(fired)
    return 0 if not down else 1


def _cmd_probe_history(args: argparse.Namespace) -> int:
    from .gcs import GcsError
    from .observe import ProbeLog
    from .scheduled import (
        fold_probe_history,
        load_cadence,
        read_sweep_rows,
    )

    cadence = load_cadence(args.cadence)
    if args.local:
        rows = ProbeLog(Path(args.local)).read()
        origin = args.local
    else:
        gcs = _gcs_bucket(args.gcs_bucket)
        if gcs is None:
            print(
                "probe-history: no GCS bucket configured (--gcs-bucket / "
                "SIG_OPS_GCS_BUCKET) and no --local log given",
                file=sys.stderr,
            )
            return 2
        try:
            rows = read_sweep_rows(gcs, cadence.probe_gcs_prefix)
        except GcsError as exc:
            print(f"probe-history: GCS read failed: {exc}", file=sys.stderr)
            return 1
        origin = f"gs://{gcs.bucket}/{cadence.probe_gcs_prefix}/"
    summaries = fold_probe_history(rows, last=args.last)
    if not summaries:
        print(f"probe-history: no stored sweeps under {origin}")
        return 0
    print(f"probe-history over {origin} (last-{args.last} p95):")
    print("| target | probes | ok | uptime % | latest | latest state | p95 ms |")
    print("|---|---|---|---|---|---|---|")
    for s in summaries:
        print(
            f"| {s.target} | {s.probes} | {s.ok} | "
            f"{s.uptime_pct if s.uptime_pct is not None else '—'} | {s.latest_ts} | "
            f"{'healthy' if s.latest_ok else 'DOWN'} | "
            f"{s.p95_ms if s.p95_ms is not None else '—'} |"
        )
    return 0


def _cloudsql_dsn_from_parts() -> str | None:
    """The Cloud SQL unix-socket DSN from the job's ``SIG_PG_*`` env parts (HG-09).

    The password arrives from Secret Manager as ``$SIG_PG_PASSWORD``; it is never a
    command-line argument. ``None`` when the parts are absent (a local shell).
    """
    user = os.environ.get("SIG_PG_USER", "")
    db = os.environ.get("SIG_PG_DB", "")
    conn = os.environ.get("SIG_CLOUDSQL_CONNECTION", "")
    password = os.environ.get("SIG_PG_PASSWORD", "")
    if user and db and conn:
        return f"postgresql://{user}:{password}@/{db}?host=/cloudsql/{conn}"
    return None


def _cmd_backfill_run_completions(args: argparse.Namespace) -> int:
    """P31.2 / ADR-109: append completions for the WORM run rows that prove one."""
    import psycopg
    from connectors.runner import CONNECTOR_FOR_SOURCE
    from psycopg import sql

    from .run_completion import backfill_run_completions, read_worm_rows
    from .scheduled import load_cadence

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print("backfill-run-completions: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts")
        return 2
    gcs = _gcs_bucket(args.gcs_bucket)
    if gcs is None:
        print("backfill-run-completions: needs --gcs-bucket / SIG_OPS_GCS_BUCKET (the WORM rows)")
        return 2
    prefix = args.prefix or load_cadence(args.cadence).runs_gcs_prefix
    rows = read_worm_rows(gcs, prefix, connector_for_source=CONNECTOR_FOR_SOURCE)
    with psycopg.connect(dsn, autocommit=True) as conn:
        if args.role:
            # Least privilege (ADR-103): the materialize role may INSERT completions
            # and read the public tier, nothing else.
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(args.role)))
        report = backfill_run_completions(conn, rows, dry_run=args.dry_run)
    print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    return 0


def _cmd_scheduled_ingest(args: argparse.Namespace) -> int:
    from .alerts import utcnow
    from .scheduled import load_cadence, run_object_uri, scheduled_ingest, store_run_row

    cadence = load_cadence(args.cadence)
    if bool(args.source) == bool(args.batch):
        print("scheduled-ingest: exactly one of --source / --batch is required")
        return 2
    members: list[str] = []
    if args.batch:
        batch = next((b for b in cadence.batches if b.id == args.batch), None)
        if batch is None:
            print(f"scheduled-ingest: no [[batches]] row with id {args.batch!r}")
            return 2
        members = list(batch.members)
    else:
        members = [args.source]
    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN")
    if args.sink == "pg" and not dsn:
        dsn = _cloudsql_dsn_from_parts()
    if args.sink == "pg" and not dsn:
        print("scheduled-ingest: --sink pg needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts")
        return 2
    from connectors.sinks import resolve_commit_chunk_size

    if args.target_limit is not None and args.target_limit < 1:
        print("scheduled-ingest: --target-limit must be >= 1")
        return 2
    try:
        commit_chunk_size = resolve_commit_chunk_size(args.commit_chunk_size)
    except ValueError as bad:
        print(f"scheduled-ingest: invalid commit chunk size: {bad}")
        return 2
    local_dir = Path(os.environ.get("SIG_RUN_LOG", str(_STATE_DIR / "runs")))
    # P31.4 / ADR-111: the capture store. A hosted job mounts the restricted bucket
    # and points SIG_CAPTURE_DIR into it, so captures survive the execution and a
    # restart can re-process them; unset, captures stay under the local state dir.
    capture_dir = Path(os.environ.get("SIG_CAPTURE_DIR") or str(_STATE_DIR / "captures"))
    gcs = _gcs_bucket(args.gcs_bucket)
    exit_code = 0
    for source in members:
        # P31.2 / ADR-109: the WORM object name is fixed by the start time, so the
        # execution's completion row can name the run row written just below.
        started = utcnow()
        run_uri = (
            run_object_uri(gcs.bucket, cadence.runs_gcs_prefix, source, started)
            if gcs is not None
            else None
        )
        row = scheduled_ingest(
            source,
            sink_kind=args.sink,
            dsn=dsn,
            capture_dir=capture_dir,
            commit_chunk_size=commit_chunk_size,
            now=started,
            run_record_uri=run_uri,
            logical_run=_logical_run_for(cadence, source, started, args),
            target_limit=args.target_limit,
            code_commit=os.environ.get("SIG_CODE_COMMIT", "").strip() or None,
        )
        written = store_run_row(row, prefix=cadence.runs_gcs_prefix, gcs=gcs, local_dir=local_dir)
        print(json.dumps(row.as_json(), sort_keys=True))
        for where, loc in written.items():
            print(f"  run row stored ({where}): {loc}")
        if row.exit_code:
            exit_code = exit_code or row.exit_code
    if gcs is None:
        print(
            "  ! no GCS bucket configured — run row recorded locally only",
            file=sys.stderr,
        )
    return exit_code


def _cmd_replay_ingest(args: argparse.Namespace) -> int:
    """P31.6 / ADR-113: the asserting replay over persisted captures."""
    from connectors.runner import replay_ingest
    from connectors.sinks import resolve_commit_chunk_size

    from .alerts import utcnow
    from .scheduled import RunRow, load_cadence, run_object_uri, store_run_row

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print("replay-ingest: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts")
        return 2
    try:
        commit_chunk_size = resolve_commit_chunk_size(args.commit_chunk_size)
    except ValueError as bad:
        print(f"replay-ingest: invalid commit chunk size: {bad}")
        return 2
    capture_dir = Path(os.environ.get("SIG_CAPTURE_DIR") or str(_STATE_DIR / "captures"))
    gcs = _gcs_bucket(args.gcs_bucket)
    cadence = load_cadence(args.cadence)
    local_dir = Path(os.environ.get("SIG_RUN_LOG", str(_STATE_DIR / "runs")))
    started = utcnow()
    t0 = time.monotonic()
    run_uri = (
        run_object_uri(gcs.bucket, cadence.runs_gcs_prefix, args.source, started)
        if gcs is not None
        else None
    )
    outcome = "ok"
    exit_code = 0
    detail = ""
    run_id = ""
    claims = 0
    try:
        report = replay_ingest(
            args.source,
            dsn=dsn,
            capture_dir=capture_dir,
            run_ids=list(args.run_id or []) or None,
            code_commit=os.environ.get("SIG_CODE_COMMIT", "").strip() or "unknown",
            run_record_uri=run_uri,
            commit_chunk_size=commit_chunk_size,
            replay_key=args.replay_key,
        )
        run_id = report.run_id or ""
        claims = report.claims_inserted
        outcome = report.status
        parts = [
            f"replayed {report.captures_replayed}/{report.captures_considered} captures",
            f"inserted {report.claims_inserted} / duplicate {report.claims_duplicate}",
            f"replay_of={','.join(report.replayed_from_runs) or 'none'}",
        ]
        if report.detail:
            parts.append(report.detail)
        detail = "; ".join(parts)
    except Exception as exc:  # noqa: BLE001 - the outcome IS the exception class
        outcome, exit_code = "error", 1
        detail = f"{type(exc).__name__}: {exc}"
    row = RunRow(
        kind="replay-ingest",
        source=args.source,
        mode="replay",
        outcome=outcome,
        exit_code=exit_code,
        started_at=started,
        duration_seconds=time.monotonic() - t0,
        claims_added=claims,
        detail=detail,
        ingest_run_id=run_id,
    )
    written = store_run_row(row, prefix=cadence.runs_gcs_prefix, gcs=gcs, local_dir=local_dir)
    print(json.dumps(row.as_json(), sort_keys=True))
    for where, loc in written.items():
        print(f"  run row stored ({where}): {loc}")
    return exit_code


def _logical_run_for(
    cadence: CadenceConfig, source: str, started: str, args: argparse.Namespace
) -> str | None:
    """The run's logical-run key (P31.4 / ADR-111), or ``None`` when it never resumes.

    ``--logical-run`` pins the key; ``--no-resume`` disables resume; otherwise the
    key is the source's cadence window (``ops.cadence_window``). A source with no
    cadence row has no window, so it never resumes.
    """
    from datetime import datetime

    from .cadence_window import CronError, cron_for_source, logical_run_key

    if args.no_resume or args.sink != "pg":
        return None
    if args.logical_run:
        return str(args.logical_run)
    cron = cron_for_source(cadence, source)
    if cron is None:
        return None
    try:
        return logical_run_key(source, cron, datetime.fromisoformat(started.replace("Z", "+00:00")))
    except CronError as bad:
        # An unparseable cron costs only the resume, never the run.
        print(f"  ! {source}: no logical run ({bad}); running without resume", file=sys.stderr)
        return None


def _cmd_roll_jobs(args: argparse.Namespace) -> int:
    """Roll jobs onto a pinned digest (P31.4 / ADR-111); plan-only unless --apply."""
    from .job_roll import (
        JobPlan,
        RollError,
        apply_roll,
        gcloud_cli,
        plan_roll,
        resolve_digest,
        roll_record,
    )
    from .scheduled import load_cadence

    project = args.project or os.environ.get("SIG_GCP_PROJECT", "")
    region = args.region or os.environ.get("SIG_GCP_REGION", "us-central1")
    if not project:
        print("roll-jobs: --project / SIG_GCP_PROJECT is required")
        return 2
    bucket = (
        args.capture_bucket
        if args.capture_bucket is not None
        else os.environ.get("SIG_OPS_GCS_BUCKET", "")
    ) or None
    jobs = list(args.job)
    if not jobs:
        cadence = load_cadence(args.cadence)
        jobs = [
            cadence.probe_job,
            *(s.job for s in cadence.sources),
            *(b.job for b in cadence.batches),
        ]
    jobs = [j for j in dict.fromkeys(jobs) if j not in set(args.exclude)]
    plans: list[JobPlan] = []
    digest = ""
    failed: str | None = None
    try:
        digest = resolve_digest(args.image, project=project, gcloud=gcloud_cli)
        plans = plan_roll(
            jobs, digest, project=project, region=region, gcloud=gcloud_cli, capture_bucket=bucket
        )
        for plan in plans:
            store = " + capture store" if plan.add_capture_store else ""
            print(f"{plan.job}: {plan.before_image} ({plan.before_digest}) -> {digest}{store}")
        if args.apply:
            apply_roll(
                plans,
                project=project,
                region=region,
                gcloud=gcloud_cli,
                capture_bucket=bucket,
                allow_unresolved_rollback=args.allow_unresolved_rollback,
            )
    except RollError as exc:
        failed = str(exc)
    finally:
        # Always write the record: a roll that failed part-way still names every
        # job's rollback digest and which updates ran.
        if args.record and plans:
            record = roll_record(
                plans, image_ref=args.image, image_digest=digest, applied=args.apply
            )
            Path(args.record).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if failed is not None:
        print(f"roll-jobs: {failed}")
        return 1
    verified = sum(1 for p in plans if p.after_image_verified == digest)
    outcome = f"rolled, {verified} verified" if args.apply else "planned (no --apply)"
    print(f"roll-jobs: {len(plans)} job(s) {outcome}")
    return 0


def _monitoring_defs_dir(args: argparse.Namespace) -> Path:
    if args.defs:
        return Path(args.defs)
    return Path(__file__).resolve().parents[2] / "monitoring"


def _monitoring_defs_live(project: str) -> dict[str, list]:
    """Read the live alert set — list verbs only, never a mutating call."""
    from .job_roll import RollError, gcloud_cli

    def _list(args: list[str]) -> list:
        out = gcloud_cli([*args, f"--project={project}", "--format=json"])
        return json.loads(out)

    try:
        return {
            "channels": _list(["beta", "monitoring", "channels", "list"]),
            "uptime_checks": _list(["monitoring", "uptime", "list-configs"]),
            "policies": _list(["alpha", "monitoring", "policies", "list"]),
        }
    except RollError as exc:
        print(f"monitoring-defs verify: live read failed: {exc}", file=sys.stderr)
        raise


def _cmd_monitoring_defs(args: argparse.Namespace) -> int:
    """The committed alert set: list / render / verify (P34.4)."""
    from .monitoring_defs import (
        DefsError,
        format_findings,
        infer_project,
        load_definitions,
        load_live_dir,
        render_policy_body,
        verify_definitions,
        verify_exit_code,
    )

    defs_dir = _monitoring_defs_dir(args)
    try:
        defs = load_definitions(defs_dir)
    except DefsError as exc:
        print(f"monitoring-defs: {exc}", file=sys.stderr)
        return 2
    cmd = args.monitoring_defs_command
    if cmd == "list":
        for d in defs:
            print(f"{d.kind}/{d.slug} apply={d.apply} id={d.rid or '-'} {d.display_name}")
        return 0
    project = args.project or os.environ.get("SIG_GCP_PROJECT", "")
    if cmd == "render":
        if not project:
            print(
                "monitoring-defs render: --project / SIG_GCP_PROJECT is required",
                file=sys.stderr,
            )
            return 2
        for d in defs:
            if d.slug == args.slug:
                print(json.dumps(render_policy_body(d, project), indent=2, sort_keys=True))
                return 0
        print(f"monitoring-defs render: no policy def slug {args.slug!r}", file=sys.stderr)
        return 2
    if cmd == "verify":
        if args.live and not project:
            print(
                "monitoring-defs verify --live: --project / SIG_GCP_PROJECT is required",
                file=sys.stderr,
            )
            return 2
        try:
            live = _monitoring_defs_live(project) if args.live else load_live_dir(args.from_state)
        except Exception as exc:
            print(f"monitoring-defs verify: {exc}", file=sys.stderr)
            return 2
        if not project:
            project = infer_project(live)
        if not project:
            print(
                "monitoring-defs verify: --project / SIG_GCP_PROJECT required "
                "(the capture carries no projects/<id>/ name to infer it from)",
                file=sys.stderr,
            )
            return 2
        findings = verify_definitions(defs, live, project)
        print(format_findings(findings))
        return verify_exit_code(findings)
    print("monitoring-defs: a subcommand is required (list|render|verify)", file=sys.stderr)
    return 2


def _cmd_sink_bench(args: argparse.Namespace) -> int:
    """Time real-source PgClaimSink passes (P31.3 / ADR-110, the hosted measurement)."""
    import tempfile

    import psycopg
    from connectors.runner import RunMode, run_source
    from connectors.sinks import resolve_commit_chunk_size
    from connectors.stages import registered_connectors
    from db.claim_sink import DEFAULT_COMMIT_CHUNK_SIZE, record_resightings
    from db.sink_bench import run_pass

    if args.passes < 1:
        print("sink-bench: --passes must be >= 1")
        return 2
    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print("sink-bench: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts")
        return 2
    chunk = resolve_commit_chunk_size(args.commit_chunk_size) or DEFAULT_COMMIT_CHUNK_SIZE
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as captures:
        # The fetch is the scheduled path's: live gate first, then the politeness
        # layer. The memory sink asserts nothing, so the timed passes below are the
        # only writes.
        report = run_source(
            args.source, mode=RunMode.LIVE, sink_kind="memory", capture_dir=Path(captures)
        )
    fetch_seconds = time.perf_counter() - started
    version = getattr(registered_connectors()[report.connector], "version", "1.0.0")
    print(
        json.dumps(
            {
                "phase": "fetch",
                "source": args.source,
                "connector": report.connector,
                "records": len(report.claims),
                "captures": len(report.captures),
                "seconds": round(fetch_seconds, 3),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        for n in range(args.passes):
            result = run_pass(
                conn,
                report.claims,
                label=f"pass-{n + 1}",
                connector_name=report.connector,
                connector_version=str(version),
                code_commit=args.code_commit,
                commit_chunk_size=chunk,
                source_id=args.source,
                # P31.7 / ADR-R9-RESIGHT: the bench exercises the production sink
                # path, which now appends a re-sighting link per duplicate claim —
                # so its +0 pass is also the bounded claim_evidence growth measure.
                sink_kwargs={"on_duplicates": record_resightings},
            )
            print(result.as_json(), flush=True)
    return 0


def _cmd_cadence(args: argparse.Namespace) -> int:
    from .scheduled import load_cadence, unscheduled_live_sources

    cadence = load_cadence(args.cadence)
    print(
        f"probes: job={cadence.probe_job} scheduler={cadence.probe_scheduler} "
        f"cron={cadence.probe_schedule!r} → gs://<restricted>/{cadence.probe_gcs_prefix}/"
    )
    for spec in cadence.probe_targets:
        print(f"  target {spec.name} ({spec.kind})")
    print(f"runs → gs://<restricted>/{cadence.runs_gcs_prefix}/<source>/<date>/<ts>.json")
    print("scheduled sources:")
    for s in cadence.sources:
        marker = " (existing — verify only)" if s.existing else ""
        print(f"  {s.source:38s} {s.cadence:8s} {s.cron:12s} {s.job} ← {s.scheduler}{marker}")
    if cadence.batches:
        print("scheduled batches (P26.16 GL-GATE-07):")
        for b in cadence.batches:
            print(
                f"  {b.id:38s} {b.cadence:8s} {b.cron:12s} {b.job} ← {b.scheduler}"
                f"  [{len(b.members)} members]"
            )
    missing = unscheduled_live_sources(cadence)
    if missing:
        print(
            "UNSCHEDULED live-target sources (loadable, in live_targets.toml, no "
            f"cadence row): {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1 if args.check else 0
    if args.check:
        print("cadence check OK — every loadable live-target source has a cadence row")
    return 0


def _cmd_alerts(args: argparse.Namespace) -> int:
    from .alerts import AlertLedger
    from .observe import prune_jsonl

    ledger = AlertLedger(_alert_ledger_path())
    if args.prune:
        config = _observability_config(args.config)
        dropped = prune_jsonl(ledger.path, config.retention())
        if dropped:
            print(f"  (retention: pruned {dropped} alert rows)", file=sys.stderr)
    rows = ledger.read()
    if args.limit:
        rows = rows[-args.limit :]
    if not rows:
        print("no alerts recorded")
        return 0
    for row in rows:
        print(json.dumps(row, sort_keys=True))
    return 0


def _cmd_alert(args: argparse.Namespace) -> int:
    alert = _fire_alert(args.kind, args.severity, args.message)
    print(
        f"recorded alert: {alert.severity} {alert.kind} at {alert.ts} "
        f"(ledger {_alert_ledger_path()})"
    )
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    from .alerts import AlertLedger
    from .egress import EgressConfig, build_report
    from .observe import (
        ProbeLog,
        compute_uptime,
        prune_jsonl,
        render_dashboard,
        verify_keepalive,
    )

    config_path = args.config or (_COMPOSE_FILE.parent / "config.toml")
    config = _observability_config(config_path)
    log = ProbeLog(_probe_log_path())
    ledger = AlertLedger(_alert_ledger_path())
    prune_jsonl(log.path, config.retention())
    prune_jsonl(ledger.path, config.retention())
    records = log.read()
    budgets = compute_uptime(
        records, window_days=config.window_days, target_pct=config.uptime_target_pct
    )
    latest = {r.service: r for r in records}  # last write wins per service
    egress = build_report(EgressConfig.from_toml(config_path), args.usage_gb).as_json()
    keepalive = verify_keepalive(repo_root=_REPO_ROOT) if args.verify_keepalive else None
    text = render_dashboard(
        budgets=budgets,
        latest=latest,
        alerts=ledger.read(),
        egress=egress,
        keepalive=keepalive,
        window_days=config.window_days,
        target_pct=config.uptime_target_pct,
    )
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"dashboard written to {out}")
    else:
        print(text, end="")
    return 0


def _git_head() -> str:
    """The worktree's commit — recorded on the report's input identity."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _read_id_file(path: str | None) -> set[str]:
    """A newline-delimited claim-id file (targeted set / population selection)."""
    if not path:
        return set()
    return {
        ln.strip()
        for ln in Path(path).read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }


def _cmd_evidence_audit(args: argparse.Namespace) -> int:
    """``sig-ops evidence-audit`` — the offline read-only audit (P32.6)."""
    from . import evidence_audit as ea

    if args.input_json:
        units, watermark, eligible = ea.load_input_json(args.input_json)
        input_source = f"input-json:{args.input_json}"
    else:
        dsn = args.dsn or default_dsn()
        try:
            import psycopg  # lazy — only the live-read path needs the driver
        except ImportError:
            print("evidence-audit: psycopg unavailable", file=sys.stderr)
            return 2
        # The session is enforced read-only at the libpq level: the audit can
        # never mutate the spine, even through a code path bug.
        conn = psycopg.connect(dsn, options="-c default_transaction_read_only=on")
        from db.evidence_audit import load_audit_input

        ids = _read_id_file(args.claim_ids)
        load = load_audit_input(conn, claim_ids=sorted(ids) if ids else None)
        units = ea.units_from_rows(load.rows, load.marks, load.eligible_claim_ids)
        watermark = load.watermark
        input_source = "dsn(read-only)"
        if args.dump_input:
            from db.evidence_audit import dump_rows

            dump_rows(args.dump_input, load)
            print(f"evidence-audit: input rows dumped to {args.dump_input}")

    probe: ea.CaptureProbe
    if args.capture_dir:
        from evidence.ocfl import OcflStore
        from evidence.storage import LocalFileStore

        probe = ea.OcflCaptureProbe(
            OcflStore(LocalFileStore(str(args.capture_dir))),
            root_desc=str(args.capture_dir),
        )
    else:
        probe = ea.NULL_PROBE

    adjudications = None
    if args.adjudications:
        adjudications = {
            str(k): str(v)
            for k, v in json.loads(Path(args.adjudications).read_text(encoding="utf-8")).items()
        }

    report = ea.run_audit(
        units,
        probe,
        seed=str(args.seed),
        sample_size=int(args.sample),
        boundary=args.roll_boundary or ea.DEFAULT_ROLL_BOUNDARY,
        targeted_ids=_read_id_file(args.targeted),
        adjudications=adjudications,
        watermark=watermark,
        input_source=input_source,
        code_commit=_git_head(),
        generated_at=None,  # deterministic output; the run ledger records wall time
        byte_budget=args.byte_budget or ea.PILOT_BYTE_BUDGET,
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report.write(out / "audit_report.json")
    (out / "AUDIT_REPORT.md").write_text(ea.render_audit_markdown(report), encoding="utf-8")
    census = report.census
    print(
        "evidence-audit: "
        f"{census['claims']} claims, {len(report.strata)} strata, "
        f"{report.input['sampled']} sampled — "
        f"support_all={report.adjudication['support_all']}, "
        f"yield={report.adjudication['adjudication_yield']} "
        f"→ {out}/audit_report.json"
    )
    return 0


def _cmd_recovery_plan(args: argparse.Namespace) -> int:
    """``sig-ops recovery-plan`` — the dry-run-only recovery planner (P32.6)."""
    from . import recovery_plan as rp

    report = rp.load_report(args.audit)
    applied: set[str] = set()
    if args.applied:
        applied = _read_id_file(args.applied)
    repairs = None
    if args.repairs:
        repairs = json.loads(Path(args.repairs).read_text(encoding="utf-8"))
    plan = rp.build_recovery_plan(
        report,
        applied_digests=applied,
        repair_instructions=repairs,
        withhold_unverifiable_public=not args.no_withhold_unverifiable,
        free_storage_bytes=args.free_storage_bytes,
        generated_at=None,  # deterministic output
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plan.write(out / "recovery_plan.json")
    paths = rp.write_live_packet(plan, report, out)
    # The applier's resume file: the digests this plan proposed.
    (out / "plan_digests.txt").write_text("\n".join(rp.plan_digests(plan)) + "\n", encoding="utf-8")
    print(
        "recovery-plan: "
        f"{plan.totals['actions']} actions "
        f"({plan.totals['proposed']} proposed, {plan.totals['already_applied']} "
        f"already-applied, {plan.totals['deferred_ambiguous']} deferred-ambiguous, "
        f"{plan.totals['unrecoverable']} unrecoverable, "
        f"{plan.totals['restricted']} restricted, "
        f"{plan.totals['digest_mismatch']} digest-mismatch), "
        f"{plan.totals['batches']} batch(es) "
        f"→ {out}/recovery_plan.json + {paths['markdown'].name}"
    )
    return 0


def _cmd_recovery_apply(args: argparse.Namespace) -> int:
    """``sig-ops recovery-apply`` — the bounded apply (P32.22)."""
    from . import recovery_apply as ra

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))

    # --- reconcile + report the scope WITHOUT writing (the default) ---------
    selection = ra.select_actions(
        plan,
        batches=[b.strip() for b in (args.batches or "").split(",") if b.strip()] or None,
        kinds=[k.strip() for k in (args.kinds or "").split(",") if k.strip()] or None,
        claim_ids=sorted(_read_id_file(args.claims)) or None,
        max_actions=args.max_actions,
    )
    problems = ra.reconcile_apply(plan, audit, selection)
    if problems:
        for p in problems:
            print(f"recovery-apply: REFUSED — {p}", file=sys.stderr)
        return 3
    if not args.apply:
        print(
            "recovery-apply (dry reconcile): "
            f"{len(selection.actions)} proposed actions selected "
            f"({len(selection.excluded)} excluded by scope/status), "
            f"batches {list(selection.batches)} — re-run with --apply to execute"
        )
        return 0
    if not args.execution_id or not args.authority:
        print(
            "recovery-apply: --apply requires --execution-id and --authority "
            "(the operator authorization the receipts + dispositions record)",
            file=sys.stderr,
        )
        return 2

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print("recovery-apply: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("recovery-apply: psycopg unavailable", file=sys.stderr)
        return 2

    probe = None
    if args.capture_dir:
        from evidence.ocfl import OcflStore
        from evidence.storage import LocalFileStore

        from . import evidence_audit as ea

        probe = ea.OcflCaptureProbe(
            OcflStore(LocalFileStore(str(args.capture_dir))),
            root_desc=str(args.capture_dir),
        )

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        report = ra.execute_bounded_apply(
            conn,
            plan,
            audit,
            execution_id=str(args.execution_id),
            authority=str(args.authority),
            decided_by=args.decided_by,
            adjudicator=args.adjudicator,
            probe=probe,
            batches=[b.strip() for b in (args.batches or "").split(",") if b.strip()] or None,
            kinds=[k.strip() for k in (args.kinds or "").split(",") if k.strip()] or None,
            claim_ids=sorted(_read_id_file(args.claims)) or None,
            max_actions=args.max_actions,
            code_commit=_git_head(),
            role=args.role or None,
            verify_rerun=bool(args.verify_rerun),
            rematerialize=bool(args.rematerialize),
            generated_at=None,
        )
    except ra.ApplyScopeError as exc:
        print(f"recovery-apply: REFUSED — {exc}", file=sys.stderr)
        conn.rollback()
        conn.close()
        return 3
    if args.out:
        out = Path(args.out)
        paths = ra.write_report(report, out)
        shadow = ra.build_provisional_vs_shadow(code_commit=_git_head())
        (out / "PROVISIONAL_VS_SHADOW.json").write_text(
            json.dumps(shadow, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (out / "PROVISIONAL_VS_SHADOW.md").write_text(
            ra.render_shadow_markdown(shadow), encoding="utf-8"
        )
        ra.write_apply_return_pass(out, apply_report=report, snapshot=None)
        print(f"recovery-apply: report + packet written under {paths['report'].parent}")
    conn.commit()
    conn.close()
    counts = report["counts"]
    print(
        f"recovery-apply: {report['status']} — {counts.get('applied', 0)} applied, "
        f"{counts.get('conflict_existing', 0)} already-bound, "
        f"{counts.get('skipped', 0)} skipped, {len(report['failures'])} failed "
        f"(+0 rerun verified: {report.get('rerun', {}).get('plus_zero')})"
    )
    return 0 if report["status"] == "complete" else 3


def _cmd_recovery_freeze(args: argparse.Namespace) -> int:
    """``sig-ops recovery-freeze`` — the unpublished HUMAN-H4 snapshot frame."""
    from . import recovery_apply as ra

    apply_report = json.loads(Path(args.apply_report).read_text(encoding="utf-8"))
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print("recovery-freeze: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("recovery-freeze: psycopg unavailable", file=sys.stderr)
        return 2

    probe = None
    if args.capture_dir:
        from evidence.ocfl import OcflStore
        from evidence.storage import LocalFileStore

        from . import evidence_audit as ea

        probe = ea.OcflCaptureProbe(
            OcflStore(LocalFileStore(str(args.capture_dir))),
            root_desc=str(args.capture_dir),
        )

    adjudications = None
    if args.adjudications:
        adjudications = {
            str(k): str(v)
            for k, v in json.loads(Path(args.adjudications).read_text(encoding="utf-8")).items()
        }
    # The snapshot re-loads the audited population READ-ONLY.
    conn = psycopg.connect(dsn, options="-c default_transaction_read_only=on")
    snapshot = ra.freeze_snapshot(
        conn,
        apply_report=apply_report,
        plan=plan,
        audit=audit,
        probe=probe,
        seed=args.seed,
        sample_size=int(args.sample or 0),
        targeted_ids=_read_id_file(args.targeted),
        adjudications=adjudications,
        code_commit=_git_head(),
        sqitch_head=args.sqitch_head,
        out_dir=args.out,
    )
    conn.close()
    print(
        f"recovery-freeze: snapshot {snapshot['snapshot_digest'][:20]}… — "
        "frozen_unpublished, provisional preview (the HUMAN-H4 frame; "
        "P32.23a owns the release candidate)"
    )
    return 0


def _cmd_recovery_fixture_seed(args: argparse.Namespace) -> int:
    """``sig-ops recovery-fixture-seed`` — seed a deployed TEST spine from the
    committed P32.6 fixture packet (deterministic uuid5 mapping; idempotent)."""
    from . import recovery_fixture as rf

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print(
            "recovery-fixture-seed: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts",
            file=sys.stderr,
        )
        return 2
    try:
        import psycopg
    except ImportError:
        print("recovery-fixture-seed: psycopg unavailable", file=sys.stderr)
        return 2
    conn = psycopg.connect(dsn)
    try:
        id_map = rf.seed_fixture_spine(conn, args.fixture)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "id_map.json").write_text(
            json.dumps(id_map, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        rf.write_remapped_fixtures(id_map, out)
    print(
        f"recovery-fixture-seed: {len(id_map['claims'])} claims, "
        f"{len(id_map['captures'])} captures, {len(id_map['runs'])} runs seeded "
        f"from {args.fixture}"
    )
    return 0


def _cmd_release_candidate(args: argparse.Namespace) -> int:
    """``sig-ops release-candidate`` — the unpublished P32.23a candidate."""
    from . import release_candidate as rc

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8")) if args.plan else None
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8")) if args.audit else None
    apply_report = (
        json.loads(Path(args.apply_report).read_text(encoding="utf-8"))
        if args.apply_report
        else None
    )
    shadow = json.loads(Path(args.shadow).read_text(encoding="utf-8")) if args.shadow else None
    dossier_packets = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.dossier_packet]

    dsn = args.dsn or os.environ.get("SIG_STAGING_DSN") or _cloudsql_dsn_from_parts()
    if not dsn:
        print(
            "release-candidate: needs --dsn / SIG_STAGING_DSN / SIG_PG_* parts",
            file=sys.stderr,
        )
        return 2
    try:
        import psycopg
    except ImportError:
        print("release-candidate: psycopg unavailable", file=sys.stderr)
        return 2

    conn = psycopg.connect(dsn)
    try:
        manifest = rc.run_candidate(
            conn,
            snapshot=snapshot,
            out_dir=args.out,
            plan=plan,
            audit=audit,
            apply_report=apply_report,
            shadow_report=shadow,
            registry_dir=args.registry,
            as_of=args.as_of,
            role=args.role or None,
            dossier_packets=dossier_packets,
            code_commit=_git_head(),
            sqitch_head=args.sqitch_head,
            renderer_revision=_git_head(),
        )
        conn.commit()
    except rc.CandidateError as exc:
        conn.rollback()
        print(f"release-candidate: REFUSED [{exc.code}] {exc}", file=sys.stderr)
        return 3
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    c = manifest["candidate"]
    print(
        f"release-candidate: identity {str(c['identity_digest'])[:24]}… — "
        f"pub {manifest['release']['publication_id']} staged unpublished, "
        f"materialization +0={manifest['materialization']['plus_zero']}, "
        f"pointer unchanged={manifest['publication_pointer']['unchanged']} "
        f"({args.out})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `ops` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "up":
        return _cmd_up(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "down":
        return _cmd_down(args)
    if args.command == "seed":
        return _cmd_seed(args)
    if args.command == "dossier-packet":
        return _cmd_dossier_packet(args)
    if args.command == "dossier-packet-tulsa":
        return _cmd_dossier_packet_tulsa(args)
    if args.command == "dossier-packet-san-diego":
        return _cmd_dossier_packet_san_diego(args)
    if args.command == "seed-correct":
        return _cmd_seed_correct(args)
    if args.command == "egress-report":
        return _cmd_egress_report(args)
    if args.command == "swh-save":
        return _cmd_swh_save(args)
    if args.command == "degraded":
        return _cmd_degraded(args)
    if args.command == "deploy":
        return _cmd_deploy(args)
    if args.command == "publish-web":
        return _cmd_publish_web(args)
    if args.command == "republish-probe":
        return _cmd_republish_probe(args)
    if args.command == "backup-drill":
        return _cmd_backup_drill(args)
    if args.command == "cloudsql-drill":
        return _cmd_cloudsql_drill(args)
    if args.command == "keepalive-check":
        return _cmd_keepalive_check(args)
    if args.command == "probe":
        return _cmd_probe(args)
    if args.command == "probe-hosted":
        return _cmd_probe_hosted(args)
    if args.command == "probe-history":
        return _cmd_probe_history(args)
    if args.command == "scheduled-ingest":
        return _cmd_scheduled_ingest(args)
    if args.command == "replay-ingest":
        return _cmd_replay_ingest(args)
    if args.command == "cadence":
        return _cmd_cadence(args)
    if args.command == "backfill-run-completions":
        return _cmd_backfill_run_completions(args)
    if args.command == "sink-bench":
        return _cmd_sink_bench(args)
    if args.command == "roll-jobs":
        return _cmd_roll_jobs(args)
    if args.command == "alerts":
        return _cmd_alerts(args)
    if args.command == "alert":
        return _cmd_alert(args)
    if args.command == "monitoring-defs":
        return _cmd_monitoring_defs(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "evidence-audit":
        return _cmd_evidence_audit(args)
    if args.command == "recovery-plan":
        return _cmd_recovery_plan(args)
    if args.command == "recovery-apply":
        return _cmd_recovery_apply(args)
    if args.command == "recovery-freeze":
        return _cmd_recovery_freeze(args)
    if args.command == "recovery-fixture-seed":
        return _cmd_recovery_fixture_seed(args)
    if args.command == "release-candidate":
        return _cmd_release_candidate(args)
    if args.command == "release-serve":
        return _cmd_release_serve(args)
    if args.command == "renamed-routes":
        from . import renamed_routes

        argv_tail = ["--out", args.out]
        if getattr(args, "dry_run", False):
            argv_tail.append("--dry-run")
        return renamed_routes.main(argv_tail)
    if args.command == "journey-verify":
        return _cmd_journey_verify(args)
    if args.command == "journey-intake":
        return _cmd_journey_intake(args)
    if args.command == "release-publish":
        return _cmd_release_publish(args)
    if args.command == "composed-verify":
        return _cmd_composed_verify(args)
    parser.print_help()
    return 0


def _cmd_release_serve(args: argparse.Namespace) -> int:
    from . import release_serving

    if args.serve_command == "apply":
        return release_serving.main_apply(args.registry, args.staged)
    if args.serve_command == "check":
        return release_serving.main_check(args.registry, args.route)
    return 2


def _cmd_journey_verify(args: argparse.Namespace) -> int:
    from . import journey_verify

    portfolio = journey_verify.run_portfolio(
        candidate_dir=args.candidate,
        out_dir=args.out,
        intake_proof=args.intake_proof,
        renderer_revision=args.renderer,
    )
    summary = portfolio["summary"]
    counts = summary["counts"]
    print(
        f"sig-ops journey-verify: verdict={portfolio['verdict']} "
        f"(checks={summary['total']}: {counts['pass']} pass, "
        f"{counts['verified_by_test']} verified-by-test, "
        f"{counts['deferred']} deferred, {counts['not_applicable']} n/a, "
        f"{counts['fail']} fail)"
    )
    for check in portfolio["checks"]:
        if check["status"] == "fail":
            print(
                f"  FAIL {check['id']}: {check['detail']}\n"
                f"       owner={check['owner']} landing={check['landing']}"
            )
    return 0 if portfolio["verdict"] == "pass" else 1


def _cmd_release_publish(args: argparse.Namespace) -> int:
    from . import release_publish_verify

    proof = release_publish_verify.run(
        candidate_dir=args.candidate,
        out_dir=args.out,
        prior_export_dir=args.prior_export,
        gate_readout=args.gate_readout,
    )
    counts = proof["counts"]
    print(
        f"sig-ops release-publish: verdict={proof['verdict']} "
        f"(checks={proof['total_checks']}: {counts['pass']} pass, "
        f"{counts['fail']} fail, {counts['deferred']} deferred, "
        f"{counts['not_applicable']} n/a)"
    )
    for check in proof["checks"]:
        if check["status"] == "fail":
            print(
                f"  FAIL {check['id']}: {check['detail']}\n"
                f"       owner={check['owner']} landing={check['landing']}"
            )
    return 0 if proof["verdict"] == "pass" else 1


def _cmd_composed_verify(args: argparse.Namespace) -> int:
    from . import composed_verify

    try:
        proof = composed_verify.run_composed_verification(
            args.dsn or default_dsn(),
            out_dir=args.out,
            renderer_revision=args.renderer,
        )
    except Exception as exc:  # noqa: BLE001 - an unusable DSN fails LOUD
        print(
            f"sig-ops composed-verify: UNAVAILABLE — {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return 1
    n_checks = sum(len(leg["checks"]) for leg in proof["legs"])
    n_ok = sum(1 for leg in proof["legs"] for c in leg["checks"] if c["ok"])
    print(
        f"sig-ops composed-verify: verdict={proof['verdict']} "
        f"({n_ok}/{n_checks} checks) publication={proof['release'].get('publication_id')}"
    )
    for leg in proof["legs"]:
        for c in leg["checks"]:
            if not c["ok"]:
                print(f"  FAIL {leg['leg']}::{c['check']}: {c['detail']}", file=sys.stderr)
    return 0 if proof["verdict"] == "pass" else 1


def _cmd_journey_intake(args: argparse.Namespace) -> int:
    from . import journey_verify

    if not args.publication:
        print("journey-intake: --publication is required (the cited release id)", file=sys.stderr)
        return 2
    proof = journey_verify.run_intake_journey(
        dsn=args.dsn or default_dsn(),
        publication_id=args.publication,
        record_key_value=args.record,
        report_key=args.key,
    )
    body = json.dumps(proof, indent=2, sort_keys=True, default=str)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body + "\n")
        print(f"sig-ops journey-intake: proof at {out}")
    else:
        print(body)
    failed = [s for s in proof["steps"] if not s.get("ok")]
    for step in failed:
        print(f"  FAIL {step['step']}: {step['detail']}", file=sys.stderr)
    return 0 if not failed else 1
