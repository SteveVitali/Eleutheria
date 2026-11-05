# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``sig-ops security-baseline`` — the scan/SBOM/cosign machinery (P37.4a,
R11-OPS-08, SIG-SEC-006, ADR-231).

The deploy path signs every pushed image digest with cosign under a Cloud KMS
asymmetric key (``gcpkms://`` — key material never leaves GCP, so no signing
secret rides an env var), and Artifact Registry's Container Analysis scans
pushed digests. This module is the offline-verifiable core:

* ``plan`` — the ordered mutation plan (APIs, KMS, scan, sign, verify).
* ``sbom`` — emit ``sbom.cdx.json`` for a lockfile (delegates to
  ``exports.sbom`` — deterministic over ``pylock.toml``).
* ``sign``/``verify`` — the cosign command sets over pinned digests; check
  mode prints, ``--apply`` executes through the injected runner and emits a
  ``sig.image-signature/1`` / ``sig.image-verify/1`` record.
* ``scan-status`` — the Container-Analysis occurrence read for a digest;
  check mode prints the query, ``--apply`` execs it.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SIGNATURE_SCHEMA = "sig.image-signature/1"
VERIFY_SCHEMA = "sig.image-verify/1"
SCAN_SCHEMA = "sig.image-scan/1"

#: Artifact Registry / Container Analysis / KMS APIs the leg enables.
REQUIRED_APIS: tuple[str, ...] = (
    "containeranalysis.googleapis.com",
    "containerscanning.googleapis.com",
    "ondemandscanning.googleapis.com",
    "cloudkms.googleapis.com",
)

KMS_RING = "sig-release"
KMS_KEY = "sig-image-sign"
KMS_ALGO = "ec-sign-p256-sha256"


