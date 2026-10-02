#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 The SIG project (vendoring) and the build-memory skill authors.
#
# Vendored copy of the build-memory layout validator (BM-VALID-01) so this repository can validate its
# committed build-memory layout (docs/build/, docs/tickets/, docs/adr/) WITHOUT the
# build-memory skill installed (e.g. in CI / make docs-check, deliverable P22.3/EL.1).
#
# Provenance: copied from
#   ~/agent-skills/skills/build-memory/scripts/check-build-memory.sh
#   on 2026-09-09 by ticket P22.3 (build-memory v2 migration). The MIT licence of the
#   source skill is retained above.
#
# LOCAL PATCH (P32.8 / SIG-MEM-003, ADR-127 — this copy is NO LONGER byte-identical to
# upstream; do not describe it as such). The upstream detection logic (layout allowlist,
# ticket-sequence grammar, manifest<->files, DEFERRALS ids, ADR index<->files, LEDGER key
# set, secret/size scans, exit codes) is unchanged; the patch touches only output/reporting:
#   1. the JSON report goes to a caller-selected path (--json PATH) or a unique per-run
#      temp file — the shared /tmp/build-memory-check.json destination (a write-collision
#      between concurrent worktrees) is removed;
#   2. the report records the checked input identity (repo, HEAD commit, dirty flag and an
#      input digest over every file the checker read) so a stale report cannot masquerade
#      as fresh;
#   3. diagnostic records carry {check, severity, file, obligation, evidence, message} and
#      the summary records the process exit code so report severity and exit status agree.
# The reviewed upstream-patch contract for this delta lives in
#   docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md (skill-entry-point integration section).
# ---------------------------------------------------------------------------
# check-build-memory.sh — validate a repo's build-memory layout. (BM-VALID-01.)
#
# Read-only. Everything the other skills derive (ADR index, BUILD_INDEX rows, the
# ticket sequence, DEFERRALS ids, the layout) is CHECKED here, never trusted:
# decompose-spec runs it after seeding, implement-spec before its close commit,
# orchestrate-build at every boundary. A failure is a real block.
#
# Usage:
#   check-build-memory.sh [repo_root] [--json PATH]
#
# Arguments:
#   repo_root — the repo/worktree to check (default: current git toplevel, else cwd).
#   --json PATH — write the machine-readable report to PATH (default: a unique temp
#     file under ${TMPDIR:-/tmp}; the exact path is printed on the last stdout line).
#
# Checks (each violation names the file and the rule):
#   - layout: only the named entries at the root of docs/build/; logs/.gitignore present
#   - ticket filenames: grammar (NN[a-z]?_<ID>__<slug>.md) + unique sequence keys;
#     a legacy filename is accepted when the manifest chain table lists it
#   - manifest <-> files: every chain row has a file; every ticket file has a chain row
#     (companions excepted); every HUMAN/GATE marker is a chain row
#   - Depends on: only points backward (no forward dependency)
#   - skeletons: Kind: skeleton has NO Run: line
#   - DEFERRALS.md: ids unique; statuses in {OPEN,PARTIAL,DONE,WONTFIX,ACCEPTED-SKELETON};
#     no OPEN row scoped to a gate whose readout says PASSED
#   - ADRs: files <-> generated index (regenerate + diff); every ADR has ## Revisit trigger;
#     spec ADR appendix equals the file set when a spec+appendix is resolvable
#   - LEDGER.md: the CURRENT STATE key set present and in order; nextTicket names a chain
#     row or DONE; every PHASE LOG "done" ticket has a BUILD_INDEX row and runs/<ID>.md
#   - REQ coverage (when canonicalSpec + req_id_pattern resolve): every id a ticket cites
#     exists in the spec; every in-scope id has exactly one owner
#   - size + secrets: fixtures >1MB / any file >5MB under docs/build flagged; no secret
#     token shapes in docs/build or docs/tickets
#
# Output:
#   Human-readable summary to stdout (final line names the exact report path).
#   Machine-readable JSON to --json PATH or a unique temp file — never a shared
#   path: two worktrees can validate concurrently without overwriting each other.
#
# Report shape (build-memory-check/2):
#   {"schema","tool","input":{"repo","commit","dirty","input_digest"},
#    "buildMemory":true,"summary":{"violations":N,"warnings":M,"exit":E},
#    "violations":[{check,severity,file,obligation,evidence,message}],
#    "warnings":[…same…]}
#   input_digest is a sha256 over the sha256 of every file the checker read —
#   a report is valid only for the exact input revision it names.
#
# Exit codes:
#   0 — clean (build-memory repo, no violations)
#   1 — violations found
#   2 — not a build-memory repo (no docs/build/README.md marker)
#
# Read-only: never writes or mutates the repo (only the report file).
# Compatible with bash 3.2+ (macOS default). No associative arrays, no mapfile.

