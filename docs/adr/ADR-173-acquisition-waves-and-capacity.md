# ADR-173: Acquisition waves and capacity — one ING-GO per wave, US-first with non-US kept, a 40 GB cap

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 173)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: A-19 at 2026-10-01T04:25:48Z (log round 8); S5-4 at
  04:28:49Z (round 9); B-11 at 04:35:53Z (round 12); B-18 at 04:39:45Z (round 13); C-8 at 04:59:05Z (round 21)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P). This ADR records the decision.
- **Relation to landed ADRs:** none named by §7. ADR-021 (registry gate), ADR-107 (Cloud SQL steady-state tier), ADR-111
  (pinned job images), ADR-130 (acquisition reviewed queue) and ADR-140 (acquisition pilot funnel) are unchanged.
- **Related:** `PD/design/I8-acquisition-design.md` §7 (hosted ingestion plan) and §11 (`PD` =
  `docs/build/planning/2026-09-30-next-phase/`); ADR-168 (collection conduct), ADR-169 (rights; the operator's flip
  lists), ADR-172 (direction), ADR-174 (scheduler of record; provisional, written by P35.1a); `PD/NEXT_PHASE_PLAN.md`
  §4.2 A-19, §4.3 S5-4, §4.4 B-11/B-18, §5.5, §8.3, §8.4, §8.8, §10.4, §15 LATER-08/LATER-09;
  `PD/data/decision_catalog.csv` rows Q-23, I8-Q2…Q5, S5-4, CF-06, D-SOURCES.7-2, D-SOURCES.8-2, OD-15, OD-21; plan rows
  P35.6–P35.11, P36.1a, P36.12, P37.1, P37.2, P37.47–P37.54, P37.66, P37.69a/b, P37.70; operator actions OP-10, OP-13,
  OP-26.

## Context

Stream I's acquisition design (I8) turned 694 consolidated candidates into a hosted ingestion plan: a widening group (46
configuration units under already-flipped sources), Tier 1 (108 candidates in eight connector families), the OSM national
ALPR layer moved to its origin, and a conditional Tier-2 wave. I8 §7 sets the jobs and schedulers, first-run safety rules,
a calendar, the Cloud SQL capacity and cost projection, rematerialization, monitoring, verification and rollback, and §11
asks the operator five questions (Q-23 capacity, OSM cadence, ING-GO granularity, targets under flipped sources, Wave D).

I8 measured the spine at 6.42 GB used (2026-09-30) on a 15 GB SSD with **no autoresize limit**, memory at its daily max
on every day 09-16…09-24, CPU peaks during materialize and export, ≈ 2.51 M claims, and derived ≈ 2.55 KB of disk per
claim (inference). CF-06 (S4c) proposed **US-first**: drop the international portals and OGC WFS family (ACQ-23a/b) and
keep Wave C to the US and territories.

Contact strings: EDGAR's declared-contact user agent and the US 511 / QLDTraffic / NSW key sign-ups need a contact
string; P16 forbids sending the operator's personal identifiers.

## Decision

1. **Waves, each opened by one verbatim ING-GO** (B-11, *"As stated (Recommended)"*, 2026-10-01T04:35:53Z; I8-Q3 a).
   Each acquisition wave activates only on the operator's verbatim go for that wave **and** the operator's executed flip
   list for its sources (ADR-169; OP-26); an unanswered ING-GO queues the wave's legs and activates nothing. Dates below
   are the plan's earliest windows (UTC, plan §8.4), not records; they slip under A-19.
   - **Wave A** — widening (Legistar keyword pass, USAspending/CROL vocabulary, the 2026 statute seed refreshed from
     origins): activation P35.11, ING-GO-A at GATE-G4, legs 10-19 → 10-23.
   - **Wave B** — Tier 1 (eight families) plus the Flock transparency-portal probe (P36.74, probe-only under WV-10):
     activation P36.12, ING-GO-B with the Wave-B flip list at GATE-G4, one family a day 10-26 → 11-05; Wave-B data
     publishes in P36.72b's Class S release.
   - **Wave C** — OpenStreetMap becomes the **origin** of the national ALPR layer (P37.1 code, P37.2 activation):
     ING-GO-C at GATE-G5, legs 11-16 → 11-20.
   - **Wave D — in scope** (I8-Q5 a): the Tier-2 rows P37.47–P37.53, the international portals and OGC WFS family
     P37.69a/b (ACQ-23a/b; N1–N21), and the first activation of Axon Connect, DocumentCloud and Sourcewell/OMNIA
     (P36.76–P36.78): activation P37.54, ING-GO-D with the Wave-D flip list at GATE-G6, windows 11-23 → 12-04 and
     12-14 → 12-18.
   - Targets added under an already-flipped source are **configuration**, not a new HG-03 line (I8-Q4 yes); the Part VIII
     screen still applies.
   - OpenStreetMap runs **monthly** (I8-Q2 a).
