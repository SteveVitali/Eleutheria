# A1 — Planning baseline (frozen 2026-09-30)

Row **A1** of `META_PLAN.md` (Stage P). Read-only capture: git, GitHub, build-memory control files, GCP
(`zeta-medley-508121-u7`, `us-central1`) and the live site. Machine-readable twin: `baseline.json` (flat keys; every
manual key names its command in `_provenance`, every command id and its `date -u` time is in `_commands`). Raw
captures: `docs/build/logs/next-phase/A1/` (gitignored). Evidence class for everything below: `live-read`
unless marked. Command ids (C01…C30) are defined in `baseline.json → _commands`; times are `date -u`.

**Freeze point:** `clock.captured_at_utc = 2026-09-30T16:31:55Z` (C30, the final `a1_delta.py capture`). Values read
earlier (C02–C25) were re-derived by C30 unchanged, except where the Track-0 section notes a concurrent change.

## Clock

| event | UTC (`date -u`) |
|---|---|
| A1 start (C01) | 2026-09-30T16:22:59Z |
| first read (C02, git) | 2026-09-30T16:23:10Z |
| final capture C30 (freeze point) | 2026-09-30T16:31:55Z → 16:32:52Z |
| delta self-test (0 changed keys) | 2026-09-30T16:34:13Z |
| A1 end | 2026-09-30T16:37:01Z |

## Git

