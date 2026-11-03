# Copy batch 15 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.57 (row 400, explore bar and scoped-search placement), the
     row needing new public sentences after batch-14: the K5 §5.5 "Show on the
     map" control + its records-list link on the sources explorer rows, and
     the unkeyed-dossier variant of the explore bar's search link. Agent-
     drafted, pending verbatim confirmation. Append-only: rows are never
     deleted or edited in place — a correction is a new row superseding the
     old id, and a status change is recorded in the confirmation log below
     with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, source names), not drafted copy.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| SM-01 | /dossier/&lt;path&gt;/sources/ | Show on the map | a2cb714a928755c0f80c0f3c48502b8fe52692011337afc18920110f6095fa69 | pending |
| SM-02 | /dossier/&lt;path&gt;/sources/ | records list | c18e0222e279a717602e467280232d0382064b459bb0c45a5afdfd418c1d0288 | pending |
| EB-03 | /dossier/&lt;path&gt;/ | Search the release → | 2932c0865650cd401ec4035db8ea3b7cf8c5ad71ba0a68aefde6ea41fcb97808 | pending |
| EB-04 | /dossier/&lt;path&gt;/ | Search within {name} → | e7e4dfeed0c4da82ea46d8b9d41d5fe1b999aaa16e4674065c1e4ee1b8c1172d | pending |

## Confirmation log

<!-- operator/appointer confirmations append here, one `date -u`-stamped
     line per row id, never an edit of the rows above. -->
