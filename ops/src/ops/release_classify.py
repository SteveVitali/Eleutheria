# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.60 (REL-06) — the §7.3 release classifier, the standing-go checks and
the §7.4 Class-S readout generator (SIG-REL-012, SIG-CONF-010, ADR-154).

Three pieces live here, all *consumers* of landed evidence:

* **The classifier** — :func:`classify` maps the candidate release onto the
  §7.3 matrix. Its inputs are the *emitted* P35.58 suite rows (V14's
  ``deltas`` block and V15's gate evidence, read verbatim from the
  ``sig.release-results/1`` docs ``release verify`` wrote), the staged
  release's declared metadata (descriptor / ``release.json`` / integrity
  manifest / catalog entry), the journal (the cut's provenance) and the
  conf-generation history (the last Class-S-signed code). It never
  re-derives a V14 measurement and it **fails closed**: Class R only when
  every §7.3 R-column condition is proven — any trigger, any unevaluable
  check, any anomaly → Class S (SIG-ENG-042, RM-6).
* **The standing go** — :func:`evaluate_standing_go` validates an operator's
  ``sig.promotion-approval/1`` ``standing_go`` record: present, adopted
  (never implied), unexpired (an expired go is honoured once for a release
  classified while it was still valid — the in-flight rule), unvoided,
  in-scope. Voiding is append-only: a ``<name>.voided`` record beside the
  go, written by the classifier when a voiding trigger lands
  (B-9: ratchet regression, Part VIII screen change, new source).
* **The readout** — :func:`draft_readout` fills the §7.4 fields into a
  labelled **agent-drafted** document pair (markdown + JSON twin under
  ``registry/readouts/``). The signature slot is emitted *empty* — an agent
  never signs, and the required posture sentences are the spec's verbatim:
  "single maintainer, no second reviewer" (ADR-163), "no human check
  performed" (SIG-CONF-010), and SIG-MEM-009's authorship sentence. The
  pending-readout notice goes through the landed ``alerts`` seam — the
  operator's destination lives in the environment-configured channel,
  never in a repository file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json, sha256_hex
from exports.release_identity import parse_instant

from . import alerts
from . import release_pipeline as rp
from . import release_verify as rv

# --------------------------------------------------------------------------- #
# Schemas, names, vocabulary                                                   #
# --------------------------------------------------------------------------- #

#: The classification record the apply-path appends (append-only objects).
CLASSIFICATION_SCHEMA = "sig.release-classification/1"
CLASSIFICATIONS_PREFIX = "registry/classifications/"

#: The readout pair — the markdown the operator signs and its JSON twin.
READOUT_SCHEMA = "sig.release-readout/1"
READOUTS_PREFIX = "registry/readouts/"

#: The append-only void marker beside a standing-go record: voiding writes
#: ``registry/approvals/<name>.voided`` — never an edit of the go itself.
GO_VOID_SCHEMA = "sig.standing-go-void/1"
GO_VOID_SUFFIX = ".voided"

#: The notice kinds on the landed alert/mail channel (OBS.1 / ACT-02): a
#: Class-S readout draft awaits a signature; a Class-R classification is the
#: diff+check-results mail the standing go promises ("each such release is
#: emailed to me with its diff and check results" — B-9/G3 §7.3).
NOTICE_KIND_S = "release.readout-pending"
NOTICE_KIND_R = "release.classified"

#: §7.3 R-column bounds, verbatim: total −2 %…+15 %, no compartment
#: < −5 % or > +50 %, no source loses > 20 % (a source's share floor).
TOTAL_BOUNDS = (-2.0, 15.0)
COMP_BOUNDS = (-5.0, 50.0)
SOURCE_SHARE_FLOOR = 0.8

#: The adopted standing-go scope (B-9, verbatim in SIG-REL-012): the go is
#: **void** on a ratchet regression, a Part VIII screen change or a new
#: source. Those classifier triggers append the void record.
VOID_TRIGGERS = frozenset({"ratchet-regression", "new-source", "part-viii-screen-change"})

#: The §7.4 / SIG-CONF-010 / ADR-163 / SIG-MEM-009 wording, verbatim — the
#: readout draft carries each sentence exactly; a paraphrase is a defect.
WORDING_MAINTAINER = "single maintainer, no second reviewer"
WORDING_NO_HUMAN = "no human check performed"
WORDING_MEM9 = (
    "An operator or authorized human record supplies the decision; an agent "
    "must not sign or assume silence is approval."
)
#: The signature's explicit basis — the operator picks exactly one; both
#: options are SIG-CONF-010's wording verbatim.
BASIS_REVIEWED = "I have reviewed the readout fields and the diff summary"
BASIS_CHECKS_ONLY = "I have not reviewed the files; the signature attests to the checks only"

#: `version_schema` keys a delta on which is a §7.3 version/schema trigger.
VERSION_KEYS = (
    "descriptor_schema",
    "descriptor_version",
    "catalog_schema",
    "site_schema",
    "ruleset_version",
)

#: The descriptor ``versions`` fields a delta on which is a version/schema
#: trigger — §7.3's "same versions: ruleset, resolver, policy, projection,
#: ontology, descriptor-schema". Read from the two descriptors verbatim
#: (declared release metadata — never a re-measurement).
DESCRIPTOR_VERSION_KEYS = (
    "ruleset_version",
    "resolver_version",
    "policy_version",
    "projection_version",
    "search_index_version",
    "ontology_version",
    "descriptor_schema",
)


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(store: rp.Store, name: str) -> tuple[dict[str, Any] | None, str | None]:
    """``(doc, None)`` or ``(None, error)`` — an absent/unreadable object is
    evidence for the fail-closed path, never an exception."""
    body = store.read(name)
    if body is None:
        return None, f"{name} absent"
    try:
        doc = json.loads(body)
    except ValueError as exc:
        return None, f"{name} is not JSON: {exc}"
    if not isinstance(doc, dict):
        return None, f"{name} is not a JSON object"
    return doc, None


@dataclass
class _Verdicts:
    """The classifier's per-check ledger: every check lands exactly one row
    — ``r`` (R-condition proven), ``trigger`` (a named §7.2/§7.3 S trigger
    fired) or ``unevaluable`` (the input was absent/malformed — itself an
    S outcome). The class is R iff the ledger holds only ``r`` rows."""

    rows: list[dict[str, Any]] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    unevaluable: list[str] = field(default_factory=list)

    def r(self, check: str, detail: str, **evidence: Any) -> None:
        self.rows.append({"check": check, "verdict": "r", "detail": detail, **evidence})

    def trigger(self, trigger_id: str, detail: str, *, check: str | None = None) -> None:
        self.triggers.append(trigger_id)
        self.rows.append(
            {
                "check": check or trigger_id.split(":", 1)[0],
                "verdict": "trigger",
                "trigger": trigger_id,
                "detail": detail,
            }
        )

    def blocked(self, check: str, detail: str, **evidence: Any) -> None:
        self.unevaluable.append(check)
        self.rows.append({"check": check, "verdict": "unevaluable", "detail": detail, **evidence})


# --------------------------------------------------------------------------- #
# Suite-row consumption (the P35.58 inputs — read, never re-derived)          #
# --------------------------------------------------------------------------- #


def load_suite_documents(results: Path | str) -> tuple[list[dict[str, Any]], list[str]]:
    """Read a ``sig.release-results/1`` doc — a suite file or a results
    directory's ``suite-*.json`` docs. Returns ``(docs, unreadable_paths)``;
    unreadable files are reported so the classifier fails closed, never
    silently dropped."""
    path = Path(results)
    files: list[Path]
    if path.is_dir():
        files = sorted(path.glob("suite-*.json"))
    elif path.is_file():
        files = [path]
    else:
        return [], [f"{path} — no such file or directory"]
    docs: list[dict[str, Any]] = []
    bad: list[str] = []
    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            bad.append(f"{f.name}: {exc}")
            continue
        if isinstance(doc, dict) and doc.get("schema") == rv.RESULT_SCHEMA:
            docs.append(doc)
        else:
            bad.append(f"{f.name}: not a {rv.RESULT_SCHEMA} doc")
    return docs, bad


def _suite_rows(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("check")): r for r in suite.get("results") or [] if isinstance(r, dict)}


