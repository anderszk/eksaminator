"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { nb } from "@/lib/nb";

interface Scores {
  korrekthet: number;
  begrunnelse: number;
  forbehold: number;
  struktur: number;
}

interface Props {
  scores?: Scores;
  feedbackMd?: string;
  bluffed?: boolean;
  usedShape?: string;
  missedPoints?: string[];
  modelAnswer?: string;
  whyAsked?: string;
  sourceRefs?: Array<{ page: number; section_path?: string }>;
  delivery?: {
    duration_ms?: number;
    wpm?: number;
    filler_count?: number;
    longest_pause_ms?: number;
  };
  onFollowUp?: () => void;
  onNext?: () => void;
  isStreaming?: boolean;
}

const SCORE_LABELS: Record<keyof Scores, string> = {
  korrekthet:  nb.scores.korrekthet,
  begrunnelse: nb.scores.begrunnelse,
  forbehold:   nb.scores.forbehold,
  struktur:    nb.scores.struktur,
};

const SHAPE_LABELS: Record<string, string> = {
  direkte:    "Direkte (påstand → belegg → forbehold)",
  utfordre:   "Utfordre premisset",
  innrommelse: "Innrømmelse",
  uklar:      "Uklar struktur",
};

export default function FeedbackPanel({
  scores, feedbackMd, bluffed, usedShape, missedPoints,
  modelAnswer, whyAsked, sourceRefs, delivery, onFollowUp, onNext, isStreaming,
}: Props) {
  const [showModel, setShowModel] = useState(false);
  const [showWhy, setShowWhy] = useState(false);

  if (!scores && isStreaming) {
    return (
      <div style={{ padding: "24px 0", display: "flex", alignItems: "center", gap: 10, color: "var(--ink-muted)", fontSize: 14 }}>
        <div className="spinner" />
        {nb.drill.grading}
      </div>
    );
  }

  if (!scores) return null;

  const mean = Object.values(scores).reduce((s, v) => s + v, 0) / 4;

  return (
    <div className="fade-up" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header: mean + shape */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <MeanBadge score={mean} />
        {usedShape && (
          <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>{SHAPE_LABELS[usedShape] ?? usedShape}</span>
        )}
        {bluffed && (
          <span className="badge badge-red">Bluffing</span>
        )}
      </div>

      {/* Score bars */}
      <div className="card" style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {(Object.keys(SCORE_LABELS) as (keyof Scores)[]).map(k => (
          <ScoreRow key={k} label={SCORE_LABELS[k]} value={scores[k]} />
        ))}
      </div>

      {/* Feedback text */}
      {feedbackMd && (
        <div style={{
          padding: "16px 18px",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          fontSize: 14,
          lineHeight: 1.7,
        }}>
          <div className="prose">
            <ReactMarkdown>{feedbackMd}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Missed points */}
      {missedPoints && missedPoints.length > 0 && (
        <div style={{ padding: "14px 18px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "var(--radius)", fontSize: 13 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: "#92400e", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Ikke dekket
          </div>
          <ul style={{ margin: 0, padding: "0 0 0 16px", display: "flex", flexDirection: "column", gap: 4 }}>
            {missedPoints.map((p, i) => (
              <li key={i} style={{ color: "#78350f" }}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Delivery strip */}
      {delivery && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 1,
          background: "var(--border)",
          borderRadius: "var(--radius)",
          overflow: "hidden",
        }}>
          <MetricCell label={nb.delivery.duration} value={delivery.duration_ms ? `${(delivery.duration_ms / 1000).toFixed(0)}s` : "–"} highlight={delivery.duration_ms ? delivery.duration_ms / 1000 < 30 || delivery.duration_ms / 1000 > 105 : false} />
          <MetricCell label={nb.delivery.wpm} value={delivery.wpm ? `${Math.round(delivery.wpm)}` : "–"} highlight={delivery.wpm ? delivery.wpm < 110 || delivery.wpm > 180 : false} />
          <MetricCell label={nb.delivery.fillers} value={delivery.filler_count !== undefined ? String(delivery.filler_count) : "–"} highlight={(delivery.filler_count ?? 0) > 5} />
          <MetricCell label={nb.delivery.pause} value={delivery.longest_pause_ms ? `${(delivery.longest_pause_ms / 1000).toFixed(1)}s` : "–"} highlight={false} />
        </div>
      )}

      {/* Model answer (collapsible) */}
      {modelAnswer && (
        <div className="card" style={{ padding: "0 0" }}>
          <button
            className="collapsible-trigger"
            style={{ padding: "14px 18px", fontSize: 14 }}
            onClick={() => setShowModel(v => !v)}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <BookIcon />
              {nb.drill.model_answer}
            </span>
            <ChevronIcon open={showModel} />
          </button>
          {showModel && (
            <div className="fade-up" style={{ padding: "0 18px 16px", borderTop: "1px solid var(--border)" }}>
              <blockquote style={{
                margin: "12px 0 0",
                padding: "14px 16px",
                background: "var(--bg-elevated)",
                borderRadius: "var(--radius)",
                fontFamily: "var(--font-serif, Georgia, serif)",
                fontSize: 14,
                lineHeight: 1.7,
                fontStyle: "italic",
              }}>
                {modelAnswer}
              </blockquote>
            </div>
          )}
        </div>
      )}

      {/* Source refs */}
      {sourceRefs && sourceRefs.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {sourceRefs.map((r, i) => (
            <span key={i} className="pill" style={{ fontSize: 11 }}>
              s. {r.page}{r.section_path ? ` · ${r.section_path.split(">").pop()?.trim()}` : ""}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
        {onFollowUp && (
          <button className="btn btn-secondary" onClick={onFollowUp} style={{ flex: 1, justifyContent: "center" }}>
            <FollowUpIcon />
            {nb.drill.follow_up}
          </button>
        )}
        {onNext && (
          <button className="btn btn-primary" onClick={onNext} style={{ flex: 1, justifyContent: "center" }}>
            {nb.drill.next}
            <ArrowIcon />
          </button>
        )}
      </div>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  const pct = (value / 4) * 100;
  const color = value < 1.5 ? "var(--score-0)" : value < 2.5 ? "var(--score-2)" : value < 3.5 ? "var(--score-3)" : "var(--score-4)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 140, fontSize: 13, color: "var(--ink-muted)", flexShrink: 0 }}>{label}</div>
      <div style={{ flex: 1 }}>
        <div className="score-bar-track">
          <div
            className="score-bar-fill"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
      </div>
      <div className="mono" style={{ width: 28, textAlign: "right", fontSize: 13, fontWeight: 600, color }}>{value}/4</div>
    </div>
  );
}

function MeanBadge({ score }: { score: number }) {
  const pct = Math.round(score * 25);
  const color = score < 1.5 ? "var(--score-0)" : score < 2.5 ? "var(--score-2)" : score < 3.5 ? "var(--score-3)" : "var(--score-4)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <svg width={44} height={44} viewBox="0 0 44 44">
        <circle cx={22} cy={22} r={18} fill="none" stroke="var(--border)" strokeWidth={4} />
        <circle
          cx={22} cy={22} r={18}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={2 * Math.PI * 18}
          strokeDashoffset={2 * Math.PI * 18 * (1 - score / 4)}
          transform="rotate(-90 22 22)"
          style={{ transition: "stroke-dashoffset 0.6s cubic-bezier(0.34,1.56,0.64,1)" }}
        />
        <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fontSize="11" fontWeight="700" fill={color} fontFamily="var(--font-mono)">
          {score.toFixed(1)}
        </text>
      </svg>
    </div>
  );
}

function MetricCell({ label, value, highlight }: { label: string; value: string; highlight: boolean }) {
  return (
    <div style={{
      padding: "10px 12px",
      background: highlight ? "#fffbeb" : "var(--bg-card)",
      textAlign: "center",
    }}>
      <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: highlight ? "var(--timer-amber)" : "var(--ink)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function BookIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function FollowUpIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 10 20 15 15 20" />
      <path d="M4 4v7a4 4 0 0 0 4 4h12" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}
