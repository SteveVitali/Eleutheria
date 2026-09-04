# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Parser-drift defences: committed fixtures and a live-source canary (§24.3).

Upstream sources change shape without warning, and a parser that keeps running against a
changed shape produces silent garbage — R11 names this a top-5 operational risk. Two
complementary mechanisms defend against it, and this module owns the reusable core of both:

* **Committed fixtures (SIG-PARSE-007).** Every parser ships a real captured input paired
  with its expected output. :func:`assert_no_drift` re-runs the parser over each fixture and
  fails (:class:`ParserDrift`) on any mismatch — so an upstream redesign, or a careless edit
  to the parser, **fails a test** instead of quietly changing what SIG extracts. Fixtures
  pin *known* inputs and keep passing forever.

* **A nightly canary (SIG-PARSE-008).** Fixtures alone cannot catch an upstream that changes
  *after* the fixture was captured — they keep passing on the old bytes. The canary is the
  complement: it runs each parser's structural expectations against a **live** sample on a
  cadence and **alerts** when the structure drifts. :func:`structural_findings` is that
  check's deterministic core (the nightly job is a thin fetch-and-call wrapper), and it
  **alerts** — returns findings — rather than silently dropping the changed data.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ParserDrift",
    "FixtureCase",
    "FixtureResult",
    "run_fixture",
    "check_fixtures",
    "assert_no_drift",
    "StructuralExpectation",
    "CanaryReport",
    "structural_findings",
    "run_canary",
    "EACH",
]

#: A path segment meaning "every element of this list" (SIG-PARSE-008 canary paths).
EACH = "[]"


class ParserDrift(AssertionError):
    """A parser's output diverged from its committed fixture (SIG-PARSE-007).

    Raised by :func:`assert_no_drift`. An :class:`AssertionError` so a fixture mismatch fails
    a test loudly — the whole point is that an upstream redesign or a careless parser edit
    cannot pass CI silently.
    """


# --- committed fixtures (SIG-PARSE-007) ---------------------------------------


@dataclass(frozen=True)
class FixtureCase:
    """A committed parser fixture: a real captured input and its expected output.

    ``input_bytes`` is the captured source input (e.g. a snapshot committed under
    ``tests/parsing/fixtures``); ``expected`` is what the parser must produce from it. The
    pair is the regression pin SIG-PARSE-007 requires.
    """

    name: str
    input_bytes: bytes
    expected: Any
    media_type: str = "application/octet-stream"


@dataclass(frozen=True)
class FixtureResult:
    """The outcome of running one parser over one fixture."""

    name: str
    passed: bool
    expected: Any = None
    actual: Any = None

    def failure_line(self) -> str:
        """A one-line description of the mismatch (empty when it passed)."""
        if self.passed:
            return ""
        return f"{self.name}: expected {self.expected!r} but parser produced {self.actual!r}"


def run_fixture(parse: Callable[[bytes], Any], case: FixtureCase) -> FixtureResult:
    """Run ``parse`` over one fixture's input and compare to its expected output."""
    actual = parse(case.input_bytes)
    return FixtureResult(
        name=case.name, passed=actual == case.expected, expected=case.expected, actual=actual
    )


def check_fixtures(
    parse: Callable[[bytes], Any], cases: Sequence[FixtureCase]
) -> list[FixtureResult]:
    """Run ``parse`` over every fixture and return one :class:`FixtureResult` each."""
    return [run_fixture(parse, case) for case in cases]


def assert_no_drift(parse: Callable[[bytes], Any], cases: Sequence[FixtureCase]) -> None:
    """Fail (:class:`ParserDrift`) if ``parse`` diverges from any committed fixture.

    The assertion SIG-PARSE-007 is built on: a parser change that alters what SIG extracts
    from a known input fails here rather than shipping. Reports **every** mismatch, not just
    the first, so a redesign sees its full blast radius.
    """
    results = check_fixtures(parse, cases)
    failures = [r.failure_line() for r in results if not r.passed]
    if failures:
        joined = "\n  ".join(failures)
        raise ParserDrift(f"{len(failures)} parser fixture(s) drifted:\n  {joined}")


# --- live-source canary (SIG-PARSE-008) ---------------------------------------


@dataclass(frozen=True)
class StructuralExpectation:
    """One structural expectation a live sample must satisfy, else the canary alerts.

    ``path`` is a tuple of keys into a parsed sample; the sentinel :data:`EACH` (``"[]"``)
    means "for every element of the list here". ``description`` is the human-readable name
    of the expectation, quoted in the alert when it is violated. The canary deliberately
    checks *structure* — the keys/shape the parser depends on — not values: a new field
    value (e.g. an unknown device kind) is handled as an unmapped value plus a research
    task, never treated as drift.
    """

    description: str
    path: tuple[str, ...]

    def violations(self, sample: Any) -> list[str]:
        """The findings this expectation raises against ``sample`` (empty = satisfied)."""
        return [] if _path_present(sample, self.path) else [self.description]


@dataclass(frozen=True)
class CanaryReport:
    """The result of running a parser's canary against a live sample (SIG-PARSE-008).

    ``findings`` names each structural expectation the sample violated; an **empty** list is
    a clean run. :attr:`alerted` is what the nightly job checks to decide whether to raise an
    alert — the canary alerts, it never silently drops the changed data.
    """

    parser: str
    findings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def alerted(self) -> bool:
        """Whether the canary found structural drift worth alerting on."""
        return bool(self.findings)


def structural_findings(sample: Any, expectations: Sequence[StructuralExpectation]) -> list[str]:
    """The structural-drift findings for ``sample`` (SIG-PARSE-008 deterministic core).

    Returns one finding per violated expectation; an empty list means no drift. This is a
    pure function of the parsed sample, so the nightly job is a thin fetch-and-call wrapper
    and the check is testable against committed fixtures.
    """
    findings: list[str] = []
    for expectation in expectations:
        findings.extend(expectation.violations(sample))
    return findings


def run_canary(
    parser: str, sample: Any, expectations: Sequence[StructuralExpectation]
) -> CanaryReport:
    """Run ``parser``'s structural expectations against a live ``sample`` (SIG-PARSE-008)."""
    return CanaryReport(parser=parser, findings=tuple(structural_findings(sample, expectations)))


def _path_present(sample: Any, path: tuple[str, ...]) -> bool:
    """Whether ``path`` resolves in ``sample`` (``EACH`` requires it in every list element)."""
    if not path:
        return True
    head, rest = path[0], path[1:]
    if head == EACH:
        if not isinstance(sample, (list, tuple)):
            return False
        return all(_path_present(item, rest) for item in sample)
    if not isinstance(sample, Mapping) or head not in sample:
        return False
    return _path_present(sample[head], rest)
