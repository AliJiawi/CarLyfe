import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
PER_BRAND = 110
DEMO_PER_BRAND = 10
OUT = Path("fleet_data")

BRANDS = {
    "Zephyr": {"prefix": "ZPH", "models": ["Aria", "Volta"]},
    "Kinto": {"prefix": "KNT", "models": ["Hikari", "Sora", "Mizu"]},
    "Marlin": {"prefix": "MRL", "models": ["Tide", "Surge", "Harbor"]},
}
ZONES = ["tropical", "hot_arid", "temperate", "cold"]
ZONE_P = [0.4, 0.15, 0.3, 0.15]
ZONE_LIFE = {"tropical": 0.85, "hot_arid": 0.8, "temperate": 1.0, "cold": 0.95}
ZONE_COOLANT = {"tropical": 3, "hot_arid": 5, "temperate": 0, "cold": -3}
ZONE_COLD = {"tropical": 0, "hot_arid": 0, "temperate": 0, "cold": 1}

COMMON_COLUMNS = [
    "vehicle_id", "brand", "model", "odometer_km", "battery_age_months",
    "short_trip_share_pct", "resting_voltage", "cranking_min_voltage",
    "cranking_duration_ms", "alternator_voltage", "coolant_temp_c",
    "tire_tread_mm", "brake_pad_mm", "fuel_trim_pct", "dtc_codes",
    "climate_zone", "rul_months", "battery_health_pct",
]
SPARSE_COLUMNS = ["coolant_temp_c", "tire_tread_mm", "brake_pad_mm", "fuel_trim_pct"]


def make_brand(rng, brand, n):
    cfg = BRANDS[brand]
    zone = rng.choice(ZONES, size=n, p=ZONE_P)
    short = np.clip(rng.beta(2, 5, n) * 100, 2, 85)
    veh_age = rng.integers(6, 121, n)
    annual = np.clip(rng.normal(14000, 4500, n), 4000, 30000)
    odo = np.clip(veh_age / 12 * annual + rng.normal(0, 800, n), 500, None)

    life = (
        52
        * np.array([ZONE_LIFE[z] for z in zone])
        * (1 - 0.35 * short / 100)
        * rng.lognormal(0, 0.12, n)
    )
    batt_age = np.where(rng.random(n) < 0.6, veh_age, rng.uniform(2, veh_age))
    batt_age = np.minimum(batt_age, 96)
    replaced = batt_age > life + 4
    batt_age = np.where(replaced, rng.uniform(1, 0.6 * life), batt_age)

    d = np.clip((batt_age / life) ** 1.5, 0, 1.5)
    rul = np.clip(life - batt_age, 0, None)
    soh = np.clip(100 - 30 * d, 0, 100)
    cold = np.array([ZONE_COLD[z] for z in zone])

    rest = np.clip(12.72 - 0.75 * d + rng.normal(0, 0.04, n), 11.6, 12.78)
    crank_min = np.clip(10.7 - 1.9 * d - 0.5 * cold + rng.normal(0, 0.15, n), 7.5, 11.2)
    crank_ms = np.clip(480 + 650 * d**1.3 + 120 * cold + rng.normal(0, 40, n), 300, 2500)

    alt = rng.normal(14.35, 0.12, n)
    u = rng.random(n)
    alt = np.where(
        u < 0.04,
        rng.uniform(12.6, 13.4, n),
        np.where(u > 0.985, rng.uniform(15.2, 15.8, n), alt),
    )

    coolant = rng.normal(90, 3, n) + np.array([ZONE_COOLANT[z] for z in zone])
    coolant = np.where(rng.random(n) < 0.05, rng.uniform(100, 112, n), coolant)

    tire_km = np.minimum(rng.uniform(0, 50000, n), odo)
    tread = np.clip(8.5 - 7 * tire_km / 50000 + rng.normal(0, 0.3, n), 1.0, 9.0)
    brake_km = np.minimum(rng.uniform(0, 70000, n), odo)
    pad = np.clip(12 - 9 * brake_km / 70000 * (1 + short / 200) + rng.normal(0, 0.4, n), 1.5, 12.0)

    trim = rng.normal(0, 3, n)
    trim = np.where(rng.random(n) < 0.08, rng.choice([-1, 1], n) * rng.normal(14, 3, n), trim)
    trim = np.clip(trim, -25, 25)

    codes = []
    for i in range(n):
        c = []
        if (soh[i] < 78 and rng.random() < 0.6) or alt[i] < 13.5:
            c.append("P0562")
        if alt[i] > 15.1:
            c.append("P0563")
        if trim[i] > 10:
            c.append("P0171")
        if trim[i] < -10:
            c.append("P0172")
        if coolant[i] > 100:
            c.append("P0217")
        if rng.random() < 0.03:
            c.append("P0420")
        if rng.random() < 0.02:
            c.append("C0750")
        if rng.random() < 0.01:
            c.append("U0100")
        codes.append(";".join(c))

    if brand == "Marlin":
        ids = [f"1MRL{rng.integers(10**12, 10**13)}" for _ in range(n)]
    else:
        ids = [f"{cfg['prefix']}-{i + 1:05d}" for i in range(n)]

    df = pd.DataFrame(
        {
            "vehicle_id": ids,
            "brand": brand,
            "model": rng.choice(cfg["models"], n),
            "odometer_km": odo.round(0),
            "battery_age_months": batt_age.round(1),
            "short_trip_share_pct": short.round(1),
            "resting_voltage": rest.round(2),
            "cranking_min_voltage": crank_min.round(2),
            "cranking_duration_ms": crank_ms.round(0),
            "alternator_voltage": alt.round(2),
            "coolant_temp_c": coolant.round(1),
            "tire_tread_mm": tread.round(1),
            "brake_pad_mm": pad.round(1),
            "fuel_trim_pct": trim.round(1),
            "dtc_codes": codes,
            "climate_zone": zone,
            "rul_months": rul.round(1),
            "battery_health_pct": soh.round(1),
        }
    )
    assert df.vehicle_id.is_unique
    return df[COMMON_COLUMNS]


