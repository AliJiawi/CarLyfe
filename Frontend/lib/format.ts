import type { Status } from "./types";

export const STATUS_LABEL: Record<Status, string> = {
  ok: "OK",
  warning: "Warning",
  critical: "Critical",
  unknown: "No data",
};

export const STATUS_ICON: Record<Status, string> = {
  ok: "✓",
  warning: "!",
  critical: "✕",
  unknown: "?",
};

export const fmtKm = (n: number) => `${n.toLocaleString("en-US")} km`;
export const fmtCost = (n: number) => `RM${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
export const fmtMonths = (n: number) => (n <= 0 ? "0 mo" : `${Math.round(n * 10) / 10} mo`);
export const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
