#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# P34.24a / ADR-196 (SIG-ENG-045, SIG-STORE-041): the whole-plan sqitch
# lifecycle proof, run on every PR by the `python` CI job and by
# `make test-sqitch-roundtrip` / `make ci-local`.
#
#   1. fresh postgis/postgis:18-3.6 container on a throwaway network
#   2. CREATE DATABASE sig TEMPLATE template0 — the plan owns its extensions
#      (the image's own database pre-installs postgis dependents, which is the
#      D-P32.16a-1 false environment; template0 = the deployment shape)
#   3. sqitch deploy --verify (the whole plan, every verify script)
#   4. sqitch verify
#   5. sqitch revert -y   (the WHOLE plan)
#   6. clean-state assertions: only plpgsql remains, no non-sqitch relations,
#      the sqitch registry holds zero deployed changes
#   7. sqitch deploy --verify (redeploy)
#   8. sqitch verify
#
# The sqitch image is pinned by digest (a mutable tag fails
# tests/unit/test_sqitch_hygiene.py). Everything is logged to
# docs/build/logs/sqitch-roundtrip-<UTC>.log (gitignored, durable) — the log is
# the cited evidence for D-P32.10a-1 / D-P32.16a-1. Docker must be reachable;
# this gate never skips silently.

set -euo pipefail

PG_IMAGE="postgis/postgis:18-3.6"
SQITCH_IMAGE="sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3"
PG_USER="sig"
PG_PASSWORD="sig"
ADMIN_DB="postgres"   # the image's own database — postgis lands here, NOT plan-owned
PLAN_DB="sig"         # created TEMPLATE template0 — the plan owns its extensions
NET="sig-rt-net"
PG="sig-rt-pg"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="docs/build/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sqitch-roundtrip-$STAMP.log"

exec > >(tee "$LOG") 2>&1

echo "sqitch-roundtrip $STAMP"
echo "  pg image     : $PG_IMAGE"
echo "  sqitch image : $SQITCH_IMAGE"
echo "  log          : $LOG"

if ! docker info >/dev/null 2>&1; then
  echo "FAIL: the Docker daemon is not reachable — the round-trip gate cannot run" >&2
  exit 1
fi

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" --network-alias db \
  -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" \
  -e POSTGRES_DB="$ADMIN_DB" "$PG_IMAGE" >/dev/null

echo "waiting for postgres ..."
# The postgis image restarts the server once after initdb — a single ready
# probe can pass inside the restart window, so require three consecutive real
# connections, 2s apart.
ok=0
for i in $(seq 1 90); do
  if docker exec "$PG" psql -U "$PG_USER" -d "$ADMIN_DB" -tAc 'SELECT 1' >/dev/null 2>&1; then
    ok=$((ok + 1))
    [ "$ok" -ge 3 ] && break
  else
    ok=0
  fi
  [ "$i" -lt 90 ] || { echo "FAIL: postgres never became ready" >&2; exit 1; }
  sleep 2
done

echo "== step 2: CREATE DATABASE $PLAN_DB TEMPLATE template0 =="
docker exec "$PG" psql -U "$PG_USER" -d "$ADMIN_DB" -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS $PLAN_DB" \
  -c "CREATE DATABASE $PLAN_DB TEMPLATE template0"
echo "extensions in $PLAN_DB before deploy (expect plpgsql only):"
docker exec "$PG" psql -U "$PG_USER" -d "$PLAN_DB" -tAc \
  "SELECT extname FROM pg_extension ORDER BY 1"

SQ="docker run --rm --network $NET -v $PWD/db:/repo:ro -w /repo $SQITCH_IMAGE"
URI="db:pg://$PG_USER:$PG_PASSWORD@db:5432/$PLAN_DB"

echo "== step 3: sqitch deploy --verify =="
$SQ deploy --verify "$URI"
echo "extensions after deploy:"
docker exec "$PG" psql -U "$PG_USER" -d "$PLAN_DB" -tAc \
  "SELECT extname FROM pg_extension ORDER BY 1"

echo "== step 4: sqitch verify (whole plan) =="
$SQ verify "$URI"

echo "== step 5: sqitch revert -y (whole plan) =="
$SQ revert -y "$URI"

echo "== step 6: clean-state assertions =="
exts="$(docker exec "$PG" psql -U "$PG_USER" -d "$PLAN_DB" -tAc \
  "SELECT string_agg(extname, ',' ORDER BY extname) FROM pg_extension")"
echo "extensions after full revert: $exts"
[ "$exts" = "plpgsql" ] || {
  echo "FAIL: expected only plpgsql after a full revert, got: $exts" >&2
  exit 1
}
non_sqitch="$(docker exec "$PG" psql -U "$PG_USER" -d "$PLAN_DB" -tAc \
  "SELECT count(*) FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'sqitch')")"
echo "non-sqitch relations after full revert: $non_sqitch"
[ "$non_sqitch" = "0" ] || {
  echo "FAIL: $non_sqitch non-sqitch tables remain after a full revert" >&2
  exit 1
}
deployed="$(docker exec "$PG" psql -U "$PG_USER" -d "$PLAN_DB" -tAc \
  "SELECT count(*) FROM sqitch.changes")"
echo "sqitch.changes rows after full revert: $deployed"
[ "$deployed" = "0" ] || {
  echo "FAIL: sqitch registry still records $deployed deployed changes" >&2
  exit 1
}

echo "== step 7: sqitch deploy --verify (redeploy) =="
$SQ deploy --verify "$URI"

echo "== step 8: sqitch verify (whole plan, redeployed) =="
$SQ verify "$URI"

echo "OK: deploy -> verify -> revert -> clean -> redeploy -> verify all green"
echo "log: $LOG"
