# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `parsing` stage (SIG-ENG-013).

Sub-commands expose the model-assisted-extraction boundary (§25):

* ``extract PATH``   — run the extraction scaffolding over a JSON job (capture text,
  model provenance, and candidate items) and print the R6/``PROPOSED`` proposals, or the
  rejection when a span is not present in the capture (SIG-LLM-003/004/005).
* ``sampling``       — list the per-extraction-type review sampling rate and gold-accuracy
  floor; with ``--type`` and ``--accuracy`` report whether the type is demoted to
  human-only (SIG-LLM-006).

With no sub-command it prints help and exits 0 (the SIG-ENG-013 convention).
"""

from __future__ import annotations

import argparse
import json

from . import __version__
from .extraction import (
    EXTRACTION_SCHEMA_VERSION,
    ExtractionRejected,
    ModelExtraction,
    deterministic_parameters,
    evaluate_demotion,
    extract_claims,
    load_policies,
)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `parsing` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-parsing",
        description="SIG parsing stage: the model-assisted-extraction boundary (§25).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    extract = sub.add_parser("extract", help="run model-assisted extraction over a JSON job")
    extract.add_argument(
        "path",
        help=(
            "a JSON object: {capture_text, model_id, prompt_version, extraction_type, "
            "parameters?, items:[{subject,predicate,value,span:{text,start,end,locator}}]}"
        ),
    )

    sampling = sub.add_parser("sampling", help="show per-extraction-type review sampling policy")
    sampling.add_argument("--type", dest="extraction_type", help="restrict to one extraction type")
    sampling.add_argument(
        "--accuracy",
        type=float,
        help="a measured gold accuracy; with --type, report the demotion decision",
    )
    return parser


def _run_extract(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        job = json.load(fh)
    parameters = job.get("parameters") or deterministic_parameters()
    try:
        extraction = ModelExtraction(
            model_id=str(job["model_id"]),
            prompt_version=str(job["prompt_version"]),
            extraction_type=str(job["extraction_type"]),
            parameters=parameters,
        )
        claims = extract_claims(
            job.get("items", []),
            capture_text=str(job["capture_text"]),
            extraction=extraction,
        )
    except ExtractionRejected as exc:
        print(f"rejected: {exc}")
        return 2
    if not claims:
        print("(no candidate claims in the job)")
        return 0
    print(
        f"{len(claims)} PROPOSED claim(s) from model {extraction.model_id} "
        f"prompt {extraction.prompt_version} (schema v{EXTRACTION_SCHEMA_VERSION}):"
    )
    for claim in claims:
        print(
            f"  {claim.source_reliability}/{claim.claim_status}  "
            f"{claim.subject} {claim.predicate} {claim.value!r}  "
            f"span[{claim.span.start}:{claim.span.end}]={claim.span.text!r}  "
            f"writes_to_graph={claim.writes_to_graph}"
        )
    return 0


def _run_sampling(extraction_type: str | None, accuracy: float | None) -> int:
    policies = load_policies()
    if extraction_type is not None:
        policy = policies.get(extraction_type)
        if policy is None:
            print(f"unknown extraction type: {extraction_type}")
            return 2
        if accuracy is not None:
            decided = evaluate_demotion(policy, accuracy)
            state = "human-only (demoted)" if decided.human_only else "model-assisted"
            print(
                f"{policy.extraction_type}: measured {accuracy:.3f} vs floor "
                f"{policy.accuracy_threshold:.3f} → {state}"
            )
            return 0
        policies = {extraction_type: policy}
    for policy in policies.values():
        print(
            f"{policy.extraction_type}: review_sample_rate={policy.review_sample_rate:.2f} "
            f"accuracy_threshold={policy.accuracy_threshold:.2f} human_only={policy.human_only}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `parsing` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        return _run_extract(args.path)
    if args.command == "sampling":
        return _run_sampling(args.extraction_type, args.accuracy)

    parser.print_help()
    return 0
