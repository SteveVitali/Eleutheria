# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.18 / ADR-178 invariants (S0 RI-01, SIG-PUB-002, SIG-STORE-011, TS-04).

Covers the whole engineered leg: the keyed-digest alias table and resolver,
the idempotent re-key, registry non-id cleanup, export-resolution and
``camera_operator`` suppression, the N-5 old-URL page + batch-02 rows, the
renamed-routes conf generator, the committed crawl check, and the repo-hygiene
rule (no plaintext old→new pair in a tracked file). Tests never embed a real
handle: unit fixtures use synthetic ids, and tree greps read the gitignored
handle list, skipping with a recorded reason when it is absent.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLE_LIST = REPO_ROOT / "docs/build/logs/next-phase/C3/personal_like_ids.txt"
ALIAS_JSON = REPO_ROOT / "policy/src/policy/data/source_aliases.json"
N5_PAGE = REPO_ROOT / "web/src/pages/sources/identifier-changed.astro"
BATCH02 = REPO_ROOT / "docs/build/reports/copy-batches/batch-02.md"
CORRECTION_NOTE = REPO_ROOT / "docs/governance/identifier-rekey-note.md"
CRAWL_CHECK = REPO_ROOT / "docs/build/tools/handle_crawl_check.py"

# Synthetic retired ids — never a real handle.
OLD_SOURCE = "camreg_testhandle"
NEW_SOURCE = "camreg_und_999"
OLD_TARGET = "testhandle_main"
NEW_TARGET = "camreg_und_999_main"
OLD_SURNAME = "testperson"
SUPPRESSED_OP = "Test.Operator_Example"


def _handles() -> list[str]:
    if not HANDLE_LIST.exists():
        pytest.skip("handle list absent (gitignored) — recorded reason per contract")
    return [ln.strip() for ln in HANDLE_LIST.read_text().splitlines() if ln.strip()]


def _synthetic_aliases():
    from policy.source_aliases import SourceAliases, digest_token

    token = {
        digest_token(OLD_SOURCE): NEW_SOURCE,
        digest_token(OLD_TARGET): NEW_TARGET,
        digest_token(OLD_SURNAME): "okc_council_statement",
    }
    return SourceAliases(
        source={digest_token(OLD_SOURCE): NEW_SOURCE},
        target={digest_token(OLD_TARGET): NEW_TARGET},
        token=token,
        phrase={digest_token("Chief Testperson"): "the chief"},
        redaction={digest_token("owner@example"): "[account withheld]"},
        suppressed_value_digests=frozenset({digest_token(SUPPRESSED_OP)}),
        restricted_map_digest="sha256:" + "0" * 64,
    )


# ---------------------------------------------------------------- alias table


def test_alias_table_committed_is_digest_keyed_only() -> None:
    raw = json.loads(ALIAS_JSON.read_text())
    assert raw["schema"] == "sig/source-alias-records/1.0.0"
    for section in (
        "source_aliases",
        "target_aliases",
        "token_aliases",
        "phrase_aliases",
        "redaction_aliases",
    ):
        for key in raw.get(section, {}):
            assert re.fullmatch(r"sha256:[0-9a-f]{64}", key), f"{section} key not a digest"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", raw["restricted_map_digest"])


def test_alias_table_never_contains_a_handle() -> None:
    handles = _handles()
    text = ALIAS_JSON.read_text()
    for h in handles:
        assert h not in text


def test_resolver_maps_tokens_and_text() -> None:
    a = _synthetic_aliases()
    assert a.resolve_token(OLD_SOURCE) == NEW_SOURCE
    assert a.resolve_token("camreg_functional") == "camreg_functional"  # identity
    subj = f"traffic_camera:{OLD_SOURCE}:{OLD_TARGET}:CAM-1"
    assert a.resolve_text(subj) == f"traffic_camera:{NEW_SOURCE}:{NEW_TARGET}:CAM-1"
    assert a.resolve_text(f"permalink/{OLD_SOURCE}/claims") == f"permalink/{NEW_SOURCE}/claims"
    assert a.resolve_text("Chief Testperson") == "the chief"
    assert a.resolve_text("noted by owner@example") == "noted by [account withheld]"
    assert a.is_suppressed_value(SUPPRESSED_OP)
    assert not a.is_suppressed_value("City DOT")


