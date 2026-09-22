# Stage-0 outreach letter — template (SIG-CONTRIB-012 / 012a / 013, spec §35.1)

> The published template SIG uses for the **first contact** with every
> federation-compact project (spec §6, §35.1). Stage-0 outreach MUST be attempted
> and its outcome recorded **before** any connector is written for the project
> (SIG-CONTRIB-012, SIG-CHART-033). The recorded outcome — including `no_response`
> — determines the permitted ingestion posture (SIG-INGEST-027).
>
> **Fill the `<...>` fields per project.** Address the letter to an
> **organisational** channel (a project inbox / issue tracker / contact form) — never
> a private individual by name (Part VIII §0.7). Keep the record in
> `docs/build/STAGE0_OUTREACH_RECORD.md` (a new dated row per real outreach event;
> append-only, P1–P3 — never rewrite an earlier row).

---

## Subject

`Reconciliation layer for the ALPR-transparency ecosystem — an offer to <project>`

## Body

Hello <project> team,

**What SIG is.** SIG (Surveillance Infrastructure Graph) is an evidence-first,
append-only, open graph of public surveillance infrastructure, assembled from public
records and the work of independent researchers. It is **connective infrastructure for
a movement**, not another surveillance map (SIG-CHART-034/035).

**What we want.** To *reference and reconcile* your published work — linking to it,
preserving your identifiers and epistemic labels, and sending corrections upstream —
so your project's value is amplified, not copied.

**What we will NOT do** (the compact's binding constraints, spec §6):

- We will **not compete with or duplicate** your project, and will **not re-host your
  differentiator** (e.g. plate-level search, your live crawler, your UX).
- We will **not fork** your project (DeFlock: SIG-CHART-015.1).
- We treat lead-generation sources as **leads only**, never auto-confirmed (§43.5).
- We honour robots/ToS and conservative crawler conduct (§26); where your terms do not
  permit a use, we do not make it.

**What we offer** (it gives before it asks — the cheapest demonstration of the compact):

- **Corrections upstream, free**, with no attribution required and no reciprocal data
  access requested — e.g. running our graph-scale plausibility / implausible-submission
  checks and feeding the results back (SIG-CONTRIB-012a: where you have *publicly asked
  for help* with a problem we already solve, that is our opening offer, ahead of any
  data ask).
- **Traffic and citation** back to your project as the primary source.
- **Targeted research tasks** and methodology co-authorship.
- **Archival succession (SIG-CONTRIB-013):** SIG will hold a mirror that **survives your
  project's disappearance, on terms you set.** Several ecosystem projects are
  single-maintainer efforts and some relevant domains are excluded from the general web
  archive — if a project vanishes, the record can vanish with it. This is insurance,
  offered at almost no cost to you and no obligation.

**What we ask of you.** Only that you tell us which of the above you welcome, and under
what terms — including "no thanks." 

**Explicit opt-out.** If you would prefer we not reference your work at all, reply and we
will record that and comply. Silence will be recorded as `no_response` and we will use
only your public terms, nothing more.

Thank you for the work you do.

— The SIG project (organisational contact: <sig public contact channel>)

---

## Outcome to record (closed `compact_status` vocabulary, SIG-INGEST-027)

`not_contacted` · `contacted_awaiting_response` · `no_response` · `permission_granted` ·
`permission_granted_conditional` · `permission_declined` · `public_terms_only` ·
`partnership_active`

Record the outcome (project, date, outcome, governed source ids) as a new row in
`docs/build/STAGE0_OUTREACH_RECORD.md` and, where it changes a source's posture, on the
`sources.toml` row (with `last_verified`). A flip to `ingestion_permitted = true` also
requires the rights-review metadata (`rights_reviewed_by`, `rights_reviewed_on`) — see
`docs/adr/ADR-063-*.md`.
