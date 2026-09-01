# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `parsing` stage (SIG-ENG-013).

Sub-commands expose the layered parsing stack (§24) and the model-assisted-extraction
boundary (§25):

* ``classify PATH``  — classify a file before parsing and print the verdict; a mixed-format
  ZIP is classified **per member** (SIG-PARSE-002), and each verdict names the cheapest
  sufficient layer (SIG-PARSE-001).
* ``layers``         — list the seven extraction layers, cheapest first, with the method
  string recorded on the extraction (SIG-PARSE-001).
* ``reason KIND TEXT`` — normalize a reason field through the versioned mapping, retaining
  the raw text and stamping the mapping version (SIG-PARSE-005/006); ``--reverse CODE``
  instead lists the raw variants a canonical code maps from (the reversible view).
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
import zipfile

from . import __version__
from .classification import classify, classify_archive
from .extraction import (
    EXTRACTION_SCHEMA_VERSION,
    ExtractionRejected,
    ModelExtraction,
    deterministic_parameters,
    evaluate_demotion,
    extract_claims,
    load_policies,
)
from .layers import LAYER_ORDER
from .reason_codes import ReasonKind, load_reason_mapping, normalize_reason


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `parsing` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-parsing",
        description="SIG parsing stage: the model-assisted-extraction boundary (§25).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    classify_cmd = sub.add_parser("classify", help="classify a file before parsing (§24.1)")
    classify_cmd.add_argument("path", help="a file to classify; a ZIP is classified per member")

    sub.add_parser("layers", help="list the seven extraction layers, cheapest first (§24.1)")

    reason = sub.add_parser("reason", help="normalize a reason field through the versioned mapping")
    reason.add_argument(
        "kind",
        choices=[k.value for k in ReasonKind],
        help="the form the reason arrived in (a dropdown value is a stronger signal)",
    )
    reason.add_argument("text", nargs="?", help="the raw reason text to normalize")
    reason.add_argument(
        "--reverse",
        metavar="CODE",
        help="instead of normalizing, list the raw variants this canonical code maps from",
    )

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


def _run_classify(path: str) -> int:
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        archive = classify_archive(path, data)
    except zipfile.BadZipFile:
        archive = None
    if archive is not None:
        print(f"{path}: ZIP archive, {len(archive.members)} member(s) (SIG-PARSE-002):")
        for member in archive.members:
            layer = member.recommended_layer
            method = layer.method if layer is not None else "-"
            print(
                f"  {member.filename}: {member.file_format.value} → {method}  "
                f"scanned={member.scanned} encrypted={member.encrypted} "
                f"merged_headers={member.merged_headers} multi_sheet={member.multi_sheet}"
            )
        return 0
    verdict = classify(path, data)
    layer = verdict.recommended_layer
    method = layer.method if layer is not None else "-"
    print(
        f"{path}: {verdict.file_format.value} → {method}  "
        f"scanned={verdict.scanned} encrypted={verdict.encrypted} "
        f"merged_headers={verdict.merged_headers} multi_sheet={verdict.multi_sheet}"
    )
    for note in verdict.notes:
        print(f"    - {note}")
    return 0


def _run_layers() -> int:
    print("The seven extraction layers, cheapest first (§24.1, SIG-PARSE-001):")
    for layer in LAYER_ORDER:
        print(f"  {layer.cost}  {layer.method}")
    return 0


def _run_reason(kind_value: str, text: str | None, reverse: str | None) -> int:
    kind = ReasonKind(kind_value)
    if reverse is not None:
        mapping = load_reason_mapping()
        variants = mapping.raw_variants(reverse, kind)
        if not variants:
            print(f"no {kind.value} variants map to {reverse!r} (mapping v{mapping.version})")
            return 2
        print(f"{reverse} ({kind.value}, mapping v{mapping.version}) maps from:")
        for variant in variants:
            print(f"  {variant!r}")
        return 0
    if text is None:
        print("reason: TEXT is required unless --reverse is given")
        return 2
    result = normalize_reason(text, kind)
    code = result.code if result.matched else "(unmapped)"
    print(
        f"{text!r} [{result.reason_kind.value}] → {code}  "
        f"signal={result.signal_strength.value}  mapping v{result.mapping_version}  "
        f"raw_value={result.raw_text!r}"
    )
    return 0


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

    if args.command == "classify":
        return _run_classify(args.path)
    if args.command == "layers":
        return _run_layers()
    if args.command == "reason":
        return _run_reason(args.kind, args.text, args.reverse)
    if args.command == "extract":
        return _run_extract(args.path)
    if args.command == "sampling":
        return _run_sampling(args.extraction_type, args.accuracy)

    parser.print_help()
    return 0