set -o pipefail

REPO=""
JSON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON="$2"; shift 2 ;;
    --json=*) JSON="${1#--json=}"; shift ;;
    --help|-h)
      sed -n '24,44p' "$0" 2>/dev/null || true
      echo "usage: check-build-memory.sh [repo_root] [--json PATH]"
      exit 0 ;;
    *) if [ -z "$REPO" ]; then REPO="$1"; else echo "check-build-memory: unexpected argument '$1'" >&2; exit 2; fi; shift ;;
  esac
done
REPO="${REPO:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
MARKER='<!-- build-memory: v2 -->'
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$JSON" ]; then
  # Unique per-invocation report path — the caller never races another worktree
  # over a fixed /tmp filename. BSD mktemp substitutes only trailing X's, so the
  # template carries no .json suffix. The resolved path is printed on stdout.
  JSON="$(mktemp "${TMPDIR:-/tmp}/build-memory-check.XXXXXXXX")" || exit 2
else
  # Caller-selected destination — its parent may not exist yet.
  _json_dir="$(dirname "$JSON")"
  [ -d "$_json_dir" ] || mkdir -p "$_json_dir" 2>/dev/null || true
fi

BUILD="$REPO/docs/build"
TICKETS="$REPO/docs/tickets"
ADR="$REPO/docs/adr"

# portable file digest (sha256sum | shasum | openssl), hex digest only
_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}';
  else openssl dgst -sha256 "$1" | awk '{print $NF}'; fi
}
_sha256_stream() {   # sha256 of stdin
  if command -v sha256sum >/dev/null 2>&1; then sha256sum | awk '{print $1}';
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 | awk '{print $1}';
  else openssl dgst -sha256 | awk '{print $NF}'; fi
}

# Not a build-memory repo → exit 2 (the two freshness detectors' "nothing to do" convention).
if [ ! -f "$BUILD/README.md" ] || ! grep -qF "$MARKER" "$BUILD/README.md" 2>/dev/null; then
  echo "check-build-memory: $REPO is not a build-memory repo (no docs/build/README.md marker '$MARKER')."
  printf '{"schema":"build-memory-check/2","repo":"%s","buildMemory":false,"summary":{"violations":0,"warnings":0,"exit":2},"violations":[],"warnings":[]}\n' "$REPO" > "$JSON" || {
    echo "check-build-memory: cannot write report to $JSON" >&2; exit 2; }
  echo "  JSON: $JSON"
  exit 2
fi

VIOL="$(mktemp)"; WARN="$(mktemp)"
trap 'rm -f "$VIOL" "$WARN" 2>/dev/null' EXIT
# diag record: <check>\t<file>\t<obligation>\t<evidence>\t<message>
viol() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "${3:-}" "${4:-}" "${5:-}" "$2" >> "$VIOL"; }
warn() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "${3:-}" "${4:-}" "${5:-}" "$2" >> "$WARN"; }

