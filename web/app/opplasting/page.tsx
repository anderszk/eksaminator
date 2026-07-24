"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { nb } from "@/lib/nb";

type RunStatus = "pending" | "running" | "done" | "failed";
interface StageInfo { status: RunStatus; cost_usd?: number; duration_ms?: number }

const STAGE_LABELS: Record<string, string> = {
  ingest:          "Leser og deler opp tekst",
  structure:       "Bygger strukturkart",
  claims:          "Identifiserer påstander",
  vulnerabilities: "Analyserer svakheter",
  questions:       "Genererer spørsmål",
  answers:         "Skriver eksempelsvar",
  summaries:       "Lager studiesammendrag",
};
const STAGE_ORDER = Object.keys(STAGE_LABELS);

export default function OpplastingPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [phase, setPhase] = useState<"idle" | "uploading" | "analysing" | "done" | "error">("idle");
  const [docId, setDocId] = useState<string | null>(null);
  const [stages, setStages] = useState<Record<string, StageInfo>>({});
  const [totalCost, setTotalCost] = useState(0);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const stopPoll = () => { if (pollRef.current) clearInterval(pollRef.current); };

  useEffect(() => () => stopPoll(), []);

  const handleFiles = useCallback((files: FileList | null) => {
    const f = files?.[0];
    if (!f) return;
    if (f.type !== "application/pdf") { setError(nb.errors.upload); return; }
    if (f.size > 50 * 1024 * 1024) { setError(nb.errors.upload); return; }
    setError("");
    setFile(f);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const startUpload = async () => {
    if (!file) return;
    setPhase("uploading");
    setError("");
    try {
      const res = await api.documents.upload(file) as any;
      setDocId(res.id);

      if (res.existing) {
        // Already fully analysed — go straight to library
        router.push(`/bibliotek/${res.id}`);
        return;
      }

      // Trigger all pipeline stages
      await api.pipeline.run(res.id);
      setPhase("analysing");

      pollRef.current = setInterval(async () => {
        try {
          const status = await api.pipeline.status(res.id) as any;
          setStages(status.stages ?? {});
          setTotalCost(status.total_cost_usd ?? 0);

          const vals: StageInfo[] = Object.values(status.stages ?? {});
          const done = vals.every(s => s.status === "done");
          const failed = vals.some(s => s.status === "failed");

          if (done) {
            stopPoll();
            setPhase("done");
            setTimeout(() => router.push(`/bibliotek/${res.id}`), 1200);
          } else if (failed) {
            stopPoll();
            setPhase("error");
            setError("En analysesteg feilet. Sjekk logger.");
          }
        } catch {/* poll errors are transient */}
      }, 2000);

    } catch {
      setPhase("error");
      setError(nb.errors.upload);
    }
  };

  const stageDone = (s: string) => stages[s]?.status === "done";
  const stageRunning = (s: string) => stages[s]?.status === "running";
  const stageFailed = (s: string) => stages[s]?.status === "failed";
  const stageActive = (s: string) => stageDone(s) || stageRunning(s) || stageFailed(s);

  return (
    <main className="page" style={{ maxWidth: 600 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ marginBottom: 6 }}>{nb.upload.title}</h1>
        <p style={{ color: "var(--ink-muted)", fontSize: 14 }}>
          Analysen gjøres én gang og caches. Tar 2–4 minutter.
        </p>
      </div>

      {/* Drop zone */}
      {phase === "idle" && (
        <>
          <div
            className={`drop-zone ${isDragging ? "dragging" : ""}`}
            style={{ padding: "56px 32px", textAlign: "center" }}
            onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              style={{ display: "none" }}
              onChange={e => handleFiles(e.target.files)}
            />
            <div style={{ marginBottom: 16 }}>
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--border-strong)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto" }}>
                <rect x="8" y="4" width="32" height="40" rx="3" />
                <path d="M16 16h16M16 22h16M16 28h10" />
                <path d="M32 34l4-4 4 4" />
                <path d="M36 30v8" />
              </svg>
            </div>

            {file ? (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{file.name}</div>
                <div style={{ color: "var(--ink-muted)", fontSize: 13 }}>
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>{nb.upload.drop}</div>
                <div style={{ color: "var(--ink-muted)", fontSize: 13 }}>PDF, maks 50 MB</div>
              </div>
            )}
          </div>

          {error && (
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#fee2e2", borderRadius: "var(--radius)", color: "#991b1b", fontSize: 13 }}>
              {error}
            </div>
          )}

          {file && (
            <button
              className="btn btn-primary btn-lg"
              style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
              onClick={startUpload}
            >
              Last opp og analyser
            </button>
          )}
        </>
      )}

      {/* Upload progress spinner */}
      {phase === "uploading" && (
        <div style={{ textAlign: "center", padding: "48px 0" }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px", borderWidth: 3 }} />
          <div style={{ color: "var(--ink-muted)" }}>Laster opp…</div>
        </div>
      )}

      {/* Pipeline progress */}
      {(phase === "analysing" || phase === "done" || phase === "error") && (
        <div>
          <div style={{ marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <p style={{ fontSize: 14, color: "var(--ink-muted)" }}>{nb.upload.analysing}</p>
            {totalCost > 0 && (
              <span className="mono" style={{ fontSize: 12, color: "var(--ink-faint)" }}>
                ${totalCost.toFixed(3)}
              </span>
            )}
          </div>

          <div className="card" style={{ padding: "4px 20px" }}>
            {STAGE_ORDER.map((s, i) => {
              const done = stageDone(s);
              const running = stageRunning(s);
              const failed = stageFailed(s);
              const pending = !stageActive(s);
              return (
                <div key={s} className="stage-row" style={{ opacity: pending ? 0.45 : 1, transition: "opacity 0.3s" }}>
                  <div className={`stage-dot ${done ? "stage-dot-done" : running ? "stage-dot-running" : failed ? "stage-dot-failed" : "stage-dot-pending"}`}>
                    {done && <CheckIcon />}
                    {running && <span style={{ fontSize: 10, color: "var(--accent)", fontWeight: 700 }}>●</span>}
                    {failed && <span style={{ fontSize: 13 }}>✕</span>}
                    {pending && <span className="mono" style={{ fontSize: 10, color: "var(--ink-faint)", fontWeight: 600 }}>{i + 1}</span>}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{STAGE_LABELS[s]}</div>
                    {stages[s]?.duration_ms && (
                      <div className="mono" style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 1 }}>
                        {(stages[s].duration_ms! / 1000).toFixed(1)}s
                        {stages[s].cost_usd ? ` · $${stages[s].cost_usd!.toFixed(3)}` : ""}
                      </div>
                    )}
                  </div>
                  {running && (
                    <div className="spinner" />
                  )}
                </div>
              );
            })}
          </div>

          {phase === "done" && (
            <div className="fade-up" style={{
              marginTop: 20,
              padding: "14px 18px",
              background: "#dcfce7",
              border: "1px solid #bbf7d0",
              borderRadius: "var(--radius)",
              color: "#14532d",
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 14,
              fontWeight: 500,
            }}>
              <CheckIcon color="#15803d" />
              Analyse ferdig. Tar deg til biblioteket…
            </div>
          )}

          {phase === "error" && error && (
            <div style={{ marginTop: 16, padding: "12px 16px", background: "#fee2e2", borderRadius: "var(--radius)", color: "#991b1b", fontSize: 14 }}>
              {error}
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function CheckIcon({ color = "currentColor", size = 14 }: { color?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,7 6,11 12,3" />
    </svg>
  );
}
