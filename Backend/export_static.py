import json
from pathlib import Path

from llm_explain import add_ai_explanations, get_client, summarize_fleet
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

ai_on = get_client() is not None
add_ai_explanations(all_results, limit=len(all_results))
fleet_summary = summarize_fleet(all_results) if ai_on else None

with open("static_fallback.json", "w") as f:
    json.dump(all_results, f, indent=2, allow_nan=False)
with open("static_fleet_summary.json", "w") as f:
    json.dump({"summary": fleet_summary}, f, indent=2)

written = sum(1 for r in all_results if r.get("ai_explanation"))
print(f"Exported {len(all_results)} demo vehicles to 'static_fallback.json'")
if ai_on:
    print(f"AI explanations written for {written} vehicles; fleet summary: {'yes' if fleet_summary else 'FAILED'}")
else:
    print("GRAFILAB_API_KEY not set: ai_explanation fields are null and no fleet summary was written")
