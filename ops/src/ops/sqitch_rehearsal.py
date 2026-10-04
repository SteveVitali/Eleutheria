# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The L44–52 sqitch deploy rehearsal on a drill clone (P34.24b / SIG-ENG-045).

Before anyone deploys ``db/sqitch.plan`` L44–52 (the Round-10 schema set,
extended to the plan tip by P34.24a's ``@r11-sqitch-hygiene`` rework and
P34.25's ``public_read_allowlist`` grants change) to production, P34.46's
go/no-go needs measured numbers: the ``ACCESS EXCLUSIVE`` hold on
``claim_evidence``, per-change wall time, temporary disk and index-build
time. This module is the measurement half of
``ops/gcp/sqitch-rehearsal.sh`` — the shell owns gcloud/proxy/docker; this
module owns the SQL surface, the sample math and the ``sig.sqitch-rehearsal/1``
record, all unit-testable without credentials, network or Docker
(``connect`` injectable — ``ops/backup.py``'s runner pattern).

Three rules encoded here:

- **The target is name-checked.** ``assert_rehearsal_target`` delegates to
  ``cloudsql_drill.assert_drill_name`` — it refuses ``sig-pg`` outright and
  every name outside the producer shapes, tighter than the contract's
  ``sig-pg-drill-*`` wildcard so a hand-typed or truncated name fails
  closed *and* every deployable name is deletable by the same check.
- **Every query is a SELECT.** The rehearsal measures; the only mutation on
  the clone is ``sqitch deploy`` itself. ``sig-pg`` is read for the
  no-write evidence (``pg_stat_database`` counters) and never otherwise.
- **Honest bounds, not false precision.** A 250 ms poll cannot see a lock's
  exact take/release instants, so an episode's hold is reported as an
  observed window plus the sampling upper bound (window + 2 intervals);
  the containing change's deploy seconds bound it from above. Numbers the
  sampler cannot see are recorded as ``None``, never fabricated.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .cloudsql_drill import assert_drill_name

#: The rehearsal record schema id.
REHEARSAL_SCHEMA = "sig.sqitch-rehearsal/1"

#: The plan's protected span (C-10) — recorded by sha256, never touched.
PROTECTED_PLAN_LINES = (44, 52)

#: The FEA-07 lock ceiling the rehearsal deploy sets on its own session
#: (P34.46's go/no-go: the ACCESS EXCLUSIVE hold on claim_evidence must be
#: ≤ 20 min and ≤ 2× this measurement). Setting it bounds the rehearsal the
#: same way the production deploy is bounded — a lock that would exceed the
#: ceiling aborts the change rather than passing silently.
LOCK_TIMEOUT_MS = 1_200_000  # 20 minutes

#: Default sampler cadence — short enough to see a multi-second rewrite,
#: light enough that the probe itself cannot skew a single-vCPU clone.
DEFAULT_SAMPLE_INTERVAL_S = 0.25


def assert_rehearsal_target(name: str) -> str:
    """Return ``name`` iff it is a drill instance; refuse anything else.

    Delegates to :func:`ops.cloudsql_drill.assert_drill_name`, which refuses
    ``sig-pg`` outright and every name outside ``sig-pg-drill(-b|-l44)?-<stamp>``
    — stricter than the contract's "refuses `sig-pg` and any name outside
    ``sig-pg-drill-*``" so every name the deploy can target is a name the
    name-checked delete accepts too.
    """
    return assert_drill_name(name)


# ---- read-only SQL -------------------------------------------------------------
# Every statement this module issues is a SELECT. A unit test greps this module
# for write verbs so the measurement surface can never grow a mutation.

SQITCH_TIP_SQL = (
    "SELECT change, change_id, planned_at, committed_at "
    "FROM sqitch.changes ORDER BY committed_at, change"
)

#: Database-level counters — temp disk usage and the write counters the
#: "sig-pg shows no write" leg compares pre/post on the SOURCE.
DB_STATS_SQL = (
    "SELECT temp_files, temp_bytes, xact_commit, xact_rollback, "
    "tup_returned, tup_fetched, tup_inserted, tup_updated, tup_deleted "
    "FROM pg_stat_database WHERE datname = current_database()"
)

DATABASE_SIZE_SQL = "SELECT pg_database_size(current_database())"

#: Per-relation sizes for every user table (the honest per-table view; the
#: record annotates the tables the deploy set rewrites).
RELATION_SIZES_SQL = (
    "SELECT c.relname, "
    "  pg_total_relation_size(c.oid), pg_relation_size(c.oid), "
    "  pg_indexes_size(c.oid), COALESCE(s.n_live_tup, 0) "
    "FROM pg_class c "
    "LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid "
    "WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r' "
    "ORDER BY c.relname"
)

#: ACCESS EXCLUSIVE relation locks — the measurement the whole rehearsal
#: exists for. Joined to pg_stat_activity so the holding backend's query
#: head attributes the lock to the deploying change (the deploy runs as the
#: same `sig` user, so its query text is visible).
LOCK_SAMPLE_SQL = (
    "SELECT l.pid, l.mode, l.granted, c.relname, "
    "  a.query_start, a.state, left(a.query, 200) AS query "
    "FROM pg_locks l "
    "JOIN pg_class c ON c.oid = l.relation "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "LEFT JOIN pg_stat_activity a ON a.pid = l.pid AND a.datname = l.database "
    "WHERE l.locktype = 'relation' AND l.mode = 'AccessExclusiveLock' "
    "  AND n.nspname NOT IN ('pg_catalog', 'information_schema')"
)

#: In-flight index builds (the L44–52 set includes
#: claim_evidence_establishing_idx and claim_qualifier_pk). PG12+ progress
#: view; fields the role cannot see arrive NULL and are recorded as such.
INDEX_PROGRESS_SQL = (
    "SELECT p.pid, p.phase, "
    "  t.relname AS table_rel, i.relname AS index_rel, "
    "  p.blocks_done, p.blocks_total, p.tuples_done, p.tuples_total "
    "FROM pg_stat_progress_create_index p "
    "JOIN pg_class t ON t.oid = p.relid "
    "JOIN pg_class i ON i.oid = p.index_relid"
)


class _Conn(Protocol):
    """The sliver of ``psycopg.Connection`` the rehearsal uses (injectable)."""

    def execute(self, query: str, params: tuple = ()) -> Any: ...

    def __enter__(self) -> _Conn: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Any: ...


ConnectFactory = Callable[[str], _Conn]


def _connect(dsn: str) -> _Conn:
    import psycopg

    return psycopg.connect(dsn, connect_timeout=15, autocommit=True)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_instant(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _scalar(conn: _Conn, sql: str, params: tuple = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def sqitch_tip(conn: _Conn) -> list[dict[str, str | None]]:
    """The ordered ``sqitch.changes`` registry — the deployed head, verbatim.

    A database without the sqitch schema (never deployed) reads as ``[]``
    rather than erroring — a missing registry is itself recorded state."""
    try:
        rows = conn.execute(SQITCH_TIP_SQL).fetchall()
    except Exception:  # noqa: BLE001 — undefined_table on a virgin DB is a state, not a crash
        return []
    return [
        {
            "change": str(c),
            "change_id": str(i),
            "planned_at": _iso(p),
            "committed_at": _iso(m),
        }
        for c, i, p, m in rows
    ]


def tip_sha256(tip: Sequence[Mapping[str, Any]]) -> str:
    """sha256 over the ordered deployed change ids — the head fingerprint."""
    payload = "\n".join(str(r.get("change_id", "")) for r in tip)
    return hashlib.sha256(payload.encode()).hexdigest()


def db_stats(conn: _Conn) -> dict[str, int]:
    """The ``pg_stat_database`` row for the current database."""
    row = conn.execute(DB_STATS_SQL).fetchone()
    keys = (
        "temp_files",
        "temp_bytes",
        "xact_commit",
        "xact_rollback",
        "tup_returned",
        "tup_fetched",
        "tup_inserted",
        "tup_updated",
        "tup_deleted",
    )
    return {k: int(v or 0) for k, v in zip(keys, row or (), strict=True)}


def relation_sizes(conn: _Conn) -> dict[str, dict[str, int]]:
    """``{table: {total_bytes, table_bytes, index_bytes, n_live_tup}}``."""
    rows = conn.execute(RELATION_SIZES_SQL).fetchall()
    return {
        str(name): {
            "total_bytes": int(total),
            "table_bytes": int(rel),
            "index_bytes": int(idx),
            "n_live_tup": int(tup),
        }
        for name, total, rel, idx, tup in rows
    }


def snapshot(conn: _Conn) -> dict[str, Any]:
    """A read-only point-in-time capture: deployed head + sizes + counters."""
    tip = sqitch_tip(conn)
    return {
        "at": _iso(datetime.now(UTC)),
        "sqitch_tip": tip,
        "sqitch_tip_sha256": tip_sha256(tip),
        "sqitch_changes": len(tip),
        "sqitch_head_change": str(tip[-1]["change"]) if tip else None,
        "db_stats": db_stats(conn),
        "database_bytes": int(_scalar(conn, DATABASE_SIZE_SQL) or 0),
        "relations": relation_sizes(conn),
    }


def sample_once(conn: _Conn) -> dict[str, Any]:
    """One sampler tick — SELECTs only."""
    locks = conn.execute(LOCK_SAMPLE_SQL).fetchall()
    indexes = conn.execute(INDEX_PROGRESS_SQL).fetchall()
    stats = db_stats(conn)
    return {
        "at": _iso(datetime.now(UTC)),
        "locks": [
            {
                "pid": int(pid),
                "mode": str(mode),
                "granted": bool(granted),
                "relation": str(rel),
                "query_start": _iso(qs),
                "state": str(state) if state is not None else None,
                "query": str(q) if q is not None else None,
            }
            for pid, mode, granted, rel, qs, state, q in locks
        ],
        "index_progress": [
            {
                "pid": int(pid),
                "phase": str(phase),
                "table": str(trel),
                "index": str(irel),
                "blocks_done": int(bd) if bd is not None else None,
                "blocks_total": int(bt) if bt is not None else None,
                "tuples_done": int(td) if td is not None else None,
                "tuples_total": int(tt) if tt is not None else None,
            }
            for pid, phase, trel, irel, bd, bt, td, tt in indexes
        ],
        "temp_files": stats["temp_files"],
        "temp_bytes": stats["temp_bytes"],
    }


def sample_loop(
    dsn: str,
    out_path: str | Path,
    stop_file: str | Path,
    *,
    interval_s: float = DEFAULT_SAMPLE_INTERVAL_S,
    deadline_s: float = 4 * 3600,
    connect: ConnectFactory | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Append :func:`sample_once` JSON lines until ``stop_file`` exists.

    Returns the number of samples written. A query failure is recorded as an
    ``{"at": …, "error": …}`` line and the connection is rebuilt — a
    transient proxy wobble degrades the sample density, never the rehearsal.
    The deadline backstops a forgotten stop file.
    """
    connect = connect or _connect
    out, stop = Path(out_path), Path(stop_file)
    deadline = time.monotonic() + deadline_s
    n = 0
    conn = connect(dsn)
    with out.open("a", encoding="utf-8") as fh:
        while not stop.exists() and time.monotonic() < deadline:
            try:
                sample = sample_once(conn)
            except Exception as exc:  # noqa: BLE001 — record + reconnect, never crash the leg
                sample = {"at": _iso(datetime.now(UTC)), "error": f"{type(exc).__name__}: {exc}"}
                try:
                    conn = connect(dsn)
                except Exception:  # noqa: BLE001 — next tick retries
                    pass
            fh.write(json.dumps(sample, sort_keys=True) + "\n")
            fh.flush()
            n += 1
            sleep(interval_s)
    try:
        conn.__exit__(None, None, None)
    except Exception:  # noqa: BLE001
        pass
    return n


# ---- deploy-log timing ----------------------------------------------------------

_DEPLOY_RE = re.compile(r"^Deploying\s+(?P<change>\S+)")


def parse_deploy_log(lines: Iterable[str]) -> dict[str, Any]:
    """Per-change wall times from a timestamped ``sqitch deploy`` log.

    The shell stamps every sqitch output line ``<ISO>\t<text>``; each
    ``Deploying <change>`` marks that change's start and the previous
    change's end. The last change ends at the last stamped line. Changes
    are identified by their sqitch output, not the plan file, so a skipped
    or failed change is visible as absent.
    """
    events: list[tuple[datetime, str]] = []
    last_ts: datetime | None = None
    for line in lines:
        line = line.rstrip("\n")
        if "\t" not in line:
            continue
        stamp, text = line.split("\t", 1)
        ts = _parse_instant(stamp.strip())
        if ts is None:
            continue
        last_ts = ts
        match = _DEPLOY_RE.match(text.strip())
        if match:
            events.append((ts, match.group("change")))
    changes: list[dict[str, Any]] = []
    for i, (ts, change) in enumerate(events):
        end = events[i + 1][0] if i + 1 < len(events) else last_ts
        changes.append(
            {
                "change": change,
                "started_at": _iso(ts),
                "ended_at": _iso(end) if end is not None else None,
                "seconds": round((end - ts).total_seconds(), 3) if end else None,
            }
        )
    started = events[0][0] if events else None
    ended = last_ts if events else None
    return {
        "started_at": _iso(started),
        "ended_at": _iso(ended),
        "wall_seconds": round((ended - started).total_seconds(), 3)
        if started is not None and ended is not None
        else None,
        "changes": changes,
    }


# ---- lock-episode math ------------------------------------------------------------


def lock_episodes(samples: Sequence[Mapping[str, Any]], interval_s: float) -> list[dict[str, Any]]:
    """Group sampled AccessExclusiveLock rows into hold episodes.

    Sightings of ``(pid, mode, relation)`` belong to one episode while their
    sample gap stays ≤ ``2 * interval_s`` — a missed tick doesn't split an
    episode, a gap longer than the tolerance does (a real release-and-retake
    or a pid that moved on).

    ``observed_s`` is a floor — the lock demonstrably spanned the sampled
    window. ``upper_bound_s`` adds one poll interval on each side. A hold
    that started and ended between two ticks is invisible to polling; the
    containing change's deploy seconds bound every hold from above, which
    is why the record keeps both.
    """
    gap_s = 2 * interval_s
    open_eps: dict[tuple[int, str, str], dict[str, Any]] = {}
    closed: list[dict[str, Any]] = []
    for sample in samples:
        at = _parse_instant(sample.get("at"))
        if at is None:
            continue
        seen: set[tuple[int, str, str]] = set()
        for lock in sample.get("locks") or []:
            key = (int(lock["pid"]), str(lock["mode"]), str(lock["relation"]))
            seen.add(key)
            ep = open_eps.get(key)
            if ep is None or (at - ep["_last"]).total_seconds() > gap_s:
                if ep is not None:
                    closed.append(ep)
                ep = {
                    "pid": key[0],
                    "relation": key[2],
                    "_first": at,
                    "_last": at,
                    "samples": 0,
                    "query": None,
                    "states": [],
                }
                open_eps[key] = ep
            ep["_last"] = at
            ep["samples"] += 1
            granted = str(bool(lock.get("granted"))).lower()
            if not ep["states"] or ep["states"][-1] != granted:
                ep["states"].append(granted)
            if not ep["query"] and lock.get("query"):
                ep["query"] = str(lock["query"])
        for key, ep in list(open_eps.items()):
            if key not in seen and (at - ep["_last"]).total_seconds() > gap_s:
                closed.append(ep)
                del open_eps[key]
    closed.extend(open_eps.values())
    out: list[dict[str, Any]] = []
    for ep in sorted(closed, key=lambda e: e["_first"]):
        observed = (ep["_last"] - ep["_first"]).total_seconds()
        out.append(
            {
                "pid": ep["pid"],
                "relation": ep["relation"],
                "first_seen": _iso(ep["_first"]),
                "last_seen": _iso(ep["_last"]),
                "samples": ep["samples"],
                "states": ep["states"],
                "query": ep["query"],
                "observed_s": round(observed, 3),
                "upper_bound_s": round(observed + 2 * interval_s, 3),
            }
        )
    return out


def lock_summary(
    episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Per-relation + headline rollups of the episode list."""
    by_relation: dict[str, dict[str, Any]] = {}
    for ep in episodes:
        rel = str(ep["relation"])
        agg = by_relation.setdefault(
            rel, {"episodes": 0, "max_observed_s": 0.0, "max_upper_bound_s": 0.0}
        )
        agg["episodes"] += 1
        agg["max_observed_s"] = max(agg["max_observed_s"], float(ep["observed_s"]))
        agg["max_upper_bound_s"] = max(agg["max_upper_bound_s"], float(ep["upper_bound_s"]))
    return {
        "n_episodes": len(episodes),
        "by_relation": dict(sorted(by_relation.items())),
        "claim_evidence": by_relation.get(
            "claim_evidence",
            {"episodes": 0, "max_observed_s": 0.0, "max_upper_bound_s": 0.0},
        ),
    }


def registry_change_timings(
    pre_tip: Sequence[Mapping[str, Any]],
    post_tip: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Per-change durations the registry itself recorded.

    The deploy's new changes are exactly ``post_tip`` minus ``pre_tip`` (by
    ``change_id`` — sqitch is append-only, so a redeploy never rewrites a
    row). Each new change's ``committed_at`` stamps when it finished; its
    duration runs from the previous committed change's stamp. The FIRST new
    change's ``seconds`` is ``None`` — its predecessor is the pre-deploy
    head whose stamp could be days old; the stamped deploy log bounds that
    one instead.
    """
    pre_ids = {str(r.get("change_id")) for r in pre_tip}
    new = [r for r in post_tip if str(r.get("change_id")) not in pre_ids]
    ordered = list(post_tip)
    out: list[dict[str, Any]] = []
    for row in new:
        idx = ordered.index(row)
        prev_at = _parse_instant(ordered[idx - 1].get("committed_at")) if idx else None
        this_at = _parse_instant(row.get("committed_at"))
        seconds = None
        if prev_at is not None and this_at is not None and idx:
            if str(ordered[idx - 1].get("change_id")) in pre_ids:
                # the first new change — its start is the deploy's start,
                # not the predecessor's stamp (which predates the rehearsal)
                seconds = None
            else:
                seconds = round((this_at - prev_at).total_seconds(), 3)
        out.append(
            {
                "change": str(row.get("change")),
                "committed_at": _iso(this_at),
                "seconds": seconds,
            }
        )
    return out


# ---- static change flags ----------------------------------------------------------

_FLAG_RES = {
    "create_index": re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b", re.IGNORECASE),
    "alter_table": re.compile(r"\bALTER\s+TABLE\b", re.IGNORECASE),
    "update_rows": re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
}


def deploy_change_flags(deploy_sql: str) -> dict[str, bool]:
    """Static flags for one deploy script — which heavy shapes it carries."""
    return {name: bool(rx.search(deploy_sql)) for name, rx in _FLAG_RES.items()}


# ---- C-10 plan-line hashes --------------------------------------------------------


def plan_line_hashes(plan_text: str) -> dict[str, Any]:
    """sha256 of the whole plan and of lines 44–52 exactly as stamped (C-10)."""
    lines = plan_text.splitlines(keepends=True)
    lo, hi = PROTECTED_PLAN_LINES
    span = "".join(lines[lo - 1 : hi])
    return {
        "plan_sha256": hashlib.sha256(plan_text.encode()).hexdigest(),
        "plan_l44_52_sha256": hashlib.sha256(span.encode()).hexdigest(),
        "plan_l44_52_lines": f"{lo}-{hi}",
        "plan_tip_line": len(lines),
    }


# ---- the record ---------------------------------------------------------------------


def build_record(
    *,
    meta: Mapping[str, Any],
    pre: Mapping[str, Any],
    post: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    deploy: Mapping[str, Any],
    verify: Mapping[str, Any] | None = None,
    source: Mapping[str, Any] | None = None,
    sample_interval_s: float = DEFAULT_SAMPLE_INTERVAL_S,
) -> dict[str, Any]:
    """Assemble the ``sig.sqitch-rehearsal/1`` record from its measured parts.

    ``meta`` carries the fields the shell owns: clone_instance,
    clone_point_in_time, chain_tip_commit, plan hashes, the deploy exit
    code, clone-deletion fields and cost note. Everything derivable is
    derived here, so the shell can never hand the record a wrong number.
    """
    episodes = lock_episodes(samples, sample_interval_s)
    index_builds: dict[tuple[int, str], dict[str, Any]] = {}
    for sample in samples:
        at = _parse_instant(sample.get("at"))
        for prog in sample.get("index_progress") or []:
            key = (int(prog["pid"]), str(prog["index"]))
            row = index_builds.setdefault(
                key,
                {
                    "pid": int(prog["pid"]),
                    "index": str(prog["index"]),
                    "table": str(prog["table"]),
                    "first_seen": _iso(at),
                    "last_seen": _iso(at),
                    "phase_last": None,
                    "blocks_done_max": None,
                },
            )
            row["last_seen"] = _iso(at)
            row["phase_last"] = prog.get("phase")
            if prog.get("blocks_done") is not None:
                row["blocks_done_max"] = max(row["blocks_done_max"] or 0, int(prog["blocks_done"]))

    pre_stats = (pre.get("db_stats") or {}) if pre else {}
    post_stats = (post.get("db_stats") or {}) if post else {}
    temp_delta = None
    if "temp_bytes" in pre_stats and "temp_bytes" in post_stats:
        temp_delta = int(post_stats["temp_bytes"]) - int(pre_stats["temp_bytes"])

    relations_before = (pre.get("relations") or {}) if pre else {}
    relations_after = (post.get("relations") or {}) if post else {}
    size_delta = {
        t: {
            "total_bytes_before": relations_before.get(t, {}).get("total_bytes"),
            "total_bytes_after": relations_after.get(t, {}).get("total_bytes"),
        }
        for t in sorted(set(relations_before) | set(relations_after))
    }

    source_no_write = None
    if source:
        before = source.get("before") or {}
        after = source.get("after") or {}
        source_no_write = {
            "before": before,
            "after": after,
            "delta": {
                k: int(after.get(k, 0)) - int(before.get(k, 0))
                for k in sorted(set(before) | set(after))
            },
            "operations_before": source.get("operations_before"),
            "operations_after": source.get("operations_after"),
        }

    record = {
        "schema": REHEARSAL_SCHEMA,
        "at": _iso(datetime.now(UTC)),
        **{k: meta.get(k) for k in meta},
        "head_before": {
            "sqitch_changes": pre.get("sqitch_changes"),
            "sqitch_head_change": pre.get("sqitch_head_change"),
            "sqitch_tip_sha256": pre.get("sqitch_tip_sha256"),
            "sqitch_tip": pre.get("sqitch_tip"),
        },
        "head_after": {
            "sqitch_changes": post.get("sqitch_changes"),
            "sqitch_head_change": post.get("sqitch_head_change"),
            "sqitch_tip_sha256": post.get("sqitch_tip_sha256"),
            "sqitch_tip": post.get("sqitch_tip"),
        },
        "deploy": {
            **{k: deploy.get(k) for k in deploy},
            "lock_timeout_ms": LOCK_TIMEOUT_MS,
            "registry_changes": registry_change_timings(
                pre.get("sqitch_tip") or [], post.get("sqitch_tip") or []
            ),
        },
        "verify": verify,
        "locks": {
            "sample_interval_s": sample_interval_s,
            "samples": len(samples),
            "sample_errors": sum(1 for s in samples if "error" in s),
            "episodes": episodes,
            **lock_summary(episodes),
        },
        "index_builds": list(index_builds.values()),
        "temp_disk": {
            "temp_bytes_before": pre_stats.get("temp_bytes"),
            "temp_bytes_after": post_stats.get("temp_bytes"),
            "temp_bytes_delta": temp_delta,
            "temp_files_before": pre_stats.get("temp_files"),
            "temp_files_after": post_stats.get("temp_files"),
            "claim_evidence_total_bytes_before": relations_before.get("claim_evidence", {}).get(
                "total_bytes"
            ),
            "claim_evidence_total_bytes_after": relations_after.get("claim_evidence", {}).get(
                "total_bytes"
            ),
        },
        "relations": size_delta,
        "database_bytes": {
            "before": pre.get("database_bytes"),
            "after": post.get("database_bytes"),
        },
        "source_no_write": source_no_write,
        "bounds_note": (
            "lock observed_s is the sampled floor; upper_bound_s adds one "
            "sample interval on each side; the containing change's deploy "
            "seconds bound the hold from above. Numbers the sampler could "
            "not see are null, never estimated."
        ),
    }
    return record


__all__ = [
    "DATABASE_SIZE_SQL",
    "DB_STATS_SQL",
    "DEFAULT_SAMPLE_INTERVAL_S",
    "INDEX_PROGRESS_SQL",
    "LOCK_SAMPLE_SQL",
    "LOCK_TIMEOUT_MS",
    "PROTECTED_PLAN_LINES",
    "REHEARSAL_SCHEMA",
    "RELATION_SIZES_SQL",
    "SQITCH_TIP_SQL",
    "assert_rehearsal_target",
    "build_record",
    "db_stats",
    "deploy_change_flags",
    "lock_episodes",
    "lock_summary",
    "parse_deploy_log",
    "plan_line_hashes",
    "registry_change_timings",
    "relation_sizes",
    "sample_loop",
    "sample_once",
    "snapshot",
    "sqitch_tip",
    "tip_sha256",
]
