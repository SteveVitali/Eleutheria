<!--
  docs/build/README.md — the memory-root marker file (v2). Rewritten by P22.3 (build-memory v2 migration)
  from templates/build-README.md. MUST contain the marker line below verbatim — memory-root.sh keys
  committed mode on it. Do not delete the marker.
-->
# Build memory

<!-- build-memory: v2 -->

The committed record of **what happened** during this build. The layout contract — the tree, the
modes, who writes what — is `skills/build-memory/layout.md` (in the `agent-skills` repo); this
directory does not restate it. Established by **P19.1** (ADR-058); migrated to the v2 layout by
**P22.3** (ADR-073), which retired the gitignored `.agents/scratch/` and committed the build's
memory here.

- `LEDGER.md` — the machine-state file (`orchestrate-build` / `drive-build.sh` parse it).
- `BUILD_INDEX.md` — one row per landed chain row (rows 1-66).
- `runs/<ID>.md` — the `implement-spec` run ledger for each ticket; `pr/<ID>.md` — its PR body.
- `readouts/GATE-G<k>.md` — gate readouts (append-only); `planning/` — re-planning rounds.
- `tools/`, `fixtures/`, `reports/` — committed; `logs/` — the one gitignored subtree.
- `reports/` — the project-specific reports the build produced (capstone verification, backlog themes,
  jurisdiction/rights/curation/infra reports, and the functional `okc/`, `live_runs/`, `rights/`
  subtrees the connectors reference by path).

