# P35.21 — partner-name disposition packet (D-P32.3-1)

**Status:** `measured` — measured over `fixture-spine (P35.21 test fixture)`, read-only.

- **Obligation:** `D-P32.3-1` (sizes the engineering half; stays OPEN — the operator's OP-15 dispositions decide)
- **Spine:** `fixture-spine (P35.21 test fixture)` · **Scheme:** `sig.org.name` · **Dry run:** `true`
- **Generated:** 2026-10-26T15:27:10Z (`date -u`)
- **Query sha256:** `dcc24c347ae3ee34599c8b5ed036199011def8b1e9ac77c839f06f78230a9396`
- **Report sha256:** `b58d51aa4b12d9673af79b47412b8e02e677060146f1a88d7a030afcc1c49fbd`
- **Run bounds (`date -u`):** 2026-10-26T15:27:08Z → 2026-10-26T15:27:09Z

## N

**`legacy_keys` = 3** — counted, never sampled (SIG-ENG-042).

| measure | count |
|---|---|
| legacy `sig.org.name` keys (N) | 3 |
| keys splitting into >1 scoped candidate | 1 |
| `sig.org.name_scoped` candidates total | 5 |
| distinct asserting sources observed | 3 |

## OP-15 option blast radii

| option | keys | scoped candidates | basis |
|---|---|---|---|
| keep | 2 | — | single-source keys (harmless union) |
| split | 1 | 5 | multi-source keys (the auto-union exposure) |
| same_as | *not sized* | — | this query carries no strong-id joinability — no count claimed |

## Split-count histogram

| keys decomposing into N scoped candidates | key count |
|---|---|
| 1 | 2 |
| 3 | 1 |

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
