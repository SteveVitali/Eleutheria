# P35.21 — partner-name disposition packet (D-P32.3-1)

**Status:** `prepared_not_executed` — the hosted read-only audit is QUEUED; nothing was measured and no count is claimed.

- **Obligation:** `D-P32.3-1` (sizes the engineering half; stays OPEN — the operator's OP-15 dispositions decide)
- **Spine:** `sig-pg (read-only sig_read_public)` · **Scheme:** `sig.org.name` · **Dry run:** `true`
- **Generated:** 2026-10-26T15:27:10Z (`date -u`)
- **Query sha256:** `dcc24c347ae3ee34599c8b5ed036199011def8b1e9ac77c839f06f78230a9396`
- **Report sha256:** `null` — no report exists yet
- **Run bounds (`date -u`):** None → None

## Queued run — the re-run measures

- **Reason:** hosted env absent at this row — no ADC, SIG_GCP_PROJECT unset, SIG_PARTNER_AUDIT_DSN unset; the leg stays armed, never executed
- **Planned at:** 2026-10-26T15:27:10Z (`date -u`)
- **Re-run (verbatim):**

```
implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true
```

- **Environment required:** `SIG_GCP_PROJECT`, `ADC (gcloud auth application-default)`, `SIG_PARTNER_AUDIT_DSN`, `cloud-sql-proxy on PATH`

N, the per-option blast radii and the per-key rows are `null`/`[]` — an absent hosted read is recorded, never fabricated.

## The provenance query (verbatim)

```sql
SELECT ei.value AS name_key,
       e.entity_id::text,
       o.cached_canonical_name AS label,
       ea.source_id,
       c.predicate_id
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
  LEFT JOIN organization o ON o.entity_id = e.entity_id
  JOIN claim c ON c.object_entity = e.entity_id AND c.object_type = 'entity_ref'
  JOIN claim_evidence ce ON ce.claim_id = c.claim_id
  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
 WHERE ei.scheme = %s
 ORDER BY ei.value, ea.source_id, c.predicate_id
```

## Part VIII

Key ids and counts only: per-key rows (`keys.csv`, `packet.json`) are `entity_id` + `name_key_sha256` + counts. No registrant name, label or free text leaves the audit report into a committed artifact — the full report JSON (which names keys) stays in the gitignored `docs/build/logs/` tree.

*This packet measures; it never decides. Every disposition of a legacy key is the operator's OP-15 decision, recorded on its own line — `D-P32.3-1` stays OPEN until those land.*
