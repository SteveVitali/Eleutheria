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
| title | /404.html | Page not found | a469ab4ca4e55bf547566e9ebfa1b809c933207e9d558156bc0c4252b17533fe | pending |
| NF-01 | /404.html | This address does not name a page in the published record. | 4bf6a31cea6b0b3cdd530bb9d4edf0f544c14284521d5179de8018e49937e036 | pending |
| NF-02 | /404.html | Go to the home page | adceddedfd5962e31a232a284d14ee514b150e8baed9faeb7c9ca217623de072 | pending |
| title | /403/ | Access refused | 07edbc210200672dd22b8675ff412e2dfb0bdb32cd35bf98f215643a2969b360 | pending |
| FB-01 | /403/ | This address is not open to the public record. | 1c53fb5591a3cb3bd20d3db1adf0b367f3ce267d630b06302ad5cbafaca29e8b | pending |
| FB-02 | /403/ | Go to the home page | adceddedfd5962e31a232a284d14ee514b150e8baed9faeb7c9ca217623de072 | pending |
| title | /410/ | Page removed | 07bfb4386863abf77f91715a0bc1ae0a6ee8db3a005d952e9161e6b0a4f8367e | pending |
| GN-01 | /410/ | Go to the home page | adceddedfd5962e31a232a284d14ee514b150e8baed9faeb7c9ca217623de072 | pending |
| title | /terms/ | Terms of acceptable use | cd9c8f9815b668373aa0e899adeed724126616c1fa133c171edaa919c4739a18 | pending |
| TR-01 | /terms/ | The acceptable-use terms are served by the read API. | e22ca2017eb209fce805f46a746b5acb626149dafa14c854d1fdea25379ca6b4 | pending |
| TR-02 | /terms/ | Open the API terms | c9e30377375fad6ba26cb3435ab8eb4f6f6cfbc354828fd0f66f39f7e09aef8c | pending |
| title | /data-freshness/status/ | Data freshness — sorted by status | d71bef933ccd036a923cf641eb9417338d97a523423285f20db56f0b53906fe7 | pending |
| HW-11 | component/HowWeKnowThis | — site-wide | 38e27b025baf2b029337868415e2ada529c1d2a9ed169219699b18283740862a | pending |
| HW-12 | component/HowWeKnowThis | — {pageName} | 75431417c85a646c90b86306a022e7efc5b7cd89833e41808e5786632f577d1b | pending |
| HW-13 | component/HowWeKnowThis | — this page | 2abeefadfd80aed1a6c7c4cb12b9e6730d153cccf440e66b800bfb978370c329 | pending |
| MD-01 | lib/meta.ts | ${title} — Surveillance Infrastructure Graph (SIG) | b0f3d7cd012e8c848f0b0b5a39e533fbcdbb63229dfad78d2f33082486f11d52 | pending |
| WM-01 | component/BaseLayout | SIG Surveillance Infrastructure Graph — home | 626b082b24a64831515e39f3f6830f963e38e56f3a291f870ce0e4312e116463 | pending |
| JD-01 | /dossier/[slug]/ | This dossier combines {combinesList}. | a4ca28564fa4004f5cf5dc38b14730e16b0d6a863ec7680b97e32bd3ede366ea | pending |
| JD-02 | /dossier/[slug]/print/ | This dossier combines {combinesList}. | a4ca28564fa4004f5cf5dc38b14730e16b0d6a863ec7680b97e32bd3ede366ea | pending |
| JD-03 | /dossier/[slug]/ | A jurisdiction code SIG has not yet named is on this page — flag it in the research queue. | 5796d1b02c7514d060d2f1553ec48464f0676894c92f8f30cbf8ade25e2b2258 | pending |
| JD-04 | /dossier/ | A jurisdiction code SIG has not yet named is on this page — flag it in the research queue. | 5796d1b02c7514d060d2f1553ec48464f0676894c92f8f30cbf8ade25e2b2258 | pending |
| JD-05 | /search/ | A jurisdiction code SIG has not yet named is on this page — flag it in the research queue. | 5796d1b02c7514d060d2f1553ec48464f0676894c92f8f30cbf8ade25e2b2258 | pending |
| JD-06 | / | A jurisdiction code SIG has not yet named is on this page — flag it in the research queue. | 5796d1b02c7514d060d2f1553ec48464f0676894c92f8f30cbf8ade25e2b2258 | pending |
| JD-07 | /dossier/[slug]/print/ | A jurisdiction code SIG has not yet named is on this page — flag it in the research queue. | 5796d1b02c7514d060d2f1553ec48464f0676894c92f8f30cbf8ade25e2b2258 | pending |
| MP-01 | /map/ | The surveillance-infrastructure map. | 12aff29a27641cab7020fd119b1e7d4b86fa3c23c53842ecd7e4e66f261eb59f | pending |
| MP-02 | /map/ | Everything the map shows is also in the tables below — they are the equivalent, not a fallback; the interactive map is an opt-in enhancement that loads only when JavaScript runs. | 67f6d63f004d51fd5edbaa40a4fdda4ee93001806fe05255ba8bb1cc18b50644 | pending |
| MP-03 | /map/ | The tiles are self-hosted static vector archives — no third-party tile CDN is required. | 270eb5c4ae17c74f0c14b3d45bcca350ff0aef33ad867ed19f510ea9c5017edd | pending |
| MP-04 | /map/ | Layers with no records in this build are not listed. | e7e3bfa354472e33636741ba6f1f375b58e67c3ee0bccf1a04a028feaa55a52b | pending |
| MP-05 | /map/ | Records | 47a84e92d5b225ee185aff8a30bafb3240a41b84c740bcaeac43772dd7f2fd37 | pending |
| MP-07 | /map/ | Located records (tabular equivalent) | 2bc1ccefb36c0461c7c1a42ed19af5c60298b78890d9c3b2a44b3dfe987777cb | pending |
| MP-08 | /map/ | Record | bfdd510698ef3ccbf17f2c67fc47790e1ba72894fb74fe284bbc136b47ef73e6 | pending |
| MP-09 | /map/ | Showing the first {locatableRows.shown} of {locatableRows.total} located records | a626dba9ae581d2fd948bc6c721e1719fdd3dc5e57ad0ea2690750957e4d3671 | pending |
| MP-10 | /map/ | Records without a published point | e31851bcc8a602c15a3eae5d1339c520d805fdf724fa8e347935d20f5415933b | pending |
| MP-11 | /map/ | {j.count} record(s) with no published point. | 5b3267efa4d964896c061d251eceebd7519e383e68fa8b4746a59c981f64967d | pending |
| MP-12 | /map/ | — {contested} contested; see the {j.jurisdiction} dossier. | 254d212030a35e9678e655f477c36682e4e015afbc22edbc0be17fc32ceff128 | pending |
| MP-13 | /map/ | — {contested} contested. | 1d2873f6fe6e2a67ea76a369b86d7981fc9db2f3d2e3fcfc4e1bdebacf5e3284 | pending |
| MP-14 | /map/ | Records with no coordinates — or whose sensitivity tier forbids publishing a point — are not dropped. | 98809f22f8abccd0ae846ad2e63ba601c575c3c80443e083fc7cb277bbec2ecf | pending |
| MP-15 | /map/ | They appear as jurisdiction-level indicators, so the map does not systematically understate capability (SIG-UI-020). | e1fbd1e4b704366c7adf702d6997aae397fd717f1bb5b0c44b96a2ffff408299 | pending |
| MP-06 | lib/map.ts | suppressed | f63d5b6b4de4fca716f2be8a179211b92682dc2e030b7063aea1d4a210f40033 | pending |
| NW-01 | /network/ | SIG has not merged organisations across sources — one agency can appear more than once in these lists. | b8407ad50425890711a7e3d256741339dc7fe76aa36ce455fb489e1656a57cdc | pending |
| NW-02 | /network/ | No centrality or hub ranking is published; the resolution review that would make one honest has not passed its gate. | ea36b45843d56aff5111119c735e0587a3b14b26598079b42263d73d728f46fd | pending |
| NW-03 | lib/empty.ts | Network statistics are only as good as entity resolution; SIG publishes none until the resolution review that would make one honest has passed its gate. Their absence is not a measurement of zero. | a14feda910497bd8567d0fc2df6e25562668118b780c88474fccc992f8960692 | pending |
| WS-01 | lib/workspace-state.ts | This address names {facets}, which this view does not apply — they do not filter what is shown. | 8abde874a4456f5a5687983935170b1ae1a712159a46970daf628b5c4969515c | pending |
| GC-01 | docs/governance/governance-and-code-of-conduct.md | SIG does not yet have an editorial board. | f37f6b4ed1822a9066db7b6bd2545944380b675c7587126a9d6ebbcd31d575ba | pending |
| GC-02 | docs/governance/governance-and-code-of-conduct.md | Until it does, editorial decisions (contested claims and sensitivity classifications) are made by the maintainer and recorded publicly in the editorial decisions log. | 764e01a9d5d9fee8da546c2a5180ba7ab673e9911d25baa48e0f4a1631284b5d | pending |
| GC-03 | docs/governance/governance-and-code-of-conduct.md | Officer and person naming is turned off. | 44526964e7f357d3abc771dde05f985a456096e9fc4f62dfa6802cf2e365e5b8 | pending |
| GC-04 | docs/governance/governance-and-code-of-conduct.md | Published on the maintainer's own rights and publication decisions. | efee2089e2fa2a2532d5ce21a55acab761a8829be02ac7ed579e6b8aa194201f | pending |
| GC-05 | docs/governance/governance-and-code-of-conduct.md | No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel. | f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f | pending |
| GC-06 | docs/governance/governance-and-code-of-conduct.md | Published on the maintainer's own rights and publication decisions. No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel. | c7e4f78bcd07b99b9a656c2bc4e6e56a19be7fd86b5d2329b2447414348a6e02 | pending |
| GC-07 | docs/governance/governance-and-code-of-conduct.md | SIG has been public since 2026-09-16. | 20e5a4d4c2f2e92b87876e068fa0ac2e5ec7a4de5d178518926274973ecde2d8 | pending |
| GC-08 | docs/governance/governance-and-code-of-conduct.md | A second independent reviewer has not yet been appointed; Round-11 releases state 'single maintainer, no second reviewer'. | 86241b8fc1f653e6d121a8c1eaa929f4bb0ac6c37d2e4b8e726aec0ee6dcd17d | pending |
| GC-09 | docs/governance/governance-and-code-of-conduct.md | Corrections come by e-mail; senders disclose their address. | 5fd09424c73234803b5bb180fab78154805e361fcb2368b30504b7a93d44fa5f | pending |
| GC-11 | docs/governance/governance-and-code-of-conduct.md | The five registry determinations earlier recorded as 'counsel (HG-02)' were the operator's own (no counsel). | fbeb4ee0b228bb7963cc2f95bc6dab3b13c70fa5e957e5c523b89ad680bc5604 | pending |
| SL-01 | /sources/ | Sources and licences | 6adf604fbf18a253bb12576a4d3acb2b7063cc4b12c616c01d7e2dec5fde0181 | pending |
| SL-02 | /sources/ | Every source SIG publishes rows from is listed with the licence its rows are filed under; a source whose express terms the operator accepted the risk of republishing shows its captured terms verbatim and the basis on which SIG publishes them. | dade1f541a5426dc989bb96a3b1d95291be65f9c93d371093217d9e8760db239 | pending |
| SL-03 | /sources/ | Published under the operator's recorded acceptance of the express-terms risk (ADR-183); the source's captured terms appear verbatim. | d6255f667f05ac5cb412b91e2c18ddbcccb7b46150eb6c32172f6d60294743a4 | pending |
| SL-04 | /sources/ | Scheduled refreshes of these sources are covered by the same acceptance (SB-2); a new source carrying a non-commercial clause is added facts-and-pointers only (A-9). | a8c94b85ec36e2c2839f6e296a34bfde0b779b49bca5996ccff436bbf1bbfe4d | pending |
<!-- P34.19 (F-403, ADR-183): the interim sources-and-licences page's
     disclosure sentences — page title, the page explainer, the per-source
     basis line and the refresh-scope sentence. The captured terms verbatim
     and the basis string are DATA (sig.terms-disclosure/1 via
     `getTermsDisclosure`), not drafted copy — the rows below pin only the
     page's own framing. The page slug `/sources/` names the intended
     interim page P34.17 builds; if P34.17 renders under a different slug
     the page column is updated by that run (the sentence text + sha256 are
     what B-2 pins). All pending — none ships until the operator confirms
     it verbatim at a copy-batch sitting (B-2). added 2026-10-03. -->
