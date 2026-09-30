# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# The SIG read-API image (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075). Built + pushed
# to Artifact Registry by `sig-ops deploy --target gcp`, run on Cloud Run
# (min-instances 0, scales to zero) with managed TLS. Contains NO secret: the PG
# password + API env are injected from Secret Manager at deploy time (HG-09).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# The uv workspace metadata + sources (built context = repo root). uv resolves
# the workspace from the root pyproject, which declares every member in
# [tool.uv.workspace].members — so each member directory must exist even though
# only sig-api's transitive closure is installed (P24.1 gap-closure, ADR-075).
COPY pyproject.toml uv.lock pylock.toml ./
COPY ontology ./ontology
COPY db ./db
COPY connectors ./connectors
COPY parsing ./parsing
COPY resolution ./resolution
COPY reconcile ./reconcile
COPY inference ./inference
COPY tasks ./tasks
COPY api ./api
COPY exports ./exports
COPY orchestration ./orchestration
COPY policy ./policy
COPY ops ./ops
COPY evidence ./evidence

# Install uv and the read-API package (+ its transitive workspace deps) into the
# system env. Installing ./api pulls sig-reconcile/-inference/-policy/-evidence/
# -db/-resolution/-exports from the local workspace. ./connectors is installed
# too (P25.5): the same image backs `sig-connectors run` Cloud Run jobs (the
# MuckRock Cloudflare WAF challenges local/residential egress but answers GCP
# datacenter egress — probe 2026-09-15), so the live connector path runs in
# cloud. ./ops joins it (P26.1 / OPS.2): the scheduled `sig-probe` +
# `sig-ingest-<source>` Cloud Run jobs run `sig-ops probe-hosted` /
# `sig-ops scheduled-ingest`, which wraps the same gated `connectors.runner`
# path and appends the WORM run rows to gs://…-sig-restricted/ops/. Secret
# values still arrive only from Secret Manager env vars (HG-09).
#
# P31.2: the install is CONSTRAINED to the committed uv.lock (exported as a
# constraints file), so an image build is reproducible and a new upstream release
# cannot break it. Observed 2026-09-24: an unconstrained resolve picked
# sqlalchemy 2.1.0, whose sdist uv refuses (duplicate normalized extra), and the
# build failed; the lock pins 2.0.52.
RUN pip install --no-cache-dir uv \
 && uv export --frozen --no-emit-workspace --no-hashes --all-packages --no-dev \
      -o /tmp/constraints.txt \
 && uv pip install --system -c /tmp/constraints.txt ./api ./connectors ./ops \
 && rm /tmp/constraints.txt

# Cloud Run provides $PORT; bind the read API there. When SIG_CLOUDSQL_CONNECTION
# is set (the Cloud SQL socket instance connection name), assemble the PgReadStore
# DSN at runtime from the parts — the PG password arrives from Secret Manager as
# $SIG_PG_PASSWORD and is NEVER stored in the deploy config or image (HG-09). The
# public API SET ROLEs to $SIG_API_ROLE (default sig_read_public) so RLS serves
# only tier-0 rows. With no Cloud SQL connection the demo store is served (local).
ENV SIG_API_HOST=0.0.0.0 \
    SIG_PG_USER=sig \
    SIG_PG_DB=sig \
    SIG_API_ROLE=sig_read_public
EXPOSE 8080
CMD ["sh", "-c", "if [ -n \"$SIG_CLOUDSQL_CONNECTION\" ]; then exec sig-api serve --host 0.0.0.0 --port ${PORT:-8080} --dsn \"postgresql://${SIG_PG_USER}:${SIG_PG_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}\" ${SIG_API_ROLE:+--role \"$SIG_API_ROLE\"}; else exec sig-api serve --host 0.0.0.0 --port ${PORT:-8080}; fi"]
