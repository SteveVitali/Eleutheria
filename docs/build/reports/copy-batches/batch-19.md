# Copy batch 19 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P37.8 (row 428, R11-GOV-03 — the legal-demand posture +
     published counts page, /about/legal-demands/, plus the /corrections/
     pointer sentence). Append-only, same convention as batch-01: rows are
     never deleted or edited in place; a status change is recorded in the
     confirmation log with a `date -u` stamp. Id prefix: LD-* = the
     legal-demands page. -->

## Convention

Same as batch-01 (`docs/build/reports/copy-batches/batch-01.md` § Convention):
`pending` = agent-drafted, awaiting verbatim confirmation · `confirmed` = the
operator confirmed these words verbatim. P37.8-specific notes:

- The count figures (`received` / `complied with` / `refused`, the `as_of`
  date and the snapshot id) are **record content** — the committed
  `sig.legal-demand-counts/1` snapshot in `web/src/lib/legal-demands.ts` —
  bound by test, not this register (the batch-18 precedent for record
  entries).
- **LD-08** renders only when no count snapshot exists (one does — the
  2026-11-06 zero snapshot is what ships).
- **LD-10** binds `/corrections/` — the transparency report's pointer to
  this page (design E2-10's "/corrections/ gains legal-demand counts").
- The posture document of record `docs/governance/legal-demand-posture.md`
  carries the same sentences verbatim; the binding is by test, not this
  register.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| LD-01 | /about/legal-demands/ | This page is SIG's written posture for legal demands — subpoenas, warrants, preservation letters and takedown demands — set down before the first demand arrives, and the published count of demands received, complied with and refused. | 4b0a7772bb653f5ab047498bb183b44e8428275e918409bf07bf12a6afee0cf1 | pending |
| LD-02 | /about/legal-demands/ | This posture is not legal advice. No lawyer's written opinion has been obtained, and no lawyer has reviewed it. The operator adopted it on 2026-10-01. | b43bbb0328015f4d483b01005053490d536d1eec34cdc6626bc528e72a44bbeb | pending |
| LD-03 | /about/legal-demands/ | SIG holds public records about surveillance infrastructure, the evidence behind each claim, and the append-only record of decisions and corrections. It holds no contributor accounts, no reader tracking, and no per-person or plate data — not holding data is the main protection. | 163ca8cf770732935321b383d332b944275f2e5d4092ca8663eb0cc4c5e725d3 | pending |
| LD-04 | /about/legal-demands/ | The operator — an individual, disclosed as SIG's interim legal home — receives all legal process addressed to SIG. There is no organisation and no lawyer. The channel is the e-mail address the dispute page names. | 8723ca8dc84f6b07f6f711bedcc3c8aeb396cebd8f4a3f91843b11f55b708472 | pending |
| LD-05 | /about/legal-demands/ | A preservation request is logged with its date and scope. SIG's claim record and evidence store are append-only and versioned, so preservation is the default: a correction never overwrites or deletes. A lawful preservation request is honoured as a recorded legal hold on what exists. | 103afc17364ae1e8f2a2053784758ddedcef4975357385d98eb00855181023b0 | pending |
| LD-06 | /about/legal-demands/ | Where a demand seeks information about an identifiable person and the law allows notice, SIG tells that person before complying. SIG holds almost nothing about individuals, so in most cases there is no one to notify. | ba763ca2c9170d7041999bd8d8ada8627b0e572f367cec25d7ef16b99c785b84 | pending |
| LD-07 | /about/legal-demands/ | The counts below are republished when a demand arrives or when a demand's handling changes. Each update is a new dated snapshot appended to the count record — counts only: never a requester's identity or case detail. | 06477f0e581515149a5052f1b5d19f4df26670fd1c2471a18b45bdef866efb33 | pending |
| LD-08 | /about/legal-demands/ | No count snapshot is recorded. | 099b4f98e1e7f67caff71f1a2bece4ff78a216388be35b1bd6b58cc8d0187ed9 | pending |
| LD-09 | /about/legal-demands/ | SIG does not operate a warrant canary. With one maintainer and no lawyer, a scheduled canary cannot be maintained reliably, and a lapsed canary would itself read as a signal — so the canary is declined, and this page says so. | 961f02f09704f946cc7cc76e0719301b3fbd6d4338d4c8c2d3452c4be64f55df | pending |
| LD-10 | /corrections/ | The written response posture and the count record sit on the legal-demands page. | f120306dc2c79671670eff9ff9da24ecdc21621d2d51e1bea8f2655e5e2bb82f | pending |
