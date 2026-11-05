# Copy batch 17 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P36.65 (row 408, UXK14-11 — onboarding content: per-page
     reading keys, the typed EmptySurface kind registry, the annotated
     how-to-read-a-dossier page). Append-only, same convention as batch-01:
     rows are never deleted or edited in place; a status change is recorded
     in the confirmation log with a `date -u` stamp. Id prefixes: KY-* =
     the ReadingKey component + lib/reading-key.ts withheld line; EK-* =
     lib/empty.ts EMPTY_KIND_PARTS (the four unsurfaced cause classes:
     filtered_none, not_redistributable, degraded, not_monitored);
     HD-* = /about/how-to-read-a-dossier/. -->

## Convention

Same as batch-01 (`docs/build/reports/copy-batches/batch-01.md` § Convention):
`pending` = agent-drafted, awaiting verbatim confirmation · `confirmed` = the
operator confirmed these words verbatim. P36.65-specific notes:

- **`{name}` / `{section-bodies}`** are rendered placeholders (the
  `{reviewStatus}`/`{combinesList}` precedent — the row pins the sentence
  shape; HD-02's `{name}` resolves to the golden dossier's display name,
  HD-07 names the per-section callout bodies the page generates from the
  dossier's own template plan (five drafted variants, listed below).
- The reading-key item labels and plain lines are the lexicon's own
  strings (`lexicon.json`, already governed) — only the summary, the
  glossary affordance and the withheld line are new drafted sentences.

### HD-07 variants (the per-section callout bodies, by dossier position)

| position | text | sha256 |
|---|---|---|
| variant | The locator, the record map, and the section's figures — every numeral expands to the sources and rule behind it. | b0a2b60aad7c5744d95e717a40a50eafad544f0600e6784e648e42f5dbe498de |
| variant | The full gap list — each entry a typed absence, never a blank cell. | 17bd8335da5fcc3b927f956bf5e13d3128716e51de7d46e8ea9aa10320561c02 |
| variant | The provenance for this page's own figures — sources, runs and review status at dossier scope. | 82a2b6873f74128aa4b6c5eab5ac419f633fd64cbe889551677214b2546a6dd3 |
| variant | The section's facts and rows; a figure slot waits here until the network figures ship — an empty slot is a typed state, never a hole. | cd33918e8222657fc32f730e6727ca71668d1d8e6432af8f2f9fb1e3001a14e5 |
| variant | The section's facts and rows — a value, a typed absence, or an explicit unknown; never a silent blank. | 9456761b311f4c785532b0cb74ad0a5b2f9c09948994d03d3a20acee28a65abe |

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| KY-01 | component | How to read this page | fde652c7da93486fd91a0a83f92de8a3afc4c4bbe930cbc51fa9073c7bf40ec6 | pending |
| KY-02 | component | glossary › | a9efad353452c9a5c27211b0a1f5adb2cde3d55012f6493f7d0f019d1902e458 | pending |
| KY-03 | lib/reading-key.ts | A value SIG withholds under its publication policy — the row names the reason. | 6c9b937a380344efea54412a061555075cfad828e0bf997c4668d76fb14f0dd8 | pending |
| EK-01 | lib/empty.ts | No records match this filter | c6dba0d3e8664e44a025aafb05a5909d5fb47280ccf1e5db229a984f3618ce10 | pending |
| EK-02 | lib/empty.ts | The filter returned nothing — this is not an absence in the record. | d1a9dd1c1d83b944f75b1cec4951532e2c33018de696f339e7a4c77e6f382f0c | pending |
| EK-03 | lib/empty.ts | The unfiltered list holds every record this view covers. | 90249730fdeb1737019716f4a5f38c41cd4caa50d679b98a5b6e29dd3334d7d5 | pending |
| EK-04 | lib/empty.ts | Clear filters | 7179ea0035fca783ec62b7185659b68c75f2a7c12b909306a57183dc9b3fa44b | pending |
| EK-05 | lib/empty.ts | The filter result changes only when the records or the filter change. | 6b98fdc5bda81738280456008a27d409a235d427f72ed63422beb513fb2fdede | pending |
| EK-06 | lib/empty.ts | This record cannot be redistributed | 394d11e10384da6f4d2d8a3e98815a6e4a6d38bc39b838c5a26f3fef30dddbd7 | pending |
| EK-07 | lib/empty.ts | The licence on this data does not permit SIG to republish it — a rights hold, not a gap. | 8eacc673c432d88def25781e1edcfb0a47ecb06a7ab60351a8ea682228ada2e1 | pending |
| EK-08 | lib/empty.ts | The source registry names where the record lives upstream. | d08079415b38b6d25b37c3bb75a972e116ffbf37f52874d2df42e1ee32338d34 | pending |
| EK-09 | lib/empty.ts | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| EK-10 | lib/empty.ts | The record appears only if its licence posture changes. | 3f7c98894b8b02db1d5a618d57794847a63ba401c32a3164d2c6bcf4ee014a2a | pending |
| EK-11 | lib/empty.ts | This surface is temporarily limited | 8b03f79c27a4cb38f4900a7bf0145ae8c229e8c199d8f3f6a8dcfeeac190122b | pending |
| EK-12 | lib/empty.ts | A serving fault limits this view right now — it is not an absence in the record. | beed41eda2a0a00e47c0d72333aac0ff63489cfe0af48d40bee24c1a554496ce | pending |
| EK-13 | lib/empty.ts | The status page records any known serving fault. | 634b83fbad8d773485577586fbc0c8de1b27d65e762029f058cff7e6c15fd197 | pending |
| EK-14 | lib/empty.ts | Check the status page | 1b735dab904d4711198029b2ccfed779997a4ac37cc58362c43655a8df834b16 | pending |
| EK-15 | lib/empty.ts | The view returns when the fault clears. | 54b5e6623828deec5633c4b4ffa8b04e34667cc71173f268418816c82b90a55f | pending |
| HD-01 | /about/how-to-read-a-dossier/ | A dossier is one place's record: what is deployed, who runs it, what it costs, who can see the data, and what SIG does not yet know. This page walks the parts top to bottom. | 3db1c6bfd4cc7a87ab88a97f3bcc06d6e3a818ff8e9fbb112aa45ee46d852a58 | pending |
| HD-02 | /about/how-to-read-a-dossier/ | Every numbered note below links the live section it describes — the example is this release's own dossier for {name}, so the walk can never drift from what the page renders. | 6289e7955986480f351499de8aeeb9b472db11f1392406166eb11632dac22f7f | pending |
| HD-03 | /about/how-to-read-a-dossier/ | The place's name, where it sits in the tree, the release the page was built from, and the Cite, Print, Downloads and JSON actions. | 319a5e5cda24d4f6d9cf92a79b36d67369f6b97c3bde1ea6b727437e43277547 | pending |
| HD-04 | /about/how-to-read-a-dossier/ | A collapsible key listing only the symbols this page carries — expand it whenever a marker is unfamiliar. | 6c471aaf06cfb28b80c7d05d5022e024fcb6ba689533419157869a5362aaa2cc | pending |
| HD-05 | /about/how-to-read-a-dossier/ | One honest count of the fields the record does not yet cover — the number is an invitation to look, never a verdict on the place. | 89d78edc28abb1516b4302aa9024dbe4fd23a82b2375418ce1c98b882e815961 | pending |
| HD-06 | /about/how-to-read-a-dossier/ | The headline gaps up front — each labelled by kind, each linking the task that would close it. | a821b2450d5ff908c6221d3c9214bacda6f8f032eac4478378e0cf638d11ee7f | pending |
| HD-07 | /about/how-to-read-a-dossier/ | {section-bodies} | 2bf03f426866dc19a6259cb2773a33bed397cfbba98a44fc897893149aa69887 | pending |
| HD-08 | /about/how-to-read-a-dossier/ | The sources the page is built on and what each contributes. | 426f247b86d07cdfb3c6598c7a694f0421c34b813a04012eaf46e0da2a0964b3 | pending |
| HD-09 | /about/how-to-read-a-dossier/ | The dated decisions SIG tracks for this place — or the named reason none appear yet. | 6ae655791f2f1438e14aa11ecb585433517297f50090f62a0caffe1de1fbffa9 | pending |
| HD-10 | /about/how-to-read-a-dossier/ | Outside projects a reader may also find useful — linked, never endorsed. | 8669dbf80bb8591408be78a12ee34b2c4bc71be35af10b3dd9b8857d3261c23e | pending |
| HD-11 | /about/how-to-read-a-dossier/ | The places this dossier rolls up — a child with no page is a named absence, not a dead link. | 6b245dec41c18c48688fd3be3ef2caaad637eec432b585fcdbaa590a6885064e | pending |
| HD-12 | /about/how-to-read-a-dossier/ | No joined example dossier in this release | 25e2f2173dbc6e9161dff64e79afb6bc40f9c819e33abe045a0870333c3a6781 | pending |
| HD-13 | /about/how-to-read-a-dossier/ | The annotated walk regenerates from the release's golden dossier — a joined place (three or more sources and a recorded disagreement). This release has none, so the walk annotates the template contract instead of a live page. | 5b2eb31c0135af72443afff78f2d8fd4628a4ec68bdf4ea28e06aa706ab1e317 | pending |
| HD-14 | /about/how-to-read-a-dossier/ | The dossier index lists every place the release does publish. | 73d8302aedca1c147fecfda4a089011a8f8867eb4c3fabb3befb957c1bc5f164 | pending |
| HD-15 | /about/how-to-read-a-dossier/ | Browse the dossier index | 4705b966cf2d58ee8a868364855a7e4e87e2c91cfbafe27aaa9698cb98d482c8 | pending |
| HD-16 | /about/how-to-read-a-dossier/ | The walk re-anchors to a real dossier with the first release that joins one. | b22df30d4f3c3424238cd8572a1b4c4231f7b7af875fbade8fdb4d65c106cf85 | pending |
| HD-17 | /about/how-to-read-a-dossier/ | Numbers are never bare: expand any figure to see the evidence behind it, and look for the markers the key names — support, contested, the absence kinds, and provisional. | e6910e0a19e0cae208509eb03e84e4674207d390ef8876f69a7712de979420c2 | pending |
| EK-16 | lib/empty.ts | SIG does not yet monitor a decision body for this place | 6e7616c71de7cafff73fc9a30eee170b605a6bdab18856bcfc1f3577662677fb | pending |
| EK-17 | lib/empty.ts | SIG does not yet check any agenda or procurement source for this place. Decisions in bodies SIG does not check will not appear here. | edf34b7a2282cfc3018a4a6e9fc56bd0312be95feab211e235169ce4279977b4 | pending |
| EK-18 | lib/empty.ts | The watch index lists the places and bodies SIG does check. | e408e2459e37011afc09502c0b183fadd5c1804dc1fbc82181172169ae30df2c | pending |
| EK-19 | lib/empty.ts | See the research queue | 45b799925bddcd51d01f2346a1dea8e3e7adb3b7ddf2654dfd589b182566fa6c | pending |
| EK-20 | lib/empty.ts | A registered agenda or procurement source for this place would bring it into the monitored set. | 9315e8df6fb436d0818d91dcefdd6cfb142f278ca39f582a5601957c8ec2a74b | pending |
| HD-18 | /about/how-to-read-a-dossier/ | The record's level, counts and freshness in one strip — where the place sits, how much is covered, and when the data was current. | 2dca59a9213a1271a682e8364d4f779aa371d20f0e1b92ddde02f72d34eb3c60 | pending |
