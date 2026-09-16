# Ruleset calibration over the real spine — 2026-09-16 (D-META.1-1 / BL-045)

**Run:** P25.9 (`docs/tickets/P25.9__post-live-deferral-closures-meta.md`).
**Corpus:** the hosted Cloud SQL spine (`sig-pg`), read via the documented
proxy — **19,702 claims · 6,573 subjects · 19 claims-bearing sources · 79
distinct predicates · 14 ingest runs** as of 2026-09-16. All numbers below are
computed over that corpus; nothing is asserted beyond it (§3.1).

The calibration question (BL-045, RISK-P1-03/P1-04/P4-08): do the shipped
ruleset constants — the predicate-registry volatility/half-life rows
(`ontology/vocab/predicates.yaml` → `predicate_registry.json`), the (genre ×
predicate) directness matrix, the `ruleset.toml` numeric tolerances, and the
resolver's Atlas-supersession posture — hold on real data, or does real data
argue for retuning?

## Corpus caveat (load-bearing)

The corpus is essentially **single-epoch**. `valid_period` is the unbounded
`(,)` range on all 19,702 rows (the sink stamps no validity window) and only
**2,102 claims (10.7%)** carry `observed_at` (range 2020-01-28 → 2026-09-16).
Half-lives are a *change-over-time* constant; one observation epoch cannot
falsify them. Where the corpus can speak — churn, cross-source disagreement,
genre coverage — it does, below.

## 1. Volatility / half-lives (RISK-P1-04)

**Registry coverage of the real corpus is the headline finding.** 79 distinct
predicates appear in the spine; **12 are registered** in
`predicate_registry.json` and carry 5,652 claims (28.7%); the other **67
predicates / 14,050 claims (71.3%) are unregistered** — unresolvable by
construction (SIG-RECON-013: a predicate with no registry row is never
guessed at).

Observed churn on the registered surface:

| predicate | class / half-life | subjects | claims | subjects with >1 distinct value |
|---|---|---|---|---|
| `deployment_exists` | SLOW / 3y | 4,957 | 5,574 | **0** |
| `federal_award_id` | IMMUTABLE / ∞ | 65 | 67 | 2 |
| `claimed_device_count` | FAST / 6mo | 1 | 2 | 1 |
| others (7 predicates) | IMMUTABLE/GLACIAL/SLOW/MODERATE/FAST | 1 each | 1 each | 0 |

- `deployment_exists` — the largest registered surface — shows **zero value
  churn across 4,957 subjects**: consistent with SLOW/3y, and far from
  contradicting it.
- `claimed_device_count` shows the corpus's one genuine cross-source
  disagreement: the OKC Flock deployment is claimed `190` by `bacy`
  (observed 2026-08-18) and `299` by `deflock` (observed 2026-08-20). Relative
  spread 0.365 — **above** the FAST numeric tolerance (0.15), so under the
  defaults these claims stand off rather than silently picking the newer one.
  The tolerance constant is doing its job on real data.
- `federal_award_id` (IMMUTABLE, `single`) shows 2 subjects with 2 distinct
  values. Inspection shows the cause is **subject keying, not predicate
  volatility**: the USAspending connector keys one `funding_instrument`
  subject to a roll-up that aggregates multiple sub-award ids
  (`…Y400MN6225136…` + `…YS30MN6225136…` under one subject). The finding is a
  keying/cardinality question for that connector's subject shape — recorded
  here, not silently resolved.
- The unregistered-but-multi-valued predicates are almost all legitimately
  multi-valued roll-ups (`surveillance_zone` 461 subjects, `products`,
  `seller`, `amount`, `ai_surveillance_supplier` 49 — a country↔supplier
  matrix where many values per subject is the shape, not churn).

**Finding: the documented volatility classes and half-lives hold on every
measurement the corpus can make.** No retune is justified — and none could be:
a single observation epoch cannot estimate a change rate. The half-lives stay
build-time defaults by evidence, not by omission.

## 2. Directness matrix (RISK-P1-03)

The matrix is (genre × predicate) → D1–D6 over the nine published
`artifact_genres`. Measured coverage on real claims:

- **19,686 of 19,702 claims (99.92%) carry the default `connector_run`
  evidence genre**, which has no row in the registry's genre vocabulary — the
  resolver would drop every one of them at the `no directness row` filter
  (`reconcile/resolve.py` phase 1). The connectors do not stamp
  `evidence_genre`; the default floods the corpus.