def pick_demo(df, k):
    order = df.sort_values("rul_months", kind="stable").index.to_list()
    pos = np.linspace(0, len(order) - 1, k).round().astype(int)
    return [order[p] for p in pos]


def add_gaps(df, rng):
    out = df.copy()
    for col in SPARSE_COLUMNS:
        out.loc[rng.random(len(out)) < 0.015, col] = np.nan
    return out


def clean(x):
    return None if pd.isna(x) else float(x)


def export_zephyr(df, path, rng):
    region = {"tropical": "SEA", "hot_arid": "MENA", "temperate": "EU-TEMP", "cold": "NORDIC"}
    out = pd.DataFrame(
        {
            "VehicleRef": df.vehicle_id,
            "ModelName": df.model,
            "Mileage_km": df.odometer_km.astype(int),
            "BatteryAgeMonths": df.battery_age_months,
            "ShortTripPct": df.short_trip_share_pct,
            "BattRestV": df.resting_voltage,
            "CrankMinV": df.cranking_min_voltage,
            "CrankDurMs": df.cranking_duration_ms.astype(int),
            "AlternatorV": df.alternator_voltage,
            "CoolantC": df.coolant_temp_c,
            "TreadDepthMM": df.tire_tread_mm,
            "BrakePadMM": df.brake_pad_mm,
            "FuelTrimPct": df.fuel_trim_pct,
            "FaultCodes": df.dtc_codes.str.replace(";", "|", regex=False),
            "Region": df.climate_zone.map(region),
            "InfotainmentSW": rng.choice(["4.2.1", "4.3.0", "5.0.2"], len(df)),
        }
    )
    out.to_csv(path, index=False, sep=";")


