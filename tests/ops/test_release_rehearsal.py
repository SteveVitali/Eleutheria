# SPDX-License-Identifier: Apache-2.0
"""Fixture-verified tests for the P36.70 (REL-11) second-release acceptance
rehearsal runner (``ops/src/ops/release_rehearsal.py``).

The rehearsal is the contract's QUEUED leg — it runs Class S under operator
``sig.operator-authority/1`` records (the B-9 standing go is valid now but
expires at GATE-G6, when the P36.72b-promoted precondition lands — the
contract's own fallback). These tests pin: the deterministic
``sig.withdrawal-order/1`` pair and its bound (entity-kind, ≤4, exact-twin
reinstate), the plan's QUEUED blockers (no promoted release / no rollback
target / unverifiable authority), the four timed legs over a fixture
registry (rollback → restore → deny → allow) with the ``sig.release-rehearsal/1``
record's measured timings + budgets, latest restored byte-for-byte at the
pointer level, and the honest byte-restore note (append-only — a NEW
disposition, the next release's staging)."""

from __future__ import annotations

import itertools
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from policy.eligibility import TargetKind

from ops import release_conf as rc
from ops import release_pipeline as rp
from ops import release_rehearsal as rh
from ops import release_reversal as rr

NOW = datetime(2026, 11, 16, 15, 0, 0, tzinfo=UTC)  # a Monday inside the band

PUB_A = "p-" + "a" * 64
PUB_B = "p-" + "b" * 64
EID = "ent-low-stakes-1"

_DENY_LINE = re.compile(r"^location = (\S+) \{ error_page 410 (\S+); return 410; \}$")


def _store(tmp_path: Path) -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path / "reg")


def _put(store: rp.Store, name: str, body: bytes | dict[str, Any]) -> None:
    data = json.dumps(body, sort_keys=True).encode() if isinstance(body, dict) else body
    meta = store.stat(name)
    if meta is None:
        store.insert(name, data, content_type="application/json")
    else:
        store.replace(
            name, data, generation=int(meta["generation"]), content_type="application/json"
        )


def _catalog_entry(pub: str, label: str) -> dict[str, Any]:
    return {
        "schema": "sig.publication-catalog-entry/1",
        "publication_id": pub,
        "data_release_id": label,
        "label": label,
        "manifest_sha256": "0" * 64,
        "descriptor_sha256": "1" * 64,
        "compartments": [{"compartment": "sig_graph"}],
        "compat": {"as_of_world": "2026-11-13"},
    }


def _seed_pub(store: rp.Store, pub: str, label: str, *, eid: str = EID) -> None:
    _put(store, f"staged/releases/{pub}/catalog_entry.json", _catalog_entry(pub, label))
    _put(
        store,
        f"staged/releases/{pub}/release.json",
        {"schema": "sig.site-release/1", "data_release_id": label},
    )
    _put(
        store,
        f"staged/releases/{pub}/descriptor.json",
        {"schema": "sig.release-descriptor/2", "label": label, "code": {"commit": "x" * 40}},
    )
    store.insert(f"staged/releases/{pub}/index.html", f"<html>{label}</html>".encode())
    store.insert(f"staged/r/{pub}/index.html", f"<html>{label} landing</html>".encode())
    store.insert(
        f"staged/r/{pub}/c/sig_graph/entity/deployment/{eid}/index.html",
        f"<html>{eid}</html>".encode(),
    )
    store.insert(
        f"staged/r/{pub}/c/sig_graph/entity/deployment/{eid}.json",
        json.dumps({"entity_id": eid}).encode(),
    )
    store.insert(f"staged/v/{pub}/index.html", f"<html>v {label}</html>".encode())
    store.insert(f"staged/s/{pub}/index.html", f"<html>s {label}</html>".encode())


def _gen_files(gen: int, pubs: set[str], latest: dict[str, Any] | None) -> dict[str, bytes]:
    latest_bytes = json.dumps(latest, sort_keys=True).encode() if latest else b"{}"
    return {
        "promoted.map": rc.render_promoted_map(pubs, gen=gen),
        "latest.json": latest_bytes,
        "withdrawn.conf": rr._deny_map_bytes(Path("/nonexistent")),
        "selectors.conf": rc._empty_selectors(gen),
        "labels.conf": rc.render_labels_conf({}, gen=gen),
        "releases/index.html": b"<html>releases</html>",
        "releases/catalog.json": b"{}",
        "releases/latest.json": latest_bytes,
    }