def _check_suite(
    v: _Verdicts, suites: list[dict[str, Any]], bad_paths: list[str], pub: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """The all-green gate: every S-mode suite row must be ``pass`` with zero
    waivers. Returns ``(s_suites, v14_row)`` for downstream consumption."""
    for bp in bad_paths:
        v.blocked("suite-input", f"results input unreadable: {bp}")
    s_suites = [s for s in suites if s.get("mode") == "S" and s.get("publication_id") == pub]
    if not s_suites:
        v.blocked(
            "suite-input",
            f"no S-mode {rv.RESULT_SCHEMA} suite names {pub} — the verify "
            "results are the classifier's only input (P35.58)",
        )
        return [], None
    v14: dict[str, Any] | None = None
    for suite in s_suites:
        sid = str(suite.get("object") or suite.get("origin") or "suite")
        rows = _suite_rows(suite)
        missing = [c for c in rv.CHECKS_S if c not in rows]
        if missing:
            v.blocked(
                "suite-input",
                f"{sid} lacks result rows for {missing} — a check without a "
                "recorded row is unevaluable",
            )
            continue
        waivers = list(suite.get("waivers") or [])
        if waivers or suite.get("verdict") == "waived":
            v.trigger(
                "waiver-present",
                f"{sid} carries waiver(s) {waivers or suite.get('verdict')!r} — "
                "a waiver is possible only with Class S (§5.5)",
                check="waivers",
            )
        for cid in rv.CHECKS_S:
            row = rows[cid]
            status = row.get("status")
            if status == "pass":
                continue
            v.trigger(
                f"check-not-green:{cid}",
                f"{sid} {cid} = {status!r}: {row.get('detail')!r} — §7.3 "
                "R-column requires all checks green",
                check="suite-green",
            )
        # V14's deltas are consumed even when the row failed — the emitted
        # numbers tell the classification's story either way.
        v14 = rows["V14"]
        # V15's quality-gate signal (ADR-154): a ratchet regression is always S.
        gate = ((rows.get("V15") or {}).get("evidence") or {}).get("gate") or {}
        ratchet = gate.get("ratchet_regressions") or []
        if (rows.get("V15") or {}).get("evidence", {}).get("class_s_signal") or ratchet:
            v.trigger(
                "ratchet-regression",
                f"V15 quality gate reports {len(ratchet)} ratchet regression(s) "
                f"{[str(r)[:120] for r in ratchet]} — a ratchet regression is "
                "always Class S (SIG-CONF-007/ADR-154)",
                check="ratchet",
            )
        ne = gate.get("not_evaluable_enforce") or []
        for check_id in ne:
            v.trigger(
                f"unevaluable-check:{check_id}",
                f"V15's gate could not evaluate enforce check {check_id} — "
                "an unevaluable check is Class S (SIG-ENG-042)",
                check="ratchet",
            )
    if v14 is None:
        v.blocked("deltas", "no V14 row in the S suite(s) — the deltas are absent")
    return s_suites, v14


# --------------------------------------------------------------------------- #
# The §7.3 checks                                                           #
# --------------------------------------------------------------------------- #


def _check_deltas(
    v: _Verdicts, deltas: dict[str, Any], v14_failures: list[str] | None = None
) -> None:
    """Apply the §7.3 bounds to V14's *emitted* delta values — the classifier
    reads the measured numbers; it never re-measures."""
    baseline = deltas.get("baseline")
    if not baseline:
        v.trigger(
            "first-release",
            "V14 reports no baseline release — the first release under the "
            "model (or a lost baseline) is Class S by name (§7.2)",
            check="baseline",
        )
        return
    v.r("baseline", f"baseline {str((baseline or {}).get('publication_id'))[:18]}… named")

    failures = [str(f) for f in (v14_failures or [])]  # V14's emitted failure lines

    rec = deltas.get("records") or {}
    total = rec.get("total") or {}
    pt, ct = total.get("previous"), total.get("current")
    if isinstance(pt, int) and isinstance(ct, int):
        tpct = ((ct - pt) / pt * 100.0) if pt else (100.0 if ct else 0.0)
        lo, hi = TOTAL_BOUNDS
        if tpct < lo or tpct > hi:
            v.trigger(
                "total-records-bounds",
                f"total records {pt} → {ct} ({tpct:+.1f}%) outside {lo:+.0f}%…{hi:+.0f}% (§7.3)",
                check="bounds",
            )
        else:
            v.r("bounds-total", f"total records {pt} → {ct} ({tpct:+.1f}%) in bounds")
    else:
        v.blocked("bounds-total", "V14 deltas.records.total is absent/malformed")
    comp_d = rec.get("per_compartment") or {}
    for comp, dd in sorted(comp_d.items()):
        p, c = dd.get("previous"), dd.get("current")
        pct = dd.get("pct")
        if p == 0 and c:
            v.trigger(
                f"new-compartment:{comp}",
                f"compartment {comp} appears first here (0 → {c} records) — a "
                "new compartment is Class S (§7.2)",
                check="compartments",
            )
        elif isinstance(pct, (int, float)) and (pct < COMP_BOUNDS[0] or pct > COMP_BOUNDS[1]):
            v.trigger(
                f"compartment-bounds:{comp}",
                f"compartment {comp}: {pct:+.1f}% outside "
                f"{COMP_BOUNDS[0]:+.0f}%…{COMP_BOUNDS[1]:+.0f}% (§7.3)",
                check="bounds",
            )
    for line in failures:
        v.trigger("v14-anomaly", f"V14 failure: {line}", check="v14-failures")

    srcs = deltas.get("sources") or {}
    if srcs.get("added"):
        v.trigger(
            "new-source",
            f"source(s) first public appearance: {srcs['added']} (§7.2 — also "
            "a standing-go void condition, B-9)",
            check="sources",
        )
    fp = deltas.get("template_fingerprint") or {}
    if fp.get("state") == "unavailable":
        v.blocked(
            "template-fingerprint",
            f"template fingerprint {fp.get('state')}: {fp.get('owner')} — unevaluable → S",
        )
    elif fp.get("changed"):
        v.trigger(
            "template-fingerprint-change",
            "the template fingerprint differs from the previous release's "
            "(§7.3 — a template drift is Class S)",
            check="template-fingerprint",
        )
    elif fp.get("current"):
        v.r(
            "template-fingerprint",
            f"template fingerprint equal ({str(fp.get('current'))[:12]}…)",
            fingerprint=fp.get("current"),
        )
    else:
        v.blocked("template-fingerprint", "V14 deltas.template_fingerprint is malformed")


def _check_source_withdrawals(v: _Verdicts, store: rp.Store, deltas: dict[str, Any]) -> None:
    """Removed sources: 'fewer only through recorded withdrawals' (§7.3)."""
    srcs = deltas.get("sources") or {}
    removed = list(srcs.get("removed") or [])
    if not removed:
        v.r("sources", "the source set is unchanged")
        return
    wdoc, werr = _read_json(store, "registry/withdrawals.json")
    if wdoc is None:
        v.blocked(
            "sources-withdrawn",
            f"{werr} — a dropped source needs a recorded withdrawal and the registry is unreadable",
        )
        return
    entries = wdoc.get("dispositions") or wdoc.get("entries") or []
    recorded: set[str] = set()
    for e in entries:
        if not isinstance(e, dict):
            continue
        if str(e.get("disposition") or "") in ("allow", "reinstate"):
            continue
        for key in (str(e.get("target_id") or ""), str(e.get("source_id") or "")):
            for sid in removed:
                if key == sid or key == f"source:{sid}":
                    recorded.add(sid)
    unrecorded = [s for s in removed if s not in recorded]
    if unrecorded:
        v.trigger(
            "source-withdrawal-unrecorded",
            f"source(s) dropped with no recorded withdrawal: {unrecorded} — "
            "'fewer only through recorded withdrawals' (§7.3)",
            check="sources-withdrawn",
        )
    else:
        v.r(
            "sources-withdrawn",
            f"removed source(s) {removed} each covered by a recorded withdrawal",
            recorded=sorted(recorded),
        )


def _check_licences(v: _Verdicts, deltas: dict[str, Any]) -> None:
    lic = deltas.get("licences") or {}
    added, removed = list(lic.get("added") or []), list(lic.get("removed") or [])
    if added or removed:
        v.trigger(
            "licence-change",
            f"licence set changed +{added} −{removed} — a new licence, "
            "attribution text or redistribution lane is Class S (§7.2)",
            check="licences",
        )
    else:
        v.r("licences", "the licence set is unchanged")


def _check_versions(
    v: _Verdicts,
    deltas: dict[str, Any],
    cur_desc: dict[str, Any] | None,
    prev_desc: dict[str, Any] | None,
) -> None:
    """Same versions — two inputs: V14's emitted ``version_schema`` delta
    (the schema-level measure) and the descriptors' own ``versions`` block
    (the declared ruleset/resolver/policy/projection/ontology values)."""
    vd = deltas.get("version_schema") or {}
    prev, cur = vd.get("previous") or {}, vd.get("current") or {}
    if not prev or not cur:
        v.blocked(
            "versions",
            "V14 deltas.version_schema lacks a side — a version check it cannot run is Class S",
        )
        return
    fired = False
    for key in VERSION_KEYS:
        pv, cv = prev.get(key), cur.get(key)
        # absent on both sides is "equal" — a field the schema legitimately
        # never carries is no change; asymmetric absence IS a change
        if pv == cv:
            continue
        fired = True
        v.trigger(
            f"version-change:{key}",
            f"{key} {pv!r} → {cv!r} — a ruleset/resolver/policy/projection/"
            "ontology/descriptor-schema change is Class S (§7.2)",
            check="versions",
        )
    if cur_desc is None or prev_desc is None:
        v.blocked("versions", "a descriptor side is absent — versions unevaluable")
        return
    cvers, pvers = cur_desc.get("versions") or {}, prev_desc.get("versions") or {}
    for key in DESCRIPTOR_VERSION_KEYS:
        pv, cv = pvers.get(key), cvers.get(key)
        if pv == cv:
            continue
        fired = True
        if key == "policy_version":
            v.trigger(
                "part-viii-screen-change",
                f"policy_version {pv!r} → {cv!r} — the Part VIII "
                "sensitivity screen rides the policy package: a change "
                "is Class S and voids the standing go (B-9)",
                check="part-viii-screen",
            )
        else:
            v.trigger(
                f"version-change:{key}",
                f"versions.{key} {pv!r} → {cv!r} — a ruleset/resolver/"
                "policy/projection/ontology/descriptor-schema change is "
                "Class S (§7.2)",
                check="versions",
            )
    if not fired:
        v.r(
            "versions",
            "ruleset/resolver/policy/projection/ontology/schema versions all equal",
        )


def _surface_routes(store: rp.Store, pub: str) -> tuple[set[str] | None, str | None]:
    """The release's *non-record* route set — the manifest artifact paths
    minus the ``r/<pub>/c/<comp>/`` record churn a data refresh legitimately
    produces. Read from the declared integrity manifest (release metadata,
    not a V14 re-derivation)."""
    man, err = _read_json(store, f"staged/releases/{pub}/integrity_manifest.json")
    if man is None:
        return None, err
    out: set[str] = set()
    for a in man.get("artifacts") or []:
        p = str(a.get("path") or "")
        rel = p
        for prefix in (f"r/{pub}/", f"releases/{pub}/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix) :]
                break
        if rel.startswith("c/"):
            continue  # record-namespace churn — bounded by the §7.3 record deltas
        out.add(rel)
    return out, None


def _check_surfaces(v: _Verdicts, store: rp.Store, pub: str, baseline_pub: str | None) -> None:
    """Allow-list digest + the non-record public surface (§7.3 'same
    allow-list' / §7.2 'a route allow-list change; a new public surface')."""
    cur_rel, cerr = _read_json(store, f"staged/releases/{pub}/release.json")
    if cur_rel is None:
        v.blocked("allowlist", f"candidate release.json: {cerr}")
        return
    if baseline_pub is None:
        return  # the first-release trigger already fired
    prev_rel, perr = _read_json(store, f"staged/releases/{baseline_pub}/release.json")
    if prev_rel is None:
        v.blocked("allowlist", f"baseline release.json: {perr}")
        return
    csha, psha = cur_rel.get("routes_sha256"), prev_rel.get("routes_sha256")
    if csha is None or psha is None:
        v.blocked(
            "allowlist",
            f"routes_sha256 absent on {'candidate' if csha is None else 'baseline'} "
            "— the allow-list digest is the §7.3 input",
        )
    elif csha != psha:
        v.trigger(
            "allowlist-change",
            f"routes_sha256 {str(psha)[:12]}… → {str(csha)[:12]}… — a route "
            "allow-list change is Class S (§7.2)",
            check="allowlist",
        )
    else:
        v.r("allowlist", f"routes_sha256 equal ({str(csha)[:12]}…)")
    cur_surf, csurf_err = _surface_routes(store, pub)
    prev_surf, psurf_err = _surface_routes(store, baseline_pub)
    if cur_surf is None or prev_surf is None:
        v.blocked(
            "public-surface",
            f"integrity manifest unreadable: {csurf_err or psurf_err}",
        )
        return
    added = sorted(cur_surf - prev_surf)
    removed = sorted(prev_surf - cur_surf)
    if added:
        v.trigger(
            "new-public-surface",
            f"new non-record route(s) {added[:10]} — a new public surface is Class S (§7.2)",
            check="public-surface",
        )
    if removed:
        v.trigger(
            "surface-route-removed",
            f"non-record route(s) removed {removed[:10]} — a surface change is Class S",
            check="public-surface",
        )
    if not added and not removed:
        v.r("public-surface", "the non-record public surface is unchanged")


def _check_environment(v: _Verdicts, descriptor: dict[str, Any] | None, derr: str | None) -> None:
    if descriptor is None:
        v.blocked("environment", f"candidate descriptor.json: {derr}")
        return
    env = descriptor.get("environment")
    if env != "production":
        v.trigger(
            "non-production-environment",
            f"descriptor.environment {env!r} != 'production' — Class R needs "
            "the production environment (§7.3)",
            check="environment",
        )
    else:
        v.r("environment", "environment is production")


def _check_cut(v: _Verdicts, store: rp.Store, pub: str) -> dict[str, Any] | None:
    """The candidate's cut provenance — a replay or emergency cut is Class S
    by name (§7.2). The cut the candidate rode is the latest ``cut`` event
    preceding the candidate's first journal entry."""
    events = rp.list_events(store)
    first_idx: int | None = None
    for i, ev in enumerate(events):
        if ev.get("publication_id") == pub:
            first_idx = i
            break
    prior = events[: first_idx if first_idx is not None else len(events)]
    cut = next((e for e in reversed(prior) if e.get("verb") == "cut"), None)
    if cut is None:
        v.blocked(
            "cut-provenance",
            "the journal holds no `cut` event before this candidate — a "
            "scheduled/drift-triggered cut cannot be proven (§7.3)",
        )
        return None
    if cut.get("replay") or cut.get("emergency"):
        v.trigger(
            "replay-or-emergency-cut",
            f"the cut carried replay={cut.get('replay')!r} "
            f"emergency={cut.get('emergency')!r} — a --replay or --emergency "
            "cut is Class S (§7.2)",
            check="cut-provenance",
        )
    else:
        v.r(
            "cut-provenance",
            f"cut at {cut.get('t0') or cut.get('recorded_at')} — scheduled, "
            "no replay/emergency flag",
            cut_object=cut.get("object"),
        )
    return cut


def _check_fields(v: _Verdicts, store: rp.Store, pub: str, baseline_pub: str | None) -> None:
    """Disclosure set, evaluation status (§7.3 R-column: 'same …
    disclosures, and the same evaluation status')."""
    if baseline_pub is None:
        return
    cur, cerr = _read_json(store, f"staged/releases/{pub}/descriptor.json")
    prev, perr = _read_json(store, f"staged/releases/{baseline_pub}/descriptor.json")
    if cur is None or prev is None:
        v.blocked("fields", f"descriptor unreadable: {cerr or perr}")
        return
    if canonical_json(cur.get("disclosures") or []) != canonical_json(
        prev.get("disclosures") or []
    ):
        v.trigger(
            "disclosure-change",
            "the disclosure set/text differs — a change of disclosure text is Class S (§7.2)",
            check="fields",
        )
    else:
        v.r("disclosures", "disclosures identical")
    cev = str(((cur.get("evaluation") or {}).get("status")) or "")
    pev = str(((prev.get("evaluation") or {}).get("status")) or "")
    if cev != pev:
        v.trigger(
            "evaluation-status-change",
            f"evaluation.status {pev!r} → {cev!r} — an evaluation-status change is Class S (§7.2)",
            check="fields",
        )
    else:
        v.r("evaluation-status", f"evaluation.status {cev!r} unchanged")


def _check_signed_code(v: _Verdicts, store: rp.Store, descriptor: dict[str, Any] | None) -> None:
    """§7.3 R-column row 1: same ``code.commit`` as a release the operator
    signed under Class S. The newest conf generation carrying ``class:
    'S'`` names that release; its ``approval_ref`` must resolve to a
    ``signed_readout`` record, and that release's descriptor commit must
    equal the candidate's."""
    if descriptor is None:
        v.blocked("signed-code", "candidate descriptor absent")
        return
    cand_commit = str(((descriptor.get("code") or {}).get("commit")) or "")
    if not cand_commit:
        v.blocked("signed-code", "candidate descriptor carries no code.commit")
        return
    from . import release_conf as rc  # deferred — release_conf imports rp only

    signed_pub: str | None = None
    signed_gen: dict[str, Any] | None = None
    for gen in range(rc.current_generation(store), 0, -1):
        doc = rc.read_generation(store, gen)
        if not doc:
            continue
        if str(doc.get("class") or "") == "S" and rc.PUB_RE.match(
            str(doc.get("publication_id") or "")
        ):
            signed_pub = str(doc["publication_id"])
            signed_gen = doc
            break
    if signed_pub is None or signed_gen is None:
        v.trigger(
            "no-signed-code-baseline",
            "no conf generation records a Class-S-signed release — there is "
            "no signed code to be 'the same' as (§7.3)",
            check="signed-code",
        )
        return
    aref = signed_gen.get("approval_ref") or {}
    arec, aerr = _read_json(store, str(aref.get("object") or ""))
    if arec is None:
        v.blocked(
            "signed-code",
            f"the signed baseline's approval record is unreadable: {aerr}",
        )
        return
    if arec.get("kind") != "signed_readout" or arec.get("publication_id") != signed_pub:
        v.blocked(
            "signed-code",
            f"the recorded approval for gen {signed_gen.get('conf_gen')} is "
            f"kind {arec.get('kind')!r} naming {arec.get('publication_id')!r} — "
            "not a signed readout for the claimed baseline",
        )
        return
    sdesc, serr = _read_json(store, f"staged/releases/{signed_pub}/descriptor.json")
    if sdesc is None:
        v.blocked("signed-code", f"signed baseline's descriptor: {serr}")
        return
    signed_commit = str(((sdesc.get("code") or {}).get("commit")) or "")
    if signed_commit != cand_commit:
        v.trigger(
            "code-change",
            f"code.commit {signed_commit[:12]}… (signed at gen "
            f"{signed_gen.get('conf_gen')}) → {cand_commit[:12]}… — any code "
            "change is Class S (§7.2)",
            check="signed-code",
        )
    else:
        v.r(
            "signed-code",
            f"code.commit {cand_commit[:12]}… equals the Class-S-signed "
            f"release {signed_pub[:18]}… (gen {signed_gen.get('conf_gen')})",
            baseline=signed_pub,
        )


# --------------------------------------------------------------------------- #
# classify — the public entry point                                          #
# --------------------------------------------------------------------------- #


def classify(
    store: rp.Store,
    publication_id: str,
    *,
    suites: list[dict[str, Any]] | None = None,
    unreadable_inputs: list[str] | None = None,
    go: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify one staged candidate ``R`` or ``S``.

    ``suites`` are parsed ``sig.release-results/1`` docs (see
    :func:`load_suite_documents`); ``unreadable_inputs`` records inputs that
    could not be parsed (each lands as an unevaluable check → S). ``go``
    names the standing-go record to evaluate *as evidence* (the verdict is
    evidence, never the decision — promote re-validates). Returns the
    ``sig.release-classification/1`` record; ``class`` is ``class_r`` only
    when every check is proven."""
    now = now or datetime.now(UTC)
    v = _Verdicts()
    s_suites, v14 = _check_suite(v, suites or [], list(unreadable_inputs or []), publication_id)
    deltas = ((v14 or {}).get("evidence") or {}).get("deltas") or {}
    baseline_pub = str((deltas.get("baseline") or {}).get("publication_id") or "") or None

    descriptor, derr = _read_json(store, f"staged/releases/{publication_id}/descriptor.json")
    _check_environment(v, descriptor, derr)
    _check_cut(v, store, publication_id)
    prev_desc: dict[str, Any] | None = None
    if baseline_pub:
        prev_desc, _ = _read_json(store, f"staged/releases/{baseline_pub}/descriptor.json")
    if v14 is not None:
        _check_deltas(v, deltas, ((v14 or {}).get("evidence") or {}).get("failures"))
        _check_source_withdrawals(v, store, deltas)
        _check_licences(v, deltas)
        _check_versions(v, deltas, descriptor, prev_desc)
        _check_surfaces(v, store, publication_id, baseline_pub)
        _check_fields(v, store, publication_id, baseline_pub)
    else:
        for cid in (
            "deltas",
            "sources",
            "licences",
            "versions",
            "part-viii-screen",
            "allowlist",
            "public-surface",
            "fields",
        ):
            # every delta-fed check is unevaluable without the V14 row
            if not any(r["check"] == cid and r["verdict"] == "unevaluable" for r in v.rows):
                v.blocked(cid, "no V14 row — the delta evidence is absent")
    _check_signed_code(v, store, descriptor)

    cls = "class_r" if not v.triggers and not v.unevaluable else "class_s"
    record: dict[str, Any] = {
        "schema": CLASSIFICATION_SCHEMA,
        "publication_id": publication_id,
        "label": (descriptor or {}).get("label"),
        "classified_at": _iso(now),
        "class": cls,
        "failclosed": cls == "class_s" and bool(v.unevaluable),
        "triggers": list(v.triggers),
        "unevaluable": list(v.unevaluable),
        "checks": v.rows,
        "evidence": {
            "suites": [
                {
                    "mode": s.get("mode"),
                    "origin": s.get("origin"),
                    "verdict": s.get("verdict"),
                    "counts": s.get("counts"),
                    "waivers": s.get("waivers"),
                }
                for s in s_suites
            ],
            "v14_deltas": deltas or None,
            "v14_failures": ((v14 or {}).get("evidence") or {}).get("failures"),
            "baseline_publication_id": baseline_pub,
        },
    }
    if go:
        record["standing_go"] = evaluate_standing_go(
            store,
            go,
            publication_id,
            now=now,
            classified_at=now,
            candidate_commit=str(((descriptor or {}).get("code") or {}).get("commit") or "")
            or None,
        )
    return record


# --------------------------------------------------------------------------- #
# The standing go — validated, never implied                                 #
# --------------------------------------------------------------------------- #


def evaluate_standing_go(
    store: rp.Store,
    name: str,
    publication_id: str,
    *,
    now: datetime | None = None,
    classified_at: datetime | None = None,
    candidate_commit: str | None = None,
) -> dict[str, Any]:
    """Validate ``registry/approvals/<name>`` as a Class-R standing go.

    Status vocabulary: ``valid`` · ``absent`` · ``unreadable`` ·
    ``bad-schema`` · ``wrong-kind`` · ``revoked`` · ``voided`` · ``expired``
    · ``expired-in-flight-honoured`` · ``out-of-scope``. Only ``valid`` and
    ``expired-in-flight-honoured`` authorise. ``classified_at`` is the
    release's classification instant — a go that expired *after* the
    classify is honoured once for that in-flight release (the §7.3 rule);
    a go already expired *at* the classify is refused.
    """
    now = now or datetime.now(UTC)
    from . import release_conf as rc

    out: dict[str, Any] = {"name": name, "status": "absent", "detail": ""}
    obj = f"{rc.APPROVALS_PREFIX}{name}"
    rec, err = _read_json(store, obj)
    if rec is None:
        out["status"] = "absent" if "absent" in str(err) else "unreadable"
        out["detail"] = str(err)
        return out

    if rec.get("schema") != rc.APPROVAL_SCHEMA:
        out.update(
            status="bad-schema",
            detail=f"{obj} does not declare schema {rc.APPROVAL_SCHEMA!r}",
        )
        return out
    if rec.get("kind") != "standing_go":
        out.update(
            status="wrong-kind",
            detail=f"kind {rec.get('kind')!r} — a Class-R go must be kind='standing_go'",
        )
        return out
    declared = rec.get("class")
    if declared and declared != "class_r":
        out.update(
            status="out-of-scope",
            detail=f"the record is scoped to {declared!r}, not 'class_r'",
        )
        return out
    scope_pub = rec.get("publication_id")
    if scope_pub not in (None, "", publication_id):
        out.update(
            status="out-of-scope",
            detail=f"the go is scoped to {scope_pub!r}, not {publication_id}",
        )
        return out
    scope = rec.get("scope") or {}
    scope_commit = scope.get("code_commit")
    if scope_commit and candidate_commit and scope_commit != candidate_commit:
        out.update(
            status="out-of-scope",
            detail=f"the go's scope.code_commit {scope_commit[:12]}… != the "
            f"candidate's {candidate_commit[:12]}…",
        )
        return out
    if rec.get("revoked") is True:
        out.update(status="revoked", detail="the record carries revoked=true")
        return out
    void_body = store.read(f"{obj}{GO_VOID_SUFFIX}")
    if void_body is not None:
        detail = "a void record exists"
        try:
            vrec = json.loads(void_body)
            detail = (
                f"voided {vrec.get('voided_at')} on trigger "
                f"{vrec.get('triggers') or vrec.get('trigger')}"
            )
        except ValueError:
            pass
        out.update(status="voided", detail=detail)
        return out
    expires = rec.get("expires_at")
    if expires:
        exp_dt = parse_instant(str(expires))
        if exp_dt is None:
            out.update(
                status="unreadable",
                detail=f"expires_at {expires!r} is not an ISO instant",
            )
            return out
        if exp_dt <= now:
            if classified_at is not None and classified_at <= exp_dt:
                out.update(
                    status="expired-in-flight-honoured",
                    detail=(
                        f"the go expired at {expires} but the release was "
                        f"classified at {_iso(classified_at)} while it was "
                        "valid — honoured once for the in-flight release (§7.3)"
                    ),
                )
                out["honoured_in_flight"] = True
                return out
            out.update(
                status="expired",
                detail=f"the go expired at {expires}"
                + (
                    f" (before this release's classify at {_iso(classified_at)})"
                    if classified_at is not None
                    else ""
                ),
            )
            return out
    out.update(
        status="valid",
        detail=f"standing go {name} authorises this Class-R promotion"
        + (f" (expires {expires})" if expires else ""),
    )
    out["record_sha256"] = sha256_hex(canonical_json(rec))
    out["expires_at"] = expires
    return out


def record_go_void(
    store: rp.Store,
    name: str,
    publication_id: str,
    triggers: list[str],
    *,
    now: datetime | None = None,
) -> str | None:
    """Append ``registry/approvals/<name>.voided`` when a voiding trigger
    lands (B-9: ratchet regression · Part VIII screen change · new source).
    Returns the object name, or ``None`` when no go record exists to void or
    no void trigger fired. Never edits the go itself (append-only)."""
    from . import release_conf as rc

    voiding = sorted(set(triggers) & VOID_TRIGGERS)
    obj = f"{rc.APPROVALS_PREFIX}{name}"
    if not voiding or store.read(obj) is None or store.read(f"{obj}{GO_VOID_SUFFIX}") is not None:
        return None
    now = now or datetime.now(UTC)
    doc = {
        "schema": GO_VOID_SCHEMA,
        "go": name,
        "voided_at": _iso(now),
        "publication_id": publication_id,
        "triggers": voiding,
        "detail": (
            "the standing go is void on a ratchet regression, a Part VIII "
            "screen change or a new source (B-9); the classifier observed "
            f"{voiding} — a new adopted go record is required for any later "
            "Class R"
        ),
    }
    store.insert(f"{obj}{GO_VOID_SUFFIX}", canonical_json(doc), content_type="application/json")
    return f"{obj}{GO_VOID_SUFFIX}"


# --------------------------------------------------------------------------- #
# The Class-S readout (§7.4) — agent-drafted, never signed                  #
# --------------------------------------------------------------------------- #


def _pct_str(p: Any, c: Any) -> str:
    if isinstance(p, int) and isinstance(c, int) and p:
        return f"{(c - p) / p * 100.0:+.1f}%"
    return "n/a"


def draft_readout(record: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Build the §7.4 readout pair from a classification record —
    ``(json_doc, markdown)``. The draft is labelled agent-drafted and its
    signature slot is empty by construction."""
    pub = str(record.get("publication_id") or "")
    evidence = record.get("evidence") or {}
    deltas = evidence.get("v14_deltas") or {}
    suites = evidence.get("suites") or []
    fp = (deltas.get("template_fingerprint") or {}).get("current")
    trig = list(record.get("triggers") or [])
    unev = list(record.get("unevaluable") or [])

    doc: dict[str, Any] = {
        "schema": READOUT_SCHEMA,
        "publication_id": pub,
        "label": record.get("label"),
        "class": record.get("class"),
        "classified_at": record.get("classified_at"),
        "agent_drafted": True,
        "template_fingerprint": fp,
        "triggers": trig,
        "unevaluable": unev,
        "diff_summary": deltas,
        "verify_summary": suites,
        "required_wording": [WORDING_MAINTAINER, WORDING_NO_HUMAN, WORDING_MEM9],
        "basis_options": [BASIS_REVIEWED, BASIS_CHECKS_ONLY],
        "basis": None,
        "signature": None,
        "signed_at": None,
        "authority": "HG-11 / SIG-REL-012 (D-G3-3, B-9 adopted standing-go form)",
    }

    rec = deltas.get("records") or {}
    total = rec.get("total") or {}
    comp_lines = []
    for comp, dd in sorted((rec.get("per_compartment") or {}).items()):
        comp_lines.append(
            f"| {comp} | {dd.get('previous')} | {dd.get('current')} | {dd.get('pct')}% |"
        )
    srcs = deltas.get("sources") or {}
    lic = deltas.get("licences") or {}
    routes = deltas.get("routes") or {}
    rows_md = []
    for row in record.get("checks") or []:
        rows_md.append(
            f"| {row.get('check')} | {row.get('verdict')} | "
            f"{str(row.get('detail'))[:160].replace('|', '/')} |"
        )
    suite_md = []
    for s in suites:
        c = s.get("counts") or {}
        suite_md.append(
            f"| {s.get('mode')} | {s.get('origin')} | {s.get('verdict')} | "
            f"{c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('skip', 0)} | "
            f"{s.get('waivers') or []} |"
        )
    total_delta = _pct_str(total.get("previous"), total.get("current"))
    fp_state = (
        "changed" if (deltas.get("template_fingerprint") or {}).get("changed") else "unchanged"
    )
    md = f"""# Release readout — {record.get("label") or "<label>"} (`{pub[:18]}…`)

> **agent-drafted** — generated by `sig-ops release classify` at
> {record.get("classified_at")} (P35.60 / REL-06). The decision is the
> operator's; the signature slot below is empty by construction.

{WORDING_MEM9}

## Identity

| field | value |
|---|---|
| publication id | `{pub}` |
| label | `{record.get("label")}` |
| class | **{record.get("class")}** |
| template fingerprint | `{fp}` |
| baseline | `{(evidence.get("baseline_publication_id") or "none")}` |

## Classifier result

- **class:** `{record.get("class")}` (fail-closed — Class R only when every
  §7.3 condition is proven)
- **§7.2/§7.3 triggers found:** {trig or "none"}
- **unevaluable checks:** {unev or "none"}

## V14 diff summary (consumed, never re-derived)

| measure | previous | current | delta |
|---|---|---|---|
| total records | {total.get("previous")} | {total.get("current")} | {total_delta} |
{chr(10).join(comp_lines) or "| (no compartments) | | | |"}

- sources added: {srcs.get("added") or "[]"} · removed: {srcs.get("removed") or "[]"}
- licences added: {lic.get("added") or "[]"} · removed: {lic.get("removed") or "[]"}
- routes added: {routes.get("added")} · removed: {routes.get("removed")}
- template fingerprint: {fp_state}
- V14 failures: {evidence.get("v14_failures") or "[]"}

## Verification summary

| mode | origin | verdict | pass | fail | skip | waivers |
|---|---|---|---|---|---|---|
{chr(10).join(suite_md) or "| — | — | — | | | | |"}

## Check ledger

| check | verdict | detail |
|---|---|---|
{chr(10).join(rows_md)}

## Posture — stated verbatim, always

- {WORDING_MAINTAINER}
- {WORDING_NO_HUMAN}

## Basis — the signature asserts exactly one (SIG-CONF-010 wording)

- [ ] "{BASIS_REVIEWED}"
- [ ] "{BASIS_CHECKS_ONLY}"

## Signature

signature: _empty — the operator signs; an agent never signs, and silence is never approval_
signed_at: _empty_
"""
    return doc, md


def write_readout(
    store: rp.Store, record: dict[str, Any], *, now: datetime | None = None
) -> dict[str, str]:
    """Write the readout pair under ``registry/readouts/`` (create-if-absent —
    the draft is immutable once written; a signature is the operator's own
    record). Returns ``{json: <name>, md: <name>}``."""
    doc, md = draft_readout(record)
    pub = str(record.get("publication_id") or "")
    names = {
        "json": f"{READOUTS_PREFIX}{pub}.json",
        "md": f"{READOUTS_PREFIX}{pub}.md",
    }
    for name, data in (
        (names["json"], canonical_json(doc)),
        (names["md"], md.encode("utf-8")),
    ):
        if store.read(name) is None:
            store.insert(name, data)
    return names


# --------------------------------------------------------------------------- #
# The pending-readout notice — the landed alert/mail path                    #
# --------------------------------------------------------------------------- #


def notify_classification(
    record: dict[str, Any],
    readout_names: dict[str, str] | None,
    *,
    ledger: alerts.AlertLedger | None = None,
    notifiers: list[alerts.Notifier] | None = None,
    notice_hook: Any = None,
    now: str | None = None,
) -> alerts.Alert:
    """Fire the §7.3 classification notice through the landed alert seam.

    Class S → ``release.readout-pending`` (the readout draft awaits the
    operator's signature); Class R → ``release.classified`` (the standing
    go's promised diff+check-results mail). The alert is *recorded first*
    (the append-only ledger — ``SIG_ALERT_LOG``, default
    ``.sig/ops/alerts.jsonl``) then fanned out to the environment-configured
    notifiers — the log line the sig-alerts receiver turns into the
    operator mail (ACT-02). The operator's address is never a function
    argument or a file: it lives in the channel's own configuration.
    ``notice_hook`` is the test seam (called with the Alert instead of the
    real fan-out)."""
    pub = str(record.get("publication_id") or "")
    deltas = (record.get("evidence") or {}).get("v14_deltas") or {}
    suites = (record.get("evidence") or {}).get("suites") or []
    class_s = record.get("class") == "class_s"
    alert = alerts.Alert.create(
        NOTICE_KIND_S if class_s else NOTICE_KIND_R,
        "alarm",
        (
            f"release {record.get('label') or pub[:18]} classified class_s — a "
            "candidate readout draft awaits the operator's signature"
        )
        if class_s
        else f"release {record.get('label') or pub[:18]} classified class_r — "
        "the standing-go diff+check-results mail",
        detail={
            "publication_id": pub,
            "label": record.get("label"),
            "class": record.get("class"),
            "triggers": record.get("triggers"),
            "unevaluable": record.get("unevaluable"),
            "readout": readout_names,
            "v14_diff": deltas.get("records"),
            "verify_summary": [
                {"mode": s.get("mode"), "verdict": s.get("verdict"), "counts": s.get("counts")}
                for s in suites
            ],
            "approval_ref": (record.get("standing_go") or {}).get("name"),
        },
        now=now,
    )
    if notice_hook is not None:
        notice_hook(alert)
        return alert
    alerts.fire(
        alert,
        ledger=ledger
        or alerts.AlertLedger(Path(os.environ.get("SIG_ALERT_LOG", ".sig/ops/alerts.jsonl"))),
        notifiers=notifiers if notifiers is not None else alerts.notifiers_from_env(),
    )
    return alert


__all__ = [
    "BASIS_CHECKS_ONLY",
    "BASIS_REVIEWED",
    "CLASSIFICATION_SCHEMA",
    "CLASSIFICATIONS_PREFIX",
    "COMP_BOUNDS",
    "GO_VOID_SCHEMA",
    "GO_VOID_SUFFIX",
    "NOTICE_KIND_R",
    "NOTICE_KIND_S",
    "READOUT_SCHEMA",
    "READOUTS_PREFIX",
    "SOURCE_SHARE_FLOOR",
    "TOTAL_BOUNDS",
    "VOID_TRIGGERS",
    "WORDING_MAINTAINER",
    "WORDING_MEM9",
    "WORDING_NO_HUMAN",
    "classify",
    "draft_readout",
    "evaluate_standing_go",
    "load_suite_documents",
    "notify_classification",
    "record_go_void",
    "write_readout",
]
