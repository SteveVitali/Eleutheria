# Release candidate manifest — P32.23a (`sig.candidate-manifest/1`)

> **Unpublished.** Built under the active PROVISIONAL resolution policy;
> the S3 human-evaluation spine is deferred — there is no final
> evaluation decision. `eval-confidence/1` is shadow (`applied=[]`);
> P32.10's confidence policy is not activated.

- identity digest: `sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f`
- ruleset: `provisional-ruleset/1`
- frozen snapshot: `sha256:138714a684982c982610ece27a8215fc93e0c4cc4a220b7574307ad358695d99`
- evaluation: **deferred** · policy `eval-confidence/1` mode `shadow`
- publication id (staged, NOT activated): `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`
- release manifest: `3966c7657b7b30b379c50608e6cb6d35f90b29bd03b0f336716bca48fc9a23ce`
- descriptor sha256: `sha256:17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`
- validation ok: `True`
- records built: `0`

## Materialization (dependency order)

- pass-1 inserted +3 · rerun inserted +0 · **+0: True**
- order: resolution → camera-sites → edges → contradictions → coverage → accountability

## Publication pointer

- before: `null`
- after: `null`
- unchanged: `True`

## Deferral dispositions

- **D-R10-HUMAN-1** — `amended_open` — 2026-10-19 operator choice: the S3 human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) is deferred wholesale. There is NO final evaluation decision — this candidate is built under the active PROVISIONAL resolution policy, with the deferral disclosed everywhere the candidate is described.
- **D-R6.1-EVAL** — `open` — provisional rules remain active; the candidate pins them as provisional-ruleset/1
- **D-R10-LIVE-1** — `open` — the production candidate still needs the hosted repaired spine — the return-pass packet pins it
- **D-R10-PUBLISH-1** — `open` — publication needs P32.24 validation + GATE-G3 + P32.25

PROVISIONAL EVALUATION BASIS — review-only. The S3 human-evaluation spine is deferred wholesale by explicit operator choice (2026-10-19): there is no final evaluation decision. The camera-site auto-write tiers and the historical 0.98 point-gate remain PROVISIONAL-active (D-R6.1-EVAL stays OPEN) and eval-confidence/1 stays mode=shadow with applied=[] — nothing was promoted, demoted, or certified. Any resolved-sites figure on this candidate is computed from THIS build's materialized export, carries its own denominator, and is provisional/review-only — it is not a certified count, and no figure is carried from any prior preview or evaluation artifact.
