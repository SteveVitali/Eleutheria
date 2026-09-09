# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Degraded-but-alive mode (SIG-GOV-021, RISK-P0-12, LD-P07, §46.4-5, ADR-067).

SIG defines a mode that runs at ~zero marginal cost: the fully static site, served from
the last-published export behind an honest staleness banner, with **no live API**. This
is the survival mode when the budget or the infrastructure is gone.

The static build is a **pure function of committed bytes** — the shell reads its data at
BUILD time (``web/src/lib/data.ts``, ADR-066), so ``web/dist`` has no runtime API
dependency by construction. This module drives that build and, crucially, **fails
loudly** if it cannot rebuild: *a sustainability plan that fails silently is not a plan*
(the governance doc's dormant-scheduler warning). The monthly keepalive workflow
(``.github/workflows/keepalive.yml``) runs exactly this so a free scheduler that silently
disables dormant jobs is caught by a red build, not by a dead site.

Cost: **$0 beyond the static host** — one `npm run build` over committed bytes, no
database, no API process, no paid infrastructure (SIG-STORE-003).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

#: An injectable process runner (real ``subprocess.run`` in production; a stub in tests).
Runner = Callable[..., subprocess.CompletedProcess[str]]


class DegradedBuildError(RuntimeError):
    """Raised when the degraded static build cannot be produced — fails LOUD (RISK-P0-12)."""


def build_static_site(
    *,
    repo_root: Path,
    data_source: str = "fixtures",
    export_dir: str | None = None,
    runner: Runner = subprocess.run,
) -> Path:
    """Build the fully static site (``web/dist``) with **no API dependency**.

    ``data_source`` is ``fixtures`` (the committed typed fixtures — always present) or
    ``export`` (the last committed export snapshot). Raises :class:`DegradedBuildError`
    the moment the build command fails or ``web/dist`` is not produced — never returns a
    stale/partial success (the fails-loudly contract).
    """
    web = repo_root / "web"
    if not web.exists():
        raise DegradedBuildError(f"web/ not found at {web}")
    env = os.environ.copy()
    env["SIG_DATA_SOURCE"] = data_source
    if export_dir:
        env["SIG_EXPORT_DIR"] = export_dir
    cmd: Sequence[str] = ["npm", "--prefix", str(web), "run", "build"]
    try:
        result = runner(cmd, env=env, capture_output=True, text=True, cwd=str(repo_root))
    except FileNotFoundError as exc:  # npm not installed
        raise DegradedBuildError(f"cannot run the static build: {exc}") from exc
    if result.returncode != 0:
        raise DegradedBuildError(
            "degraded static build FAILED (rc="
            f"{result.returncode}): the site could not be rebuilt from committed bytes. "
            "A keepalive that cannot rebuild must fail loudly (RISK-P0-12).\n"
            f"{(result.stderr or result.stdout or '')[-2000:]}"
        )
    dist = web / "dist"
    if not dist.exists() or not any(dist.iterdir()):
        raise DegradedBuildError(
            f"degraded build reported success but produced no static site at {dist}"
        )
    return dist


__all__ = ["Runner", "DegradedBuildError", "build_static_site"]
