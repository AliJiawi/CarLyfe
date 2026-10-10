import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BASE_URL = os.environ.get("GRAFILAB_BASE_URL", "https://llm.grafilab.ai/v1")
MODEL = os.environ.get("GRAFILAB_MODEL", "gemini/gemini-3.1-flash-lite-preview")
TIMEOUT_S = float(os.environ.get("GRAFILAB_TIMEOUT", "20"))
MAX_AI_VEHICLES = int(os.environ.get("MAX_AI_VEHICLES", "10"))

CAR_SYSTEM = (
    "You write short vehicle health notes for a car manufacturer's fleet service team. "
    "Use ONLY the facts in the JSON you are given. Do not invent causes, parts, prices or numbers. "
    "Write 2 to 3 plain sentences with no markdown, no bullet points and no headings. "
    "Say what is wrong, why the data suggests it, and what service should do first. "
    "The remaining battery life comes from a machine learning model trained on simulated data; refer to it as a prediction."
)
FLEET_SYSTEM = (
    "You write a short fleet health briefing for a car manufacturer's service planner. "
    "Use ONLY the figures in the JSON you are given and do not compute or invent other numbers. "
    "Write 3 to 4 plain sentences with no markdown and no bullet points. "
    "Lead with how many vehicles need attention and the most common problem, then mention any pattern by brand or climate zone."
)

_client = None


def get_client():
    global _client
    key = os.environ.get("GRAFILAB_API_KEY")
    if not key:
        return None
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=key, base_url=BASE_URL, timeout=TIMEOUT_S, max_retries=1)
    return _client


def ask(system, payload, max_tokens=300):
    client = get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None


def car_facts(result):
    battery = result["battery_analytics"]
    return {
        "vehicle": f"{result['brand']} {result['model']}",
        "climate_zone": result["climate_zone"],
        "overall_health_score": result["overall_health_score"],
        "overall_status": result["overall_status"],
        "battery": {
            "predicted_remaining_months": battery["remaining_months"],
            "health_pct": battery["health_pct"],
            "status": result["components"][0]["status"],
            "signals": result["components"][0]["metric_value"],
            "rule_based_note": battery["primary_driver"],
        },
        "other_issues": [
            {"part": c["name"], "status": c["status"], "reading": c["metric_value"], "note": c["reason"]}
            for c in result["components"][1:]
            if c["status"] in ("warning", "critical")
        ],
        "sensors_not_reported": result.get("missing_signals", []),
    }


def explain_vehicle(result):
    return ask(CAR_SYSTEM, car_facts(result))


def needs_attention(result):
    return result["overall_status"] != "ok" or result["components"][0]["status"] != "ok"


def add_ai_explanations(results, limit=None):
    limit = MAX_AI_VEHICLES if limit is None else limit
    for r in results:
        r["ai_explanation"] = None
    if get_client() is None or limit <= 0:
        return results
    targets = sorted((r for r in results if needs_attention(r)), key=lambda r: r["overall_health_score"])[:limit]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for r, text in zip(targets, pool.map(explain_vehicle, targets)):
            r["ai_explanation"] = text
    return results


def fleet_facts(results):
    total = len(results)
    by_status = Counter(r["overall_status"] for r in results)
    problems = Counter()
    for r in results:
        for c in r["components"]:
            if c["status"] in ("warning", "critical"):
                problems[f"{c['name']} ({c['status']})"] += 1
    battery_urgent = [r for r in results if r["components"][0]["status"] == "critical"]
    by_brand = {}
    by_zone = {}
    for r in results:
        if r["components"][0]["status"] != "ok":
            by_brand[r["brand"]] = by_brand.get(r["brand"], 0) + 1
            by_zone[r["climate_zone"]] = by_zone.get(r["climate_zone"], 0) + 1
    return {
        "vehicles_analyzed": total,
        "vehicles_by_overall_status": dict(by_status),
        "vehicles_needing_battery_replacement_soon": len(battery_urgent),
        "most_common_problems": problems.most_common(5),
        "vehicles_with_battery_warning_or_critical_by_brand": by_brand,
        "vehicles_with_battery_warning_or_critical_by_climate_zone": by_zone,
        "note": "Battery life values are predictions from a model trained on simulated data.",
    }


def summarize_fleet(results):
    if not results:
        return None
    return ask(FLEET_SYSTEM, fleet_facts(results), max_tokens=400)
