# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Configuration generations + metadata-only promotion (P35.54, REL-03b,
SIG-REL-006, ADR-220).

The release bucket's serving surface is pinned by an immutable
``registry/conf/<gen>/`` generation — the promoted map, the latest
pointer, the withdrawal/selector/label includes and the ``/releases/``
index set — and ``sig-ops release promote`` writes exactly the next
generation, copies no release bytes, rolls ``sig-api`` then ``sig-web`` by
digest, runs the post-promote checks and journals ``promoted``.

Layout (G3 §4.1/§4.2 + ADR-220 D3):

    registry/conf/<gen>/
        promoted.map      the promoted set — `p-<64hex> 1;` lines
        latest.json       sig.latest-pointer/2
        withdrawn.conf    the deny barrier — carried byte-identical
                          (the writer is `release withdraw`, P35.55)
        selectors.conf    the J3 §8.3 selector routes — carried; its
                          writer lands in a later row
        labels.conf       label → pub 301 aliases, composed from the
                          label map (G3 line 170: "from the catalog")
        releases/
            index.html    the generated /releases/ index (C4 NEW-10)
            catalog.json  sig.publication-catalog/2
            latest.json   byte-identical copy of the pointer (the
                          /releases/latest.json alias serves it)

``registry/approvals/<name>.json`` carries the operator's
``sig.promotion-approval/1`` records — a standing go (Class R) or a
signed readout naming the pub (Class S). The verb checks the record; it
never creates one.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.release_identity import parse_instant

from . import release_pipeline as rp
from .job_roll import DIGEST_REF

# --------------------------------------------------------------------------- #
# Schemas + names                                                            #
# --------------------------------------------------------------------------- #

CONF_PREFIX = "registry/conf/"
APPROVALS_PREFIX = "registry/approvals/"

LATEST_SCHEMA_V2 = "sig.latest-pointer/2"
CATALOG_SCHEMA_V2 = "sig.publication-catalog/2"
APPROVAL_SCHEMA = "sig.promotion-approval/1"
INDEX_SCHEMA_NOTE = "sig.release-index/1"

#: The p-<64hex> publication-id shape (release_identity.publication_id).
PUB_RE = re.compile(r"^p-[0-9a-f]{64}$")

#: The generation files promote composes (every write is create-if-absent).
GENERATION_FILES: tuple[str, ...] = (
    "promoted.map",
    "latest.json",
    "withdrawn.conf",
    "selectors.conf",
    "labels.conf",
    "releases/index.html",
    "releases/catalog.json",
    "releases/latest.json",
)

#: The journal fold states a candidate may promote from (RM-6: a merely
#: staged candidate refuses — the bounded verify must have run).
PROMOTABLE_STATES: frozenset[str] = frozenset({"verified", "classified"})

#: The public services promote rolls, in order — api first so a revision
#: that cannot serve the release is never publicly reachable (§4.3/§5.1).
ROLL_ORDER: tuple[str, ...] = ("sig-api", "sig-web")

#: An injected gcloud runner — ``job_roll.gcloud_cli``'s contract.
Gcloud = Callable[[list[str]], str]


def _canonical(obj: Any) -> bytes:
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        + b"\n"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _conf_name(gen: int, rel: str) -> str:
    return f"{CONF_PREFIX}{gen}/{rel}"


# --------------------------------------------------------------------------- #
# Reading the store                                                          #
# --------------------------------------------------------------------------- #


def current_generation(store: rp.Store) -> int:
    """The highest ``registry/conf/<n>/`` generation present; 0 when none."""
    gens: set[int] = set()
    for name in store.list(CONF_PREFIX):
        rest = name[len(CONF_PREFIX) :]
        head = rest.split("/", 1)[0]
        if head.isdigit():
            gens.add(int(head))
    return max(gens) if gens else 0


def read_generation(store: rp.Store, gen: int) -> dict[str, Any] | None:
    """A generation's ``latest.json`` document; ``None`` when absent."""
    body = store.read(_conf_name(gen, "latest.json"))
    if body is None:
        return None
    try:
        doc = json.loads(body)
    except ValueError:
        return {"_unreadable": True}
    return doc if isinstance(doc, dict) else {"_unreadable": True}


def parse_promoted_map(text: str) -> set[str]:
    """The pub set a ``promoted.map`` body declares (`p-<64hex> 1;` lines)."""
    pubs: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rstrip(";").split()
        if len(parts) == 2 and parts[1] == "1" and PUB_RE.match(parts[0]):
            pubs.add(parts[0])
    return pubs


def read_promoted_map(store: rp.Store, gen: int) -> set[str]:
    body = store.read(_conf_name(gen, "promoted.map"))
    if body is None:
        return set()
    return parse_promoted_map(body.decode("utf-8", errors="replace"))


def read_label_map(store: rp.Store) -> dict[str, str]:
    """pub → label from ``registry/labels.json`` (both directions land)."""
    body = store.read("registry/labels.json")
    if body is None:
        return {}
    try:
        doc = json.loads(body)
    except ValueError:
        return {}
    out: dict[str, str] = {}
    for entry in doc.get("labels") or []:
        pub = entry.get("publication_id")
        label = entry.get("label")
        if isinstance(pub, str) and PUB_RE.match(pub) and isinstance(label, str):
            out[pub] = label
    return out


