# ops/monitoring — the committed alert set (P34.4; QA-3/QA-4/QA-5, SIG-OPS-006)

One JSON file per live Cloud Monitoring resource, in **REST shape minus
volatile fields**, `{project}` templated, so the committed set can be diffed
against the live project and re-applied. This is the alerting-as-code slice
P34.4 owns; the general mechanism (reconciliation loops, escalation) is
P35.2's row (SIG-OPS-006).

## Layout

| file prefix | kind | live resource |
|---|---|---|
| `channel.*.json` | `channel` | a notification channel (`monitoring channels`) |
| `uptime-check.*.json` | `uptime` | an uptime check (`monitoring uptime`) |
| `alert-policy.*.json` | `policy` | an alert policy (`monitoring policies`) |

Every file carries a `_sig` envelope the verify engine and apply path use:

```json
{"_sig": {"kind": "policy",
          "id": "7285515107319155929",
          "displayName": "SIG — Cloud Run job execution failed",
          "apply": "update",
          "source": "track0.5-live-export-2026-10-02"}}
```

- `id` — the server-side id the def matches on (the suffix of `name`). `null`
  matches by `displayName` — used for policies this change creates (no id yet).
- `apply` — `update`/`create`: `alerts.sh --apply` may write this def
  (`gcloud monitoring policies update <id> --policy-from-file` /
  `… create --policy-from-file`). `diff-only`: never written by the script —
  the channel and uptime checks predate this row (Track 0.5); their recreation
  is P35.2 scope.
- `source` — where the definition came from (a dated live export or the
  authoring ticket).

## Invariants (tests pin them)

- **No volatile fields** — `name`, `creationRecord`, `mutationRecord(s)`,
  `verificationStatus`, condition `name`s are stripped; they are
  server-assigned and would churn the diff.
- **`{project}` is templated** — no literal project id; verify and render
  substitute it. (The project id appears in `_sig`-free bodies only.)
- **`<placeholder>` leaves never compare** — a leaf whose whole value starts
  with `<` skips the diff. That is how the operator's e-mail address stays out
  of the repo while the channel still verifies: `email_address` is
  `"<redacted …>"`. Nothing else may use a placeholder.
- **`enabled: true` on every def** — a disabled committed alert is a defect.

## Verify

```bash
# against a capture dir (channels.json, uptime-checks.json, alert-policies.json)
uv run sig-ops monitoring-defs verify --from-state <dir> --project <p>
# against the live project (list verbs only)
uv run sig-ops monitoring-defs verify --live --project <p>
```

Emits `OK/DRIFT/MISSING` per declared resource, `EXTRA` per undeclared live
resource, and `probe: monitoring-defs-verify result=ok|drift`; exit 1 on any
non-OK. `ops/gcp/alerts.sh --verify` runs the same engine and reports
`N OK, 0 DRIFT` when the committed set matches live.

## Apply

`ops/gcp/alerts.sh --apply all` is the only write path: it renders each
`apply: create|update` policy def (minus `_sig`, project resolved) and calls
`gcloud alpha monitoring policies create|update --policy-from-file`. Creates
are idempotent — an existing policy with the same `displayName` is updated in
place rather than duplicated. Rollback for an update is the captured prior
definition (re-applied the same way); for a create, `gcloud alpha monitoring
policies delete <id>`.
