# P37.69b fixtures — synthetic reconstructions, never fetched captures

Every file under `fixtures/p37_69b/` is a **synthetic reconstruction** of the
served shape the committed candidate records describe — written by hand for
the `ogc_wfs` connector's replay/shadow tests (`tests/connectors/test_p37_69b_ogc_wfs.py`).
No file was fetched from any live endpoint; the seats stay
`ingestion_permitted=false` pending the operator's OP-26 Wave-D flips.

| file | models | basis |
|---|---|---|
| `capabilities_geoserver.xml` | Runnymede (`camreg_gb_eng_runny_cctv_cameras`, I5-C312) | committed record: "GeoServer WFS community:cctv_cameras"; resource URL `…/geoserver/community/cctv_cameras/wms?service=WMS&request=GetCapabilities` |
| `capabilities_statmap.xml` | South Kesteven (`camreg_gb_eng_south_skdc_cctv`, I5-C315) | committed record: INSPIRE WFS/WMS at `…/map/wfs.svc/SKDC_INSPIRE_WFS` — no typename recorded; the single served type exercises `feature_type_selector = "sole"` |
| `capabilities_cadcorp.xml` | Clackmannanshire (`camreg_gb_sct_clackmannanshire_cctv`, I5-C321) | committed record: literal Cadcorp GetFeature URL `…/WFS/wfs.exe?…&typenames=ns:cctv_cameras` |
| `getfeature_geoserver.xml` | Runnymede feature page | invented member points inside GB-ENG:Runnymede |
| `getfeature_statmap.xml` | South Kesteven feature page | invented member points inside GB-ENG:South Kesteven |
| `getfeature_cadcorp.xml` | Clackmannanshire feature page | invented member points inside GB-SCT:Clackmannanshire |
| `exception_report.xml` | an OGC `ows:ExceptionReport` envelope | drift tests: the lane refuses it closed |

Coordinates are invented points inside each published jurisdiction — they are
test stand-ins, not surveyed camera locations; a fixture run mints claims over
synthetic bytes only.
