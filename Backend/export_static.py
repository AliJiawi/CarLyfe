import json
from pathlib import Path

from mapping_layer import ingest_file
from pipeline import analyze_vehicles, load_artifact

artifact = load_artifact()

out_dir = Path("fleet_data")
demo_files = [
    out_dir / "demo_zephyr.csv",
    out_dir / "demo_kinto.xlsx",
    out_dir / "demo_marlin.json",
]

all_results = []
for p in demo_files:
    if not p.exists():
        continue
    df, unmapped = ingest_file(p, p.name)
    all_results.extend(analyze_vehicles(df, unmapped, artifact))

with open("static_fallback.json", "w") as f:
    json.dump(all_results, f, indent=2, allow_nan=False)

print(f"Exported {len(all_results)} demo vehicles across Zephyr, Kinto, and Marlin to 'static_fallback.json'")
