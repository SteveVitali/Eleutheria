import json
import pandas as pd
from splink import DuckDBAPI, Linker

df = pd.DataFrame([
    {"unique_id": 1, "name": "travis county sheriff office", "state": "TX"},
    {"unique_id": 2, "name": "travis county so", "state": "TX"},
    {"unique_id": 3, "name": "los angeles police department", "state": "CA"},
    {"unique_id": 4, "name": "houston police department", "state": "TX"},
])

# A fully-specified settings dict: every comparison level carries m/u, so predict()
# is deterministic and needs no training.
settings = {
    "link_type": "dedupe_only",
    "probability_two_random_records_match": 0.01,
    "retain_intermediate_calculation_columns": True,
    "blocking_rules_to_generate_predictions": [{"blocking_rule": 'l."state" = r."state"'}],
    "comparisons": [
        {
            "output_column_name": "name",
            "comparison_levels": [
                {"sql_condition": '"name_l" IS NULL OR "name_r" IS NULL', "label_for_charts": "Null", "is_null_level": True},
                {"sql_condition": '"name_l" = "name_r"', "label_for_charts": "Exact", "m_probability": 0.6, "u_probability": 0.0001},
                {"sql_condition": 'jaro_winkler_similarity("name_l","name_r") >= 0.9', "label_for_charts": "JW>=0.9", "m_probability": 0.3, "u_probability": 0.01},
                {"sql_condition": "ELSE", "label_for_charts": "All other", "m_probability": 0.1, "u_probability": 0.9899},
            ],
        },
        {
            "output_column_name": "state",
            "comparison_levels": [
                {"sql_condition": '"state_l" IS NULL OR "state_r" IS NULL', "label_for_charts": "Null", "is_null_level": True},
                {"sql_condition": '"state_l" = "state_r"', "label_for_charts": "Exact", "m_probability": 0.9, "u_probability": 0.02},
                {"sql_condition": "ELSE", "label_for_charts": "All other", "m_probability": 0.1, "u_probability": 0.98},
            ],
        },
    ],
}
db_api = DuckDBAPI()
linker = Linker(df, settings, db_api)
res = linker.inference.predict(threshold_match_weight=-20)
pdf = res.as_pandas_dataframe()
cols = [c for c in pdf.columns if c.startswith(("match_", "gamma_", "bf_")) or c in ("unique_id_l","unique_id_r")]
print("ALLCOLS:", list(pdf.columns))
print(pdf[cols].to_string())
