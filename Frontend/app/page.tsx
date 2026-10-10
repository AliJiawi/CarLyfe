"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { UploadPanel } from "@/components/UploadPanel";
import { FleetSummary } from "@/components/FleetSummary";
import { FleetTable, TableSkeleton } from "@/components/FleetTable";
import { CarDetail } from "@/components/CarDetail";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LIVE_TIMEOUT_MS, UserFileError, analyzeFile, fetchSummary, loadFallback } from "@/lib/api";
import type { FleetResult } from "@/lib/types";

type Phase = { kind: "idle" } | { kind: "loading"; since: number } | { kind: "error"; message: string };

export default function Home() {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [result, setResult] = useState<FleetResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const loading = phase.kind === "loading";

  useEffect(() => {
    if (phase.kind !== "loading") return;
    const since = phase.since;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - since) / 1000)), 500);
    return () => clearInterval(t);
  }, [phase]);

  const showFallback = useCallback(async (reason: string) => {
    try {
      setResult(await loadFallback(reason));
      setPhase({ kind: "idle" });
    } catch (e) {
      setPhase({ kind: "error", message: e instanceof Error ? e.message : "Could not load demo data." });
    }
  }, []);

  const useDemo = useCallback(() => {
    abortRef.current?.abort();
    setSelectedId(null);
    void showFallback("You chose the demo data.");
  }, [showFallback]);

  const analyze = useCallback(
    async (file: File) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        ctrl.abort();
      }, LIVE_TIMEOUT_MS);

      setSelectedId(null);
      setElapsed(0);
      setPhase({ kind: "loading", since: Date.now() });
      try {
        const live = await analyzeFile(file, ctrl.signal);
        clearTimeout(timer);
        setResult(live);
        setPhase({ kind: "idle" });
        // The fleet briefing is a nice-to-have; fill it in when it arrives.
        void fetchSummary(live.vehicles, ctrl.signal).then((summary) => {
          if (summary && !ctrl.signal.aborted) setResult((r) => (r && r.source === "live" ? { ...r, summary } : r));
        });
      } catch (e) {
        clearTimeout(timer);
        if (ctrl.signal.aborted && !timedOut) return; // superseded by the user (e.g. "Use demo data")
        if (e instanceof UserFileError) {
          setResult(null);
          setPhase({ kind: "error", message: e.message });
          return;
        }
        await showFallback(timedOut ? "The live server took too long to respond." : "The live server could not be reached.");
      }
    },
    [showFallback],
  );

  const selected = result?.vehicles.find((v) => v.vehicle_id === selectedId) ?? null;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <ThemeToggle />
          <span className="wordmark">
            <span className="sr-only">CarLyfe</span>
            <span aria-hidden="true">
              {"CarLyfe".split("").map((ch, i) => (
                <span key={i} className="wm-letter" style={{ "--i": i } as React.CSSProperties}>
                  {ch}
                </span>
              ))}
            </span>
          </span>
          <span className="topbar-sub">Made to maintain your car</span>
        </div>
        {loading && <div className="progress" role="presentation" />}
      </header>

      <main className="page">
        <UploadPanel
          busy={loading}
          elapsed={elapsed}
          source={result?.source ?? null}
          count={result?.vehicles.length ?? 0}
          onAnalyze={analyze}
          onDemo={useDemo}
        />

        {phase.kind === "error" && (
          <div className="strip strip-error" role="alert">
            <span className="dot dot-critical" aria-hidden="true" />
            <span>Upload failed: {phase.message}</span>
          </div>
        )}

        {!loading && result?.source === "fallback" && (
          <div className="strip" role="status">
            <span className="tag">Demo data</span>
            <span>
              {result.reason ?? "Live results are unavailable."} Showing {result.vehicles.length} sample vehicles, not your upload.
            </span>
          </div>
        )}

        {loading && <TableSkeleton />}

        {!loading && result && (
          <>
            <FleetSummary vehicles={result.vehicles} summary={result.summary} />
            <FleetTable vehicles={result.vehicles} selectedId={selectedId} onSelect={setSelectedId} />
          </>
        )}

        {!loading && !result && phase.kind === "idle" && (
          <p className="muted empty-note">No fleet loaded. Upload a file or use the demo data to see vehicles ranked by health score.</p>
        )}
      </main>

      {selected && <CarDetail vehicle={selected} onClose={() => setSelectedId(null)} />}
    </>
  );
}
