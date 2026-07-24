"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch(path: string) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

interface Document { id: string; filename: string; uploaded_at: string; page_count: number }
interface WeakestQ { id: string; text: string; category: string; difficulty: number; mean_score: number; attempts: number }
interface Coverage { chapter: string; category: string; mean_score: number | null; attempts: number }
interface Progress { date: string; mean_score: number; session_count: number }
interface PlanItem { id: string; day: number; title: string; minutes?: number; kind: string; done: boolean; linked_categories: string[] }

const CATEGORIES = ["motivasjon","metodevalg","metodeforstaelse","resultater","statistikk","validitet","alternativ","relevans","grunnlag","kritisk"];
const CAT_SHORT: Record<string, string> = {
  motivasjon:"Mot.",metodevalg:"Meto.",metodeforstaelse:"Forst.",resultater:"Res.",
  statistikk:"Stat.",validitet:"Val.",alternativ:"Alt.",relevans:"Rel.",grunnlag:"Grunn.",kritisk:"Krit.",
};
const KIND_COLORS: Record<string, string> = {
  lesing: "#dbeafe", analyse: "#f3e8ff", muntlig: "#dcfce7", mock: "#fef9c3", hvile: "#f1f5f9",
};

export default function OversiktPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const [weakest, setWeakest] = useState<WeakestQ[]>([]);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [progress, setProgress] = useState<Progress[]>([]);
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/documents").then((data: any) => {
      const list: Document[] = Array.isArray(data) ? data : data.documents ?? [];
      setDocs(list);
      if (list.length > 0) setActiveDoc(list[0].id);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!activeDoc) return;
    Promise.all([
      apiFetch(`/stats/weakest?document_id=${activeDoc}&limit=10`).catch(() => ({ questions: [] })),
      apiFetch(`/stats/coverage?document_id=${activeDoc}`).catch(() => ({ coverage: [] })),
      apiFetch(`/stats/progress?document_id=${activeDoc}`).catch(() => ({ progress: [] })),
      apiFetch(`/plan?document_id=${activeDoc}`).catch(() => ({ plan: [] })),
    ]).then(([w, cov, prog, pl]) => {
      setWeakest(w.questions ?? w ?? []);
      setCoverage(cov.coverage ?? cov ?? []);
      setProgress(prog.progress ?? prog ?? []);
      setPlan(pl.plan ?? pl ?? []);
    });
  }, [activeDoc]);

  const togglePlan = async (item: PlanItem) => {
    const newDone = !item.done;
    setPlan(p => p.map(i => i.id === item.id ? { ...i, done: newDone } : i));
    try { await fetch(`${API}/plan/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ done: newDone }) }); }
    catch { setPlan(p => p.map(i => i.id === item.id ? { ...i, done: item.done } : i)); }
  };

  if (loading) {
    return (
      <main className="page">
        <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
          <div className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      </main>
    );
  }

  if (docs.length === 0) {
    return (
      <main className="page" style={{ maxWidth: 560, textAlign: "center", paddingTop: 80 }}>
        <div style={{ fontSize: 40, marginBottom: 20 }}>📄</div>
        <h2 style={{ marginBottom: 8 }}>Ingen oppgave lastet opp</h2>
        <p style={{ color: "var(--ink-muted)", marginBottom: 28 }}>Last opp masteroppgaven din for å komme i gang.</p>
        <Link href="/opplasting" className="btn btn-primary btn-lg">Last opp oppgave</Link>
      </main>
    );
  }

  const chapters = [...new Set(coverage.map(c => c.chapter))].sort();
  const today = new Date().getDay(); // 0 = Sunday

  return (
    <main className="page-wide">
      {/* Doc selector */}
      {docs.length > 1 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          {docs.map(d => (
            <button
              key={d.id}
              className={`btn ${activeDoc === d.id ? "btn-primary" : "btn-secondary"} btn-sm`}
              onClick={() => setActiveDoc(d.id)}
            >
              {d.filename}
            </button>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>

        {/* Coverage heatmap */}
        <div className="card" style={{ padding: "20px 24px", gridColumn: "1 / -1" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <h3>Dekningskart</h3>
              <p style={{ color: "var(--ink-muted)", fontSize: 13, marginTop: 2 }}>Kapittel × kategori · grå = ikke forsøkt</p>
            </div>
            <HeatmapLegend />
          </div>

          {coverage.length === 0 ? (
            <div style={{ padding: "32px 0", textAlign: "center", color: "var(--ink-faint)", fontSize: 14 }}>
              Trenger minst ett besvart spørsmål per celle.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "separate", borderSpacing: 3, fontSize: 11 }}>
                <thead>
                  <tr>
                    <th style={{ width: 80, textAlign: "left", fontWeight: 500, color: "var(--ink-muted)", paddingBottom: 6, fontSize: 11 }}>Kapittel</th>
                    {CATEGORIES.map(cat => (
                      <th key={cat} style={{ width: 44, fontWeight: 500, color: "var(--ink-muted)", paddingBottom: 6, textAlign: "center" }}>
                        {CAT_SHORT[cat]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {chapters.map(ch => (
                    <tr key={ch}>
                      <td style={{ color: "var(--ink-muted)", fontSize: 11, paddingRight: 8, whiteSpace: "nowrap" }}>{ch}</td>
                      {CATEGORIES.map(cat => {
                        const cell = coverage.find(c => c.chapter === ch && c.category === cat);
                        const score = cell?.mean_score ?? null;
                        return (
                          <td key={cat} style={{ padding: 0 }}>
                            <HeatCell score={score} attempts={cell?.attempts ?? 0} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Weakest 10 */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <h3 style={{ marginBottom: 4 }}>Svakeste ti</h3>
          <p style={{ color: "var(--ink-muted)", fontSize: 13, marginBottom: 16 }}>Sortert etter laveste gjennomsnitt</p>
          {weakest.length === 0 ? (
            <p style={{ color: "var(--ink-faint)", fontSize: 14 }}>Ikke nok data ennå. Svar på minst ti spørsmål.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {weakest.map((q, i) => (
                <div key={q.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)", width: 16, flexShrink: 0 }}>{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{q.text}</div>
                    <div style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 1 }}>{q.category} · {q.attempts} svar</div>
                  </div>
                  <ScorePill score={q.mean_score} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Progress chart */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <h3 style={{ marginBottom: 4 }}>Utvikling</h3>
          <p style={{ color: "var(--ink-muted)", fontSize: 13, marginBottom: 16 }}>Gjennomsnittlig skår per dag</p>
          {progress.length < 2 ? (
            <p style={{ color: "var(--ink-faint)", fontSize: 14 }}>Svar på spørsmål over minst to dager for å se utvikling.</p>
          ) : (
            <ProgressChart data={progress} />
          )}
        </div>
      </div>

      {/* 14-day plan */}
      {plan.length > 0 && (
        <div className="card" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <h3>14-dagers plan</h3>
              <p style={{ color: "var(--ink-muted)", fontSize: 13, marginTop: 2 }}>
                {plan.filter(p => p.done).length}/{plan.length} fullført
              </p>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8 }}>
            {Array.from({ length: 14 }, (_, day) => {
              const items = plan.filter(p => p.day === day + 1);
              const allDone = items.length > 0 && items.every(p => p.done);
              return (
                <div key={day} style={{
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  overflow: "hidden",
                  opacity: items.length === 0 ? 0.4 : 1,
                }}>
                  <div style={{
                    padding: "6px 8px",
                    background: allDone ? "#dcfce7" : "var(--bg-elevated)",
                    borderBottom: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-muted)" }}>Dag {day + 1}</span>
                    {allDone && <span style={{ fontSize: 10, color: "#15803d" }}>✓</span>}
                  </div>
                  <div style={{ padding: "6px 8px" }}>
                    {items.map(item => (
                      <label key={item.id} style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 6,
                        cursor: "pointer",
                        fontSize: 11,
                        lineHeight: 1.4,
                        color: item.done ? "var(--ink-faint)" : "var(--ink)",
                        marginBottom: items.length > 1 ? 4 : 0,
                      }}>
                        <input
                          type="checkbox"
                          checked={item.done}
                          onChange={() => togglePlan(item)}
                          style={{ marginTop: 1, flexShrink: 0, accentColor: "var(--ink)" }}
                        />
                        <span style={{
                          textDecoration: item.done ? "line-through" : "none",
                          background: `${KIND_COLORS[item.kind] ?? "transparent"}`,
                          padding: "1px 3px",
                          borderRadius: 2,
                        }}>
                          {item.title}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick links */}
      <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
        <Link href={`/bibliotek/${activeDoc}`} className="btn btn-secondary">Åpne bibliotek</Link>
        <Link href={`/trening/new?docId=${activeDoc}`} className="btn btn-primary">Start trening</Link>
        <Link href={`/eksamen/new?docId=${activeDoc}`} className="btn btn-secondary">Start eksamen</Link>
      </div>
    </main>
  );
}

function HeatCell({ score, attempts }: { score: number | null; attempts: number }) {
  if (score === null || attempts === 0) {
    return <div className="heatmap-cell" style={{ background: "var(--bg-elevated)", width: 40, height: 40 }} />;
  }
  const pct = score / 4;
  const hue = pct * 120; // 0 (red) → 120 (green)
  const bg = `hsl(${hue}, 65%, 88%)`;
  const fg = `hsl(${hue}, 50%, 35%)`;
  return (
    <div
      className="heatmap-cell mono"
      style={{ background: bg, color: fg, width: 40, height: 40, fontSize: 10 }}
      title={`Snitt: ${score.toFixed(1)} · ${attempts} svar`}
    >
      {score.toFixed(1)}
    </div>
  );
}

function HeatmapLegend() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--ink-faint)" }}>
      <div style={{ width: 14, height: 14, background: "hsl(0,65%,88%)", borderRadius: 3 }} />
      <span>0</span>
      <div style={{ width: 40, height: 4, background: "linear-gradient(to right, hsl(0,65%,88%), hsl(60,65%,88%), hsl(120,65%,88%))", borderRadius: 2 }} />
      <span>4</span>
      <div style={{ width: 14, height: 14, background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 3, marginLeft: 4 }} />
      <span>Ikke forsøkt</span>
    </div>
  );
}

function ScorePill({ score }: { score: number }) {
  const color = score < 1.5 ? "#ef4444" : score < 2.5 ? "#eab308" : score < 3.5 ? "#84cc16" : "#22c55e";
  return (
    <span className="mono" style={{ fontSize: 12, fontWeight: 700, color, flexShrink: 0 }}>{score.toFixed(1)}</span>
  );
}

function ProgressChart({ data }: { data: Progress[] }) {
  const W = 340, H = 120, PAD = 12;
  const vals = data.map(d => d.mean_score);
  const min = 0, max = 4;
  const pts = vals.map((v, i) => ({
    x: PAD + (i / Math.max(vals.length - 1, 1)) * (W - PAD * 2),
    y: H - PAD - ((v - min) / (max - min)) * (H - PAD * 2),
  }));
  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${H} L${pts[0].x.toFixed(1)},${H} Z`;

  return (
    <svg width={W} height={H} style={{ overflow: "visible" }}>
      {/* Grid lines */}
      {[0,1,2,3,4].map(v => {
        const y = H - PAD - (v / 4) * (H - PAD * 2);
        return <line key={v} x1={PAD} y1={y} x2={W - PAD} y2={y} stroke="var(--border)" strokeWidth={0.5} />;
      })}
      {/* Area fill */}
      <path d={areaPath} fill="var(--accent)" fillOpacity={0.07} />
      {/* Line */}
      <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {/* Dots */}
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3.5} fill="var(--bg-card)" stroke="var(--accent)" strokeWidth={2}>
          <title>{data[i].date}: {vals[i].toFixed(2)}</title>
        </circle>
      ))}
      {/* Labels */}
      {[0, 2, 4].map(v => (
        <text key={v} x={PAD - 4} y={H - PAD - (v / 4) * (H - PAD * 2) + 4} fontSize={9} fill="var(--ink-faint)" textAnchor="end" fontFamily="var(--font-mono)">{v}</text>
      ))}
    </svg>
  );
}
