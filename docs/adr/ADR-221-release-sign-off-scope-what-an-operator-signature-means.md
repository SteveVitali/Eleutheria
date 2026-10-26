# ADR-221 — Release sign-off scope: what an operator signature means (P35.60)

- Date: 2026-10-24
- Status: accepted
- Ticket: P35.60 (REL-06, on `r11/P35.60-release-classifier-standing-go-readout`)
- Base: `r11/P35.59-dark-cutover-to-release-layout`
- Related: SIG-REL-012 (owned here: release classes and the standing go —
  the §7.3 matrix, the fail-closed default, the standing-go conditions),
  SIG-CONF-010 (owned here: the readout's required wording and the notice
  path), SIG-REL-D12 (promotion is Class S unless every Class R condition
  is proven), D-G3-3 (B-9 = a — the operator adopted the standing-go
  form), ADR-154 (a ratchet regression is Class S), ADR-163 (the "single
  maintainer, no second reviewer" sentence), ADR-152 (no maintainer check
  this round — "no human check performed"), ADR-124 (the authority and
  disclosure idiom the readout inherits), ADR-220 (the conf-generation +
  approval-record mechanics the classifier plugs into), SIG-SEC-010 (the
  machinery verifies a signature record, never produces one), SIG-ENG-042
  (fail-closed), SIG-MEM-009 (readout authorship — no proxy signatures),
  SIG-MEM-010 (append-only records)

## Context

G3 §7.3 fixes the sign-off scope: every promotion is either **Class R** —
a routine data refresh published under the operator's recorded standing
go — or **Class S** — a candidate-specific readout the operator signs for
that release alone. Until P35.60 the pipeline had no way to compute that
boundary: `release classify` was a placeholder that always answered
Class S, the standing-go record existed only as approval-file shape
(ADR-220 D4), and there was no readout artefact for the operator to sign.

Three properties of the rule made the machinery delicate, and they are
what this ADR settles rather than re-litigates:

1. **The classifier must not measure.** The P35.58 suite already emits
   V14's diff-sanity deltas and V15's gate signal. A classifier that
   re-derived the same numbers would be a second, unaudited copy of the
   measurement — and any disagreement would silently redefine the bounds.
2. **The classifier must fail closed.** SIG-REL-D12: promotion is Class S
   *unless every Class R condition is proven*. A check whose input is
   absent, malformed or ambiguous is not a passed check — it is a Class-S
   outcome with the reason recorded.
3. **The signature belongs to the operator.** An agent drafts, classifies
   and notifies; it never signs, never adopts the standing go on the
   operator's behalf, and never treats silence as approval. The honest
   posture sentences are part of the artefact's required wording, not
   decoration.

## Decision

