# SPDX-License-Identifier: Apache-2.0
"""Fixture-verified tests for the P35.55 release reversal verbs (REL-08,
SIG-REL-013, G3 §8.1–8.6, SIG-OPS-010/SIG-SEC-009).

Covers the ticket's fixture-verified list: rollback re-applies the CURRENT
withdrawal set and never reverts config bytes (RR-7 — new revisions, never
a traffic reversion); a rollback target under a current denying release
disposition is refused; clear-latest is the honest no-current-release
state; withdraw appends the order's dispositions append-only and emits an
alias-complete ``withdrawn.conf`` (every alias → its own sig.tombstone/1
body) plus a dated receipt; a compartment-scoped withdrawal reaches only
``c/<comp>/`` routes (§42.3 — never the other compartment); the legacy
floor imports under ``v/legacy-<date>/`` (never a pub id); ``--purge-versions``
touches noncurrent object versions only; the conf-gen regression probe
emits sig.probe-run/1; and D-P35.54-1's promote-time barrier re-derivation
+ marker + in-lock drift refusal.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from policy.eligibility import Disposition, ReasonCategory, TargetKind

from ops import release_conf as rc
from ops import release_pipeline as rp
from ops import release_reversal as rr

NOW = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)

PUB_A = "p-" + "a" * 64
PUB_B = "p-" + "b" * 64
PUB_C = "p-" + "c" * 64
EID = "ent-test-1"

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
        "compat": {"as_of_world": "2026-10-20"},
    }


def _seed_pub(store: rp.Store, pub: str, label: str, *, eid: str = EID) -> None:
    """A minimal staged tree for one release: the four namespaces, a release
    stamp + descriptor + catalog entry, and one entity record route (html
    page + .json twin) under ``c/sig_graph/``."""
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


def _gen_files(
    store: rp.Store, gen: int, pubs: set[str], latest: dict[str, Any] | None
) -> dict[str, bytes]:
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


def _seed_registry(
    store: rp.Store,
    pubs: list[tuple[str, str]],
    *,
    current: str | None = None,
) -> int:
    """Two-generation registry: every pub staged + catalogued; one conf gen
    per pub (each promotes one more); the LAST gen's latest is ``current``
    (default the last pub). Returns the current generation."""
    catalog = {
        "schema": "sig.publication-catalog/1",
        "publications": [_catalog_entry(pub, label) for pub, label in pubs],
    }
    _put(store, "registry/catalog.json", catalog)
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
            "publication_id": (current if gen == len(pubs) else pub) or pub,
            "label": label,
            "activated_at": NOW.isoformat(),
            "conf_gen": gen,
            "previous": prior,
            "rolled_back": False,
            "withdrawals_sha256": rr.withdrawals_sha256(store),
        }
        for name, body in _gen_files(store, gen, promoted, latest).items():
            store.insert(f"registry/conf/{gen}/{name}", body)
    return len(pubs)


def _authority(store: rp.Store, name: str = "go-1", **fields: Any) -> dict[str, Any]:
    rec = {
        "schema": rr.AUTHORITY_SCHEMA,
        "kind": "go",
        "ref": f"OPS-{name}",
        "issued_at": "2026-10-24T00:00:00Z",
        **fields,
    }
    _put(store, f"{rr.AUTHORITIES_PREFIX}{name}", rec)
    return rec


def _order(
    tmp_path: Path,
    entries: list[dict[str, Any]],
    **meta: Any,
) -> Path:
    doc = {"schema": rr.ORDER_SCHEMA, "order_id": "ord-1", "entries": entries, **meta}
    p = tmp_path / "order.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def _entity_deny(eid: str = EID, **extra: Any) -> dict[str, Any]:
    return {
        "target_kind": TargetKind.ENTITY.value,
        "target_id": eid,
        "disposition": Disposition.WITHDRAW.value,
        "reason_category": ReasonCategory.SAFETY_WITHDRAWAL.value,
        **extra,
    }


def _deny_uris(conf_text: str) -> set[str]:
    return {m.group(1) for m in map(_DENY_LINE.match, conf_text.splitlines()) if m}


# --------------------------------------------------------------------------- #
# rollback (§8.1) — re-applies the CURRENT withdrawal set; never a config     #
# reversion (RR-7); refuses a denied target                                    #
# --------------------------------------------------------------------------- #


def test_rollback_repoints_latest_and_keeps_the_barrier(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_pub(store, PUB_B, "sig-2026-10-02.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1"), (PUB_B, "sig-2026-10-02.1")])
    _authority(store)
    # a withdrawal lands under B's generation — the rollback must KEEP it
    order = _order(tmp_path, [_entity_deny()])
    rr.verb_withdraw(store, apply_=True, disposition=order, authority="go-1", now=NOW)
    denied_before = _deny_uris(store.read("registry/conf/3/withdrawn.conf").decode())
    out = rr.verb_rollback(store, apply_=True, to=PUB_A, reason="bad gen 3", go="go-1", now=NOW)
    assert out["applied"] is True and out["conf_gen"] == 4
    latest = rc.read_generation(store, 4)
    assert latest["publication_id"] == PUB_A and latest["rolled_back"] is True
    assert latest["previous"] == PUB_B
    # the deny map survives the rollback — never a revived route
    denied_after = _deny_uris(store.read("registry/conf/4/withdrawn.conf").decode())
    assert denied_before <= denied_after
    # the journal carries both events
    kinds = {e["verb"] for e in rp.list_events(store)}
    assert {"withdraw", "rolled-back", "rolled-back-from"} <= kinds
    # the promoted set still names every promoted release — never shrunk
    promoted = rc.read_promoted_map(store, 4)
    assert {PUB_A, PUB_B} <= promoted


def test_rollback_refuses_a_target_under_a_release_deny(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_pub(store, PUB_B, "sig-2026-10-02.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1"), (PUB_B, "sig-2026-10-02.1")])
    _authority(store)
    order = _order(
        tmp_path,
        [
            {
                "target_kind": TargetKind.RELEASE_ARTIFACT.value,
                "target_id": PUB_A,
                "disposition": Disposition.WITHDRAW.value,
                "reason_category": ReasonCategory.RIGHTS_WITHDRAWAL.value,
            }
        ],
    )
    rr.verb_withdraw(store, apply_=True, disposition=order, authority="go-1", now=NOW)
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_rollback(store, apply_=True, to=PUB_A, reason="roll to denied", go="go-1", now=NOW)
    assert "denied" in str(exc.value).lower() or "disposition" in str(exc.value).lower()


def test_rollback_refuses_same_latest_and_never_promoted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_rollback(store, apply_=True, to=PUB_A, reason="same", go="go-1", now=NOW)
    assert exc.value.code == "same-latest"
    with pytest.raises(rp.PipelineError) as exc2:
        rr.verb_rollback(store, apply_=True, to=PUB_C, reason="unknown", go="go-1", now=NOW)
    assert exc2.value.code in {"never-promoted", "unstaged-target"}


def test_rollback_dry_run_writes_nothing_and_takes_no_lock(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_pub(store, PUB_B, "sig-2026-10-02.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1"), (PUB_B, "sig-2026-10-02.1")])
    before = set(store.list(""))
    out = rr.verb_rollback(store, apply_=False, to=PUB_A, reason="plan", now=NOW)
    assert out["dry_run"] is True and out["applied"] is False
    assert set(store.list("")) == before
    assert store.read("registry/LOCK") is None


# --------------------------------------------------------------------------- #
# clear-latest (§8.2) — the honest no-current-release state                   #
# --------------------------------------------------------------------------- #


def test_clear_latest_nulls_the_pointer_and_keeps_the_archive(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    out = rr.verb_clear_latest(store, apply_=True, reason="takedown window", go="go-1", now=NOW)
    assert out["applied"] is True
    latest = rc.read_generation(store, 2)
    assert latest["publication_id"] is None and latest["cleared"] == PUB_A
    # the promoted set is untouched — the archive still serves the namespaces
    assert PUB_A in rc.read_promoted_map(store, 2)
    # the registry latest pointer cleared too (the view wrote it back absent)
    assert store.read("registry/latest.json") is None
    kinds = {e["verb"] for e in rp.list_events(store)}
    assert "cleared-latest" in kinds


def test_clear_latest_on_an_empty_registry_refuses_honestly(tmp_path: Path) -> None:
    """With no latest pointer at all there is nothing to clear — the verb
    refuses rather than silently re-clearing (the file-layout machinery's
    own fail-closed rule)."""
    store = _store(tmp_path)
    _authority(store)
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_clear_latest(store, apply_=True, reason="never promoted", go="go-1", now=NOW)
    assert exc.value.code == "clear-latest-refused"


# --------------------------------------------------------------------------- #
# withdraw (§8.3) — order → dispositions → deny map + tombstones → receipt    #
# --------------------------------------------------------------------------- #


def test_withdraw_denies_every_alias_and_receipts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    order = _order(tmp_path, [_entity_deny()])
    out = rr.verb_withdraw(store, apply_=True, disposition=order, authority="go-1", now=NOW)
    assert out["applied"] is True and out["conf_gen"] == 2
    route = f"r/{PUB_A}/c/sig_graph/entity/deployment/{EID}"
    uris = _deny_uris(store.read("registry/conf/2/withdrawn.conf").decode())
    # the complete alias set: no-slash, trailing-slash, index.html + .json twin
    assert {f"/{route}", f"/{route}/", f"/{route}/index.html", f"/{route}.json"} <= uris
    # the withdrawal registry carries the append-only record
    registry_doc = json.loads(store.read("registry/withdrawals.json"))
    assert len(registry_doc["entries"]) == 1
    rec = registry_doc["entries"][0]
    assert rec["target_id"] == EID and rec["disposition"] == "withdraw"
    assert rec["seq"] == 0  # first append — insert order, never file order
    # the dated receipt is committed and names the authority
    receipts = store.list(rr.RECEIPTS_PREFIX)
    assert receipts == [out["receipt"]]
    receipt = json.loads(store.read(out["receipt"]))
    assert receipt["schema"] == rr.RECEIPT_SCHEMA
    assert receipt["authority"]["ref"] == "OPS-go-1"
    assert receipt["claim_spine_touched"] is False
    # the route's staged bytes answer a sig.tombstone/1 page now — the
    # original record HTML is gone (the deny map 410s onto the same shape)
    body = store.read(f"staged/{route}/index.html") or b""
    assert b"withdrawn" in body and b"<html>ent-test-1</html>" not in body


def test_withdraw_emits_tombstone_bodies_for_every_alias(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    order = _order(tmp_path, [_entity_deny()])
    out = rr.verb_withdraw(store, apply_=True, disposition=order, authority="go-1", now=NOW)
    conf = store.read("registry/conf/2/withdrawn.conf").decode()
    probes = [p for p in out["probes"] if p["kind"] in {"deny-line", "tombstone-body"}]
    assert probes and all(p["status"] == "pass" for p in probes)
    # the error_page bodies exist under the staged tombstone dir
    bodies = {m.group(2) for m in map(_DENY_LINE.match, conf.splitlines()) if m}
    assert bodies
    for body in bodies:
        assert store.read(f"staged/{body}") is not None


def test_withdraw_compartment_scope_never_crosses_the_boundary(tmp_path: Path) -> None:
    """§42.3: a withdrawal scoped to ``osm_physical`` denies only the
    ``c/osm_physical/`` routes — the sig_graph copy of the same entity keeps
    serving (compartments never bleed)."""
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    # the same entity id staged under the ODbL compartment too
    store.insert(
        f"staged/r/{PUB_A}/c/osm_physical/entity/deployment/{EID}/index.html",
        b"<html>osm copy</html>",
    )
    store.insert(
        f"staged/r/{PUB_A}/c/osm_physical/entity/deployment/{EID}.json",
        json.dumps({"entity_id": EID}).encode(),
    )
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    order = _order(tmp_path, [_entity_deny(compartment="osm_physical")])
    out = rr.verb_withdraw(store, apply_=True, disposition=order, authority="go-1", now=NOW)
    assert out["applied"] is True
    uris = _deny_uris(store.read("registry/conf/2/withdrawn.conf").decode())
    assert f"/r/{PUB_A}/c/osm_physical/entity/deployment/{EID}" in uris
    assert not any("/c/sig_graph/" in u for u in uris)
    # the sig_graph bytes stay staged — serving continues
    assert (
        store.read(f"staged/r/{PUB_A}/c/sig_graph/entity/deployment/{EID}/index.html") is not None
    )
    # the scoped record round-trips through the registry document
    doc = json.loads(store.read("registry/withdrawals.json"))
    assert doc["entries"][0]["compartment"] == "osm_physical"


def test_withdraw_requires_an_authority_record(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    order = _order(tmp_path, [_entity_deny()])
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_withdraw(store, apply_=True, disposition=order, now=NOW)
    assert exc.value.code == "authority-required"
    with pytest.raises(rp.PipelineError) as exc2:
        rr.verb_withdraw(store, apply_=True, disposition=order, authority="nope", now=NOW)
    assert exc2.value.code == "authority-absent"
    # revoked records refuse the same way
    _authority(store, name="revoked", revoked=True)
    with pytest.raises(rp.PipelineError) as exc3:
        rr.verb_withdraw(store, apply_=True, disposition=order, authority="revoked", now=NOW)
    assert exc3.value.code == "authority-refused"


def test_withdraw_validates_the_order_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    order = _order(
        tmp_path,
        [
            {
                "target_kind": "not-a-kind",
                "target_id": "x",
                "disposition": "withdraw",
                "reason_category": "safety_withdrawal",
            }
        ],
    )
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_withdraw(store, apply_=False, disposition=order, now=NOW)
    assert exc.value.code == "order-entry"
    empty = _order(tmp_path, [])
    with pytest.raises(rp.PipelineError) as exc2:
        rr.verb_withdraw(store, apply_=False, disposition=empty, now=NOW)
    assert exc2.value.code == "order-empty"
    with pytest.raises(rp.PipelineError):
        rr.verb_withdraw(store, apply_=False, disposition=tmp_path / "absent.json", now=NOW)


# --------------------------------------------------------------------------- #
# --purge-versions — bucket objects only, noncurrent generations only        #
# --------------------------------------------------------------------------- #


def test_purge_versions_is_a_noop_on_a_local_dir_store(tmp_path: Path) -> None:
    out = rr.purge_noncurrent_versions(_store(tmp_path), ["staged/r/x/index.html"])
    assert out["status"] == "noop-local-store" and out["versions_deleted"] == 0


def test_purge_versions_deletes_only_noncurrent_generations(tmp_path: Path) -> None:
    deleted: list[tuple[str, int]] = []

    class FakeClient:
        def list_object_versions(self, name: str) -> list[dict[str, Any]]:
            assert name == "staged/r/x/index.html"
            return [
                {"name": name, "generation": 100, "timeDeleted": True},
                {"name": name, "generation": 200},  # a noncurrent live version
                {"name": name, "generation": 300},  # the LIVE generation — kept
            ]

        def delete_object(self, name: str, *, generation: int | None = None) -> str:
            deleted.append((name, int(generation or -1)))
            return name

    class FakeStore(rp.LocalDirStore):
        pass

    store = FakeStore(tmp_path / "reg")
    store.client = FakeClient()  # type: ignore[attr-defined]
    out = rr.purge_noncurrent_versions(store, ["staged/r/x/index.html"])
    assert out["status"] == "purged" and out["versions_deleted"] == 1
    # generation 200 is deleted; 300 (the live generation) and 100 (already
    # deleted) are never touched — the claim spine is nowhere in this path
    assert deleted == [("staged/r/x/index.html", 200)]


# --------------------------------------------------------------------------- #
# legacy floor (§8.5) — labelled legacy-<date>, never a publication id        #
# --------------------------------------------------------------------------- #


def test_import_floor_stages_a_labelled_tree(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _authority(store)
    src = tmp_path / "floor"
    (src / "entity").mkdir(parents=True)
    (src / "index.html").write_text("<html>old site</html>", encoding="utf-8")
    (src / "entity" / "x.html").write_text("<html>x</html>", encoding="utf-8")
    out = rr.verb_import_floor(
        store, apply_=True, source_dir=src, label="legacy-20251001", go="go-1", now=NOW
    )
    assert out["applied"] is True and out["objects"] == 2
    assert store.read("staged/v/legacy-20251001/index.html") == b"<html>old site</html>"
    floor = json.loads(store.read(rr.FLOOR_OBJECT))
    assert floor["floors"][0]["label"] == "legacy-20251001"
    assert not rc.PUB_RE.match("legacy-20251001")
    assert "legacy-floor-imported" in {e["verb"] for e in rp.list_events(store)}


def test_import_floor_refuses_a_pub_shaped_label(tmp_path: Path) -> None:
    store = _store(tmp_path)
    src = tmp_path / "floor"
    src.mkdir()
    (src / "index.html").write_text("x", encoding="utf-8")
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_import_floor(store, apply_=False, source_dir=src, label=PUB_A, now=NOW)
    assert exc.value.code == "bad-floor-label"


def test_rollback_to_a_legacy_floor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _authority(store)
    src = tmp_path / "floor"
    src.mkdir()
    (src / "index.html").write_text("<html>floor</html>", encoding="utf-8")
    rr.verb_import_floor(
        store, apply_=True, source_dir=src, label="legacy-20251001", go="go-1", now=NOW
    )
    out = rr.verb_rollback(
        store, apply_=True, to="legacy-20251001", reason="emergency floor", go="go-1", now=NOW
    )
    assert out["applied"] is True
    latest = rc.read_generation(store, 2)
    assert latest["publication_id"] is None
    assert latest["legacy_floor"] == "legacy-20251001"


def test_rollback_to_an_unknown_floor_refuses(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_registry(store, [])
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_rollback(store, apply_=True, to="legacy-20990101", reason="no floor", now=NOW)
    assert exc.value.code == "unknown-floor"


# --------------------------------------------------------------------------- #
# The conf-gen regression probe (P1)                                          #
# --------------------------------------------------------------------------- #


def _fetch_gen(gen: int | None, status: int = 200):
    def fetch(url: str):
        headers = {"X-SIG-Conf-Gen": str(gen)} if gen is not None else {}
        return status, headers, b""

    return fetch


def test_conf_gen_probe_pass_fail_and_skip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])  # recorded gen = 1

    ok = rr.conf_gen_probe(store, origins=["https://web.example"], fetch=_fetch_gen(1))
    assert ok["overall"] == "pass" and ok["version"].startswith("sig.probe-run")

    older = rr.conf_gen_probe(store, origins=["https://web.example"], fetch=_fetch_gen(0))
    # an older generation CAN be recorded — 0 is unrecorded; seed a real gen-0?
    # recorded==1 so served==0 < recorded → the P1 alarm fires
    assert older["overall"] == "fail"

    newer = rr.conf_gen_probe(store, origins=["https://web.example"], fetch=_fetch_gen(9))
    assert newer["overall"] == "fail"

    no_hdr = rr.conf_gen_probe(store, origins=["https://web.example"], fetch=_fetch_gen(None))
    assert no_hdr["overall"] == "fail"  # no header = a non-release config is serving

    nothing = rr.conf_gen_probe(store, origins=[], fetch=_fetch_gen(1))
    assert nothing["overall"] == "partial"  # non-evaluated set — never a fake pass

    def boom(url: str):
        raise OSError("unreachable")

    unreach = rr.conf_gen_probe(store, origins=["https://web.example"], fetch=boom)
    assert unreach["overall"] == "partial"  # skipped, never fabricated


# --------------------------------------------------------------------------- #
# D-P35.54-1 — promote-time barrier re-derivation + marker + drift refusal    #
# --------------------------------------------------------------------------- #


def _approval(store: rp.Store, name: str = "go-pub") -> None:
    _put(
        store,
        f"{rc.APPROVALS_PREFIX}{name}",
        {
            "schema": rc.APPROVAL_SCHEMA,
            "ref": f"GO-{name}",
            "kind": "standing_go",
            "class": "class_r",
            "issued_at": "2026-10-24T00:00:00Z",
        },
    )


def _promote_ready(store: rp.Store, pub: str, label: str) -> None:
    """A candidate that folds 'verified' + carries a class_r journal row."""
    _seed_pub(store, pub, label)
    rp.emit_event(store, "verified", pub, {"outcome": "recorded", "checks": []}, now=NOW)
    rp.emit_event(
        store,
        "classified",
        pub,
        {"outcome": "recorded", "class": "class_r"},
        now=NOW,
    )


def test_promote_rederives_the_barrier_for_a_late_disposition(tmp_path: Path) -> None:
    """A disposition journaled between verify and promote lands in the
    promoted generation's withdrawn.conf — the carry is re-derived
    (D-P35.54-1) and latest.json stamps the digest it was composed from."""
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _promote_ready(store, PUB_B, "sig-2026-10-02.1")
    _approval(store)
    # the late disposition — recorded after the prior generation composed
    from exports.release import ReleaseRegistry
    from policy.eligibility import new_disposition

    view = rr.registry_view(store, tmp_path / "view")
    reg = ReleaseRegistry(view)
    reg.save_withdrawals(
        [
            new_disposition(
                target_kind=TargetKind.ENTITY,
                target_id=EID,
                disposition=Disposition.WITHDRAW,
                reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
                authority="OPS-late",
                decided_at=NOW,
                seq=0,
            )
        ]
    )
    _put(store, "registry/withdrawals.json", json.loads((view / "withdrawals.json").read_text()))
    out = rc.verb_promote(
        store,
        apply_=True,
        publication_id=PUB_B,
        approval="go-pub",
        derive_barrier=rr.derive_withdrawal_barrier,
        now=NOW,
    )
    assert out["applied"] is True and out["barrier"] == "re-derived"
    conf = store.read("registry/conf/2/withdrawn.conf").decode()
    uris = _deny_uris(conf)
    assert f"/r/{PUB_A}/c/sig_graph/entity/deployment/{EID}" in uris
    latest = rc.read_generation(store, 2)
    assert latest["withdrawals_sha256"] == rr.withdrawals_sha256(store)


def test_promote_carries_the_barrier_when_undrifted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _promote_ready(store, PUB_B, "sig-2026-10-02.1")
    _approval(store)
    out = rc.verb_promote(
        store,
        apply_=True,
        publication_id=PUB_B,
        approval="go-pub",
        derive_barrier=rr.derive_withdrawal_barrier,
        now=NOW,
    )
    assert out["applied"] is True and out["barrier"] == "carried"
    # the marker lands even on the carried path — a LATER promote can detect
    # drift from the pointer alone
    assert rc.read_generation(store, 2)["withdrawals_sha256"] == rr.withdrawals_sha256(store)


def test_promote_refuses_when_the_registry_drifts_inside_the_lock(tmp_path: Path) -> None:
    """The in-lock re-check: a derive hook that lands a NEW disposition while
    composing simulates drift between compose and the write — promote
    refuses; the next compose re-derives fresh."""
    store = _store(tmp_path)
    _seed_pub(store, PUB_A, "sig-2026-10-01.1")
    _seed_registry(store, [(PUB_A, "sig-2026-10-01.1")])
    _promote_ready(store, PUB_B, "sig-2026-10-02.1")
    _approval(store)
    # drift BEFORE compose → the derive hook runs; the hook mutating the
    # registry AGAIN simulates a disposition landing between the composed
    # barrier and the locked write — the in-lock re-check catches it.
    _put(
        store,
        "registry/withdrawals.json",
        {"schema": "sig.withdrawal-registry/1", "entries": [{"marker": "pre-compose"}]},
    )

    def sneaky_derive(store: rp.Store, work: Path, *, active_pub: str | None = None) -> bytes:
        _put(
            store,
            "registry/withdrawals.json",
            {"schema": "sig.withdrawal-registry/1", "entries": [{"marker": "inside-window"}]},
        )
        return b"# derived\n"

    with pytest.raises(rp.PipelineError) as exc:
        rc.verb_promote(
            store,
            apply_=True,
            publication_id=PUB_B,
            approval="go-pub",
            derive_barrier=sneaky_derive,
            now=NOW,
        )
    assert exc.value.code == "withdrawal-drift"
    assert store.read("registry/conf/2/latest.json") is None  # nothing written
