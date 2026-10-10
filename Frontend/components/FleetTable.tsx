"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Vehicle } from "@/lib/types";
import { fmtCost, titleCase } from "@/lib/format";
import { daysToRisk, diagnosis, fmtDays, issueCount, shortAction } from "@/lib/present";
import { StatusBadge } from "./StatusBadge";

type SortKey = "overall_health_score" | "vehicle_id" | "days" | "projected_cost_at_risk_usd";
type Dir = "asc" | "desc";

const COLUMNS: { key: SortKey | null; label: string; numeric?: boolean; className?: string }[] = [
  { key: "vehicle_id", label: "Vehicle" },
  { key: "overall_health_score", label: "Status" },
  { key: "days", label: "Days to risk", numeric: true },
  { key: null, label: "Diagnosis", className: "col-diagnosis" },
  { key: null, label: "Recommended action", className: "col-action" },
  { key: "projected_cost_at_risk_usd", label: "Cost at risk", numeric: true },
];

function sortValue(v: Vehicle, key: SortKey): string | number {
  if (key === "days") return daysToRisk(v) ?? Number.MAX_SAFE_INTEGER; // no timeline sorts last
  return v[key];
}

interface Props {
  vehicles: Vehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function FleetTable({ vehicles, selectedId, onSelect }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("overall_health_score");
  const [dir, setDir] = useState<Dir>("asc"); // lowest score (worst) first
  const [status, setStatus] = useState<"all" | Vehicle["overall_status"]>("all");
  const [query, setQuery] = useState("");
  const bodyRef = useRef<HTMLTableSectionElement>(null);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = vehicles.filter(
      (v) =>
        (status === "all" || v.overall_status === status) &&
        (!q || `${v.vehicle_id} ${v.brand} ${v.model} ${v.climate_zone}`.toLowerCase().includes(q)),
    );
    const sign = dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const x = sortValue(a, sortKey);
      const y = sortValue(b, sortKey);
      const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
      // tie-break on score so equal rows stay worst-first
      return c !== 0 ? c * sign : a.overall_health_score - b.overall_health_score;
    });
  }, [vehicles, sortKey, dir, status, query]);

  // Re-sorting: rows drop in from the top, one after another, so the new order reads top to bottom.
  const sortedOnce = useRef(false);
  useLayoutEffect(() => {
    if (!sortedOnce.current) {
      sortedOnce.current = true; // skip the initial render; rows already have their entrance
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    bodyRef.current?.querySelectorAll<HTMLTableRowElement>("tr[data-id]").forEach((tr, i) => {
      tr.animate(
        [
          { opacity: 0, transform: "translateY(-14px)" },
          { opacity: 1, transform: "none" },
        ],
        { duration: 420, delay: Math.min(i, 16) * 30, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "backwards" },
      );
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortKey, dir]);

  const toggle = (key: SortKey) => {
    if (key === sortKey) setDir(dir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setDir("asc");
    }
  };

  return (
    <section aria-label="Vehicles">
      <div className="table-tools">
        <span className="muted">
          {rows.length === vehicles.length ? `${vehicles.length} vehicles` : `${rows.length} of ${vehicles.length} vehicles`}
        </span>
        <div className="tools-right">
          <input
            type="search"
            className="field"
            placeholder="Search vehicle, brand, climate"
            aria-label="Search vehicles"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="field"
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value as typeof status)}
          >
            <option value="all">All statuses</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="ok">OK</option>
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table className="fleet">
          <thead>
            <tr>
              <th scope="col" className="col-rank">
                #
              </th>
              {COLUMNS.map((c) => (
                <th
                  key={c.label}
                  scope="col"
                  className={[c.numeric ? "num" : "", c.className ?? ""].join(" ").trim() || undefined}
                  aria-sort={c.key && sortKey === c.key ? (dir === "asc" ? "ascending" : "descending") : undefined}
                >
                  {c.key ? (
                    <button className="sort" onClick={() => toggle(c.key as SortKey)}>
                      {c.label}
                      <span
                        className={`sort-mark${sortKey === c.key ? " active" : ""}${sortKey === c.key && dir === "desc" ? " desc" : ""}`}
                        aria-hidden="true"
                      >
                        ↑
                      </span>
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody ref={bodyRef}>
            {rows.map((v, i) => {
              const more = issueCount(v) - 1;
              return (
                <tr
                  key={v.vehicle_id}
                  data-id={v.vehicle_id}
                  style={{ "--i": i } as React.CSSProperties}
                  className={[v.overall_status === "critical" ? "is-critical" : "", v.vehicle_id === selectedId ? "selected" : ""]
                    .join(" ")
                    .trim() || undefined}
                  onClick={() => onSelect(v.vehicle_id)}
                >
                  <td className="col-rank">{i + 1}</td>
                  <td>
                    <button
                      className="row-link"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(v.vehicle_id);
                      }}
                    >
                      {v.vehicle_id}
                    </button>
                    <span className="sub">
                      {v.brand} {v.model} · {titleCase(v.climate_zone)}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={v.overall_status} />
                    <span className="score">{v.overall_health_score}</span>
                  </td>
                  <td className="num">{fmtDays(daysToRisk(v))}</td>
                  <td className="col-diagnosis" title={diagnosis(v)}>
                    <span className="clip">{diagnosis(v)}</span>
                    {more > 0 && <span className="more">+{more}</span>}
                  </td>
                  <td className="col-action">
                    <span className="clip">{shortAction(v)}</span>
                  </td>
                  <td className="num">{fmtCost(v.projected_cost_at_risk_usd)}</td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr className="no-hover">
                <td colSpan={7} className="empty">
                  No vehicles match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function TableSkeleton() {
  return (
    <section aria-label="Loading vehicles" aria-busy="true">
      <div className="table-tools">
        <span className="skel" style={{ width: 96, height: 14 }} />
      </div>
      <div className="table-wrap">
        <table className="fleet">
          <tbody>
            {Array.from({ length: 8 }, (_, i) => (
              <tr key={i} className="no-hover">
                <td className="col-rank">
                  <span className="skel" style={{ width: 14 }} />
                </td>
                <td>
                  <span className="skel" style={{ width: 96 }} />
                </td>
                <td>
                  <span className="skel" style={{ width: 72 }} />
                </td>
                <td className="num">
                  <span className="skel" style={{ width: 36 }} />
                </td>
                <td className="col-diagnosis">
                  <span className="skel" style={{ width: "70%" }} />
                </td>
                <td className="col-action">
                  <span className="skel" style={{ width: "55%" }} />
                </td>
                <td className="num">
                  <span className="skel" style={{ width: 48 }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
