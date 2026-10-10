import pandas as pd

REPAIR_COST_USD = {"battery": 250.0, "brakes": 450.0, "tires": 600.0, "coolant": 900.0}

DTC_INFO = {
    "P0562": ("System voltage low", "critical"),
    "P0563": ("System voltage high", "warning"),
    "P0171": ("Fuel system too lean", "warning"),
    "P0172": ("Fuel system too rich", "warning"),
    "P0217": ("Engine overtemperature", "critical"),
    "P0420": ("Catalyst efficiency below threshold", "warning"),
    "C0750": ("Tire pressure sensor circuit", "warning"),
    "U0100": ("Lost communication with engine controller", "critical"),
}


def safe_val(val, default=None):
    if val is None or pd.isna(val):
        return default
    return val


def component(name, status, metric, reason):
    return {"name": name, "status": status, "metric_value": metric, "reason": reason}


def unknown(name, signal):
    return component(name, "unknown", "N/A", f"{signal} not reported by this vehicle.")


def volts(v):
    return "N/A" if v is None else f"{v:.2f} V"


def battery_section(row, rul):
    crank_v = safe_val(row.get("cranking_min_voltage"))
    rest_v = safe_val(row.get("resting_voltage"))
    alt_v = safe_val(row.get("alternator_voltage"))
    age_mo = safe_val(row.get("battery_age_months"))
    short_pct = safe_val(row.get("short_trip_share_pct"))

    drivers = []
    if crank_v is not None:
        if crank_v < 9.0:
            drivers.append(f"severe cranking voltage drop ({crank_v:.2f} V)")
        elif crank_v < 9.6:
            drivers.append(f"cranking voltage sag ({crank_v:.2f} V)")
    if rest_v is not None and rest_v < 12.1:
        drivers.append(f"low resting voltage ({rest_v:.2f} V)")
    if age_mo is not None and age_mo > 48:
        drivers.append(f"battery age ({age_mo:.0f} months)")
    if short_pct is not None and short_pct > 55:
        drivers.append(f"mostly short trips ({short_pct:.0f}% of trips)")
    alt_bad = alt_v is not None and (alt_v < 13.5 or alt_v > 15.1)
    if alt_v is not None and alt_v < 13.5:
        drivers.append(f"weak alternator output ({alt_v:.2f} V)")
    elif alt_v is not None and alt_v > 15.1:
        drivers.append(f"overcharging alternator ({alt_v:.2f} V)")

    health = None
    if age_mo is not None and age_mo + rul > 0:
        health = round(min(100.0, max(0.0, rul / (age_mo + rul) * 100.0)), 1)

    critical = rul < 6.0 or (crank_v is not None and crank_v < 8.8)
    warning = rul < 14.0 or (health is not None and health < 35.0) or (crank_v is not None and crank_v < 9.6)
    factors = ", ".join(drivers)
    head = f"Predicted {rul:g} months of life left."

    if critical:
        status, urgency, penalty = "critical", "critical", 45
        detail = f"Contributing factors: {factors}." if drivers else "No single sensor is out of range; the prediction is driven by battery age and usage pattern."
        reason = f"{head} {detail}"
        action = "Replace the battery at the earliest service visit and test the charging system."
    elif warning:
        status, urgency, penalty = "warning", "elevated", 20
        detail = f"Contributing factors: {factors}." if drivers else "No single sensor is out of range; the prediction is driven by battery age and usage pattern."
        reason = f"{head} {detail}"
        action = "Schedule a battery load test and charging-system check at the next service."
    else:
        status, urgency, penalty = "ok", "nominal", 0
        reason = f"{head} Within limits, but watch: {factors}." if drivers else f"{head} Voltages and age are within normal ranges."
        action = "No action needed; continue routine monitoring."
    if alt_bad:
        action = "Inspect the alternator output (out of range) at the next service." if status == "ok" else f"{action} Also inspect the alternator (output out of range)."

    comp = component("Battery System", status, f"{volts(crank_v)} crank / {volts(rest_v)} rest", reason)
    analytics = {
        "health_pct": health,
        "remaining_months": rul,
        "urgency": urgency,
        "primary_driver": reason,
        "prescriptive_action": action,
    }
    return comp, analytics, penalty


