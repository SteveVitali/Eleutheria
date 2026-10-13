# GATE-<id> — pending readout

<!-- Readout template (P34.28; G4b; SIG-MEM-008/009; ADR-147). Copy for a gate
     (`GATE-<id>`), rename to `GATE-<id>.md`, and fill the criterion verbatim from
     its ticket. Signing rules — enforced by `memory_guard.py` and, for origin, by
     `check_gate_signatures.py`:
       - the guard sentence below stays permanently;
       - signing may ONLY move `Status:` from PENDING to one of {SIGNED, PASSED,
         SKIPPED-BY-OPERATOR, NOT-PASSABLE} and append a `## Signature` block —
         nothing else is edited, no checkbox is ticked;
       - the decision line quotes the operator's exact words and equals the
         `answer (verbatim)` of the named GATE DECISIONS row (ADR-147 rule 1);
       - hedge / question / conditional ("I think…", "perhaps", "should we…") is
         not a decision — it is recorded as such and decided only by a later
         plain confirmation (G4a);
       - agent-written text sits inside a labelled `agent-drafted` block whose
         sha256 the operator confirmed in words recorded as a GATE DECISIONS
         `confirmation` row;
       - an agent never signs and never assumes silence is approval; the commit
         that signs verifies against the committed `allowed_signers` (OP-25,
         G4c — while the key is outstanding the check fails closed). -->

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/<NNN>_<TICKET>__<slug>.md`.
Decision domain: <what this signature would approve — gate id, scope>.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] <criterion text copied verbatim from the ticket — the signature block
      quotes what the operator declares met; it never ticks this box>

## Signature

<!-- Appended only at signing, by the commit that moves Status:. Fields:
     `received` is `date -u` when the operator's words arrived; `<channel>` is
     how (e.g. chat); the GATE DECISIONS row line names the exact LEDGER row —
     its date and gate must resolve to one row and the quote equals its answer.
     Delete the agent-drafted block if none is appended. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | <gate id, e.g. GATE-G4>
<!-- agent-drafted:begin sha256=<64 hex over the block body> -->
<agent-written summary, labelled — optional>
<!-- agent-drafted:end -->
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:<first 12>
Signed by: repository operator. Recorded by <harness>/<model>/<tier>, which does not sign.