2. **US-first ordering, non-US kept** (S5-4, *"Keep non-US acquisition"*, 2026-10-01T04:28:49Z). The operator chose
   this **against the recommendation**: they declined *"Confirm US-first (Recommended)"* (CF-06: ACQ-23a/b leave the
   round; Wave C limited to the US and territories). So ACQ-23a/b stay in the round as P37.69a/b, and Wave C's national
   run keeps its non-US objects (I8's ≈ 1.11 M-claim Wave-C figure is again the planning figure). **US-first remains the
   priority order** — Flock/Axon US-nationwide first (U-007).
3. **Capacity** (B-11; Q-23 a). Cloud SQL storage autoresize gets a **binding cap of 40 GB**; the disk is **pre-grown to
   25 GB** before Wave C (a one-way change); the tier is bumped **temporarily** for the Wave-C national run and camera-site
   rematerialization only (I8: `db-custom-1-3840` → `db-custom-2-7680`, ≈ 48 h, reverted after a 24 h soak), each tier
   change with its own verbatim go when the leg is due, inside the wave's window. I8 §7.4 adds disk-utilisation alerts
   at 70 % and 85 % of the cap. **No permanent scale-up** in the round: it waits for LATER-08's trigger (sustained
   CPU/latency, or disk past ADR-022's threshold); I8 §7.4 proposes the concrete conditions (memory at its maximum on
   ≥ 3 of 7 days with API `/health` p95 above its SLO, `sig-materialize` beyond 2 h, or a monthly batch missing its
   window) as ADR-107/ADR-111's revisit trigger.
4. **Keyed APIs after the alias** (B-18, *"US + AU keys, fold rest (Recommended)"*, 2026-10-01T04:39:45Z; the
   recommendation was updated mid-session after S5-4; C-8 *"Alias first (Recommended)"*, 2026-10-01T04:59:05Z). The
   operator registers the free US 511 keys (D-SOURCES.7-2 a) and the QLDTraffic + NSW Live Traffic keys
   (D-SOURCES.8-2 a) in Secret Manager (HG-09; OP-13) **after** `contact@surveillancegraph.org` exists (OP-10); no
   request that needs a contact string is sent before then. Keys are never in files. P37.12 (US 511) and P37.70 (AU)
   consume them. B-18 also folds D-P32.3-1 into A-10 + P37.46; D-P30.2b-1 has no fold target after B-31 and stays OPEN,
   non-blocking (T-EVAL-IND).
5. **Calendar slips** (A-19, *"Let waves slip (Recommended)"*, 2026-10-01T04:25:48Z; OD-21 a): if first dispatch is later
   than ≈ 10-07, each wave slips to its next window (the cliff table, plan §8.8); nothing is dropped; Wave-D overflow
   ships in the 2027-01-15 cut.
6. **First-run safety and order of work** (I8 §7.2, as planned): no Round-11 acquisition first run before the 10-10 OSM
   replay's read-back, inside an AR-3 freeze window, inside the daily 03:00–06:30Z band, or on a release-cut day; new
   jobs are created **paused** on the wave's single pinned image digest; each wave runs pre-state capture → on-demand
   backup → image roll → paused create → manual runs one family a day → verification → +0 re-runs → resume →
   materialize; at most one new manual job at a time, never concurrent with `sig-materialize`. Before any Round-11
   acquisition fetch, P35.38a (owned UA contact page) and P36.1a (opt-out register + SIG-INGEST-046c refusal) have landed
   (ADR-168). Every wave's new sources ship in a **Class S** release (operator readout).
