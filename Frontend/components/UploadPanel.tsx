"use client";

import { useRef, useState } from "react";

interface Props {
  busy: boolean;
  elapsed: number;
  /** null until something has been shown */
  source: "live" | "fallback" | null;
  count: number;
  onAnalyze: (file: File) => void;
  onDemo: () => void;
}

const ACCEPT = ".csv,.xlsx,.xls,.json";

export function UploadPanel({ busy, elapsed, source, count, onAnalyze, onDemo }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const start = (f: File | undefined | null) => {
    if (!f) return;
    setFileName(f.name);
    onAnalyze(f);
  };

  const input = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPT}
      className="sr-only"
      tabIndex={-1}
      aria-label="Fleet file"
      onChange={(e) => {
        start(e.target.files?.[0]);
        e.target.value = ""; // allow re-selecting the same file
      }}
    />
  );
  const openPicker = () => inputRef.current?.click();

  // Slim bar once there is a result (or an analysis running)
  if (busy || source) {
    const label = busy
      ? `Analyzing ${fileName ?? "file"}`
      : source === "fallback"
        ? "Demo data"
        : (fileName ?? "Uploaded file");
    return (
      <section className="bar" aria-label="Data source">
        {input}
        <div className="bar-main">
          <span className="bar-file">{label}</span>
          <span className="muted">
            {busy
              ? `${elapsed} s${elapsed >= 8 ? " · free server may be waking up, up to 60 s" : ""}`
              : `${count} vehicles`}
          </span>
        </div>
        <div className="bar-actions">
          <button className="btn" onClick={openPicker}>
            Replace file
          </button>
          <button className="btn ghost" onClick={onDemo}>
            Use demo data
          </button>
        </div>
      </section>
    );
  }

  return (
    <section
      className={`drop${dragging ? " dragging" : ""}`}
      aria-label="Upload fleet file"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        start(e.dataTransfer.files?.[0]);
      }}
    >
      {input}
      <div className="drop-text">
        <strong>Upload a fleet file</strong>
        <span className="muted">CSV, Excel or JSON. Drop it here or choose a file.</span>
        <span className="muted">
          Samples:{" "}
          <a href="/samples/demo_zephyr.csv" download>
            Zephyr CSV
          </a>
          ,{" "}
          <a href="/samples/demo_kinto.xlsx" download>
            Kinto XLSX
          </a>
          ,{" "}
          <a href="/samples/demo_marlin.json" download>
            Marlin JSON
          </a>
        </span>
      </div>
      <div className="bar-actions">
        <button className="btn primary" onClick={openPicker}>
          Choose file
        </button>
        <button className="btn" onClick={onDemo}>
          Use demo data
        </button>
      </div>
    </section>
  );
}
