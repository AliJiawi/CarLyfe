from pathlib import Path

import joblib
import pandas as pd

from rules_engine import evaluate_vehicle_health

NUMERIC_FEATURES = [
    "battery_age_months",
    "short_trip_share_pct",
    "resting_voltage",
    "cranking_min_voltage",
    "cranking_duration_ms",
    "alternator_voltage",
    "odometer_km",
]
ZONES = ["tropical", "hot_arid", "temperate", "cold"]
FEATURES = NUMERIC_FEATURES + [f"zone_{z}" for z in ZONES]
ARTIFACT_PATH = Path(__file__).with_name("battery_rf_pipeline.pkl")


def build_features(df, medians):
    X = df[NUMERIC_FEATURES].apply(pd.to_numeric, errors="coerce")
    X = X.fillna(pd.Series(medians))
    for zone in ZONES:
        X[f"zone_{zone}"] = (df["climate_zone"] == zone).astype(float)
    return X[FEATURES]


def load_artifact():
    return joblib.load(ARTIFACT_PATH)


def analyze_vehicles(df, unmapped, artifact):
    X = build_features(df, artifact["medians"])
    predictions = artifact["model"].predict(X)
    missing = list(df.attrs.get("missing_signals", []))
    results = []
    for i, row in enumerate(df.to_dict("records")):
        diagnosis = evaluate_vehicle_health(row, predictions[i])
        odometer = row.get("odometer_km")
        results.append({
            "vehicle_id": str(row["vehicle_id"]),
            "brand": str(row["brand"]),
            "model": str(row["model"]),
            "odometer_km": None if pd.isna(odometer) else int(odometer),
            "climate_zone": str(row["climate_zone"]),
            **diagnosis,
            "unmapped_signals": list(unmapped),
            "missing_signals": missing,
        })
    return results