def read_release_meta(store: rp.Store, pub: str) -> dict[str, Any]:
    """The promoted pub's stamped metadata, from its own staged objects —
    ``staged/releases/<pub>/catalog_entry.json`` (label, manifest digest,
    as-of pair) and ``descriptor.json`` (code identity). Nothing is
    invented: an absent field is ``None``, not a guess."""
    meta: dict[str, Any] = {
        "label": None,
        "manifest_sha256": None,
        "descriptor_sha256": None,
        "as_of_world": None,
        "code_commit": None,
        "code_tag": None,
    }
    entry_body = store.read(f"staged/releases/{pub}/catalog_entry.json")
    if entry_body is not None:
        try:
            entry = json.loads(entry_body)
        except ValueError:
            entry = {}
        if isinstance(entry, dict):
            meta["label"] = entry.get("data_release_id") or meta["label"]
            meta["manifest_sha256"] = entry.get("manifest_sha256")
            meta["descriptor_sha256"] = entry.get("descriptor_sha256")
            compat = entry.get("compat") or {}
            if isinstance(compat, dict):
                meta["as_of_world"] = compat.get("as_of_world")
    desc_body = store.read(f"staged/releases/{pub}/descriptor.json")
    if desc_body is not None:
        try:
            desc = json.loads(desc_body)
        except ValueError:
            desc = {}
        if isinstance(desc, dict):
            meta["label"] = meta["label"] or desc.get("label")
            code = desc.get("code") or {}
            if isinstance(code, dict):
                meta["code_commit"] = code.get("commit")
                meta["code_tag"] = code.get("tag")
    return meta


def journal_class(store: rp.Store, pub: str) -> str | None:
    """The promotion class the journal's latest ``classified`` event
    recorded; ``None`` when the classifier never ran."""
    cls: str | None = None
    for ev in rp.list_events(store, pub):
        if ev.get("verb") == "classified" and ev.get("publication_id") == pub:
            cls = str(ev.get("class") or "") or cls
    return cls


def _publication_states(store: rp.Store) -> dict[str, str]:
    """pub → folded §3.4 state across the whole journal."""
    states: dict[str, str] = {}
    events = rp.list_events(store)
    pubs = {
        str(ev.get("publication_id"))
        for ev in events
        if PUB_RE.match(str(ev.get("publication_id") or ""))
    }
    for pub in pubs:
        states[pub] = rp.fold_state(events, pub)["state"]
    return states


def _generation_history(store: rp.Store) -> dict[str, dict[str, Any]]:
    """pub → the generation pointer record for every earlier generation —
    the superseded releases' activation data, verbatim from their own
    ``latest.json`` (never re-derived)."""
    history: dict[str, dict[str, Any]] = {}
    for gen in range(1, current_generation(store) + 1):
        doc = read_generation(store, gen)
        if not doc or doc.get("_unreadable"):
            continue
        pub = str(doc.get("publication_id") or "")
        if PUB_RE.match(pub):
            history[pub] = {
                "activated_at": doc.get("activated_at"),
                "label": doc.get("label"),
                "conf_gen": doc.get("conf_gen"),
            }
    return history


# --------------------------------------------------------------------------- #
# The approval check — reads a record, never writes one (ADR-220 D4)       #
# --------------------------------------------------------------------------- #