# Ticket-id grammar (canonical interpretation of BM-LAYOUT-02; documented in layout.md).
# GATE-ACCEPT is the one named gate marker (the operator's accepted-deviations signature, BM-TAIL-01).
ID_RE='((HUMAN-H|GATE-G)[0-9]+|GATE-ACCEPT|[A-Z]+[0-9]*[a-z]?(\.[0-9]+[a-z]?)?)'
FNAME_RE="^[0-9]{2,3}[a-z]?_${ID_RE}__[a-z0-9-]+\.md$"

# ── LEDGER value reader (never-fail; strips inline comments) ──────────────────
LEDGER="$BUILD/LEDGER.md"
lval() {
  [ -f "$LEDGER" ] || return 0
  grep -m1 -E "^[[:space:]]*${1}:" "$LEDGER" 2>/dev/null \
    | sed -E "s/^[[:space:]]*${1}:[[:space:]]*//; s/[[:space:]]*#.*$//; s/[[:space:]]*$//"
}

MANIFEST_REL="$(lval manifest)"; [ -n "$MANIFEST_REL" ] || MANIFEST_REL="docs/tickets/00_MANIFEST.md"
case "$MANIFEST_REL" in /*) MANIFEST="$MANIFEST_REL" ;; *) MANIFEST="$REPO/$MANIFEST_REL" ;; esac

# ── 1. Layout: allowlist at the root of docs/build/ ──────────────────────────
ALLOWED=" README.md LEDGER.md BUILD_INDEX.md runs pr readouts planning reports tools fixtures logs COVERAGE_MATRIX.csv CAPSTONE_GAP_ANALYSIS.md COMPOSED_E2E_REPORT.md CAPSTONE_CLOSURE.md BACKLOG.csv BACKLOG.md TICKET_VS_SPEC.md SPEC_RECONCILIATION_PLAN.md INTEGRATION_PLAN.md OPERATIONAL_READINESS.md "
for entry in "$BUILD"/* "$BUILD"/.[!.]*; do
  [ -e "$entry" ] || continue
  b="$(basename "$entry")"
  case "$ALLOWED" in *" $b "*) : ;; *) viol layout "docs/build/$b is not an allowed build-memory root entry" "docs/build/$b" ;; esac
done
# logs/.gitignore present with the right contents (BM-LAYOUT-03).
if [ ! -f "$BUILD/logs/.gitignore" ]; then
  viol layout "docs/build/logs/.gitignore is missing (must contain '*' and '!.gitignore')" "docs/build/logs/.gitignore"
else
  grep -qE '^\*$' "$BUILD/logs/.gitignore" || warn layout "docs/build/logs/.gitignore should contain a bare '*'" "docs/build/logs/.gitignore"
  grep -qE '^!\.gitignore$' "$BUILD/logs/.gitignore" || warn layout "docs/build/logs/.gitignore should contain '!.gitignore'" "docs/build/logs/.gitignore"
fi

# ── Parse the manifest chain table + companions ──────────────────────────────
CHAIN_FILES="$(mktemp)"     # one filename per chain-table row
COMPANIONS="$(mktemp)"
trap 'rm -f "$VIOL" "$WARN" "$CHAIN_FILES" "$COMPANIONS" 2>/dev/null' EXIT
REQ_PATTERN=""
if [ -f "$MANIFEST" ]; then
  # companions: line (comma-separated filenames).
  grep -m1 -iE '^[[:space:]]*companions:' "$MANIFEST" 2>/dev/null \
    | sed -E 's/^[^:]*:[[:space:]]*//' | tr ',' '\n' \
    | sed -E 's/[`[:space:]]//g' | grep -E '\.md$' >> "$COMPANIONS" || true
  # req_id_pattern: line.
  REQ_PATTERN="$(grep -m1 -iE '^[[:space:]]*req_id_pattern:' "$MANIFEST" 2>/dev/null | sed -E 's/^[^:]*:[[:space:]]*//; s/[`[:space:]]*$//; s/^`//')"
  # Chain rows: table lines inside the "## The chain" section that name a *.md file.
  awk '
    /^##[[:space:]]+The chain/ {inchain=1; next}
    inchain && /^##[[:space:]]/ {inchain=0}
    inchain && /^\|/ {print}
  ' "$MANIFEST" | grep -E '[A-Za-z0-9_.-]+\.md' | while IFS= read -r row; do
    printf '%s\n' "$row" | grep -oE '[0-9A-Za-z_.-]+\.md' | head -1
  done | sort -u >> "$CHAIN_FILES"
