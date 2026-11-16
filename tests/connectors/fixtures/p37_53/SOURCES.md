# P37.53 fixtures — synthetic reconstructions (ACQ-26 S1 screened lane)

Every fixture in this directory is a SYNTHETIC reconstruction authored at the
P37.53 registration review from the candidate records' live-read evidence
(docs/build/planning/2026-09-30-next-phase/data/candidates_*.csv +
acquisition_plan.csv AP-T2 rows). They are NOT captured bytes — the committed
fixture shape exercises the reviewed target rows' emit paths; a live first run
reconciles against the real upstream (drift records, never smooths).

- `*_features.json` — ArcGIS REST query envelopes ({"features":[{attributes,
  geometry}]}) carrying the operator_screen lane's AGENCY-row allowlist
  (OBJECTID + geometry only — the S1 screen's private-operator values are
  never represented, exactly as the server-side `IN` screen returns them).
- `*_count.json` — ArcGIS `returnCountOnly` envelopes ({"count": N}) — the
  private-operator complement total or the count_only lane's published total.
- `eye_on_nola.json` — the Django REST Framework paginated envelope
  ({"count": N, "next", "previous", "results": [one row]}) the
  django_rest_api lane reads under its declared page_size=1 contract; the
  result row carries field NAMES only (denied names are a whole refusal).
- `*.html` — minimal programme pages for the ten `dossier_documents` targets
  (the reviewed field literals verbatim; no registrant content by
  construction — the S1 lane asserts portal existence only).