<!-- P34.16 (F-189, G2 0c): candidate sentences for the governance
     doc's Corrections section — GC-01…03 are ADR-164's E2-03 drafted
     wording verbatim; GC-04/05 and the combined GC-06 are ADR-167's pinned
     publication-basis forms (the ADR records their sha256: f62f9e98… for
     GC-05, c7e4f78b… for GC-06 — the row pins must equal them); GC-07…09 and
     GC-11 are agent-drafted record candidates (GC-10 was dropped pre-commit:
     the doc cites the /dispute/ page's own words, so no drafted sentence was
     needed there). All pending — none lands until the
     operator confirms it verbatim at a copy-batch sitting (B-2); the
     section's sentences state the posture only in the operator's adopted
     words until then. added 2026-10-03. -->
<!-- P34.15 (QW-12, K1 NEW-20, K12b NEW-7, K2 NEW-6, K6 NEW-1): the map's
     "records" vocabulary and dropped-layer/suppressed-count honesty, the
     contested-count → dossier lead, the network's merged-organisations and
     withdrawn-ranking sentences, and the islands' ignored-parameter notice.
     `{locatableRows.shown}`/`{j.count}`/`{contested}`/`{j.jurisdiction}` are
     rendered template placeholders (the `{combinesList}` precedent — the row
     pins the sentence shape); `{facets}` resolves in facetNoticeText to the
     reader-facing parameter names. MP-06 pins the constant a value-suppressed
     bin prints where its count would stand; NW-03 pins the (currently
     unrendered) centrality empty-state body. pending — added 2026-10-03. -->