def check_approval(
    store: rp.Store,
    publication_id: str,
    release_class: str,
    approval_name: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify ``registry/approvals/<approval_name>`` authorises this
    promotion. Class R needs an unrevoked, unexpired ``standing_go``;
    Class S needs a ``signed_readout`` naming this pub with a ``signature``
    present (presence-checked only — cryptographic verification is the
    operator's readout path, never the pipeline's). Returns the approval
    ref recorded into ``latest.json``; refusals raise PipelineError."""
    if "/" in approval_name or approval_name.startswith("."):
        raise rp.PipelineError(
            "bad-approval-name",
            f"approval names a single object under {APPROVALS_PREFIX} — got {approval_name!r}",
        )
    obj = f"{APPROVALS_PREFIX}{approval_name}"
    body = store.read(obj)
    if body is None:
        raise rp.PipelineError(
            "approval-absent",
            f"{obj} does not exist — the operator writes the approval "
            "record; the verb checks it, never creates one",
        )
    try:
        rec = json.loads(body)
    except ValueError as exc:
        raise rp.PipelineError("approval-unreadable", f"{obj} is not JSON: {exc}") from exc
    if not isinstance(rec, dict) or rec.get("schema") != APPROVAL_SCHEMA:
        raise rp.PipelineError(
            "approval-schema",
            f"{obj} does not declare schema {APPROVAL_SCHEMA!r}",
        )
    reasons: list[str] = []
    if rec.get("revoked") is True:
        reasons.append("the record carries revoked=true")
    expires = rec.get("expires_at")
    if expires:
        exp_dt = parse_instant(str(expires))
        if exp_dt is None:
            reasons.append(f"expires_at {expires!r} is not an ISO instant")
        elif exp_dt <= (now or datetime.now(UTC)):
            reasons.append(f"the record expired at {expires}")
    declared_class = rec.get("class")
    if declared_class and declared_class != release_class:
        reasons.append(
            f"the record is scoped to {declared_class!r}, not this promotion's {release_class!r}"
        )
    kind = rec.get("kind")
    if release_class == "class_s":
        if kind != "signed_readout":
            reasons.append(f"Class S needs kind='signed_readout' — got {kind!r} (SIG-REL-012)")
        elif rec.get("publication_id") != publication_id:
            reasons.append(
                f"the signed readout names {rec.get('publication_id')!r}, not {publication_id}"
            )
        elif not isinstance(rec.get("signature"), str) or not rec["signature"].strip():
            reasons.append("the signed readout carries no signature field")
    else:
        if kind != "standing_go":
            reasons.append(f"Class R needs kind='standing_go' — got {kind!r}")
        elif rec.get("publication_id") not in (None, "", publication_id):
            reasons.append(
                f"the standing go is scoped to {rec.get('publication_id')!r}, not {publication_id}"
            )
    if reasons:
        raise rp.PipelineError(
            "approval-refused",
            f"{obj} does not authorise this promotion: " + "; ".join(reasons),
        )
    return {
        "object": obj,
        "sha256": _sha256(body),
        "kind": kind,
        "ref": rec.get("ref"),
        "approved_at": rec.get("approved_at"),
    }


# --------------------------------------------------------------------------- #
# Composing the generation                                                   #
# --------------------------------------------------------------------------- #


def render_promoted_map(pubs: set[str], *, gen: int) -> bytes:
    """The ``promoted.map`` body — one ``p-<64hex> 1;`` line per promoted
    publication, sorted (the map's `default 0` in nginx.conf is the gate)."""
    lines = [
        "# sig.promoted-map — the promoted set, conf generation "
        f"{gen} (SIG-REL-002). Written whole by `sig-ops release",
        "# promote`; a generation is immutable once served (NEW-7). The",
        "# nginx `map $uri_pub $promoted` default-0s anything not listed.",
    ]
    lines += [f"{pub} 1;" for pub in sorted(pubs)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_labels_conf(label_map: dict[str, str], *, gen: int) -> bytes:
    """``labels.conf`` — the label → pub 301 aliases, composed whole from
    the label map (G3 line 170: labels.conf is 'from the catalog';
    append-only aliases). Exact-match `location =` entries evaluate before
    the gated ``location /releases/`` prefix, so a promoted label resolves
    to its pub landing."""
    lines = [
        "# sig.labels-conf — label → pub aliases, conf generation "
        f"{gen}. Composed by `sig-ops release",
        "# promote` from the label map; an alias is a 301, never a rewrite.",
    ]
    for pub, label in sorted(label_map.items(), key=lambda kv: kv[1]):
        lines.append(f"location = /releases/{label} {{ return 301 /releases/{pub}/; }}")
        lines.append(f"location = /releases/{label}/ {{ return 301 /releases/{pub}/; }}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _carry_or_placeholder(store: rp.Store, gen: int, rel: str, *, placeholder: bytes) -> bytes:
    """Carry a generation file byte-identical from the current generation;
    emit the placeholder when there is no prior generation (the file's
    writer owns its content — carried files are never edited here)."""
    if gen > 0:
        body = store.read(_conf_name(gen, rel))
        if body is not None:
            return body
    return placeholder


def _empty_withdrawn(gen: int) -> bytes:
    return (
        "# sig.withdrawn-conf — the withdrawal deny barrier, conf generation\n"
        f"# {gen}. Empty map: no dispositions carried forward. The writer is\n"
        "# `sig-ops release withdraw` (P35.55, REL-08): each withdraw writes\n"
        "# the deny lines + staged/conf/tombstone/<hash> bodies into the NEW\n"
        "# generation; promote carries them byte-identical.\n"
    ).encode()


def _empty_selectors(gen: int) -> bytes:
    return (
        "# sig.selectors-conf — the J3 §8.3 selector routes, conf generation\n"
        f"# {gen}. Placeholder: no selector rows carried forward (the\n"
        "# selector writer lands with the J3/TX-13b selector rows).\n"
    ).encode()


def catalog_v2(
    store: rp.Store,
    *,
    gen: int,
    pub: str,
    label: str,
    meta: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """``sig.publication-catalog/2`` — the machine index served at
    ``/releases/catalog.json``. Entries derive from the journal fold, the
    label map, the earlier generations' own pointers, and the new pub's
    staged catalog entry — every field sourced, never invented."""
    states = _publication_states(store)
    labels = read_label_map(store)
    history = _generation_history(store)
    entries: list[dict[str, Any]] = []
    all_pubs = sorted(set(states) | set(labels) | set(history) | {pub})
    activated_at: str | None
    p_label: str | None
    for p in all_pubs:
        if p == pub:
            state = "promoted"
            activated_at = _iso(now)
            p_label = label
            p_meta = meta
        else:
            prior = history.get(p)
            if prior:
                state = "superseded"
                activated_at = prior.get("activated_at")
                p_label = prior.get("label") or labels.get(p)
            else:
                state = states.get(p) or "never-promoted"
                activated_at = None
                p_label = labels.get(p)
            p_meta = read_release_meta(store, p) if state != "never-promoted" else {}
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
        "schema": CATALOG_SCHEMA_V2,
        "conf_gen": gen,
        "generated_at": _iso(now),
        "generator": "sig-ops release promote (the release tool alone — C4 NEW-10)",
        "entries": entries,
    }


def releases_index_html(catalog: dict[str, Any], *, gen: int) -> bytes:
    """The generated ``/releases/`` index (C4 NEW-10) — a deterministic
    table over the v2 catalog; promoted landings link, withdrawn/superseded
    and never-promoted rows state themselves (§3.1)."""
    rows: list[str] = []
    for e in catalog["entries"]:
        pub = e["publication_id"]
        label = html.escape(str(e.get("label") or "—"))
        state = html.escape(str(e.get("state") or ""))
        link = (
            f'<a href="/releases/{pub}/"><code>{pub[:18]}…</code></a>'
            if e.get("state") == "promoted"
            else f"<code>{html.escape(pub[:18])}…</code>"
        )
        rows.append(
            f'<tr data-state="{state}"><td>{label}</td><td>{link}</td>'
            f"<td>{state}</td><td>{html.escape(str(e.get('as_of_world') or '—'))}</td>"
            f"<td>{html.escape(str(e.get('activated_at') or '—'))}</td></tr>"
        )
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Releases — SIG</title></head>
<body>
<!-- {INDEX_SCHEMA_NOTE} · conf generation {gen} · generated by
     `sig-ops release promote` — the release tool is this file's only
     writer (C4 NEW-10); never hand-edited. -->
<h1>Releases</h1>
<p>The current release is <code>conf_gen&nbsp;{gen}</code>'s latest
pointer. Unpromoted candidates stay private; withdrawn content answers
410, never silently.</p>
<table><thead><tr><th>Label</th><th>Publication</th><th>State</th>
<th>As-of (world)</th><th>Activated</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody></table>
</body></html>
"""
    return doc.encode("utf-8")


def compose_generation(
    store: rp.Store,
    *,
    gen: int,
    pub: str,
    label: str,
    release_class: str,
    approval_ref: dict[str, Any] | None,
    meta: dict[str, Any],
    api_image: str | None,
    web_image: str | None,
    now: datetime,
    withdrawn_conf: bytes | None = None,
    withdrawals_sha256: str | None = None,
) -> dict[str, bytes]:
    """Every ``registry/conf/<gen>/`` object, deterministic — the dry-run
    plan and the apply write compose the same bytes.

    ``withdrawn_conf``: when the caller re-derived the deny map from the
    CURRENT withdrawal registry (D-P35.54-1), those bytes win over the
    carried copy; ``withdrawals_sha256`` stamps the registry digest the
    map was composed from into ``latest.json`` — a later promote detects
    the drift from the pointer alone.
    """
    prior_gen = gen - 1
    promoted = read_promoted_map(store, prior_gen) | {pub}
    latest = {
        "schema": LATEST_SCHEMA_V2,
        "label": label,
        "publication_id": pub,
        "manifest_sha256": meta.get("manifest_sha256"),
        "descriptor_sha256": meta.get("descriptor_sha256"),
        "activated_at": _iso(now),
        "conf_gen": gen,
        "class": "R" if release_class == "class_r" else "S",
        "approval_ref": approval_ref,
        "previous": (read_generation(store, prior_gen) or {}).get("publication_id"),
        "serving": {"sig_api_image": api_image, "sig_web_image": web_image},
        "rolled_back": False,
        "withdrawals_sha256": withdrawals_sha256,
    }
    catalog = catalog_v2(store, gen=gen, pub=pub, label=label, meta=meta, now=now)
    latest_bytes = _canonical(latest)
    return {
        "promoted.map": render_promoted_map(promoted, gen=gen),
        "latest.json": latest_bytes,
        "withdrawn.conf": (
            withdrawn_conf
            if withdrawn_conf is not None
            else _carry_or_placeholder(
                store, prior_gen, "withdrawn.conf", placeholder=_empty_withdrawn(gen)
            )
        ),
        "selectors.conf": _carry_or_placeholder(
            store, prior_gen, "selectors.conf", placeholder=_empty_selectors(gen)
        ),
        "labels.conf": render_labels_conf(read_label_map(store), gen=gen),
        "releases/index.html": releases_index_html(catalog, gen=gen),
        "releases/catalog.json": _canonical(catalog),
        "releases/latest.json": latest_bytes,
    }


def write_generation(store: rp.Store, gen: int, files: dict[str, bytes]) -> list[str]:
    """Write a whole generation — every object create-if-absent. A name
    that already exists refuses BEFORE any write (the two-phase check
    makes a generation collision atomic, never partial)."""
    names = sorted(_conf_name(gen, rel) for rel in files)
    existing = [n for n in names if store.stat(n) is not None]
    if existing:
        raise rp.PipelineError(
            "generation-exists",
            f"conf generation {gen} already carries {existing} — a generation "
            "is immutable once written (NEW-4/NEW-7)",
        )
    written: list[str] = []
    for rel, body in files.items():
        name = _conf_name(gen, rel)
        try:
            store.insert(name, body, content_type=_media_type(name))
        except Exception as exc:
            raise rp.PipelineError(
                "generation-collision",
                f"{name} appeared mid-write ({exc}) — a generation is "
                "immutable; refusing rather than overwriting",
            ) from exc
        written.append(name)
    return written


def _media_type(name: str) -> str:
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".html"):
        return "text/html"
    return "application/octet-stream"


# --------------------------------------------------------------------------- #
# The service roll — api then web, by digest (ADR-220 D5)                    #
# --------------------------------------------------------------------------- #


@dataclass
class ServiceRoll:
    """One Cloud Run service roll leg — the args are recorded verbatim
    whether or not they ever execute."""

    service: str
    image_digest: str
    env: dict[str, str]
    min_instances: int | None
    args: list[str]
    status: str = "prepared"  # prepared → rolled | refused
    before_image: str | None = None
    revision: str | None = None
    detail: str | None = None


def service_update_args(
    service: str,
    *,
    image_digest: str,
    env: dict[str, str],
    project: str,
    region: str,
    min_instances: int | None = None,
) -> list[str]:
    """The ``gcloud run services update`` argv for one leg — digest-pinned
    image, per-revision env, ``min-instances`` when given (the flip keeps
    ≥1 web instance so the latest view never scales to zero, §4.3)."""
    args = [
        "run",
        "services",
        "update",
        service,
        f"--project={project}",
        f"--region={region}",
        f"--image={image_digest}",
        "--update-env-vars=" + ",".join(f"{k}={v}" for k, v in sorted(env.items())),
    ]
    if min_instances is not None:
        args.append(f"--min-instances={min_instances}")
    return args


def describe_service(service: str, *, project: str, region: str, gcloud: Any) -> dict[str, Any]:
    out = gcloud(
        [
            "run",
            "services",
            "describe",
            service,
            f"--project={project}",
            f"--region={region}",
            "--format=json",
        ]
    )
    try:
        doc = json.loads(out)
    except ValueError as exc:
        raise rp.PipelineError(
            "describe-failed", f"{service}: describe output is not JSON — {exc}"
        ) from exc
    return doc if isinstance(doc, dict) else {}


def _service_container(svc: dict[str, Any]) -> dict[str, Any]:
    spec = svc.get("spec") or {}
    template = spec.get("template") or {}
    tspec = template.get("spec") or {}
    containers = tspec.get("containers") or []
    return containers[0] if containers else {}


def _service_env(svc: dict[str, Any]) -> dict[str, str]:
    return {
        str(e.get("name")): str(e.get("value"))
        for e in (_service_container(svc).get("env") or [])
        if isinstance(e, dict) and e.get("name") is not None
    }


def plan_service_roll(
    service: str,
    *,
    image_digest: str,
    env: dict[str, str],
    project: str,
    region: str,
    min_instances: int | None = None,
    gcloud: Any = None,
) -> ServiceRoll:
    """Plan one service roll. Refuses a non-digest image ref (an image
    roll is pinned by construction — job_roll's DIGEST_REF contract) and
    refuses ``SIG_STAGING=1`` on any service not named ``*-staging`` —
    the staging gate is a rendered constant, never a deployable mistake
    (GT-9)."""
    if not DIGEST_REF.match(image_digest):
        raise rp.PipelineError(
            "image-not-digest",
            f"{service}: {image_digest!r} is not a digest-pinned ref "
            "(<repo>/<image>@sha256:<64>) — rolls never move a tag",
        )
    if env.get("SIG_STAGING") == "1" and not service.endswith("-staging"):
        raise rp.PipelineError(
            "staging-env-on-public",
            f"{service}: SIG_STAGING=1 belongs on a *-staging origin only — "
            "refusing to render the bypass on a public service (GT-9)",
        )
    staging_env = env.get("SIG_STAGING")
    if staging_env is not None and staging_env not in ("0", "1"):
        raise rp.PipelineError(
            "bad-staging-env", f"{service}: SIG_STAGING={staging_env!r} — only 0|1 render"
        )
    roll = ServiceRoll(
        service=service,
        image_digest=image_digest,
        env=dict(env),
        min_instances=min_instances,
        args=service_update_args(
            service,
            image_digest=image_digest,
            env=env,
            project=project,
            region=region,
            min_instances=min_instances,
        ),
    )
    if gcloud is not None:
        before = describe_service(service, project=project, region=region, gcloud=gcloud)
        roll.before_image = str(_service_container(before).get("image") or "") or None
    return roll


def apply_service_roll(roll: ServiceRoll, *, project: str, region: str, gcloud: Any) -> ServiceRoll:
    """Execute one leg then verify the deployed revision: image digest,
    every planned env var, the ready revision name — a drifted outcome
    refuses (the api leg refusing means web never starts: no
    mixed-release window)."""
    gcloud(roll.args)
    after = describe_service(roll.service, project=project, region=region, gcloud=gcloud)
    image = str(_service_container(after).get("image") or "")
    if image != roll.image_digest:
        raise rp.PipelineError(
            "roll-drift",
            f"{roll.service}: deployed image {image!r} != pinned {roll.image_digest!r}",
        )
    env = _service_env(after)
    drifted = {k: v for k, v in roll.env.items() if env.get(k) != v}
    if drifted:
        raise rp.PipelineError(
            "roll-env-drift",
            f"{roll.service}: the revision does not carry the planned env "
            f"{sorted(drifted)} — got {env}",
        )
    status = after.get("status") or {}
    revision = str(status.get("latestReadyRevisionName") or "")
    if not revision:
        raise rp.PipelineError(
            "roll-not-ready",
            f"{roll.service}: no latestReadyRevisionName — the roll did not converge",
        )
    roll.status = "rolled"
    roll.revision = revision
    return roll


# --------------------------------------------------------------------------- #
# The post-promote checks (invoked, never re-implemented — ADR-220 D6)       #
# --------------------------------------------------------------------------- #


def default_post_checks(store: rp.Store, *, gen: int, pub: str) -> list[dict[str, Any]]:
    """The structural post-promote set: every generation object exists and
    says what the promote wrote — plus the V7 api-parity check invoked
    against the staged tree when a local registry makes it reachable
    (release_publish_verify's check, never a re-implementation)."""
    checks: list[dict[str, Any]] = []

    def record(check_id: str, ok: bool, detail: str, **extra: Any) -> None:
        checks.append(
            {"id": check_id, "status": "pass" if ok else "fail", "detail": detail, **extra}
        )

    latest = read_generation(store, gen)
    record(
        "conf.latest",
        latest is not None
        and latest.get("publication_id") == pub
        and latest.get("conf_gen") == gen,
        f"conf/{gen}/latest.json names {pub} at gen {gen}"
        if latest
        else "latest.json absent or unreadable",
    )
    promoted = read_promoted_map(store, gen)
    record(
        "conf.promoted-map",
        pub in promoted,
        f"conf/{gen}/promoted.map lists {pub}"
        if pub in promoted
        else f"conf/{gen}/promoted.map does not list {pub}",
    )
    for rel in ("withdrawn.conf", "selectors.conf", "labels.conf"):
        record(
            f"conf.{rel}",
            store.stat(_conf_name(gen, rel)) is not None,
            f"conf/{gen}/{rel} present (carried into this generation)",
        )
    for rel in ("releases/index.html", "releases/catalog.json", "releases/latest.json"):
        record(
            f"conf.{rel}",
            store.stat(_conf_name(gen, rel)) is not None,
            f"conf/{gen}/{rel} present (the release tool's only index)",
        )
    served = store.read(_conf_name(gen, "releases/latest.json"))
    pointer = store.read(_conf_name(gen, "latest.json"))
    record(
        "conf.latest-alias",
        served is not None and served == pointer,
        "the /releases/latest.json alias serves the pointer byte-identically",
    )
    cat_body = store.read(_conf_name(gen, "releases/catalog.json"))
    if cat_body is not None:
        try:
            cat = json.loads(cat_body)
        except ValueError:
            cat = {}
        mine = [e for e in (cat.get("entries") or []) if e.get("publication_id") == pub]
        record(
            "conf.catalog",
            bool(mine) and mine[0].get("state") == "promoted",
            f"catalog v2 entry for {pub} reads state=promoted"
            if mine
            else "the v2 catalog carries no entry for the promoted pub",
        )
    else:
        record("conf.catalog", False, "releases/catalog.json unreadable")
    # V7 api-parity — invoked, never re-implemented (release_publish_verify
    # owns the check; only a local registry can reach the staged bytes).
    if isinstance(store, rp.LocalDirStore):
        manifest = store.read(f"staged/releases/{pub}/integrity_manifest.json")
        if manifest is not None:
            from . import release_publish_verify as rpv

            try:
                artifacts = (json.loads(manifest).get("artifacts")) or []
                res = rpv.api_parity_check(Path(store.root) / "staged", pub, artifacts)
                checks.append(
                    {
                        "id": res.get("id", "PF.api_parity"),
                        "status": res.get("status", "pass"),
                        "detail": res.get("detail", ""),
                        "evidence": res.get("evidence"),
                    }
                )
            except Exception as exc:  # noqa: BLE001 — a refusal is a failed check
                checks.append(
                    {
                        "id": "PF.api_parity",
                        "status": "fail",
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
    return checks


# --------------------------------------------------------------------------- #
# The verb                                                                   #
# --------------------------------------------------------------------------- #


def verb_promote(
    store: rp.Store,
    *,
    apply_: bool,
    publication_id: str,
    approval: str | None = None,
    label: str | None = None,
    release_class: str | None = None,
    api_image: str | None = None,
    web_image: str | None = None,
    min_instances: int = 1,
    project: str | None = None,
    region: str | None = None,
    execute_rolls: bool = False,
    gcloud: Any = None,
    post_checks: Callable[..., list[dict[str, Any]]] | None = None,
    derive_barrier: Callable[..., bytes] | None = None,
    break_lock: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """``promote`` — the §5.1 sequence: check the approval → write
    ``conf/<gen+1>`` → roll sig-api then sig-web by digest → post-promote
    checks → ``promoted`` event. Metadata-only: zero bytes under
    ``staged/**`` are written or copied (SIG-REL-006).

    ``derive_barrier`` (D-P35.54-1, wired by the caller to
    ``release_reversal.derive_withdrawal_barrier``): when the withdrawal
    registry's digest moved since the prior generation's marker, apply
    re-derives ``withdrawn.conf`` from the CURRENT registry through this
    hook over a throwaway mirror — a disposition journaled between the
    candidate's verify and its promote lands in the promoted generation's
    deny map. The marker ``withdrawals_sha256`` stamps every new
    ``latest.json`` either way.

    Resumable: a ``conf/<gen+1>`` already naming this pub means a crashed
    promote — the write is skipped and the rolls/checks/event continue.
    ``--execute-rolls`` runs the gcloud legs for real (the operator's leg);
    absent, the conf generation is written and the roll args are recorded
    ``prepared`` verbatim — the composed stack executes the same flip by
    recreating the service with the new env.
    """
    pub = publication_id
    if not PUB_RE.match(pub or ""):
        raise rp.PipelineError(
            "bad-publication-id",
            f"{pub!r} is not a p-<64hex> publication id",
        )
    now = now or _now()
    gen = current_generation(store)
    current = read_generation(store, gen) if gen else None
    # A crashed promote wrote conf/<gen> naming this pub but never
    # journaled `promoted` — the current generation IS the half-finished
    # one; resume completes it (rolls + checks + event), never rewrites.
    resume = False
    events = rp.list_events(store, pub)
    if current and current.get("publication_id") == pub:
        promoted_here = any(
            ev.get("verb") == "promoted" and ev.get("conf_gen") == gen for ev in events
        )
        if promoted_here:
            return {
                "verb": "promote",
                "publication_id": pub,
                "outcome": "already-promoted",
                "conf_gen": gen,
                "label": current.get("label"),
                "applied": False,
            }
        resume = True
    next_gen = gen if resume else gen + 1
    # The candidate gate — the journal is the state machine (§3.4): the
    # candidate must carry a verify (or classify) record, and must never
    # have been promoted, withdrawn or rolled back. A re-promote is the
    # rollback verb's shape (P35.55), never this verb's.
    folded = rp.fold_state(events, pub)
    history = set(folded["history"])
    if "promoted" in history:
        raise rp.PipelineError(
            "already-promoted-once",
            f"{pub} already carries a `promoted` event — a re-promote is "
            "the rollback verb's shape (P35.55); this verb refuses",
        )
    if history & {"withdrawn-whole", "rolled-back-from"}:
        raise rp.PipelineError(
            "terminal-candidate",
            f"{pub} carries {sorted(history & {'withdrawn-whole', 'rolled-back-from'})} "
            "— a withdrawn or rolled-back release never re-promotes (RM-1)",
        )
    if not history & {"verified", "classified"}:
        raise rp.PipelineError(
            "not-promotable",
            f"{pub} folds to {folded['state']!r} — promote needs a "
            "verified or classified record in the journal (RM-6)",
        )
    staged = [ns for ns in rp.STAGED_NAMESPACES if store.list(f"staged/{ns}/{pub}/")]
    if not staged:
        raise rp.PipelineError(
            "unstaged",
            f"{pub} carries no staged/{'{'}r,v,s,releases{'}'}/ tree — stage before promote",
        )
    # The label — the staged descriptor's own stamp, or an explicit arg
    # validated against it (never trusted blind).
    meta = read_release_meta(store, pub)
    label_map = read_label_map(store)
    label = label or meta.get("label") or label_map.get(pub)
    if not label:
        raise rp.PipelineError(
            "no-label",
            f"{pub} carries no label — the descriptor/catalog_entry stamp or --label must name it",
        )
    if meta.get("label") and label != meta["label"]:
        raise rp.PipelineError(
            "label-mismatch",
            f"--label {label!r} != the release's stamped {meta['label']!r}",
        )
    # The class — the journal's classified event wins; --class only when
    # the journal is silent; fail-closed Class S (the classifier's RM-6
    # default). Class S additionally needs the signed readout.
    cls = journal_class(store, pub) or release_class or "class_s"
    if cls not in ("class_r", "class_s"):
        raise rp.PipelineError("bad-class", f"{cls!r} — only class_r|class_s")
    # The approval — required for apply; checked read-only either way.
    approval_ref: dict[str, Any] | None = None
    if approval:
        approval_ref = check_approval(store, pub, cls, approval, now=now)
    elif apply_:
        raise rp.PipelineError(
            "approval-required",
            "promote --apply needs --approval <name> naming the operator's "
            f"{APPROVALS_PREFIX}<name> record — the verb checks it, "
            "never creates one",
        )
    # D-P35.54-1 — the withdrawal-registry marker: the prior generation's
    # pointer records the digest its barrier was composed from (a marker
    # absent from the pointer stands for the empty registry). On drift the
    # APPLY path re-derives withdrawn.conf over a staged mirror — never a
    # carried, possibly-stale, byte copy — and the in-lock re-check refuses
    # a drift that lands between compose and write.
    w_body = store.read("registry/withdrawals.json")
    w_sha = _sha256(w_body or b"")
    prior_marker = (current or {}).get("withdrawals_sha256")
    barrier_drifted = (prior_marker or _sha256(b"")) != w_sha
    derived_barrier: bytes | None = None
    if apply_ and barrier_drifted and derive_barrier is not None and not resume:
        with tempfile.TemporaryDirectory(prefix="sig-promote-barrier-") as td:
            derived_barrier = derive_barrier(store, Path(td), active_pub=pub)
    files = compose_generation(
        store,
        gen=next_gen,
        pub=pub,
        label=label,
        release_class=cls,
        approval_ref=approval_ref,
        meta=meta,
        api_image=api_image,
        web_image=web_image,
        now=now,
        withdrawn_conf=derived_barrier,
        withdrawals_sha256=w_sha,
    )
    web_env = {
        "SIG_CONF_GEN": str(next_gen),
        "SIG_LATEST_PUB": pub,
        "SIG_LATEST_LABEL": label,
        "SIG_STAGING": "0",
    }
    api_env = {"SIG_CONF_GEN": str(next_gen), "SIG_LATEST_PUB": pub}
    legs: list[ServiceRoll] = []
    plan: list[str] = [
        f"check {APPROVALS_PREFIX}<approval> authorises a {cls} promote of {pub}",
        f"write registry/conf/{next_gen}/ ({len(files)} objects, create-if-absent"
        + ("; withdrawn.conf re-derived — barrier digest drifted" if barrier_drifted else "")
        + ")",
        f"roll sig-api → {api_image or '<no image pinned>'} (env: {sorted(api_env)})",
        f"roll sig-web → {web_image or '<no image pinned>'} "
        f"(env: {sorted(web_env)}; min-instances={min_instances})",
        "run the post-promote checks (structural + V7 api-parity when local)",
        "journal the `promoted` event under registry/events/ (append-only)",
    ]
    if api_image and web_image and project and region:
        legs.append(
            plan_service_roll(
                "sig-api",
                image_digest=api_image,
                env=api_env,
                project=project,
                region=region,
                min_instances=None,
                gcloud=gcloud if execute_rolls else None,
            )
        )
        legs.append(
            plan_service_roll(
                "sig-web",
                image_digest=web_image,
                env=web_env,
                project=project,
                region=region,
                min_instances=min_instances,
                gcloud=gcloud if execute_rolls else None,
            )
        )
    result: dict[str, Any] = {
        "verb": "promote",
        "publication_id": pub,
        "label": label,
        "conf_gen": next_gen,
        "previous_generation": gen,
        "class": cls,
        "resume": resume,
        "staged_namespaces": staged,
        "withdrawals_sha256": w_sha,
        "barrier": "re-derived" if derived_barrier is not None else "carried",
        "plan": plan,
        "generation_files": sorted(files),
        "promoted_pubs": sorted(parse_promoted_map(files["promoted.map"].decode())),
        "approval": approval_ref,
        "rolls": [
            {
                "service": leg.service,
                "image_digest": leg.image_digest,
                "env": leg.env,
                "min_instances": leg.min_instances,
                "status": leg.status,
                "args": leg.args,
            }
            for leg in legs
        ]
        or None,
        "copies_release_bytes": False,
        "applied": False,
    }
    if not apply_:
        result["dry_run"] = True
        return result
    with rp.acquire_lock(store, "promote", break_lock=break_lock, now=now):
        # D-P35.54-1, the refusal half: a disposition that lands between
        # the composed barrier and this write moves the registry digest —
        # refuse; the operator re-runs and the next compose re-derives.
        if _sha256(store.read("registry/withdrawals.json") or b"") != w_sha:
            raise rp.PipelineError(
                "withdrawal-drift",
                "registry/withdrawals.json changed between compose and the "
                "locked write — the composed deny map is stale; re-run "
                "promote (the next compose re-derives it)",
            )
        written: list[str] = []
        if not resume:
            written = write_generation(store, next_gen, files)
        else:
            written = [
                _conf_name(next_gen, rel)
                for rel in sorted(files)
                if store.stat(_conf_name(next_gen, rel))
            ]
        result["written"] = sorted(written)
        # The rolls — api first (a serving-incapable api is never public),
        # web with min-instances=1 so the latest view never scales to zero.
        if execute_rolls:
            if not (api_image and web_image and project and region):
                raise rp.PipelineError(
                    "roll-args-missing",
                    "--execute-rolls needs --api-image + --web-image + --project + --region",
                )
            if gcloud is None:
                raise rp.PipelineError(
                    "roll-runner-missing",
                    "--execute-rolls needs a gcloud runner (cli.py wires "
                    "job_roll.gcloud_cli; tests inject one)",
                )
            for idx, leg in enumerate(legs):
                try:
                    apply_service_roll(leg, project=project, region=region, gcloud=gcloud)
                except rp.PipelineError as exc:
                    leg.status = "refused"
                    leg.detail = str(exc)
                    later = legs[idx + 1].service if idx + 1 < len(legs) else None
                    emit_failure = emit_failed(store, pub, next_gen, label, exc, legs, now=now)
                    raise rp.PipelineError(
                        exc.code,
                        f"the {leg.service} leg refused — "
                        + (
                            f"the flip aborted before {later} touched traffic "
                            if later
                            else "the roll did not converge "
                        )
                        + f"({emit_failure})",
                    ) from exc
        else:
            for leg in legs:
                leg.detail = (
                    "prepared_not_executed — the composed stack flips by "
                    "recreating the service with this env; the hosted leg "
                    "is the operator's (OP-24)"
                )
        result["rolls"] = [
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
        # The post-promote checks.
        checks = (post_checks or default_post_checks)(store, gen=next_gen, pub=pub)
        failed_checks = [c for c in checks if c.get("status") == "fail"]
        result["checks"] = checks
        if failed_checks:
            emit_failed(
                store,
                pub,
                next_gen,
                label,
                rp.PipelineError(
                    "post-check-failed",
                    "; ".join(f"{c['id']}: {c['detail']}" for c in failed_checks),
                ),
                legs,
                now=now,
            )
            raise rp.PipelineError(
                "post-check-failed",
                f"{len(failed_checks)} post-promote check(s) failed — the "
                f"generation is written (resume continues at the checks): "
                + "; ".join(c["id"] for c in failed_checks),
            )
        name = rp.emit_event(
            store,
            "promoted",
            pub,
            {
                "outcome": "recorded",
                "conf_gen": next_gen,
                "previous_generation": gen,
                "label": label,
                "class": cls,
                "approval_ref": approval_ref,
                "resume": resume,
                "serving": {"sig_api_image": api_image, "sig_web_image": web_image},
                "rolls": [
                    {
                        "service": leg.service,
                        "image_digest": leg.image_digest,
                        "status": leg.status,
                        "revision": leg.revision,
                        "min_instances": leg.min_instances,
                    }
                    for leg in legs
                ],
                "checks": [{"id": c["id"], "status": c["status"]} for c in checks],
                "written": sorted(written),
                "withdrawals_sha256": w_sha,
                "barrier": "re-derived" if derived_barrier is not None else "carried",
            },
            now=now,
        )
        result.update(applied=True, event=name, outcome="promoted")
    return result


def emit_failed(
    store: rp.Store,
    pub: str,
    gen: int,
    label: str,
    exc: BaseException,
    legs: list[ServiceRoll],
    *,
    now: datetime | None = None,
) -> str:
    """Journal the §3.4 ``failed`` state — the promote's refusal is audit
    visible with the generation + how far the rolls got."""
    return rp.emit_event(
        store,
        "failed",
        pub,
        {
            "outcome": "failed",
            "conf_gen": gen,
            "label": label,
            "refusal": str(exc),
            "code": getattr(exc, "code", "promote-failed"),
            "rolls": [
                {"service": leg.service, "status": leg.status, "detail": leg.detail} for leg in legs
            ],
        },
        now=now,
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "APPROVAL_SCHEMA",
    "APPROVALS_PREFIX",
    "CATALOG_SCHEMA_V2",
    "CONF_PREFIX",
    "GENERATION_FILES",
    "LATEST_SCHEMA_V2",
    "PROMOTABLE_STATES",
    "PUB_RE",
    "ROLL_ORDER",
    "ServiceRoll",
    "apply_service_roll",
    "catalog_v2",
    "check_approval",
    "compose_generation",
    "current_generation",
    "default_post_checks",
    "describe_service",
    "journal_class",
    "parse_promoted_map",
    "plan_service_roll",
    "read_generation",
    "read_label_map",
    "read_promoted_map",
    "read_release_meta",
    "releases_index_html",
    "render_labels_conf",
    "render_promoted_map",
    "service_update_args",
    "verb_promote",
    "write_generation",
]