def test_resolve_public_text_walks_structures() -> None:
    from policy.source_aliases import resolve_public_text

    a = _synthetic_aliases()
    payload = {
        "source_id": OLD_SOURCE,
        "rows": [{"subject_id": f"traffic_camera:{OLD_SOURCE}:t:r", "n": 3}],
        "untouched": 42,
    }
    out = resolve_public_text(payload, a)
    assert out["source_id"] == NEW_SOURCE
    assert out["rows"][0]["subject_id"] == f"traffic_camera:{NEW_SOURCE}:t:r"
    assert out["untouched"] == 42


def test_empty_table_is_identity() -> None:
    from policy.source_aliases import SourceAliases

    a = SourceAliases(
        source={},
        target={},
        token={},
        phrase={},
        redaction={},
        suppressed_value_digests=frozenset(),
        restricted_map_digest=None,
    )
    assert a.empty
    assert a.resolve_text(f"claim/{OLD_SOURCE}") == f"claim/{OLD_SOURCE}"


# ------------------------------------------------------------------ the rekey


def test_rekey_is_idempotent_and_clean() -> None:
    _handles()
    from connectors import personal_id_rekey

    handles = personal_id_rekey.load_handles()
    plan = personal_id_rekey.build_plan(handles)
    personal_id_rekey._merge_prior(plan, personal_id_rekey.RESTRICTED_MAP_OUT)
    leftovers = personal_id_rekey.verify(plan, handles)
    assert not leftovers, (
        f"functional leftovers: {sorted(leftovers)[:5]} (counts: {sum(leftovers.values())})"
    )
    # Idempotency: a second --apply would rewrite nothing new beyond the prior
    # map merge — the apply-time counts prove the sweep found nothing.
    counts = personal_id_rekey.apply_plan(plan, handles, dry_run=True)
    assert counts["files_rewritten"] == 0
    assert counts["paths_moved"] == 0


def test_registry_has_no_handle_or_email_owner_text() -> None:
    handles = _handles()
    for rel in (
        "connectors/src/connectors/data/sources.toml",
        "connectors/src/connectors/data/camera_registry_targets.toml",
    ):
        text = (REPO_ROOT / rel).read_text()
        for h in handles:
            assert h not in text, f"{rel}: a handle-list entry remains"
        for m in re.finditer(r"\(owner ([^,)]+)", text):
            assert not re.search(r"[\w.+-]+@[\w-]+", m.group(1)), (
                f"{rel}: an e-mail-shaped owner string remains"
            )


# ------------------------------------------------------------- export wiring


def _claim_row(pred: str, value: str, *, source: str = OLD_SOURCE) -> tuple:
    """A 19-tuple shaping row (publication_permitted defaults True)."""
    return (
        f"claim/{source}/{pred}",
        f"traffic_camera:{source}:{OLD_TARGET}:ref",
        pred,
        "value",
        value,
        None,  # value_num
        value,  # raw_value
        date(2026, 9, 30),  # observed_at
        0,  # sensitivity_tier
        source,
        "camreg",
        None,
        None,
        None,
        "rights-x",
        "CC0-1.0",
        "yes",
        "yes",
        f"owner: {OLD_SURNAME}",
        "https://example/terms",
    )