**D1 — The classifier consumes evidence; it never measures.**
`ops/release_classify.py::classify` reads V14's emitted `deltas` block
and V15's `gate` evidence verbatim from the `sig.release-results/1` suite
docs, plus declared release metadata (the descriptor's `versions`, the
integrity manifest's route set, the catalog entry), the journal, and the
conf-generation history (the code commit the last signed release ran).
Every §7.3 R-column condition maps to exactly one verdict row: `r`
(proven), `trigger` (a named §7.2/§7.3 S trigger fired), or `unevaluable`
(the input was absent or malformed). The class is R iff the ledger holds
only `r` rows — one trigger, one unevaluable check or one anomaly yields
Class S with the reason named. There is no "probably R" path (SIG-ENG-042).

**D2 — Class R means the same release, narrower numbers.** The R column is
the §7.3 contract verbatim: same code commit as an operator-signed
release; same declared versions (ruleset, resolver, policy, projection,
ontology, descriptor schema — read from the two descriptors); same
public-surface route set (normalized so a publication-id path prefix is
not a route change); same compartments, licences, attribution texts,
disclosures and evaluation status; the same or fewer sources where a
removal is backed by a recorded withdrawal entry; V14's numeric bounds
(total −2 %…+15 %, no compartment < −5 % or > +50 %, no source losing
> 20 % of its records — the constants live beside the code, cited to the
spec); V1–V14 green with zero waivers; `environment=production`; and the
cut outside freezes on a scheduled or drift trigger. A `policy_version`
delta is named `part-viii-screen-change` explicitly — the §7.3 Part-VIII
trigger row, not a generic version bump.

**D3 — The standing go exists only as the operator's adopted record.**
A `sig.promotion-approval/1` record with `kind: standing_go` is valid
only when it is present, adopted by the operator (the record asserts the
adoption; the machinery never implies it), unexpired (the earlier of its
`expires_at` and the next sub-round gate), unrevoked, unvoided, and in
scope for this candidate's code commit. An expired go is honoured once
for a release *classified* while it was still valid — the in-flight rule
verbatim — then the next Class R needs a signed readout. A bare
"continue" renews nothing; renewal is a recorded operator act at a
sub-round gate. Voiding is append-only: `registry/approvals/<name>.voided`
(`sig.standing-go-void/1`) is written beside the go, never an edit of it,
and the classifier appends it itself when a voiding trigger lands
(`ratchet-regression`, `new-source`, `part-viii-screen-change` — the B-9
text verbatim).

**D4 — The readout is an agent draft with an empty signature slot.**
`draft_readout` fills the §7.4 fields — publication id, label, class,
template fingerprint, the diff summary, the verify summary, the authority
reference — into a labelled `agent-drafted` pair (markdown + a
`sig.release-readout/1` JSON twin under `registry/readouts/`). The
`signature` field is emitted empty; signing is the operator's act and may
only change the status line and append the signature block — the drafted
decision text is the gate record's verbatim, so a signed readout cannot
drift from what was classified. Every draft carries the required posture
sentences verbatim: "single maintainer, no second reviewer" (ADR-163),
"no human check performed" (SIG-CONF-010 — automated checks stand in for
review this round), the explicit basis options ("I have reviewed the
readout fields and the diff summary" / "I have not reviewed the files;
the signature attests to the checks only"), and the authorship sentence
(SIG-MEM-009): an operator or authorized human record supplies the
decision; an agent must not sign or assume silence is approval.

**D5 — Every classification notifies; no address lives in a file.**
`notify_classification` goes through the landed `alerts` seam (OBS.1 /
ACT-02): a Class-S result records a `release.readout-pending` notice (the
signature is awaited); a Class-R result records `release.classified` —
the diff + check-results mail the standing-go text itself promises ("each
such release is emailed to me with its diff and check results"). The
operator's destination is the channel's environment-configured target —
no address, and no secret, is written into a repository file; the seam's
existing secret scrubbing applies. Alerts are recorded before any
external delivery attempt, so a silent channel is itself visible.

**D6 — The template fingerprint makes template-drift deterministic.**
`exports/release_fingerprint.py` digests the release's template-relevant
surface (the emitted page templates and their includes, canonicalized)
and `build_release` / `site_release` stamp it into the release metadata
where V14 already reads it. A fingerprint delta across otherwise-equal
inputs is a trigger, never a judgement call — the same commit rebuilds
the same digest, so the check is a pure equality on declared metadata.

**D7 — The no-readout set is untouched.** `withdraw`, `rollback`,
`clear-latest` and the automatic post-promote rollback still need no
readout — each keeps requiring the operator go / pre-authorisation id it
ran under (§7.3 verbatim). This row adds no way around `go-required`;
the tests assert the refusal still fires before any other rollback leg.

## Consequences

- `release classify` now writes an append-only
  `sig.release-classification/1` record per applied run and journals a
  `classified` event; `release promote` reads the journal's class (never
  a CLI flag's say-so) and `check_approval` validates the standing-go
  shape against it.
- A promotion can no longer reach R by accident: every absent input —
  missing suite doc, missing descriptor side, missing withdrawal
  registry, malformed record — lands in `unevaluable`, which is itself a
  Class-S verdict with the gap named.
- The operator's signature now has a defined scope ("what it means"):
  it attests to this candidate's readout fields and the checks they cite,
  under the single-maintainer posture the wording states — nothing more
  is claimed, and no agent artefact claims it for them.
- The standing go's void conditions are now enforced rather than
  recited: the three voiding triggers write the `.voided` record at
  classify time, so a go cannot quietly survive the events that kill it.
- Deferred to the operator (recorded in DEFERRALS): adopting the
  standing-go text, and signing the first Class-S readout — both are
  recorded acts the machinery waits on, never implies.

## Revisit trigger

Revisit if the §7.3 matrix itself changes (a new trigger row, a bound
revision, or the D-G3-3 scope amended — the classifier's constants track
the spec, they do not redefine it); if the standing go is extended to
cover anything the B-9 text excludes (a new adoption is a new record,
never an edited one); if a signature-verification leg lands (the
readout's signature slot stays presence-checked until then); if the
notice channel's transport changes (the seam is `alerts`, the destination
is configuration — a new channel lands behind the same `notify_classification`
call, not inside it); or if P37.45's notice-surface extension absorbs the
readout delivery path.
