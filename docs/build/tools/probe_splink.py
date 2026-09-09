import pandas as pd
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
import splink.comparison_library as cl

df = pd.DataFrame([
    {"unique_id": 1, "name": "travis county sheriff office", "state": "TX"},
    {"unique_id": 2, "name": "travis county so", "state": "TX"},
    {"unique_id": 3, "name": "los angeles police department", "state": "CA"},
    {"unique_id": 4, "name": "los angeles police dept", "state": "CA"},
])

settings = SettingsCreator(
    link_type="dedupe_only",
    comparisons=[
        cl.JaroWinklerAtThresholds("name", [0.9, 0.7]),
        cl.ExactMatch("state"),
    ],
    blocking_rules_to_generate_predictions=[block_on("state")],
    probability_two_random_records_match=0.01,
)
db_api = DuckDBAPI()
linker = Linker(df, settings, db_api)
# Fully specify m/u so predict is deterministic (no EM training).
# Inspect what settings API exposes.
res = linker.inference.predict(threshold_match_weight=-20)
pdf = res.as_pandas_dataframe()
print("COLUMNS:", list(pdf.columns))
print(pdf.to_string())
