<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Pseudonymous reviewer provisioning — P32.9 (SIG-EVAL-002, ADR-128)

Operator instructions for bringing a real human reviewer onto a campaign.
This is an **operator runbook** — it provisions nobody by itself, and there
is no open signup. Recruitment/selection is a human decision outside this
packet's authority.

## 1. Roles on the evaluation surface

| PostgreSQL role | Who holds it | What it can do |
|---|---|---|
| `sig_eval_admin` | campaign tooling/operator | prepare campaigns, manifests, samples, packets, assignments; read released views. **Cannot** write labels or adjudications. |
| `sig_eval_reviewer` | one login **per human reviewer** | read only their own assignments/packets/labels (RLS via `sig.eval_reviewer`); append labels + attestations **as themselves**. |
| `sig_eval_custodian` | campaign custodian | read all evaluation rows; record adjudications and the one-time release. **Cannot** mint labels (no grant on `human_eval_label` insert path as custodian; label writes are pinned to the reviewer role + GUC). |
| `sig_materialize`, `sig_read_*`, `sig_export`, `sig_ingest` | existing spine roles | **zero** access to `human_eval_*`. Sealed labels never reach clustering or export. |

Separation rule: prefer reviewers who did **not** author the candidate rule
or the operational decision for an item. One person may hold administrative
roles if separation is documented, but one person's repeated labels are not
independent humans.

## 2. Provision a reviewer

Choose a **pseudonymous handle** — `rev-a`, `rev-b`, … — never a legal name,
email, or employee id. Personal contact/employment data does not belong in
the graph.

```sql
-- as the database superuser (migration already created the group role):
CREATE ROLE rev_a LOGIN PASSWORD '<issued-secret>' IN ROLE sig_eval_reviewer;
CREATE ROLE rev_b LOGIN PASSWORD '<issued-secret>' IN ROLE sig_eval_reviewer;
```

Secrets are environment/handoff material only — never committed (HG-09).

Each reviewer's session must set the **reviewer token** before any read or
label write:

```sql
SET sig.eval_reviewer = 'rev-a';
```

The CLI does this for them:

```bash
sig-resolution eval export      --dsn ... --campaign-id <id> --reviewer rev-a
sig-resolution eval import-labels --dsn ... --campaign-id <id> \
    --reviewer rev-a --workbook filled.jsonl --role sig_eval_reviewer
```

RLS enforces that `rev-a` sees only rows where `reviewer_id = 'rev-a'` —
their own assignments, packet rows for assigned samples, and their own
labels. Two reviewers cannot see each other's first-pass labels or any model
prediction (there is no prediction column in reviewer-visible rows at all).

## 3. Human attestation (required before first label)

A label row references `human_eval_attestation`; the database **refuses** a
label whose attestation row does not exist for that reviewer+campaign.
Record it once per reviewer per campaign:

```bash
sig-resolution eval attest --dsn ... --campaign-id <id> \
    --reviewer rev-a --attestation-kind human_identity \
    --statement "I am a human reviewer; I produce my own judgments under eval-rubric/1"
```

Attestation kinds: `human_identity` (required), plus optional
`qualification`, `training_completed`, `conflict_of_interest` rows — each
append-only, each timestamped.

**An agent or LLM cannot attest on a human's behalf.** The attestation is a
claim made under the reviewer's own login; automation asserting it would be
a provenance falsification and is out of policy for this repository.

## 4. Assignments

```bash
sig-resolution eval assign --dsn ... --campaign-id <id> \
    --reviewer rev-a --pass 1 --samples all
sig-resolution eval assign --dsn ... --campaign-id <id> \
    --reviewer rev-b --pass 1 --samples all
```

Assignments are append-only rows recording `reviewer × sample × pass`.
Pass 2 rows exist only for adjudication-stage re-looks the protocol defines;
first-pass work is pass 1.

## 5. Deprovisioning

When a reviewer leaves a campaign:

1. `REVOKE rev_a FROM sig_eval_reviewer;` (and rotate the login or `DROP ROLE`).
2. Do **not** delete any row — labels, attestations and assignments stay as
   history. If the reviewer withdraws work, record a `withdrawn_reviewer`
   state on the marker and adjudicate the affected samples; the rows remain.

## 6. What provisioning never does

- Never grants `sig_eval_custodian` or `sig_eval_admin` the ability to write
  labels — the label insert path is pinned to `sig_eval_reviewer` +
  `sig.eval_reviewer` equality.
- Never exposes `sealed_final` labels to `sig_materialize` or any
  development-scope view — there is no grant path.
- Never records real names, emails, or contact data in any `human_eval_*`
  column — `reviewer_id` is the pseudonym, `attestation` holds statements
  not identifiers.