def export_kinto(df, path, rng):
    zone = {"tropical": "Hot-Humid", "hot_arid": "Hot-Dry", "temperate": "Mild", "cold": "Cold"}
    out = pd.DataFrame(
        {
            "veh_id": df.vehicle_id,
            "model_code": df.model,
            "odo_km": df.odometer_km.astype(int),
            "batt_age_yr": (df.battery_age_months / 12).round(2),
            "short_trip_pct": df.short_trip_share_pct,
            "batt_rest_mv": (df.resting_voltage * 1000).round(0),
            "batt_crank_min_mv": (df.cranking_min_voltage * 1000).round(0),
            "crank_time_s": (df.cranking_duration_ms / 1000).round(2),
            "alt_out_v": df.alternator_voltage,
            "coolant_temp_c": df.coolant_temp_c,
            "tire_tread_mm": df.tire_tread_mm,
            "brake_pad_mm": df.brake_pad_mm,
            "fuel_trim_pct": df.fuel_trim_pct,
            "dtc_list": df.dtc_codes.str.replace(";", ", ", regex=False),
            "zone": df.climate_zone.map(zone),
            "cabin_air_idx": rng.integers(20, 120, len(df)),
            "sw_build": rng.choice(["K-210", "K-214", "K-301"], len(df)),
        }
    )
    out.to_excel(path, index=False, sheet_name="FleetExport")


def export_marlin(df, path, rng):
    region = {
        "tropical": "Gulf Coast",
        "hot_arid": "Southwest",
        "temperate": "Midwest",
        "cold": "Northern Plains",
    }
    rows = []
    for r in df.itertuples():
        tread = clean(r.tire_tread_mm)
        pad = clean(r.brake_pad_mm)
        coolant = clean(r.coolant_temp_c)
        rows.append(
            {
                "vin": r.vehicle_id,
                "vehicle": {"make": "Marlin", "model": r.model},
                "odometer_mi": round(r.odometer_km / 1.609344, 0),
                "battery": {
                    "age_months": r.battery_age_months,
                    "rest_voltage": r.resting_voltage,
                    "crank_min_voltage": r.cranking_min_voltage,
                    "crank_ms": r.cranking_duration_ms,
                    "alternator_voltage": r.alternator_voltage,
                },
                "temps_f": {"coolant_f": None if coolant is None else round(coolant * 9 / 5 + 32, 1)},
                "wear": {
                    "tire_tread_32nds": None if tread is None else round(tread * 32 / 25.4, 1),
                    "brake_pad_32nds": None if pad is None else round(pad * 32 / 25.4, 1),
                },
                "fuel_trim": {"ltft_pct": clean(r.fuel_trim_pct)},
                "trips": {"short_trip_pct": r.short_trip_share_pct},
                "dtcs": [c for c in r.dtc_codes.split(";") if c],
                "region": region[r.climate_zone],
                "telematics": {"ota_channel": str(rng.choice(["stable", "beta"]))},
            }
        )
    with open(path, "w") as f:
        json.dump({"export_version": "2.1", "vehicles": rows}, f, indent=2)


EXPORTERS = {
    "Zephyr": (export_zephyr, "csv"),
    "Kinto": (export_kinto, "xlsx"),
    "Marlin": (export_marlin, "json"),
}


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(exist_ok=True)

    fleet, demo = {}, {}
    for brand in BRANDS:
        df = make_brand(rng, brand, PER_BRAND)
        idx = pick_demo(df, DEMO_PER_BRAND)
        demo[brand] = df.loc[idx].reset_index(drop=True)
        fleet[brand] = df.drop(index=idx).reset_index(drop=True)

    pd.concat(fleet.values(), ignore_index=True).to_csv(OUT / "fleet_common_truth.csv", index=False)
    pd.concat(demo.values(), ignore_index=True).to_csv(OUT / "demo_common_truth.csv", index=False)

    for brand, (exporter, ext) in EXPORTERS.items():
        exporter(add_gaps(fleet[brand], rng), OUT / f"fleet_{brand.lower()}.{ext}", rng)
        exporter(add_gaps(demo[brand], rng), OUT / f"demo_{brand.lower()}.{ext}", rng)

    print(sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()