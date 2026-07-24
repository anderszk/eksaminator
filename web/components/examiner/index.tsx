"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  questionText: string;
  audioUrl?: string;
  whyAsked?: string;
  category?: string;
  difficulty?: number;
  persona?: "vennlig" | "grundig" | "krevende";
  onAudioEnd?: () => void;
}

const PERSONA_LABELS = {
  vennlig:   "Vennlig sensor",
  grundig:   "Grundig sensor",
  krevende:  "Krevende ekstern sensor",
};
const CATEGORY_LABELS: Record<string, string> = {
  motivasjon:         "Motivasjon",
  metodevalg:         "Metodevalg",
  metodeforstaelse:   "Metodeforståelse",
  resultater:         "Resultater",
  statistikk:         "Statistikk",
  validitet:          "Validitet",
  alternativ:         "Alternative forklaringer",
  litteratur:         "Litteratur",
  relevans:           "Klinisk relevans",
  etikk:              "Etikk",
  reproduserbarhet:   "Reproduserbarhet",
  grunnlag:           "Faglig grunnlag",
  videre:             "Videre arbeid",
  kritisk:            "Kritisk",
};
const DIFF_LABELS = ["", "Gjenkalle", "Forklare", "Forsvare", "Motstå"];

export default function Examiner({ questionText, audioUrl, whyAsked, category, difficulty, persona = "grundig", onAudioEnd }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const [audioError, setAudioError] = useState(false);

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => setAudioError(true));
    }
  }, [audioUrl]);

  const replay = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => {});
    }
  };

  return (
    <div className="fade-up">
      {/* Persona header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <ExaminerAvatar persona={persona} />
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{PERSONA_LABELS[persona]}</div>
          <div style={{ display: "flex", gap: 6, marginTop: 3, flexWrap: "wrap" }}>
            {category && (
              <span className="pill">{CATEGORY_LABELS[category] ?? category}</span>
            )}
            {difficulty && (
              <span className="pill" style={{ color: diffColor(difficulty), borderColor: diffColor(difficulty), background: diffBg(difficulty) }}>
                {DIFF_LABELS[difficulty]}
              </span>
            )}
          </div>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {audioUrl && !audioError && (
            <button
              className="btn btn-icon btn-sm"
              onClick={replay}
              title="Spill av spørsmålet på nytt"
            >
              <ReplayIcon />
            </button>
          )}
        </div>
      </div>

      {/* The question — large serif */}
      <blockquote style={{
        margin: 0,
        padding: "20px 24px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderLeft: "4px solid var(--ink)",
        borderRadius: "var(--radius-lg)",
        position: "relative",
      }}>
        <p className="q-text">{questionText}</p>
      </blockquote>

      {/* Audio element (hidden) */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onPlay={() => setPlaying(true)}
          onEnded={() => { setPlaying(false); onAudioEnd?.(); }}
          onPause={() => setPlaying(false)}
          onError={() => setAudioError(true)}
          style={{ display: "none" }}
        />
      )}

      {playing && (
        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8, color: "var(--ink-muted)", fontSize: 13 }}>
          <WaveformIcon />
          Spiller av spørsmål…
        </div>
      )}

      {/* Why asked — collapsible */}
      {whyAsked && (
        <div style={{ marginTop: 16 }}>
          <button
            className="collapsible-trigger"
            onClick={() => setShowWhy(v => !v)}
            style={{ fontSize: 13, color: "var(--ink-muted)" }}
          >
            {/* label */}
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <InfoIcon />
              Hvorfor stilles dette spørsmålet?
            </span>
            <ChevronIcon className={`collapsible-chevron ${showWhy ? "open" : ""}`} />
          </button>
          {showWhy && (
            <div className="fade-up" style={{ marginTop: 8, padding: "12px 14px", background: "var(--bg-elevated)", borderRadius: "var(--radius)", fontSize: 13, color: "var(--ink-muted)", lineHeight: 1.6 }}>
              {whyAsked}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function diffColor(d: number) {
  return ["", "var(--score-4)", "var(--score-3)", "var(--timer-amber)", "var(--timer-danger)"][d] ?? "var(--ink-muted)";
}
function diffBg(d: number) {
  return ["", "var(--success-bg)", "var(--success-bg)", "var(--warning-bg)", "var(--error-bg)"][d] ?? "var(--bg-elevated)";
}

function ExaminerAvatar({ persona }: { persona: string }) {
  const color = persona === "krevende" ? "#C15048" : persona === "grundig" ? "#5C61C9" : "#4E9B6B";
  const initials = persona === "krevende" ? "KS" : persona === "grundig" ? "GS" : "VS";
  return (
    <div style={{
      width: 40, height: 40, borderRadius: "50%",
      background: `${color}18`,
      border: `1.5px solid ${color}44`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 12, fontWeight: 700, color,
      flexShrink: 0,
    }}>
      {initials}
    </div>
  );
}

function ReplayIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 .49-3.27" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function ChevronIcon({ className }: { className: string }) {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function WaveformIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
      <path d="M2 12h2M4 8v8M8 6v12M12 4v16M16 6v12M20 8v8M22 12h2" />
    </svg>
  );
}
