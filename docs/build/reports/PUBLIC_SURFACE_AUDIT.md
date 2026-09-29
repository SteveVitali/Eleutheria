# Public-surface data & rights audit — as-of snapshot (P27.1, LAUNCH.1)

> **PROVISIONAL pre/mid-OSM snapshot.** These are as-of numbers, **not** a settled
> launch total. A hosted OSM land (`camreg_osm_surveillance`, ~1.37M claims via the
> P26.18 chunked-commit path) may be in flight while this ran, growing the spine toward
> ~2.43M claims. **A re-audit (re-run of `sig-exports audit`) after the OSM land completes
> is REQUIRED before any export/launch is frozen** (deferral D-P27.1-1).

- **as_of:** `2026-09-22T16:57:19Z` · **generated_at (UTC):** `2026-09-22T16:57:20Z`
- **spine:** `postgresql://sig@127.0.0.1:5433/sig`
- **note:** OSM land (camreg_osm_surveillance ~1.37M claims) in flight — PROVISIONAL pre/mid-OSM snapshot; re-audit required after the land completes (D-P27.1-1)
- **schema:** `p27.1/1.0.0`

## Headline (denominator-bearing — never a bare total, §32/SIG-METRIC-008)

| metric | value |
|---|---|
| total claims | 1,059,533 (1,059,533 current) |
| total entities | 92,206 |
| sources | 210 (210 ingestion_permitted) |
| publishable | 803,361 of 1,059,533 claims (redistributable=yes) (75.82%) |
| UNDETERMINED rights | 256,438 of 1,059,533 claims (rights UNDETERMINED) (24.2%) |
| geolocated | 75,479 of 92,206 entities (81.86%) |

## Licence mix (claims by `rights_record.spdx_expression`)

| claims | spdx | redistributable | derivative |
|---:|---|---|---|
| 372,869 | LicenseRef-PublicRecord-FactualCompilation | yes | yes |
| 256,438 | UNDETERMINED | UNDETERMINED | UNDETERMINED |
| 225,753 | LicenseRef-OperatorAccepted-DBRight | yes | yes |
| 82,539 | CC0-1.0 | yes | yes |
| 46,992 | CC-BY-SA-2.0 | yes | yes |
| 44,305 | CC-BY-4.0 | yes | yes |
| 12,359 | OGL-3.0 | yes | yes |
| 11,642 | CC-BY-SA-4.0 | yes | yes |
| 5,929 | ODbL-1.0 | yes | yes |
| 640 | LicenseRef-StAlbert-ODL-1.0 | yes | yes |
| 333 | LicenseRef-Peel-ODL-1.0 | yes | yes |

Redistributability split (compartment posture at claim granularity):

| redistributable | claims |
|---|---:|
| yes | 803,361 |
| UNDETERMINED | 256,438 |

## UNDETERMINED rights by connector (`ingest_run.connector_name`) — the P27.2 worklist

| connector | UNDETERMINED claims |
|---|---:|
| procurement | 205,184 |
| dot_511 | 34,650 |
| france_belgium_procurement | 14,462 |
| data_driven | 1,015 |
| coarse_international | 851 |
| state_statute_seed | 108 |
| government_mandated_disclosure | 81 |
| france_belgium_records | 65 |
| okcpd_policy | 6 |
| records | 6 |
| france-seed | 4 |
| ok_statute | 3 |
| pathways | 3 |

## Claims by connector (top of the spine — context/denominators)

| connector | claims |
|---|---:|
| dot_511 | 814,066 |
| procurement | 205,184 |
| france_belgium_procurement | 14,462 |
| flock_portal | 11,192 |
| atlas | 5,373 |
| osm | 4,505 |
| accountability | 2,863 |
| data_driven | 1,015 |
| coarse_international | 851 |
| state_statute_seed | 108 |
| government_mandated_disclosure | 81 |
| france_belgium_records | 65 |
| france-seed | 11 |
| okcpd_policy | 6 |
| records | 6 |
| okc-seed | 5 |
| ok_statute | 3 |
| pathways | 3 |

## Geolocation (aggregate only — Part VIII §0.7 / §19.4 / §43.3)

