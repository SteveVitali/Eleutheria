# Manual-acquisition runbook (SIG-INGEST-008)

Some dependencies are **manual-acquisition**: a human obtains them through a
login, a mailed disc, a records release, or a one-off download the build has no
lawful automatic path to. The registry `connectors/src/connectors/data/manual_acquisitions.toml`
(`sig.manual-acquisitions/1`) is the model; this runbook is the documented human
procedure it names. The build MUST NOT assume these dependencies are fetchable —
`sig-connectors run` refuses a registered manual dependency in every mode, and
the acquisition provenance lands **here**, not in code.

## When this applies

A dependency is manual-acquisition when its `sources.toml` row declares
`access_method` containing `manual` (e.g. `"manual acquisition (login)"`) **and**
a `[[dependency]]` row exists in the registry. Today that is:

- `leaic_crosswalk` — ICPSR study 35158, the ORI↔FIPS↔place bridge (§14.2).

## The procedure

1. **Read the registry row.** `sig-connectors validate` confirms the registry is
   well-formed; each row names `access` (the human path) and this runbook.
2. **Acquire the artifact as a human**, through the `access` path the row
   records (e.g. an ICPSR account → study 35158 → data-file download). Never
   script around the access path — a manual dependency has no lawful automatic
   fetch, and scripting it is exactly the "pretending it is automatable" failure
   SIG-INGEST-008 names.
3. **Record the provenance on the registry row** — the MUST is DOI (or the
   publisher's identifier), version, and checksum:
   - `identifier` — the publisher's own id (e.g. `"ICPSR study 35158"`).
   - `doi` — the DOI the publisher mints for the version acquired, verbatim.
     Leave empty only if the publisher genuinely mints none (the `identifier`
     then carries the citation).
   - `version` — the acquired version (e.g. `v1`), verbatim from the publisher.
   - `sha256` — `shasum -a 256 <file>` over the acquired bytes.
   - `acquired_at` — the real acquisition date (`date -u +%F` on the day).
   - `status = "acquired"`.
4. **Place the bytes** where the dependency's consumer expects them — the
   committed fixture/data path the consuming module names, or the OCFL evidence
   store as a `capture_method = "manual_upload"` capture (§17 `capture_method`
   vocabulary) so the upload is itself a recorded event, never an invisible
   drop-in.
5. **Re-run `sig-connectors validate`.** An `acquired` row missing DOI/
   identifier, version, or checksum fails validation — the provenance is the
   record, not decoration.

## What never happens

- No connector is written to "fetch" a manual dependency. The
  `ingestion_mode = "manual"` declaration (§21.3, P37.5a) exists precisely so a
  human-in-the-loop source can be honest about its mode.
- `sig-connectors run --source <manual-dep>` refuses (exit 3) in every mode —
  there is no automatic fetch path for the driver to run.
- A `pending` row carries no `doi`/`version`/`sha256`/`acquired_at` — recording
  provenance before the leg ran is a fabricated record.
