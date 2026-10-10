"use client";

import { useEffect, useState } from "react";
import type { Vehicle } from "@/lib/types";
import { fmtCost } from "@/lib/format";

/** Counts up from 0 to `to` once on mount; shows the final value straight away for reduced motion. */
function CountUp({ to, format = String }: { to: number; format?: (n: number) => string }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(to);
      return;
    }
    const start = performance.now() + 150; // let the strip fade in first
    const duration = 800;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      setValue(to * (1 - Math.pow(1 - t, 3))); // ease-out cubic
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);

  return <>{format(Math.round(value))}</>;
}

export function FleetSummary({ vehicles, summary }: { vehicles: Vehicle[]; summary?: string | null }) {
  const count = (s: string) => vehicles.filter((v) => v.overall_status === s).length;
  const avg = vehicles.length ? Math.round(vehicles.reduce((a, v) => a + v.overall_health_score, 0) / vehicles.length) : 0;
  const cost = vehicles.reduce((a, v) => a + v.projected_cost_at_risk_usd, 0);

  const secondary: { label: string; value: number; format?: (n: number) => string }[] = [
    { label: "Warning", value: count("warning") },
    { label: "OK", value: count("ok") },
    { label: "Vehicles", value: vehicles.length },
    { label: "Avg. health", value: avg },
    { label: "Cost at risk", value: cost, format: fmtCost },
  ];

  return (
    <section className="summary" aria-label="Fleet summary">
      <dl className="strip-stats">
        <div className="primary">
          <dt>
            <span className="dot dot-critical" aria-hidden="true" /> Critical
          </dt>
          <dd>
            <CountUp to={count("critical")} />
          </dd>
        </div>
        {secondary.map((s) => (
          <div key={s.label}>
            <dt>{s.label}</dt>
            <dd>
              <CountUp to={s.value} format={s.format} />
            </dd>
          </div>
        ))}
      </dl>
      {summary && (
        <div className="briefing">
          <h2 className="micro">Fleet briefing</h2>
          <p>{summary}</p>
        </div>
      )}
    </section>
  );
}