- distinct geolocated entities: **75,479 of 92,206 entities (81.86%)**
- `value_geom` populated on **0** of 1,059,533 claims (the assembly gap P27.3 fills)
- geolocation claims by predicate:

| predicate | claims |
|---|---:|
| camera_latitude | 93,305 |
| camera_longitude | 93,305 |

Jurisdiction spread (`camera_jurisdiction`, coarse label; distinct subjects):

| jurisdiction | distinct subjects |
|---|---:|
| unresolved | 11,682 |
| FL | 9,965 |
| GA | 7,049 |
| CA | 6,139 |
| TX | 3,996 |
| IL | 3,446 |
| WA | 2,754 |
| MD | 2,753 |
| TH | 2,110 |
| DC | 1,713 |
| GB-ENG | 1,710 |
| AU-QLD | 1,479 |
| OR | 1,418 |
| AU-ACT | 1,328 |
| PA | 1,249 |
| SA | 1,128 |
| MO | 1,107 |
| LA | 1,067 |
| NZ | 1,060 |
| IA | 1,002 |
| CA-ON | 996 |
| MN | 995 |
| MA | 845 |
| CA-BC | 829 |
| CA-MB | 795 |
| US | 629 |
| GB-SCT | 595 |
| KY | 587 |
| NY | 585 |
| AL | 556 |
| AZ | 526 |
| ID | 500 |
| BD | 447 |
| MY | 386 |
| VA | 383 |
| CA-AB | 354 |
| HI | 252 |
| SD | 234 |
| TN | 190 |
| IE-DL | 123 |
| KS | 97 |
| AU-VIC | 67 |
| JP | 57 |
| NL | 54 |
| CO-MET | 50 |
| NC | 44 |
| UT | 32 |
| DE | 24 |
| HK | 22 |
| BE | 19 |
| GB-NIR | 18 |
| CO | 14 |
| GB | 12 |
| PS | 6 |
| PT | 1 |

## Freshness (§32.4)

- 174,128 of 1,059,533 claims carry `observed_at` (16.43%)
- observed span: `2020-01-28 00:00:00+00:00` … `2026-09-22 00:00:00+00:00`

## Modeling-table population (the shaping gap P27.3 fills)

| table | rows | state |
|---|---:|---|
| `resolution` | 0 | EMPTY |
| `jurisdiction` | 0 | EMPTY |
| `coverage_record` | 0 | EMPTY |
| `relationship` | 0 | EMPTY |
| `organization_relation` | 0 | EMPTY |
| `physical_asset` | 0 | EMPTY |
| `deployment` | 0 | EMPTY |
| `contradiction` | 0 | EMPTY |
| `legal_instrument` | 0 | EMPTY |
| `policy` | 0 | EMPTY |
| `claim.value_geom` | 0 | EMPTY |

## Exact queries

All read-only SELECTs, run inside a `READ ONLY` transaction (no INSERT/UPDATE/DELETE):

