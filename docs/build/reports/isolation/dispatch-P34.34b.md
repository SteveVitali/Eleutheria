# Isolation record — dispatch P34.34b (C1)

- **Dispatch:** 2026-10-06T23:59:26Z (orchestrator `date -u` at dispatch)
- **Ticket:** P34.34b — `docs/tickets/242_P34.34b__export-mode-ci-build-and-island-budgets.md` (row 242)
- **Probe class:** orchestrator restart (plan §8.5 (3)) — fresh nonce + control token
- **Control token:** `P34B-CTL-748d499f` (revealed to the sub-agent in the prompt)
- **Nonce:** 32-hex token; never placed in the prompt or persistent state. SHA-256 = `93066de93fa5a111abbc87394468d8b3f91ea3d860c2a9775bd383f01bf18b2c`. Reveal + verdict appended below after the sub-agent reports.
- **Required report fields:** control token echo; initial context sources (first reads); whether any 32-hex token was held; start time; harness/model.
- **Prior boundary:** `ci: pass #238@e93e51c` (run 37548493579, 5/5, stack pass, merges:0) — log `docs/build/logs/ci-P34.34a-boundary2.json`.

## Verdict

_(to be appended on report)_
