from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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
async def analyze_fleet(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        df, unmapped = ingest_file(contents, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")
    return analyze_vehicles(df, unmapped, artifact)


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
    }
