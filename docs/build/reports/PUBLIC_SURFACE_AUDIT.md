# Public-surface data & rights audit — as-of snapshot (P27.1, LAUNCH.1)

> **PROVISIONAL pre/mid-OSM snapshot.** These are as-of numbers, **not** a settled
> launch total. A hosted OSM land (`camreg_osm_surveillance`, ~1.37M claims via the
> P26.18 chunked-commit path) may be in flight while this ran, growing the spine
> toward ~2.43M claims. **A re-audit (re-run of `sig-exports audit`) after the OSM
> land completes is REQUIRED before any export/launch is frozen** (D-P27.1-1).

- **as_of:** `2026-09-22 post-P27.2 decisions` · **generated_at (UTC):** `2026-09-22T18:29:25Z`
- **spine:** `postgresql://sig@127.0.0.1:5433/sig`
- **note:** P27.2 post-decision re-measure; OSM land in flight — PROVISIONAL (D-P27.1-1 owes the settled re-audit)
- **schema:** `p27.2/1.0.0`

## Headline (denominator-bearing — never a bare total, §32/SIG-METRIC-008)

| metric | value |
|---|---|
| total claims | 1,109,799 (1,109,799 current) |
| total entities | 99,307 |
| sources | 212 (211 ingestion_permitted) |
| publishable | 853,361 of 1,109,799 claims (redistributable=yes) (76.89%) |
| UNDETERMINED rights | 256,438 of 1,109,799 claims (rights UNDETERMINED) (23.11%) |
| publishable (effective, post-decision) | 1,109,793 of 1,109,799 claims (effective redistributable=yes) (100.0%) |
| UNDETERMINED rights (effective, post-decision) | 0 of 1,109,799 claims (effective UNDETERMINED) (0.0%) |
| geolocated | 82,579 of 99,307 entities (83.16%) |

## Licence mix (claims by `rights_record.spdx_expression`)

| claims | spdx | redistributable | derivative |
|---:|---|---|---|
| 372,869 | LicenseRef-PublicRecord-FactualCompilation | yes | yes |
| 256,438 | UNDETERMINED | UNDETERMINED | UNDETERMINED |
| 225,753 | LicenseRef-OperatorAccepted-DBRight | yes | yes |
| 82,539 | CC0-1.0 | yes | yes |
| 55,929 | ODbL-1.0 | yes | yes |
| 46,992 | CC-BY-SA-2.0 | yes | yes |
| 44,305 | CC-BY-4.0 | yes | yes |
| 12,359 | OGL-3.0 | yes | yes |
| 11,642 | CC-BY-SA-4.0 | yes | yes |
| 640 | LicenseRef-StAlbert-ODL-1.0 | yes | yes |
| 333 | LicenseRef-Peel-ODL-1.0 | yes | yes |

Redistributability split (compartment posture at claim granularity):

| redistributable | claims |
|---|---:|
| yes | 853,361 |
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

## Effective rights — post-decision resolution (P27.2, ADR-095)

The spine is append-only: a claim's *recorded* `rights_id` is the provenance
of what was known at assertion time and is never rewritten. A recorded
`rights_decision` row resolves a source's UNDETERMINED-recorded claims to
the reviewed licence; the tables below show the **effective** posture.

Recorded `rights_decision` rows: **33**

Effective licence mix (as resolved through `rights_decision`):

| claims | spdx | redistributable | derivative |
|---:|---|---|---|
| 372,869 | LicenseRef-PublicRecord-FactualCompilation | yes | yes |
| 225,753 | LicenseRef-OperatorAccepted-DBRight | yes | yes |
| 205,677 | CC-BY-4.0 | yes | yes |
| 151,906 | CC0-1.0 | yes | yes |
| 55,969 | ODbL-1.0 | yes | yes |
| 46,992 | CC-BY-SA-2.0 | yes | yes |
| 14,465 | LicenceOuverte-2.0 | yes | yes |
| 14,055 | OGL-3.0 | yes | yes |
| 11,642 | CC-BY-SA-4.0 | yes | yes |
| 6,027 | CC-BY-3.0 | yes | yes |
| 1,288 | OGL-Canada-2.0 | yes | yes |
| 1,108 | LicenseRef-Ottawa-ODL-2.0 | yes | yes |
| 1,069 | LicenseRef-DerivedFacts-Citations | yes | yes |
| 640 | LicenseRef-StAlbert-ODL-1.0 | yes | yes |
| 333 | LicenseRef-Peel-ODL-1.0 | yes | yes |
| 6 | LicenseRef-MuckRock-API-ToS | no | no |

