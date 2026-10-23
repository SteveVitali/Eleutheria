# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Release reversal verbs — rollback / clear-latest / withdraw / import-floor /
the conf-gen regression probe (P35.55, REL-08; G3 §7.3/§8.1–8.5/RR-7).

Every verb here *wraps* the landed machinery — the withdrawal registry,
tombstone/deny-map emitters, rollback and pointer-clearing bodies live in
``exports.release``; the immutable ``conf/<gen>`` writer and the digest-pinned
api→web roll legs live in ``ops.release_conf``. This module adds the operator
surface the §8 contract fixes around them:

* **The layout bridge** — ``exports.release``'s registry functions take one
  directory that holds both the registry documents *and* ``staged/``; the §4.1
  bucket layout splits them into ``registry/*`` and ``staged/*`` objects. A
  scratch *view* rebuilds the one-directory shape: registry documents are
  copied in, ``staged`` is a symlink for ``LocalDirStore`` (writes land in
  place) or a mirrored tree for ``GcsStore`` (changed bytes write back under
  metageneration preconditions; objects the withdrawal removed are deleted —
  the disposition-authorised removals, the only deletes the layout allows).
* **The authority check** — ``--authority``/``--go`` name a
  ``registry/authorities/<name>.json`` ``sig.operator-authority/1`` record the
  operator wrote. The verb verifies it (present, schema'd, unrevoked,
  unexpired) and records its digest — it never fabricates one (SIG-SEC-010).
* **``rollback --to <pub|label|legacy-YYYYMMDD> --reason <text>``** — resolves
  the target, re-applies the CURRENT withdrawal set through the landed
  ``exports.release.rollback`` (a roll to a denied or unstaged pub is refused
  there), writes ``conf/<gen+1>`` with ``latest = <target>`` + the re-derived
  deny map, rolls api→web as NEW revisions (never a traffic reversion — RR-7:
  an old revision's pinned ``SIG_CONF_GEN`` would re-serve withdrawn routes).
* **``clear-latest``** — the archive-only case (§8.2): the latest pointer is
  removed through the landed ``clear_latest_pointer``; the new generation's
  pointer is null and the roll env points the latest view at ``v/none/`` — a
  guaranteed-absent tree, so every latest-view route 404s while ``/releases/``
  and the gated namespaces keep serving.
* **``withdraw --disposition <file> --authority <ref>``** — the §8.3 order, in
  order: append-only disposition INSERT → ``record_withdrawal`` →
  ``apply_withdrawals`` over every staged namespace → ``conf/<gen+1>`` with
  the full-alias ``withdrawn.conf`` → api→web roll → cache/CDN/R2 purge hooks
  (wired, dormant — a missing/disabled mirror is a recorded no-op, never an
  error) → every-alias probes → a dated receipt under ``registry/receipts/``.
  ``--purge-versions`` (Part VIII/legal takedowns) additionally removes the
  *noncurrent object versions* of the bucket objects the withdrawal removed —
  bucket objects only; the claim spine is never touched (P39).
* **``import-floor --from <dir>``** — the §8.5 legacy floor: the then-live
  root tree imports to ``staged/v/legacy-<YYYYMMDD>/``, labelled
  ``legacy-<date>`` (never a publication id), recorded under
  ``registry/floor.json``. ``rollback --to legacy-<date>`` serves it.
* **``conf-gen-probe``** — the P1 regression probe (G3 §1.1/RR-7): every
  origin's served ``X-SIG-Conf-Gen`` must equal the registry's recorded
  generation; an older — or unrecorded — generation fails loud.

Rollback and withdrawal journals are append-only: dispositions are INSERTs,
tombstones immutable, reinstatement a NEW disposition plus a NEW release —
no UPDATE/DELETE path exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json
from exports.release import (
    ReleaseError,
    ReleaseRegistry,
    apply_withdrawals,
    clear_latest_pointer,
    record_withdrawal,
)
from exports.release import (
    rollback as exports_rollback,
)
from policy.eligibility import (
    DENYING,
    Disposition,
    DispositionRecord,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

from . import gcs as _gcs
from . import probe_run
from . import release_conf as rc
from . import release_pipeline as rp

# --------------------------------------------------------------------------- #
# Schemas + names                                                            #
# ---------------------------------------------------------------------------#

ORDER_SCHEMA = "sig.withdrawal-order/1"
AUTHORITY_SCHEMA = "sig.operator-authority/1"
FLOOR_SCHEMA = "sig.legacy-floor/1"
RECEIPT_SCHEMA = "sig.withdrawal-receipt/1"
LATEST_SCHEMA_V1 = "sig.latest-pointer/1"

AUTHORITIES_PREFIX = "registry/authorities/"
RECEIPTS_PREFIX = "registry/receipts/"
FLOOR_OBJECT = "registry/floor.json"
STAGED_DENY_MAP = "staged/conf/withdrawn_routes.conf"

#: The archive-only latest-view sentinel — ``staged/v/none/`` is never staged,
#: so every latest-view route 404s while /releases/ + the gated namespaces
#: keep serving (the entrypoint still gets a fully-set env pair — never a
#: half-set refusal).
NO_LATEST_SENTINEL = "none"
NO_LATEST_LABEL = "no-current-release"

#: ``--to`` accepts a pub id, a label, or the legacy floor label.
LEGACY_LABEL_RE = re.compile(r"^legacy-(\d{8})$")

#: The registry documents the bridge view carries.
_VIEW_REGISTRY_FILES = (
    "catalog.json",
    "compat_index.json",
    "withdrawals.json",
    "labels.json",
)

#: A fetcher for the origin probes: url -> (status, headers, body).
Fetch = Callable[[str], tuple[int, dict[str, str], bytes]]


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(obj: Any) -> bytes:
    return canonical_json(obj)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def withdrawals_sha256(store: rp.Store) -> str:
    """The digest of the registry's withdrawal document — the marker every
    generation's ``latest.json`` records so a later promote can detect a
    disposition that arrived after the deny map was composed (D-P35.54-1)."""
    return _sha256(store.read("registry/withdrawals.json") or b"")


# --------------------------------------------------------------------------- #
# The authority check — verifies a record, never writes one (SIG-SEC-010)    #
# ---------------------------------------------------------------------------#


def check_authority(store: rp.Store, name: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Verify ``registry/authorities/<name>.json`` — the operator's go /
    pre-authorisation / takedown authority record. Returns the ref recorded
    into the journal + pointer; refusals raise PipelineError."""
    if not name or "/" in name or name.startswith("."):
        raise rp.PipelineError(
            "bad-authority-name",
            f"authority names a single object under {AUTHORITIES_PREFIX} — got {name!r}",
        )
    obj = f"{AUTHORITIES_PREFIX}{name}"
    body = store.read(obj)
    if body is None:
        raise rp.PipelineError(
            "authority-absent",
            f"{obj} does not exist — the operator writes the authority "
            "record; the verb checks it, never creates one (SIG-SEC-010)",
        )
    try:
        rec = json.loads(body)
    except ValueError as exc:
        raise rp.PipelineError("authority-unreadable", f"{obj} is not JSON: {exc}") from exc
    if not isinstance(rec, dict) or rec.get("schema") != AUTHORITY_SCHEMA:
        raise rp.PipelineError(
            "authority-schema",
            f"{obj} does not declare schema {AUTHORITY_SCHEMA!r}",
        )
    reasons: list[str] = []
    if rec.get("revoked") is True:
        reasons.append("the record carries revoked=true")
    expires = rec.get("expires_at")
    if expires:
        from exports.release_identity import parse_instant

        exp_dt = parse_instant(str(expires))
        if exp_dt is None:
            reasons.append(f"expires_at {expires!r} is not an ISO instant")
        elif exp_dt <= (now or _now()):
            reasons.append(f"the record expired at {expires}")
    if not str(rec.get("ref") or "").strip():
        reasons.append("the record carries no ref (the go/pre-authorisation id)")
    if reasons:
        raise rp.PipelineError(
            "authority-refused",
            f"{obj} does not authorise the action: " + "; ".join(reasons),
        )
    return {
        "object": obj,
        "sha256": _sha256(body),
        "kind": rec.get("kind"),
        "ref": rec.get("ref"),
        "issued_at": rec.get("issued_at"),
    }


# --------------------------------------------------------------------------- #
# The withdrawal order — sig.withdrawal-order/1                               #
# ---------------------------------------------------------------------------#


def load_order(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a ``sig.withdrawal-order/1`` file → ``(entries, meta)``.

    Accepts either the bare JSON list the §8.3 contract fixes or a document
    carrying ``entries`` + optional ``order_id``/``issued_at``/``note``.
    Every entry validates: ``target_kind`` is a real TargetKind,
    ``disposition`` is a real Disposition (an ``allow`` row is the
    reinstatement path — a NEW disposition, never an edit),
    ``reason_category`` a real ReasonCategory; ``compartment``,
    ``evidence_claim_id`` and ``supersedes`` are optional strings.
    ``seq`` is assigned at INSERT — never taken from the file.
    """
    p = Path(path)
    if not p.is_file():
        raise rp.PipelineError("order-absent", f"--disposition {p} does not exist")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise rp.PipelineError("order-unreadable", f"{p} is not JSON: {exc}") from exc
    meta: dict[str, Any] = {"order_sha256": _sha256(p.read_bytes())}
    if isinstance(doc, dict):
        meta["order_id"] = doc.get("order_id")
        meta["issued_at"] = doc.get("issued_at")
        meta["note"] = doc.get("note")
        if doc.get("schema") not in (None, ORDER_SCHEMA):
            raise rp.PipelineError(
                "order-schema", f"{p} declares schema {doc.get('schema')!r}, not {ORDER_SCHEMA!r}"
            )
        entries = doc.get("entries")
    else:
        entries = doc
    if not isinstance(entries, list) or not entries:
        raise rp.PipelineError(
            "order-empty", f"{p} carries no disposition entries — an empty order writes nothing"
        )
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise rp.PipelineError("order-entry", f"entry {i} is not an object")
        try:
            kind = TargetKind(str(raw["target_kind"]))
            disp = Disposition(str(raw["disposition"]))
            reason = ReasonCategory(str(raw["reason_category"]))
        except (KeyError, ValueError) as exc:
            raise rp.PipelineError(
                "order-entry",
                f"entry {i} carries a bad target_kind/disposition/reason_category: {exc}",
            ) from exc
        target_id = str(raw.get("target_id") or "").strip()
        if not target_id:
            raise rp.PipelineError("order-entry", f"entry {i} carries no target_id")
        compartment = raw.get("compartment")
        if compartment is not None and not str(compartment).strip():
            raise rp.PipelineError("order-entry", f"entry {i} carries an empty compartment scope")
        out.append(
            {
                "target_kind": kind,
                "target_id": target_id,
                "disposition": disp,
                "reason_category": reason,
                "compartment": str(compartment).strip() if compartment else None,
                "evidence_claim_id": raw.get("evidence_claim_id"),
                "supersedes": raw.get("supersedes"),
            }
        )
    meta["entries"] = len(out)
    return out, meta


def _order_records(
    entries: Sequence[dict[str, Any]],
    *,
    authority_ref: dict[str, Any],
    base_seq: int,
    now: datetime,
) -> list[DispositionRecord]:
    """Stamp the order entries into append-only DispositionRecords — the file
    registry's writer stamps ``decided_at`` exactly as the claim spine's
    ``DEFAULT clock_timestamp()`` would (one clock authority, never a typed
    input); ``seq`` is the append position (insert order, §8.3)."""
    records: list[DispositionRecord] = []
    for i, e in enumerate(entries):
        records.append(
            new_disposition(
                target_kind=e["target_kind"],
                target_id=e["target_id"],
                disposition=e["disposition"],
                reason_category=e["reason_category"],
                authority=str(authority_ref.get("ref") or authority_ref.get("object")),
                decided_at=now,
                evidence_claim_id=e.get("evidence_claim_id"),
                supersedes=e.get("supersedes"),
                seq=base_seq + i,
                compartment=e.get("compartment"),
            )
        )
    return records


# --------------------------------------------------------------------------- #
# The layout bridge — the old-layout view over the §4.1 object layout        #
# ---------------------------------------------------------------------------#


def _view_catalog(store: rp.Store, view: Path) -> None:
    """``view/catalog.json`` — the base registry catalog merged with one
    entry per staged release (from its own ``catalog_entry.json`` — the
    release's stamped metadata, never invented), so
    ``ReleaseRegistry.find`` resolves every staged pub."""
    base: dict[str, Any] = {"schema": "sig.publication-catalog/1", "publications": []}
    body = store.read("registry/catalog.json")
    if body is not None:
        try:
            doc = json.loads(body)
            if isinstance(doc, dict):
                base = doc
        except ValueError:
            base = {"schema": "unreadable", "publications": []}
    pubs = {str(e.get("publication_id")) for e in base.get("publications") or []}
    for name in store.list("staged/releases/"):
        if not name.endswith("/catalog_entry.json"):
            continue
        entry_body = store.read(name)
        if entry_body is None:
            continue
        try:
            entry = json.loads(entry_body)
        except ValueError:
            continue
        pub = str(entry.get("publication_id") or name.split("/")[2])
        if pub not in pubs:
            base.setdefault("publications", []).append(entry)
            pubs.add(pub)
    (view / "catalog.json").write_bytes(_canonical(base))


def _view_latest(store: rp.Store, view: Path) -> None:
    """``view/latest.json`` — the registry pointer verbatim, or synthesised
    from the CURRENT conf generation's pointer (the new-model pointer lives
    in ``conf/<gen>/latest.json``; the exports machinery reads the
    file-layout pointer — the synthesis maps the same fact, never invents)."""
    body = store.read("registry/latest.json")
    if body is None:
        gen = rc.current_generation(store)
        doc = rc.read_generation(store, gen) if gen else None
        if doc and rc.PUB_RE.match(str(doc.get("publication_id") or "")):
            body = _canonical(
                {
                    "schema": LATEST_SCHEMA_V1,
                    "publication_id": doc["publication_id"],
                    "label": doc.get("label"),
                    "manifest_sha256": doc.get("manifest_sha256"),
                    "data_release_id": doc.get("label"),
                    "ordinal": -1,
                }
            )
    if body is not None:
        (view / "latest.json").write_bytes(body)


def registry_view(store: rp.Store, work: Path, *, link_staged: bool = True) -> Path:
    """Build the one-directory registry view the exports machinery consumes.

    ``view/{catalog,compat_index,withdrawals,labels}.json`` are copies;
    ``view/latest.json`` is the registry pointer or the current generation's
    synthesised; ``view/catalog.json`` additionally names every staged pub;
    ``view/activations/`` mirrors the receipts; ``view/staged`` is a symlink
    for ``LocalDirStore`` when ``link_staged`` (mutations land in place) —
    pass ``link_staged=False`` for a derivation that must not touch
    ``staged/**`` (promote's metadata-only contract, SIG-REL-006) — or a
    mirrored tree for ``GcsStore``.
    """
    view = work / "registry-view"
    view.mkdir(parents=True, exist_ok=True)
    for name in _VIEW_REGISTRY_FILES:
        body = store.read(f"registry/{name}")
        if body is not None:
            (view / name).write_bytes(body)
    _view_latest(store, view)
    _view_catalog(store, view)
    for name in store.list("registry/activations/"):
        body = store.read(name)
        if body is not None:
            target = view / "activations" / name.rsplit("/", 1)[-1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    staged_link = view / "staged"
    if link_staged and isinstance(store, rp.LocalDirStore):
        staged_root = Path(store.root) / "staged"
        staged_root.mkdir(parents=True, exist_ok=True)
        os.symlink(staged_root, staged_link)
    else:
        staged_link.mkdir()
        for name in store.list("staged/"):
            body = store.read(name)
            if body is not None:
                target = staged_link / name[len("staged/") :]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
    return view


def derive_withdrawal_barrier(
    store: rp.Store, work: Path, *, active_pub: str | None = None
) -> bytes:
    """Re-derive the deny map for a NEW conf generation from the CURRENT
    withdrawal registry (D-P35.54-1): ``promote`` composes through this hook
    so a disposition recorded between the candidate's verify and its
    promote lands in the promoted generation's ``withdrawn.conf``.

    ``staged`` is MIRRORed (never symlinked) — the barrier is derived over a
    throwaway copy; promote stays metadata-only and no ``staged/**`` byte is
    touched (SIG-REL-006). A malformed withdrawal registry surfaces as the
    apply's own error — the caller's promote refuses, fail-closed.
    """
    view = registry_view(store, work, link_staged=False)
    apply_withdrawals(
        view / "staged",
        ReleaseRegistry(view).withdrawals(),
        active_pub=active_pub,
    )
    return _deny_map_bytes(view)


def _write_back_json(store: rp.Store, name: str, body: bytes) -> None:
    """Metageneration-matched write of a registry document."""
    meta = store.stat(name)
    if meta is None:
        store.insert(name, body, content_type="application/json")
    else:
        store.replace(
            name, body, generation=int(meta["generation"]), content_type="application/json"
        )


def sync_registry_back(store: rp.Store, view: Path) -> dict[str, Any]:
    """Write the view's registry documents + new activations back to the
    store; returns the sync summary for the journal."""
    synced: dict[str, Any] = {"written": [], "inserted": [], "latest_cleared": False}
    wbody = view / "withdrawals.json"
    if wbody.is_file():
        _write_back_json(store, "registry/withdrawals.json", wbody.read_bytes())
        synced["written"].append("registry/withdrawals.json")
    lbody = view / "latest.json"
    if lbody.is_file():
        _write_back_json(store, "registry/latest.json", lbody.read_bytes())
        synced["written"].append("registry/latest.json")
    elif store.stat("registry/latest.json") is not None:
        store.delete("registry/latest.json")
        synced["latest_cleared"] = True
    known = set(store.list("registry/activations/"))
    act_dir = view / "activations"
    if act_dir.is_dir():
        for p in sorted(act_dir.iterdir()):
            name = f"registry/activations/{p.name}"
            if name not in known:
                store.insert(name, p.read_bytes(), content_type="application/json")
                synced["inserted"].append(name)
    return synced


def sync_staged_back(store: rp.Store, view: Path) -> dict[str, Any]:
    """For a non-local store: write the applied staged tree back — changed
    bytes under metageneration preconditions; remote objects the apply
    removed are deleted (disposition-authorised removals only — the diff is
    the removal set). LocalDirStore mutations already landed via the
    symlink; returns the object names removed (``--purge-versions``' scope)."""
    if isinstance(store, rp.LocalDirStore):
        return {"removed": [], "written": "in-place (local dir store)"}
    staged_link = view / "staged"
    local: dict[str, bytes] = {}
    for p in sorted(staged_link.rglob("*")):
        if p.is_file():
            local[f"staged/{p.relative_to(staged_link).as_posix()}"] = p.read_bytes()
    remote = set(store.list("staged/"))
    written = 0
    for name, body in local.items():
        meta = store.stat(name)
        if meta is None:
            store.insert(name, body, content_type=_media_type(name))
            written += 1
        elif meta.get("md5Hash") != rp._md5_b64(body):
            store.replace(
                name, body, generation=int(meta["generation"]), content_type=_media_type(name)
            )
            written += 1
    removed = sorted(remote - set(local))
    for name in removed:
        store.delete(name)
    return {"removed": removed, "written": written}


def staged_removal_diff(store: rp.Store, before: set[str]) -> list[str]:
    """The staged objects a disposition apply removed (LocalDirStore path —
    the same set ``sync_staged_back`` computes for a bucket store)."""
    return sorted(before - set(store.list("staged/")))


def _media_type(name: str) -> str:
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".html"):
        return "text/html"
    if name.endswith(".jsonl"):
        return "application/x-ndjson"
    return "application/octet-stream"


# --------------------------------------------------------------------------- #
# The generation composer for the reversal verbs                              #
# ---------------------------------------------------------------------------#


def catalog_v2_reversal(
    store: rp.Store,
    *,
    gen: int,
    current_pub: str | None,
    current_label: str | None,
    current_activated_at: str | None,
    now: datetime,
) -> dict[str, Any]:
    """``sig.publication-catalog/2`` for a reversal generation — the current
    latest pointer names the row that stays ``promoted``; every other pub
    derives from the journal fold (``withdrawn-whole`` wins over
    ``superseded`` — a wholly withdrawn release states itself, §3.1)."""
    states = rc._publication_states(store)
    labels = rc.read_label_map(store)
    history = rc._generation_history(store)
    entries: list[dict[str, Any]] = []
    all_pubs = sorted(
        set(states) | set(labels) | set(history) | ({current_pub} if current_pub else set())
    )
    for p in all_pubs:
        if p == current_pub:
            state = "promoted"
            activated_at = current_activated_at
            p_label = current_label
            p_meta = rc.read_release_meta(store, p)
        else:
            fold = states.get(p)
            prior = history.get(p)
            if fold == "withdrawn-whole":
                state = "withdrawn-whole"
            elif prior:
                state = "superseded"
            else:
                state = fold or "never-promoted"
            activated_at = (prior or {}).get("activated_at")
            p_label = (prior or {}).get("label") or labels.get(p)
            p_meta = rc.read_release_meta(store, p) if state != "never-promoted" else {}
        entries.append(
            {
                "publication_id": p,
                "label": p_label,
                "state": state,
                "as_of_world": p_meta.get("as_of_world"),
                "activated_at": activated_at,
                "code": {
                    "commit": p_meta.get("code_commit"),
                    "tag": p_meta.get("code_tag"),
                },
                "manifest_sha256": p_meta.get("manifest_sha256"),
                "descriptor_sha256": p_meta.get("descriptor_sha256"),
            }
        )
    return {
        "schema": rc.CATALOG_SCHEMA_V2,
        "conf_gen": gen,
        "generated_at": _iso(now),
        "generator": (
            "sig-ops release (rollback|clear-latest|withdraw) — the release tool alone (C4 NEW-10)"
        ),
        "entries": entries,
    }


def compose_reversal_generation(
    store: rp.Store,
    *,
    gen: int,
    latest_doc: dict[str, Any],
    withdrawn_conf: bytes,
    current_pub: str | None,
    now: datetime,
) -> dict[str, bytes]:
    """Every ``registry/conf/<gen>/`` object a reversal verb writes —
    ``promoted.map`` + ``selectors.conf`` carried byte-identical (the
    promoted set never shrinks), ``latest.json`` the new pointer doc,
    ``withdrawn.conf`` the re-derived deny map (never a carried copy — the
    rollback/withdraw always re-applies the CURRENT registry first),
    ``labels.conf`` + the ``releases/`` index set recomposed."""
    prior_gen = gen - 1
    catalog = catalog_v2_reversal(
        store,
        gen=gen,
        current_pub=current_pub,
        current_label=str(latest_doc.get("label") or "") or None,
        current_activated_at=str(latest_doc.get("activated_at") or "") or None,
        now=now,
    )
    latest_bytes = _canonical(latest_doc)
    return {
        "promoted.map": rc._carry_or_placeholder(
            store,
            prior_gen,
            "promoted.map",
            placeholder=rc.render_promoted_map(set(), gen=gen),
        ),
        "latest.json": latest_bytes,
        "withdrawn.conf": withdrawn_conf,
        "selectors.conf": rc._carry_or_placeholder(
            store,
            prior_gen,
            "selectors.conf",
            placeholder=rc._empty_selectors(gen),
        ),
        "labels.conf": rc.render_labels_conf(rc.read_label_map(store), gen=gen),
        "releases/index.html": rc.releases_index_html(catalog, gen=gen),
        "releases/catalog.json": _canonical(catalog),
        "releases/latest.json": latest_bytes,
    }


# --------------------------------------------------------------------------- #
# Roll legs — api → web, NEW revisions by digest (never a traffic reversion) #
# ---------------------------------------------------------------------------#


def _plan_rolls(
    *,
    next_gen: int,
    latest_pub_env: str,
    latest_label_env: str,
    api_image: str | None,
    web_image: str | None,
    min_instances: int,
    project: str | None,
    region: str | None,
    execute_rolls: bool,
    gcloud: Any,
) -> list[rc.ServiceRoll]:
    """Plan the api→web roll legs. The env swap to a NEW revision is the
    whole roll — ``gcloud run services update`` only; traffic reversion is
    forbidden (RR-7): an old revision's pinned SIG_CONF_GEN would re-serve
    routes a later withdrawal denied."""
    if not (api_image and web_image and project and region):
        return []
    web_env = {
        "SIG_CONF_GEN": str(next_gen),
        "SIG_LATEST_PUB": latest_pub_env,
        "SIG_LATEST_LABEL": latest_label_env,
        "SIG_STAGING": "0",
    }
    api_env = {"SIG_CONF_GEN": str(next_gen), "SIG_LATEST_PUB": latest_pub_env}
    legs = [
        rc.plan_service_roll(
            "sig-api",
            image_digest=api_image,
            env=api_env,
            project=project,
            region=region,
            min_instances=None,
            gcloud=gcloud if execute_rolls else None,
        ),
        rc.plan_service_roll(
            "sig-web",
            image_digest=web_image,
            env=web_env,
            project=project,
            region=region,
            min_instances=min_instances,
            gcloud=gcloud if execute_rolls else None,
        ),
    ]
    return legs


def _execute_or_prepare_rolls(
    legs: list[rc.ServiceRoll],
    *,
    execute_rolls: bool,
    project: str | None,
    region: str | None,
    gcloud: Any,
) -> None:
    if not execute_rolls:
        for leg in legs:
            leg.detail = (
                "prepared_not_executed — the composed stack flips by "
                "recreating the service with this env; the hosted leg "
                "is the operator's (OP-24)"
            )
        return
    if not project or not region:
        raise rp.PipelineError(
            "roll-args-missing",
            "--execute-rolls needs --project + --region",
        )
    if gcloud is None:
        raise rp.PipelineError(
            "roll-runner-missing",
            "--execute-rolls needs a gcloud runner (cli.py wires "
            "job_roll.gcloud_cli; tests inject one)",
        )
    for idx, leg in enumerate(legs):
        try:
            rc.apply_service_roll(leg, project=project, region=region, gcloud=gcloud)
        except rp.PipelineError as exc:
            leg.status = "refused"
            leg.detail = str(exc)
            later = legs[idx + 1].service if idx + 1 < len(legs) else None
            raise rp.PipelineError(
                exc.code,
                f"the {leg.service} leg refused — "
                + (
                    f"the flip aborted before {later} touched traffic "
                    if later
                    else "the roll did not converge "
                ),
            ) from exc


def _roll_rows(legs: list[rc.ServiceRoll]) -> list[dict[str, Any]] | None:
    return [
        {
            "service": leg.service,
            "image_digest": leg.image_digest,
            "env": leg.env,
            "min_instances": leg.min_instances,
            "status": leg.status,
            "revision": leg.revision,
            "detail": leg.detail,
            "args": leg.args,
        }
        for leg in legs
    ] or None


# --------------------------------------------------------------------------- #
# Purge — the dormant CDN/R2 hooks + --purge-versions (bucket objects only)   #
# ---------------------------------------------------------------------------#


def purge_hooks(
    *,
    denied_routes: Sequence[str],
    removed_objects: Sequence[str],
    mirrors_path: str | Path | None = None,
    gcloud: Any = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """The §8.3 step-5 purge legs — CDN/R2 cache purges keyed on
    ``ops/mirrors.toml``. Wired, dormant: every mirror row disabled or
    absent records ``dormant`` with its reason — a missing mirror
    configuration is a no-op, never an error (the mirror manifest is
    committed gate-pending/disabled until the operator's own leg)."""
    now = now or _now()
    legs: list[dict[str, Any]] = []
    path = Path(mirrors_path) if mirrors_path else Path("ops/mirrors.toml")
    if not path.is_file():
        legs.append(
            {
                "kind": "mirror-purge",
                "status": "dormant",
                "reason": f"{path} absent — no mirror configuration; nothing to purge",
            }
        )
        return legs
    import tomllib

    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    mirrors = [m for m in doc.get("mirror") or [] if isinstance(m, dict)]
    enabled = [m for m in mirrors if m.get("enabled") is True]
    for m in mirrors:
        if m.get("enabled") is True:
            continue
        legs.append(
            {
                "kind": "mirror-purge",
                "mirror": m.get("name"),
                "status": "dormant",
                "reason": "mirror row disabled/gate-pending — the enable leg is "
                "the operator's (the committed rows name their gates)",
            }
        )
    for m in enabled:
        # An enabled object-store mirror plans a key-delete per removed
        # object + a CDN invalidation per denied route; executed only with
        # an injected runner — recorded either way.
        legs.append(
            {
                "kind": "mirror-purge",
                "mirror": m.get("name"),
                "status": "planned" if gcloud is None else "executed",
                "objects": list(removed_objects),
                "routes": list(denied_routes),
            }
        )
    return legs


def purge_noncurrent_versions(store: rp.Store, objects: Sequence[str]) -> dict[str, Any]:
    """``--purge-versions`` — delete the NONCURRENT versions of the bucket
    objects the withdrawal removed. Bucket objects only — the claim spine
    is never touched; a store without versioning records a no-op."""
    if not objects:
        return {"status": "nothing-removed", "versions_deleted": 0}
    client = getattr(store, "client", None)
    if client is None or not hasattr(client, "list_object_versions"):
        return {
            "status": "noop-local-store",
            "detail": "a local dir store carries no object versions — "
            "the removed names are recorded; a bucket run deletes their "
            "noncurrent generations",
            "objects": list(objects),
            "versions_deleted": 0,
        }
    deleted = 0
    details: list[dict[str, Any]] = []
    prefix = getattr(store, "prefix", "")

    def _full(name: str) -> str:
        return f"{prefix}/{name}" if prefix else name

    for name in objects:
        versions = client.list_object_versions(_full(name))
        # the live generation is the newest non-deleted version — NEVER
        # purged (the purge removes history only; the tombstone/replacement
        # generation stays so the object still answers).
        live_gens = {int(v["generation"]) for v in versions if not v.get("timeDeleted")}
        live_gen = max(live_gens) if live_gens else None
        removed = 0
        for v in versions:
            g = int(v["generation"])
            if v.get("timeDeleted") or g == live_gen:
                continue
            client.delete_object(_full(name), generation=g)
            removed += 1
        deleted += removed
        details.append({"object": name, "versions": len(versions), "purged": removed})
    return {"status": "purged", "versions_deleted": deleted, "objects": details}


# --------------------------------------------------------------------------- #
# The every-alias probe (§8.3 step 6) + the P1 conf-gen regression probe      #
# ---------------------------------------------------------------------------#


def _default_fetch(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 — operator-named origins
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def probe_denied_aliases(
    *,
    withdrawn_conf: bytes,
    view: Path | None,
    denied_routes: Sequence[str],
    origins: Sequence[str],
    fetch: Fetch | None = None,
) -> list[dict[str, Any]]:
    """Every alias of every denied route is verified: structurally — the
    ``location =`` line exists in the new generation's ``withdrawn.conf``
    and its ``error_page 410`` body object exists under
    ``staged/conf/tombstone/`` — and, for each ``--origin`` given, by HTTP
    (410 with the route's own tombstone body, never a generic page)."""
    fetch = fetch or _default_fetch
    conf_text = withdrawn_conf.decode("utf-8", errors="replace")
    conf_lines = {
        ln.strip() for ln in conf_text.splitlines() if ln.strip().startswith("location =")
    }
    body_paths = {
        m.group(2)
        for ln in conf_lines
        if (m := re.match(r"^location = (\S+) \{ error_page 410 (\S+); return 410; \}$", ln))
    }
    legs: list[dict[str, Any]] = []
    for route in sorted(denied_routes):
        aliases = (
            [f"/{route}", f"/{route}/", f"/{route}/index.html"]
            if not route.endswith(".json")
            else [f"/{route}"]
        )
        for alias in aliases:
            line = next((ln for ln in conf_lines if ln.startswith(f"location = {alias} ")), None)
            ok = line is not None
            detail = f"deny line present for {alias}" if ok else f"NO deny line for {alias}"
            legs.append(
                {
                    "alias": alias,
                    "kind": "deny-line",
                    "status": "pass" if ok else "fail",
                    "detail": detail,
                }
            )
    if view is not None:
        tomb_root = view / "staged" / "conf" / "tombstone"
        for body in sorted(body_paths):
            exists = (tomb_root / Path(body).name).is_file()
            legs.append(
                {
                    "alias": body,
                    "kind": "tombstone-body",
                    "status": "pass" if exists else "fail",
                    "detail": f"tombstone body {body} staged"
                    if exists
                    else f"tombstone body {body} MISSING",
                }
            )
    for origin in origins:
        origin = origin.rstrip("/")
        for route in sorted(denied_routes):
            for alias in (
                [f"/{route}", f"/{route}/", f"/{route}/index.html"]
                if not route.endswith(".json")
                else [f"/{route}"]
            ):
                try:
                    status, _h, _b = fetch(f"{origin}{alias}")
                    ok = status == 410
                    legs.append(
                        {
                            "alias": f"{origin}{alias}",
                            "kind": "http-probe",
                            "status": "pass" if ok else "fail",
                            "detail": f"HTTP {status} (410 required — the alias must deny)",
                        }
                    )
                except Exception as exc:  # noqa: BLE001 — a probe leg records, never dies
                    legs.append(
                        {
                            "alias": f"{origin}{alias}",
                            "kind": "http-probe",
                            "status": "fail",
                            "detail": f"{type(exc).__name__}: {exc}",
                        }
                    )
    return legs


def conf_gen_probe(
    store: rp.Store,
    *,
    origins: Sequence[str],
    fetch: Fetch | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """The P1 conf-generation regression probe: the recorded generation is
    read from the registry; every origin's ``X-SIG-Conf-Gen`` header must
    equal it. An OLDER generation served is the rollback-revives-withdrawn-
    routes alarm (RR-7); a NEWER unrecorded one means the registry record is
    stale — both fail. Emits a ``sig.probe-run/1`` record."""
    fetch = fetch or _default_fetch
    recorded = rc.current_generation(store)
    checks: dict[str, probe_run.CheckResult] = {}
    for origin in origins:
        origin = origin.rstrip("/")
        leg = f"conf-gen:{origin}"
        try:
            _status, headers, _b = fetch(f"{origin}/")
        except Exception as exc:  # noqa: BLE001 — recorded, never fabricated
            checks[leg] = probe_run.CheckResult(
                "skipped",
                {
                    "reason": (
                        "origin unreachable — cannot rule out a regression: "
                        f"{type(exc).__name__}: {exc}"
                    )
                },
            )
            continue
        served_raw = headers.get("X-SIG-Conf-Gen") or headers.get("x-sig-conf-gen")
        if served_raw is None:
            checks[leg] = probe_run.CheckResult(
                "fail",
                {
                    "reason": (
                        "the origin carries no X-SIG-Conf-Gen header — a "
                        "non-release config is serving"
                    )
                },
            )
            continue
        served = int(served_raw) if str(served_raw).isdigit() else -1
        if served == recorded:
            checks[leg] = probe_run.CheckResult(
                "pass", {"served_gen": served, "recorded_gen": recorded}
            )
        elif served < recorded:
            checks[leg] = probe_run.CheckResult(
                "fail",
                {
                    "reason": "served-older-generation — the P1 alarm: an "
                    "older conf generation is serving (a withdrawn route "
                    "may be reachable)",
                    "served_gen": served,
                    "recorded_gen": recorded,
                },
            )
        else:
            checks[leg] = probe_run.CheckResult(
                "fail",
                {
                    "reason": "served-unrecorded-generation — the origin "
                    "serves a generation the registry never recorded",
                    "served_gen": served,
                    "recorded_gen": recorded,
                },
            )
    if not checks:
        checks["conf-gen:no-origins"] = probe_run.CheckResult(
            "skipped", {"reason": "no --origin named — nothing evaluated"}
        )
    return probe_run.build_record(
        "conf-gen-regression",
        checks,
        subject={"origins": list(origins)},
        release={"recorded_conf_gen": recorded},
        now=now,
    )


# --------------------------------------------------------------------------- #
# Shared verb plumbing                                                        #
# ---------------------------------------------------------------------------#


def _require_go(store: rp.Store, go: str | None, apply_: bool, verb: str) -> dict[str, Any] | None:
    """Every reversal verb records the operator go / pre-authorisation id
    (§7.3) — required for --apply, checked read-only either way."""
    if go:
        return check_authority(store, go)
    if apply_:
        raise rp.PipelineError(
            "go-required",
            f"release {verb} --apply needs --go <name> naming the operator's "
            f"{AUTHORITIES_PREFIX}<name>.json go/pre-authorisation record — "
            "the verb checks it, never creates one (§7.3)",
        )
    return None


def _rebaseline(lock: rp.Lock) -> None:
    """After the verb's own recorded registry writes, the lock's state
    digest re-baselines — ``refresh()`` then still refuses NEW drift."""
    lock.state_digest = rp.registry_state_digest(lock.store)


def _deny_map_bytes(view: Path) -> bytes:
    body = view / "staged" / "conf" / "withdrawn_routes.conf"
    if body.is_file():
        return body.read_bytes()
    return (
        "# Generated by the SIG release tooling — withdrawn release routes (P34.41).\n"
    ).encode()


def _write_floor_latest(
    view: Path, floor_label: str, reason: str, previous: str | None, now: datetime
) -> None:
    """The file-layout latest pointer for a legacy-floor serve — a label,
    never a publication id (§8.5)."""
    (view / "latest.json").write_bytes(
        _canonical(
            {
                "schema": LATEST_SCHEMA_V1,
                "publication_id": None,
                "label": floor_label,
                "legacy_floor": floor_label,
                "ordinal": -1,
                "rolled_back": True,
                "reason": reason,
                "previous": previous,
                "rolled_back_at": _iso(now),
            }
        )
    )


def _floor_record(store: rp.Store) -> dict[str, Any]:
    body = store.read(FLOOR_OBJECT)
    if body is None:
        return {"schema": FLOOR_SCHEMA, "floors": []}
    try:
        doc = json.loads(body)
    except ValueError:
        return {"schema": FLOOR_SCHEMA, "floors": [], "_unreadable": True}
    return doc if isinstance(doc, dict) else {"schema": FLOOR_SCHEMA, "floors": []}


def _resolve_target(store: rp.Store, to: str) -> dict[str, Any]:
    """``--to`` → {kind: pub|floor, publication_id?, label, env values}."""
    to = (to or "").strip()
    if not to:
        raise rp.PipelineError("no-target", "rollback needs --to <pub|label|legacy-YYYYMMDD>")
    if rc.PUB_RE.match(to):
        return {"kind": "pub", "publication_id": to}
    if LEGACY_LABEL_RE.match(to):
        doc = _floor_record(store)
        floor = next((f for f in doc.get("floors") or [] if f.get("label") == to), None)
        if floor is None:
            raise rp.PipelineError(
                "unknown-floor",
                f"{to!r} is not an imported legacy floor — `release import-floor` "
                "stages it first (known floors: "
                f"{[f.get('label') for f in doc.get('floors') or []]})",
            )
        return {"kind": "floor", "label": to, "floor": floor}
    labels = rc.read_label_map(store)
    for pub, label in labels.items():
        if label == to:
            return {"kind": "pub", "publication_id": pub}
    raise rp.PipelineError(
        "unknown-target",
        f"{to!r} is not a p-<64hex> publication id, a known label "
        f"({sorted(labels.values())}), or an imported legacy floor — nothing to roll to",
    )


def _rollback_post_checks(
    store: rp.Store,
    *,
    gen: int,
    target_kind: str,
    target_pub: str | None,
    env_pub: str,
    prior_pub: str | None,
    withdrawn_conf: bytes,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, ok: bool, detail: str, **extra: Any) -> None:
        checks.append(
            {"id": check_id, "status": "pass" if ok else "fail", "detail": detail, **extra}
        )

    latest = rc.read_generation(store, gen)
    if target_kind == "pub":
        record(
            "conf.latest",
            latest is not None
            and latest.get("publication_id") == target_pub
            and latest.get("rolled_back") is True,
            f"conf/{gen}/latest.json names {target_pub} with rolled_back=true",
        )
    else:
        record(
            "conf.latest",
            latest is not None
            and latest.get("publication_id") is None
            and latest.get("legacy_floor") == env_pub,
            f"conf/{gen}/latest.json points at the legacy floor {env_pub}",
        )
    record(
        "conf.previous",
        latest is not None and latest.get("previous") == prior_pub,
        f"the pointer records previous={prior_pub}",
    )
    record(
        "conf.withdrawn",
        store.stat(rc._conf_name(gen, "withdrawn.conf")) is not None
        and store.read(rc._conf_name(gen, "withdrawn.conf")) == withdrawn_conf,
        "the generation carries the re-derived deny map byte-identically",
    )
    promoted = rc.read_promoted_map(store, gen)
    record(
        "conf.promoted-map",
        target_pub is None or target_pub in promoted,
        "the carried promoted.map keeps the promoted set"
        + (f" ({target_pub} listed)" if target_pub in promoted else ""),
    )
    for rel in ("selectors.conf", "labels.conf", "releases/index.html", "releases/catalog.json"):
        record(
            f"conf.{rel}",
            store.stat(rc._conf_name(gen, rel)) is not None,
            f"conf/{gen}/{rel} present",
        )
    return checks


# --------------------------------------------------------------------------- #
# verb_rollback — §8.1                                                        #
# ---------------------------------------------------------------------------#


def verb_rollback(
    store: rp.Store,
    *,
    apply_: bool,
    to: str,
    reason: str | None = None,
    go: str | None = None,
    api_image: str | None = None,
    web_image: str | None = None,
    min_instances: int = 1,
    project: str | None = None,
    region: str | None = None,
    execute_rolls: bool = False,
    gcloud: Any = None,
    origins: Sequence[str] = (),
    post_checks: Callable[..., list[dict[str, Any]]] | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``rollback --to <pub|label|legacy-YYYYMMDD> --reason <text>`` —
    re-apply the CURRENT withdrawal set, write ``conf/<gen+1>`` with
    ``latest = <target>``, roll api→web as new revisions. Never a Cloud Run
    traffic reversion (RR-7): an old revision's pinned SIG_CONF_GEN would
    re-serve routes the current withdrawal set denies."""
    now = now or _now()
    reason = (reason or "").strip()
    if not reason:
        raise rp.PipelineError(
            "reason-required", "rollback needs --reason <text> — the journal records it"
        )
    target = _resolve_target(store, to)
    gen = rc.current_generation(store)
    prior = rc.read_generation(store, gen) if gen else None
    prior_pub = str(prior.get("publication_id") or "") or None if prior else None
    next_gen = gen + 1
    if target["kind"] == "pub":
        pub = target["publication_id"]
        if pub == prior_pub:
            raise rp.PipelineError(
                "same-latest",
                f"{pub} is already the latest pointer — a rollback to the "
                "current release is a no-op, never a generation",
            )
        promoted = rc.read_promoted_map(store, gen)
        if pub not in promoted:
            raise rp.PipelineError(
                "never-promoted",
                f"{pub} is not in the promoted set (conf/{gen}/promoted.map) — "
                "rollback targets an earlier PROMOTED release (§8.1)",
            )
        if not store.list(f"staged/v/{pub}/"):
            raise rp.PipelineError(
                "unstaged-target",
                f"no staged/v/{pub}/ tree — a roll to a release whose latest "
                "view was never staged would serve 404s (§8.1)",
            )
        env_pub, env_label = pub, (rc.read_release_meta(store, pub).get("label") or "unsigned")
    else:
        env_pub = env_label = target["label"]
        pub = None
    go_ref = _require_go(store, go, apply_, "rollback")
    legs = _plan_rolls(
        next_gen=next_gen,
        latest_pub_env=env_pub,
        latest_label_env=env_label,
        api_image=api_image,
        web_image=web_image,
        min_instances=min_instances,
        project=project,
        region=region,
        execute_rolls=execute_rolls,
        gcloud=gcloud,
    )
    plan = [
        f"resolve --to {to} → {env_pub} ({target['kind']})",
        "re-apply the CURRENT withdrawal set over every staged namespace "
        "(exports.release.rollback / clear_latest_pointer — the deny map is "
        "re-derived, never carried)",
        f"write registry/conf/{next_gen}/ (8 objects, create-if-absent)",
        f"roll sig-api → sig-web as NEW revisions by digest (env "
        f"SIG_CONF_GEN={next_gen} SIG_LATEST_PUB={env_pub}; never a "
        "traffic reversion — RR-7)",
        "journal `rolled-back` (+ `rolled-back-from` on the prior latest)",
    ]
    result: dict[str, Any] = {
        "verb": "rollback",
        "to": to,
        "target": target,
        "previous_latest": prior_pub,
        "conf_gen": next_gen,
        "previous_generation": gen,
        "reason": reason,
        "go": go_ref,
        "plan": plan,
        "rolls": _roll_rows(legs),
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        return result
    with rp.acquire_lock(store, "rollback", break_lock=break_lock, now=now) as lock:
        lock.refresh()  # registry state must not have drifted since acquire
        before_staged = set(store.list("staged/"))
        with tempfile.TemporaryDirectory(prefix="sig-rollback-") as td:
            view = registry_view(store, Path(td))
            try:
                if target["kind"] == "pub":
                    applied = exports_rollback(view, pub, now=now)
                else:
                    # the floor serve: the pointer clears (the withdrawal set
                    # re-applies) then the floor pointer lands — a label,
                    # never a publication id.
                    if (view / "latest.json").is_file():
                        applied = clear_latest_pointer(view, now=now)
                    else:
                        applied = {
                            "cleared": False,
                            "withdrawals_applied": apply_withdrawals(
                                view / "staged", ReleaseRegistry(view).withdrawals()
                            ),
                        }
                    _write_floor_latest(view, env_label, reason, prior_pub, now)
            except ReleaseError as exc:
                raise rp.PipelineError("rollback-refused", str(exc)) from exc
            synced = sync_registry_back(store, view)
            synced_staged = sync_staged_back(store, view)
            removed = (
                synced_staged["removed"]
                if not isinstance(store, rp.LocalDirStore)
                else staged_removal_diff(store, before_staged)
            )
            withdrawn_conf = _deny_map_bytes(view)
        latest_doc = {
            "schema": rc.LATEST_SCHEMA_V2,
            "conf_gen": next_gen,
            "activated_at": _iso(now),
            "rolled_back": True,
            "rollback_reason": reason,
            "previous": prior_pub,
            "go_ref": go_ref,
            "withdrawals_sha256": withdrawals_sha256(store),
            "serving": {"sig_api_image": api_image, "sig_web_image": web_image},
        }
        if target["kind"] == "pub":
            meta = rc.read_release_meta(store, pub)
            history = rc._generation_history(store)
            prior_ptr = history.get(pub) or {}
            latest_doc.update(
                {
                    "publication_id": pub,
                    "label": meta.get("label") or prior_ptr.get("label") or "unsigned",
                    "manifest_sha256": meta.get("manifest_sha256"),
                    "descriptor_sha256": meta.get("descriptor_sha256"),
                }
            )
        else:
            latest_doc.update(
                {
                    "publication_id": None,
                    "label": env_label,
                    "legacy_floor": env_label,
                }
            )
        files = compose_reversal_generation(
            store,
            gen=next_gen,
            latest_doc=latest_doc,
            withdrawn_conf=withdrawn_conf,
            current_pub=pub,
            now=now,
        )
        written = rc.write_generation(store, next_gen, files)
        _execute_or_prepare_rolls(
            legs, execute_rolls=execute_rolls, project=project, region=region, gcloud=gcloud
        )
        checks = (post_checks or _rollback_post_checks)(
            store,
            gen=next_gen,
            target_kind=target["kind"],
            target_pub=pub,
            env_pub=env_pub,
            prior_pub=prior_pub,
            withdrawn_conf=withdrawn_conf,
        )
        failed_checks = [c for c in checks if c.get("status") == "fail"]
        result["checks"] = checks
        result["written"] = sorted(written)
        result["removed_objects"] = removed
        result["synced"] = {**synced, "staged": synced_staged}
        _rebaseline(lock)
        if failed_checks:
            rp.emit_event(
                store,
                "failed",
                pub,
                {
                    "outcome": "failed",
                    "conf_gen": next_gen,
                    "refusal": "; ".join(c["id"] for c in failed_checks),
                },
                now=now,
            )
            raise rp.PipelineError(
                "post-check-failed",
                f"{len(failed_checks)} post-rollback check(s) failed — the "
                "generation is written; refusing rather than journaling a "
                "green it did not earn",
            )
        ev1 = rp.emit_event(
            store,
            "rolled-back",
            pub,
            {
                "outcome": "recorded",
                "conf_gen": next_gen,
                "previous_generation": gen,
                "rolled_back_from": prior_pub,
                "reason": reason,
                "go_ref": go_ref,
                "withdrawals_applied": applied.get("withdrawals_applied"),
                "activations": synced.get("inserted"),
                "serving": {"sig_api_image": api_image, "sig_web_image": web_image},
                "rolls": [{"service": leg.service, "status": leg.status} for leg in legs],
            },
            now=now,
        )
        if prior_pub and rc.PUB_RE.match(prior_pub):
            rp.emit_event(
                store,
                "rolled-back-from",
                prior_pub,
                {"outcome": "recorded", "conf_gen": next_gen, "rolled_back_to": pub or env_pub},
                now=now,
            )
        result.update(applied=True, event=ev1, outcome="rolled-back", applied_withdrawals=applied)
    return result


# --------------------------------------------------------------------------- #
# verb_clear_latest — §8.2                                                    #
# ---------------------------------------------------------------------------#


def verb_clear_latest(
    store: rp.Store,
    *,
    apply_: bool,
    reason: str | None = None,
    go: str | None = None,
    api_image: str | None = None,
    web_image: str | None = None,
    min_instances: int = 1,
    project: str | None = None,
    region: str | None = None,
    execute_rolls: bool = False,
    gcloud: Any = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``clear-latest`` — the archive-only case (§8.2): the latest pointer is
    removed, ``/releases/`` shows no current release, every latest-view route
    404s under ``v/none/``. Re-applies the current withdrawal set first —
    the archive serves the barrier always."""
    now = now or _now()
    reason = (reason or "").strip()
    if not reason:
        raise rp.PipelineError(
            "reason-required", "clear-latest needs --reason <text> — the journal records it"
        )
    gen = rc.current_generation(store)
    prior = rc.read_generation(store, gen) if gen else None
    prior_pub = str(prior.get("publication_id") or "") or None if prior else None
    next_gen = gen + 1
    go_ref = _require_go(store, go, apply_, "clear-latest")
    legs = _plan_rolls(
        next_gen=next_gen,
        latest_pub_env=NO_LATEST_SENTINEL,
        latest_label_env=NO_LATEST_LABEL,
        api_image=api_image,
        web_image=web_image,
        min_instances=min_instances,
        project=project,
        region=region,
        execute_rolls=execute_rolls,
        gcloud=gcloud,
    )
    result: dict[str, Any] = {
        "verb": "clear-latest",
        "previous_latest": prior_pub,
        "conf_gen": next_gen,
        "reason": reason,
        "go": go_ref,
        "rolls": _roll_rows(legs),
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        result["plan"] = [
            "clear_latest_pointer — remove registry/latest.json, re-apply "
            "the current withdrawal set, drop the entity stubs",
            f"write registry/conf/{next_gen}/ with a null latest pointer",
            f"roll api→web with SIG_LATEST_PUB={NO_LATEST_SENTINEL} "
            "(the v/none/ tree never exists — every latest-view route 404s)",
            "journal `cleared-latest` + `superseded` on the prior latest",
        ]
        return result
    with rp.acquire_lock(store, "clear-latest", break_lock=break_lock, now=now) as lock:
        lock.refresh()
        before_staged = set(store.list("staged/"))
        with tempfile.TemporaryDirectory(prefix="sig-clear-") as td:
            view = registry_view(store, Path(td))
            try:
                applied = clear_latest_pointer(view, now=now)
            except ReleaseError as exc:
                raise rp.PipelineError("clear-latest-refused", str(exc)) from exc
            synced = sync_registry_back(store, view)
            synced_staged = sync_staged_back(store, view)
            removed = (
                synced_staged["removed"]
                if not isinstance(store, rp.LocalDirStore)
                else staged_removal_diff(store, before_staged)
            )
            withdrawn_conf = _deny_map_bytes(view)
        latest_doc = {
            "schema": rc.LATEST_SCHEMA_V2,
            "conf_gen": next_gen,
            "publication_id": None,
            "label": None,
            "activated_at": _iso(now),
            "rolled_back": False,
            "cleared": prior_pub,
            "clear_reason": reason,
            "go_ref": go_ref,
            "withdrawals_sha256": withdrawals_sha256(store),
            "serving": {"sig_api_image": api_image, "sig_web_image": web_image},
        }
        files = compose_reversal_generation(
            store,
            gen=next_gen,
            latest_doc=latest_doc,
            withdrawn_conf=withdrawn_conf,
            current_pub=None,
            now=now,
        )
        written = rc.write_generation(store, next_gen, files)
        _execute_or_prepare_rolls(
            legs, execute_rolls=execute_rolls, project=project, region=region, gcloud=gcloud
        )
        latest = rc.read_generation(store, next_gen)
        checks = [
            {
                "id": "conf.latest-null",
                "status": "pass" if latest and latest.get("publication_id") is None else "fail",
                "detail": "the new generation's latest pointer is null — archive-only",
            },
            {
                "id": "conf.withdrawn",
                "status": "pass"
                if store.read(rc._conf_name(next_gen, "withdrawn.conf")) == withdrawn_conf
                else "fail",
                "detail": "the re-derived deny map is served",
            },
        ]
        result["checks"] = checks
        result["written"] = sorted(written)
        result["removed_objects"] = removed
        _rebaseline(lock)
        if any(c["status"] == "fail" for c in checks):
            raise rp.PipelineError("post-check-failed", "the clear-latest generation checks failed")
        ev = rp.emit_event(
            store,
            "cleared-latest",
            prior_pub,
            {
                "outcome": "recorded",
                "conf_gen": next_gen,
                "reason": reason,
                "go_ref": go_ref,
                "withdrawals_applied": applied.get("withdrawals_applied"),
                "activations": synced.get("inserted"),
            },
            now=now,
        )
        if prior_pub and rc.PUB_RE.match(prior_pub):
            rp.emit_event(
                store,
                "superseded",
                prior_pub,
                {"outcome": "recorded", "conf_gen": next_gen, "by": "cleared-latest"},
                now=now,
            )
        result.update(applied=True, event=ev, outcome="cleared-latest", applied_withdrawals=applied)
    return result


# --------------------------------------------------------------------------- #
# verb_withdraw — §8.3                                                        #
# ---------------------------------------------------------------------------#


def verb_withdraw(
    store: rp.Store,
    *,
    apply_: bool,
    disposition: str | Path | None = None,
    authority: str | None = None,
    purge_versions: bool = False,
    api_image: str | None = None,
    web_image: str | None = None,
    min_instances: int = 1,
    project: str | None = None,
    region: str | None = None,
    execute_rolls: bool = False,
    gcloud: Any = None,
    origins: Sequence[str] = (),
    fetch: Fetch | None = None,
    mirrors_path: str | Path | None = None,
    post_checks: Callable[..., list[dict[str, Any]]] | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``withdraw --disposition <file> --authority <ref>`` — the §8.3 order,
    verbatim: (1) append-only disposition INSERT → (2) record_withdrawal →
    (3) apply_withdrawals over every staged namespace → (4) a new
    ``conf/<gen+1>`` whose ``withdrawn.conf`` carries full alias coverage →
    (5) api→web roll → (6) cache purge hooks (wired, dormant) → (7) probe
    every alias → (8) a dated receipt. ``--purge-versions`` (Part
    VIII/legal takedowns) additionally deletes the removed objects'
    noncurrent bucket versions — never the claim spine."""
    now = now or _now()
    if disposition is None:
        raise rp.PipelineError(
            "disposition-required", "withdraw needs --disposition <file> — the order file"
        )
    entries, order_meta = load_order(disposition)
    if authority is None and apply_:
        raise rp.PipelineError(
            "authority-required",
            "withdraw --apply needs --authority <name> naming the operator's "
            f"{AUTHORITIES_PREFIX}<name>.json record — the verb verifies it, "
            "never fabricates (SIG-SEC-010)",
        )
    authority_ref = check_authority(store, authority) if authority else None
    gen = rc.current_generation(store)
    prior = rc.read_generation(store, gen) if gen else None
    prior_pub = str(prior.get("publication_id") or "") or None if prior else None
    next_gen = gen + 1
    whole_pubs = [
        e["target_id"]
        for e in entries
        if e["target_kind"] == TargetKind.RELEASE_ARTIFACT
        and e["disposition"] in DENYING
        and rc.PUB_RE.match(e["target_id"])
    ]
    env_pub = prior_pub or NO_LATEST_SENTINEL
    env_label = str(prior.get("label") or NO_LATEST_LABEL) if prior else NO_LATEST_LABEL
    legs = _plan_rolls(
        next_gen=next_gen,
        latest_pub_env=env_pub,
        latest_label_env=env_label,
        api_image=api_image,
        web_image=web_image,
        min_instances=min_instances,
        project=project,
        region=region,
        execute_rolls=execute_rolls,
        gcloud=gcloud,
    )
    result: dict[str, Any] = {
        "verb": "withdraw",
        "order": order_meta,
        "entries": len(entries),
        "authority": authority_ref,
        "conf_gen": next_gen,
        "purge_versions": purge_versions,
        "rolls": _roll_rows(legs),
        "applied": False,
        "plan": [
            "parse + validate the sig.withdrawal-order/1 file",
            f"verify {AUTHORITIES_PREFIX}<authority> (the recorded authority — never fabricated)",
            "INSERT the dispositions (append-only, seq=insert order) + record_withdrawal",
            "apply_withdrawals over EVERY staged namespace (deny map + tombstones re-derived)",
            f"write registry/conf/{next_gen}/ — withdrawn.conf carries the full alias set",
            "roll sig-api → sig-web (new revisions; the barrier serves from conf)",
            "purge caches — CDN/R2 hooks (dormant unless a mirror row is enabled)",
            "probe every alias (deny-line + tombstone-body + per-origin 410s)",
            "write the dated receipt under registry/receipts/ + journal the events",
        ],
    }
    if not apply_:
        result["dry_run"] = True
        return result
    with rp.acquire_lock(store, "withdraw", break_lock=break_lock, now=now) as lock:
        lock.refresh()
        before_staged = set(store.list("staged/"))
        with tempfile.TemporaryDirectory(prefix="sig-withdraw-") as td:
            view = registry_view(store, Path(td))
            base_seq = len(ReleaseRegistry(view).withdrawals())
            records = _order_records(
                entries,
                authority_ref=authority_ref or {"ref": authority, "object": None},
                base_seq=base_seq,
                now=now,
            )
            try:
                record_withdrawal(view, records)
            except ReleaseError as exc:
                raise rp.PipelineError("withdraw-refused", str(exc)) from exc
            applied = apply_withdrawals(
                view / "staged",
                ReleaseRegistry(view).withdrawals(),
                active_pub=prior_pub,
            )
            synced = sync_registry_back(store, view)
            synced_staged = sync_staged_back(store, view)
            removed = (
                synced_staged["removed"]
                if not isinstance(store, rp.LocalDirStore)
                else staged_removal_diff(store, before_staged)
            )
            withdrawn_conf = _deny_map_bytes(view)
        # step 4 — the new generation carries the re-derived barrier
        latest_doc: dict[str, Any] = dict(prior) if prior else {"schema": rc.LATEST_SCHEMA_V2}
        latest_doc.update(
            {
                "schema": rc.LATEST_SCHEMA_V2,
                "conf_gen": next_gen,
                "carried_by": "withdraw",
                "carried_at": _iso(now),
                "authority_ref": authority_ref,
                "withdrawals_sha256": withdrawals_sha256(store),
            }
        )
        files = compose_reversal_generation(
            store,
            gen=next_gen,
            latest_doc=latest_doc,
            withdrawn_conf=withdrawn_conf,
            current_pub=prior_pub,
            now=now,
        )
        written = rc.write_generation(store, next_gen, files)
        # step 5 — api then web
        _execute_or_prepare_rolls(
            legs, execute_rolls=execute_rolls, project=project, region=region, gcloud=gcloud
        )
        # step 6 — cache purge hooks (dormant no-ops when unconfigured)
        purge_legs = purge_hooks(
            denied_routes=applied.get("routes") or [],
            removed_objects=removed,
            mirrors_path=mirrors_path,
            gcloud=gcloud,
            now=now,
        )
        purge_v = (
            purge_noncurrent_versions(store, removed)
            if purge_versions
            else {"status": "not-requested"}
        )
        # step 7 — probe every alias
        probes = probe_denied_aliases(
            withdrawn_conf=withdrawn_conf,
            view=None,
            denied_routes=applied.get("routes") or [],
            origins=origins,
            fetch=fetch,
        )
        # the tombstone-body structural leg needs the staged bodies — probe
        # them off the store when there is no local view left.
        tomb_names = {
            ln.split("error_page 410 ")[1].split(";")[0]
            for ln in withdrawn_conf.decode().splitlines()
            if "error_page 410" in ln
        }
        for body in sorted(tomb_names):
            ok = store.stat(f"staged/{body.lstrip('/')}") is not None
            probes.append(
                {
                    "alias": body,
                    "kind": "tombstone-body",
                    "status": "pass" if ok else "fail",
                    "detail": f"tombstone body staged at staged/{body.lstrip('/')}",
                }
            )
        # step 8 — the dated receipt
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "recorded_at": _iso(now),
            "order": order_meta,
            "authority": authority_ref,
            "entries": len(records),
            "dispositions_seq": [r.seq for r in records],
            "conf_gen": next_gen,
            "denied_routes": applied.get("routes"),
            "entity_stubs": sorted((applied.get("entity_stubs") or {}).keys())
            if isinstance(applied.get("entity_stubs"), Mapping)
            else applied.get("entity_stubs"),
            "removed_objects": removed,
            "purge_hooks": purge_legs,
            "purge_versions": purge_v,
            "probes": probes,
            "rolls": _roll_rows(legs),
            "claim_spine_touched": False,
            "note": "append-only — reinstatement is a NEW disposition + a NEW "
            "release; the claim spine is never altered (§8.3/P39)",
        }
        receipt_name = (
            f"{RECEIPTS_PREFIX}withdraw-{now.strftime('%Y%m%dT%H%M%SZ')}-"
            f"{_sha256(Path(disposition).read_bytes())[:12]}.json"
        )
        store.insert(receipt_name, _canonical(receipt), content_type="application/json")
        _rebaseline(lock)
        events: list[str] = []
        for wpub in whole_pubs:
            events.append(
                rp.emit_event(
                    store,
                    "withdrawn-whole",
                    wpub,
                    {
                        "outcome": "recorded",
                        "conf_gen": next_gen,
                        "order": order_meta.get("order_sha256"),
                        "authority": authority_ref,
                        "receipt": receipt_name,
                    },
                    now=now,
                )
            )
        events.append(
            rp.emit_event(
                store,
                "withdraw",
                None,
                {
                    "outcome": "recorded",
                    "conf_gen": next_gen,
                    "order": order_meta,
                    "authority": authority_ref,
                    "entries": len(records),
                    "denied": applied.get("denied"),
                    "receipt": receipt_name,
                    "purged_versions": purge_v.get("versions_deleted", 0),
                    "rolls": [{"service": leg.service, "status": leg.status} for leg in legs],
                },
                now=now,
            )
        )
        failed = [p for p in probes if p.get("status") == "fail"]
        result.update(
            applied=True,
            outcome="withdrawn",
            written=sorted(written),
            denied_routes=applied.get("routes"),
            removed_objects=removed,
            purge_hooks=purge_legs,
            purge_versions_result=purge_v,
            probes=probes,
            probe_failures=len(failed),
            receipt=receipt_name,
            events=events,
            synced={**synced, "staged": synced_staged},
        )
        if failed:
            rp.emit_event(
                store,
                "failed",
                None,
                {
                    "outcome": "failed",
                    "conf_gen": next_gen,
                    "refusal": f"{len(failed)} alias probe(s) failed after the deny landed",
                    "receipt": receipt_name,
                },
                now=now,
            )
            raise rp.PipelineError(
                "probe-failed",
                f"{len(failed)} alias probe(s) failed — the deny landed and "
                f"the receipt {receipt_name} records it; refusing a green "
                "the probes did not earn",
            )
    return result


# --------------------------------------------------------------------------- #
# verb_import_floor — §8.5                                                    #
# ---------------------------------------------------------------------------#


def verb_import_floor(
    store: rp.Store,
    *,
    apply_: bool,
    source_dir: str | Path,
    label: str | None = None,
    go: str | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``import-floor --from <dir>`` — import the then-live root tree to
    ``staged/v/legacy-<YYYYMMDD>/``, labelled ``legacy-<date>`` (never a
    publication id). ``rollback --to legacy-<date>`` serves it (§8.5)."""
    now = now or _now()
    src = Path(source_dir)
    if not src.is_dir():
        raise rp.PipelineError("bad-input", f"--from {src} is not a directory")
    label = (label or f"legacy-{now.strftime('%Y%m%d')}").strip()
    if not LEGACY_LABEL_RE.match(label):
        raise rp.PipelineError(
            "bad-floor-label",
            f"floor label {label!r} — the floor is labelled legacy-<YYYYMMDD>, "
            "never a p-<64hex> publication id",
        )
    files = sorted(p for p in src.rglob("*") if p.is_file())
    if not files:
        raise rp.PipelineError("empty-input", f"{src} carries no files — nothing to import")
    go_ref = _require_go(store, go, apply_, "import-floor")
    namespace = f"v/{label}"
    plan = [f"staged/{namespace}/{p.relative_to(src).as_posix()}" for p in files]
    result: dict[str, Any] = {
        "verb": "import-floor",
        "label": label,
        "namespace": namespace,
        "objects": len(plan),
        "source": str(src),
        "go": go_ref,
        "applied": False,
        "plan": [
            f"insert {len(plan)} objects under staged/{namespace}/ (create-if-absent)",
            f"record the floor under {FLOOR_OBJECT} (labelled, never a pub id)",
            "journal `legacy-floor-imported`",
        ],
    }
    if not apply_:
        result["dry_run"] = True
        return result
    with rp.acquire_lock(store, "import-floor", break_lock=break_lock, now=now) as lock:
        lock.refresh()
        nbytes = 0
        written = 0
        for p, name in zip(files, plan, strict=True):
            body = p.read_bytes()
            try:
                store.insert(name, body, content_type=_media_type(name))
                written += 1
                nbytes += len(body)
            except _gcs.GcsPreconditionFailed as exc:
                meta = store.stat(name) or {}
                if meta.get("md5Hash") == rp._md5_b64(body):
                    continue  # identical bytes — a resume
                raise rp.NameCollision(name) from exc
        doc = _floor_record(store)
        floors = doc.get("floors") or []
        existing = next((f for f in floors if f.get("label") == label), None)
        if existing is None:
            floors.append(
                {
                    "label": label,
                    "namespace": namespace,
                    "imported_at": _iso(now),
                    "source": str(src),
                    "objects": written,
                    "bytes": nbytes,
                    "go_ref": go_ref,
                }
            )
            doc["floors"] = floors
            _write_back_json(store, FLOOR_OBJECT, _canonical(doc))
        _rebaseline(lock)
        ev = rp.emit_event(
            store,
            "legacy-floor-imported",
            None,
            {
                "outcome": "recorded",
                "label": label,
                "namespace": namespace,
                "objects": written,
                "bytes": nbytes,
                "source": str(src),
                "go_ref": go_ref,
            },
            now=now,
        )
        result.update(applied=True, written=written, bytes=nbytes, event=ev)
    return result


__all__ = [
    "AUTHORITY_SCHEMA",
    "AUTHORITIES_PREFIX",
    "FLOOR_OBJECT",
    "FLOOR_SCHEMA",
    "LEGACY_LABEL_RE",
    "NO_LATEST_LABEL",
    "NO_LATEST_SENTINEL",
    "ORDER_SCHEMA",
    "RECEIPT_SCHEMA",
    "check_authority",
    "compose_reversal_generation",
    "conf_gen_probe",
    "derive_withdrawal_barrier",
    "load_order",
    "probe_denied_aliases",
    "purge_hooks",
    "purge_noncurrent_versions",
    "registry_view",
    "sync_registry_back",
    "sync_staged_back",
    "verb_clear_latest",
    "verb_import_floor",
    "verb_rollback",
    "verb_withdraw",
    "withdrawals_sha256",
]
