# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Composed end-to-end verification of the whole SIG build (P19.3, CAPSTONE step 3).

For the first time the build is driven as **one unit**: the PG18+PostGIS claim
spine (real ``db/sqitch.plan``) → OCFL evidence store → connector replay over
committed fixtures → entity resolution → the reconciliation resolver → the read
API → exports → the ``web/`` build.  One ordered test per seam (S1…S8) shares the
session fixtures in ``conftest.py``.

**Never fabricate green (orchestrate-build §3.1).**  A seam that *exists but has
never been wired together* is recorded as an ``xfail`` whose reason begins with
its ``LEDGER_DEFERRALS`` id (``^LD-[A-Z]+[0-9]+[a-z]?:``) — never a loosened or
removed assertion.  P19.4 crosses the two claim-spine seams (S3 ``LD-F06b`` and S6
``LD-F06``); the ER seam (``LD-F04``) moves to P19.5 per that ticket's size guard,
and web rendering (``LD-V08``) is P21.4:

* S3 ``LD-F06b`` — CROSSED (P19.4): connector claims persist to PG via ``PgClaimSink``.
* S4 ``LD-F04``  — CROSSED (P19.5): ER matches + review decisions persist to PG via
  ``sig-resolution match/review`` over ``review_item`` / ``review_decision``.
* S6 ``LD-F06``  — CROSSED (P19.4): the API reads the spine via ``PgReadStore``.
* S8 ``LD-V08``  — CROSSED (P21.4): ``web/`` builds from the export bytes via
  ``web/src/lib/data.ts`` (``SIG_DATA_SOURCE=export``); the OKC dossier renders the
  299-vs-190 contradiction from the jurisdiction export, not the TS fixtures.

Docker gating mirrors ``tests/db/conftest.py``: without a daemon the module
**skips**; with ``SIG_REQUIRE_DB_TESTS=1`` a missing daemon is a hard failure.
S8 adds the same "skip when the required environment is absent" gate for the
``web/`` build (P20.4): without ``npm`` / ``web/node_modules`` the ``web_build``
fixture **skips cleanly** (the web build is covered by the CI ``web`` job), and
where the env is present it runs unchanged into the ``LD-V08`` xfail.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _docker_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


# Module-level gate: without Docker and without the CI opt-in, skip cleanly. With
# SIG_REQUIRE_DB_TESTS set, collection proceeds and the composed_db fixture turns
# an unreachable daemon into a hard failure (never a silent no-op).
if not _docker_reachable() and not os.environ.get("SIG_REQUIRE_DB_TESTS"):
    pytest.skip(
        "Docker daemon not reachable; composed stack tests skip (P19.3)",
        allow_module_level=True,
    )


# --- shared connector-run scaffolding ----------------------------------------

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_ATLAS_FIX = REPO_ROOT / "tests" / "connectors" / "fixtures" / "atlas"
_OSM_FIX = REPO_ROOT / "tests" / "connectors" / "fixtures" / "osm"
_OKC_FIXTURE = REPO_ROOT / "tests" / "acceptance" / "fixtures" / "okc_sources.json"


