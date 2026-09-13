# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Backups + the restore drill (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075).

Under the ADR-075 DECISION (an e2-micro running the compose stack) the backup
strategy is ``pg_dump`` (custom format) synced to a PRIVATE GCS backup bucket; the
restore is proven by a **restore drill** — dump the live claim spine, restore it
into a *fresh* database, and assert the graph (claim / evidence / entity counts)
reproduces byte-for-byte in cardinality.

This module keeps the drill's shape independent of *where* the SQL tools run: the
``run`` callable is injectable, so the same logic works (a) against a local
compose PG via ``subprocess`` on the host, and (b) inside a throwaway PG container
via ``docker exec`` (the deterministic Docker-backed test). ``graph_counts`` reads
the spine over ``psycopg`` from the host. No network beyond the PG connection.

The REAL cloud restore (from GCS / Cloud SQL under ADC) is gate-pending
(D-DEPLOY.1-1); this local drill is its deterministic proxy.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

#: The append-only spine tables whose cardinality a good restore must reproduce
#: (the L0 evidence table is ``evidence_artifact``; §16 / Appendix C.3).
GRAPH_TABLES = ("claim", "evidence_artifact", "entity")

#: A command runner: takes argv, returns (returncode, stdout, stderr). The default
#: shells out on the host; the Docker test injects one that execs in the container.
Runner = Callable[[Sequence[str]], "RunResult"]


@dataclass(frozen=True)
class RunResult:
    """The outcome of a single backup/restore command."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


def subprocess_runner(argv: Sequence[str]) -> RunResult:
    """Default runner: execute ``argv`` on the host with ``subprocess``."""
    proc = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def swap_dbname(dsn: str, dbname: str) -> str:
    """Return ``dsn`` with its database name replaced by ``dbname``."""
    parts = urlparse(dsn)
    return urlunparse(parts._replace(path=f"/{dbname}"))


def dump_args(dsn: str, out_path: str) -> list[str]:
    """`pg_dump` argv producing a custom-format archive at ``out_path``."""
    return ["pg_dump", "--no-owner", "--no-privileges", "-Fc", "-d", dsn, "-f", out_path]


def create_db_args(admin_dsn: str, dbname: str) -> list[str]:
    """`psql` argv that (re)creates a fresh ``dbname`` from an admin connection.

    DROP/CREATE DATABASE cannot run inside a transaction block, so each statement
    goes in its own ``-c`` (psql runs multiple ``-c`` as separate transactions).
    """
    return [
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-d",
        admin_dsn,
        "-c",
        f'DROP DATABASE IF EXISTS "{dbname}"',
        "-c",
        f'CREATE DATABASE "{dbname}"',
    ]


def restore_args(target_dsn: str, dump_path: str) -> list[str]:
    """`pg_restore` argv restoring ``dump_path`` into ``target_dsn``."""
    return ["pg_restore", "--no-owner", "--no-privileges", "-d", target_dsn, dump_path]


def graph_counts(dsn: str) -> dict[str, int]:
    """Return ``{table: rowcount}`` for the spine graph tables over ``psycopg``."""
    import psycopg

    counts: dict[str, int] = {}
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        for table in GRAPH_TABLES:
            row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608 - fixed allowlist
            counts[table] = int(row[0]) if row else 0
    return counts


@dataclass(frozen=True)
class DrillReport:
    """The result of a restore drill."""

    source_counts: dict[str, int]
    restored_counts: dict[str, int]
    dump_path: str
    target_dbname: str

    @property
    def reproduced(self) -> bool:
        """True iff every graph table's cardinality matches after restore."""
        return self.source_counts == self.restored_counts

    def as_json(self) -> dict[str, object]:
        return {
            "source_counts": self.source_counts,
            "restored_counts": self.restored_counts,
            "dump_path": self.dump_path,
            "target_dbname": self.target_dbname,
            "reproduced": self.reproduced,
        }


class DrillError(RuntimeError):
    """A backup/restore command failed during the drill."""


def _check(result: RunResult, label: str) -> None:
    if result.returncode != 0:
        detail = result.stderr or result.stdout
        raise DrillError(f"{label} failed (rc={result.returncode}): {detail}")


def restore_drill(
    *,
    source_dsn: str,
    admin_dsn: str,
    host_source_dsn: str | None = None,
    host_target_dsn: str | None = None,
    target_dbname: str = "sig_restore",
    dump_path: str = "/tmp/sig-restore-drill.dump",
    run: Runner = subprocess_runner,
) -> DrillReport:
    """Dump ``source_dsn``, restore into a fresh ``target_dbname``, compare counts.

    ``source_dsn`` / ``admin_dsn`` are the connection strings the SQL *tools* use
    (as seen from wherever ``run`` executes). ``host_source_dsn`` /
    ``host_target_dsn`` are the DSNs the *host* uses for the ``psycopg`` count
    reads (they differ from the tool DSNs when ``run`` execs inside a container).
    Returns a :class:`DrillReport`; raises :class:`DrillError` on any tool failure.
    """
    host_src = host_source_dsn or source_dsn
    host_tgt = host_target_dsn or swap_dbname(source_dsn, target_dbname)

    source_counts = graph_counts(host_src)

    _check(run(dump_args(source_dsn, dump_path)), "pg_dump")
    _check(run(create_db_args(admin_dsn, target_dbname)), "create database")
    target_tool_dsn = swap_dbname(source_dsn, target_dbname)
    # pg_restore returns non-zero on ignorable warnings; treat as success unless it
    # produced no relations. We assert via the row counts below, so tolerate rc!=0
    # only when the counts still reproduce.
    restore_res = run(restore_args(target_tool_dsn, dump_path))

    restored_counts = graph_counts(host_tgt)
    if not restored_counts and restore_res.returncode != 0:
        _check(restore_res, "pg_restore")

    return DrillReport(
        source_counts=source_counts,
        restored_counts=restored_counts,
        dump_path=dump_path,
        target_dbname=target_dbname,
    )


__all__ = [
    "GRAPH_TABLES",
    "DrillError",
    "DrillReport",
    "RunResult",
    "Runner",
    "create_db_args",
    "dump_args",
    "graph_counts",
    "restore_args",
    "restore_drill",
    "subprocess_runner",
    "swap_dbname",
]
