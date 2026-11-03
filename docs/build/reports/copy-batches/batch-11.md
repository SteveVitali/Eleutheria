# Copy batch 11 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.50 (row 393, downloads center), the row needing new
     public sentences after batch-10 (B-2 "Batches + notice allowance",
     D-J3-12 = OD-07 a): the `/data/` downloads-center and `/data/api/`
     API-docs pages' wording — the latest-view label, the mirror posture,
     the integrity/verify sentences, the listing summary, and the API
     terms — is agent-drafted, pending verbatim confirmation. Append-only:
     rows are never deleted or edited in place — a correction is a new row
     superseding the old id, and a status change is recorded in the
     confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, hosts, licence ids, file names), not drafted copy.
AP-04's `|` separates the four list items.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| DL-01 | /data/ | This page lists the downloads of the latest activated release — {releaseLabel}, data as of {asOfWorld} — a mutable convenience view; cite the fixed release URL below, not this page. | 6fd40361bb4a672d69938837c4d40d5dcb20dd0ba0d69893072a8aef096cafea | pending |
| DL-02 | /data/ | Downloads are served from the zero-egress mirror {mirrorBase} ({provider}) as content-hash keys — a URL names exactly these bytes forever. The mirror is committed-disabled until the publish leg runs; links name the host the objects resolve on once pushed. | 8d2b49327472ed3b735c66fd61ebfddf3f457d7ffcb33391830ef8a523325e2c | pending |
| DL-03 | /data/ | Every bundle's ATTRIBUTION.txt/LICENCE.txt states the captured terms and the operator-accepted basis verbatim (no withdrawal — a bad bundle is corrected by a new release, never retracted silently). | 6b816d3e562435eeb870afc4ccf8682f564d25abb9a78849496f3bfbf5659ea0 | pending |
| DL-04 | /data/ | Signed by the SIG release pipeline ({algorithm}) — the signature proves integrity, never approval. Public key: {publicKeyFile}. | 553008616ce42dc7bef7243140c26202a401a01875fa51747e0b609911632be8 | pending |
| DL-05 | /data/ | Not yet signed — {reason}. {checksumFile} still verifies every byte below. | 8ea1ec5651bdef121758f72d8825c712b2ca9b4ecf14c96b5c06acd1c251b6c9 | pending |
| DL-06 | /data/ | Verify a download: sha256sum -c {checksumFile} · minisign -Vm {checksumFile} -p {publicKeyFile} | 021fbe689149d3cda7c6042e25340d5ffe033bd59e2b18c4ee8e6517d05ff8ca | pending |
| DL-07 | /data/ | {files} files · {bytes} · {compartments} compartments · {sources} per-source slices (each carries its statements slice — the claim-level statements file — plus ATTRIBUTION.txt/LICENCE.txt). | 4a60a22eace35b44ab4fe4f64714b3201c81cc04aa867d73615ef7d27d9bc641 | pending |
| AP-01 | /data/api/ | The public API is read-only. Every transparency page on this site has a JSON twin, and the API serves the same release-backed data — the API URL a page's facts came from is its equivalent request. | 7428984080497cb23338212ffc720e218e6d1c4a0a60b673075b988ee2b544c3 | pending |
| AP-02 | /data/api/ | A page's machine-readable twin is named in its Technical details or beside its download links — the same rows, licences and counts the HTML shows. The release-pinned twin is the citable form; the site-root twin is the mutable latest view. | a23987b9df2b239e54ad9d8c50697a136fa31f456c0348610108e7379dce3e8c | pending |
| AP-03 | /data/api/ | Release-pinned routes answer from the immutable release files. Anything a route serves beyond the pinned release is labelled live, not a citation. | f5b48a698a79c759c27ce591a36bbc86c64cd5ab7fc1a0df50cee3685512fc76 | pending |
| AP-04 | /data/api/ | 30 requests per 60 seconds per client, burst 10 — a 429 answer names the retry. \| Read-only; no API key. Bulk data belongs to the downloads, not repeated paging. \| Each response's data carries the compartment licence of the release it came from. \| No query logging for search; requests are never tied to a reader's identity. | 383100bc6e4716a045129e450330d7f823132bb4f2614ec7ba3e6cd31385b58a | pending |

## Confirmation log

<!-- one line per status change, `date -u` stamped; empty until the
     operator confirms a row verbatim. -->
