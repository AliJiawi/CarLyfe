"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Vehicle } from "@/lib/types";
import { fmtKm, fmtMonths, fmtCost, titleCase } from "@/lib/format";
import { daysToRisk, fmtDays, shortAction } from "@/lib/present";
import { StatusBadge } from "./StatusBadge";

export function CarDetail({ vehicle, onClose }: { vehicle: Vehicle; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [leaving, setLeaving] = useState(false);
  const leavingRef = useRef(false);
  const b = vehicle.battery_analytics;
  // ai_explanation is null when no AI note was generated; show the rule-based driver instead.
  const hasAi = Boolean(vehicle.ai_explanation);
  const reason = hasAi ? vehicle.ai_explanation : b.primary_driver;

  // Play the exit animation, then tell the parent to unmount.
  const close = useCallback(() => {
    if (leavingRef.current) return;
    leavingRef.current = true;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return onClose();
    setLeaving(true);
    window.setTimeout(onClose, 180);
  }, [onClose]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  return (
    <div className={`overlay${leaving ? " leaving" : ""}`} onClick={close}>
      <aside
        className="panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Details for ${vehicle.vehicle_id}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="panel-head">
          <div className="panel-title">
            <h2>{vehicle.vehicle_id}</h2>
            <p className="muted">
              {vehicle.brand} {vehicle.model} · {titleCase(vehicle.climate_zone)} · {fmtKm(vehicle.odometer_km)}
            </p>
          </div>
          <button ref={closeRef} className="btn" onClick={close}>
            Close
          </button>
        </header>

        <div className="panel-body">
          <dl className="facts">
            <div>
              <dt>Status</dt>
              <dd>
                <StatusBadge status={vehicle.overall_status} />
              </dd>
            </div>
            <div>
              <dt>Health score</dt>
              <dd>{vehicle.overall_health_score}</dd>
            </div>
            <div>
              <dt>Cost at risk</dt>
              <dd>{fmtCost(vehicle.projected_cost_at_risk_usd)}</dd>
            </div>
          </dl>

          <section>
            <h3 className="micro">Reason</h3>
            <p className="reason">{reason}</p>
            <p className="source">
              <span className={`tag${hasAi ? " tag-accent" : ""}`}>{hasAi ? "AI note" : "Rule-based"}</span>
            </p>
          </section>

          <section>
            <h3 className="micro">Forecast</h3>
            <dl className="rows">
              <div>
                <dt>Days to risk</dt>
                <dd>{fmtDays(daysToRisk(vehicle))}</dd>
              </div>
              <div>
                <dt>Battery life left</dt>
                <dd>{fmtMonths(b.remaining_months)}</dd>
              </div>
              <div>
                <dt>Battery health</dt>
                <dd>{b.health_pct}%</dd>
              </div>
              <div>
                <dt>Battery urgency</dt>
                <dd>{titleCase(b.urgency)}</dd>
              </div>
            </dl>
            <p className="note">Battery figures are a model prediction trained on simulated data.</p>
          </section>

          <section>
            <h3 className="micro">Options</h3>
            <ul className="options">
              <li>
                <strong>{shortAction(vehicle)}</strong>
              </li>
              <li className="muted">{b.prescriptive_action}</li>
            </ul>
          </section>

          <section>
            <h3 className="micro">Components</h3>
            <ul className="comps">
              {vehicle.components.map((c) => (
                <li key={c.name}>
                  <div className="comp-line">
                    <span className="comp-name">{c.name}</span>
                    <span className="comp-metric">{c.metric_value}</span>
                    <StatusBadge status={c.status} />
                  </div>
                  <p className="muted comp-reason">{c.reason}</p>
                </li>
              ))}
            </ul>
          </section>

          {(vehicle.missing_signals.length > 0 || vehicle.unmapped_signals.length > 0) && (
            <section>
              <h3 className="micro">Data notes</h3>
              {vehicle.missing_signals.length > 0 && <p className="muted">Not reported: {vehicle.missing_signals.join(", ")}</p>}
              {vehicle.unmapped_signals.length > 0 && <p className="muted">Ignored: {vehicle.unmapped_signals.join(", ")}</p>}
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}