def evaluate_vehicle_health(row, pred_rul_months):
    penalty = 0
    rul = max(0.0, round(float(pred_rul_months), 1))

    battery_comp, battery_analytics, battery_penalty = battery_section(row, rul)
    penalty += battery_penalty
    components = [battery_comp]
    statuses = {"battery": battery_comp["status"]}

    brake_pad = safe_val(row.get("brake_pad_mm"))
    if brake_pad is None:
        comp = unknown("Braking System", "Brake pad thickness")
    elif brake_pad < 2.5:
        comp = component("Braking System", "critical", f"{brake_pad:.1f} mm", "Pad thickness below the 2.5 mm minimum; replace now.")
        penalty += 30
    elif brake_pad < 4.0:
        comp = component("Braking System", "warning", f"{brake_pad:.1f} mm", "Pad thickness below 4 mm; plan replacement.")
        penalty += 15
    else:
        comp = component("Braking System", "ok", f"{brake_pad:.1f} mm", "Pad thickness is within limits.")
    components.append(comp)
    statuses["brakes"] = comp["status"]

    tread = safe_val(row.get("tire_tread_mm"))
    if tread is None:
        comp = unknown("Tires", "Tread depth")
    elif tread < 2.0:
        comp = component("Tires", "critical", f"{tread:.1f} mm", "Tread depth below 2 mm; replace tires.")
        penalty += 30
    elif tread < 3.5:
        comp = component("Tires", "warning", f"{tread:.1f} mm", "Tread depth below 3.5 mm; plan replacement.")
        penalty += 10
    else:
        comp = component("Tires", "ok", f"{tread:.1f} mm", "Tread depth is within limits.")
    components.append(comp)
    statuses["tires"] = comp["status"]

    coolant = safe_val(row.get("coolant_temp_c"))
    if coolant is None:
        comp = unknown("Thermal / Coolant Loop", "Coolant temperature")
    elif coolant > 105.0:
        comp = component("Thermal / Coolant Loop", "critical", f"{coolant:.1f} °C", "Coolant temperature above 105 °C (overheating risk).")
        penalty += 35
    elif coolant > 99.0:
        comp = component("Thermal / Coolant Loop", "warning", f"{coolant:.1f} °C", "Coolant temperature above 99 °C (running hot).")
        penalty += 10
    else:
        comp = component("Thermal / Coolant Loop", "ok", f"{coolant:.1f} °C", "Coolant temperature is within the normal range.")
    components.append(comp)
    statuses["coolant"] = comp["status"]

    trim = safe_val(row.get("fuel_trim_pct"))
    if trim is None:
        comp = unknown("Fuel Trim / Mixture", "Fuel trim")
    elif abs(trim) > 15.0:
        comp = component("Fuel Trim / Mixture", "warning", f"{trim:.1f}%", "Fuel correction beyond ±15%; check for air leaks, injectors or sensors.")
        penalty += 15
    else:
        comp = component("Fuel Trim / Mixture", "ok", f"{trim:.1f}%", "Fuel correction is within ±15%.")
    components.append(comp)

    raw_codes = str(safe_val(row.get("dtc_codes"), ""))
    codes = [c.strip() for c in raw_codes.replace(",", ";").split(";") if c.strip() and c.strip().lower() not in ("none", "nan")]
    if codes:
        info = [DTC_INFO.get(c, ("Unrecognized code", "warning")) for c in codes]
        status = "critical" if any(sev == "critical" for _, sev in info) else "warning"
        reason = "; ".join(f"{c}: {desc}" for c, (desc, _) in zip(codes, info))
        components.append(component("DTC Trouble Codes", status, ";".join(codes), reason))
        penalty += min(35, sum(25 if sev == "critical" else 10 for _, sev in info))
    else:
        components.append(component("DTC Trouble Codes", "ok", "NONE", "No active ECU error codes."))

    overall_score = max(5, int(100 - penalty))
    overall_status = "critical" if overall_score < 60 else ("warning" if overall_score < 80 else "ok")
    risk_cost = sum(REPAIR_COST_USD[k] for k, s in statuses.items() if s == "critical")

    return {
        "overall_health_score": overall_score,
        "overall_status": overall_status,
        "projected_cost_at_risk_usd": float(risk_cost),
        "battery_analytics": battery_analytics,
        "components": components,
    }
