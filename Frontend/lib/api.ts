import type { FleetResult, Vehicle } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "https://carlyfe.onrender.com").replace(/\/$/, "");

// The free Render instance can take ~60 s to wake, plus time for the AI notes.
export const LIVE_TIMEOUT_MS = 90_000;

/** An error the user caused (bad file etc.); showing demo data silently would be misleading. */
export class UserFileError extends Error {}

function isFleet(data: unknown): data is Vehicle[] {
  return (
    Array.isArray(data) &&
    data.every((v) => v && typeof v === "object" && "vehicle_id" in v && "overall_health_score" in v && "components" in v)
  );
}

export async function loadFallback(reason: string): Promise<FleetResult> {
  const [fleetRes, summaryRes] = await Promise.all([
    fetch("/static_fallback.json"),
    fetch("/static_fleet_summary.json").catch(() => null),
  ]);
  if (!fleetRes.ok) throw new Error("Could not load the built-in demo data.");
  const vehicles = (await fleetRes.json()) as Vehicle[];
  let summary: string | null = null;
  try {
    summary = summaryRes && summaryRes.ok ? ((await summaryRes.json()).summary ?? null) : null;
  } catch {
    summary = null;
  }
  return { vehicles, source: "fallback", reason, summary };
}

export async function analyzeFile(file: File, signal: AbortSignal): Promise<FleetResult> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_URL}/analyze?ai=true`, { method: "POST", body, signal });

  if (!res.ok) {
    let detail = `The server responded with ${res.status}.`;
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail;
    } catch {
      /* keep default */
    }
    if (res.status >= 400 && res.status < 500) throw new UserFileError(detail);
    throw new Error(detail);
  }

  const data: unknown = await res.json();
  if (!isFleet(data)) throw new Error("The server returned an unexpected response.");
  return { vehicles: data, source: "live", summary: null };
}

/** Best-effort fleet briefing; never throws. */
export async function fetchSummary(vehicles: Vehicle[], signal: AbortSignal): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(vehicles),
      signal,
    });
    if (!res.ok) return null;
    const j = await res.json();
    return typeof j?.summary === "string" ? j.summary : null;
  } catch {
    return null;
  }
}
