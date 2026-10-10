import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

COMMON_COLUMNS = [
    "vehicle_id", "brand", "model", "odometer_km", "battery_age_months",
    "short_trip_share_pct", "resting_voltage", "cranking_min_voltage",
    "cranking_duration_ms", "alternator_voltage", "coolant_temp_c",
    "tire_tread_mm", "brake_pad_mm", "fuel_trim_pct", "dtc_codes",
    "climate_zone",
]
TEXT_DEFAULTS = {"brand": "unknown", "model": "unknown", "dtc_codes": "", "climate_zone": "unknown"}
MIN_MATCH = 0.7


def keep(s):
    return s


def num(scale=1.0, offset=0.0, digits=None):
    def convert(s):
        out = pd.to_numeric(s, errors="coerce") * scale + offset
        return out.round(digits) if digits is not None else out
    return convert


def label(table):
    def convert(s):
        return s.map(table)
    return convert


def dtc(sep):
    def one(v, sep=sep):
        if isinstance(v, (list, tuple)):
            return ";".join(str(c).strip() for c in v if str(c).strip())
        if pd.isna(v):
            return ""
        return ";".join(c.strip() for c in str(v).split(sep) if c.strip())

    def convert(s):
        return s.map(one)
    return convert


PROFILES = {
    "zephyr": {
        "brand": "Zephyr",
        "columns": {
            "vehicle_id": ("VehicleRef", keep),
            "brand": (None, None),
            "model": ("ModelName", keep),
            "odometer_km": ("Mileage_km", num()),
            "battery_age_months": ("BatteryAgeMonths", num()),
            "short_trip_share_pct": ("ShortTripPct", num()),
            "resting_voltage": ("BattRestV", num()),
            "cranking_min_voltage": ("CrankMinV", num()),
            "cranking_duration_ms": ("CrankDurMs", num()),
            "alternator_voltage": ("AlternatorV", num()),
            "coolant_temp_c": ("CoolantC", num()),
            "tire_tread_mm": ("TreadDepthMM", num()),
            "brake_pad_mm": ("BrakePadMM", num()),
            "fuel_trim_pct": ("FuelTrimPct", num()),
            "dtc_codes": ("FaultCodes", dtc("|")),
            "climate_zone": ("Region", label({"SEA": "tropical", "MENA": "hot_arid", "EU-TEMP": "temperate", "NORDIC": "cold"})),
        },
    },
    "kinto": {
        "brand": "Kinto",
        "columns": {
            "vehicle_id": ("veh_id", keep),
            "brand": (None, None),
            "model": ("model_code", keep),
            "odometer_km": ("odo_km", num()),
            "battery_age_months": ("batt_age_yr", num(12.0, digits=1)),
            "short_trip_share_pct": ("short_trip_pct", num()),
            "resting_voltage": ("batt_rest_mv", num(0.001, digits=2)),
            "cranking_min_voltage": ("batt_crank_min_mv", num(0.001, digits=2)),
            "cranking_duration_ms": ("crank_time_s", num(1000.0, digits=0)),
            "alternator_voltage": ("alt_out_v", num()),
            "coolant_temp_c": ("coolant_temp_c", num()),
            "tire_tread_mm": ("tire_tread_mm", num()),
            "brake_pad_mm": ("brake_pad_mm", num()),
            "fuel_trim_pct": ("fuel_trim_pct", num()),
            "dtc_codes": ("dtc_list", dtc(",")),
            "climate_zone": ("zone", label({"Hot-Humid": "tropical", "Hot-Dry": "hot_arid", "Mild": "temperate", "Cold": "cold"})),
        },
    },
    "marlin": {
        "brand": "Marlin",
        "columns": {
            "vehicle_id": ("vin", keep),
            "brand": ("vehicle.make", keep),
            "model": ("vehicle.model", keep),
            "odometer_km": ("odometer_mi", num(1.609344, digits=0)),
            "battery_age_months": ("battery.age_months", num()),
            "short_trip_share_pct": ("trips.short_trip_pct", num()),
            "resting_voltage": ("battery.rest_voltage", num()),
            "cranking_min_voltage": ("battery.crank_min_voltage", num()),
            "cranking_duration_ms": ("battery.crank_ms", num()),
            "alternator_voltage": ("battery.alternator_voltage", num()),
            "coolant_temp_c": ("temps_f.coolant_f", num(5 / 9, -160 / 9, digits=1)),
            "tire_tread_mm": ("wear.tire_tread_32nds", num(25.4 / 32, digits=1)),
            "brake_pad_mm": ("wear.brake_pad_32nds", num(25.4 / 32, digits=1)),
            "fuel_trim_pct": ("fuel_trim.ltft_pct", num()),
            "dtc_codes": ("dtcs", dtc(";")),
            "climate_zone": ("region", label({"Gulf Coast": "tropical", "Southwest": "hot_arid", "Midwest": "temperate", "Northern Plains": "cold"})),
        },
    },
}


