# P37.47 fixtures — synthetic reconstructions (ACQ-19 tier-2 reuse wave)

Every fixture in this directory is a SYNTHETIC reconstruction authored at the
P37.47 registration review from the candidate records' live-read evidence
(docs/build/planning/2026-09-30-next-phase/data/candidates_*.csv +
acquisition_plan.csv AP-T2 rows). They are NOT captured bytes — the committed
fixture shape exercises the reviewed target rows' emit paths; a live first run
reconciles against the real upstream (drift records, never smooths).

- `*.json` — ArcGIS REST query envelopes ({"features":[{attributes,geometry}]})
  for the ten pinned dot_511/camera-registry target rows.
- `*.html` — minimal index/document pages for the twenty `dossier_documents`
  targets (anchor/link + literal coverage per the configured listings/fields).
