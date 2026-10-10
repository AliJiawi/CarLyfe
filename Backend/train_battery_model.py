from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

import generate_synthetic_fleet as sim
from pipeline import ARTIFACT_PATH, FEATURES, NUMERIC_FEATURES, build_features

TARGET = "rul_months"
TRAIN_SEED = 2026
TRAIN_PER_BRAND = 1500
HOLDOUT_FILES = {
    "fleet files": Path("fleet_data/fleet_common_truth.csv"),
    "demo files": Path("fleet_data/demo_common_truth.csv"),
}

rng = np.random.default_rng(TRAIN_SEED)
train_df = pd.concat(
    [sim.make_brand(rng, brand, TRAIN_PER_BRAND) for brand in sim.BRANDS],
    ignore_index=True,
)
medians = train_df[NUMERIC_FEATURES].median().to_dict()

model = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42, n_jobs=-1)
model.fit(build_features(train_df, medians), train_df[TARGET])

print("=" * 55)
print("        BATTERY RUL MODEL BENCHMARK (simulated data)")
print("=" * 55)
print(f"Trained on {len(train_df)} simulated vehicles")

metrics = {}
for name, path in HOLDOUT_FILES.items():
    if not path.exists():
        continue
    hold = pd.read_csv(path)
    preds = model.predict(build_features(hold, medians))
    mae = mean_absolute_error(hold[TARGET], preds)
    r2 = r2_score(hold[TARGET], preds)
    metrics[name] = {"cars": len(hold), "mae_months": round(float(mae), 2), "r2": round(float(r2), 3)}
    print(f"{name} ({len(hold)} cars never seen in training): MAE {mae:.2f} months, R2 {r2:.3f}")
print("=" * 55)

importances = dict(sorted(
    zip(FEATURES, [round(float(v), 3) for v in model.feature_importances_]),
    key=lambda item: item[1],
    reverse=True,
))

joblib.dump(
    {
        "model": model,
        "features": FEATURES,
        "medians": medians,
        "importances": importances,
        "metrics": metrics,
        "training_cars": len(train_df),
    },
    ARTIFACT_PATH,
)
print(f"Exported model artifact to '{ARTIFACT_PATH.name}'")