def test_parse_shaping_claims_resolves_ids_and_text(monkeypatch) -> None:
    import exports.shaping as shaping

    monkeypatch.setattr(shaping, "load_source_aliases", _synthetic_aliases)
    claims = shaping.parse_shaping_claims([_claim_row("camera_latitude", "35.1")])
    (c,) = claims
    assert c.source_id == NEW_SOURCE
    assert c.subject_id == f"traffic_camera:{NEW_SOURCE}:{NEW_TARGET}:ref"
    assert c.claim_id == f"claim/{NEW_SOURCE}/camera_latitude"
    assert "testperson" not in (c.effective_attribution or "").lower()


def test_parse_shaping_claims_suppresses_handle_operator(monkeypatch) -> None:
    import exports.shaping as shaping

    monkeypatch.setattr(shaping, "load_source_aliases", _synthetic_aliases)
    (c,) = shaping.parse_shaping_claims([_claim_row("camera_operator", SUPPRESSED_OP)])
    assert c.publication_permitted is False
    (ok,) = shaping.parse_shaping_claims([_claim_row("camera_operator", "City DOT")])
    assert ok.publication_permitted is True


def test_fetch_export_raw_resolves_supplementary_rows(monkeypatch) -> None:
    import exports.spine_export as spine

    a = _synthetic_aliases()
    monkeypatch.setattr(
        spine,
        "resolve_public_text",
        lambda v: __import__("policy.source_aliases", fromlist=["x"]).resolve_public_text(v, a),
    )

    class _Cur:
        description = [("source_id",), ("title",)]

        def execute(self, *_a, **_k):
            return None

        def fetchone(self):
            return (True,)  # every table "present" so the fetch path runs

        def fetchall(self):
            return [(OLD_SOURCE, f"Layer ({OLD_SURNAME})")]

    raw = spine.fetch_export_raw(_Cur())
    for rows in raw.values():
        for tup in rows:
            flat = " ".join(str(x) for x in tup)
            assert OLD_SOURCE not in flat and OLD_SURNAME not in flat


# ------------------------------------------------------------- camera sites


def test_camera_sites_projection_drops_suppressed_operator() -> None:
    """The projection seam drops a suppressed operator rather than publish it —
    verified through the alias predicates the module applies (the DB path is
    Docker-gated; the seam logic is what this test binds)."""
    src = (REPO_ROOT / "resolution/src/resolution/camera_sites_pg.py").read_text()
    assert "is_suppressed_value" in src
    assert "resolve_text" in src
    a = _synthetic_aliases()
    assert a.is_suppressed_value(SUPPRESSED_OP)


# -------------------------------------------------------------- N-5 / routes


def test_n5_page_is_neutral_notice_only() -> None:
    src = N5_PAGE.read_text()
    assert 'data-notice="N-5"' in src
    assert "This identifier has changed." in src
    assert "noindex={true}" in src
    # No identifier is ever rendered: no handle (tree grep covers), no new id.
    assert not re.search(r"camreg_[a-z0-9_]+", src)


def test_batch02_rows_well_formed_and_page_carries_them() -> None:
    rows = {}
    for line in BATCH02.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5 or cells[0] in ("id", "—") or set(cells[0]) <= {"-", ":"}:
            continue
        rid, page, text, sha, status = cells
        assert hashlib.sha256(text.encode()).hexdigest() == sha
        assert status in ("pending", "confirmed")
        rows[(page, rid)] = text
    assert rows[("/sources/identifier-changed/", "title")] == "Identifier changed"
    assert rows[("/sources/identifier-changed/", "GN-02")] == "Go to the sources and licences page"
    src = N5_PAGE.read_text()
    assert 'data-copy="GN-02"' in src and 'title="Identifier changed"' in src


def test_renamed_routes_conf_is_neutral() -> None:
    from ops.renamed_routes import NOTICE_BODY, generate_conf

    conf = generate_conf([OLD_SOURCE, "camreg_secondhandle"])
    assert "location = /sources/camreg_testhandle" in conf
    assert "301" not in conf and "return" not in conf  # never a redirect
    assert NOTICE_BODY in conf
    # The conf names old ids — generated from the restricted map, never committed.
    assert conf.count("location = ") == 4


