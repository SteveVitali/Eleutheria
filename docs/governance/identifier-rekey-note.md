# Correction note — source identifiers re-keyed for personal-data protection (2026-10-03)

*P34.18 / ADR-178 · S0 finding RI-01 (F-097/F-131) · operator decisions DR-C6-01
(B-3), OD-17 (A-0.1), OD-20 (A-0.4) — Part VIII personal-data protection.*

## What changed

A cohort of public source identifiers was minted from personal account handles
(and one from a surname): the `camreg_<handle>` source ids, the camera target
ids derived from them, and every identifier composed from those — camera
subject ids, claim ids, evidence/permalink ids and tile properties. Those
identifiers have been re-keyed to neutral ids (`camreg_us_ny_<n>` /
`camreg_und_<n>` / `okc_council_statement`), which are not derived from any
personal token.

The change was made under **Part VIII** of the design spec: identifiers that
embed a person's handle are personal data unrelated to institutional conduct,
and SIG's public surface must not carry them (SIG-PUB-002).

## What did not change

- **No claim was rewritten.** The claim spine is append-only (P1–P3,
  SIG-STORE-011): every claim keeps the identifier it was recorded under.
  Resolution of an old identifier to its neutral form is a read/export-time
  projection, not an edit of the record.
- **No history was rewritten.** The repository's git history retains the old
  strings — that is the operator's accepted posture (OD-20, *"Accept and
  disclose"*). Anyone inspecting past commits will find them; this note is the
  honest disclosure of that fact, and it is the condition under which the
  archive deposits (P37.55) proceed after their history scan.

## Old citations

A URL or citation that carries a retired identifier now resolves to a neutral
notice — *"This identifier has changed."* — rather than to a new page. There is
deliberately **no public redirect and no public old→new list**: a redirect or a
published mapping would repeat the handle (DR-C6-01). The old→new mapping
exists once, in a restricted location, for the operator's audit and rollback
needs only.

## Registry text

The same review removed e-mail-shaped owner strings and handle tokens from the
source registry's non-identifier text (notes, names, agency fields), replacing
them with neutral markers such as `[account withheld]`. One `camera_operator`
value that was itself an account handle is suppressed from public surfaces; the
recorded claim is retained.

## Records

The append-only record of this change: ADR-178 (the decision), the committed
re-key tool (`sig-connectors rekey-personal-ids`, dry-run by default), the
keyed-digest alias table (`policy/src/policy/data/source_aliases.json` —
sha256 digests, no plaintext handles), and the counts-only crawl check
(`docs/build/tools/handle_crawl_check.py`). The re-keyed public pages and the
neutral-notice routes ship with republish #2 (P34.21b).
