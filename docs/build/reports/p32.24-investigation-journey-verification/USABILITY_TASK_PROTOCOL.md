# P32.24 — independent usability task protocol

**Compensating control for `D-R10-USERS-1` (OPEN).** This protocol is landed
*unexecuted*: no volunteers were available during the P32.24 run and no
session results exist. When a session runs, its recording + scoring append
to this directory and the portfolio's `UX.independent_sessions` check is
re-evaluated — never before.

This is a **moderated think-aloud** protocol for the *public* investigation
surface — the staged release archive and/or the served web app. Participants
get tasks, never instructions; expected answers below are the
evidence-grounded rubric the moderator scores against (they come from the
released records, not from the facilitator's opinion).

## Participants

- **Recruit:** 4–6 volunteers, mixed familiarity (at least 2 non-technical;
  no SIG contributors). Operator-gated recruitment — this row stays OPEN
  until a roster exists.
- **Consent:** recorded session? participant chooses; notes-only is the
  default. No personal data beyond a session id + familiarity band.
- **Compensation/accessibility:** per operator policy; the protocol is
  screen-reader + keyboard accessible by construction (zero-JS surface).

## Session format (45–60 min, moderated)

1. **Briefing (5 min):** "This is a public archive of claims about
   surveillance infrastructure. Everything it shows is tied to published
   evidence. We are testing the archive, not you."
2. **Tasks T1–T7 below** (~35 min): participant thinks aloud; moderator
   records path taken, time-to-first-meaningful-answer, wrong turns,
   dead ends, and whether the final answer cites its evidence.
3. **Debrief (10 min):** "What did you trust least? What was missing?"
   — free text, recorded verbatim.

## Tasks + evidence-grounded expected answers

| id | task (as handed to participant) | expected answer (rubric) | acceptance leg |
|---|---|---|---|
| T1 | "Find the record for a surveillance deployment you can name in this archive. How would you cite it so someone sees exactly what you saw?" | Lands on an entity record page and reads its `/r/p-<64>/…` citation — understands the immutable route is the citation, not the browse URL | A.records_reachable, A.citation |
| T2 | "Is there a record whose location we *don't* publish a point for? How is that shown?" | Finds an `unreported`/no-public-point record and states the location is withheld/unknown — does not conclude the site doesn't exist | A.location_states, A.search (no-public-point) |
| T3 | "This record's page links evidence. Follow one link — what can you actually see, and what can't you?" | Reaches the evidence anchor page; states it shows *metadata* (capture digest, artifact, role) — capture bytes are not served. Does not claim to have "seen the document" | A.evidence_anchors |
| T4 | "Two places show the same partner organisation. Does the archive say sharing *happened*, or that it's *allowed*?" | Distinguishes `configured_access`/`declared_policy` from `observed_use` — participant answer mentions permission vs observed activity | B.edges_typed, expected_answers.configured_vs_observed |
| T5 | "Search for something that isn't here. What does the archive tell you?" | Gets the explicit empty state *for this released collection* — does not read it as "no surveillance exists" | A.search (no-match) |
| T6 | "You believe a record is wrong. What can you do about it? What happens next?" | Finds the correction-intake path; can state the durable-receipt expectation and that a moderator reviews — does NOT expect instant factual change | C.receipt_to_moderation, C.publish_linkage |
| T7 | "One dossier is 'provisional' — what does that mean for what you can rely on?" | Names the provisional/eval-deferred posture from the dossier's own text; does not treat derived interpretation as settled fact | A.dossiers, B.eval_deferred |

## Recording + scoring

- Per task: `completed | completed_with_help | abandoned`, path notes,
  evidence-cited y/n, first-wrong-interpretation y/n (e.g. read an empty
  search as "no surveillance").
- Per session: familiarity band, session id, consent scope, notable quotes.
- **Aggregate rule:** report medians + the *distribution*, never an average
  satisfaction score. Any task where ≥1 participant reaches a *wrong
  evidenced conclusion* is a UX finding with an owner — not a rounding error.
- **Output shape:** `USABILITY_SESSIONS.json` (session records) +
  `USABILITY_READOUT.md` appended here; the portfolio check consumes
  `volunteers=[…]` + the readout pointer.

## Integrity rules

- The moderator may clarify the *task text* but never the *archive's answer*.
- Failure of a task is a finding about the surface, not the participant.
- No fabricated sessions: a session row with no recording/notes link is
  invalid and rejected at readout.
- Participants may withdraw; their rows are removed, not edited.
- This protocol never runs against production user data — staged releases
  only (the acceptance corpus is synthetic by construction).