def _seed_two_release_registry(store: rp.Store) -> None:
    """Two promoted releases: PUB_A (the first), PUB_B (current latest —
    P36.72b's stand-in). PUB_B's generation-2 latest records previous=PUB_A,
    so the rehearsal's rollback target resolves deterministically."""
    pubs = [(PUB_A, "sig-2026-11-10.1"), (PUB_B, "sig-2026-11-13.1")]
    _put(
        store,
        "registry/catalog.json",
        {
            "schema": "sig.publication-catalog/1",
            "publications": [_catalog_entry(pub, label) for pub, label in pubs],
        },
    )
    _put(store, "registry/withdrawals.json", {"schema": "sig.withdrawal-registry/1", "entries": []})
    _put(
        store,
        "registry/labels.json",
        {
            "schema": "sig.label-map/1",
            "labels": [{"publication_id": p, "label": lbl} for p, lbl in pubs],
        },
    )
    for gen, (pub, label) in enumerate(pubs, start=1):
        prior = pubs[gen - 2][0] if gen > 1 else None
        promoted = {p for p, _lbl in pubs[:gen]}
        latest = {
            "schema": rc.LATEST_SCHEMA_V2,
            "publication_id": pub,
            "label": label,
            "activated_at": NOW.isoformat(),
            "conf_gen": gen,
            "previous": prior,
            "rolled_back": False,
            "withdrawals_sha256": rr.withdrawals_sha256(store),
        }
        for name, body in _gen_files(gen, promoted, latest).items():
            store.insert(f"registry/conf/{gen}/{name}", body)


def _authority(store: rp.Store, name: str, **fields: Any) -> None:
    _put(
        store,
        f"{rr.AUTHORITIES_PREFIX}{name}",
        {
            "schema": rr.AUTHORITY_SCHEMA,
            "kind": "go",
            "ref": f"OPS-{name}",
            "issued_at": "2026-11-13T12:00:00Z",
            **fields,
        },
    )


def _clock(start: datetime = NOW, step_s: float = 1.5):
    """A deterministic now_fn + monotonic pair — each leg advances the fake
    clock so the record's per-leg seconds are measured, never zero-ish."""
    ticks = itertools.count()

    def now_fn() -> datetime:
        return start + timedelta(seconds=step_s * next(ticks))

    mono = itertools.count(start=0.0, step=step_s)

    def monotonic() -> float:
        return next(mono)

    return now_fn, monotonic


def _deny_uris(conf_text: str) -> set[str]:
    return {m.group(1) for m in map(_DENY_LINE.match, conf_text.splitlines()) if m}


def _orders(tmp_path: Path, ids: list[str] | None = None) -> tuple[Path, Path]:
    deny, allow = rh.rehearsal_orders(ids or [EID])
    d = tmp_path / "deny.json"
    a = tmp_path / "allow.json"
    d.write_bytes(json.dumps(deny, sort_keys=True).encode())
    a.write_bytes(json.dumps(allow, sort_keys=True).encode())
    return d, a


# --------------------------------------------------------------------------- #
# the orders — deterministic, bounded, exact-twin                             #
# --------------------------------------------------------------------------- #


def test_rehearsal_orders_are_deterministic_and_bounded(tmp_path: Path) -> None:
    deny, allow = rh.rehearsal_orders([EID], compartment="sig_graph")
    assert deny["schema"] == rr.ORDER_SCHEMA == allow["schema"]
    (e,) = deny["entries"]
    assert e["target_kind"] == "entity" and e["target_id"] == EID
    assert e["disposition"] == "withdraw" and e["compartment"] == "sig_graph"
    (a,) = allow["entries"]
    assert a["disposition"] == "allow" and a["target_id"] == EID
    assert a["compartment"] == "sig_graph"
    # byte-stable: the same inputs re-derive the same pair (resume-safe)
    assert (deny, allow) == rh.rehearsal_orders([EID], compartment="sig_graph")
    # the bound refuses a wide blast radius outright
    with pytest.raises(rp.PipelineError) as exc:
        rh.rehearsal_orders([f"e{i}" for i in range(rh.MAX_ORDER_ENTRIES + 1)])
    assert exc.value.code == "order-too-wide"
    with pytest.raises(rp.PipelineError):
        rh.rehearsal_orders([])