Effective redistributability split:

| redistributable | claims |
|---|---:|
| yes | 1,109,793 |
| no | 6 |

Effective UNDETERMINED residue by connector:

| connector | UNDETERMINED claims |
|---|---:|

Recorded rights decisions (the review audit trail):

| source | spdx | redistributable | reviewer | decided_at |
|---|---|---|---|---|
| camreg_act_au | CC-BY-4.0 | yes | maintainer (delegated) | 2026-09-22 18:23:44.531653+00:00 |
| camreg_austin_tx | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:23:55.787550+00:00 |
| camreg_baltimore_md | CC-BY-3.0 | yes | maintainer (delegated) | 2026-09-22 18:24:05.316520+00:00 |
| camreg_batonrouge_la | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:24:49.281636+00:00 |
| camreg_nola_la | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:24:43.817297+00:00 |
| camreg_ottawa_on | LicenseRef-Ottawa-ODL-2.0 | yes | maintainer (delegated) | 2026-09-22 18:24:38.782190+00:00 |
| camreg_sheffield_gb | OGL-3.0 | yes | maintainer (delegated) | 2026-09-22 18:24:12.281442+00:00 |
| camreg_siouxfalls_sd | CC-BY-4.0 | yes | maintainer (delegated) | 2026-09-22 18:24:17.031517+00:00 |
| camreg_winnipeg_mb | OGL-Canada-2.0 | yes | maintainer (delegated) | 2026-09-22 18:24:28.816815+00:00 |
| carnegie_ai_gsi | LicenseRef-DerivedFacts-Citations | yes | counsel (HG-02) | 2026-09-22 18:26:34.282081+00:00 |
| ccops_nyc_post | LicenseRef-DerivedFacts-Citations | yes | maintainer (delegated) | 2026-09-22 18:26:41.283096+00:00 |
| ccops_seattle | LicenseRef-DerivedFacts-Citations | yes | maintainer (delegated) | 2026-09-22 18:26:48.531915+00:00 |
| civicclerk | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:23:16.565932+00:00 |
| decp_fr | LicenceOuverte-2.0 | yes | maintainer (delegated) | 2026-09-22 18:23:33.534062+00:00 |
| eff_data_driven | CC-BY-4.0 | yes | maintainer (delegated) | 2026-09-22 18:26:24.782882+00:00 |
| escribe | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:23:10.282794+00:00 |
| facial_recognition_world_map | LicenseRef-DerivedFacts-Citations | yes | counsel (HG-02) | 2026-09-22 18:25:15.088199+00:00 |
| legistar | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:22:35.282266+00:00 |
| madada | LicenseRef-DerivedFacts-Citations | yes | counsel (HG-02) | 2026-09-22 18:27:03.538552+00:00 |
| muckrock | LicenseRef-MuckRock-API-ToS | no | maintainer (delegated) | 2026-09-22 18:25:01.534583+00:00 |
| okcpd_policy | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:26:16.281803+00:00 |
| ok_statute | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:26:00.283202+00:00 |
| pathways_acoustic_drone_location | LicenseRef-DerivedFacts-Citations | yes | maintainer (delegated) | 2026-09-22 18:25:35.791394+00:00 |
| pathways_rtcc_federation | LicenseRef-DerivedFacts-Citations | yes | maintainer (delegated) | 2026-09-22 18:25:21.783864+00:00 |
| procportal_austin_tx | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:23:04.316288+00:00 |
| procportal_kcmo_mo | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:22:49.781985+00:00 |
| procportal_nyc_ny | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:22:44.281552+00:00 |
| procportal_sf_ca | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:22:59.031958+00:00 |
| raa_prefectures | ODbL-1.0 | yes | maintainer (delegated) | 2026-09-22 18:25:49.038835+00:00 |
| sam_gov | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:23:23.294562+00:00 |
| state_alpr_statute_inventory | LicenseRef-DerivedFacts-Citations | yes | maintainer (delegated) | 2026-09-22 18:25:10.281548+00:00 |
| ted_eu | CC-BY-4.0 | yes | maintainer (delegated) | 2026-09-22 18:21:49.783932+00:00 |
| usaspending | CC0-1.0 | yes | maintainer (delegated) | 2026-09-22 18:22:21.281883+00:00 |

## Claims by connector (top of the spine — context/denominators)

| connector | claims |
|---|---:|
| dot_511 | 864,066 |
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

