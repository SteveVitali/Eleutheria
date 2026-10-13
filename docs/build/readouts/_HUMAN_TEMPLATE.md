# HUMAN-<id> — pending readout

<!-- Human-check readout template (P34.28; G4b; SIG-MEM-008/009; ADR-147). For a
     HUMAN-Hn / human-check verdict (including a Class-S release go): copy, rename
     to `<ID>.md`, fill the criterion verbatim. The same rules as
     `_GATE_TEMPLATE.md` bind — the guard sentence stays permanently; signing
     only moves `Status:` and appends the `## Signature` block; the decision
     line is the operator's verbatim words equal to the named GATE DECISIONS
     row's answer; hedged/conditional/delegating language is not a decision;
     agent text lives only in hash-confirmed agent-drafted blocks; the signing
     commit verifies against `allowed_signers` (OP-25 — fails closed while the
     key is outstanding). A human check is reported, never claimed by an agent
     (B-31, B-42). -->

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/<NNN>_<TICKET>__<slug>.md`.
Decision domain: <what the human check covers — id, scope>.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] <check text copied verbatim from the ticket>

## Signature

<!-- Same fields as `_GATE_TEMPLATE.md` — appended only at signing. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | <id>
<!-- agent-drafted:begin sha256=<64 hex over the block body> -->
<agent-written summary, labelled — optional>
<!-- agent-drafted:end -->
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:<first 12>
Signed by: repository operator. Recorded by <harness>/<model>/<tier>, which does not sign.