def test_assert_bounded_orders_refuses_wide_and_mismatched(tmp_path: Path) -> None:
    deny, allow = rh.rehearsal_orders([EID])
    de, _ = rr.load_order(_write(tmp_path / "d.json", deny))
    ae, _ = rr.load_order(_write(tmp_path / "a.json", allow))
    rh.assert_bounded_orders(de, ae)  # the honest pair passes
    # a release-kind deny is a real withdrawal, never a rehearsal
    bad = [dict(de[0], target_kind=TargetKind.RELEASE_ARTIFACT, target_id=PUB_A)]
    with pytest.raises(rp.PipelineError) as exc:
        rh.assert_bounded_orders(bad, ae)
    assert exc.value.code == "order-too-wide"
    # a reinstate missing a target is refused
    with pytest.raises(rp.PipelineError) as exc2:
        rh.assert_bounded_orders(de + de, ae)
    assert exc2.value.code in {"order-too-wide", "order-mismatch"}
    # a reinstate that does not cover the deny's targets is refused
    short = [dict(ae[0], target_id="other")]
    with pytest.raises(rp.PipelineError) as exc3:
        rh.assert_bounded_orders(de, short)
    assert exc3.value.code == "order-mismatch"


def _write(path: Path, doc: dict[str, Any]) -> Path:
    path.write_bytes(json.dumps(doc, sort_keys=True).encode())
    return path


# --------------------------------------------------------------------------- #
# plan + blockers — the QUEUED reasons, never a fabricated run                #
# --------------------------------------------------------------------------- #


def test_plan_reports_queued_when_nothing_promoted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    found = rh.blockers(store, go="go-1", authority="auth-1")
    assert any("no-promoted-release" in b for b in found)
    out = rh.plan(store, go="go-1", authority="auth-1")
    assert out["blockers"] and out["snapshot"]["conf_gen"] == 0