- distinct geolocated entities: **82,579 of 99,307 entities (83.16%)**
- `value_geom` populated on **0** of 1,109,799 claims (the assembly gap P27.3 fills)
- geolocation claims by predicate:

| predicate | claims |
|---|---:|
| camera_latitude | 100,405 |
| camera_longitude | 100,405 |

Jurisdiction spread (`camera_jurisdiction`, coarse label; distinct subjects):

| jurisdiction | distinct subjects |
|---|---:|
| unresolved | 18,783 |
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

- 174,128 of 1,109,799 claims carry `observed_at` (15.69%)
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
-- (P27.2) effective-rights queries — run only when rights_decision exists
-- effective_licence_mix
WITH latest_decision AS (  SELECT DISTINCT ON (rd.source_id, rd.prior_rights_id)         rd.source_id, rd.prior_rights_id, rd.rights_id    FROM rights_decision rd   ORDER BY rd.source_id, rd.prior_rights_id, rd.decided_at DESC, rd.decision_id DESC), claim_source AS (  SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id    FROM claim_evidence ce    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id   WHERE ce.role = 'establishes'   ORDER BY ce.claim_id, ea.source_id ASC) SELECT rr.spdx_expression, rr.redistributable, rr.derivative_permitted, count(*) AS n  FROM claim c  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id  LEFT JOIN latest_decision ld         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id) GROUP BY rr.spdx_expression, rr.redistributable, rr.derivative_permitted ORDER BY n DESC, rr.spdx_expression ASC;
-- effective_redistributable_split
WITH latest_decision AS (  SELECT DISTINCT ON (rd.source_id, rd.prior_rights_id)         rd.source_id, rd.prior_rights_id, rd.rights_id    FROM rights_decision rd   ORDER BY rd.source_id, rd.prior_rights_id, rd.decided_at DESC, rd.decision_id DESC), claim_source AS (  SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id    FROM claim_evidence ce    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id   WHERE ce.role = 'establishes'   ORDER BY ce.claim_id, ea.source_id ASC) SELECT rr.redistributable, count(*) AS n  FROM claim c  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id  LEFT JOIN latest_decision ld         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id) GROUP BY rr.redistributable ORDER BY n DESC, rr.redistributable ASC;
-- effective_undetermined_by_connector
WITH latest_decision AS (  SELECT DISTINCT ON (rd.source_id, rd.prior_rights_id)         rd.source_id, rd.prior_rights_id, rd.rights_id    FROM rights_decision rd   ORDER BY rd.source_id, rd.prior_rights_id, rd.decided_at DESC, rd.decision_id DESC), claim_source AS (  SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id    FROM claim_evidence ce    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id   WHERE ce.role = 'establishes'   ORDER BY ce.claim_id, ea.source_id ASC) SELECT ir.connector_name, count(*) AS n  FROM claim c  JOIN ingest_run ir ON c.ingest_run_id = ir.run_id  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id  LEFT JOIN latest_decision ld         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id) WHERE rr.redistributable = 'UNDETERMINED' GROUP BY ir.connector_name ORDER BY n DESC, ir.connector_name ASC;
-- rights_decisions
SELECT rd.source_id, rr.spdx_expression, rr.redistributable, rd.reviewer,       rd.decided_at, rd.prior_rights_id, rd.rights_id  FROM rights_decision rd JOIN rights_record rr ON rd.rights_id = rr.rights_id ORDER BY rd.source_id ASC, rd.decided_at ASC, rd.decision_id ASC;
```

## Caveats (observation-level, pre-resolution)

- Counts are **raw claims, pre-resolution** — cross-source duplicate cameras
  (`dot_511` vs `osm` vs `atlas` vs `flock_portal`) are **not** deduped; the
  geolocated-entity count is **observation-level**, not a resolved device inventory.
- Rights → source attribution via `rights_id` alone fans out (many sources share one
  record); UNDETERMINED is attributed via `ingest_run.connector_name` (per-run).
- The **effective** rights view resolves each claim through the latest
  `rights_decision` matching `(source, recorded rights_id)`; a decision can
  only lift an UNDETERMINED-recorded claim, never relicense a resolved one.
  One deterministic source is attributed per claim (`claim_evidence`
  'establishes' → `evidence_artifact.source_id`, smallest source_id wins).
- Coordinates are reported **only in aggregate** (a distinct-subject count + coarse
  jurisdiction spread); no per-person, per-plate, or raw-coordinate field is emitted.
- **PROVISIONAL** per the OSM land in flight — re-run this verb after it completes.
