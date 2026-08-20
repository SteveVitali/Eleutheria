## 18. The analytics boundary

The outline (OL-Q22) asks how high-volume audit aggregates stay separate from the knowledge
graph. The answer has a hard privacy component, not only a performance one.

### 18.1 The bright line

**SIG-STORE-025 (MUST NOT).** Raw per-search or per-plate audit rows MUST NOT be stored in the
canonical store **or** in the published analytics store. *(REQ-R6-34; discharges non-goals N1 and
N2, OL-13.1-02, OL-A.8.)*

**SIG-STORE-026 (MUST).** The claim schema MUST contain **no column capable of holding a licence
plate**. This is not merely a policy; it is a schema property, and a schema test asserts it. A
predicate whose registered datatype could carry plate-like values MUST be rejected at vocabulary
review.

### 18.2 The substrate

**SIG-STORE-027 (MUST).** High-volume aggregates MUST live outside PostgreSQL as
**Hive-partitioned Parquet queried by DuckDB**. No columnar Postgres extension may be adopted as
canonical. *(REQ-R6-31; R6-F43, R6-F44, R6-F11.)* ClickHouse (Apache-2.0) remains the documented
escape hatch if interactive aggregate latency ever demands it. *(R6-F45.)*

### 18.3 The join

**SIG-STORE-028 (MUST).** Aggregate partitions MUST join to the graph **only** via `sig_entity_id`
UUIDs and period — **never via names** — and MUST carry `ingest_run_id` and
`agg_ruleset_version`. *(REQ-R6-32.)*

Joining on names would reintroduce, at the analytics layer, exactly the entity-resolution failure
that P6 exists to prevent — and it would do so invisibly, in a layer where nobody is looking.

**SIG-STORE-029 (MUST).** Aggregate partitions MUST be registered as **evidence artifacts** with
digests. A claim is created only when SIG asserts a *summary statement* about a partition — e.g.
"agency X performed 412 searches in the 30 days to 2026-07-15" — and that claim cites the
partition as its evidence. *(REQ-R6-33.)* This keeps the chain of §10.1 unbroken across the
boundary.

### 18.4 Disclosure control

**SIG-STORE-030 (MUST).** Published aggregate cells with counts **1–4** MUST be suppressed —
published as null with `suppressed_flag` and `k_threshold`, **never as zero** — complementary
suppression MUST be applied so that a single suppression is not invertible from published totals,
and the finest published time granularity MUST be one month. *(REQ-R6-35.)*

**SIG-STORE-031 (MUST).** Suppression MUST record **which rationale applied**. Institutional
small counts MUST NOT be suppressed merely because they are small. *(REQ-R6-36.)*

| Rationale | Applies when | Action |
|---|---|---|
| `protects_individual` | A small cell could identify a private person or their movements | Suppress |
| `institutional_conduct` | The cell describes an organization's conduct (e.g. "this agency ran 3 immigration-reason searches") | **Publish.** Suppressing it would defeat the project's purpose |
| `contractual` | The upstream licence forbids cell-level republication | Suppress, cite the rights record |

**SIG-STORE-032 (MUST).** The distinction in that table is load-bearing and is easy to get
backwards. "Three searches" by an *agency* is accountability information about an institution and
MUST be published. "Three searches" that would isolate one *individual's* vehicle movements MUST
be suppressed. The default when the two cannot be separated is to suppress and to raise a review
task, not to publish.

**SIG-STORE-033 (RATIONALE).** Authoritative external small-cell thresholds could not be verified from a
primary US federal source during research (R6-F46). The k = 5 threshold above is therefore
adopted as SIG's own documented policy, not as a claimed standard, and the methodology page MUST
present it as such. Where a partner's licence imposes a different threshold, the stricter applies.

---
