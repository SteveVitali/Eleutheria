# Copy batch 16 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P36.64 (row 407, UXK14-6 — home/About/how-it-works/methodology
     hub). Append-only, same convention as batch-01: rows are never deleted or
     edited in place; a status change is recorded in the confirmation log with
     a `date -u` stamp. Id prefixes: K14-* = the D-K14-1 [C-4] lines; IB-* =
     "In brief" leads; PC-*/DF-*/RK-*/TR-* = / rows; CP-*/CB-* =
     lib/capabilities.ts rows; AB-* = /about/ rows. -->

## Convention

Same as batch-01 (`docs/build/reports/copy-batches/batch-01.md` § Convention):
`pending` = agent-drafted, awaiting verbatim confirmation · `confirmed` = the
operator confirmed these words verbatim. P36.64-specific rules:

- **The K14-01…07 rows are HELD — they bind no element anywhere.** D-K14-1
  [C-4] (the plan cell, verbatim): the sub-head, the About paragraph, the
  why-it-exists line and the four "is not" lines ship ONLY after verbatim
  confirmation — they are registered here `pending` so the operator's
  copy-batch sitting can confirm them, but they are never rendered as shipped
  text meanwhile (the page ships without them, never with placeholder prose).
  `tests/unit/test_p36_64_copy_batch.py` fails if any K14-* text appears in a
  `web/src` file, and fails if a "who runs SIG" section or placeholder exists
  anywhere (D-K14-7 [C-5]).
- **K14-00 is the exception**: D-K14-1's answered half — the tagline ships
  now, confirmed verbatim by the operator's plan-cell answer (recorded below;
  the answer is the operator's words, not an agent's).
- **`{reviewStatus}`** is a rendered placeholder (the `{combinesList}`
  precedent — the row pins the sentence shape); it resolves to the
  provenance row's recorded review-status label at build.
- Example-question chips and persona step labels are generated/navigational
  text bound to release data (`lib/onboarding.ts`), not drafted prose — they
  are covered by the example-contract e2e, not this register.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| K14-00 | / | Public surveillance, traced to the documents. | e997a77e482bcd29e294ee9008c8eb7d69fad00ec3a24a6b61b48c3010786f6e | confirmed |
