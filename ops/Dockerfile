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

# The uv workspace metadata + sources (built context = repo root).
COPY pyproject.toml uv.lock pylock.toml ./
COPY api ./api
COPY db ./db
COPY ontology ./ontology

# Install uv and the read-API package (+ its workspace deps) into the system env.
RUN pip install --no-cache-dir uv \
 && uv pip install --system ./api ./db

# Cloud Run provides $PORT; bind the read API there. The DSN + secrets arrive as
# environment variables injected from Secret Manager at deploy time.
ENV SIG_API_HOST=0.0.0.0
EXPOSE 8080
CMD ["sh", "-c", "sig-api serve --host 0.0.0.0 --port ${PORT:-8080}"]