Everything here is a **historical record**: corrected by a new entry, never by editing an old one.
Run `bash scripts/docs/check-build-memory.sh .` (or the skill's `check-build-memory.sh`) to validate.

## Migration to v2 (P22.3, ADR-073)

Move/rename only; **no file's contents were edited** (invariants P1-P3). Three moves happened:

1. **`.agents/scratch/` -> `docs/build/`** via `build-memory migrate from=.agents/scratch apply=true`:
   run ledgers -> `runs/<ID>.md`, PR/commit drafts -> `pr/`, one-off generators -> `tools/`, fixtures
   -> `fixtures/`, the machine ledger -> `LEDGER.md` (the one converted file: `manifest:`/`memoryRoot:`/
   `round:` appended to CURRENT STATE, nothing else), every `*.log` dropped (regenerable). The full
   generated table is under **Migration rename mapping** below.
2. **Leftover PR bodies** the migrate left in the scratch root (it only normalizes `pr/*`), moved by
   hand to `pr/<ID>.md`, plus three PR bodies fetched with `gh pr view` for units with no run ledger
   (P19.4/PR#50, P20.2/PR#53, P22.0/PR#57) so every `BUILD_INDEX` row has a committed evidence file:

| original / source | new path |
|---|---|
| .agents/scratch/pr_body.md | docs/build/pr/CAPSTONE.md |
| .agents/scratch/pr_p22_2_body.md | docs/build/pr/P22.2.md |
| .agents/scratch/p19-3-pr-body.md | docs/build/pr/P19.3.md |
| .agents/scratch/p216_pr_body.md | docs/build/pr/P21.6.md |
| .agents/scratch/ledgers/p20-3_pr_body.md | docs/build/pr/P20.3.md |
| docs/build/pr/p19-1_pr_body.md (copied) | docs/build/pr/P19.1.md |
| gh pr view 50 (PR #50 body) | docs/build/pr/P19.4.md |
| gh pr view 53 (PR #53 body) | docs/build/pr/P20.2.md |
| gh pr view 57 (PR #57 body) | docs/build/pr/P22.0.md |

3. **Existing `docs/build/` root reports -> `docs/build/reports/`.** The v2 layout allows only a fixed
   set of entries at the root of `docs/build/` (the validator's allowlist); the capstone/post-build
   tickets had deposited project reports and functional subtrees there. They were relocated (move only,
   byte-identical) into `reports/` so the validator passes. **No code changed:** the only in-code
   references to these paths are comments, `sources.toml` `review_packet`/`notes` strings, and the
   env-gated live-api acceptance test - none read the committed bytes, so `make check` is unaffected.
   The `live_runs/`/`okc/` runtime write-paths in `connectors/runner.py` and the acceptance harness are
   recreated at runtime and are unchanged.

| original path | new path |
|---|---|
| docs/build/BACKLOG_THEMES.md | docs/build/reports/BACKLOG_THEMES.md |
| docs/build/CAPSTONE_VERIFICATION.md | docs/build/reports/CAPSTONE_VERIFICATION.md |
| docs/build/CI_STATUS.md | docs/build/reports/CI_STATUS.md |
| docs/build/CONTRIBUTION_BACK_LIVE.md | docs/build/reports/CONTRIBUTION_BACK_LIVE.md |
| docs/build/CURATION_UI.md | docs/build/reports/CURATION_UI.md |
| docs/build/DECISION_MEMO.md | docs/build/reports/DECISION_MEMO.md |
| docs/build/DEPOSITS.md | docs/build/reports/DEPOSITS.md |
| docs/build/DOCS_REFRESH_REPORT.md | docs/build/reports/DOCS_REFRESH_REPORT.md |
| docs/build/ECOSYSTEM_CONNECTORS.md | docs/build/reports/ECOSYSTEM_CONNECTORS.md |
| docs/build/FIRST_JURISDICTION_REPORT.md | docs/build/reports/FIRST_JURISDICTION_REPORT.md |
| docs/build/INFRA_RUNBOOK.md | docs/build/reports/INFRA_RUNBOOK.md |
| docs/build/LEDGER_DEFERRALS.md | docs/build/reports/LEDGER_DEFERRALS.md |
| docs/build/LIVE_WIRING_REPORT.md | docs/build/reports/LIVE_WIRING_REPORT.md |
| docs/build/PLANNING_LEDGER.md | docs/build/reports/PLANNING_LEDGER.md |
| docs/build/PUBLICATION_CHECKLIST.md | docs/build/reports/PUBLICATION_CHECKLIST.md |
| docs/build/RELEASE_NOTES_v0.1.0.md | docs/build/reports/RELEASE_NOTES_v0.1.0.md |
| docs/build/RIGHTS_REVIEW_INDEX.md | docs/build/reports/RIGHTS_REVIEW_INDEX.md |
| docs/build/SCOPING_ID_LISTS.md | docs/build/reports/SCOPING_ID_LISTS.md |
| docs/build/SCOPING_NUMBERS.md | docs/build/reports/SCOPING_NUMBERS.md |
| docs/build/STAGE0_OUTREACH_RECORD.md | docs/build/reports/STAGE0_OUTREACH_RECORD.md |
| docs/build/STAGE5_CONNECTORS.md | docs/build/reports/STAGE5_CONNECTORS.md |
| docs/build/SUCCESSION.md | docs/build/reports/SUCCESSION.md |
| docs/build/USABILITY_STUDY.md | docs/build/reports/USABILITY_STUDY.md |
| docs/build/live_runs/README.md | docs/build/reports/live_runs/README.md |
| docs/build/okc/acceptance_2026-09-09.json | docs/build/reports/okc/acceptance_2026-09-09.json |
| docs/build/okc/concurrence.md | docs/build/reports/okc/concurrence.md |
| docs/build/okc/connector_runs_2026-09-09.txt | docs/build/reports/okc/connector_runs_2026-09-09.txt |
| docs/build/okc/hostile_reader_review.md | docs/build/reports/okc/hostile_reader_review.md |
| docs/build/rights/_TEMPLATE.md | docs/build/reports/rights/_TEMPLATE.md |
| docs/build/rights/agency_audit_export.md | docs/build/reports/rights/agency_audit_export.md |
| docs/build/rights/aspi_mapping_chinas_tech_giants.md | docs/build/reports/rights/aspi_mapping_chinas_tech_giants.md |
| docs/build/rights/carnegie_ai_gsi.md | docs/build/reports/rights/carnegie_ai_gsi.md |
| docs/build/rights/civicclerk.md | docs/build/reports/rights/civicclerk.md |
| docs/build/rights/deflock.md | docs/build/reports/rights/deflock.md |
| docs/build/rights/deflock_app_repo.md | docs/build/reports/rights/deflock_app_repo.md |
| docs/build/rights/deflock_repo.md | docs/build/reports/rights/deflock_repo.md |
| docs/build/rights/eff_atlas_of_surveillance.md | docs/build/reports/rights/eff_atlas_of_surveillance.md |
| docs/build/rights/eff_data_driven.md | docs/build/reports/rights/eff_data_driven.md |
| docs/build/rights/eyes_on_flock.md | docs/build/reports/rights/eyes_on_flock.md |
| docs/build/rights/facial_recognition_world_map.md | docs/build/reports/rights/facial_recognition_world_map.md |
| docs/build/rights/flock_finder.md | docs/build/reports/rights/flock_finder.md |
| docs/build/rights/gleif.md | docs/build/reports/rights/gleif.md |
| docs/build/rights/journalrecord.md | docs/build/reports/rights/journalrecord.md |
| docs/build/rights/ok_statute.md | docs/build/reports/rights/ok_statute.md |
| docs/build/rights/okc_council.md | docs/build/reports/rights/okc_council.md |
| docs/build/rights/okc_procurement.md | docs/build/reports/rights/okc_procurement.md |
| docs/build/rights/okcpd_policy.md | docs/build/reports/rights/okcpd_policy.md |
| docs/build/rights/oklahoman.md | docs/build/reports/rights/oklahoman.md |
| docs/build/rights/osm_automated_edits_coc.md | docs/build/reports/rights/osm_automated_edits_coc.md |
| docs/build/rights/osm_copyright.md | docs/build/reports/rights/osm_copyright.md |
| docs/build/rights/osm_element_history.md | docs/build/reports/rights/osm_element_history.md |
| docs/build/rights/osm_overpass.md | docs/build/reports/rights/osm_overpass.md |
| docs/build/rights/osm_replication.md | docs/build/reports/rights/osm_replication.md |
| docs/build/rights/osm_surveillance_tagging.md | docs/build/reports/rights/osm_surveillance_tagging.md |
| docs/build/rights/osm_taginfo.md | docs/build/reports/rights/osm_taginfo.md |
| docs/build/rights/osmf_licence_guidelines.md | docs/build/reports/rights/osmf_licence_guidelines.md |
| docs/build/rights/pathways_acoustic_drone_location.md | docs/build/reports/rights/pathways_acoustic_drone_location.md |
| docs/build/rights/pathways_fr_css_forensics.md | docs/build/reports/rights/pathways_fr_css_forensics.md |
| docs/build/rights/pathways_rtcc_federation.md | docs/build/reports/rights/pathways_rtcc_federation.md |
| docs/build/rights/raa_prefectures.md | docs/build/reports/rights/raa_prefectures.md |
| docs/build/rights/sous_surveillance_osm_import.md | docs/build/reports/rights/sous_surveillance_osm_import.md |
| docs/build/rights/usaspending.md | docs/build/reports/rights/usaspending.md |
| docs/build/rights/wikidata_sparql.md | docs/build/reports/rights/wikidata_sparql.md |

## Byte-identity verification (P1-P3)

Every moved file was hashed **before** the move and re-verified after: all 189 migrated scratch files
(the 190th, `.agents/scratch/README.md`, is not a moved file - its historical mapping is carried into
this README as text) and all 63 relocated `docs/build/` report files matched byte-for-byte (`sha256`
set comparison, 0 differences). The pre-move `sha256sum` lists are recorded below for audit.

### Pre-move sha256 - migrated `.agents/scratch/` files
```
f16d8bf8a50d0e9bbe38461473dafb341d6562d0a4cd796efceea5c338bb56bb  .agents/scratch/README.md
c12ac380648cf317ca84632e043069fef6c08bb0b469a57ba73fc86909f1e656  .agents/scratch/fixtures/er_fixture.json
f62c8bdabf20e3584b0df036f2992320b565f260a74c8c3e62823e78d69bc5da  .agents/scratch/fixtures/p052_live/job_bad.json
98cf6a1e84f7f24fde4ea141eb5efc14099eeb6fd2d9ed0d814a024ebd321e9c  .agents/scratch/fixtures/p052_live/job_good.json
13624a3c7d311325254b7d1b2430753af448d09991853eb09d3ee18a553d4067  .agents/scratch/fixtures/p052_live/queue.json
73f2e83c0555f33a59000c813318c4ceaaf55c87e3ef7e358d96223196b00f70  .agents/scratch/fixtures/p052_live/records.json
2e4cb382692da60fd070b06e72fd8f9039b5f6b13a06a3ee01b52280cddcdce4  .agents/scratch/fixtures/p09-1_code_diff.txt
6aea3c447e0beb8d8251c35978d650265975b60e6c0906af34349ef650a1566f  .agents/scratch/fixtures/p12-1.diff
0a6b04ba27bb307e92aec42c8259d90dfc65263d2c7bee3d970db5f32d089764  .agents/scratch/fixtures/p14-2_build_request.json
f7d541d8c019405a114ade136c7c910c19e0ce712c98c8c7629d05499016e941  .agents/scratch/fixtures/p18-1_base_commit.txt
181a68185a857b9032c17fe74310918146cf631c5cb6365752af1cfc3f500fae  .agents/scratch/fixtures/p18-1_source.diff
99670dbef98b127e4a6c833b15e6b5aa8d2e37bc1f6c19fa1e876805a76da1d6  .agents/scratch/fixtures/p18-1_source_diffstat.txt
bb1077ee1532fc86669ec525bc6f0536d04d9a3b63bf38fa045a3a3c4aa99da9  .agents/scratch/implement-spec_devin-p19-3-capstone-composed-verification_20260115.md
7e65366f09734d5d9a064bbc464cc9112b6d5da33b01880f5f68524207362d1f  .agents/scratch/ledgers/implement-spec_P00.1.md
ca269dbb8a2ca62f6dc7f8aaab5e0e3c8ee760f0e18c12a40834a3bd98b4df2a  .agents/scratch/ledgers/implement-spec_P00.2.md
c4dda8d05e678d5e39888d33060f9f1a2cddca479f85f12a3e54fc5f0301c799  .agents/scratch/ledgers/implement-spec_P00.3.md
0d1ceb61859bd51fe2b196cad854e65714e00d0e1fa367e8302a1e7469ea8744  .agents/scratch/ledgers/implement-spec_P01.1.md
34043c78181e14ea0bc54031abc1f5479fc6121fd2cb89e3168dca802c84044b  .agents/scratch/ledgers/implement-spec_P02.1.md
9ac2db33409107e21d5b5941720468f0f17908f196d7c27256322cb8c93eae17  .agents/scratch/ledgers/implement-spec_P02.2.md
c4dedae26c391f3a6499e0c515996684f2984d0f1c5e29867308b16fd4b193fa  .agents/scratch/ledgers/implement-spec_P02.3.md
e0ba2e1ec27edb363fcc0e8c28d1810ffb0f0961339e05ace0bfa9ec46011ba5  .agents/scratch/ledgers/implement-spec_P03.1.md
c8de99858b702f376f7790804611fdb0921ba04549925fdab0c00fa8be63464f  .agents/scratch/ledgers/implement-spec_P03.2.md
ffe15484c91ac6adfea5c67884576876df0364df77b51691f305f2ed51e80de4  .agents/scratch/ledgers/implement-spec_P04.1.md
e0e57fd12986efcabf1934ea74639ec8edd53c933cd5ccaa8d35fc874447353f  .agents/scratch/ledgers/implement-spec_P04.3.md
d224f6c199f78534e57f71ae915b6d5504ee33974b883246be4f29049587bfa3  .agents/scratch/ledgers/implement-spec_P05.1.md
c35f5f6fbf73c886e4d362319162c4f884cddb6a041fa205ce60788665f59fbc  .agents/scratch/ledgers/implement-spec_P05.2.md
72c4b63a470ee016b9ab24730880e75603f2e5a953180dc2217afa013ebf38bd  .agents/scratch/ledgers/implement-spec_P06.1.md
b2d44e3436229127336ce3db1702bffa862a3c3706ae4458dc709bddb53e34dc  .agents/scratch/ledgers/implement-spec_P07.1.md
eec3d2e2740a4c863dd7ad97b21448fcefa56ea00c898142e1daafc648e84d89  .agents/scratch/ledgers/implement-spec_P07.2.md
69d73bc0cf13436726c8eedd0603cfe7cd1549a8cc99a895e6e49b202e46dde5  .agents/scratch/ledgers/implement-spec_P07.3.md
734b5d36be1063638f726e25177d78bb836652c7fe5ec81efcfdd6a5843d5d23  .agents/scratch/ledgers/implement-spec_P08.1.md
bcd710cf1cc94f0c2678810a8c2678784aca658a48f1c03e3510dd8c4d3361ed  .agents/scratch/ledgers/implement-spec_P08.2.md
4a05bbe383cee8712ce7fc3bc44e26fe0e521df1fbcae14c14193c8071329663  .agents/scratch/ledgers/implement-spec_P08.3.md
f7e036812b35394139692044e05974bd8c27b51fb62989f1af99349ae4e2ce5a  .agents/scratch/ledgers/implement-spec_P09.1.md
cd6f165a9dd99513e44f54765f05a4ce39d0ef42f933eb26a19b5ef61652fcc7  .agents/scratch/ledgers/implement-spec_P10.1.md
7d30c440c1e94881044bf76b9864958101f68115711392a31bafc2ecd4af1acb  .agents/scratch/ledgers/implement-spec_P10.2.md
1a2dd76824aa1d124588e7c99a76df64d1f8f88f8b8c3fe553e1c93cc1a7208c  .agents/scratch/ledgers/implement-spec_P10.3.md
85931848a032be2b5d32ace05ee0ded3b43515fbd4437a732a452dda9cab9991  .agents/scratch/ledgers/implement-spec_P11.1.md
6c131600cbbbc91134c35929997f959e1546b78a42499e2cf5d16243224a3e48  .agents/scratch/ledgers/implement-spec_P11.2.md
c3ad5ae28137377b3401e67145edca4edcf86df1e9e5fb9a01ec110d728101ed  .agents/scratch/ledgers/implement-spec_P12.1.md
c5e43c67e3a6ce99d5d0e4d5e36f7409e74cc54ea055ee462022bca18b782d56  .agents/scratch/ledgers/implement-spec_P12.2.md
3ebf5d3142694a8178b69d47c5f02d35ecae6797647a58d41c11b5f8bb802f92  .agents/scratch/ledgers/implement-spec_P13.1.md
0419e229fafef73681f4aee927d33c310b9d6e18bccf19f796ff75fda126dfd6  .agents/scratch/ledgers/implement-spec_P13.2.md
56e6f7de6376b33a5ada7691f330d5b41be991cb35320f91a060314d27cbc628  .agents/scratch/ledgers/implement-spec_P14.1.md
12d8e339d8d461245059a17680ab519f02f2f941cba00f2e372564cb93116ec8  .agents/scratch/ledgers/implement-spec_P14.2.md
2fda6499f7a7974edfeee6a71a0ce03367e46f29e76b9a02ac948b471f24c550  .agents/scratch/ledgers/implement-spec_P15.1.md
94c351f6f8884bd909d64586666fdf239430de89734f4ab29d9bf42d1b9bb97e  .agents/scratch/ledgers/implement-spec_P15.2.md
06f77ba4a66998dadc537c47e64c12314d1569f8bd8c00a6e39af80202f27ab2  .agents/scratch/ledgers/implement-spec_P15.3.md
1d4bbcaca341c181bc2d5fed9266a72d39315970a5744c8aa995953818b20794  .agents/scratch/ledgers/implement-spec_P15.4.md
f5b17976c8ed7b962ad626087f591ae631015abc5acb2e48eaec04e7a75031d6  .agents/scratch/ledgers/implement-spec_P15.5.md
cf13500a44bfe327a019021cab4a5af5ef1b1febaf1981751552369f99e80258  .agents/scratch/ledgers/implement-spec_P16.1.md
7a5a619c59021cc32926998a53b9ee769808a84133c51ce6e0cdf77762898574  .agents/scratch/ledgers/implement-spec_P16.2.md
714c97e8170abe158ca0949ca4036f31ff38f38233052cb43e4d40eca3675150  .agents/scratch/ledgers/implement-spec_P17.1.md
631c1cd9a29d2ed317fda42a54bb770aea3b3a38e074aa2cfbe57df2a39a5238  .agents/scratch/ledgers/implement-spec_P17.2.md
b0aa99dc95bd8384ec9ff24edb4e37077a5a19d8818f33de7e036871138a7e16  .agents/scratch/ledgers/implement-spec_P17.3.md
a93bed0e07d3d226aa46149195fcd36ae9f1067090a2db8f331c194207507e53  .agents/scratch/ledgers/implement-spec_P18.1.md
40218e401e25f7ea600b1155a7d26e61a79586cbd5fae6d2a5ec378c1cf047c4  .agents/scratch/ledgers/implement-spec_P18.2.md
96e322a9a17992f5dab82e26a53da8d71d1b34c7dd63acf45df8344699cf13a7  .agents/scratch/ledgers/implement-spec_P19.5.md
4f9a28a05ea74ffbe377f2750ff630d231159fa753a035ebfb2dd90ba34bd71e  .agents/scratch/ledgers/implement-spec_P20.1.md
a565a76f00a500dc88d89d624317239f27858e49f1b7575c57eaa156d6d11818  .agents/scratch/ledgers/implement-spec_P20.3.md
5a9b80b9f77da5e60618ab8373c72c36cddf7be71d7cab3036dedad9c02c39d6  .agents/scratch/ledgers/implement-spec_P20.4.md
318bcc00263073584cb373fced708e2eaa99dce82c08feaf2cda8a3455c956f0  .agents/scratch/ledgers/implement-spec_P21.1.md
9e488bccc889449b167d67f0a09e200b5b38e3b5c018e4559549a8573f0848eb  .agents/scratch/ledgers/implement-spec_P21.4_20260909.md
048d07aca09b1ab4a1d1ec8bf5eeea0828dd26ebe7fcdf4d43a0da7db8e3dfa6  .agents/scratch/ledgers/implement-spec_P21.7.md
72782bf766c88d2d8246e1b43ab0166fa0d62f32fe07e12fbcfb184cac76fd54  .agents/scratch/ledgers/implement-spec_P21.8.md
8c13693d84294c39dcc99cfedd267e779370a21a64bf25c9851713d2084b30f2  .agents/scratch/ledgers/implement-spec_P22.2.md
82eef112b79c6bc050319e46a4545ba8b4e5f8474c06be9a60e6001ff0cc26f8  .agents/scratch/ledgers/implement-spec_devin-p19-2-capstone-gap-analysis_20260908.md
36ac5fb7c644f82a6baddec63c9734e920f4b48685b63917fb737c4e4f3df02f  .agents/scratch/ledgers/implement-spec_devin-p21-2-persist-annotation-layer_20260101.md
a6977a0294843e1b04b0c493993ff8b030f8a197deb1d141cfc34b4187975ca0  .agents/scratch/ledgers/implement-spec_devin-p21-3-live-connector-wiring_20260101.md
9c482ece6f053434afb96c39cb877cb5b4f9931c3e91c0c24d8a6806d523890b  .agents/scratch/ledgers/implement-spec_devin-p21-5-infra-deposit-and-tiles_20260909.md
0b87dbe2e4b1bd732a33f100106b2f7bbb4319e8b2c1d9f31a3eae8c61382b61  .agents/scratch/ledgers/implement-spec_p20-3_20260909.md
0e608c6ef2217d4441da21589a3aa5d255428c11299ea862972aafe8d820fbb5  .agents/scratch/ledgers/implement-spec_p21-9-stage5-pathway-connectors_20260820.md
63d3ebc9111ca90e4b66917ec05d90db64a0c91f4141d8b114e98b0bb0b99320  .agents/scratch/ledgers/implement-spec_p22-1-repo-docs-refresh.md
0cace20859957d6654cdc700edcff52500fee0619f079744f76a0c4675481b27  .agents/scratch/ledgers/p20-3_pr_body.md
ff84d6547fc520bfb72553798226910bc3bdf52eaab2122bf538e924f7439ef0  .agents/scratch/p19-3-pr-body.md
a7691c134cac15684a6bcd68fbe670063c0201b47678204fc679c970efbccbcb  .agents/scratch/p216_pr_body.md
bfb5b9634c8b2f97558acf529da7a93c58a5573bf9c1817a8d809a24270822ed  .agents/scratch/pr/P20.1_body.md
10486fc65dd460cfa4e612a748aa32a162ce9fecc06c95831412b8837eefe69d  .agents/scratch/pr/commit_msg.txt
57ae9c338bdf2e257322eb3d7fd720d335e9ff4241f0e63f19700299e33c47ec  .agents/scratch/pr/commitmsg.txt
ff73547caab0ab5dca8a1043a942ec438a3f53c74891b441f758a70de2487e16  .agents/scratch/pr/p003_commit_msg.txt
056941f83fc4a0234b9a8ec1f22cdca6d81189d243183932b90b5350ed2f5562  .agents/scratch/pr/p003_pr_body.md
0d6677cfd7ddaf6670ae4451065622bbfefad071c0901f65e925069a5cd3e91f  .agents/scratch/pr/p021_pr_body.md
14db4f3e69d92032fea8aa3ef8f549ee5b499a0e44eef2422a6a310b7cad9496  .agents/scratch/pr/p022_commit_msg.txt
2660b30c986b86d08d247ada4051def9c1de8b2e98670cf5a51440d1929cd02b  .agents/scratch/pr/p022_pr_body.md
62b2f4bbdad84c9539242aa6d31dd79e62a3e58dde9db0a29a3211bd0f260a23  .agents/scratch/pr/p08-3_commit_msg.txt
9d6e07008d0eb83971ba161971509b23475a08459e95408c68b75c12d2d7ae4c  .agents/scratch/pr/p08-3_pr_body.md
d5f60620f332a58d5d6449591c9110dcb963fe8d95f8ea40ab08aab83db3c134  .agents/scratch/pr/p09-1_pr_body.md
bd411e3e80633623c6d1d23d399259e136c6cbd61e02f197ea7d32e4a11a9a4d  .agents/scratch/pr/p10_1_commit_msg.txt
16c7bc4dc6e16356ac631b0a4035137e24af1c8e2348521c9ba4166344529a4f  .agents/scratch/pr/p10_1_pr_body.md
5124ebfe8d45ecdd8ffc948bcbba91ce812b6ce802d3337f7051b84c6f7aeb7b  .agents/scratch/pr/p10_3_pr_body.md
0affb5b9ed13f9283411125b40d74599d37099a142d2f0e1ae6d90e00559cc94  .agents/scratch/pr/p11_1_pr_body.md
99829a9bb5c55b357a958e8ca1ce74899de38114951b87f51a9faeea70364247  .agents/scratch/pr/p12_2_commit_msg.txt
f0462f1d402c6b6cdb535876a1e0a498c2f659a61c20f6eddd441c89cfa5068d  .agents/scratch/pr/p12_2_pr_body.md
243b99728acf9030a072c43e05f9b7756bff700ecf353ff64829dfc38605de77  .agents/scratch/pr/p13-2_commit_msg.txt
0fe44e1a3466d5fa400de6fb187c83c5ed179ce3e1dc29d500666032066a916d  .agents/scratch/pr/p13-2_pr_body.md
83239008076295f20c3f0a5af124043cd42b4dc382d72826dc78d7dc7fd5a535  .agents/scratch/pr/p13_1_pr_body.md
1e4c243a956258030e027b8c85b4b7a60e5b17d3b891f5cd666f5d7517ec3149  .agents/scratch/pr/p14-2_commit_msg.txt
203e95f24b4093f77a8a2625617262801fa03aae9d7c4eab3630c923e6ef46d5  .agents/scratch/pr/p14-2_pr_body.md
ba8b5be2bafec19412447c40fe938cca40b016d8eeb378e1e07a0b0551c3d978  .agents/scratch/pr/p14_1_pr_body.md
b47a473908f67eca052fdb34898721dab5b854e9f23a472b3422032896b56718  .agents/scratch/pr/p15-3_commit_msg.txt
5c32e88e72bf20acf101c46394acd1a38d3f09eb9811db1dc48bd4b9e4c4ce54  .agents/scratch/pr/p15-3_pr_body.md
a02f59afababc9fd7ff55ff135092a3c4427062c03e7c36283831eda62c3cc13  .agents/scratch/pr/p15-4_pr_body.md
b8af201a2106199532b90e61eae033b729ab37ce474df43c692a618b3b527143  .agents/scratch/pr/p16_1_pr_body.md
7a96071c98c137652ea05ecfcce517d284dd6815aa5c7542e984a6d250c024c4  .agents/scratch/pr/p16_2_commit_msg.txt
71bfe8a3a8668464a021f62be57b826d0e18f57181fd631a79aadd92cddd422b  .agents/scratch/pr/p16_2_pr_body.md
1ce4dfcc55a34f7d37294ac200eb6f89b53ca27ba1cee985361a18e90c7c6a1b  .agents/scratch/pr/p17_1_pr_body.md
009c60dffbfa5441a1ae9e7e48dee9d34385d6a43e588097ff7d549643f18fb4  .agents/scratch/pr/p17_2_commit_msg.txt
0a7b58ec588dc7d199b05349c9c29ba4ac2d2c698582e334818eb6c8ad4b1794  .agents/scratch/pr/p17_2_pr_body.md
cfda16e05f1017df9844b1f6a6e003316b27ea70289678fac7d02dabdb624914  .agents/scratch/pr/p17_3_pr_body.md
e11a6fd0e5e425888b315f98d56be083db2eab45767afa18b232d550966c22bd  .agents/scratch/pr/p18_1_pr_body.md
e3ad03dd67ccccd5c013f2078f135bc6d7ffe8e78ad802008fd8115ca0c94154  .agents/scratch/pr/p18_2_commit_msg.txt
a604bb452d5f8105b7614fb42d292a309f510d9763f4d843977827e85753c0cc  .agents/scratch/pr/p18_2_pr_body.md
082bec97bbe41a016f0d70017601e712c5a6d9eca3d9965136f428019f4df979  .agents/scratch/pr/p19-1_pr_body.md
e5ec22516a52142cd88d7fecf190502dd8eaa5b0a75d8bde4755dfb80ff98d5f  .agents/scratch/pr/p19_5_body.md
b62d7110220c54e2e65a7517b48f1c589817f7cf1da5d88eca7d3f5efa72f245  .agents/scratch/pr/p21-1_pr_body.md
d8f58a5b6891fbad98764bb02bcaf1e70273a1dacb48c1c28e8da3e7a8c07f84  .agents/scratch/pr/p_analytics_hardening_commit.txt
b3dc34df419bab112b88a4d1467c3c607e386532e3687e95bc8386a9aad6765a  .agents/scratch/pr/pr_1.md
f5b0ce010bf769ee9ce5d6f4d1ca2a999ae151b7b42c226bf6490b24de5c365a  .agents/scratch/pr/pr_10.md
4fd503ae1089086cd18a4985240edb0c388df06b7cc3622ec833be1d46440c9f  .agents/scratch/pr/pr_11.md
95bb8e17be7542ea6196d8dfde89bc8d3facfc7cf686b92be184a8749d972dcd  .agents/scratch/pr/pr_12.md
69bd25bfa2e7a0885aa6a3844112c8093b3c803df35902df858df5943ec53263  .agents/scratch/pr/pr_13.md
824811ff1f2d026a212bc8cd73d832ac3831df9eb26892fef381bcf3b92dfb28  .agents/scratch/pr/pr_14.md
0db0d17e12bfeb27dfe5ef01b73867b712f5e2c53be2f904088780968fc0bef8  .agents/scratch/pr/pr_15.md
1848b4503c61f5e639352091cf8f3d4327434d3fa391c8d251f05706673c75fc  .agents/scratch/pr/pr_16.md
3add0c56086b8be20385d1f62afed60e1db1133f5127f75155bc66dcbba86671  .agents/scratch/pr/pr_17.md
fb1b7bd8614913c5af844cbb4d5f5f4018bdcd230438fc1eef4454dea5038d00  .agents/scratch/pr/pr_18.md
94501374fb344380808dbe48439b2b14b2b553e462b6016bf7360913a37babde  .agents/scratch/pr/pr_19.md
600fc10c95255791436b1d58a60b9f5395c3f357aa12e78480c6c8c91cab1a31  .agents/scratch/pr/pr_2.md
eaa79abedb6135a020a0d2f5038ccc3794ea4b92d277b925cc0a903a92c6b91b  .agents/scratch/pr/pr_20.md
e5c2185bea8fd849103221b428d70089c9e977a657dbfc815b4e371049a82bb6  .agents/scratch/pr/pr_21.md
665c87a15ba042f81fa84c649b6edcccd95531e63a0de2f769ddde8f13348352  .agents/scratch/pr/pr_22.md
c94abc3b97ecc07c35b2789364eaa8c481eeae00f75baecbb11d5bab368c6898  .agents/scratch/pr/pr_23.md
e0af000229343356bcc6eef535ef10f1a612287ced5d71911cd0a15162e0792a  .agents/scratch/pr/pr_24.md
6fba623be57e654c092a34122326b71106534ae817e8cc0ee1d3f0a03bf48e48  .agents/scratch/pr/pr_25.md
ef77c72a4a5906723342bf045f2d8f518112b88eb7daeb263b88bf2d2b3d1103  .agents/scratch/pr/pr_26.md
f93adeb2531800de73a3a2d505aa1bf680ded835dd53c3a848e0ec3cafdd439f  .agents/scratch/pr/pr_27.md
d51bf5a742624ed7f0eae6a7ec62515df457dba571798b70c115160cf02e7dba  .agents/scratch/pr/pr_28.md
f1462c65a8172eaf8798636955283d90d3488ee84b00ebed37f83b334903b520  .agents/scratch/pr/pr_29.md
386f4e2e2c1fe523e81d2d52cdadc20816a4fee1298eb339002e34889032df88  .agents/scratch/pr/pr_3.md
26421dc03de4fd55d1def8440216ac983113ab78448a99434029090ce21be8f7  .agents/scratch/pr/pr_30.md
096a74256b12d88d93f9aa0d73539cfc4e9da864800fc83eaa80f46819517c24  .agents/scratch/pr/pr_31.md
ad1d0ef9fca7859fa1457c614a45e1ad14c95ae102504858977c355a0880ec2b  .agents/scratch/pr/pr_32.md
88f8a29cc509c7ecda0fb965db3cc8364ee0a15fdce35b45e73dcfffa56ebc51  .agents/scratch/pr/pr_33.md
e897586632723380c83073a45cf3fb2e5831394918bf64b1837c48657d20a3e8  .agents/scratch/pr/pr_34.md
fd7992970e6265c111ba428bf44caf014bc2f260a251a17625a690cc929786f0  .agents/scratch/pr/pr_35.md
05b92d127d6c713205f2343ab4550ef60eadf629c7c86b3a27b7efd1d0d7c552  .agents/scratch/pr/pr_36.md
f5c1391b801f938e1b90eb9cabd6014577ce22784e7c85015602be5f853fd511  .agents/scratch/pr/pr_37.md
d3f274ffcc308bb1b454ddef3d683bf2df64658f0bedadaa250298f6d9fd88c7  .agents/scratch/pr/pr_38.md
e114020353088f44f96d8a9e7287a197cfe4050ba9d4efd440371c7126ae7faa  .agents/scratch/pr/pr_39.md
8217edde1b32d3dcb93da7463b493ae75f6344174a3edd4662efa67264959227  .agents/scratch/pr/pr_4.md
a2c359933bac806d5b401ad806c998b2d31b30af9d483a86cad8e7e3fc2b456a  .agents/scratch/pr/pr_40.md
9ad5a7165893c8f674e336834626562fccdac3a1c3502f9dd45b906d1a765149  .agents/scratch/pr/pr_41.md
2f296c9797d4702814eca66b0ac1006c7cd46b4a83fc754daef33d321155942f  .agents/scratch/pr/pr_42.md
3c30beefdcccd47290fe3de7c1a073543b6f7d15b095ce267f884100eaa8c7fb  .agents/scratch/pr/pr_43.md
d77eaafe5e793cc593bf42dfbe658f3c1cd4b3a181f46e8b77fb1e6cb4c15e72  .agents/scratch/pr/pr_44.md
f14bc785df44e637ce83590bc908366eb43f30fb41cb285b5b175352e78f675e  .agents/scratch/pr/pr_45.md
095bc41c231e73b7eee91b46ac2510123037b1ac258de83e51366319cb2b8c58  .agents/scratch/pr/pr_46.md
8020c9572842b3e3457d337191fac61952f41475f58fb37f3b96e626476fb0b2  .agents/scratch/pr/pr_5.md
1d27d0c16d746a7a99a4cad6a8d4eb1070c491d8eb887a5de36f14a9aa499067  .agents/scratch/pr/pr_6.md
4412b676c4eb82fdd6eeb5466c303b02a954f7c85915cc1e646b600c9b047472  .agents/scratch/pr/pr_7.md
bab67a05bf2881d744c156e5dbb164a04d3b917c2c7872eb6e14e31053449ddf  .agents/scratch/pr/pr_8.md
ae241fa0b309b651ece97d663af8aba6be059be73bbda89fbd958b99fc655303  .agents/scratch/pr/pr_9.md
0e89b1645c720ac4841331a82f3592e2a797682821f0a4ce124f27bf47f01ee5  .agents/scratch/pr/pr_body.md
26b091990142777c836b181a03cb0450f5fb5912ee128e02e7f60aa6ca91b6bc  .agents/scratch/pr/pr_body_p07-3.md
b00e48e668e774b47b3d5aab557d177c0a87f7400b6b6fb49bb0953ffaba0daf  .agents/scratch/pr/pr_body_p11_2.md
e86fba0826f24205ea2c2fccdfac8234846244aa6b1bfa20577061da88d13622  .agents/scratch/pr/pr_body_scratch-root.md
d0f27426b10d0d68f19031a363a78cedeec8dfd12e149f8b34cf87d355c12847  .agents/scratch/pr/prbody.md
26192c6185c1c718cca25903e118b630b7a17c42658df73c98253e3e885dcb1e  .agents/scratch/pr_body.md
926065597e0cba9512aedbb3a0ca44830f2a4b75de7f8e23cbce5e969b31cd18  .agents/scratch/pr_p22_2_body.md
40a3b062c664da8550f2d65b40dcc4d1a58c5159a86790bb7f47a5bd413504d6  .agents/scratch/tools/build_predicates.py
b67b8c359b27112bdc0993a6266fa0da3b0eb65e4d88e0f2f09c69a38c6fc200  .agents/scratch/tools/build_tech.py
67d27aeae74299722280fad11a6316d633769aa136e829bd1d8105c956498345  .agents/scratch/tools/classify.py
42f25e7eab4b9364c52142b04875d6c137da67d0df5a0fef714935d32d7ebcff  .agents/scratch/tools/drive_gates.py
59eae46a18edf3eb9bdb9d48caecbb06b91ab497842fe0457ad5939beb6e5918  .agents/scratch/tools/frags.txt
f1a99779c53b35710c3e1de04a61c48f211017137055d32ec08bd413a4371072  .agents/scratch/tools/gather.py
5a03cbbf08171aa5109a6eeffefe761cb99a47e7e5aaeef9055264019943b9ec  .agents/scratch/tools/gen_adrs.py
6f8ed5de843fd2b332c4d9495368338af6386ab8aeca33052ad9143b396cdc25  .agents/scratch/tools/gen_l3_sample.py
2b309a11c930d962c03bf5493063b05d2bdb528cdaebac050ab216ee0ae62b07  .agents/scratch/tools/gen_rights_index.py
b5f04fcdd4f89633a183b8a433256b4278a6d63194302c88e39b29935cb6d356  .agents/scratch/tools/gen_rights_packets.py
c1ea24df3d7b5d60b8aa7835f56c1b03bf9bf3aef0244af0e02f47de9b0e1201  .agents/scratch/tools/gen_stage0_record.py
0be66e30d76b26ca9d2b2a4b2df8370929ac57582e1452cbd13369e56f37d363  .agents/scratch/tools/id_data.json
d8578df23a8abbdfca79a44f47ed83eb9dbe8f418e7b64499810a3089fb03b05  .agents/scratch/tools/p20_build_backlog.py
525f19d93bfb8e3b02762d3bf85ccfc4f36b0b4deaa02f069c882e36f31a185c  .agents/scratch/tools/p20_extract.py
5b8d3121b86073bbd52e6362a4737ab0a884907448daaa1ae03169a43535aa5f  .agents/scratch/tools/p20_topics.py
932960ede607f02648aaadd57e7289f1edbfd35d8aa38836900029dfe494d112  .agents/scratch/tools/pr_titles.txt
28e39bbede8881d837e5799a2a9ce6c56fa6ff4b67c05963461b7174422eddb7  .agents/scratch/tools/probe_matcher.py
64363ba7e3c85090c9840284ae15cea5f4ddba60f78c82b9787c2a215225e783  .agents/scratch/tools/probe_splink.py
29c78eebae24e1fc1293c5b4273429b105a67a39af117f4ea33b46c61febffa1  .agents/scratch/tools/probe_splink2.py
7c42e812b16c49dd2b2343bcb48f63770d74d65bde7d15e7fdb60fb6c586335f  .agents/scratch/tools/relicense.py
a14f65895162ec98aa3dbfb015e9a21f2a2f7447eee5336d0213a1845349692f  .agents/scratch/tools/scaffold_pkgs.sh
```

### Pre-move sha256 - relocated `docs/build/` report files
```
5b99582f6d6ccb6fbef4b1b6754659f9e7621e2df80e97cc89b896866540b30c  docs/build/BACKLOG_THEMES.md
d1082e8456d97e7885ed2d16f49db445bafabf17f03aaa855ea44a831c3da2f3  docs/build/CAPSTONE_VERIFICATION.md
65e95a9563b9a25f6d887bd95e7d5754dde0b295221dc4b7baa771baef3270ca  docs/build/CI_STATUS.md
af21ae06aa77f29aefac8e0a876e5da6d9200fcb96ed4c1d384c9e4cfa00f275  docs/build/CONTRIBUTION_BACK_LIVE.md
413fd66ea271cccabc739bbc4b28f88a99520f1a37578b3dd164607e1a552a05  docs/build/CURATION_UI.md
505f3c72fb445f0a1770a5035725d2e30c3fcc8ac0dbb291f6b4fe800461141a  docs/build/DECISION_MEMO.md
001f436eb5a4b5b94d0dda973240331babecb0a33b96e3e1fe14f23e571dd1e3  docs/build/DEPOSITS.md
d24cf2e1486f98bc88f90b9795ecdc24e716c5755e9137d21496b5ef8dcf3b5a  docs/build/DOCS_REFRESH_REPORT.md
4af57ca5df9a79c40b8c288082593e927486a0a216fe50d5ba84aacea0d71ee3  docs/build/ECOSYSTEM_CONNECTORS.md
886391e99302c6b4d40fce63418f674210d45603674edc9f30ee1f6918262f57  docs/build/FIRST_JURISDICTION_REPORT.md
7dd4316ba972ce3e49e0f470d594e5e73d727075a2d715a41af53a587f303d0b  docs/build/INFRA_RUNBOOK.md
54e061e8761a06b6dd64f693ddbeac8baa463dd3f351b1e9f5273d2b7d88959d  docs/build/LEDGER_DEFERRALS.md
a046002c3e3e0f6ca9fdd1d9c303991b915088964a4e219eb2bd975295f50afb  docs/build/LIVE_WIRING_REPORT.md
54342edf54dd0d6fe3538fde063d6ef7fa5fbafde9dc638fbf11a8f72b648336  docs/build/PLANNING_LEDGER.md
053d2dd8534874bb51ee18911fbf67d3c1682deb78fa9eb26ba2350f9129fbaa  docs/build/PUBLICATION_CHECKLIST.md
0cb4e250ca677eb31127c365a7456929eb0af424b09d290526685ebbc1baec80  docs/build/RELEASE_NOTES_v0.1.0.md
c533cc6ef9570f4d50fdd3f8605bc6a6eab338c6853f7bf797b274d8cb854130  docs/build/RIGHTS_REVIEW_INDEX.md
c67e6449976fae7792cda77976d8d67a0b2724882fa604dc1e5749f0be21e4f2  docs/build/SCOPING_ID_LISTS.md
253b26fa05c54f4b3ae3015dd2fe12c1c6c224cf63ee57896b9834c189dea058  docs/build/SCOPING_NUMBERS.md
846d90c16e4d50ed866b14e5d1f4d95aed76906c3da60309ea95e9e7d03c6cc5  docs/build/STAGE0_OUTREACH_RECORD.md
25e367925a11f71cbed8ee1d2e6667f8e61b71196f17fb674131ac6439fa94fe  docs/build/STAGE5_CONNECTORS.md
e4294dbbae6ee55290838553ba31dd8b620fe36280bc6ca391c51e97c75f3d12  docs/build/SUCCESSION.md
c72bbf64fa4e63b270451fa08b3c59c45982d80d5425e2a4e0a77bfb58ec4b66  docs/build/USABILITY_STUDY.md
4ebf3f730dfd3957c40ad42048809a47cacf52ffe402208edba4a780f3cdaa41  docs/build/live_runs/README.md
bfda5133e7de012ddd62561cd79e1b3a0bc71911323d4194389b13c8ea1ba2f0  docs/build/okc/acceptance_2026-09-09.json
d4cf867fe75a96f24fe7080aae52bcde76899a2ac156c24832bc94ad6ec429cb  docs/build/okc/concurrence.md
a5b26c1c0e9a7fcd6fda1831a06b24d8f668b0c6271af45eea2bd11bccdb13bb  docs/build/okc/connector_runs_2026-09-09.txt
7e567d0a13e50348b2a92fae33d782ab1af3d5c53de592c423f699431b79b5e7  docs/build/okc/hostile_reader_review.md
32f297947c66c314d4e48eb3ceba8e74cd18334e53f36448d2ad8dd983807b19  docs/build/rights/_TEMPLATE.md
fbdc3896a927c5f8a1ef9855ea28c4973a761eb82470cec727c8e68d034efe0b  docs/build/rights/agency_audit_export.md
3a8219338ecded94f57f49390ca55b7f3ee3af8698140ce68a607650ff141b98  docs/build/rights/aspi_mapping_chinas_tech_giants.md
aab9c875c3ca6adf9406646772f6d85fc7af62253f8baa3aa371b8404f04ad3d  docs/build/rights/carnegie_ai_gsi.md
c2517d609079d2c59ad83535f67a158247faa7069ead0192ce79bc1189bfde82  docs/build/rights/civicclerk.md
bbf8f3ab1613c791f0f03f8bf856e9fda5b4c4bef150d779379a894fe5c01e65  docs/build/rights/deflock.md
9fa883847c06fdbe36be8e5b2b9cf8788e2a4c7514e4553c5f25471749773209  docs/build/rights/deflock_app_repo.md
b6808c1d7bc35dc7ad3754ea13744f813aad094e35ededf0526c980e9da9a1dc  docs/build/rights/deflock_repo.md
fda28e261cf29160ffa545bf5a50412ab12b0dde43bdbcbb8515d3c2e84f9533  docs/build/rights/eff_atlas_of_surveillance.md
a0c393a97f0553ff037a553ae28084fc93b003b5b19c9840ffc357062870c361  docs/build/rights/eff_data_driven.md
9e90e8385a6dfaed9fcd82f2068549bbc8dd0be9bc848971df89b6d48ef44422  docs/build/rights/eyes_on_flock.md
5bc3a369838a46b721a9b3f6ef6b83d7280a4be23675a61300d5cdb9bb236c70  docs/build/rights/facial_recognition_world_map.md
56ed911e31058dc6a6af4adaf31d187b0d38788b92e30ed52519d19c95b77606  docs/build/rights/flock_finder.md
31803646ef0c002b8dddb1266674d5dd61ba4da997ee02849fbdb41a210b2a36  docs/build/rights/gleif.md
8963b6a15f43fe9f30353ab53778174f9397804b8a8f274f6cccdb8fa1e3e1f2  docs/build/rights/journalrecord.md
d0ce0e4717d93c48bacc5752c769aa3860b9b4bc3f6360da3d54c955a67ec264  docs/build/rights/ok_statute.md
e7027b2a2a7a80ff31eacc841620bc94dc9f167a7adb143bc2f73d0e0fe820ab  docs/build/rights/okc_council.md
af41f2555d86fcf108e9375a4ce6dd14365e01cece5aab0239a7992f2a057efd  docs/build/rights/okc_procurement.md
db395fd8d935fe3eb7d9d2b6bedbf69aa369159362550f26eac6875c1d9aaeb2  docs/build/rights/okcpd_policy.md
a88586c61275eab5dbb65e85af8a7e7e81f20aa1b066ee729e551b755f9a33db  docs/build/rights/oklahoman.md
a66d3d9dccbd44348c80ad2d7244a661621ba4859908483afcd4fa44f25136d0  docs/build/rights/osm_automated_edits_coc.md
821fe96fbdb3230d6b711c8bb409e2ddbb1a0a4b6e0c47090b90692ba4817643  docs/build/rights/osm_copyright.md
c56d0d46c4bd83c743b5990ef6e0610e8c8cde973923f5e865f41b20dbf1a729  docs/build/rights/osm_element_history.md
e769359443b476fab69489aefe8bf6530bcaa5978ddcff950a74ddbb07f12a44  docs/build/rights/osm_overpass.md
e6509959668c075bf285700a975086c745db180360477a6646f43d58201ebe44  docs/build/rights/osm_replication.md
9ecd9064845555d80c5ab18a536182e5c109248dcd9a0e13b2fa9e8086d957fd  docs/build/rights/osm_surveillance_tagging.md
6507ccef47c2ce3c2e63c6616f918b4f59c5cef0dcb818158da33ef84257f043  docs/build/rights/osm_taginfo.md
f54f2078c88ba2aa7c13cebd96663242fe1a5911725a58c0a43542542d5f3f2f  docs/build/rights/osmf_licence_guidelines.md
f6a533cdf1b6c58ad54d6cf3650ad2ede0dc55fcb3db7a92b524c440a508e8a9  docs/build/rights/pathways_acoustic_drone_location.md
3ae4590e1a2fd072d35e88423b7af740e7babbdfc586f498e7af70c8e43b3210  docs/build/rights/pathways_fr_css_forensics.md
310d6840c7db797c9fe6097f1860012fa82bec2f9caf004254ff0b438f9dc861  docs/build/rights/pathways_rtcc_federation.md
b9bc4a93a0857b496a8914210b54ffb2948087d77ffb2cc70600e9b54a5951e7  docs/build/rights/raa_prefectures.md
5def1c93196f16de876be5405d11165373d998e16708368e3268350ebb2e0f12  docs/build/rights/sous_surveillance_osm_import.md
24910f3112c65adc5cb9b043bde6fbce5a01706925777e221b8b918cfb90e17e  docs/build/rights/usaspending.md
d44d9af7141c86b2a76de8d456e4ac5403a1ec9702f84d06534cf3151c77058b  docs/build/rights/wikidata_sparql.md
```

## Historical ledger rename mapping (P19.1 — carried forward from the retired `.agents/scratch/README.md`)

The 44 original run ledgers were renamed once by P19.1 (into `.agents/scratch/ledgers/`), then again by
this migration (into `docs/build/runs/`, see the table below). Carried here for provenance.

## Ledger rename mapping (P19.1 — append-only provenance, RISK-P19-02)

The 44 historical ledgers had three naming styles + two in the old root `scratch/`. They were **moved
and renamed only** (contents never edited, invariant P1–P3):

| original path | new path |
|---|---|
| `.agents/scratch/implement-spec_p00-3_20260827.md` | `ledgers/implement-spec_P00.3.md` |
| `.agents/scratch/implement-spec_devin-p01-1-ontology-as-code_20260827.md` | `ledgers/implement-spec_P01.1.md` |
| `.agents/scratch/implement-spec_p02-1-claim-spine.md` | `ledgers/implement-spec_P02.1.md` |
| `.agents/scratch/implement-spec_devin-p02-2-evidence-store_20260827.md` | `ledgers/implement-spec_P02.2.md` |
| `.agents/scratch/implement-spec_devin-p02-3-temporal-provenance_20260827.md` | `ledgers/implement-spec_P02.3.md` |
| `.agents/scratch/ledger_p03-1.md` | `ledgers/implement-spec_P03.1.md` |
| `.agents/scratch/ledger_p03-2.md` | `ledgers/implement-spec_P03.2.md` |
| `.agents/scratch/implement-spec_p04-1_20260827.md` | `ledgers/implement-spec_P04.1.md` |
| `.agents/scratch/implement-spec_p04-3-atlas_20260827.md` | `ledgers/implement-spec_P04.3.md` |
| `.agents/scratch/ledger_p05-1.md` | `ledgers/implement-spec_P05.1.md` |
| `.agents/scratch/ledger_p05-2.md` | `ledgers/implement-spec_P05.2.md` |
| `.agents/scratch/implement-spec_devin-p06-1-vertical-slice_20260901.md` | `ledgers/implement-spec_P06.1.md` |
| `.agents/scratch/ledger_p07-1.md` | `ledgers/implement-spec_P07.1.md` |
| `.agents/scratch/implement-spec_devin-p07-2-records-connectors_20260901.md` | `ledgers/implement-spec_P07.2.md` |
| `.agents/scratch/implement-spec_p07-3.md` | `ledgers/implement-spec_P07.3.md` |
| `.agents/scratch/implement-spec_P08.1-resolver.md` | `ledgers/implement-spec_P08.1.md` |
| `.agents/scratch/implement-spec_p08-2_ledger.md` | `ledgers/implement-spec_P08.2.md` |
| `.agents/scratch/implement-spec_devin-p08-3-contradiction-object_20260901.md` | `ledgers/implement-spec_P08.3.md` |
| `.agents/scratch/implement-spec_devin-p09-1-coverage_20260901.md` | `ledgers/implement-spec_P09.1.md` |
| `.agents/scratch/implement-spec_devin-p10-1-task-engine_20260901.md` | `ledgers/implement-spec_P10.1.md` |
| `.agents/scratch/implement-spec_devin-p10-2-detector-catalog_20260901.md` | `ledgers/implement-spec_P10.2.md` |
| `.agents/scratch/implement-spec_devin-p10-3-records-request-gen_20260901.md` | `ledgers/implement-spec_P10.3.md` |
| `.agents/scratch/implement-spec_devin-p11-1-flock-portal_20260901.md` | `ledgers/implement-spec_P11.1.md` |
| `.agents/scratch/implement-spec_devin-p11-2-audit-structural_20260901.md` | `ledgers/implement-spec_P11.2.md` |
| `.agents/scratch/implement-spec_devin-p12-1-usage-analytics_20260901.md` | `ledgers/implement-spec_P12.1.md` |
| `.agents/scratch/implement-spec_devin-p12-2-network-inference_20260901.md` | `ledgers/implement-spec_P12.2.md` |
| `.agents/scratch/implement-spec_devin-p13-1-accountability_20260901.md` | `ledgers/implement-spec_P13.1.md` |
| `.agents/scratch/implement-spec_p13-2-policy-legal_20260901.md` | `ledgers/implement-spec_P13.2.md` |
| `.agents/scratch/implement-spec_devin-p14-1-public-api_20260901.md` | `ledgers/implement-spec_P14.1.md` |
| `.agents/scratch/implement-spec_devin-p14-2-exports_20260901.md` | `ledgers/implement-spec_P14.2.md` |
| `.agents/scratch/implement-spec_devin-p15-1-web-shell_20260901.md` | `ledgers/implement-spec_P15.1.md` |
| `.agents/scratch/implement-spec_devin-p15-2-local-dossier_20260901.md` | `ledgers/implement-spec_P15.2.md` |
| `.agents/scratch/implement-spec_devin-p15-3-map-network_20260908.md` | `ledgers/implement-spec_P15.3.md` |
| `.agents/scratch/implement-spec_devin-p15-4-watch-evidence_20260908.md` | `ledgers/implement-spec_P15.4.md` |
| `.agents/scratch/implement-spec_devin-p15-5-corrections-methodology_20260908.md` | `ledgers/implement-spec_P15.5.md` |
| `.agents/scratch/implement-spec_devin-p16-1-contributors_20260908.md` | `ledgers/implement-spec_P16.1.md` |
| `.agents/scratch/implement-spec_devin-p16-2-contribution-back_20260908.md` | `ledgers/implement-spec_P16.2.md` |
| `.agents/scratch/implement-spec_devin-p17-1-broader-federation-rtcc_20260908.md` | `ledgers/implement-spec_P17.1.md` |
| `.agents/scratch/implement-spec_devin-p17-2-broader-fr-css-forensics_20260908.md` | `ledgers/implement-spec_P17.2.md` |
| `.agents/scratch/implement-spec_devin-p17-3-broader-acoustic-drone-loc_20260908.md` | `ledgers/implement-spec_P17.3.md` |
| `.agents/scratch/implement-spec_devin-p18-1-international-framework_20260908.md` | `ledgers/implement-spec_P18.1.md` |
| `.agents/scratch/implement-spec_devin-p18-2-france-belgium_20260908.md` | `ledgers/implement-spec_P18.2.md` |
| `scratch/implement-spec_p00-1_ledger.md` | `ledgers/implement-spec_P00.1.md` |
| `scratch/ledger_p00-2.md` | `ledgers/implement-spec_P00.2.md` |

P00.4 and P04.2 have no run ledger (their evidence is in PR #4 / #12 bodies) — 44 ledgers for 46
tickets. `pr/`, `tools/` and `fixtures/` were moved from the two old scratch roots; the old root
`scratch/pr_body.md` (P01.1-era) landed as `pr/pr_body_scratch-root.md` to avoid a name clash.

## Migration rename mapping

Written by `build-memory migrate` on 2026-09-09. Move/rename only; contents byte-identical.

| original path | new path |
|---|---|
| .agents/scratch/baseline_check.log | (dropped) |
| .agents/scratch/curation_serve.log | (dropped) |
| .agents/scratch/e2e.log | (dropped) |
| .agents/scratch/e2e_durations.log | (dropped) |
| .agents/scratch/e2e_run.log | (dropped) |
| .agents/scratch/final_check.log | (dropped) |
| .agents/scratch/fixtures/er_fixture.json | docs/build/fixtures/er_fixture.json |
| .agents/scratch/fixtures/p052_live/job_bad.json | docs/build/fixtures/job_bad.json |
| .agents/scratch/fixtures/p052_live/job_good.json | docs/build/fixtures/job_good.json |
| .agents/scratch/fixtures/p052_live/queue.json | docs/build/fixtures/queue.json |
| .agents/scratch/fixtures/p052_live/records.json | docs/build/fixtures/records.json |
| .agents/scratch/fixtures/p09-1_code_diff.txt | docs/build/fixtures/p09-1_code_diff.txt |
| .agents/scratch/fixtures/p12-1.diff | docs/build/fixtures/p12-1.diff |
| .agents/scratch/fixtures/p14-2_build_request.json | docs/build/fixtures/p14-2_build_request.json |
| .agents/scratch/fixtures/p18-1_base_commit.txt | docs/build/fixtures/p18-1_base_commit.txt |
| .agents/scratch/fixtures/p18-1_source.diff | docs/build/fixtures/p18-1_source.diff |
| .agents/scratch/fixtures/p18-1_source_diffstat.txt | docs/build/fixtures/p18-1_source_diffstat.txt |
| .agents/scratch/implement-spec_devin-p19-3-capstone-composed-verification_20260115.md | docs/build/runs/P19.3.md |
| .agents/scratch/ledgers/implement-spec_P00.1.md | docs/build/runs/P00.1.md |
| .agents/scratch/ledgers/implement-spec_P00.2.md | docs/build/runs/P00.2.md |
| .agents/scratch/ledgers/implement-spec_P00.3.md | docs/build/runs/P00.3.md |
| .agents/scratch/ledgers/implement-spec_P01.1.md | docs/build/runs/P01.1.md |
| .agents/scratch/ledgers/implement-spec_P02.1.md | docs/build/runs/P02.1.md |
| .agents/scratch/ledgers/implement-spec_P02.2.md | docs/build/runs/P02.2.md |
| .agents/scratch/ledgers/implement-spec_P02.3.md | docs/build/runs/P02.3.md |
| .agents/scratch/ledgers/implement-spec_P03.1.md | docs/build/runs/P03.1.md |
| .agents/scratch/ledgers/implement-spec_P03.2.md | docs/build/runs/P03.2.md |
| .agents/scratch/ledgers/implement-spec_P04.1.md | docs/build/runs/P04.1.md |
| .agents/scratch/ledgers/implement-spec_P04.3.md | docs/build/runs/P04.3.md |
| .agents/scratch/ledgers/implement-spec_P05.1.md | docs/build/runs/P05.1.md |
| .agents/scratch/ledgers/implement-spec_P05.2.md | docs/build/runs/P05.2.md |
| .agents/scratch/ledgers/implement-spec_P06.1.md | docs/build/runs/P06.1.md |
| .agents/scratch/ledgers/implement-spec_P07.1.md | docs/build/runs/P07.1.md |
| .agents/scratch/ledgers/implement-spec_P07.2.md | docs/build/runs/P07.2.md |
| .agents/scratch/ledgers/implement-spec_P07.3.md | docs/build/runs/P07.3.md |
| .agents/scratch/ledgers/implement-spec_P08.1.md | docs/build/runs/P08.1.md |
| .agents/scratch/ledgers/implement-spec_P08.2.md | docs/build/runs/P08.2.md |
| .agents/scratch/ledgers/implement-spec_P08.3.md | docs/build/runs/P08.3.md |
| .agents/scratch/ledgers/implement-spec_P09.1.md | docs/build/runs/P09.1.md |
| .agents/scratch/ledgers/implement-spec_P10.1.md | docs/build/runs/P10.1.md |
| .agents/scratch/ledgers/implement-spec_P10.2.md | docs/build/runs/P10.2.md |
| .agents/scratch/ledgers/implement-spec_P10.3.md | docs/build/runs/P10.3.md |
| .agents/scratch/ledgers/implement-spec_P11.1.md | docs/build/runs/P11.1.md |
| .agents/scratch/ledgers/implement-spec_P11.2.md | docs/build/runs/P11.2.md |
| .agents/scratch/ledgers/implement-spec_P12.1.md | docs/build/runs/P12.1.md |
| .agents/scratch/ledgers/implement-spec_P12.2.md | docs/build/runs/P12.2.md |
| .agents/scratch/ledgers/implement-spec_P13.1.md | docs/build/runs/P13.1.md |
| .agents/scratch/ledgers/implement-spec_P13.2.md | docs/build/runs/P13.2.md |
| .agents/scratch/ledgers/implement-spec_P14.1.md | docs/build/runs/P14.1.md |
| .agents/scratch/ledgers/implement-spec_P14.2.md | docs/build/runs/P14.2.md |
| .agents/scratch/ledgers/implement-spec_P15.1.md | docs/build/runs/P15.1.md |
| .agents/scratch/ledgers/implement-spec_P15.2.md | docs/build/runs/P15.2.md |
| .agents/scratch/ledgers/implement-spec_P15.3.md | docs/build/runs/P15.3.md |
| .agents/scratch/ledgers/implement-spec_P15.4.md | docs/build/runs/P15.4.md |
| .agents/scratch/ledgers/implement-spec_P15.5.md | docs/build/runs/P15.5.md |
| .agents/scratch/ledgers/implement-spec_P16.1.md | docs/build/runs/P16.1.md |
| .agents/scratch/ledgers/implement-spec_P16.2.md | docs/build/runs/P16.2.md |
| .agents/scratch/ledgers/implement-spec_P17.1.md | docs/build/runs/P17.1.md |
| .agents/scratch/ledgers/implement-spec_P17.2.md | docs/build/runs/P17.2.md |
| .agents/scratch/ledgers/implement-spec_P17.3.md | docs/build/runs/P17.3.md |
| .agents/scratch/ledgers/implement-spec_P18.1.md | docs/build/runs/P18.1.md |
| .agents/scratch/ledgers/implement-spec_P18.2.md | docs/build/runs/P18.2.md |
| .agents/scratch/ledgers/implement-spec_P19.5.md | docs/build/runs/P19.5.md |
| .agents/scratch/ledgers/implement-spec_P20.1.md | docs/build/runs/P20.1.md |
| .agents/scratch/ledgers/implement-spec_P20.3.md | docs/build/runs/P20.3.md |
| .agents/scratch/ledgers/implement-spec_P20.4.md | docs/build/runs/P20.4.md |
| .agents/scratch/ledgers/implement-spec_P21.1.md | docs/build/runs/P21.1.md |
| .agents/scratch/ledgers/implement-spec_P21.4_20260909.md | docs/build/runs/P21.4.md |
| .agents/scratch/ledgers/implement-spec_P21.7.md | docs/build/runs/P21.7.md |
| .agents/scratch/ledgers/implement-spec_P21.8.md | docs/build/runs/P21.8.md |
| .agents/scratch/ledgers/implement-spec_P22.2.md | docs/build/runs/P22.2.md |
| .agents/scratch/ledgers/implement-spec_devin-p19-2-capstone-gap-analysis_20260908.md | docs/build/runs/P19.2.md |
| .agents/scratch/ledgers/implement-spec_devin-p21-2-persist-annotation-layer_20260101.md | docs/build/runs/P21.2.md |
| .agents/scratch/ledgers/implement-spec_devin-p21-3-live-connector-wiring_20260101.md | docs/build/runs/P21.3.md |
| .agents/scratch/ledgers/implement-spec_devin-p21-5-infra-deposit-and-tiles_20260909.md | docs/build/runs/P21.5.md |
| .agents/scratch/ledgers/implement-spec_p20-3_20260909.md | docs/build/runs/P20.3-dup1.md |
| .agents/scratch/ledgers/implement-spec_p21-9-stage5-pathway-connectors_20260820.md | docs/build/runs/P21.9.md |
| .agents/scratch/ledgers/implement-spec_p22-1-repo-docs-refresh.md | docs/build/runs/P22.1.md |
| .agents/scratch/logs/baseline_check.log | (dropped) |
| .agents/scratch/logs/p195_check.log | (dropped) |
| .agents/scratch/logs/p195_check2.log | (dropped) |
| .agents/scratch/logs/p195_check3.log | (dropped) |
| .agents/scratch/logs/p195_e2e.log | (dropped) |
| .agents/scratch/make_check.log | (dropped) |
| .agents/scratch/make_test_db.log | (dropped) |
| .agents/scratch/npm_ci.log | (dropped) |
| .agents/scratch/p214_check.log | (dropped) |
| .agents/scratch/p214_check2.log | (dropped) |
| .agents/scratch/p216_baseline.log | (dropped) |
| .agents/scratch/p216_check1.log | (dropped) |
| .agents/scratch/p216_lhci.log | (dropped) |
| .agents/scratch/p216_webcheck.log | (dropped) |
| .agents/scratch/planning/sig-postbuild-build-ledger.md | docs/build/LEDGER.md (converted) |
| .agents/scratch/pr/P20.1_body.md | docs/build/pr/P20.1_body.md |
| .agents/scratch/pr/commit_msg.txt | docs/build/pr/commit_msg.txt |
| .agents/scratch/pr/commitmsg.txt | docs/build/pr/commitmsg.txt |
| .agents/scratch/pr/p003_commit_msg.txt | docs/build/pr/p003_commit_msg.txt |
| .agents/scratch/pr/p003_pr_body.md | docs/build/pr/p003_pr_body.md |
| .agents/scratch/pr/p021_pr_body.md | docs/build/pr/p021_pr_body.md |
| .agents/scratch/pr/p022_commit_msg.txt | docs/build/pr/p022_commit_msg.txt |
| .agents/scratch/pr/p022_pr_body.md | docs/build/pr/p022_pr_body.md |
| .agents/scratch/pr/p08-3_commit_msg.txt | docs/build/pr/p08-3_commit_msg.txt |
| .agents/scratch/pr/p08-3_pr_body.md | docs/build/pr/p08-3_pr_body.md |
| .agents/scratch/pr/p09-1_pr_body.md | docs/build/pr/p09-1_pr_body.md |
| .agents/scratch/pr/p10_1_commit_msg.txt | docs/build/pr/p10_1_commit_msg.txt |
| .agents/scratch/pr/p10_1_pr_body.md | docs/build/pr/p10_1_pr_body.md |
| .agents/scratch/pr/p10_3_pr_body.md | docs/build/pr/p10_3_pr_body.md |
| .agents/scratch/pr/p11_1_pr_body.md | docs/build/pr/p11_1_pr_body.md |
| .agents/scratch/pr/p12_2_commit_msg.txt | docs/build/pr/p12_2_commit_msg.txt |
| .agents/scratch/pr/p12_2_pr_body.md | docs/build/pr/p12_2_pr_body.md |
| .agents/scratch/pr/p13-2_commit_msg.txt | docs/build/pr/p13-2_commit_msg.txt |
| .agents/scratch/pr/p13-2_pr_body.md | docs/build/pr/p13-2_pr_body.md |
| .agents/scratch/pr/p13_1_pr_body.md | docs/build/pr/p13_1_pr_body.md |
| .agents/scratch/pr/p14-2_commit_msg.txt | docs/build/pr/p14-2_commit_msg.txt |
| .agents/scratch/pr/p14-2_pr_body.md | docs/build/pr/p14-2_pr_body.md |
| .agents/scratch/pr/p14_1_pr_body.md | docs/build/pr/p14_1_pr_body.md |
| .agents/scratch/pr/p15-3_commit_msg.txt | docs/build/pr/p15-3_commit_msg.txt |
| .agents/scratch/pr/p15-3_pr_body.md | docs/build/pr/p15-3_pr_body.md |
| .agents/scratch/pr/p15-4_pr_body.md | docs/build/pr/p15-4_pr_body.md |
| .agents/scratch/pr/p16_1_pr_body.md | docs/build/pr/p16_1_pr_body.md |
| .agents/scratch/pr/p16_2_commit_msg.txt | docs/build/pr/p16_2_commit_msg.txt |
| .agents/scratch/pr/p16_2_pr_body.md | docs/build/pr/p16_2_pr_body.md |
| .agents/scratch/pr/p17_1_pr_body.md | docs/build/pr/p17_1_pr_body.md |
| .agents/scratch/pr/p17_2_commit_msg.txt | docs/build/pr/p17_2_commit_msg.txt |
| .agents/scratch/pr/p17_2_pr_body.md | docs/build/pr/p17_2_pr_body.md |
| .agents/scratch/pr/p17_3_pr_body.md | docs/build/pr/p17_3_pr_body.md |
| .agents/scratch/pr/p18_1_pr_body.md | docs/build/pr/p18_1_pr_body.md |
| .agents/scratch/pr/p18_2_commit_msg.txt | docs/build/pr/p18_2_commit_msg.txt |
| .agents/scratch/pr/p18_2_pr_body.md | docs/build/pr/p18_2_pr_body.md |
| .agents/scratch/pr/p19-1_pr_body.md | docs/build/pr/p19-1_pr_body.md |
| .agents/scratch/pr/p19_5_body.md | docs/build/pr/p19_5_body.md |
| .agents/scratch/pr/p21-1_pr_body.md | docs/build/pr/p21-1_pr_body.md |
| .agents/scratch/pr/p_analytics_hardening_commit.txt | docs/build/pr/p_analytics_hardening_commit.txt |
| .agents/scratch/pr/pr_1.md | docs/build/pr/pr_1.md |
| .agents/scratch/pr/pr_10.md | docs/build/pr/pr_10.md |
| .agents/scratch/pr/pr_11.md | docs/build/pr/pr_11.md |
| .agents/scratch/pr/pr_12.md | docs/build/pr/pr_12.md |
| .agents/scratch/pr/pr_13.md | docs/build/pr/pr_13.md |
| .agents/scratch/pr/pr_14.md | docs/build/pr/pr_14.md |
| .agents/scratch/pr/pr_15.md | docs/build/pr/pr_15.md |
| .agents/scratch/pr/pr_16.md | docs/build/pr/pr_16.md |
| .agents/scratch/pr/pr_17.md | docs/build/pr/pr_17.md |
| .agents/scratch/pr/pr_18.md | docs/build/pr/pr_18.md |
| .agents/scratch/pr/pr_19.md | docs/build/pr/pr_19.md |
| .agents/scratch/pr/pr_2.md | docs/build/pr/pr_2.md |
| .agents/scratch/pr/pr_20.md | docs/build/pr/pr_20.md |
| .agents/scratch/pr/pr_21.md | docs/build/pr/pr_21.md |
| .agents/scratch/pr/pr_22.md | docs/build/pr/pr_22.md |
| .agents/scratch/pr/pr_23.md | docs/build/pr/pr_23.md |
| .agents/scratch/pr/pr_24.md | docs/build/pr/pr_24.md |
| .agents/scratch/pr/pr_25.md | docs/build/pr/pr_25.md |
| .agents/scratch/pr/pr_26.md | docs/build/pr/pr_26.md |
| .agents/scratch/pr/pr_27.md | docs/build/pr/pr_27.md |
| .agents/scratch/pr/pr_28.md | docs/build/pr/pr_28.md |
| .agents/scratch/pr/pr_29.md | docs/build/pr/pr_29.md |
| .agents/scratch/pr/pr_3.md | docs/build/pr/pr_3.md |
| .agents/scratch/pr/pr_30.md | docs/build/pr/pr_30.md |
| .agents/scratch/pr/pr_31.md | docs/build/pr/pr_31.md |
| .agents/scratch/pr/pr_32.md | docs/build/pr/pr_32.md |
| .agents/scratch/pr/pr_33.md | docs/build/pr/pr_33.md |
| .agents/scratch/pr/pr_34.md | docs/build/pr/pr_34.md |
| .agents/scratch/pr/pr_35.md | docs/build/pr/pr_35.md |
| .agents/scratch/pr/pr_36.md | docs/build/pr/pr_36.md |
| .agents/scratch/pr/pr_37.md | docs/build/pr/pr_37.md |
| .agents/scratch/pr/pr_38.md | docs/build/pr/pr_38.md |
| .agents/scratch/pr/pr_39.md | docs/build/pr/pr_39.md |
| .agents/scratch/pr/pr_4.md | docs/build/pr/pr_4.md |
| .agents/scratch/pr/pr_40.md | docs/build/pr/pr_40.md |
| .agents/scratch/pr/pr_41.md | docs/build/pr/pr_41.md |
| .agents/scratch/pr/pr_42.md | docs/build/pr/pr_42.md |
| .agents/scratch/pr/pr_43.md | docs/build/pr/pr_43.md |
| .agents/scratch/pr/pr_44.md | docs/build/pr/pr_44.md |
| .agents/scratch/pr/pr_45.md | docs/build/pr/pr_45.md |
| .agents/scratch/pr/pr_46.md | docs/build/pr/pr_46.md |
| .agents/scratch/pr/pr_5.md | docs/build/pr/pr_5.md |
| .agents/scratch/pr/pr_6.md | docs/build/pr/pr_6.md |
| .agents/scratch/pr/pr_7.md | docs/build/pr/pr_7.md |
| .agents/scratch/pr/pr_8.md | docs/build/pr/pr_8.md |
| .agents/scratch/pr/pr_9.md | docs/build/pr/pr_9.md |
| .agents/scratch/pr/pr_body.md | docs/build/pr/pr_body.md |
| .agents/scratch/pr/pr_body_p07-3.md | docs/build/pr/pr_body_p07-3.md |
| .agents/scratch/pr/pr_body_p11_2.md | docs/build/pr/pr_body_p11_2.md |
| .agents/scratch/pr/pr_body_scratch-root.md | docs/build/pr/pr_body_scratch-root.md |
| .agents/scratch/pr/prbody.md | docs/build/pr/prbody.md |
| .agents/scratch/retro_matrix.log | (dropped) |
| .agents/scratch/run_okc.log | (dropped) |
| .agents/scratch/test_db.log | (dropped) |
| .agents/scratch/tools/build_predicates.py | docs/build/tools/build_predicates.py |
| .agents/scratch/tools/build_tech.py | docs/build/tools/build_tech.py |
| .agents/scratch/tools/classify.py | docs/build/tools/classify.py |
| .agents/scratch/tools/drive_gates.py | docs/build/tools/drive_gates.py |
| .agents/scratch/tools/frags.txt | docs/build/tools/frags.txt |
| .agents/scratch/tools/gather.py | docs/build/tools/gather.py |
| .agents/scratch/tools/gen_adrs.py | docs/build/tools/gen_adrs.py |
| .agents/scratch/tools/gen_l3_sample.py | docs/build/tools/gen_l3_sample.py |
| .agents/scratch/tools/gen_rights_index.py | docs/build/tools/gen_rights_index.py |
| .agents/scratch/tools/gen_rights_packets.py | docs/build/tools/gen_rights_packets.py |
| .agents/scratch/tools/gen_stage0_record.py | docs/build/tools/gen_stage0_record.py |
| .agents/scratch/tools/id_data.json | docs/build/tools/id_data.json |
| .agents/scratch/tools/p20_build_backlog.py | docs/build/tools/p20_build_backlog.py |
| .agents/scratch/tools/p20_extract.py | docs/build/tools/p20_extract.py |
| .agents/scratch/tools/p20_topics.py | docs/build/tools/p20_topics.py |
| .agents/scratch/tools/pr_titles.txt | docs/build/tools/pr_titles.txt |
| .agents/scratch/tools/probe_matcher.py | docs/build/tools/probe_matcher.py |
| .agents/scratch/tools/probe_splink.py | docs/build/tools/probe_splink.py |
| .agents/scratch/tools/probe_splink2.py | docs/build/tools/probe_splink2.py |
| .agents/scratch/tools/relicense.py | docs/build/tools/relicense.py |
| .agents/scratch/tools/scaffold_pkgs.sh | docs/build/tools/scaffold_pkgs.sh |
| .agents/scratch/web_build_standalone.log | (dropped) |

## Legacy artifacts (provenance)

The `reports/` subtree holds the pre-v2 `docs/build/` artifacts (planning ledger, decision memo, coverage
matrix companions, capstone/backlog/reconciliation/jurisdiction reports) and the functional `okc/`,
`live_runs/`, `rights/` subtrees. `pr/` keeps every historical PR/commit draft under its original basename
plus the canonical `pr/<ID>.md` evidence files. `tools/` merges the committed validators (`check_spec_src.py`,
`check_coverage_matrix.py`, `check_backlog.py`, `merge_dryrun.sh`, `run_okc.sh`) with the migrated one-off
generators. Nothing here is regenerated; only broken references are repaired.
