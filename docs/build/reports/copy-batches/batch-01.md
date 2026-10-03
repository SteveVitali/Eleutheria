# Copy batch 01 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P35.38a (row 203), the first 11A row that needed the file
     (SEED-13b convention, contract "Notes"; B-2 "Batches + notice allowance",
     round 10, 2026-10-01T04:32:16Z). Append-only: rows are never deleted or
     edited in place — a correction is a new row superseding the old id, and a
     status change is recorded in the confirmation log below with a `date -u`
     stamp. -->

## Convention

- Each drafted sentence of public page copy is appended below with its **page**,
  the exact **text** (as it will render — markup contributes no text), its
  **sha256** (UTF-8, no trailing newline — `printf '%s' '<text>' | shasum -a 256`,
  the ADR-168 hash convention), and a **status**.
- **Status vocabulary:** `pending` = agent-drafted, awaiting the operator's
  verbatim confirmation · `confirmed` = the operator confirmed these words
  verbatim at a copy-batch sitting (recorded in the confirmation log below with
  a `date -u` stamp). An agent never confirms — the confirmation is the
  operator's words, recorded verbatim (OM-07/08).
- **Binding:** a row's `id` names where the sentence lives on its page. The id
  `title` binds the page's `BaseLayout` `title` prop (the `<h1>`/`<title>`);
  every other id is carried in a page element's `data-copy` attribute — an
  element holding several sentences lists its ids in order, space-separated.
  `tests/unit/test_data_collection_page.py` fails if a row's text drifts from
  the page, if a sentence ships untracked, or if a hash does not verify.