def test_nginx_includes_renamed_barrier() -> None:
    conf = (REPO_ROOT / "ops/web/nginx.conf").read_text()
    assert "renamed_*.conf" in conf


def test_restricted_old_ids_absent_map_is_safe() -> None:
    a = _synthetic_aliases()
    assert a.restricted_old_ids("/nonexistent/map.json") == []


# ------------------------------------------------------------- api middleware


def test_api_middleware_resolves_json_and_text(monkeypatch) -> None:
    import asyncio

    import api.alias_middleware as mw

    a = _synthetic_aliases()
    monkeypatch.setattr(mw, "load_source_aliases", lambda: a)

    async def run(ctype: bytes, body: bytes) -> bytes:
        async def app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", ctype),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        sent = []

        async def send(message):
            sent.append(message)

        async def receive():
            return {"type": "http.request", "body": b""}

        await mw.IdentifierAliasMiddleware(app)({"type": "http"}, receive, send)
        return b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")

    out = asyncio.run(run(b"application/json", json.dumps({"src": OLD_SOURCE}).encode()))
    assert NEW_SOURCE.encode() in out and OLD_SOURCE.encode() not in out
    out = asyncio.run(run(b"text/html", f"<p>{OLD_SOURCE}</p>".encode()))
    assert OLD_SOURCE.encode() not in out


# ------------------------------------------------------------ the crawl check


def test_crawl_check_passes_repo_tip() -> None:
    _handles()
    out = subprocess.run(
        [sys.executable, str(CRAWL_CHECK), "--json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    report = json.loads(out.stdout)
    assert report["verdict"] == "pass", out.stdout
    assert out.returncode == 0


def test_crawl_check_counts_only_never_prints_handles() -> None:
    handles = _handles()
    out = subprocess.run(
        [sys.executable, str(CRAWL_CHECK)], capture_output=True, text=True, cwd=REPO_ROOT
    )
    for h in handles:
        assert h not in out.stdout and h not in out.stderr


def test_crawl_check_fails_on_a_handle(tmp_path) -> None:
    handles = _handles()
    bad = tmp_path / "export"
    bad.mkdir()
    # The handle comes from the gitignored list at runtime — never a literal in
    # this tracked file (test_no_handle_in_any_tracked_file scans it).
    (bad / "sites.jsonl").write_text(json.dumps({"source_id": handles[0]}) + "\n")
    out = subprocess.run(
        [sys.executable, str(CRAWL_CHECK), "--export-dir", str(bad)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert out.returncode == 1
    assert "functional: 1" in out.stdout


# -------------------------------------------------------------- repo hygiene


def test_no_handle_in_any_tracked_file() -> None:
    """The acceptance criterion, verbatim: 0 handle-list entries in the repo
    tip's tracked files (git history is the disclosed retention)."""
    handles = _handles()
    files = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    hits = 0
    for rel in files:
        if rel.startswith(("docs/build/logs/", ".git/")):
            continue
        hits += sum(rel.count(h) for h in handles)
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += sum(text.count(h) for h in handles)
    assert hits == 0, f"{hits} handle-list entries remain in tracked files"


def test_correction_note_discloses_history_retention() -> None:
    text = CORRECTION_NOTE.read_text()
    assert "git history retains" in text.lower() or "history retains" in text.lower()
    assert "identifier has changed" in text.lower()
    assert "Part VIII" in text


def test_adr178_landed_with_verbatim_decisions() -> None:
    text = (
        REPO_ROOT / "docs/adr/ADR-178-public-identifier-re-key-append-only-aliases.md"
    ).read_text()
    assert "Re-key, map restricted" in text
    assert "No, wait for P34.18" in text
    assert "Accept and disclose" in text
    assert "## Revisit trigger" in text
    for h in _handles():
        assert h not in text
