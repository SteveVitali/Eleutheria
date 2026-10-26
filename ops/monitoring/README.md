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
- `apply` — `update`/`create`: the roll scripts (`alerts.sh` for P34.4's named
  set; `alerting.sh` for P35.2's full reconciliation) may write this def
  (`gcloud monitoring policies update <id> --policy-from-file` /
  `… create --policy-from-file`; uptime defs render `gcloud monitoring uptime`
  flags via `sig-ops monitoring-defs render-uptime`). `diff-only`: never
  written — the operator e-mail channel stays P34.4's mechanism (its creation
  is never this roll's; P35.2 binds policies to it).
- `source` — where the definition came from (a dated live export or the
  authoring ticket).

## P35.2 additions (SIG-OPS-006/007)

- **`alertStrategy.notificationRateLimit {period: "86400s"}` on every policy**
  — the >24 h-red condition re-notifies once daily (the hygiene row of G1
  §3.5's design table; D-P34.4-3's general-escalation leg). The executable
  rule the drill and roll cite lives in `ops/src/ops/alerting.py`
  (`renotify_due`).
- **Uptime checks carry `selectedRegions` (3 regions) and the site check a
  `contentMatchers` row** (`Surveillance Infrastructure Graph` on `/`) — the
  G1 §3.5 "synthetic" row: 5-minute cadence from 3 regions on the canonical
  public origin (LB-fronted `surveillancegraph.org`) and the API `/health`.
- **`sig-alerts` posture (G1 §3.3)** — the service is kept only as a
  repo-owned, IAM-authenticated, digest-pinned record: its runtime identity
  (`sig-alerts-rt`) and invoker bindings are declared in
  `ops/iam_identities.toml` (P34.42a); `alerting.sh --verify` asserts the
  deployed image is a `@sha256:` digest — a `:latest` or tag reference is
  DRIFT (SIG-SEC-008, F-12). The e-mail channel + Monitoring policies are the
  delivery path; the service is the webhook receiver record.
- **`alerting.sh` is the roll** — prestate → bundle → policies → uptime →
  retention → versioning → proberoll → verify; every mutating leg is
  windowed (never 03:00–06:30Z, never an AR-3 batch window), idempotent and
  reversible from its captured pre-state.

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
