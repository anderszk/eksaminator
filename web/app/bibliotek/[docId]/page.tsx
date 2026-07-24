"use client";

import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import ReactMarkdown from "react-markdown";

type Section = "ryggstad" | "kapitler" | "begreper" | "paastander" | "svakheter";

interface ThesisMap { tittel?: string; problemstilling?: string; usikkert?: string[]; [key: string]: unknown }
interface Summary { id: string; scope: string; ref: string; title: string; body_md: string }
interface Claim { id: string; text: string; claim_type: string; strength: number }
interface Vulnerability { id: string; checklist_key: string; description: string; severity: number; attack_angle: string; best_defence?: string }

export default function BibliotekPage({ params }: { params: Promise<{ docId: string }> }) {
  const { docId } = use(params);

  const [section, setSection] = useState<Section>("ryggstad");
  const [map, setMap] = useState<ThesisMap | null>(null);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [loading, setLoading] = useState(true);
  const [openVuln, setOpenVuln] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [mapData, summaryData, claimData, vulnData] = await Promise.all([
          api.documents.get(docId) as any,  // includes map via /map endpoint
          (api as any).content?.summaries?.(docId) ?? fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/documents/${docId}/summaries`).then(r => r.json()),
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/documents/${docId}/claims`).then(r => r.json()),
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/documents/${docId}/vulnerabilities`).then(r => r.json()),
        ]);

        const mapRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/documents/${docId}/map`).then(r => r.json()).catch(() => null);
        setMap(mapRes?.data ?? null);
        setSummaries(Array.isArray(summaryData) ? summaryData : summaryData?.summaries ?? []);
        setClaims(Array.isArray(claimData) ? claimData : claimData?.claims ?? []);
        setVulnerabilities(Array.isArray(vulnData) ? vulnData : vulnData?.vulnerabilities ?? []);
      } catch {/* data may not be ready yet */}
      setLoading(false);
    })();
  }, [docId]);

  const spine = summaries.find(s => s.scope === "spine" || s.ref === "spine");
  const chapters = summaries.filter(s => s.scope === "chapter");
  const concepts = summaries.filter(s => s.scope === "concept");
  const figures = summaries.filter(s => s.scope === "figure");

  const NAV: { id: Section; label: string; count?: number }[] = [
    { id: "ryggstad", label: "Ryggraden" },
    { id: "kapitler", label: "Kapitler", count: chapters.length },
    { id: "begreper", label: "Begreper og metoder", count: concepts.length },
    { id: "paastander", label: "Påstander", count: claims.length },
    { id: "svakheter", label: "Svakheter", count: vulnerabilities.length },
  ];

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 56px)" }}>
      {/* Sidebar */}
      <aside style={{
        width: 220,
        borderRight: "1px solid var(--border)",
        padding: "24px 12px",
        flexShrink: 0,
        position: "sticky",
        top: 56,
        height: "calc(100vh - 56px)",
        overflowY: "auto",
      }}>
        {map?.tittel && (
          <div style={{ padding: "0 8px 16px", borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--ink-faint)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Oppgave</div>
            <div style={{ fontWeight: 600, fontSize: 13, lineHeight: 1.4 }}>{map.tittel}</div>
          </div>
        )}

        {NAV.map(n => (
          <button
            key={n.id}
            className={`sidebar-link ${section === n.id ? "active" : ""}`}
            onClick={() => setSection(n.id)}
          >
            <span style={{ flex: 1 }}>{n.label}</span>
            {n.count !== undefined && n.count > 0 && (
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)" }}>{n.count}</span>
            )}
          </button>
        ))}

        <div style={{ marginTop: 20, padding: "0 8px" }}>
          <a
            href={`/trening/new?docId=${docId}`}
            style={{
              display: "block",
              padding: "9px 12px",
              background: "var(--ink)",
              color: "#fff",
              borderRadius: "var(--radius)",
              textDecoration: "none",
              fontSize: 13,
              fontWeight: 500,
              textAlign: "center",
            }}
          >
            Start trening
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, padding: "28px 36px", maxWidth: 800, minWidth: 0 }}>
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "64px 0" }}>
            <div className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        )}

        {!loading && (
          <>
            {/* Uncertainties banner */}
            {map?.usikkert && (map.usikkert as string[]).length > 0 && (
              <div style={{ marginBottom: 24, padding: "12px 16px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "var(--radius)", fontSize: 13 }}>
                <strong style={{ color: "#92400e" }}>Gjennomgå:</strong>
                <ul style={{ margin: "6px 0 0 16px" }}>
                  {(map.usikkert as string[]).map((u, i) => <li key={i} style={{ color: "#78350f" }}>{u}</li>)}
                </ul>
              </div>
            )}

            {/* Ryggraden */}
            {section === "ryggstad" && (
              <div>
                <h2 style={{ marginBottom: 20 }}>Ryggraden</h2>
                {spine ? (
                  <div className="card" style={{ padding: "24px 28px" }}>
                    <div className="prose">
                      <ReactMarkdown>{spine.body_md}</ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <Empty>Ryggraden genereres som del av analysepipelinen.</Empty>
                )}
              </div>
            )}

            {/* Kapitler */}
            {section === "kapitler" && (
              <div>
                <h2 style={{ marginBottom: 20 }}>Kapitler</h2>
                {chapters.length === 0 ? <Empty>Ingen kapittelssammendrag ennå.</Empty> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {chapters.map(c => (
                      <SummaryCard key={c.id} summary={c} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Begreper */}
            {section === "begreper" && (
              <div>
                <h2 style={{ marginBottom: 20 }}>Begreper og metoder</h2>
                {concepts.length === 0 ? <Empty>Ingen begrepsammendrag ennå.</Empty> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {concepts.map(c => (
                      <SummaryCard key={c.id} summary={c} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Påstander */}
            {section === "paastander" && (
              <div>
                <h2 style={{ marginBottom: 4 }}>Påstander</h2>
                <p style={{ fontSize: 13, color: "var(--ink-muted)", marginBottom: 20 }}>
                  Lav styrke (1–2) = examinator vil angripe her.
                </p>
                {claims.length === 0 ? <Empty>Ingen påstander ennå.</Empty> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {claims.sort((a, b) => a.strength - b.strength).map(c => (
                      <ClaimCard key={c.id} claim={c} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Svakheter */}
            {section === "svakheter" && (
              <div>
                <h2 style={{ marginBottom: 4 }}>Svakheter</h2>
                <p style={{ fontSize: 13, color: "var(--ink-muted)", marginBottom: 20 }}>
                  Sortert etter alvorlighetsgrad. Øv deg på angrepsvinkelen.
                </p>
                {vulnerabilities.length === 0 ? <Empty>Ingen svakheter ennå.</Empty> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {vulnerabilities.sort((a, b) => b.severity - a.severity).map(v => (
                      <VulnCard
                        key={v.id}
                        vuln={v}
                        docId={docId}
                        open={openVuln === v.id}
                        onToggle={() => setOpenVuln(openVuln === v.id ? null : v.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function SummaryCard({ summary }: { summary: Summary }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{ width: "100%", padding: "16px 20px", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between", textAlign: "left" }}
      >
        <div style={{ fontWeight: 600, fontSize: 14 }}>{summary.title}</div>
        <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="var(--ink-faint)" strokeWidth="2" strokeLinecap="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s", flexShrink: 0 }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <div className="fade-up" style={{ padding: "0 20px 18px", borderTop: "1px solid var(--border)" }}>
          <div className="prose" style={{ marginTop: 14, fontSize: 14 }}>
            <ReactMarkdown>{summary.body_md}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function ClaimCard({ claim }: { claim: Claim }) {
  const typeColors: Record<string, string> = {
    empirisk:  "#dbeafe",
    metodisk:  "#dcfce7",
    tolkning:  "#fef9c3",
    teoretisk: "#f3e8ff",
  };
  return (
    <div className="card" style={{ padding: "14px 16px", display: "flex", alignItems: "flex-start", gap: 12 }}>
      <StrengthDot strength={claim.strength} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, lineHeight: 1.5 }}>{claim.text}</div>
        <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
          <span className="pill" style={{ fontSize: 11, background: typeColors[claim.claim_type] ?? "var(--bg-elevated)" }}>
            {claim.claim_type}
          </span>
        </div>
      </div>
    </div>
  );
}

function StrengthDot({ strength }: { strength: number }) {
  const colors = ["", "#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"];
  return (
    <div style={{
      width: 28,
      height: 28,
      borderRadius: "50%",
      background: `${colors[strength]}20`,
      border: `2px solid ${colors[strength]}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 11,
      fontWeight: 700,
      color: colors[strength],
      flexShrink: 0,
    }}>
      {strength}
    </div>
  );
}

function VulnCard({ vuln, docId, open, onToggle }: { vuln: Vulnerability; docId: string; open: boolean; onToggle: () => void }) {
  const sevBg = ["", "#f0fdf4", "#fefce8", "#fff7ed", "#fef2f2", "#fef2f2"];
  const sevColor = ["", "#15803d", "#a16207", "#c2410c", "#b91c1c", "#7f1d1d"];
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden", background: sevBg[vuln.severity] ?? "var(--bg-card)" }}>
      <button
        onClick={onToggle}
        style={{ width: "100%", padding: "16px 18px", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 12, textAlign: "left" }}
      >
        <div style={{
          width: 26, height: 26, borderRadius: "50%",
          background: `${sevColor[vuln.severity]}20`,
          border: `2px solid ${sevColor[vuln.severity]}50`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 700, color: sevColor[vuln.severity],
          flexShrink: 0,
        }}>
          {vuln.severity}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{vuln.checklist_key.replace(/_/g, " ")}</div>
          <div style={{ fontSize: 13, color: "var(--ink-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: open ? "normal" : "nowrap" }}>
            {vuln.description}
          </div>
        </div>
        <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="var(--ink-faint)" strokeWidth="2" strokeLinecap="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s", flexShrink: 0 }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="fade-up" style={{ padding: "0 18px 16px", borderTop: "1px solid var(--border)" }}>
          <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--ink-faint)", marginBottom: 6 }}>Angrepsvinkel</div>
              <blockquote style={{
                margin: 0,
                padding: "12px 14px",
                background: "rgba(255,255,255,0.6)",
                borderLeft: "3px solid var(--border-strong)",
                borderRadius: "var(--radius)",
                fontSize: 14,
                fontFamily: "var(--font-serif, Georgia, serif)",
                fontStyle: "italic",
              }}>
                {vuln.attack_angle}
              </blockquote>
            </div>
            {vuln.best_defence && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--ink-faint)", marginBottom: 6 }}>Beste forsvar</div>
                <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--ink-muted)" }}>{vuln.best_defence}</div>
              </div>
            )}
            <a
              href={`/trening/new?docId=${docId}&vuln=${vuln.id}`}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "7px 14px",
                background: "var(--ink)", color: "#fff",
                borderRadius: "var(--radius)", textDecoration: "none",
                fontSize: 13, fontWeight: 500,
                alignSelf: "flex-start",
              }}
            >
              Øv på denne
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--ink-faint)", fontSize: 14 }}>
      {children}
    </div>
  );
}