<!-- P34.14 (QW-8, K4 NEW-1): the mixed-bucket sentence and the unmapped-code
     flag. `{combinesList}` is a rendered template placeholder (the HW-09
     `{provenance.denominator}` precedent — the row pins the sentence shape)
     resolving to JURISDICTION_COMBINES in web/src/lib/jurisdictions.ts, which
     renders "Idaho (US) and Indonesia" on ID and "Minnesota and Mongolia" on
     MN. The unmapped-code rows ship on every surface that shows a jurisdiction
     name; the element renders only when a code the table does not know reaches
     it — none does today. pending — added 2026-10-03. -->
<!-- P34.13: the 410 body and the /terms notice are notice strings N-6 and N-7
     verbatim — they ship by sha256 under B-2's notice allowance (until
     GATE-G4), not as batch rows; `data-notice` records which string each is.
     The /terms forwarder is noindex chrome; its redirect target is the API's
     /terms (SIG-API-013), not site copy. -->
<!-- P34.12: T-01's page (/task/new/) is RETIRED — the row stays (append-only
     history of the drafted sentence) but can never ship: no page renders it.
     The P34.11 binding test carries T-01 in a RETIRED set, not in the
     carried-somewhere check. -->

<!-- P34.17 (the honesty wave): the dispute/corrections rewrite (B-8 e-mail
     intake, WV-05, WV-08's published order with no time promise, C4 NEW-20 —
     no requirement ids in copy), the truthful hostile-reader absence
     (ADR-179), the register sentence without a counsel/board reading, the
     methodology development-evidence disclosure + publication-basis label
     (H-6 — PB-01/MB-01 pin GC-04's text, PB-02/MB-02 pin GC-05's; the sha256s
     must equal efee2089…/f62f9e98…), the interim release stamp (A-20), the
     footer dispute link, the new /status/ page (N-7 + currency), the /sources/
     licence table labels (SL-01…SL-04 were P34.19's), the /terms/ legal-home
     sentence (TR-03 = ADR-165's E2-04 drafted wording verbatim), and DC-20.
     `{intakeAddress}`, `{releaseId}` and `{asOfWorld}` are rendered template
     placeholders (the `{permalink}` precedent) — the injected operator
     address and release values are DATA, not drafted copy. DP-07 and
     OC-01…OC-05 are literal rows bound to `web/src/lib/corrections.ts`.
     SUPERSEDED (kept, append-only, bound to nothing): CL-03 → CL-06 (the
     requirement id dropped), M-20 → M-43 (the "frozen holdout" claim), DC-19 →
     DC-20 (the dispute page now names the contact address). All pending —
     none ships until the operator confirms it verbatim at a copy-batch sitting
     (B-2); `sig-ops publish-web` refuses a pending sentence in the tree.
     added 2026-10-03. -->
| title | /dispute/ | Dispute or correct a record | a04bfebf57e010475aa09c31e44b4d2637f928a30eb80fb06dd8b2eab37330c0 | pending |
| DP-01 | /dispute/ | Anyone can ask SIG to correct, annotate, suppress, or remove a record — or dispute an accurate one and attach a response. | f32c43da5255e94e8dd862376d760b7f3afdbac48f9aed708be17a1b2c465987 | pending |
| DP-17 | /dispute/ | How to report | 2ee208947047ae0ba02b0655a4b405b2f0552ec8fa28ed8c077f770b21bb37e4 | pending |
| DP-02 | /dispute/ | Reports and corrections arrive by e-mail to {intakeAddress}. | c07aba28bc06f8483773a8ca2a5dba6808416db9f4e90c173ff80b30f7e78e5b | pending |
| DP-03 | /dispute/ | Senders disclose the address they send from. | f4698409e5262dd7cc04cd03ee9ed35dd01c9a16b6b63de93c2c6400e3644056 | pending |
| DP-06 | /dispute/ | SIG promises no response time. | 4f54dfc91ffacf12c94d3eecace3704eb8f3560736d32cfa9a8b1baa3f7d589c | pending |
| DP-04 | /dispute/ | Do not send licence plate numbers or personal details about other people. | 6a99d2cbc1dd46d3206319c75bbc98d075ffdf3d7d72bdda036d0d9a81b7291c | pending |
| DP-18 | /dispute/ | Handling order | f6ddc8855156e0120669dd7a98233f50e77ed8231e440785e8e3757d181bffbf | pending |
| DP-05 | /dispute/ | SIG handles reports in this order: privacy-harm and safety reports first, then factual corrections, then everything else. | 2a9c1c3ae27314276fe1dc7f5584ce8e1937c68daf1afc8c1b040ffff1446845 | pending |
| DP-19 | /dispute/ | What are you reporting? | 98ba943343164139af7cba397417f0d11f637603c4325cbd591b94629a8fe996 | pending |
| DP-15 | /dispute/ | (handled first) | 81555b13619b02d489e6594b1829b2c1b4904031540f897cd532b45e7a560001 | pending |
| DP-16 | /dispute/ | (may require standing) | f9381a797b894d216298a314f18e6153682b3663c065987a2b1bf9e9cd412a69 | pending |
| DP-20 | /dispute/ | What can happen | 2dec45f7e5bd11d76a5105833939580f17420367fbb5aa3dc959ca79b56f31aa | pending |
| DP-08 | /dispute/ | Correct — a new, corrected assertion is appended; the prior value is preserved and stays citable. | be882729a7b7a53ee73667bc40cf5de545732f069008f3a431e4e8e2ea21e763 | pending |
| DP-09 | /dispute/ | Annotate — a response is attached alongside the claim, even when the claim is accurate. | 7081c212773b05ada56b5c7e7ed6157abcdbd0b1dfe645ff9546b72f140e5290 | pending |
| DP-10 | /dispute/ | Suppress — removed from public view, retained internally under seal. | da6beda42e61a6ef4a728c5bed06f8086214d004485074b59386b87d8cd6350f | pending |
| DP-11 | /dispute/ | Delete — reserved for material SIG must not hold at all; a content-free tombstone records that a deletion occurred. | 0be80e6969c22c0abdf82a3acb60cea849b49f6777338b34f1eee2665aaa0b00 | pending |
| DP-12 | /dispute/ | Refuse — declined, with published reasoning. Refusal is a real, exercisable option. | a15014902733cf64ab89d45572e5e1c61f7e06d3e459f69a82213ff5d8e46e6e | pending |
| DP-21 | /dispute/ | The report form | b9e121b7aae5730bc88a862491166c46f80390556666480c624e105896dec489 | pending |
| DP-13 | /dispute/ | Until then, e-mail is the channel — it carries the same categories and the same outcomes as the form will. A report is never an automatic correction, suppression or takedown vote. | 9536c4e80df78e7c8a4a9c79d384f4c39619f56cc8466bc519e4331c07e14879 | pending |
| DP-14 | /dispute/ | Dispositions and their outcomes are counted in the public corrections log's transparency report. A correction, once made, appears there in full. | 3d58406b98498647864f2d2d1aecc0d9f015716d2b9762c121f99e27e8cf5955 | pending |
| DP-07 | lib/corrections.ts | An online report form is not operating yet — it opens only after a staffed moderation owner, a ratified retention schedule and the public-exposure decision are approved. | 0a4b850bd3a79e9b703fdc0e3f1c286dc6a4e19ea793203d1190af9d4f0e7312 | pending |
| OC-01 | lib/corrections.ts | A new, corrected assertion was appended; the prior value is preserved. | a1a94a5039a90579e6c68c14419d2268deb5c037b35eab510d9cbbd3863aa679 | pending |
| OC-02 | lib/corrections.ts | A response or annotation was attached alongside the claim. | ecf79dbe42c7f36c44d400ef4bb50177357d35f22a2530d1bfbb1ae41c4b1de6 | pending |
| OC-03 | lib/corrections.ts | Removed from public view, retained internally under seal. | 974c23c888e0aa77fbf1acf32f7a6326423ce03d652b84884a9efb521b25c3de | pending |
| OC-04 | lib/corrections.ts | Deleted entirely; a content-free tombstone records that a deletion occurred. | da7f8788394889b5b475dd59aa2b09daf8872e7dedd2c50cd714ed7534a9c402 | pending |
| OC-05 | lib/corrections.ts | Declined, with published reasoning. | 3411cbf6f496d0a2ae1cf8e7c13274f3613d7e0d3ff2176ba582b3ceb91bdad6 | pending |
| title | /corrections/ | Corrections log | 146309a25c86310d99f2444bfafca0efcc44273f0cc8777137f9de14eb8d5b28 | pending |
| CL-06 | /corrections/ | A correction is a new assertion, never a deletion: the earlier value is preserved, and each entry names the belief date at which it stood. | 7c51a07865ff040d611e6e3715485fe693444f9de421cfec3e6014b17cd17555 | pending |
| CL-07 | /corrections/ | Reports and corrections arrive by e-mail — the dispute page states the address and the handling order. | 2050d5f0e26370c4ba67a6ba431041ea9fe6f320017d3e5b3a1bc1cb701dddda | pending |
| title | /editorial-standards/ | Editorial standards | ad5fad9228634cbd5e8ea56612d0e83d5e65a0e9d83dfa218a8bc7abefecadb6 | pending |
| ES-01 | /editorial-standards/ | SIG's editorial standards are what make its record usable as evidence. The style guide codifies the register rules; this page records the worked example cases and the state of the hostile-reader review that gates each dossier template version. | bc4bdf5284b21d9a98ccf6966ad2f43c6865b7492e12025df2070695ae142695 | pending |
| ES-02 | /editorial-standards/ | Conformant copy for the three hardest cases: | 8fe375d25c7a770bd7ed3cf6461a22079f618958da12849f25f6f75bc72c2933 | pending |
| ES-03 | /editorial-standards/ | Before a dossier template version is released, the standards call for two independent readers to read a real rendered dossier from the documented organization's point of view and log every sentence they would challenge. No such reading has taken place; a previously published record describing one was incorrect and has been removed. | d1e7154665655a0dae9e96a31de14c676869d98f276af96efba1bffefd3c6f84 | pending |
| ES-04 | /editorial-standards/ | The release block is waived for this round; the waiver and its reason are recorded in the project's decision log. | 9c4c62a5f4abb4379800e9793089105c186b73f87d0ee2013537c700829ecd63 | pending |
| ES-05 | /editorial-standards/ | The recorded review, its findings, and their disposition are committed alongside the template version. | 15006d109e8422f0399a299f9a7abf17a6dba3c62723c73dfcf6eca0457d0145 | pending |
| title | /style-guide/ | Editorial style guide | 1c752cf2357ea435cd30d988b2e03839f058a059d84171fbaf28371494bda72f | pending |
| SG-01 | /style-guide/ | SIG's register is what makes the work usable as evidence: a reader whose own organization is documented should find the dossier accurate, neutral, and hard to attack. These six rules govern every published sentence — including generated rationale text, which is published text and is held to exactly the same standard. | 7924ad7804ee015e5e4ba3d745df6c39a6bd683c98d00d0587de3cd05e36d590 | pending |
| HO-30 | / | and it is listed in the research queue. | ffa9d272ee091080d406cc11212ce8246ff133efc69d172e22e41a1beef3b1f3 | pending |
| M-40 | /methodology/ | Matching quality: development evidence only. | 97290b55142bb53f7e4e1af9cbc635a133dadd3a173767b57f8680086affacca | pending |
| M-41 | /methodology/ | The label sets these rules were tuned on were produced by an AI model and by agents; no person labelled them. | f7d32e9341729e35a0e63aeee305e767b1c4ab42c9b22236d258a1bc4e0f689a | pending |
| M-42 | /methodology/ | SIG is changing the merge rules so that only copies of one upstream record are merged. | d69beb3b08230a1c108736aba5673ef7143d71b78335517c587d530f463f641e | pending |
| M-43 | /methodology/ | These measure SIG's method, on the named holdout each row names — never a device population and never a capture–recapture estimate. | ec9d8d6633d887f551a108296b4ae567bec7f58977990e57653b6677742f2e48 | pending |
| MB-01 | /methodology/ | Published on the maintainer's own rights and publication decisions. | efee2089e2fa2a2532d5ce21a55acab761a8829be02ac7ed579e6b8aa194201f | pending |
| MB-02 | /methodology/ | No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel. | f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f | pending |
| RS-01 | component/BaseLayout | This site shows release {releaseId}, data as of {asOfWorld}. | 19d18b7a3ff034f1779796c385b2e4f3c22a8b870929c2a39242bc163e02cb7f | pending |
| RS-02 | component/BaseLayout | The public API is updated continuously and may show newer records. | 2e646c8d6b0d06258a65760e833ad34e4e8660608d234d2e9400941a122c4e90 | pending |
| RS-03 | component/BaseLayout | This is a development build. | 5ae20730cc116cd2b2aad7adf249e783613a81769da4a38228267cbd8aaa9698 | pending |
| PB-01 | component/BaseLayout | Published on the maintainer's own rights and publication decisions. | efee2089e2fa2a2532d5ce21a55acab761a8829be02ac7ed579e6b8aa194201f | pending |
| PB-02 | component/BaseLayout | No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel. | f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f | pending |
| DL-01 | component/DisputeLink | Something wrong, or a privacy or safety concern? Dispute or correct this record — reports arrive by e-mail. | 192aa8eb68086abceaae5d26e88f7c5ea8cb1db6981c40901db3143f32be040d | pending |
| title | /status/ | Status | 920e413c7d411b61ef3e8c63b1cb6ad058d5f95f8b481dbafe60248387d8c355 | pending |
| ST-02 | /status/ | This page names what is known to be wrong right now and how it is being corrected. | 5f1ce8898ad72dd270284fd8ae498f580a5393c9eeadfe390c6716402dcd85be | pending |
| ST-07 | /status/ | The API | f869fbbc138cf69b93d7d7618940351fc5c10365a5e70a4d416221e90da3ddec | pending |
| ST-03 | /status/ | The fix ships as part of a later release; the wrong answers stay live until then, marked here rather than hidden. | 1142c28161a0d785b6adee5bc51f7f214b1bd80d581733a77b1a4444abc3b2c4 | pending |
| ST-08 | /status/ | How current this site is | a5ba4964578efad3529accdb9cc14492df70b046b4bc38f4eac8969e75e0551a | pending |
| ST-04 | /status/ | This site shows release {releaseId}, data as of {asOfWorld}. The public API is updated continuously and may show newer records. | b7c50fafbb13c268f0ff1cb65fd5a2fe29c7bf7b67067aab0be7d8ef5a4ee626 | pending |
| ST-05 | /status/ | This is a development build. The public API is updated continuously and may show newer records. | 3e6bb805ad38f2dfc38290bdaaa3503cf04d0d9a09f48b63df964b02a3256785 | pending |
| ST-09 | /status/ | Reports | dacca3cba3f346a40893112b8670f453650a81138e3705c0034d2392024b9797 | pending |
| ST-06 | /status/ | Corrections and safety reports arrive by e-mail — the dispute page states the address and the handling order. SIG promises no response time. | 1f5163266bbccf5fc5481c734e1740a8aa9663196007e71e4ad5961e6b86616b | pending |
| SL-05 | /sources/ | Some credits are wrong or missing where the licence requires one; the correction notice above marks them, and the next data release replaces them. | 0bf6b500ba3b72a529cece789ce7b877729726074c71c381b9d6745efdc05876 | pending |
| SL-06 | /sources/ | Source | 0e570ca6fabe24f94e52c1833f3ffd25567022beb826fa16891f3322051bc221 | pending |
| SL-07 | /sources/ | Licence | f3ec8e880a46c8a6fb105396ee5400124f828934a9dd68c668f796cf6d47b1c8 | pending |
| SL-08 | /sources/ | Rows | 101f2ff3de22441fcab3e15ca0b09ac3428642cf628558f16fa404fc3137baea | pending |
| SL-09 | /sources/ | Credit | fb1875d0a5e85f29f239c293e5837e234fa07068b040fd11c2078c28df7d72d4 | pending |
| SL-10 | /sources/ | Terms | ede5489964834a514b61c7a4a8370be2452dd4a7d807180f14991ccc11ad2430 | pending |
| SL-11 | /sources/ | No source in this export carries express-terms rows. | 1d6b431c01aa81d4423d7783930495a57f4f53f3f519e1e641cd7d3da771d3b2 | pending |
| SL-12 | /sources/ | Sources and licences | 6adf604fbf18a253bb12576a4d3acb2b7063cc4b12c616c01d7e2dec5fde0181 | pending |
| SL-13 | /sources/ | Express-terms sources | aa1d616f6da77da61b01f4878398df5d8eb659519866a7fa6f87e43e837e167d | pending |
| SL-14 | /sources/ | terms | 51d2361f4faea3bc8f9facdbc7d99abb555596a2e51f7b25fd3b41c93587e616 | pending |
| SL-15 | /sources/ | express terms below | cfcefd516480abf1874f09eed8797c254f37f4a5c1fc8b8a405338f2fd8caaad | pending |
| SL-16 | /sources/ | Captured terms (verbatim) | e1d2fdad5d193bd747caff5998a7a7e86ddfb69c96161542bbd85f04cb6dd7c0 | pending |
| SL-17 | /sources/ | Terms page | 057b2bd7d6e3873ce19870eb5990d16bd072dcac4aaa430cc100152f098bfdc3 | pending |
| SL-18 | /sources/ | public rows | 4f8ae65b9e79eac15474e29b3d000e9559cc24d17b3cf70af495cbec80655622 | pending |
| SL-19 | /sources/ | rows in this export | 5f285b2ea8a9a93acb17cd852cb4478aab4e53ca25b4fd4ae5b7cff98cc94f01 | pending |
| TR-03 | /terms/ | SIG is currently run by an individual maintainer, not by an organization. It has no fiscal sponsor or incorporated legal entity yet. | 278a8979b859186856c836555c81bf28671f1ab8599e1eec45f0dcdf0f4721b8 | pending |
| DC-20 | /data-collection/ | The dispute page names the contact address and states its own operating status. | 807abbdea05119fd2521ee1c2573421053639107963ffcd561c342cbe16a8bcf | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