7. **Rollback** (I8 §7.8): a job or image re-points to the previous digest; a source is stopped by a new dated rights
   decision (`ingestion_permitted=false`), its claims kept (append-only) and withdrawn from the next release within the
   withdrawal barrier's 15 minutes; anomalous data is fixed forward by new claims, and corruption only through a PITR
   **clone**, never an in-place restore; the tier patches back.

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time (log) | words | label | sha256 |
|---|---|---|---|---|
| A-19 | 2026-10-01T04:25:48Z | *"Let waves slip (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:25:48Z | `db0fe245327f138bfaa4ddd8ceb79451c9a340640c855d1222a4315560a76896` |
| S5-4 | 2026-10-01T04:28:49Z | *"Keep non-US acquisition"* | option label selected by the operator (against the recommendation) | `83d45fda821cad6a0e368c0369abe5f288702ac25d44e5bc53bb46ea7a2b376b` |
| B-11 | 2026-10-01T04:35:53Z | *"As stated (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:35:53Z | `dda51782d3e72cf3c6621a079580c2bd3b6a17225db0b2406c08b5ec9fe52706` |
| B-18 | 2026-10-01T04:39:45Z | *"US + AU keys, fold rest (Recommended)"* | agent-drafted option (updated after S5-4), adopted by the operator at 2026-10-01T04:39:45Z | `fac770c7ec457ffd044f52ba8428b00dfd51df27140551e9b52dbaa72462bf70` |
| C-8 | 2026-10-01T04:59:05Z | *"Alias first (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:59:05Z | `8f8d7914fbb8f07dbecf848b69c378aff131ccc06bd5245ba813a756333a8f38` |

B-11's text as asked (log round 12): *"Cloud SQL cap 40 GB, pre-grow 25 GB, temporary tier bump for OSM; OSM monthly; 4
wave ING-GOs; targets under flipped sources = configuration; core + Wave D"*.

## Consequences

- **Capacity (inference, not measurement):** ≈ 1.5 M new acquisition claims (≈ 3.8 GB) plus organic growth gives
  11–17 GB at year end; the share-list claims and vendor-page connectors add an estimated ≈ 1.3–1.5 GB, so **≈ 12–19 GB,
  inside the 40 GB cap and the 25 GB pre-grow** (plan §5.5). A weekly read-only size measurement before Wave C narrows
  the band.
- **Cost (inference):** steady-state ≈ +$4–6/mo and ≈ $5–10 one-off for the waves (I8 §7.4), inside the ≤ $300/mo
  infrastructure ceiling; GATE-G4 re-projects if P34.5's measured baseline differs materially.
- **Operator load:** one ING-GO and one flip list per wave (≈ 0.25 h each for the flips), a tier-bump go for Wave C, and
  key registrations after the alias.
- **Calendar risk:** Wave D's ≈ 12 family-days against ≈ 13 weekdays is tight (inference); overflow slips to the
  2027-01-15 cut under A-19.
- **Non-US exposure:** keeping ACQ-23a/b and Wave C's non-US objects carries the EU/UK database-right risk on N1–N21
  (ADR-169; §14 R-20) and SIG-PUB-017's jurisdiction-conditional publication.

## Alternatives considered

- **Confirm US-first** (CF-06; recommended at S5-4) — declined by the operator.
- **Lower cap (25 GB)** or **no cap** (B-11) — declined; an unlimited autoresize means no ceiling can ever bind.
- **One go per family day** instead of per wave (I8-Q3) — declined; one verbatim go per wave.
- **Keep OSM weekly** (I8-Q2) — declined; monthly, with ≈ 4× less Overpass load.
- **Core only, dropping Wave D** (I8-Q5) — declined; Wave D is in scope.
- **US keys only** or **no keys** (B-18) — declined.
- **Protect the end date by dropping Wave D first** (OD-21 b) or **pause and re-plan** (OD-21 c) — declined.

## Revisit trigger

- **A capacity trigger** fires — LATER-08's (sustained CPU/latency, or disk past ADR-022's threshold) or I8 §7.4's
  proposed conditions (memory at its maximum on ≥ 3 of 7 days with API `/health` p95 above its SLO; `sig-materialize`
  beyond 2 h; a monthly batch missing its window) — or the disk reaches 85 % of the 40 GB cap.
- **P34.5's measured bill** differs materially from the inference (GATE-G4 re-projects), or a wave's spend would cross
  the $300/mo ceiling.
- First dispatch **later than ≈ 10-07**, or a wave misses its window (the cliff table re-projects each wave; A-19).
- An **egress block, objection or terms change** on a wave's hosts (ADR-168, ADR-169 triggers), or an OSM-origin
  rematerialization below its 95 % merge or lineage threshold (I8 §7.8: the origin layer is suppressed until fixed).
- The operator revisits the US-first ordering or the non-US scope.