def kms_key_uri(project: str, *, location: str = "global") -> str:
    return (
        f"gcpkms://projects/{project}/locations/{location}"
        f"/keyRings/{KMS_RING}/cryptoKeys/{KMS_KEY}/cryptoKeyVersions/1"
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class CommandStep:
    """One planned command line — printed in check, exec'd in apply."""

    label: str
    argv: tuple[str, ...]


def api_enable_steps(project: str) -> list[CommandStep]:
    return [
        CommandStep(
            f"enable {api}",
            ("gcloud", "services", "enable", api, "--project", project),
        )
        for api in REQUIRED_APIS
    ]


def kms_steps(project: str, *, location: str = "global") -> list[CommandStep]:
    return [
        CommandStep(
            f"keyring {KMS_RING}",
            (
                "gcloud",
                "kms",
                "keyrings",
                "create",
                KMS_RING,
                "--project",
                project,
                "--location",
                location,
            ),
        ),
        CommandStep(
            f"asymmetric signing key {KMS_KEY}",
            (
                "gcloud",
                "kms",
                "keys",
                "create",
                KMS_KEY,
                "--project",
                project,
                "--location",
                location,
                "--keyring",
                KMS_RING,
                "--purpose",
                "asymmetric-signing",
                "--default-algorithm",
                KMS_ALGO,
                "--protection-level",
                "hsm",
            ),
        ),
        CommandStep(
            "cosign public key export",
            (
                "cosign",
                "public-key",
                "--key",
                kms_key_uri(project, location=location),
            ),
        ),
    ]


def sign_steps(image: str, key_uri: str) -> list[CommandStep]:
    return [
        CommandStep("cosign sign", ("cosign", "sign", "--yes", "--key", key_uri, image)),
        CommandStep(
            "cosign verify",
            (
                "cosign",
                "verify",
                "--key",
                key_uri,
                image,
                "--insecure-ignore-tlog",
                "--insecure-ignore-sct",
            ),
        ),
    ]


def scan_steps(image: str, project: str, *, location: str) -> list[CommandStep]:
    return [
        CommandStep(
            "on-demand scan",
            (
                "gcloud",
                "artifacts",
                "docker",
                "images",
                "scan",
                image,
                "--project",
                project,
                "--location",
                location,
                "--remote",
            ),
        ),
        CommandStep(
            "scan result",
            (
                "gcloud",
                "artifacts",
                "docker",
                "images",
                "list-vulnerabilities",
                image,
                "--project",
                project,
                "--location",
                location,
            ),
        ),
    ]


Runner = Callable[[list[str]], str]


def _subprocess_runner(argv: list[str]) -> str:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)} exited {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout


def signature_record(
    image: str,
    *,
    key_uri: str,
    signer: str,
    now: str,
    verify_output: str,
) -> dict[str, Any]:
    """``sig.image-signature/1`` — the append-only signing event record."""
    return {
        "schema": SIGNATURE_SCHEMA,
        "image": image,
        "key_uri": key_uri,
        "signed_at": now,
        "signer": signer,
        "verify": "cosign verify --key <key_uri> --insecure-ignore-tlog --insecure-ignore-sct",
        "verify_output_head": verify_output.strip().splitlines()[:3],
    }


def run_steps(
    steps: list[CommandStep],
    *,
    apply_: bool,
    runner: Runner | None = None,
) -> list[str]:
    """Print-or-execute the step list; returns each step's rendered line."""
    runner = runner or _subprocess_runner
    lines: list[str] = []
    for step in steps:
        line = " ".join(step.argv)
        if apply_:
            out = runner(list(step.argv))
            lines.append(f"+ {line}\n{out.strip()}")
        else:
            lines.append(f"PLAN: {step.label}: {line}")
    return lines


def _utcnow() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops security-baseline",
        description=(
            "P37.4a (SIG-SEC-006, ADR-231): SBOM per release from the committed "
            "pylock.toml; Artifact-Registry scanning + cosign signing of image "
            "digests under a Cloud KMS asymmetric key."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="print the ordered mutation plan (offline)")
    p_plan.add_argument(
        "--project", default=os.environ.get("SIG_GCP_PROJECT") or "<SIG_GCP_PROJECT-unset>"
    )
    p_plan.add_argument("--location", default=os.environ.get("SIG_GCP_REGION", "us-central1"))

    p_sbom = sub.add_parser("sbom", help="emit sbom.cdx.json for a lockfile")
    p_sbom.add_argument("--lock", default=str(_repo_root() / "pylock.toml"))
    p_sbom.add_argument("--export-dir", default=None, help="write into an export dir")
    p_sbom.add_argument("--out", default=None, help="write to a file path")

    for name in ("sign", "verify", "scan-status"):
        p = sub.add_parser(name)
        p.add_argument("--image", required=True, help="digest ref <repo>@sha256:<64>")
        p.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
        p.add_argument("--location", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
        p.add_argument("--key-uri", default=os.environ.get("SIG_COSIGN_KEY_URI", ""))
        p.add_argument("--apply", action="store_true")
        p.add_argument("--record", default=None, help="write the sig.* record JSON here")

    args = parser.parse_args(argv)

    if args.cmd == "sbom":
        from exports.sbom import emit_sbom

        if args.export_dir:
            out = emit_sbom(
                args.export_dir,
                lock_path=args.lock,
                signing_secret_b64=os.environ.get("SIG_RELEASE_MINISIGN_SECRET") or None,
            )
        else:
            if not args.out:
                print(
                    "sig-ops security-baseline sbom: --export-dir or --out required",
                    file=sys.stderr,
                )
                return 2
            data = Path(args.lock)
            if not data.is_file():
                print(f"sig-ops security-baseline sbom: lockfile absent: {data}", file=sys.stderr)
                return 4
            from exports.sbom import render_sbom

            Path(args.out).write_bytes(render_sbom(data))
            out = {"emitted": True, "out": args.out}
        print(json.dumps(out, indent=1, sort_keys=True))
        return 0 if out.get("emitted") else 4

    if args.cmd == "plan":
        steps = (
            api_enable_steps(args.project)
            + kms_steps(args.project)
            + scan_steps("<image>@sha256:<digest>", args.project, location=args.location)
            + sign_steps("<image>@sha256:<digest>", kms_key_uri(args.project))
        )
        for line in run_steps(steps, apply_=False):
            print(line)
        return 0

    if not args.project:
        print(
            "sig-ops security-baseline: --project or SIG_GCP_PROJECT required",
            file=sys.stderr,
        )
        return 2

    key_uri = args.key_uri or kms_key_uri(args.project)
    if args.cmd == "sign":
        steps = sign_steps(args.image, key_uri)
    elif args.cmd == "verify":
        steps = [
            CommandStep(
                "cosign verify",
                (
                    "cosign",
                    "verify",
                    "--key",
                    key_uri,
                    args.image,
                    "--insecure-ignore-tlog",
                    "--insecure-ignore-sct",
                ),
            )
        ]
    else:  # scan-status
        steps = scan_steps(args.image, args.project, location=args.location)

    try:
        lines = run_steps(steps, apply_=bool(args.apply))
    except Exception as exc:  # noqa: BLE001 — honest failure record
        print(f"sig-ops security-baseline {args.cmd}: {exc}", file=sys.stderr)
        return 3
    for line in lines:
        print(line)

    if args.apply and args.record:
        if args.cmd == "sign":
            record = signature_record(
                args.image,
                key_uri=key_uri,
                signer=os.environ.get("SIG_SECB_AUTHOR", "unknown"),
                now=_utcnow(),
                verify_output="\n".join(lines),
            )
        else:
            record = {
                "schema": VERIFY_SCHEMA if args.cmd == "verify" else SCAN_SCHEMA,
                "image": args.image,
                "key_uri": key_uri if args.cmd == "verify" else None,
                "run_at": _utcnow(),
                "output_head": "\n".join(lines).strip().splitlines()[:5],
            }
        Path(args.record).write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"record -> {args.record}")
    return 0


__all__ = [
    "KMS_ALGO",
    "KMS_KEY",
    "KMS_RING",
    "REQUIRED_APIS",
    "SCAN_SCHEMA",
    "SIGNATURE_SCHEMA",
    "VERIFY_SCHEMA",
    "api_enable_steps",
    "kms_key_uri",
    "kms_steps",
    "run_steps",
    "scan_steps",
    "sign_steps",
    "signature_record",
]