- Ids are page-scoped (the `page` column namespaces them) and never reused.
- **Shipping rule:** only `confirmed` sentences may ship (B-2); republish #1
  (P34.17's L2) refuses a `pending` sentence.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| title | /data-collection/ | How SIG collects data | 1c5d16258cd76dd4b5777c2091214b5dd73f5e3d77c8a6c828ae749aea936187 | pending |
| DC-02 | /data-collection/ | SIG — the Surveillance Infrastructure Graph — is an open, evidence-first record of public surveillance infrastructure, built by fetching public records. | f6bb30491ce43f2e61830a5dfcc03f058e26dc7395066f67a55579f87426856a | pending |
| DC-03 | /data-collection/ | This page is the explanation the crawler's contact URL points to: what it fetches, how it identifies itself, how it treats robots.txt, and how to ask it to stop. | 545ee87c41a94f48eefb65db622f8270dfb8b9d2d5df738895e183a1ae5aa8a5 | pending |
| DC-04 | /data-collection/ | What SIG fetches | 9905fd6c5463d37c5684f7256400ceb75fe21b04ed51f9dbeb4601f9c3c0ed6d | pending |
| DC-05 | /data-collection/ | SIG fetches public records only — pages, documents, datasets and APIs that a public body or a transparency project publishes openly. | 6427a101302c913dbe112799ee558613caef1a0aed8b12fb29b7bd3b4327aefb | pending |
| DC-06 | /data-collection/ | It never collects licence-plate reads, trip histories or other per-person data: those are excluded by design, not filtered out afterwards. | 083a465740a93ea0fdbb1a95d93f17baf3f639a5ea104f27c93b554bf87e981d | pending |
| DC-07 | /data-collection/ | How the crawler identifies itself | 9041ff31e0cc9c330bf68bfadb6f833649b457f29a2b2cfe375c1adeadc4d815 | pending |
| DC-08 | /data-collection/ | Every request carries a User-Agent header of the form name/version (+https://surveillancegraph.org/data-collection/), where name is the connector doing the fetch — for example osm/1.0.0 or the project fallback SIG. | c4706342058113887278f7bafed9fb669493ca30d3f05aca1d2a4eeeb5a2a88e | pending |
| DC-09 | /data-collection/ | SIG never impersonates a browser and never rotates or disguises its agent to get past a block. | 840b3d8acccea387fa4a1c611cec89d2969eb35c150b86b59dc1b24e769181a6 | pending |
| DC-10 | /data-collection/ | How robots.txt is treated | 3954c8a945d240b87e6c8a4ffc77fd83ee319a38c14a630ae2421f678d8cd0e0 | pending |
| DC-11 | /data-collection/ | For every host it fetches, SIG retrieves and records the host's robots.txt and classifies the answer per RFC 9309. | 8f1a556592a17460913f4ab031d360adced6e1ce7b936bf6541d5a119dabbc6a | pending |
| DC-12 | /data-collection/ | Under a recorded operator decision (GL-GATE-08 — ADR-088 and ADR-168), a Disallow, or a policy that cannot be retrieved, does not by itself stop the fetch; the fetch is marked robots_disregarded in SIG's record, so the refusal stays visible instead of being silently bypassed. | bc9de25a46b53b3491c65ba83378bd4df5c08e48009dad91302d8e90f338a701 | pending |
| DC-13 | /data-collection/ | Robots.txt is not the access control: the binding check is a fail-closed rights review per source, and a source is never fetched before its rights record permits it. | 33e3ffdaf931b4761da77bfb6f6bec7d9864db1dadd36b4d1da71cd9583116c6 | pending |
| DC-14 | /data-collection/ | Rate limits | 6ed021f7e822e17d4a0fa21539b0b1d801e04c244ad6b1f15fa79968a4e5b7fc | pending |
| DC-15 | /data-collection/ | SIG fetches slowly — at least one second between requests to one host by default, and longer wherever a published crawl-delay or a documented API budget demands it. | e1d9e699c8fac05ae1501893a0212f848d06abdce38276316c08a678cec61727 | pending |
| DC-16 | /data-collection/ | An HTTP 429, 503 or 504 answer is met with bounded backoff and retry; a bot-management challenge is recorded, never defeated or worked around. | 97a631b5a2bad48c1bc1ffedc2860c83a660d2ceb337c8c3f447738d93de3c66 | pending |
| DC-17 | /data-collection/ | Ask SIG to stop | 2bc5db01badf5baad1fa1cdeff3d9bccc3910e7e0a682f96b409bf19321f3b20 | pending |
| DC-18 | /data-collection/ | To ask SIG to stop fetching a site you operate, open a request through this site's dispute channel. | 12dd33406e5944a7ebae65e1de2e611216537b57106cb99114d475bb2a2c4a99 | pending |
| DC-19 | /data-collection/ | SIG does not publish an e-mail address; the dispute page is the project's contact route and states its own operating status. | cfdb5eecfc8cb0e7fe83d1b42b920134143b00db2b58b3a409250d5b09f59474 | pending |
| HO-02 | / | SIG is an open, vendor-agnostic, temporally versioned record of public surveillance infrastructure — what is deployed, where and by whom, how it is connected and governed, and the evidence behind each published figure. | c0898d53bf3e3be886f2a9155aead22a102e0d820eb80f66070875021b701b4a | pending |
| HO-03 | / | SIG reports; it does not endorse. | a5816eca39d1d3a1316a2bb0f19fc29c355e7a8ed4b5b2d8ef4eb8264c0d7c5f | pending |
| HO-10 | / | The project's primary public artifact: per-jurisdiction — what is deployed, who can see it, what SIG knows about its cost and decision dates, and what SIG does not know. | 0a25e105206558fd030d8963a9749f1359d72961cbbe0208ed3a65038241d497 | pending |
| HO-11 | / | Each dossier also has a print view. | 34bbd9d8cb5da3170e2a5f8dc18c1c4ba55a1311b2be0fa21c76663ffcf38472 | pending |
| HO-12 | / | The contract and authorization decision dates SIG is tracking, and the evidence ranked for the next one. | 70743252a68d68b7caac51f12d224fa8722945f56ef904622a0b7d2299e3ae6a | pending |
| HO-20 | / | The methodology page explains the fields, glyphs, and gaps in plain terms. | 6f5ff664a166eb9a96dd4ff59ca1ed2c78b69e10959ec9b3dd240dab21018344 | pending |
| HO-21 | / | Every page also carries a link recording the belief-time and ruleset it was built from, and a citation line you can quote. | a3a1e5c855c4d5cc26e56f60e6d530ceb64ff376b0ac4dd93c705b35586e5116 | pending |
| DI-02 | /dossier/ | A dossier is SIG's primary public artifact for a jurisdiction: what is deployed, who can see it, what it costs, when it must be decided, and — as a headline, not an appendix — what SIG does not know. | cfaec5ca40d5e097f6e2d6252aaafdc1e100bd0e7eff494c63082a92a51a97d8 | pending |
| DI-03 | /dossier/ | Each dossier has a print view, and the page records the belief-time and ruleset it was built from. | 902b6d14612cd9c835ae1302e8aa57587caa184065036216971380140f3e4881 | pending |
| DI-04 | /dossier/ | This index lists every jurisdiction SIG has researched to a publishable standard. | 5b906acacb2b12ad52f7a93fc4058eeeead6a36d29a6bb6ddfbbb7b6414f84f6 | pending |
| DI-05 | /dossier/ | It is not a census: a jurisdiction absent here is one SIG has not yet published, not one with no surveillance infrastructure. | ddf46584d2f264671340f270870e8be5359db071204cfdc275df7bdc8b63a467 | pending |
| DI-06 | /dossier/ | These are inventory overviews, built automatically from published claims; the reviewed, evidence-complete twelve-question portfolio form is being built. | 2981f5e513e7fbc0f9ad53062be9f139f0d43efdcd8503567c188d566697b54d | pending |
| D-01 | /dossier/[slug]/ | Inventory overview — built automatically from published claims. | ee00817e7e86538f49bdefbfc0ab4747ee294dee782aecfbcd8bd2ee2ec20231 | pending |
| D-02 | /dossier/[slug]/ | The evidence-complete reviewed-portfolio form is being built. | c61a4c41d6e183b4f2433f0ab7ab1c0bffe582e5de59b59a38c4689da2853f1c | pending |
| DS-01 | lib/dossier.ts | No record in SIG. | daf71c34c8d7a8fbf59eb819f0315d5fa92baf2523a6177399328aa90a6c3180 | pending |
| DS-02 | lib/dossier.ts | The absence of a row is not evidence of absence. | 4de15753b133d323e7ac9778c0ede0091642ae963bcf6260899347d4ccaa27ea | pending |
| DS-03 | component/WhatWeDontKnow | This reflects what has been reviewed so far; it is not a guarantee the record is complete. | 9218935b386e970e1648266ee62e60ca6d1362a17cc39701206238bee67af2a3 | pending |
| HW-01 | component/HowWeKnowThis | Site-wide — these totals describe the whole published record, not this page alone. | f2f2d2108bbfa556f2a0e4c4d066c451cf64c2b7c05bb50f5b05b821dd04d59b | pending |
| HW-02 | component/HowWeKnowThis | These totals describe this page's own evidence, not the whole record. | 162f8b5122a343b682ccb6739906fc16e1834ecfa734fb6ff69aa5f58ed85897 | pending |
| HW-03 | component/HowWeKnowThis | Evidence artifacts | d4f784f46ad5a6870080ed39436e636afc2bf8641380ed8719b1981279274539 | pending |
| HW-04 | component/HowWeKnowThis | Claims by evidence tier | b49d40ddb1e2a7277bd50904ecd9c0681010df8b31510b61a1e292c216d3d42b | pending |
| HW-05 | component/HowWeKnowThis | Independent sources | 42da9b568a23730c4f95519d810e5777514022ac3e6af95906c56fd251b033cc | pending |
| HW-06 | component/HowWeKnowThis | Evidence date range | 2d1d7dfafc77e6488f2b55317f29913d82cabc477467992bb5e569d70a330d99 | pending |
| HW-07 | component/HowWeKnowThis | Rules applied | 97cc444167c0daad47b0446079a2ca25c8bc31a1bbf468815b99f91c8837dc71 | pending |
| HW-08 | component/HowWeKnowThis | Human review status | 372088a47475deacc2c4065b8263ae97bb5b52f20f0c0d422412647ea06741f7 | pending |
| HW-09 | component/HowWeKnowThis | Counted against: {provenance.denominator}. | 068f9494e1190564131725071e773c914b97824cb27700b1dc5f9e163925259f | pending |
| CC-01 | component/Citation | Link (records the as-of pair and ruleset of this build): {permalink} | 292793c264b5d5afa3b77a40ac52ab928fadc55d27e6efe9eb55b57d0a70ceb7 | pending |
| CL-01 | /corrections/ | Every correction SIG makes is public. | 8cc9822b9a705eeb015df0d90fd28913f0ef6188e5554eba846788328c6b9b40 | pending |
| CL-02 | /corrections/ | This log begins {logStart}; its counts cover only corrections recorded since that date. | 611215cee058965e318d8a93b079d41f6ccca2687a28bedf9d7faef62faa3ad4 | pending |
| CL-03 | /corrections/ | A correction is a new assertion, never a deletion: the earlier value is preserved, and each entry names the belief date at which it stood (SIG-GOV-005). | 4e2b7c4085799def4fbe00cefd531ac35aedaae9244c433b03b1de2476c1df14 | pending |
| CL-04 | /corrections/ | Each entry states what changed, when, why, and who reported it. | 9d75a3a179538c448c8a1f5a9f07c8d8d8ef352485c79e9a428b6181f961e121 | pending |
| CL-05 | /corrections/ | The earlier value is preserved on the append-only record; this link records the belief date at which it stood: belief {e.previous_belief_date}. | cea99a8d0da643706ed370f943cc23bdd88b446fce43f80101e7fed67ce89d6e | pending |
| W-05 | /watch/ | Attach this to public comment. | de24c7cbeb10d477ebad2fc39843327b484c1f155328247e0bafae1e86d4e452 | pending |
| W-06 | /watch/ | Every entry carries a link recording this build's belief-time and as-of date. | 55f3675771347a5a8416cc3bed899ba9702829f59931e09ee056356311c6d9d5 | pending |
| W-07 | /watch/ | Download as plain text. | 1b51de3bc5d1eeacf112592bff8f86acbd83b9afde7a8346c39eebbc86c93e35 | pending |
| M-20 | /methodology/ | These measure SIG's method, on a named, frozen holdout — never a device population and never a capture–recapture estimate. | 8678905637863ed3c22e0c24776fcb72ba57961c1fda64a7c81a21c0669f3993 | pending |
| M-21 | /methodology/ | The full report and its generator are committed with the build. | c1c1e7fb983206e35f8078a07937dfb5915acef2d64a22ff0effd817c54a5579 | pending |
| M-30 | /methodology/ | The SIG-authored data SIG offers upstream to OpenStreetMap is dual-licensed CC0-1.0 for that purpose. | 5032db231128673a97f3099e5cd127deb44d4f27e85c7dfc3cd39ae182e58e60 | pending |
| T-01 | /task/new/ | Return to the dossier index. | b6568bcc2bb151c7ea20087dd140f32c33da21817b4d766bdfab785337334558 | pending |
| DF-01 | lib/dossier-fixture.ts | A 'shares data with' edge to the Oklahoma County Sheriff is recorded but contested; the full partner list is not established. | f76a7cf92d0e8cf50ba3ad1eb447d0a7023f7e1337a7a3785c50f64c2bfc9ea3 | pending |
| DF-02 | lib/dossier-fixture.ts | A lower bound. See the infrastructure map for locations at published precision. | 5e91229992e0dea8651b85c52414202d4a99d12e313b8ce9fd43119fd209d911 | pending |
| DF-03 | lib/dossier-fixture.ts | Infrastructure map | 85e5272bd7063b11f5a2b208ce17d0593e75688da3be96f665e8246159e78112 | pending |
| CM-01 | lib/corrections-methodology-fixture.ts | recorded contradictions | d9ad443d30fbd63cc8a60c2e2491e04e15c79d1455ef2c71987641ef46503b08 | pending |
| CM-02 | lib/corrections-methodology-fixture.ts | This page shows only the recorded count; SIG does not publish a contradiction browser. | 475087caa6d404c136dd87585451c61a0a0fe887a972da6ec6b6c399cf087722 | pending |
| XD-01 | exports/web_dossier.py | A 'shares data with' edge to the Oklahoma County Sheriff is recorded but contested; the full partner list is not established. | f76a7cf92d0e8cf50ba3ad1eb447d0a7023f7e1337a7a3785c50f64c2bfc9ea3 | pending |
| XD-02 | exports/web_dossier.py | A lower bound (OSM/ODbL). See the infrastructure map for locations at published precision. | cca9a622971c86076c7524e9679625e4ebbe7982a78a3506651c3db4b334ba05 | pending |
| XD-03 | exports/web_dossier.py | Infrastructure map | 85e5272bd7063b11f5a2b208ce17d0593e75688da3be96f665e8246159e78112 | pending |
| XC-01 | exports/spine_export.py | recorded contradictions | d9ad443d30fbd63cc8a60c2e2491e04e15c79d1455ef2c71987641ef46503b08 | pending |
| XC-02 | exports/spine_export.py | This page shows only the recorded count; SIG does not publish a contradiction browser. | 475087caa6d404c136dd87585451c61a0a0fe887a972da6ec6b6c399cf087722 | pending |
| HW-10 | component/HowWeKnowThis | These totals describe the {pageName}'s own evidence, not the whole record. | 334535f8afc75bcc1a78527cd3a510f2b70b8d30c6fd386329ec37520f7cfc1f | pending |
| RQ-01 | lib/research-queue.ts | not yet classified | bb563272ba6e0dd5a84d94137f0156a345d8f3d0041bd9d54046978086209c48 | pending |
| XC-03 | exports/spine_export.py | not yet classified | bb563272ba6e0dd5a84d94137f0156a345d8f3d0041bd9d54046978086209c48 | pending |
<!-- P34.12: T-01's page (/task/new/) is RETIRED — the row stays (append-only
     history of the drafted sentence) but can never ship: no page renders it.
     The P34.11 binding test carries T-01 in a RETIRED set, not in the
     carried-somewhere check. -->

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
