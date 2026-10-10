import type { Component, Vehicle } from "./types";

// Display-only helpers: they reshape fields the API already returns into the short
// labels the table shows. Nothing here changes or re-scores the data.

const SEVERITY: Record<string, number> = { critical: 2, warning: 1 };

/** The component that most needs attention (critical first, then warning), or null if none. */
export function worstComponent(v: Vehicle): Component | null {
  let best: Component | null = null;
  for (const c of v.components) {
    const s = SEVERITY[c.status] ?? 0;
    if (s > 0 && (!best || s > SEVERITY[best.status])) best = c;
  }
  return best;
}

export function issueCount(v: Vehicle): number {
  return v.components.filter((c) => c.status === "critical" || c.status === "warning").length;
}

const isBattery = (c: Component) => c.name.toLowerCase().startsWith("battery");

/**
 * Days until the car is at risk, or null when no timing applies.
 * A critical fault outside the battery means the risk is already present (0).
 * A non-critical fault outside the battery has no timeline in the data (null).
 * Otherwise it is the battery's predicted remaining life.
 */
export function daysToRisk(v: Vehicle): number | null {
  if (v.components.some((c) => c.status === "critical" && !isBattery(c))) return 0;
  const worst = worstComponent(v);
  if (worst && !isBattery(worst)) return null;
  return Math.max(0, Math.round(v.battery_analytics.remaining_months * 30));
}

export function fmtDays(days: number | null): string {
  if (days === null) return "—";
  if (days <= 0) return "Now";
  if (days >= 365) return "365+ d";
  return `${days} d`;
}

export function diagnosis(v: Vehicle): string {
  const c = worstComponent(v);
  if (!c) return "No issues flagged";
  return c.metric_value && c.metric_value !== "N/A" ? `${c.name}: ${c.metric_value}` : c.name;
}

/** Short imperative label, e.g. "Replace battery within 9 d". */
export function shortAction(v: Vehicle): string {
  const c = worstComponent(v);
  if (!c) return "No action";
  const crit = c.status === "critical";
  const n = c.name.toLowerCase();

  if (n.startsWith("battery")) {
    const d = daysToRisk(v) ?? 0;
    if (crit) return d <= 0 ? "Replace battery now" : `Replace battery within ${d} d`;
    return "Load-test battery at next service";
  }
  if (n.startsWith("brak")) return crit ? "Replace brake pads now" : "Plan brake pad replacement";
  if (n.startsWith("tire")) return crit ? "Replace tires now" : "Plan tire replacement";
  if (n.startsWith("thermal")) return "Inspect cooling system";
  if (n.startsWith("fuel")) return "Inspect fuel mixture";
  if (n.startsWith("dtc")) return "Diagnose fault codes";
  return `Inspect ${n}`;
}