```sql
-- claim_current_total
SELECT count(*) FROM claim WHERE upper_inf(sys_period);
-- claim_total
SELECT count(*) FROM claim;
-- claims_by_connector
SELECT ir.connector_name, count(*) AS n FROM claim c JOIN ingest_run ir ON c.ingest_run_id = ir.run_id GROUP BY ir.connector_name ORDER BY n DESC, ir.connector_name ASC;
-- entity_by_type
SELECT entity_type, count(*) AS n FROM entity GROUP BY entity_type ORDER BY n DESC, entity_type ASC;
-- entity_total
SELECT count(*) FROM entity;
-- geo_claims
SELECT predicate_id, count(*) AS n FROM claim WHERE predicate_id IN ('camera_latitude','camera_longitude') GROUP BY predicate_id ORDER BY predicate_id ASC;
-- geolocated_entities
SELECT count(DISTINCT subject_id) FROM claim WHERE predicate_id IN ('camera_latitude','camera_longitude');
-- jurisdiction_spread
SELECT value_text AS jurisdiction, count(DISTINCT subject_id) AS n FROM claim WHERE predicate_id = 'camera_jurisdiction' AND value_text IS NOT NULL GROUP BY value_text ORDER BY n DESC, value_text ASC;
-- licence_mix
SELECT r.spdx_expression, r.redistributable, r.derivative_permitted, count(*) AS n FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id GROUP BY r.spdx_expression, r.redistributable, r.derivative_permitted ORDER BY n DESC, r.spdx_expression ASC;
-- observed_at_coverage
SELECT count(*) FILTER (WHERE observed_at IS NOT NULL) AS observed, min(observed_at) AS earliest, max(observed_at) AS latest FROM claim;
-- redistributable_split
SELECT r.redistributable, count(*) AS n FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id GROUP BY r.redistributable ORDER BY n DESC, r.redistributable ASC;
-- sensitivity_by_tier
SELECT sensitivity_tier, count(*) AS n FROM claim GROUP BY sensitivity_tier ORDER BY sensitivity_tier ASC;
-- source_permitted
SELECT count(*) FROM source_registry WHERE ingestion_permitted;
-- source_total
SELECT count(*) FROM source_registry;
-- undetermined_by_connector
SELECT ir.connector_name, count(*) AS n FROM claim c JOIN rights_record r ON c.rights_id = r.rights_id JOIN ingest_run ir ON c.ingest_run_id = ir.run_id WHERE r.redistributable = 'UNDETERMINED' GROUP BY ir.connector_name ORDER BY n DESC, ir.connector_name ASC;
-- value_geom_populated
SELECT count(*) FROM claim WHERE value_geom IS NOT NULL;
```

## Caveats (observation-level, pre-resolution)

- Counts are **raw claims, pre-resolution** — cross-source duplicate cameras
  (`dot_511` vs `osm` vs `atlas` vs `flock_portal`) are **not** deduped; the geolocated-
  entity count is **observation-level**, not a resolved device inventory.
- Rights → source attribution via `rights_id` alone fans out (many sources share one
  record); UNDETERMINED is attributed via `ingest_run.connector_name`, which is per-run.
- Coordinates are reported **only in aggregate** (a distinct-subject count + coarse
  jurisdiction spread); no per-person, per-plate, or raw-coordinate field is emitted.
- **PROVISIONAL** per the OSM land in flight — re-run this verb after it completes.

<!-- ────────────────────────────────────────────────────────────────────────
     Everything ABOVE this line is the deterministic output of `sig-exports audit`
     (the durable, re-runnable deliverable). Regenerate the snapshot with:

       cloud-sql-proxy --port 5433 zeta-medley-508121-u7:us-central1:sig-pg &
       export PGPASSWORD="$(gcloud secrets versions access latest \
         --secret=sig-pg-password --project=zeta-medley-508121-u7)"
       uv run python -m exports audit \
         --dsn "postgresql://sig@127.0.0.1:5433/sig?sslmode=disable" \
         --as-of "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
         --note "OSM land complete — re-audit" \
         --markdown-out docs/build/reports/PUBLIC_SURFACE_AUDIT.md \
         --json-out docs/build/reports/public_surface_audit.json

     Everything BELOW is the human-authored launch-scope memo (P27.1 deliverable 4).
     ──────────────────────────────────────────────────────────────────────── -->

## Launch-scope memo (P27.1 deliverable 4)

> **Provisional pending the OSM-complete re-audit (D-P27.1-1).** The operator has consciously chosen to
> run P27.1 now against the current spine while `camreg_osm_surveillance` (~1.37M OSM claims) lands
> concurrently (D-SOURCES.17-1). The numbers above are a pre/mid-OSM **snapshot**, not a settled launch
> total; the ordered scope below is a *shape* decision that holds regardless, but the counts MUST be
> refreshed (re-run the verb) before the export/launch is frozen.

### What a national public surface can honestly show *now*

1. **A national + international camera/site inventory (observation-level).** ~75.5k distinct entities
   carry `camera_latitude`/`camera_longitude` (81.9% of ~92k entities). National in spread
   (`camera_jurisdiction`: FL/GA/IL/CA/WA/TX/… + GB-ENG/AU-QLD/NZ/TH) with a large **`(null)`/unresolved**
   bucket that must be surfaced honestly, never hidden. **Caveat:** these are raw observations, **not**
   deduped devices — cross-source duplicates (`dot_511`/`osm`/`atlas`/`flock_portal`) are not resolved,
   so the surface must frame this as "observations/sites seen", with named denominators, not "N cameras".