class _StaticTransport:
    """Serves one document's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes, media_type: str) -> None:
        self._body = body
        self._media_type = media_type
        self.user_agents: list[str] = []

    def robots(self, robots_url: str) -> Any:
        from connectors.net import RobotsResult

        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> Any:
        from connectors.net import FetchResult

        self.user_agents.append(user_agent)
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type=self._media_type,
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


@dataclasses.dataclass
class _ConnectorRun:
    name: str
    live_claims: list[dict[str, Any]]
    sink_claims: list[Mapping[str, Any]]
    replay_claims: list[dict[str, Any]]
    replay_reproducible: bool
    n_captures: int


def _run_connector(
    connector: Any,
    source_id: str,
    fixture: Path,
    *,
    media_type: str,
    kind: str,
) -> _ConnectorRun:
    """Drive one connector end-to-end over a committed fixture, then replay it."""
    from connectors.net import PoliteFetcher
    from connectors.pipeline import run
    from connectors.registry import get
    from connectors.replay import replay, replay_fingerprint
    from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    transport = _StaticTransport(fixture.read_bytes(), media_type)
    fetcher = PoliteFetcher(
        connector_name=connector.name, connector_version="1.0.0", transport=transport
    )
    # A reviewer flips the seed row to permitted to run, exactly as the unit
    # tests do (the seed stays ingestion_permitted=false; SIG-INGEST-028).
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    sink = InMemoryClaimSink()
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=sink,
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": kind}]},
    )
    report = run(connector, ctx)
    replay_a = replay(connector, ctx, report.captures)
    replay_b = replay(connector, ctx, report.captures)
    return _ConnectorRun(
        name=connector.name,
        live_claims=report.claims,
        sink_claims=list(sink.claims),
        replay_claims=replay_a,
        replay_reproducible=replay_fingerprint(replay_a) == replay_fingerprint(replay_b),
        n_captures=len(report.captures),
    )


# --- S2 fixture: OCFL evidence capture ----------------------------------------


@dataclasses.dataclass
class _OcflResult:
    store: Any
    object_ids: list[str]
    round_trip_ok: bool


@pytest.fixture(scope="session")
def ocfl_capture(tmp_path_factory: pytest.TempPathFactory) -> _OcflResult:
    """S2: capture the 10 OKC fixture artifacts as OCFL evidence objects."""
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    root = tmp_path_factory.mktemp("ocfl_root")
    store = OcflStore(LocalFileStore(str(root)))
    artifacts = json.loads(_OKC_FIXTURE.read_text())["artifacts"]
    object_ids: list[str] = []
    round_trip_ok = True
    for art in artifacts:
        object_id = f"sig:evidence:{art['artifact_id']}"
        payload = json.dumps(art, sort_keys=True, ensure_ascii=False).encode("utf-8")
        store.add_version(object_id, {"artifact.json": payload}, message="okc capture")
        object_ids.append(object_id)
        # Resolve version → digest → content path → bytes (OCFL, without SIG code).
        if store.resolve(object_id, "v1", "artifact.json") != payload:
            round_trip_ok = False
    return _OcflResult(store=store, object_ids=object_ids, round_trip_ok=round_trip_ok)


# --- S3 fixture: connector replay over committed fixtures ---------------------


@pytest.fixture(scope="session")
def connector_replay() -> dict[str, _ConnectorRun]:
    """S3: run + replay the atlas and osm connectors over their committed fixtures."""
    from connectors.atlas import ATLAS_SOURCE_ID, AtlasConnector
    from connectors.osm import OSM_SOURCE_ID, OSMConnector

    return {
        "atlas": _run_connector(
            AtlasConnector(),
            ATLAS_SOURCE_ID,
            _ATLAS_FIX / "adoption_feed.csv",
            media_type="text/csv",
            kind="bulk_csv",
        ),
        "osm": _run_connector(
            OSMConnector(),
            OSM_SOURCE_ID,
            _OSM_FIX / "overpass_snapshot.json",
            media_type="application/json",
            kind="overpass",
        ),
    }


# --- S6 fixture: a live API server over the in-memory ReadStore ---------------


@dataclasses.dataclass
class _ApiServer:
    base_url: str
    store: Any


@pytest.fixture(scope="session")
def api_server() -> Iterator[_ApiServer]:
    """S6: serve the read API with a real uvicorn process and hit it over HTTP."""
    import uvicorn
    from api.demo import build_demo_store

    from api import create_app

    store = build_demo_store()
    app = create_app(store)

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 30
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("uvicorn server did not start within 30s")
    sock = server.servers[0].sockets[0]
    port = sock.getsockname()[1]
    try:
        yield _ApiServer(base_url=f"http://127.0.0.1:{port}", store=store)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


# --- S7 fixture: an exports release built by the sig-exports CLI --------------

_EXPORT_REQUEST = {
    "build_spec": {
        "as_of_snapshot": "2026-06-30",
        "as_of_belief": "2026-06-30",
        "ruleset_version": "ruleset/1",
        "resolver_version": "resolver/1",
    },
    "rights": [
        {
            "source_id": "osm",
            "spdx": "ODbL-1.0",
            "attribution": "© OSM",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "u",
            "retrieval_date": "2026-01-01",
        },
        {
            "source_id": "sig",
            "spdx": "CC-BY-4.0",
            "attribution": "© SIG",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "u",
            "retrieval_date": "2026-01-01",
        },
    ],
    "tables": [
        {
            "name": "devices",
            "kind": "geo",
            "compartment": "osm_physical",
            "rows": [
                {
                    "source_id": "osm",
                    "data": {
                        "subject_id": "d1",
                        "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    },
                }
            ],
        },
        {
            "name": "claims",
            "kind": "tabular",
            "rows": [{"source_id": "sig", "data": {"subject_id": "e1"}}],
        },
    ],
}


@dataclasses.dataclass
class _ExportRelease:
    out_dir: Path
    summary: dict[str, Any]
    returncode: int


@pytest.fixture(scope="session")
def exports_release(tmp_path_factory: pytest.TempPathFactory) -> _ExportRelease:
    """S7: drive `sig-exports build --zenodo-dry-run` as a real subprocess."""
    work = tmp_path_factory.mktemp("exports")
    request = work / "request.json"
    request.write_text(json.dumps(_EXPORT_REQUEST), encoding="utf-8")
    out = work / "release"
    proc = subprocess.run(
        [
            "sig-exports",
            "build",
            str(request),
            "--out",
            str(out),
            "--zenodo-dry-run",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    summary: dict[str, Any] = {}
    if proc.returncode == 0 and proc.stdout.strip():
        summary = json.loads(proc.stdout)
    return _ExportRelease(out_dir=out, summary=summary, returncode=proc.returncode)


# --- S8 fixture: the web/ static build ----------------------------------------


@dataclasses.dataclass
class _WebBuild:
    dist: Path
    returncode: int
    data_source: str


def _require_web_env() -> Path:
    web_dir = REPO_ROOT / "web"
    if shutil.which("npm") is None or not (web_dir / "node_modules").exists():
        pytest.skip(
            "web build environment unavailable (no npm / web/node_modules); the web "
            "build is covered by the CI `web` job"
        )
    return web_dir


@pytest.fixture(scope="session")
def web_build() -> _WebBuild:
    """S8 (fixtures mode): build the Astro `web/` site with `npm run build`.

    Gated on a usable web-build environment, mirroring the Docker
    ``_require_or_skip`` pattern this module already uses (``tests/db/conftest.py``,
    ``tests/e2e/conftest.py``). The CI ``python`` job runs the whole pytest suite
    (``tests/e2e`` included) but installs no Node / ``web/node_modules`` — only the
    CI ``web`` job does. Without that environment ``npm run build`` cannot run, so
    S8 **skips cleanly** here rather than failing (rc 127). Fixtures mode is the CI
    default (``SIG_DATA_SOURCE=fixtures``), so this build is unchanged.
    """
    web_dir = _require_web_env()
    proc = subprocess.run(
        ["npm", "--prefix", str(web_dir), "run", "build"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "SIG_DATA_SOURCE": "fixtures"},
    )
    return _WebBuild(dist=web_dir / "dist", returncode=proc.returncode, data_source="fixtures")


@pytest.fixture(scope="session")
def web_build_from_export(tmp_path_factory: pytest.TempPathFactory) -> _WebBuild:
    """S8 (export mode, LD-V08 CROSSED, P21.4): build `web/` FROM the export bytes.

    First build the fixture-backed jurisdiction export with ``sig-exports build
    --jurisdiction okc`` (no green sources on this build → the committed slice, not
    a live fetch; network-isolated), which emits ``web/dossiers.json`` (the `/v1`
    dossier contract) alongside the ODbL/CC-BY compartments. Then build the static
    site with ``SIG_DATA_SOURCE=export`` pointed at that export dir, so the dossier
    route renders from the EXPORT bytes rather than the committed TS fixtures — the
    seam ``LD-V08`` recorded as never-wired. ``web/src/lib/data.ts`` is the switch.
    """
    web_dir = _require_web_env()
    export_dir = tmp_path_factory.mktemp("okc_export")
    built = subprocess.run(
        ["sig-exports", "build", "--jurisdiction", "okc", "--out", str(export_dir)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert built.returncode == 0, f"sig-exports build --jurisdiction okc failed: {built.stderr}"
    assert (export_dir / "web" / "dossiers.json").exists(), "export must emit web/dossiers.json"
    proc = subprocess.run(
        ["npm", "--prefix", str(web_dir), "run", "build"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "SIG_DATA_SOURCE": "export",
            "SIG_EXPORT_DIR": str(export_dir),
        },
    )
    return _WebBuild(dist=web_dir / "dist", returncode=proc.returncode, data_source="export")


# =============================================================================
# S1 — claim spine: deploy db/sqitch.plan into a fresh PG18+PostGIS container
# =============================================================================


def test_s1_claim_spine_sqitch_deploy_and_append_only(composed_conn: Any) -> None:
    import psycopg
    from conftest import insert_claim, seed_claim_prerequisites  # tests/e2e/conftest

    # The sqitch plan landed the spine: the core tables are present.
    expected = {
        "claim",
        "entity",
        "evidence_artifact",
        "evidence_capture",
        "resolution",
        "contradiction",
        "coverage_record",
        "research_task",
    }
    present = {
        r[0]
        for r in composed_conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ).fetchall()
    }
    assert expected <= present, f"missing spine tables: {sorted(expected - present)}"

    # PostGIS is installed (§48 requires the geospatial extension).
    postgis = composed_conn.execute("SELECT postgis_version()").fetchone()[0]
    assert postgis

    # Append-only preserved through the composed DB path (P1–P3, SIG-STORE-011):
    # a value UPDATE on `claim` is rejected as immutable, exactly as tests/db asserts.
    prereqs = seed_claim_prerequisites(composed_conn)
    insert_claim(composed_conn, prereqs)
    with pytest.raises(psycopg.Error) as excinfo:
        with composed_conn.transaction():
            composed_conn.execute("UPDATE claim SET value_text = '999'")
    assert "immutable" in str(excinfo.value)
    with pytest.raises(psycopg.Error) as excinfo:
        with composed_conn.transaction():
            composed_conn.execute("DELETE FROM claim")
    assert "DELETE forbidden" in str(excinfo.value)


# =============================================================================
# S2 — evidence store: OcflStore captures the 10 OKC fixture artifacts
# =============================================================================


def test_s2_ocfl_evidence_capture(ocfl_capture: _OcflResult) -> None:
    assert len(ocfl_capture.object_ids) == 10
    assert ocfl_capture.round_trip_ok, "every OCFL object must resolve back to its bytes"
    # Every object is a conformant OCFL 1.1 object with a readable inventory.
    for object_id in ocfl_capture.object_ids:
        assert ocfl_capture.store.object_exists(object_id)
        inventory = ocfl_capture.store.read_inventory(object_id)
        assert inventory["id"] == object_id
        assert inventory["head"] == "v1"
        assert inventory["digestAlgorithm"] == "sha512"


# =============================================================================
# S3 — connector → claim spine: replay atlas + osm over committed fixtures
# =============================================================================


def test_s3_connector_replay_to_claim_sink(
    connector_replay: dict[str, _ConnectorRun], composed_db: dict[str, object]
) -> None:
    import psycopg
    from db.claim_sink import PgClaimSink

    for name in ("atlas", "osm"):
        run = connector_replay[name]
        # Crossed: the live run asserted claims into the in-memory sink, and the
        # network-isolated replay reproduces the same claim set byte-for-byte
        # (SIG-INGEST-003/017/018).
        assert run.n_captures >= 1, f"{name}: expected at least one capture"
        assert run.sink_claims, f"{name}: live run asserted no claims"
        assert run.replay_claims, f"{name}: replay produced no claims"
        assert run.replay_reproducible, f"{name}: replay is not reproducible"

    # Seam CROSSED (P19.4, LD-F06b): the atlas + osm claim sets are now persisted to
    # the PG `claim` spine through db.claim_sink.PgClaimSink — L0 evidence + L2
    # identity + L1 claims, append-only, recorded_at set by the DB. Replaying the
    # same run is idempotent (content-digest ON CONFLICT), so N>0 the first time and
    # 0 new rows the second.
    dsn = (
        f"postgresql://{composed_db['user']}:{composed_db['password']}"
        f"@{composed_db['host']}:{composed_db['port']}/{composed_db['dbname']}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        before = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest IS NOT NULL"
        ).fetchone()[0]
    for name in ("atlas", "osm"):
        sink = PgClaimSink.from_dsn(
            dsn, connector_name=name, connector_version="1.0.0", code_commit="p19.3-composed"
        )
        sink.assert_claims(connector_replay[name].sink_claims)
        assert sink.report.inserted > 0, f"{name}: no claims were written to the PG spine"
        # Idempotent replay of the identical run inserts nothing new.
        replay_sink = PgClaimSink.from_dsn(
            dsn, connector_name=name, connector_version="1.0.0", code_commit="p19.3-composed"
        )
        replay_sink.assert_claims(connector_replay[name].sink_claims)
        assert replay_sink.report.inserted == 0, f"{name}: replay must be idempotent"
    with psycopg.connect(dsn, autocommit=True) as conn:
        after = conn.execute(
            "SELECT count(*) FROM claim WHERE content_digest IS NOT NULL"
        ).fetchone()[0]
    assert after > before, "connector claims must land in the PG claim table"


# =============================================================================
# S4 — entity resolution: ProbabilisticMatcher.match + ReviewQueue round-trip
# =============================================================================

_ER_RECORDS = [
    {
        "unique_id": "okcpd-1",
        "normalized_name": "oklahoma city police department",
        "name_first_token": "oklahoma",
        "state": "OK",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "okcpd-2",
        "normalized_name": "oklahoma city police dept",
        "name_first_token": "oklahoma",
        "state": "OK",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "tcso-1",
        "normalized_name": "tulsa county sheriff office",
        "name_first_token": "tulsa",
        "state": "OK",
        "organization_class": "us.le.sheriff",
    },
]


def test_s4_probabilistic_er_and_review_round_trip(composed_db: dict[str, object]) -> None:
    import psycopg
    from resolution.cli import main as resolution_main
    from resolution.review_pg import PgReviewQueue

    dsn = (
        f"postgresql://{composed_db['user']}:{composed_db['password']}"
        f"@{composed_db['host']}:{composed_db['port']}/{composed_db['dbname']}"
    )

    # Seam CROSSED (P19.5, LD-F04): the near-duplicate OKCPD organisations live in
    # the PG spine as `organization` projections; the matcher reads them from PG,
    # scores the pair, and persists the tier-4/5 PROPOSED proposals + the human
    # review decision to the append-only `review_item` / `review_decision` tables.
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE review_decision, review_item CASCADE")
        for subject, canonical, org_type in (
            ("okc:okcpd-1", "Oklahoma City Police Department", "us.le.municipal_police"),
            ("okc:okcpd-2", "Oklahoma City Police Dept", "us.le.municipal_police"),
            ("okc:tcso-1", "Tulsa County Sheriff Office", "us.le.sheriff"),
        ):
            existing = conn.execute(
                "SELECT entity_id FROM entity_identifier "
                "WHERE scheme = 'sig.connector.subject' AND value = %s",
                (subject,),
            ).fetchone()
            if existing is None:
                entity_id = conn.execute(
                    "INSERT INTO entity(entity_type) VALUES ('organization') RETURNING entity_id"
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s)",
                    (entity_id, "sig.connector.subject", subject),
                )
                conn.execute(
                    "INSERT INTO entity_identifier(entity_id, scheme, value) VALUES (%s, %s, %s)",
                    (entity_id, "us.state", "OK"),
                )
            else:
                entity_id = existing[0]
            conn.execute(
                "INSERT INTO organization(entity_id, organization_type, cached_canonical_name) "
                "VALUES (%s, %s, %s) ON CONFLICT (entity_id) "
                "DO UPDATE SET cached_canonical_name = EXCLUDED.cached_canonical_name",
                (entity_id, org_type, canonical),
            )

    # Crossed: `sig-resolution match --dsn … --jurisdiction okc` scores the PG
    # candidates and enqueues the tier-4/5 PROPOSED proposals (never auto-writes,
    # SIG-IDENT-020).
    assert resolution_main(["match", "--dsn", dsn, "--jurisdiction", "okc"]) == 0
    queue = PgReviewQueue.from_dsn(dsn)
    pending = queue.pending()
    assert pending, "the OKCPD near-duplicate pair should be scored and enqueued to PG"

    # Crossed: a curator's accept/reject appends an append-only `review_decision`
    # row recording the human reviewer (SIG-IDENT-026, P1–P3). Deciding the same
    # item again appends a second row — a decision history, never an edit.
    item_id = pending[0].item_id
    decision = queue.decide(item_id, "accept", reviewer="curator:okc")
    assert decision.accepted and decision.reviewer == "curator:okc"
    queue.decide(item_id, "reject", reviewer="curator:okc")
    with psycopg.connect(dsn, autocommit=True) as conn:
        n = conn.execute(
            "SELECT count(*) FROM review_decision WHERE item_id = %s", (item_id,)
        ).fetchone()[0]
    assert n == 2, "each decide call appends exactly one append-only review_decision row"


# =============================================================================
# S5 — resolver: RESOLVE keeps the 299-vs-190 claimed_device_count contradiction
#      VISIBLE, not collapsed to one number (P06.1 retrospective, §3.1)
# =============================================================================


def test_s5_resolver_keeps_contradiction_visible() -> None:
    from reconcile.model import Evidence
    from reconcile.resolve import RESOLVE, Claim

    subject = "sig:deployment:okc-okcpd-flock"
    predicate = "claimed_device_count"

    def _ev(family: str) -> Evidence:
        return Evidence(
            source_id=f"src:{family}",
            source_family=family,
            artifact_type=family,
            stable_locator=f"https://example/{family}",
            capture_digest="b" + "0" * 40,
            locator={"selector": "#v", "text_span": [0, 3]},
            excerpt="…",
        )

    def _claim(cid: str, value: int, observed: date) -> Claim:
        return Claim(
            claim_id=cid,
            subject_id=subject,
            predicate_id=predicate,
            value=value,
            reliability="R2",
            integrity="I1",
            genre="news_article",
            observed_at=observed,
            raw_value=str(value),
            source_id=f"src:{cid}",
            count_basis="claimed",
            evidence=_ev(cid),
        )

    # DeFlock ~299 vs Chief Bacy ~190 (the P06.1 slice's within-predicate
    # disagreement, tests/acceptance/okc_slice.py).
    deflock = _claim("deflock", 299, date(2026, 8, 20))
    bacy = _claim("bacy", 190, date(2026, 8, 18))
    resolved = RESOLVE(
        subject,
        predicate,
        [deflock, bacy],
        as_of_world=date(2026, 9, 1),
        as_of_belief=date(2026, 9, 1),
    )

    # The contradiction stays VISIBLE: the resolver does NOT collapse it to a
    # single number — it emits UNRESOLVED/CONTESTED with both claims retained.
    assert resolved.resolution_status == "UNRESOLVED"
    assert resolved.value is None, "a contested value must not be collapsed to one number"
    assert resolved.contradiction_state == "unresolved_conflict"
    assert resolved.agreement == "CONTESTED"
    assert set(resolved.considered_claim_ids) == {"deflock", "bacy"}
    # Both underlying values remain reachable from the record (no synthetic certainty).
    assert {deflock.value, bacy.value} == {299, 190}


# =============================================================================
# S6 — API: create_app(store) served live; every §37.3 family returns 200
# =============================================================================


def test_s6_api_serves_resolution_envelope_and_families(
    api_server: _ApiServer, composed_db: dict[str, object]
) -> None:
    import httpx

    subject = "agency:okcpd"
    predicate = "active_device_count"
    with httpx.Client(base_url=api_server.base_url, timeout=10.0) as client:
        # Crossed: the API serves the full resolution envelope (SIG-API-002/005).
        r = client.get(f"/v1/resolution/{subject}/{predicate}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert {"fact", "coverage", "attribution", "as_of"} <= set(body)

        # Crossed: every §37.3 resource family answers 200 with an envelope.
        for path in (
            "/v1/dossier/jurisdiction:okc",
            "/v1/coverage/agency:okcpd",
            "/v1/contradiction",
            "/v1/contradiction/contradiction:okcpd-count",
            "/v1/task",
            "/v1/task/task:okcpd-count",
            "/id/agency/okcpd",
        ):
            resp = client.get(path)
            assert resp.status_code == 200, f"{path}: {resp.status_code} {resp.text}"

    # Seam CROSSED (P19.4, LD-F06): the same hand-written app now serves over the PG
    # claim spine through api.store_pg.PgReadStore. create_app(store) is unchanged;
    # the store reads the claims S3 persisted (belief-time as-of, RLS enabled,
    # publication applied at the store boundary) and the resolver keeps any
    # within-predicate disagreement visible.
    from api.store_pg import PgReadStore
    from starlette.testclient import TestClient

    from api import create_app

    # Build the DSN from the composed DB the connector run (S3) populated.
    dsn = (
        f"postgresql://{composed_db['user']}:{composed_db['password']}"
        f"@{composed_db['host']}:{composed_db['port']}/{composed_db['dbname']}"
    )
    pg_store = PgReadStore(dsn)
    try:
        with TestClient(create_app(pg_store)) as pg_client:
            # A subject + predicate that S3 wrote to the spine.
            row = pg_store._conn.execute(  # noqa: SLF001 - test reaches into the store conn
                "SELECT subject_id, predicate_id FROM claim "
                "WHERE content_digest IS NOT NULL LIMIT 1"
            ).fetchone()
            assert row is not None, "S3 must have written claims the API can read"
            subject_id, predicate_id = str(row[0]), str(row[1])
            for path in (
                f"/v1/resolution/{subject_id}/{predicate_id}",
                f"/v1/entity/deployment/{subject_id}",
                "/v1/contradiction",
                "/v1/task",
                "/v1/crosswalk",
                "/v1/changes",
            ):
                resp = pg_client.get(path)
                assert resp.status_code == 200, f"PG {path}: {resp.status_code} {resp.text[:200]}"
                assert "as_of" in resp.json(), f"PG {path}: not an as-of envelope"
    finally:
        pg_store.close()


# =============================================================================
# S7 — exports: sig-exports build --zenodo-dry-run; licence split + PMTiles
# =============================================================================


def test_s7_exports_build_licence_split_and_pmtiles(exports_release: _ExportRelease) -> None:
    assert exports_release.returncode == 0, "sig-exports build must exit 0"
    out = exports_release.out_dir
    assert (out / "manifest.json").exists()

    # Licence compartment split: the ODbL geo compartment is written separately
    # from the CC-BY graph compartment (SIG-LIC-004a / SIG-EXPORT-*).
    assert (out / "osm_physical" / "devices.pmtiles").exists(), "PMTiles archive present"
    assert (out / "sig_graph" / "claims.parquet").exists()

    licenses = set(exports_release.summary.get("licenses", []))
    assert {"ODbL-1.0", "CC-BY-4.0"} <= licenses, f"both licences present: {licenses}"
    # The dry-run Zenodo deposit split concept vs version DOI (SIG-EXPORT-002).
    zenodo = exports_release.summary.get("zenodo", {})
    assert zenodo.get("concept_doi", "").startswith("10.5281/zenodo.")
    assert zenodo.get("version_doi") != zenodo.get("concept_doi")


# =============================================================================
# S8 — web: npm --prefix web run build; the dossier route is emitted
# =============================================================================


def test_s8_web_build_emits_dossier_route(web_build: _WebBuild) -> None:
    assert web_build.returncode == 0, "npm run build must exit 0"
    # The static build emits the dossier route for the slice jurisdiction (fixtures
    # mode — the CI default, SIG_DATA_SOURCE=fixtures, unchanged).
    dossier_html = web_build.dist / "dossier" / "oklahoma-city" / "index.html"
    assert dossier_html.exists(), "the OKC dossier route must be in web/dist"
    assert b"Oklahoma City" in dossier_html.read_bytes()


def test_s8_web_build_renders_from_export_bytes(web_build_from_export: _WebBuild) -> None:
    """S8 LD-V08 CROSSED (P21.4): the dossier renders from the EXPORT, not fixtures.

    Building with ``SIG_DATA_SOURCE=export`` over the jurisdiction export's
    ``web/dossiers.json``, the OKC dossier page carries the defining-standard
    contradiction (§3.1): the 299-vs-190 ``claimed_device_count`` disagreement with
    BOTH sources and dates — a value the committed TS fixtures do NOT contain, so
    its presence proves the page was rendered from the export bytes.
    """
    assert web_build_from_export.returncode == 0, "SIG_DATA_SOURCE=export build must exit 0"
    dossier_html = web_build_from_export.dist / "dossier" / "oklahoma-city" / "index.html"
    assert dossier_html.exists(), "the OKC dossier route must be built from the export"
    html = dossier_html.read_text(encoding="utf-8")

    # The contradiction is on the page, both values retained (never collapsed).
    assert "299" in html, "DeFlock's ~299 claim must be on the export-built dossier"
    assert "190" in html, "Chief Bacy's ~190 claim must be on the export-built dossier"
    assert "Claimed device count" in html, "the claimed-count figure must render"
    # Both sources and both dates — every number links claim → evidence (§3.1).
    assert "DeFlock" in html and "Bacy" in html, "both competing sources must be shown"
    assert "2026-08-20" in html and "2026-08-18" in html, "both claim dates must be shown"