| K14-01 | held | SIG joins public records about government surveillance so anyone can see, for a place, what is deployed, who runs it, who can access its data and when it is next decided — with every fact linked to its source, every disagreement shown and every gap labelled. | d5418f0b13b476a3922cc1c00434c0d96ae9d8f2ee9bfc9ec2be5cf3f8218f18 | pending |
| K14-02 | held | The Surveillance Infrastructure Graph (SIG) is an open record of the surveillance technology public agencies use — licence-plate readers, camera networks, real-time crime centres, face recognition and more — and of the contracts, policies and data-sharing arrangements behind it. It joins many independent public sources: agency and vendor disclosures, contracts, council records, grants, crowdsourced maps and records releases. Every fact stays linked to the document it came from. Where sources disagree, SIG shows both sides. Where SIG does not know, it says what kind of unknown it is and what would settle it. SIG is not another camera map and not a census: it reconciles what others publish, links back to them, and turns the result into place pages you can explore, cite and print — for an advocate preparing for a council vote, a journalist checking a claim, and an organizer working out who decides what. | 66351e8a1ed20751caa29b60b0420979572d995fd19d4d397a1e9ef8ac40ed2a | pending |
| K14-03 | held | Facts about public surveillance are scattered across thousands of agency portals, contracts and meeting records, and each existing project answers one piece. SIG joins the pieces so anyone can see the whole picture for a place — and check every part of it. | 2046fd888ff820679f481f8264ae432ab727bf53282a085bc6a6f1f3e8c52ad6 | pending |
| K14-04 | held | Not a census. Counts are what named sources record, never a total. | 0eeccfd28becc1d2c0cf374c2b4e1a44d1d82ebdeaae5b21e66100df6e863e0b | pending |
| K14-05 | held | Not another camera map. It links to the projects that map cameras. | c5de80f3198cf0697fdf03130dff21dfd407688f4c938b3f12cb2d24f4f5cb7a | pending |
| K14-06 | held | Not advocacy. It reports; it does not characterize or endorse. | 75809cda2f59a804956f8f16d7a9c1965cd087aec48ea18e4f377a40a104d74f | pending |
| K14-07 | held | Not live. It publishes dated, citable releases. | 83d2110520ba5634c6fe9debf276e207602895cd595eb32128421b3b17e00e37 | pending |
| IB-01 | /coverage-metrics/ | SIG publishes counted quantities with named denominators, bounds derived from its own records, and measured recall — never a total and never an estimated population. This page lists every coverage figure and what it is counted against. | 74fa6d20328a99457ba31d03eb7eaf8d7c147e2505e8733376cd9206d0612d1a | pending |
| IB-02 | /editorial-standards/ | SIG's editorial standards are what make its record usable as evidence. This page shows the worked example cases and the state of the hostile-reader review that gates each dossier template version. | 5626a068075a1a294421d91a28ffc1abe267e3d8b21dac3c6fc0bff3bb928497 | pending |
| IB-03 | /about/ | SIG joins public records about surveillance infrastructure into one record per place, keeps every fact linked to its source, and publishes it as dated, citable releases. This page says what SIG is, how it works, and what it is not. | 2e4708cee0fc274a2ff6c6625ade723d9469c685304d418629b1d0ee91420fbd | pending |
| PC-01 | / | I have a council meeting coming up | f09718f73e40e23bfa6d1062a4d80ce625fef186d948c5f72cf669eb45c5893f | pending |
| PC-02 | / | I'm checking a figure or a claim | 918d4530e043d7e161ea6f38150c8867a938a92ed42d8ebf3b254e3867970b18 | pending |
| PC-03 | / | I'm organizing in my area | 1f5d0f3adc0e598c2fa89066410d9bcd41ca567e118fcca9477ed25e398fe316 | pending |
| PC-04 | / | I want the data — downloads, API and licences › | c8e4b4dde63eecce3a2b3569ad675c3dbf13e7724e578160ea505e17800ebdfd | pending |
| DF-01 | / | Joined, not copied | 1fe0def25c6336d8fc36d7a36e03f6018761b115164d79b361453c81b9eeab2e | pending |
| DF-02 | / | Many independent public sources reconciled into one record — never a scrape of a single list. | 76308b0e87b0bf530a2a66dab5ab8d06bb4c7be62c201d101f0a379211fc9ff6 | pending |
| DF-03 | / | Disagreements stay visible | 38740d6fa12f3d8245cfc506562dc8339695ab91f9d5aa3ea6dc06b782eb38ac | pending |
| DF-04 | / | Where sources disagree, both sides stay on the page with their dates and documents. | 27463fcd9a10bbfe9f7aeb4fab8a43cd9bc6d0b1c9c78fb91be602e4b137fa61 | pending |
| DF-05 | / | Gaps are labelled | eaff28edc674ab87f1126bab9f31245c0c3e359f05e864a4b946d13a3b2d31fa | pending |
| DF-06 | / | What SIG does not know is a named kind of unknown — and a task a reader can close. | df06dbbe782d036b9799efc26ff510210b24a7b78cfb9250ecf7ab0024ac230c | pending |
| DF-07 | / | Cite it, print it | ec1673eff3abdc63be39e0ccffe634ba162f83640945a6971524cbbd96597b61 | pending |
| DF-08 | / | Every page carries a pinned citation; every dossier prints as a council brief. | 6ba578b08fa3df682c9b04d161a40887df182c15411a01f1954e7682434e3ce7 | pending |
| RK-01 | / | Why a value is trusted — the evidence classes behind it. | 01c782380fb474b8e50876ec696b542a2a6885be0d645593fc81642f48287fae | pending |
| RK-02 | / | Sources disagree; both sides stay on the page. | 83c93736ea4cbe84fe35812d6649469ecfeb0c2e53359ad828e6cfa5bda6023c | pending |
| RK-03 | / | A labelled gap — not researched, none found, stated absent, or unresolved. | c99255b60569dc8355c93ee3927426d696374f576462c038c0bf4f143a8a06f9 | pending |
| RK-04 | / | Output of a method not yet independently evaluated. | e169fb4550d94285ceebf7bb6b6d4fca75d5f7a07823531e4f242f9e7ada820f | pending |
| TR-01 | / | SIG is published by a single maintainer; its review status is recorded as: {reviewStatus}. | 51651e11883210bfb7da5bdf433d196ff28601fe0d25694f21f6b9dad7adc3de | pending |
| CP-01 | lib/capabilities.ts | Look up a state, county or city and see what the record holds. | 447f1f05287813917e18a3931bca14e0eee2a3bb82e8fb0b1a51600081f8e5f0 | pending |
| CP-02 | lib/capabilities.ts | Follow any figure to the sources and rows behind it. | 10618fbfce7ecdd049ab23e95b6ce23e9a3cb91c779cde096bb6d5606db497be | pending |
| CP-03 | lib/capabilities.ts | See where sources agree, disagree, or say nothing. | 0b922c66a6a73a879f2e946541eb536f5d9c88a810a09f412284b004a71a086c | pending |
| CP-04 | lib/capabilities.ts | Know what is up for a decision, and subscribe. | 33c5dd979f48e6b3243859a1fb64b63df829d3bfcdd8ab3feabe2c702ac9d6b7 | pending |
| CP-05 | lib/capabilities.ts | Cite a pinned page, print a council brief, download the data. | 8232a93888e15b4cb1d6b2a96f84b42ccfbe5e7243976c1d5f54b517041919e3 | pending |
| CB-01 | lib/capabilities.ts | Place lookup — being built | 82670e00e09959ea88ae53578d8af1860c9626184e87cf3102ff95baed24610e | pending |
| CB-02 | lib/capabilities.ts | Figure tracing — being built | b22d13d241ea3ddb0ba2e4ebd6447468f27890f1138834e84194b70c84ed2c41 | pending |
| CB-03 | lib/capabilities.ts | Source disagreements — being built | beba7b7133d037749469933ff3fd35d7296e50dcad05e21becdcd10eac5c99e1 | pending |
| CB-04 | lib/capabilities.ts | Decision tracking — being built | 51e33c0da466f19e06eb8cefa5a16a6f5036206687faafaf374ce0e25cfb7bf4 | pending |
| CB-05 | lib/capabilities.ts | Pinned citations — being built | bfa3a6f25cc13b9d206def46073ddc17d52158ca404491931c62c343a7283380 | pending |
| AB-01 | /about/ | SIG — the Surveillance Infrastructure Graph — is an open record of the surveillance technology public agencies use and of the contracts, policies and data-sharing arrangements behind it. | cefb4f7c26ca4ea6a9a22174d598b3c95484b95d9027ee5ed81624e84b68c739 | pending |
| AB-02 | /about/ | Every claim stays linked to the source it came from; where sources disagree, both sides stay on the page. | 9e0becb6774b4d7ac73a4b93924330a6a3e2eda64c3c177808282ec4307d141e | pending |
| AB-10 | /about/ | Collect. | a7bee25193b2bf8f1a1749248403b7435319701c70eb7f4154773c9a33f29909 | pending |
| AB-11 | /about/ | Capture. | 7f0968e95f960e3e9d149ed2918c912d29ed4b45f44e8963fb4d0e260d372055 | pending |
| AB-12 | /about/ | Extract claims. | bb6edd9cd385a09e88007c5fab28f6a56861a78f845388f9d9893a5ab35dbe55 | pending |
| AB-13 | /about/ | Reconcile. | bcfd5753e7e6da7ea985851c534e7c73ee0974d2362f607b3e24fdf7a872c337 | pending |
| AB-14 | /about/ | Publish releases. | c995c4ba4b5bbe4b4c336b1b372503add30adaae252ed9f6eca756b4ea638abd | pending |
| AB-40 | /about/ | Public sources, each with a recorded rights review. | b88e8fea72b7aae19aa603db8f67c1ba15f677c711ecdc4537dd6d4ebfc8f45e | pending |
| AB-41 | /about/ | A dated, hashed copy is kept where the licence allows. | 1a4e6108ba5a3ec026976a997f72f3e1b2482150f70b3e1430649a43ecfeba42 | pending |
| AB-42 | /about/ | Each fact carries its source, date and how directly the source supports it. | 5b4a55e7d440f4489c4a5e4a2ef44c0fae32ff9c13535c70256d6397ed2d351d | pending |
| AB-43 | /about/ | The same agency, vendor or camera is matched across sources; every disagreement is kept. | d1f07e17e22d8552da9772d98106d4fa5c93b6a77974401d320bbaf226a28e5b | pending |
| AB-44 | /about/ | Dated, citable and downloadable; corrections are added, never overwritten. | 7acbaadbb3e1e745aeb2488e5a89726152dd02bc4c297e9aa72d4917d0252bc5 | pending |
| AB-24 | /about/ | Each line below is measured against this release: a capability the data does not yet show is marked as being built, never promised. | 38e0af67a8cc2de7ab98091f59324365375561d93edf007a0db9fec458527e0f | pending |
| AB-20 | /about/ | SIG reports; it does not endorse. | a5816eca39d1d3a1316a2bb0f19fc29c355e7a8ed4b5b2d8ef4eb8264c0d7c5f | pending |
| AB-21 | /about/ | SIG never publishes a total: every figure names what it is counted against. | 5ddd64a1a0a4e514516c8af9d5b1b1bb0d2572124fa1ec7665240609e3b14322 | pending |
| AB-22 | /about/ | SIG publishes dated, citable releases — not a live feed. | 2ccadcd52d3f4ff7b4c708e390e6318ab61ddd150050a800e3ea78a2c320fbc0 | pending |
| AB-23 | /about/ | SIG links to the projects that map cameras; it does not rebuild them. | 8df7dc7b4000ce5918a644ddf2e4d6d04abb1917bdbc6a19b8c05384d7a9de5e | pending |
| AB-25 | /about/ | SIG is published under a sole-maintainer posture; automated checks run on every build, and the record's review status is recorded as: {reviewStatus}. | 79ea997d9cd562846c159b7bf1c177aa4e2f89e5892b1870dabaeb3df39370ce | pending |
| AB-26 | /about/ | No second independent reviewer exists yet; nothing on this site states or implies otherwise. Provisional labels mark method output that has not been independently evaluated. | 5ded49e126bcf802b46547295dfac4a268eb23216acc82bcf5be5c9b38ad4c1a | pending |
| AB-27 | /about/ | Published on the maintainer's own rights and publication decisions. | efee2089e2fa2a2532d5ce21a55acab761a8829be02ac7ed579e6b8aa194201f | pending |
| AB-28 | /about/ | No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel. | f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f | pending |
| AB-29 | /about/ | Other public resources | d346235ec4dc0e84f25978b514c7fabf740bcd69321dabcfd5ddc6ba8334b9b9 | pending |
| AB-30 | /about/ | Public resources a reader may also find useful — SIG does not endorse them, and this list never carries avoidance routing or plate lookups. | f77d09eaeff6c3234a7bd1ea9780154c7aaa55130324f4b8cfe0a4b1fcee603c | pending |

## Confirmation log

| id | status | recorded at | note |
|---|---|---|---|
| K14-00 | confirmed | 2026-11-04 | Operator's D-K14-1 [C-4] plan-cell answer, verbatim: "tagline 'Public surveillance, traced to the documents.' ships now" — recorded by P36.64; not an agent self-confirmation (the answer predates the batch). |