def source_columns(profile):
    return {src for src, _ in profile["columns"].values() if src}


def read_bytes(source):
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    data = source.read()
    return data.encode("utf-8") if isinstance(data, str) else data


def load_raw(data, filename):
    name = filename.lower()
    extra = []
    if name.endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        first_line = text.splitlines()[0]
        sep = ";" if first_line.count(";") > first_line.count(",") else ","
        raw = pd.read_csv(io.StringIO(text), sep=sep)
    elif name.endswith(".xlsx"):
        raw = pd.read_excel(io.BytesIO(data))
    elif name.endswith(".json"):
        payload = json.loads(data.decode("utf-8-sig"))
        vehicles = payload.get("vehicles") if isinstance(payload, dict) else payload
        if not isinstance(vehicles, list):
            raise ValueError("JSON export must be a list of vehicles or an object with a 'vehicles' list")
        if isinstance(payload, dict):
            extra = [k for k in payload if k != "vehicles"]
        raw = pd.json_normalize(vehicles)
    else:
        raise ValueError(f"Unsupported file format: {filename}. Use .csv, .xlsx or .json")
    return raw, extra


def detect_profile(columns):
    cols = set(columns)
    scores = sorted(
        ((len(source_columns(p) & cols) / len(source_columns(p)), key) for key, p in PROFILES.items()),
        reverse=True,
    )
    score, key = scores[0]
    if score < MIN_MATCH:
        raise ValueError(
            f"Unrecognized export format: only {score:.0%} of the columns of the closest brand profile "
            f"({PROFILES[key]['brand']}) were found. Columns in file: {', '.join(sorted(map(str, cols))[:25])}"
        )
    return key


def apply_profile(raw, profile):
    out = pd.DataFrame(index=raw.index)
    missing = []
    for col in COMMON_COLUMNS:
        source, convert = profile["columns"][col]
        if col == "brand":
            if source and source in raw.columns:
                out[col] = raw[source].fillna(profile["brand"])
            else:
                out[col] = profile["brand"]
        elif source in raw.columns:
            out[col] = convert(raw[source])
        else:
            missing.append(col)
            if col == "vehicle_id":
                out[col] = [f"{profile['brand']}-{i + 1:05d}" for i in range(len(raw))]
            else:
                out[col] = TEXT_DEFAULTS.get(col, np.nan)
    out["model"] = out["model"].fillna("unknown")
    out["dtc_codes"] = out["dtc_codes"].fillna("")
    out["climate_zone"] = out["climate_zone"].fillna("unknown")
    return out.reset_index(drop=True), missing


def ingest_file(file_path_or_bytes, filename):
    data = read_bytes(file_path_or_bytes)
    if not data.strip():
        raise ValueError("The uploaded file is empty")
    try:
        raw, extra = load_raw(data, filename)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, json.JSONDecodeError, zipfile.BadZipFile) as e:
        raise ValueError(f"Could not read {filename}: {e}") from e
    profile = PROFILES[detect_profile(raw.columns)]
    clean_df, missing = apply_profile(raw, profile)
    used = source_columns(profile)
    unmapped = [c for c in raw.columns if c not in used] + extra
    clean_df.attrs["missing_signals"] = missing
    clean_df.attrs["brand_profile"] = profile["brand"]
    return clean_df, unmapped


if __name__ == "__main__":
    out_dir = Path("fleet_data")
    truth = pd.read_csv(out_dir / "demo_common_truth.csv").set_index("vehicle_id")
    numeric = [c for c in COMMON_COLUMNS if c in truth.columns and truth[c].dtype.kind == "f"]
    for name in ["demo_zephyr.csv", "demo_kinto.xlsx", "demo_marlin.json"]:
        df, unmapped = ingest_file(out_dir / name, name)
        diff = (df.set_index("vehicle_id")[numeric] - truth.loc[df.vehicle_id, numeric]).abs().max()
        print(f"{name}: {len(df)} cars, brand {df.attrs['brand_profile']}")
        print(f"  unmapped signals: {unmapped}")
        print(f"  missing signals:  {df.attrs['missing_signals']}")
        print(f"  largest difference from ground truth: {diff.max():.3f} ({diff.idxmax()})")