fi
# _TEMPLATE.md and DEFERRALS.md are always companions.
printf '%s\n' "_TEMPLATE.md" "DEFERRALS.md" >> "$COMPANIONS"
COMPANIONS_SORTED="$(sort -u "$COMPANIONS")"

is_companion() { printf '%s\n' "$COMPANIONS_SORTED" | grep -qxF "$1"; }
in_chain() { grep -qxF "$1" "$CHAIN_FILES"; }

# ── 2. Ticket files: grammar, unique sequence, marker+chain membership ───────
SEQ_KEYS="$(mktemp)"; ID_SEQ="$(mktemp)"
trap 'rm -f "$VIOL" "$WARN" "$CHAIN_FILES" "$COMPANIONS" "$SEQ_KEYS" "$ID_SEQ" 2>/dev/null' EXIT
if [ -d "$TICKETS" ]; then
  for f in "$TICKETS"/*.md; do
    [ -f "$f" ] || continue
    b="$(basename "$f")"
    [ "$b" = "00_MANIFEST.md" ] && continue
    is_companion "$b" && continue
    if printf '%s' "$b" | grep -qE "$FNAME_RE"; then
      key="$(printf '%s' "$b" | sed -E 's/^([0-9]{2,3}[a-z]?)_.*$/\1/')"
      id="$(printf '%s' "$b" | sed -E "s/^[0-9]{2,3}[a-z]?_(${ID_RE})__.*$/\1/")"
      num="$(printf '%s' "$key" | sed -E 's/[a-z]$//')"
      printf '%s\t%s\n' "$key" "$b" >> "$SEQ_KEYS"
      printf '%s\t%s\t%s\n' "$id" "$num" "$b" >> "$ID_SEQ"
      in_chain "$b" || viol manifest "ticket file $b has no row in the manifest chain table" "docs/tickets/$b" "$id"
    else
      # Legacy filename allowed only if the chain table lists it.
      if in_chain "$b"; then
        id="$(printf '%s' "$b" | sed -E 's/__.*$//; s/^[0-9]*[a-z]?_?//; s/\.md$//')"
        num="$(printf '%s' "$b" | sed -E 's/^([0-9]+).*$/\1/')"
        case "$num" in ''|*[!0-9]*) num=0 ;; esac
        printf '%s\t%s\t%s\n' "$id" "$num" "$b" >> "$ID_SEQ"
      else
        viol filename "ticket file $b does not match the filename grammar and is not a listed chain row" "docs/tickets/$b"
      fi
    fi
  done
  # duplicate sequence keys
  if [ -s "$SEQ_KEYS" ]; then
    cut -f1 "$SEQ_KEYS" | sort | uniq -d | while IFS= read -r dup; do
      [ -n "$dup" ] && viol sequence "duplicate ticket sequence key '$dup' (two files share the same NN[a-z]? prefix)" "docs/tickets" "" "$dup"
    done
  fi
fi

# every chain-table filename must exist on disk
if [ -s "$CHAIN_FILES" ]; then
  while IFS= read -r cf; do
    [ -n "$cf" ] || continue
    [ "$cf" = "00_MANIFEST.md" ] && continue
    if [ ! -f "$TICKETS/$cf" ]; then
      # could be a docs/build companion (rare); only flag if truly absent
      [ -f "$REPO/$cf" ] || viol manifest "manifest chain row names $cf but no such file exists in docs/tickets/" "docs/tickets/00_MANIFEST.md" "" "$cf"
    fi
  done < "$CHAIN_FILES"
fi

# ── 3. Depends on (backward only) + 4. skeleton has no run line ──────────────
seq_of_id() { grep -E "^$1	" "$ID_SEQ" 2>/dev/null | head -1 | cut -f2; }   # tab-separated
if [ -d "$TICKETS" ]; then
  for f in "$TICKETS"/*.md; do
    [ -f "$f" ] || continue
    b="$(basename "$f")"
    [ "$b" = "00_MANIFEST.md" ] && continue
    is_companion "$b" && continue
    my_num="$(grep -E "	$b$" "$ID_SEQ" 2>/dev/null | head -1 | cut -f2)"
    # skeleton check (robust to markdown bold/table cells around Kind: and Run:)
    if grep -qiE 'Kind:[^|]*skeleton' "$f"; then
      if grep -E 'Run:' "$f" | grep -q 'implement-spec'; then
        viol skeleton "skeleton ticket $b carries a Run: line (a skeleton must have no run line)" "docs/tickets/$b"
      fi
    fi
    # depends-on backward check
    dep_line="$(grep -m1 -iE '(^|[|*[:space:]])Depends on:' "$f" | sed -E 's/.*Depends on:[[:space:]]*//; s/`//g')"
    case "$dep_line" in ''|*[Nn]othing*|*[Nn]one*|'—'*|-*) : ;; *)
      # extract candidate ids from the dependency line
      printf '%s' "$dep_line" | grep -oE "$ID_RE" | sort -u | while IFS= read -r dep; do
        [ -n "$dep" ] || continue
        dep_num="$(seq_of_id "$dep")"
        [ -n "$dep_num" ] || continue
        [ -n "$my_num" ] || continue
        if [ "$dep_num" -gt "$my_num" ] 2>/dev/null; then
          viol depends "ticket $b depends on $dep which lands later (forward dependency)" "docs/tickets/$b" "" "$dep"
        fi
      done
    ;; esac
  done
fi

# ── 5. DEFERRALS.md ids unique + valid statuses ──────────────────────────────
DEF="$TICKETS/DEFERRALS.md"
VALID_STATUS=" OPEN PARTIAL DONE WONTFIX ACCEPTED-SKELETON "
if [ -f "$DEF" ]; then
  DEF_IDS="$(mktemp)"
  # table rows whose first cell is an id like D-<TICKET>-<n>
  grep -E '^\|[[:space:]]*D-' "$DEF" | while IFS= read -r row; do
    id="$(printf '%s' "$row" | sed -E 's/^\|[[:space:]]*//; s/[[:space:]]*\|.*$//')"
    status="$(printf '%s' "$row" | sed -E 's/[[:space:]]*\|[[:space:]]*$//' | awk -F'|' '{print $NF}' | sed -E 's/^[[:space:]]*//; s/[[:space:]].*$//' | tr 'a-z' 'A-Z')"
    printf '%s\n' "$id" >> "$DEF_IDS"
    case "$VALID_STATUS" in
      *" $status "*) : ;;
      *) viol deferrals "DEFERRALS row $id has an invalid (orphan) status '$status'" "docs/tickets/DEFERRALS.md" "$id" ;;
    esac
  done
  if [ -s "$DEF_IDS" ]; then
    sort "$DEF_IDS" | uniq -d | while IFS= read -r dup; do
      [ -n "$dup" ] && viol deferrals "duplicate DEFERRALS id '$dup'" "docs/tickets/DEFERRALS.md" "$dup"
    done
  fi
  rm -f "$DEF_IDS" 2>/dev/null
  # no OPEN row scoped to a gate whose readout says PASSED
  if [ -d "$BUILD/readouts" ]; then
    for ro in "$BUILD"/readouts/GATE-*.md; do
      [ -f "$ro" ] || continue
      if grep -qiE 'verdict:?[[:space:]]*PASSED|^PASSED|\bPASSED\b' "$ro"; then
        g="$(basename "$ro" .md)"   # e.g. GATE-G1
        if grep -E '^\|[[:space:]]*D-' "$DEF" | grep -iE '\bOPEN\b' | grep -qF "$g"; then
          viol deferrals "an OPEN DEFERRALS row references $g whose readout says PASSED" "docs/tickets/DEFERRALS.md" "" "$g"
        fi
      fi
    done
  fi
fi

# ── 6. ADRs: index match + revisit trigger + spec appendix (when present) ────
if [ -d "$ADR" ]; then
  for a in "$ADR"/ADR-*.md; do
    [ -f "$a" ] || continue
    grep -qE '^##[[:space:]]+Revisit trigger' "$a" || viol adr "$(basename "$a") has no '## Revisit trigger' section" "docs/adr/$(basename "$a")"
  done
  if [ -f "$ADR/README.md" ]; then
    if [ -x "$SELF_DIR/adr-index.sh" ] || [ -f "$SELF_DIR/adr-index.sh" ]; then
      gen="$(mktemp)"
      bash "$SELF_DIR/adr-index.sh" --check "$ADR" > "$gen" 2>/dev/null
      if ! diff -q "$gen" "$ADR/README.md" >/dev/null 2>&1; then
        viol adr "docs/adr/README.md does not match a fresh adr-index regeneration (hand-edited or stale)" "docs/adr/README.md"
      fi
      rm -f "$gen" 2>/dev/null
    fi
  fi
fi
# spec ADR appendix == file set (BM-ADR-04, when resolvable)
SPEC_REL="$(lval canonicalSpec)"
if [ -n "$SPEC_REL" ]; then
  case "$SPEC_REL" in /*) SPEC="$SPEC_REL" ;; *) SPEC="$REPO/$SPEC_REL" ;; esac
  if [ -f "$SPEC" ] && grep -qiE 'ADR (appendix|index)|Appendix [A-Z][^\n]*ADR' "$SPEC"; then
    spec_adrs="$(grep -oE 'ADR-[0-9]{3}' "$SPEC" | sort -u)"
    file_adrs="$(ls "$ADR" 2>/dev/null | grep -oE '^ADR-[0-9]{3}' | sort -u)"
    if [ -n "$spec_adrs" ] && [ "$spec_adrs" != "$file_adrs" ]; then
      warn adr "spec ADR appendix and docs/adr/ file set differ (BM-ADR-04)" "$SPEC_REL"
    fi
  fi
fi

# ── 7. LEDGER key order + nextTicket + PHASE LOG done coverage ───────────────
EXPECTED_KEYS="projectStatus nextTicket lastCompleted blockedOn pauseRequested returnPass manifest canonicalSpec memoryRoot dispatchTarget buildWorktree buildBranchBase pinnedBaseSha chainTip benchmarkSet autonomy mergePolicy round updatedAt"
if [ -f "$LEDGER" ]; then
  # keys inside the CURRENT STATE fenced block, in file order
  got="$(awk '
    /^##[[:space:]]+CURRENT STATE/ {inblk=1; next}
    inblk && /^##[[:space:]]/ {inblk=0}
    inblk && /^[[:space:]]*[A-Za-z][A-Za-z0-9]*:([[:space:]]|$)/ {
      line=$0; sub(/^[[:space:]]*/,"",line); sub(/:.*/,"",line); print line
    }
  ' "$LEDGER" | tr '\n' ' ' | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')"
  exp="$(printf '%s' "$EXPECTED_KEYS" | sed -E 's/[[:space:]]+/ /g')"
  if [ "$got" != "$exp" ]; then
    viol ledger "LEDGER.md CURRENT STATE keys are missing or out of order (expected: $exp)" "docs/build/LEDGER.md"
  fi
  nt="$(lval nextTicket)"
  if [ -n "$nt" ] && [ "$nt" != "DONE" ] && [ "$nt" != "SETUP" ]; then
    # must name a chain row — by exact id (ID_SEQ) or as the _<ID>__ segment of a chain filename.
    nt_re="$(printf '%s' "$nt" | sed 's/[.[\*^$]/\\&/g')"
    if [ -s "$ID_SEQ" ] && ! grep -qE "^${nt_re}$(printf '\t')" "$ID_SEQ" && ! grep -qE "_${nt_re}__" "$CHAIN_FILES"; then
      warn ledger "LEDGER nextTicket '$nt' does not name a known chain row or DONE" "docs/build/LEDGER.md" "" "$nt"
    fi
  fi
  # PHASE LOG "done" tickets -> a BUILD_INDEX row + an evidence file (runs/<ID>.md or pr/<ID>.md)
  grep -E '^-[[:space:]]' "$LEDGER" | while IFS= read -r ln; do
    printf '%s' "$ln" | grep -qE '\bdone\b' || continue
    tid="$(printf '%s' "$ln" | sed -E "s/^-[[:space:]]*[0-9-]+[[:space:]]*—[[:space:]]*(${ID_RE}).*/\1/")"
    printf '%s' "$tid" | grep -qE "^${ID_RE}$" || continue
    tid_re="$(printf '%s' "$tid" | sed 's/[.[\*^$]/\\&/g')"
    # match the id as a whole table cell, not a substring (T1 must not be satisfied by a T12 row)
    if [ -f "$BUILD/BUILD_INDEX.md" ] && ! grep -qE "\|[[:space:]]*${tid_re}[[:space:]]*\|" "$BUILD/BUILD_INDEX.md"; then
      viol index "PHASE LOG marks $tid done but BUILD_INDEX.md has no row for it" "docs/build/BUILD_INDEX.md" "$tid"
    fi
    if [ ! -f "$BUILD/runs/$tid.md" ] && [ ! -f "$BUILD/pr/$tid.md" ]; then
      viol index "PHASE LOG marks $tid done but neither docs/build/runs/$tid.md nor pr/$tid.md exists (no evidence file)" "docs/build/LEDGER.md" "$tid"
    fi
  done
fi

# ── 8. REQ coverage (only when spec + pattern resolve) ───────────────────────
if [ -n "$REQ_PATTERN" ] && [ -n "${SPEC:-}" ] && [ -f "${SPEC:-/nonexistent}" ]; then
  spec_ids="$(grep -oE "$REQ_PATTERN" "$SPEC" 2>/dev/null | sort -u)"
  if [ -d "$TICKETS" ] && [ -n "$spec_ids" ]; then
    for f in "$TICKETS"/*.md; do
      [ -f "$f" ] || continue
      b="$(basename "$f")"; [ "$b" = "00_MANIFEST.md" ] && continue; is_companion "$b" && continue
      grep -oE "$REQ_PATTERN" "$f" 2>/dev/null | sort -u | while IFS= read -r rid; do
        [ -n "$rid" ] || continue
        printf '%s\n' "$spec_ids" | grep -qxF "$rid" || warn reqcov "ticket $b cites $rid which is not in the spec" "docs/tickets/$b" "" "$rid"
      done
    done
  fi
fi

# ── 9. size + secret checks ──────────────────────────────────────────────────
if [ -d "$BUILD" ]; then
  find "$BUILD" -type f ! -path '*/logs/*' 2>/dev/null | while IFS= read -r f; do
    sz="$(wc -c < "$f" 2>/dev/null | tr -d ' ')"
    case "$sz" in ''|*[!0-9]*) continue ;; esac
    [ "$sz" -gt 5242880 ] && warn size "$(printf '%s' "$f" | sed "s#$REPO/##") exceeds 5 MB" "$(printf '%s' "$f" | sed "s#$REPO/##")"
    case "$f" in */fixtures/*) [ "$sz" -gt 1048576 ] && warn size "fixture $(printf '%s' "$f" | sed "s#$REPO/##") exceeds 1 MB" "$(printf '%s' "$f" | sed "s#$REPO/##")" ;; esac
  done
fi
SECRET_RE='AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-'
for scan in "$BUILD" "$TICKETS"; do
  [ -d "$scan" ] || continue
  hits="$(grep -rlE "$SECRET_RE" "$scan" 2>/dev/null | grep -v '/logs/' || true)"
  if [ -n "$hits" ]; then
    printf '%s\n' "$hits" | while IFS= read -r h; do
      [ -n "$h" ] && viol secret "$(printf '%s' "$h" | sed "s#$REPO/##") contains a secret-shaped token" "$(printf '%s' "$h" | sed "s#$REPO/##")"
    done
  fi
done

# ── Report + JSON ────────────────────────────────────────────────────────────
NV="$(wc -l < "$VIOL" | tr -d ' ')"; NW="$(wc -l < "$WARN" | tr -d ' ')"
EXIT_CODE=0; [ "$NV" -eq 0 ] || EXIT_CODE=1

# Checked-input identity — the report is valid only for the revision it names.
COMMIT="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
DIRTY=false
if [ -n "$COMMIT" ] && [ -n "$(git -C "$REPO" status --porcelain -- docs/build docs/tickets docs/adr "${SPEC_REL:-docs/2_canonical_design_spec.md}" 2>/dev/null)" ]; then
  DIRTY=true
fi
# Every file the checker's verdict could depend on: all of docs/build (minus the
# gitignored logs subtree), all ticket markdown, the ADR set, and the canonical spec.
INPUT_SET="$(mktemp)"
{
  [ -d "$BUILD" ] && find "$BUILD" -type f ! -path '*/logs/*'
  [ -d "$TICKETS" ] && find "$TICKETS" -type f -name '*.md'
  [ -d "$ADR" ] && find "$ADR" -type f -name '*.md'
  [ -n "${SPEC:-}" ] && [ -f "$SPEC" ] && printf '%s\n' "$SPEC"
  true
} | sort -u > "$INPUT_SET"
INPUT_DIGEST="$(while IFS= read -r _f; do _sha256 "$_f"; done < "$INPUT_SET" | _sha256_stream)"
rm -f "$INPUT_SET"

_json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
_emit_diags() {  # $1 records file · $2 severity
  first=1
  while IFS="$(printf '\t')" read -r c f o e m; do
    [ -n "$c" ] || continue
    [ "$first" -eq 1 ] || printf ','
    first=0
    printf '{"check":"%s","severity":"%s","file":"%s","obligation":"%s","evidence":"%s","message":"%s"}' \
      "$(_json_escape "$c")" "$2" "$(_json_escape "$f")" "$(_json_escape "$o")" "$(_json_escape "$e")" "$(_json_escape "$m")"
  done < "$1"
}
# The report is written atomically — a crash mid-write never leaves a torn
# report another reader could mistake for complete.
{
  printf '{"schema":"build-memory-check/2","tool":"check-build-memory.sh",'
  printf '"input":{"repo":"%s","commit":"%s","dirty":%s,"input_digest":"%s"},' \
    "$(_json_escape "$REPO")" "$(_json_escape "$COMMIT")" "$DIRTY" "$INPUT_DIGEST"
  printf '"buildMemory":true,"summary":{"violations":%s,"warnings":%s,"exit":%s},' "$NV" "$NW" "$EXIT_CODE"
  printf '"violations":['; _emit_diags "$VIOL" error
  printf '],"warnings":['; _emit_diags "$WARN" warning
  printf ']}\n'
} > "$JSON.tmp" && mv "$JSON.tmp" "$JSON" || {
  rm -f "$JSON.tmp" 2>/dev/null
  echo "check-build-memory: cannot write report to $JSON" >&2
  exit 2
}

echo "check-build-memory: $REPO"
if [ "$NV" -eq 0 ]; then
  echo "  ✓ no violations ($NW warning(s))"
else
  echo "  ✗ $NV violation(s), $NW warning(s):"
  awk -F'\t' '{printf "    - %s", $1; if ($3 != "") printf " [%s]", $3; if ($2 != "") printf " %s", $2; printf ": %s\n", $5}' "$VIOL"
fi
[ "$NW" -gt 0 ] && awk -F'\t' '{printf "    ~ %s", $1; if ($3 != "") printf " [%s]", $3; if ($2 != "") printf " %s", $2; printf ": %s\n", $5}' "$WARN"
echo "  JSON: $JSON"

exit "$EXIT_CODE"
