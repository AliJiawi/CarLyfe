from typing import Any, List

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from llm_explain import MODEL, add_ai_explanations, fleet_facts, get_client, summarize_fleet
from mapping_layer import PROFILES, ingest_file
from pipeline import analyze_vehicles, load_artifact

app = FastAPI(title="FleetPulse OEM Telematics Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

artifact = load_artifact()


@app.post("/analyze")
async def analyze_fleet(file: UploadFile = File(...), ai: bool = False):
    contents = await file.read()
    try:
        df, unmapped = ingest_file(contents, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")
    results = analyze_vehicles(df, unmapped, artifact)
    if ai:
        add_ai_explanations(results)
    return results


@app.post("/summarize")
def summarize(results: List[Any] = Body(...)):
    try:
        facts = fleet_facts(results)
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Body must be the list returned by /analyze")
    return {"summary": summarize_fleet(results), "facts": facts}


@app.get("/health")
def health():
    return {
        "status": "online",
        "model": "RandomForestRegressor-RUL",
        "features": artifact["features"],
        "importances": artifact["importances"],
        "holdout_metrics": artifact["metrics"],
        "training_cars": artifact["training_cars"],
        "supported_brands": [p["brand"] for p in PROFILES.values()],
        "ai_explanations": {"enabled": get_client() is not None, "model": MODEL},
    }