| key | value | cmd |
|---|---|---|
| `git.planning_head_sha` | `a23fca8a83996af587c09f070683edf5d6e3d296` at C30 (was `251827b0…` at C02; the orchestrator committed D1 `feedback/QUESTIONNAIRE.md` during A1, then `72b83f24` at 16:32:35Z after the freeze; skipped by the delta) | C02, C30 |
| `git.chain_tip_sha_local` / `_origin` | `b051732c3c6ed11d7ebb2343a4414f2fc281fd2a` / same (`devin/p33-8-agent-docs-refresh`, PR #190) | C02, C03 |
| `git.origin_main_sha` / `origin_main_tree` | `b7c9e2e3e925ba8220d459de037202f0f03b03f2` (merge of #140, 2026-09-29T22:46:38-04:00) / `53fa9d041b462f06249428d6a379ce5828577b45` | C03, C23 |
| `git.p31_4_branch_sha` / `_tree` | `d4522d8212fce147e74e74a308d4b9b777c56d55` / `53fa9d04…` | C03, C23 |
| `git.origin_main_tree_equals_p31_4_tree` | **true** | C02, C23 |
| `git.chain_tip_descends_from_origin_main` | **false** — merge-base `13782968` (P31.4 closeout, 2026-09-24); main carries `d4522d82` (operator lockfile regen, 2026-09-29) that the chain lacks (NEW-1) | C03 |
| `#141` base `devin/round9-waveb-seed` | `34406ffc` = P31.4 closeout + 2 seed commits; **not** on `origin/main` | C06 |
| main checkout `/Users/stevenvitali/Eleutheria` | HEAD `b051732c`, 0 dirty files | C21 |
| `claude/next-phase-planning` on origin | no (local only) | C03 |
| worktrees (`git worktree list`) | 8: main checkout (b051732c), 2 × `.codex/worktrees` (round10-integration c8d72cc3 detached; six-stream-planning 240129cd), 4 × `ci-worktrees` (p28-5, p28-6, p29-1, p29-3), this planning worktree | C02 |

## GitHub PRs & CI

| key | value | cmd |
|---|---|---|
| total / merged / open / closed | **191 / 142 / 49 / 0** | C04 |
| open range | #141–#190 minus #148 (merged 2026-09-26T03:07:03Z, `devin/deploy-gcp-live`); stack contiguous (each base = previous head) | C04 |
| lowest open | **#141** `devin/p31-5-entity-ref-claims-procurement` → base `devin/round9-waveb-seed` (not `main`) | C04 |
| highest open | #190 `devin/p33-8-agent-docs-refresh` → `devin/p33-7-repo-docs-refresh`, head `b051732c` | C06 |
| off-pattern base | #156 → `codex/round10-seed-after-p31-19` (#155's head) | C04 |
| last merges | #138/#139/#140 at 2026-09-30T02:46:15Z/26Z/38Z; #191 (P27 planning seed) merged 2026-09-29T03:15:50Z | C04 |
| open heads digest | `gh.open_heads_sha256 = 8331f062…d088` (sha256 of sorted `number headOid` lines) | C06 |
| mergeable / draft | 49 MERGEABLE / 0 draft; last open-PR update 2026-09-28T22:48:14Z | C06 |
| checks per PR | 5 (`CI`: python, docs, composed, security, web) | C05 |
| all 5 green | **33** PRs (#155–#190 except #165, #179, #185) | C05 |
| failing | **16** PRs (table below) | C05 |
| `main` CI | push CI **success** on `b7c9e2e3` (run 36661393143, 02:46:41Z); scheduled: nightly 6/6 success, observability 6/6 success, **reingest 6/6 failure** (NEW-2), keepalive 0 runs on main | C21, C22 |

| failing PRs | failing checks | first completed |
|---|---|---|
| #141–#147, #149–#154 (13) | `composed`, `web` | 09-25 … 09-27 |
| #165 | `python` | 09-27 |
| #179 | `python` | 09-28 |
| #185 | `python` | 09-28 |

## Build-memory control digests

All files byte-identical between the planning worktree and chain tip `b051732c` (C07 `git diff --quiet`).

| file | bytes | sha256 |
|---|---|---|
| `docs/build/LEDGER.md` | 679,109 | `d459173f7afd5adab36cd42b9ab7600e4c10182305f4c9974a4da6c0f20a1a30` |
| `docs/tickets/DEFERRALS.md` | 339,292 | `b688f3b49b33d5f5a7f307bbe1b3b6d719300845ac324869fecf91bd6a6cc5aa` |
| `docs/tickets/00_MANIFEST.md` | 102,012 | `e493c3d347f2448130702d5f5cbfa88a32755854780556e34957027bc6f0325e` |
| `docs/build/COVERAGE_MATRIX.csv` | 201,858 | `11b77c2ce90792c96b8c2b76a4b8a91aebab76111ed24fdbc01028c877942c55` |
| `docs/build/BACKLOG.csv` | 41,474 | `99b2dd03482f9151561ca38345491b0e6c4be95580815a83bc1995faa0192092` |
| `docs/build/BUILD_INDEX.md` | 295,436 | `7830dbc3864bf934dbc6943758a7b4a9bce39f700672cdcde9f5d1533eaad029` |
| `docs/build/reports/current/CURRENT.md` | 14,203 | `0b693e7343a13b4fd5509155fba3a8af18abdce362680a8ebfba44dd5308d8cb` |
| `docs/build/reports/obligations/events.jsonl` | 75,653 | `1439087e45a405086440329b11e2c064ea4b82eabf5f11f0beee512d9717b8d4` |
| `docs/build/OPERATIONAL_READINESS.md` | 42,743 | `581fcb5558ca77d3e70a911448469aeed918fd050bb5e1108d212a41c371e7ec` |

| LEDGER CURRENT STATE (first token only; C08 `sed -n 29,54p`) | value |
|---|---|
| `projectStatus` | `IN-PROGRESS` (not the enum spelling `IN_PROGRESS`) |
| `nextTicket` / `lastCompleted` | `HUMAN-H4` / `P33.8` |
| `chainTip` / `round` | `devin/p33-8-agent-docs-refresh` / `10` |
| `blockedOn` / `pauseRequested` / `updatedAt` | `(nothing)` / `false` / `2026-09-28` |
| CURRENT STATE block size (lines 29–54) | 122,978 bytes |

| projection & registers (C08) | value |
|---|---|
| `CURRENT.md` input_commit | `c77bd45e` |
| obligations | 97 · **36 owed (32 OPEN, 4 PARTIAL)** · 61 terminal · 97 events |
| DEFERRALS rows (`^\| D-`) | 97 |
| COVERAGE_MATRIX | 715 rows: MET 562 · MET-DIFFERENTLY 77 · PARTIAL 54 · MISSING 10 · N/A-RATIONALE 7 · AT-RISK-INTEGRATION 5 → **69 not-MET** |
| BACKLOG.csv | 58 rows: open 32 · closed 22 · accepted 4 |
| ADR files | 144 |

## Production

**Cloud Run services** (C09, C10, C14)

| service | ready revision | image | min / max inst. (template) | Ready last transition |
|---|---|---|---|---|
| `sig-web` | `sig-web-00002-5nw` (created 2026-09-27T01:32:03Z) | `sig-web@sha256:d8244804eb4fa7db5b0ebe25f0177f4270409e3a6d5f484418efcd03b086ee2b` | unset (0) / 2 | 2026-09-27T01:32:09Z |
| `sig-api` | `sig-api-00011-wic` (created 2026-09-25T14:55:58Z; 100 % traffic, tag `p318`) | `sig-api@sha256:40a47da8c2cf8f68e84aede7e7e3f9f43a03ed823c83a9924d6535970354b722` | 1 / 2 | 2026-09-25T14:56:38Z |
| `sig-alerts` | `sig-alerts-00004-7xv` | **`sig-api:latest`** (resolves to `sha256:d0ea2deb…`) | unset / 20 | 2026-09-16T17:46:52Z |

Service-level `run.googleapis.com/maxScale` = 20 on sig-web and sig-api. `sig-api` reads `SIG_PG_PASSWORD` from Secret
Manager (`secretKeyRef sig-pg-password:latest`; provided: yes, value not read).

**Cloud SQL `sig-pg`** (C11 at 16:26:04Z; C25/C30 at freeze)

| field | value |
|---|---|
| state / version / edition | RUNNABLE / POSTGRES_18 / ENTERPRISE |
| tier / availability | `db-custom-1-3840` / ZONAL (us-central1-a) |
| disk | 15 GB PD_SSD, auto-resize on (no limit) |
| automated backups | **enabled**, start 05:00 UTC, 7 retained (STANDARD tier) |
| PITR | **true at freeze** (false at C11 16:26:04Z; see Track 0) — 7-day log retention, `CLOUD_STORAGE` |
| settingsVersion | 63 (61 at C11) |
| deletion protection | **false** (NEW-3) |
| network | public IPv4 on, 0 authorized networks, `sslMode ALLOW_UNENCRYPTED_AND_ENCRYPTED`, no maintenance window |
| backups (`gcloud sql backups list`) | 2 SUCCESSFUL: `1790785111976` ON_DEMAND 16:18:31→16:20:43Z; `1790785806842` AUTOMATED 16:30:06→16:31:38Z |

**Schedulers, jobs, buckets** (C13, C15)

| key | value |
|---|---|
| Cloud Scheduler jobs | **79**, all ENABLED; 45 attempted, 34 never attempted yet; 0 `:latest` (all target Run jobs) |
| Cloud Run jobs | **88**; 8 distinct images, all digest-pinned (71 on `sig-api@sha256:6ad5477d…`); **0 `:latest`** |
| unscheduled Run jobs | 9: 4 egress probes, `sig-ingest-resume-test`, `sig-sink-bench`, `sig-replay-ingest`, `sig-export`, `sig-materialize` (NEW-4) |
| OSM monthly replay (D-P31.4-1) | `sig-sched-camreg-batch-05` `35 3 10 * *` UTC → job pinned `sig-api@sha256:feff986c…`, timeout 129,600 s |
| `:latest` anywhere | only the **`sig-alerts` service** (confirms F-12) |
| buckets | `sig-backups` (PAP enforced), `sig-public`, `sig-restricted` (enforced), `sig-web`, `_cloudbuild` |
| `sig-web` bucket `curate/` | 0 objects; `sig-public/web/curate/**` 0 objects; `index.html` updated 2026-09-27T01:33:57Z |

**Public release and live site** (C16–C19)

| key | value |
|---|---|
| public `manifest.json` `release_id` | **`sig-2026-09-27-ce480ab1`** (sha256 `717aeb44…72d6`, Last-Modified Sun, 27 Sep 2026 01:30:28 GMT, generation 1790472628538699, 132 artifacts) |
| manifest reproducibility | as_of_snapshot/belief 2026-09-27 · ruleset_version `p27.3/1.0.0` · resolver_version `0.0.0` |
| `https://surveillancegraph.org/` | **200**, Last-Modified Sun, 27 Sep 2026 01:33:43 GMT, ETag `"6ab87277-14f54"`, 85,844 bytes, 0 `<script>`, sha256 `a007e380…02ab` |
| home "As of" line | "As of world 2026-09-27, belief 2026-09-27; ruleset p27.3/1.0.0" — no release id in the HTML |
| `/curate/` | **404** on `surveillancegraph.org` and `sig-web-e5ctyx36jq-uc.a.run.app` |
| API `GET /health` (`sig-api-e5ctyx36jq-uc.a.run.app`) | **200** `{"status":"ok","backend":"postgresql", pool 1–5}` |
| front door | global LB `sig-web-fr-http`/`-https` 136.81.80.102; 0 Cloud Run domain mappings; API has no custom domain |

## Track-0 state confirmation

| item | TRACK0_RECORD says | A1 observed | verdict |
|---|---|---|---|
| 0.1 automated backups | enabled 16:21:05Z, 05:00 UTC, 7 retained | enabled, 05:00, 7 retained (C11, C30) | **confirmed** |
| 0.1 on-demand backup | `1790785111976` SUCCESSFUL | listed SUCCESSFUL (C12) | **confirmed** |
| 0.1 PITR | at A1 start: "held for the operator"; amended in `72b83f24` (16:32:35Z): operator delegated, agent enabled PITR 16:28:45→16:31:41 | false at C11 16:26:04Z; UPDATE op `00f4b787` 16:28:45.745Z → DONE 16:31:41.502Z; PITR **true**, 7-day logs at freeze; AUTOMATED backup `1790785806842` 16:30:06→16:31:38Z SUCCESSFUL; API `/health` 200 at 16:27:17Z and 16:31:20Z | **confirmed** (the change happened during A1, outside this row; the baseline freezes the post-change state) |
| 0.2 `/curate/` removed | 404 both origins; bucket prefix empty | 404 both origins; 0 objects in `sig-web/curate/` and `sig-public/web/curate/` | **confirmed** |
| 0.3 key rotation | amended in `72b83f24`: operator — key "can stay stale for now" (accepted risk, routed G1) | not observable read-only | recorded, no action |
| 0.4 no merge | Round 11 builds on the chain | `origin/main` still `b7c9e2e3`; 49 open; chain tip unchanged | **confirmed** |

## Differences from META_PLAN (Appendix A and header)

- **F-17 confirmed, refined:** 49 open = #141–#190 **minus #148** (merged 09-26); 191 PRs total (142 merged, 0 closed).
  `origin/main` tree == P31.4 tree, but the chain tip does **not** descend from `origin/main` (NEW-1).
- **F-18 / F-19 confirmed exactly:** 13 PRs red on `composed`+`web`; #165/#179/#185 red on `python`; 33 all-green.
- **F-12 refined:** `sig-alerts` is a Cloud Run **service** on `:latest`; no scheduler or Run job uses `:latest`.
- **F-01 superseded** by Track 0 (backups on, 2 successful backups, PITR on at freeze).
- **Header/§5 counts confirmed:** `origin/main` `b7c9e2e3`; 144 ADR files; 97 deferrals / 36 owed; 715 coverage / 69 not-MET; 58 BL / 32 open.
- **Baseline moved during A1:** planning HEAD `251827b0 → a23fca8a → 72b83f24` (D1 questionnaire; Track-0 PITR/0.3 record) and PITR enabled — all outside A1.
  `72b83f24` also committed an interim copy of `findings/incoming/A1.csv`; it is byte-identical to the final file.

## Delta procedure (run before S1 and before T6)

1. Extract the script below to `docs/build/logs/next-phase/<row>/a1_delta.py` (e.g.
   `awk '/^```python a1_delta/{f=1;next} /^```$/{f=0} f' docs/build/planning/2026-09-30-next-phase/baseline/BASELINE.md > …/a1_delta.py`).
   Its sha256 at A1 is `c71ce1dfe3a687b3712d83d820adfe09572aeedd92ded27f82a17cb7b9965090`.
2. `date -u` · `git -C /Users/stevenvitali/Eleutheria-next-phase fetch origin` (only if `git.chain_tip_descends_from_origin_main`
   reports `unknown`) · `python3 …/a1_delta.py delta docs/build/planning/2026-09-30-next-phase/baseline/baseline.json`.
   Read-only: `git ls-remote/rev-parse/show/merge-base`, `gh pr list/checks`, `gh api` GETs, `gcloud … describe/list`,
   `gcloud storage ls`, `curl` GETs (~6 requests to the site/bucket, ~55 GitHub calls, ~8 gcloud calls; ≈ 1 min).
3. Output: one `CHANGED <key>: <baseline> -> <now>` line per differing key, then a count. It compares the 89 script-derived
   keys (every key in `baseline.json` without a `_provenance` entry); `clock.*` and `git.planning_head_sha` are skipped.
   Manual keys (with `_provenance`) are re-checked by hand only if a related core key changed.
4. Record the delta output and `date -u` in the running row's notes; any `CHANGED` in `git.*`, `gh.*` or `mem.*` means the
   plan's inputs moved (e.g. operator merges, new chain commits) and S1/T6 must re-read the affected sources; `prod.*` changes
   are routed to G1/G2. Expected drift: `gh.ci_*` if PRs are re-run; `prod.sig_pg.backups_*` grows daily (automated backups).

<details><summary><code>a1_delta.py</code> (147 lines, read-only capture/delta)</summary>

```python a1_delta
#!/usr/bin/env python3
"""A1 baseline capture / delta (read-only). Canonical copy: PD/baseline/BASELINE.md (Delta procedure).

  python3 a1_delta.py capture            -> prints flat JSON of the stable keys
  python3 a1_delta.py delta BASELINE.json -> captures again, prints changed / added / removed keys
Read-only: git rev-parse/ls-remote/show, gh (list/checks/api GET), gcloud describe/list, curl GET.
"""
import hashlib, json, subprocess, sys

WT = "/Users/stevenvitali/Eleutheria-next-phase"
REPO = "SteveVitali/Eleutheria"
PROJ, REGION = "zeta-medley-508121-u7", "us-central1"
CHAIN = "devin/p33-8-agent-docs-refresh"
P314 = "devin/p31-4-incremental-restart-and-osm-replay-readiness"
MEM = ["docs/build/LEDGER.md", "docs/tickets/DEFERRALS.md", "docs/tickets/00_MANIFEST.md",
       "docs/build/COVERAGE_MATRIX.csv", "docs/build/BACKLOG.csv", "docs/build/BUILD_INDEX.md",
       "docs/build/reports/current/CURRENT.md", "docs/build/reports/obligations/events.jsonl",
       "docs/build/OPERATIONAL_READINESS.md"]
GC = ["--project", PROJ]


def sh(*a, raw=False):
    r = subprocess.run(a, cwd=WT, capture_output=True)
    return r.stdout if raw else r.stdout.decode().strip()


def js(*a):
    out = sh(*a)
    return json.loads(out) if out else None


def capture():
    k = {"clock.captured_at_utc": sh("date", "-u", "+%Y-%m-%dT%H:%M:%SZ")}
    # --- git (remote truth via ls-remote + GitHub API; no fetch needed)
    rem = dict(reversed(l.split("\t")) for l in sh("git", "ls-remote", "origin", "refs/heads/main",
               f"refs/heads/{CHAIN}", f"refs/heads/{P314}").splitlines())
    k["git.planning_head_sha"] = sh("git", "rev-parse", "HEAD")
    k["git.chain_tip_sha_local"] = sh("git", "rev-parse", CHAIN)
    k["git.chain_tip_sha_origin"] = rem.get(f"refs/heads/{CHAIN}")
    k["git.origin_main_sha"] = rem.get("refs/heads/main")
    k["git.origin_main_tree"] = sh("gh", "api", f"repos/{REPO}/commits/main", "-q", ".commit.tree.sha")
    k["git.p31_4_branch_sha"] = rem.get(f"refs/heads/{P314}")
    k["git.p31_4_branch_tree"] = sh("gh", "api", f"repos/{REPO}/commits/{P314}", "-q", ".commit.tree.sha")
    k["git.origin_main_tree_equals_p31_4_tree"] = k["git.origin_main_tree"] == k["git.p31_4_branch_tree"]
    k["git.worktree_count"] = len(sh("git", "worktree", "list").splitlines())
    tip = k["git.chain_tip_sha_origin"]
    have = subprocess.run(["git", "cat-file", "-e", f"{tip}^{{commit}}"], cwd=WT).returncode == 0
    k["git.chain_tip_descends_from_origin_main"] = (subprocess.run(
        ["git", "merge-base", "--is-ancestor", k["git.origin_main_sha"], tip], cwd=WT).returncode == 0
        if have else "unknown: git fetch origin first")
    # --- GitHub PRs + CI
    prs = js("gh", "pr", "list", "--state", "all", "--limit", "400", "--json",
             "number,state,headRefName,baseRefName,headRefOid")
    op = sorted((p for p in prs if p["state"] == "OPEN"), key=lambda p: p["number"])
    for s in ("OPEN", "MERGED", "CLOSED"):
        k[f"gh.pr_{s.lower()}"] = sum(p["state"] == s for p in prs)
    k["gh.pr_total"] = len(prs)
    k["gh.open_min"], k["gh.open_max"] = op[0]["number"], op[-1]["number"]
    k["gh.lowest_open_base"] = op[0]["baseRefName"]
    k["gh.open_heads_sha256"] = hashlib.sha256("".join(
        f"{p['number']} {p['headRefOid']}\n" for p in op).encode()).hexdigest()
    fail = {}
    for p in op:
        c = js("gh", "pr", "checks", str(p["number"]), "--json", "name,bucket") or []
        bad = sorted(x["name"] for x in c if x["bucket"] != "pass")
        if bad:
            fail[str(p["number"])] = bad
    k["gh.ci_failing_prs"] = fail
    k["gh.ci_failing_count"] = len(fail)
    k["gh.ci_all_pass_count"] = len(op) - len(fail)
    # --- build-memory control digests (at the chain tip commit)
    for f in MEM:
        b = sh("git", "show", f"{tip}:{f}", raw=True) if have else b""
        k[f"mem.sha256.{f}"] = hashlib.sha256(b).hexdigest() if b else "unknown"
        k[f"mem.bytes.{f}"] = len(b)
    if have:
        led = sh("git", "show", f"{tip}:docs/build/LEDGER.md").splitlines()
        for key in ("projectStatus", "nextTicket", "lastCompleted", "chainTip", "round", "blockedOn",
                    "pauseRequested"):
            v = next((l.split(":", 1)[1].split()[0] for l in led if l.startswith(key + ":")), None)
            k[f"mem.ledger.{key}"] = v
    # --- production (read-only)
    for svc in ("sig-web", "sig-api", "sig-alerts"):
        d = js("gcloud", "run", "services", "describe", svc, "--region", REGION, "--format=json", *GC)
        t = d["spec"]["template"]
        a = t["metadata"].get("annotations", {})
        n = svc.replace("-", "_")
        k[f"prod.{n}.revision"] = d["status"]["latestReadyRevisionName"]
        k[f"prod.{n}.image"] = t["spec"]["containers"][0]["image"]
        k[f"prod.{n}.min_instances"] = a.get("autoscaling.knative.dev/minScale", "unset")
        k[f"prod.{n}.max_instances"] = a.get("autoscaling.knative.dev/maxScale", "unset")
        k[f"prod.{n}.ready_transition"] = next(c["lastTransitionTime"] for c in d["status"]["conditions"]
                                               if c["type"] == "Ready")
    d = js("gcloud", "sql", "instances", "describe", "sig-pg", "--format=json", *GC)
    s, b = d["settings"], d["settings"]["backupConfiguration"]
    k.update({"prod.sig_pg.state": d["state"], "prod.sig_pg.tier": s["tier"],
              "prod.sig_pg.disk_gb": s["dataDiskSizeGb"], "prod.sig_pg.settings_version": s["settingsVersion"],
              "prod.sig_pg.backup_enabled": b.get("enabled", False),
              "prod.sig_pg.backup_start_time": b.get("startTime"),
              "prod.sig_pg.backup_retained": b.get("backupRetentionSettings", {}).get("retainedBackups"),
              "prod.sig_pg.pitr_enabled": b.get("pointInTimeRecoveryEnabled", False),
              "prod.sig_pg.deletion_protection": s.get("deletionProtectionEnabled", False)})
    bk = js("gcloud", "sql", "backups", "list", "--instance", "sig-pg", "--format=json", *GC) or []
    k["prod.sig_pg.backups_count"] = len(bk)
    k["prod.sig_pg.backups_successful"] = sum(x.get("status") == "SUCCESSFUL" for x in bk)
    sj = js("gcloud", "scheduler", "jobs", "list", "--location", REGION, "--format=json", *GC)
    k["prod.scheduler.count"] = len(sj)
    k["prod.scheduler.enabled"] = sum(x.get("state") == "ENABLED" for x in sj)
    rj = js("gcloud", "run", "jobs", "list", "--region", REGION, "--format=json", *GC)
    imgs = [x["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["image"] for x in rj]
    k["prod.run_jobs.count"] = len(rj)
    k["prod.run_jobs.distinct_images"] = len(set(imgs))
    k["prod.run_jobs.latest_tag_refs"] = sum(i.endswith(":latest") for i in imgs)
    k["prod.buckets"] = sorted(l.rstrip("/").split("/")[-1] for l in sh(
        "gcloud", "storage", "ls", *GC).splitlines())
    m = sh("curl", "-sS", "https://storage.googleapis.com/zeta-medley-508121-u7-sig-public/manifest.json", raw=True)
    mj = json.loads(m)
    k["prod.public_manifest.release_id"] = mj["release_id"]
    k["prod.public_manifest.sha256"] = hashlib.sha256(m).hexdigest()
    k["prod.public_manifest.ruleset_version"] = mj["reproducibility_inputs"]["ruleset_version"]
    k["prod.public_manifest.as_of_snapshot"] = mj["reproducibility_inputs"]["as_of_snapshot"]
    for key, url in (("home", "https://surveillancegraph.org/"),
                     ("curate_apex", "https://surveillancegraph.org/curate/"),
                     ("curate_run", "https://sig-web-e5ctyx36jq-uc.a.run.app/curate/"),
                     ("api_health", "https://sig-api-e5ctyx36jq-uc.a.run.app/health")):
        k[f"prod.site.{key}_status"] = int(sh("curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url))
    hdr = sh("curl", "-sSI", "https://surveillancegraph.org/").splitlines()
    k["prod.site.home_last_modified"] = next((h.split(":", 1)[1].strip() for h in hdr
                                              if h.lower().startswith("last-modified:")), None)
    k["prod.site.home_sha256"] = hashlib.sha256(sh("curl", "-sS", "https://surveillancegraph.org/", raw=True)).hexdigest()
    return k


if __name__ == "__main__":
    cur = capture()
    if sys.argv[1] == "capture":
        print(json.dumps(cur, indent=1, sort_keys=True))
    else:
        base = json.load(open(sys.argv[2]))
        n = 0
        for key in sorted(cur):  # manual-only baseline keys (no script derivation) are not compared
            if key.startswith(("clock.", "_")) or key == "git.planning_head_sha":
                continue
            if base.get(key, "<absent>") != cur[key]:
                n += 1
                print(f"CHANGED {key}: {json.dumps(base.get(key, '<absent>'))} -> {json.dumps(cur[key])}")
        print(f"{n} changed key(s); delta run at {cur['clock.captured_at_utc']}; baseline {base['clock.captured_at_utc']}")
```

</details>
