# Build-memory current-state audit (P32.1 / SIG-MEM-001)

- root: `/Users/stevenvitali/Eleutheria`
- inputs: 125 files, SHA-256 recorded in the JSON report
- result: **0 error(s), 12 conflict(s)**

| check | severity | file | obligation | message |
|---|---|---|---|---|
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.1__rights-review-and-registry-completion.md | ticket file P21.1__rights-review-and-registry-completion.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.3__live-connector-wiring.md | ticket file P21.3__live-connector-wiring.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.4__first-jurisdiction-ingest-and-publish.md | ticket file P21.4__first-jurisdiction-ingest-and-publish.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.5__infra-deposit-and-tiles.md | ticket file P21.5__infra-deposit-and-tiles.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.7__contribution-back-live.md | ticket file P21.7__contribution-back-live.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| manifest/duplicate-file | conflict | docs/tickets/00_MANIFEST.md | P21.8__data-driven-and-coarse-international.md | ticket file P21.8__data-driven-and-coarse-international.md appears at two chain positions — verify a documented pointer row (e.g. a Lane-B re-run row) vs an authoring error |
| tickets/dependency-not-in-chain | conflict | docs/tickets/P31.19__round9-closeout.md | P31.17 | P31.19__round9-closeout.md names P31.17 in 'Depends on:' but P31.17 has no chain row (prose context or a stale reference — needs recorded reconciliation) |
| tickets/dependency-not-in-chain | conflict | docs/tickets/P31.19__round9-closeout.md | P31.18 | P31.19__round9-closeout.md names P31.18 in 'Depends on:' but P31.18 has no chain row (prose context or a stale reference — needs recorded reconciliation) |
| deferrals/status-conflict | conflict | docs/tickets/DEFERRALS.md | D-P21.4-3 | D-P21.4-3 leads OPEN but its status cell later records DONE 2026- — mechanical readers and the prose disagree; ambiguity stays open until a recorded reconciliation (no silent last-token-wins) |
| deferrals/status-conflict | conflict | docs/tickets/DEFERRALS.md | D-P21.5-1 | D-P21.5-1 leads PARTIAL but its status cell later records DONE 2026- — mechanical readers and the prose disagree; ambiguity stays open until a recorded reconciliation (no silent last-token-wins) |
| deferrals/status-conflict | conflict | docs/tickets/DEFERRALS.md | D-SOURCES.2-4 | D-SOURCES.2-4 leads PARTIAL but its status cell later records DONE 2026- — mechanical readers and the prose disagree; ambiguity stays open until a recorded reconciliation (no silent last-token-wins) |
| deferrals/status-conflict | conflict | docs/tickets/DEFERRALS.md | D-R7.3-BREADTH | D-R7.3-BREADTH leads OPEN but its status cell later records DONE 2026- — mechanical readers and the prose disagree; ambiguity stays open until a recorded reconciliation (no silent last-token-wins) |