- Of the 16 genre-stamped claims, **8 resolve** to a matrix grade —
  `(executed_contract × contract_signed_date)` → D1; `(executed_contract ×
  contract_value/procurement_state)`, `(news_article × claimed_device_count)`,
  `(agency_policy × deployment_exists/authorization_state/
  implements_technology/statutory_citation)` → D2/D3 — all plausible: a signed
  contract is the most direct evidence of its own signing date.
- **8 fail**: three stamped genres absent from the registry vocabulary
  (`community_map`, `contract`, `official_statement`) and four unregistered
  predicates (`enacting_body`, `instrument_type`, `sunset_date`,
  `acquisition_method`).

**Finding: the matrix's published grades are unrefuted on the pairs that reach
it, but the corpus exercises almost none of it.** The actionable gap is
coverage — `evidence_genre` stamping in the connectors and registry rows for
the genres/predicates real claims actually carry — not the grades. These are
recorded as backlog recommendations below, not tuned in place: a directness
edit without disagreement evidence would be tuning past the data.

## 3. Atlas supersession (RISK-P4-08)

- `eff_atlas_of_surveillance` carries **5,373 claims over 4,756 subjects**.
- **Zero (subject, predicate) pairs are shared with any other source** — Atlas
  rows have no resolved peer to supersede or be superseded by. Only 76
  subjects in the whole spine are claimed by >1 source (74 are the
  carnegie/frwm country pair, plus the OKC-deployment cluster and one FR
  pair), and none are Atlas subjects.
- Within-source: Atlas was loaded once; 404 (subject, predicate, value)
  triples are asserted more than once — same-value re-assertions (duplicate
  upstream rows), **not** value-changing supersessions (the resolver's
  same-source supersede rule fires only on a changed value).
- The `resolution`/`contradiction`/`coverage_record` tables are empty: the
  resolver has never run over the hosted spine, so no entity-merge context
  exists in which an Atlas row could be superseded.

**Finding: ADR-028's deferral is confirmed correct on real data** —
supersession is a pure resolver decision over existing claims, and the corpus
cannot yet exercise it (no cross-source entity resolution has run). The
measured answer to "does Atlas get superseded" is "the precondition — a
resolved entity graph — does not yet exist"; that is now an honest,
data-backed statement rather than an assumption.

## Recommendation

**The documented defaults hold; no ruleset constant is retuned.** The
calibration outcome is this written finding — the alternative the ticket
permits ("tuned constants with justification") is not supported by a
single-epoch corpus, and tuning unmeasured constants would violate the
defining standard.

Recorded follow-on gaps (real-data findings, engineering-actionable, not
gate-blocked):

1. **Predicate-registry coverage** — 67 of 79 observed predicates are
   unregistered (unresolvable by SIG-RECON-013). Registering them is a
   versioned data addition to `predicates.yaml` (volatility + half-life +
   strategy + a full directness row each) — a backlog item, not this run.
2. **`evidence_genre` stamping** — 99.92% of claims carry `connector_run`,
   outside the matrix's genre vocabulary; the resolver cannot grade them.
   A connector-side stamping pass (data on the claim row) is owed before a
   resolver run means anything.
3. **Subject-key granularity** — `federal_award_id` single-cardinality
   violations trace to the USAspending roll-up subject key (one subject, many
   sub-awards). Key per-award or record the predicate as multi-cardinality.
4. **Resolver run over the hosted spine** — Atlas supersession (and the whole
   resolution surface) stays unexercised until ER/resolution run on the real
   corpus. P25.10 (contradiction serve-path) is the natural carrier.
5. **`observed_at` coverage** — 10.7% of claims carry an observation time;
   currency (C1–C4) is uncomputable for the rest. Re-fetch cadence (the
   monthly MuckRock schedule, future re-runs) will create the temporal depth
   half-lives actually need.

*Method:* all figures from `psycopg` reads over `127.0.0.1:5433` (Cloud SQL
proxy → `sig-pg`), 2026-09-16; joins `claim → extraction → evidence_capture →
evidence_artifact` for source/genre attribution. Append-only: no spine row was
written, updated, or deleted for this analysis.