2. **A procurement / accountability watch.** The large `procurement`, `congress`/legislation,
   accountability and disclosure connectors give a real national watch surface.
3. **Data-freshness + coverage honesty.** Only **16.4%** of claims carry `observed_at`; the surface must
   state freshness per-source and label the rest "observation time not recorded", never imply currency it
   cannot support (§32.4). Coverage is **negative-claim-empty** (`coverage_record` = 0) — the surface can
   only say "researched vs not-yet-researched", not "known-absent", until P27.3 populates coverage.

### Publishable now vs publishable after P27.2 (rights)

| bucket | claims (snapshot) | posture |
|---|---:|---|
| **Publishable now** (redistributable=`yes`) | **803,361 (75.8%)** | already carry a redistributable licence; ODbL / CC-BY-SA rows stay in their **own compartments** (never merged) |
| **Blocked pending P27.2** (`UNDETERMINED`) | **256,438 (24.2%)** | overwhelmingly government/public-record: `procurement` ~205k + `dot_511` 34,650 + `france_belgium_procurement` 14,462 + tails |

→ The launch blocker is a **bounded rights-review pass over ~3 connectors** (P27.2 / HG-03), not a
190-source slog. `facial_recognition_world_map` + `pathways_*` are held for **explicit operator sign-off**
(Part VIII), never blanket-flipped. The fail-closed export gate (SIG-LIC-004) keeps UNDETERMINED rows OUT
of any published bundle until their rights resolve — the honest posture is a recorded gap, not a bypass.

### Recommended resolution posture

**Ship observation-level for launch; treat cross-source resolution as an explicit, later, additive layer**
(recommend for P27.3/P27.4, tracked by ADR-092). Rationale:

- The modeling tables (`resolution`/`jurisdiction`/`coverage_record`/`relationship`/`physical_asset`/
  `deployment`/`contradiction` + `claim.value_geom`) are **all empty** — ER has never run on the hosted
  spine. Resolution is real work with real epistemic risk (wrongly merging two distinct cameras is a
  false claim, §3.1); doing it under launch pressure invites exactly the errors the project forbids.
- Observation-level is **honest and shippable today**: "N observations across M sources, not yet
  deduplicated" with named denominators (§32) is a defensible national surface. Resolution can then be
  layered in additively (new resolution rows / a materialized site view via the normalization path, never
  a hand-edit) without re-architecting the surface.
- The export build is the right one-time place to assemble geometry/grouping/coverage for a static site
  (P27.3), keeping the spine append-only and the web zero-JS.

### Ordered publishable-scope list (what P27.3→P27.8 should build against)

1. Per-jurisdiction dossier index + national landing (publishable-now sources only; UNDETERMINED excluded).
2. National map layer from `camera_latitude`/`_longitude` (observation-level, ODbL compartment separate),
   coordinate reduction per §19.4/§43.3, aggregate only.
3. Data-freshness + coverage pages with named denominators and honest "not-yet-researched" gaps.
4. Procurement/accountability watch + evidence/corrections/research-queue surfaces.
5. **P27.2 rights pass** widens the publishable set from 75.8% toward ~100% for the government/public-record
   buckets; **re-run this audit** after both the OSM land (D-SOURCES.17-1) and the rights pass to freeze the
   real launch numbers.

### Intended build-memory rows (recorded per ticket §5)

- `BUILD_INDEX.md` row **117** (P27.1) — added on landing (this PR, per implement-spec Phase 6.5).
- `LEDGER.md` — `lastCompleted: P27.1`, `nextTicket: P27.2`, `chainTip: devin/p27-1-public-surface-audit`.
- `DEFERRALS.md` — **D-P27.1-1** (V, OPEN): the OSM-complete re-audit obligation (re-run this verb after
  `camreg_osm_surveillance` lands, then freeze the launch numbers).
