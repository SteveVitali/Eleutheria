# ADR-201 — The ingest identity's prefix-scoped capture-rewrite grant (P34.42b)

- Date: 2026-10-08
- Status: accepted
- Ticket: P34.42b (Round 11 / P34, row 252 — G1-01 / F-272, SIG-SEC-007; the
  conditioned grant discharges the overwrite half of SIG-STORE-048's writer
  posture, whose deletion leg stays owned by P37.3)
- Base: `r11/P34.42a-least-privilege-service-identities`
- Related: ADR-023 (the OCFL write-once evidence store whose re-versioning
  creates this need), SIG-STORE-048 (no writer holds object-delete), D-P34.42b-1
  (the standing review row), P37.3 (the owning review row)

## Context

P34.42b moves all 88 Cloud Run jobs onto job-class identities that carry only
their grants, and removes `roles/editor` from the default compute service
account (G1-01). The ingest class writes evidence captures to the restricted
bucket. Inspection of the evidence store during this row found a wrinkle the
naive "create + read, never write twice" model misses:

`OcflStore.add_version` (`evidence/src/evidence/ocfl.py`) is append-only at
the *content and prior-version* level — content-addressed payload bytes and
every `v{n}` directory are never touched again — but each re-capture
**rewrites the object's inventory head in place**: `inventory.json` and its
sidecar at the object root, plus the new version's inventory copy. GCS
implements "rewrite an existing object" as overwrite, which requires the
permission behind object-replace (`storage.objects.create` **and**
`storage.objects.delete` on that object name — `roles/storage.objectUser`).

So `objectCreator` + `objectViewer` is NOT sufficient for the ingest class: a
re-capture of an already-captured source (the resume/re-ingest paths exercise
this routinely) would fail its inventory-head write. Granting unconditional
`objectUser` would hand every ingest job bucket-wide delete — exactly the
G1-01 defect this row exists to close (SIG-STORE-048: writers never hold
delete).

## Decision

1. **The ingest class holds exactly one conditioned grant.** The committed
   declaration (`ops/iam_identities.toml`, `sig.iam-identities/1`) gives
   `sig-ingest-rt` unconditional `objectCreator` + `objectViewer` on the
   restricted bucket, plus `roles/storage.objectUser` under the IAM condition
   `p34-42b-capture-rewrite` —
   `resource.name.startsWith('projects/_/buckets/<project>-sig-restricted/objects/evidence/captures/')`.
   Object replace (and therefore delete) exists only under
   `evidence/captures/` — the prefix the OCFL store owns. Everywhere else the
   identity cannot delete. The declaration's loader refuses a condition on
   any other role (`CONDITIONABLE_ROLES = {roles/storage.objectUser}`), and
   `sig-ops iam diff` judges the recorded binding's expression byte-for-byte.

2. **The proof is read-only, twice.** The jobs leg's `analysis` action runs
   `policy-intelligence troubleshoot-iam-policy` for every runtime SA: bucket-
   scope `storage.objects.delete` and an off-prefix object path must answer
   NOT_GRANTED; the diff asserts the binding's condition title + expression.
   No deletion is ever attempted as a probe.

3. **The grant is recorded debt, not invisible machinery.** D-P34.42b-1 is the
   standing review row (owner P37.3, the SIG-STORE-048 disposition row): the
   conditioned grant stays until the evidence layer's write path changes (a
   store layout that needs no overwrite — e.g. inventory heads under a
   per-run prefix, or object-delete scoped narrower than prefix — reviewed
   there), at which point the condition is removed and the grant retires.

4. **Fail-closed, never silent.** A re-count disagreement (live job count ≠
   88, an unmapped live job), an unparseable executions list, or a missing
   prestate capture is a refusal — exit 42 inside the window rules, exit 4 on
   a contradictory read — never a partial mutate-and-hope.

## Alternatives considered

- **Unconditioned `objectUser` on the restricted bucket** — restores
  bucket-wide delete to every ingest job: the exact G1-01 blast radius this
  row removes. Rejected.
- **Object-delete only via a separate "rewriter" job identity** — the
  inventory-head write happens inside the same `put` as the content writes;
  splitting it would split one OCFL transaction across identities and leave
  a partial object on any failure. Rejected.
- **A custom role with `storage.objects.delete` conditioned the same way** —
  equivalent reach, more machinery; `objectUser` conditioned is the managed
  shape and reads identically in the troubleshooter. Rejected.
- **No condition, documented as "write-only in practice"** — the permission
  boundary would be honour-system: a compromised ingest job could delete any
  object in the bucket. Rejected.

## Consequences

- `ops/iam_identities.toml` gains `condition_title`/`condition_prefix` on the
  ingest `objectUser` binding; the loader validates the pair and refuses a
  condition on any role outside `CONDITIONABLE_ROLES`.
- `sig-ops iam plan --leg jobs` renders the binding with its
  `--condition-*` flags; `diff` asserts the recorded expression.
- `ops/gcp/iam-job-identities.sh` applies the conditioned binding and proves
  the off-prefix deny in its read-only `analysis` leg.
- D-P34.42b-1 (DEFERRALS) records the standing review obligation owned by
  P37.3; SIG-STORE-048's writer leg keeps its MET-ENGINEERED-scoped verdict —
  the prefix grant is the recorded reason the plain "no delete" wording needs
  the qualifier.

## Revisit trigger

- The OCFL store's write path changes so re-capture no longer overwrites an
  inventory head in place (a layout revision lands) — the conditioned grant
  retires with it (D-P34.42b-1, owner P37.3).
- GCS IAM conditions gain a narrower-than-prefix object verb scope — the
  review row re-judges whether `objectUser` is still the tightest managed
  role.
- A second workload class needs a conditioned storage grant — the
  `CONDITIONABLE_ROLES` allow-list is deliberately a set of one; widening it
  is a reviewable declaration change, not a silent edit.

### Trigger evaluation — P34.43 (2026-10-08): FIRED (trigger 3) — answered

P34.43's execution host is the second workload class: its
`sig-quality-probe-rt` `exec` leg needs `objectViewer` on
`objects/evidence/captures/` and `objectCreator` on `objects/ops/probes/`,
both prefix-conditioned on the restricted bucket, so `CONDITIONABLE_ROLES`
widens from a set of one to the three managed roles the conditioned-grant
shape needs. The widening is the reviewable declaration change the trigger
names — made deliberately in `ops/src/ops/iam_identities.py` with the
same validate-then-render path — and the recorded answer is ADR-202: the
roles chosen for the new bindings carry **no** object-delete or replace
permission, so the blast-radius posture this ADR established is preserved.
The decision stands; the set-of-one was scaffolding, not the invariant.
