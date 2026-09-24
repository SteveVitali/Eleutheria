#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# Dependency vulnerability audit (CI.1 / GL-CI-01, ADR-078).
#
# Exports the locked dependency tree to a requirements file and audits it with
# pip-audit (PyPA's OSV-backed auditor) via uvx — free, no account, no
# credentials, no new committed dependency. NEEDS NETWORK (it queries the
# advisory database) — that is why it rides the nightly rather than the PR gate:
# advisories drift without a commit, and a PyPI/OSV outage must not block PRs.
#
# Exit codes: 0 = no known vulnerabilities; pip-audit's exit code otherwise
# (1 = vulnerabilities found — the nightly report records it, the job goes red).
set -euo pipefail

REQ="$(mktemp -t sig-deps.XXXXXX)"
trap 'rm -f "$REQ" "$REQ.clean"' EXIT

# Export the locked tree (incl. dev group — the toolchain is attack surface too).
# Workspace members export as `-e ./<pkg>` editable lines, which a requirements
# audit cannot resolve — they are our own first-party code, so strip them.
uv export --frozen --all-packages --format requirements-txt -o "$REQ"
grep -v '^-e ' "$REQ" > "$REQ.clean"

uvx --from pip-audit pip-audit -r "$REQ.clean" --skip-editable