def test_plan_resolves_pointers_and_authority_blockers(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    snap = rh.resolve(store)
    assert snap["current_pub"] == PUB_B and snap["rollback_target"] == PUB_A
    assert snap["target_kind"] == "pub"
    # unnamed authority slots block; named-but-absent records block too
    found = rh.blockers(store)
    assert any("go-unnamed" in b for b in found)
    assert any("authority-unnamed" in b for b in found)
    found2 = rh.blockers(store, go="go-1", authority="auth-1")
    assert any("go-refused" in b for b in found2)
    _authority(store, "go-1")
    _authority(store, "auth-1")
    assert rh.blockers(store, go="go-1", authority="auth-1") == []


def test_run_apply_refuses_queued_with_no_promoted_release(tmp_path: Path) -> None:
    store = _store(tmp_path)
    deny, allow = _orders(tmp_path)
    before = set(store.list(""))
    with pytest.raises(rp.PipelineError) as exc:
        rh.run(
            store,
            apply_=True,
            deny_order=deny,
            allow_order=allow,
            go="go-1",
            authority="auth-1",
        )
    assert exc.value.code == "rehearsal-blocked"
    assert set(store.list("")) == before  # nothing written, no lock left


# --------------------------------------------------------------------------- #
# the four timed legs over the fixture registry                               #
# --------------------------------------------------------------------------- #


def test_run_executes_the_timed_legs_and_restores(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    _authority(store, "go-1")
    _authority(store, "auth-1")
    deny, allow = _orders(tmp_path)
    now_fn, monotonic = _clock()
    out = tmp_path / "rehearsal.json"
    record = rh.run(
        store,
        apply_=True,
        deny_order=deny,
        allow_order=allow,
        go="go-1",
        authority="auth-1",
        out=out,
        now_fn=now_fn,
        monotonic=monotonic,
    )
    assert record["schema"] == rh.REHEARSAL_SCHEMA
    assert record["status"] == "rehearsed"
    assert [leg["leg"] for leg in record["legs"]] == [
        "rollback-to-prior",
        "rollback-restore",
        "withdraw-deny",
        "withdraw-reinstate",
    ]
    # every leg measured + judged — never a smoothed figure
    for leg in record["legs"]:
        assert leg["outcome"] == "applied" and leg["seconds"] > 0
        assert leg["within_budget"] is True
        assert leg["started_at"].endswith("Z")
    assert record["timings"]["all_within_budget"] is True
    # the pointer ends where it started — the rehearsal restores
    assert record["post"]["latest_restored"] is True
    latest = rc.read_generation(store, rc.current_generation(store))
    assert latest["publication_id"] == PUB_B
    # the deny landed for real (every alias of the low-stakes route), then
    # the allow lifted it — both append-only records in the registry
    registry_doc = json.loads(store.read("registry/withdrawals.json"))
    disps = [e["disposition"] for e in registry_doc["entries"] if e["target_id"] == EID]
    assert disps == ["withdraw", "allow"]
    assert record["post"]["rehearsal_dispositions"] == {EID: "allow"}
    assert record["post"]["byte_restore"].startswith("next-release")
    # the deny map of the final generation no longer denies the route
    final_conf = store.read(f"registry/conf/{rc.current_generation(store)}/withdrawn.conf").decode()
    assert not any(EID in u for u in _deny_uris(final_conf))
    # the record lands in the registry's append-only home + the out file
    assert record["object"].startswith(rh.REHEARSALS_PREFIX)
    assert store.read(record["object"]) is not None
    assert json.loads(out.read_bytes())["status"] == "rehearsed"
    # the journal carries the rehearsal's verb events
    verbs = {e["verb"] for e in rp.list_events(store)}
    assert {"rolled-back", "rolled-back-from", "withdraw"} <= verbs


def test_run_without_apply_plans_and_writes_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    before = set(store.list(""))
    record = rh.run(store, apply_=False, go="go-1", authority="auth-1")
    assert record["status"] == "planned" and len(record["plan"]) == 4
    assert set(store.list("")) == before
    assert store.read("registry/LOCK") is None


def test_run_records_a_leg_failure_honestly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A leg that refuses stops the run; the emitted record names the
    applied legs + the refused leg — never a smoothed rehearsal."""
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    _authority(store, "go-1")
    _authority(store, "auth-1")
    deny, allow = _orders(tmp_path)

    real_wd = rr.verb_withdraw

    def boom(*a: Any, **kw: Any) -> dict[str, Any]:
        raise rp.PipelineError("probe-failed", "planted leg failure — the record must say so")

    monkeypatch.setattr(rr, "verb_withdraw", boom)
    now_fn, monotonic = _clock()
    with pytest.raises(rp.PipelineError):
        rh.run(
            store,
            apply_=True,
            deny_order=deny,
            allow_order=allow,
            go="go-1",
            authority="auth-1",
            out=tmp_path / "rec.json",
            now_fn=now_fn,
            monotonic=monotonic,
        )
    monkeypatch.setattr(rr, "verb_withdraw", real_wd)
    record = json.loads((tmp_path / "rec.json").read_bytes())
    assert record["status"] == "failed"
    legs = {leg["leg"]: leg for leg in record["legs"]}
    assert legs["rollback-to-prior"]["outcome"] == "applied"
    assert legs["rollback-restore"]["outcome"] == "applied"
    assert legs["withdraw-deny"]["outcome"] == "refused"
    assert "withdraw-reinstate" not in legs  # the run stopped, recorded
    # the pointer still restored — the applied pair left latest at PUB_B
    latest = rc.read_generation(store, rc.current_generation(store))
    assert latest["publication_id"] == PUB_B


def test_run_refuses_an_unstaged_rehearsal_target(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    _authority(store, "go-1")
    _authority(store, "auth-1")
    deny, allow = _orders(tmp_path, ids=["ent-never-staged"])
    before = set(store.list(""))
    with pytest.raises(rp.PipelineError) as exc:
        rh.run(
            store,
            apply_=True,
            deny_order=deny,
            allow_order=allow,
            go="go-1",
            authority="auth-1",
        )
    assert exc.value.code == "target-unstaged"
    assert set(store.list("")) == before


# --------------------------------------------------------------------------- #
# the CLI surface                                                             #
# --------------------------------------------------------------------------- #


def test_cli_orders_plan_and_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store_dir = tmp_path / "reg"
    store = rp.LocalDirStore(store_dir)
    _seed_pub(store, PUB_A, "sig-2026-11-10.1")
    _seed_pub(store, PUB_B, "sig-2026-11-13.1")
    _seed_two_release_registry(store)
    _authority(store, "go-1")
    _authority(store, "auth-1")
    assert rh.main(["orders", "--entity", EID, "--out", str(tmp_path / "ord")]) == 0
    deny = tmp_path / "ord" / "rehearsal-deny.json"
    allow = tmp_path / "ord" / "rehearsal-allow.json"
    assert deny.is_file() and allow.is_file()
    # plan over an empty registry exits 42 (queued), over the seeded one 0
    empty = tmp_path / "empty"
    assert rh.main(["plan", "--registry", str(empty)]) == 42
    assert (
        rh.main(["plan", "--registry", str(store_dir), "--go", "go-1", "--authority", "auth-1"])
        == 0
    )
    rc_run = rh.main(
        [
            "run",
            "--registry",
            str(store_dir),
            "--deny-order",
            str(deny),
            "--allow-order",
            str(allow),
            "--go",
            "go-1",
            "--authority",
            "auth-1",
            "--apply",
            "--out",
            str(tmp_path / "rec.json"),
        ]
    )
    assert rc_run == 0
    assert "rehearsed" in capsys.readouterr().out
    assert (
        store.read(
            "registry/rehearsals/"
            + sorted(n.rsplit("/", 1)[-1] for n in store.list("registry/rehearsals/"))[-1]
        )
        is not None
    )
