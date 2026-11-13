# Copy batch 28 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.45 (row 469, R11-CONF-12 — the public /quality/ page:
     the checks table's in-brief and section copy, the who-checked-what
     basis table, the cannot-tell-you list, the probe-lane and history
     panels). Append-only, same convention as batch-01. Id prefix: QL-* =
     the quality surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline),
**status** (`pending` · `confirmed`). `{slot}` names vary per render — the
row records the template the element fills. Furniture — headings, link
labels, table captions — is navigational chrome, never a row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| QL-01 | /quality/ | SIG checks its own data automatically on every release: {nChecks} checks, {nPassing} passing, {nRatchet} still being fixed. Each check below says what it tests, on how many records, and how. No person outside the project has reviewed SIG's data or its matching. So SIG merges records only when they are copies of the same upstream record, which a program can verify. Where two sources may describe the same camera but SIG cannot prove it, both stay visible, marked "possible duplicate". | c4b4105c02a0dc764a7eeb52e56c826858cc93ed33b08284b56c5dd217b2ec97 | pending |
| QL-02 | /quality/ | Every figure on this page is a mechanical check's own record — {NO_HUMAN_CHECK}. No check by a person outside the project exists; none is claimed. | 8682c069eabb966c11336a80b20e39733c8d4abf5dd18f6b8f7f79148f104c97 | pending |
| QL-03 | /quality/ | The checks | a7706846c5c0772842a6ad5881780ba893e1ac6dede852f23fb08f6ed65155f3 | pending |
| QL-04 | /quality/ | {runLead} sig.quality-page/1. | 1c53d05e2e024f8ee8a820d6450ac9675e20df18c4e04128cd4baf34983e437d | pending |
| QL-05 | /quality/ | How duplicates are handled | 953f7e2b461a1406746016dae672f5ebb3aef8056c1bb275020c5f9e4c9a980b | pending |
| QL-06 | /quality/ | SIG merges records only when they are copies of the same upstream record — a derivation a program can re-verify on every run (the GQ-23 census). Where two sources may describe the same camera but SIG cannot prove it, both stay visible as a possible duplicate and counts publish as an interval — records and, beside them, the between-lower-and-upper bound of listed cameras. | 0289fef62b2aed748792b5b9a1ad7bfc7559d349a33bc588b263bc71b9e62520 | pending |
| QL-07 | /quality/ | The measured copy layer: {m3.value ?? m3.unavailable_reason} (cross-copy agreement within the declared tolerance); the derivation census: {m1.value ?? m1.unavailable_reason}; the id-resolution sample: {m1b.value ?? m1b.unavailable_reason}. These are mechanical measures over the populations the methodology report names — never real-world precision or recall. | 0b7415a8dd5a9388f92e158aabf229ea105bbe61960d0264810a1da7abc9ed6d | pending |
| QL-08 | /quality/ | Who checked what | 1c48fdf7cceb46be70fb47a8552f16b0e9ef914ae30f72eb0682c7cebd6c2227 | pending |
| QL-09 | /quality/ | What we cannot tell you yet | fd3a370d371090d8640be5e27b63112af2f31003eb90e8508ddc1d01ba47f3f1 | pending |
| QL-10 | /quality/ | Whether a camera physically exists or operates — SIG records claims about cameras, and copies of what upstream sources list.Precision or recall of identity matching across independent sources — that needs independent human labels, which do not exist in this round.Completeness of coverage — "every" or "complete" is never claimed.Candidate recall — the pairs SIG's matcher never proposed are unmeasured.Whether two organisations with similar names are the same — only shared authoritative identifiers auto-link.Any figure a check has not measured — an unevaluated check says so, it is never smoothed over. | 09eb04198b5150caebb5d8062c04fe6af594fbc51d8abd16449f6401ff240a3c | pending |
| QL-11 | /quality/ | Corrections | 443b744e50f5454b1dfdc24d8d51ac1686b53a60cf01f571f33292c145ef2bc5 | pending |
| QL-12 | /quality/ | Corrections and safety reports arrive by e-mail — the dispute page states the address and the handling order; the corrections log publishes every received, confirmed and fixed correction with its dates. SIG promises no response time. | 88e5d0b1c0aa384107eb53a85f2f22bb005d826addc77906b9c35e491e6a0b64 | pending |
| QL-13 | /quality/ | The working database, checked nightly | 45891438a502d462025ecf184d28c8ba216a831b892dd13251e7650eb70feae6 | pending |
| QL-14 | /quality/ | The nightly spine probe checks the working database — a different, newer population than the release above, and the two are never mixed. Latest check of the working database (not yet published), {lane.generated_at}: {lane.checks.length} checks ran, verdict {lane.overall}. | a0e07a79a2ea2f898cf55e8411a2026b31960f2a545ce5b64c64bd5c5b5c9c93 | pending |
| QL-15 | /quality/ | No probe read is recorded in this build — the nightly job publishes a fresh copy when it next runs. | 5386c62550996f2caeb18409010480a264fb96f10773e4f77ccfbac1a8097c0d | pending |
| QL-16 | /quality/ | History | 0e769600933790607b2a13b33ddfade0fa17810eb62c3b28ee23e59516516491 | pending |
| QL-17 | /quality/ | {historyLine} | 7c42344a432b0c27a71e461ab0afd17fe378e71a7b348cd229064e30345f122a | pending |
