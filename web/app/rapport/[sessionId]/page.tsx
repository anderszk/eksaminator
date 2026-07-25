"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import FeedbackPanel from "@/components/feedback";

interface ReportTurn {
  turn_id: string;
  ordinal: number;
  status: string;
  question: { id: string; text: string; category: string; difficulty: number };
  transcript: string | null;
  stt_confidence: number | null;
  scores: { korrekthet: number; begrunnelse: number; forbehold: number; struktur: number } | null;
  mean_score: number | null;
  feedback_md: string | null;
  bluffed: boolean | null;
  used_shape: string | null;
  missed_points: string[] | null;
  wpm: number | null;
  duration_ms: number | null;
  filler_count: number | null;
}

interface Report {
  session_id: string;
  mode: string;
  started_at: string;
  ended_at: string | null;
  total_questions: number;
  graded_questions: number;
  mean_score: number | null;
  turns: ReportTurn[];
}

function scoreColor(score: number) {
  return score < 1.5 ? "var(--score-0)" : score < 2.5 ? "var(--score-2)" : score < 3.5 ? "var(--score-3)" : "var(--score-4)";
}

// Whisper avg_logprob below this is a reasonable heuristic for "the model wasn't
// confident about this transcription" — worth a visible warning, not a hard cutoff.
function isLowConfidence(sttConfidence: number | null | undefined): boolean {
  return sttConfidence !== null && sttConfidence !== undefined && sttConfidence < -1.0;
}

export default function RapportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const load = async () => {
      try {
        const r = await api.sessions.report(sessionId) as Report;
        if (cancelled) return;
        setReport(r);
        setLoading(false);
        // Exam grading runs as a deferred background job — poll while it's still catching up.
        if (r.ended_at && r.graded_questions < r.total_questions) {
          timer = setTimeout(load, 4000);
        }
      } catch {
        if (!cancelled) { setNotFound(true); setLoading(false); }
      }
    };
    load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [sessionId]);

  if (loading) {
    return (
      <main className="page" style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
        <div className="spinner" style={{ width: 28, height: 28 }} />
      </main>
    );
  }

  if (notFound || !report) {
    return (
      <main className="page" style={{ maxWidth: 560, textAlign: "center", paddingTop: 80 }}>
        <h2 style={{ marginBottom: 8 }}>Fant ikke rapporten</h2>
        <Link href="/oversikt" className="btn btn-secondary" style={{ marginTop: 12 }}>Til oversikt</Link>
      </main>
    );
  }

  const stillGrading = !!report.ended_at && report.graded_questions < report.total_questions;
  const dateLabel = new Date(report.started_at).toLocaleDateString("nb-NO", { day: "numeric", month: "long", year: "numeric" });

  return (
    <main className="page" style={{ maxWidth: 760 }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 13, color: "var(--ink-faint)", marginBottom: 4 }}>
          {report.mode === "exam" ? "Eksamenssimulering" : "Trening"} · {dateLabel}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <h1>Rapport</h1>
          {report.mean_score !== null && (
            <span className="mono" style={{ fontSize: 20, fontWeight: 700, color: scoreColor(report.mean_score) }}>
              {report.mean_score.toFixed(1)}/4
            </span>
          )}
        </div>
        <p style={{ color: "var(--ink-muted)", fontSize: 14, marginTop: 4 }}>
          {report.graded_questions} av {report.total_questions} spørsmål vurdert
        </p>
      </div>

      {stillGrading && (
        <div className="banner banner-info" style={{ marginBottom: 20 }}>
          <div className="spinner" style={{ width: 14, height: 14 }} />
          Vurderer fortsatt svarene …
        </div>
      )}

      {report.turns.length === 0 ? (
        <div style={{ padding: "48px 0", textAlign: "center", color: "var(--ink-faint)", fontSize: 14 }}>
          Ingen spørsmål i denne økten.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {report.turns.map(t => (
            <TurnRow key={t.turn_id} turn={t} open={openId === t.turn_id} onToggle={() => setOpenId(o => (o === t.turn_id ? null : t.turn_id))} />
          ))}
        </div>
      )}
    </main>
  );
}

function TurnRow({ turn, open, onToggle }: { turn: ReportTurn; open: boolean; onToggle: () => void }) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <button className="collapsible-trigger" style={{ padding: "14px 18px" }} onClick={onToggle}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flex: 1 }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)", width: 20, flexShrink: 0 }}>{turn.ordinal + 1}</span>
          <span style={{ fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{turn.question.text}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          {turn.mean_score !== null ? (
            <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: scoreColor(turn.mean_score) }}>{turn.mean_score.toFixed(1)}</span>
          ) : (
            <span className="pill" style={{ fontSize: 11 }}>{turn.status === "skipped" ? "Hoppet over" : "Ikke vurdert"}</span>
          )}
          <ChevronIcon open={open} />
        </div>
      </button>
      {open && (
        <div className="fade-up" style={{ padding: "0 18px 18px", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", gap: 6, margin: "14px 0" }}>
            <span className="pill">{turn.question.category}</span>
            <span className="pill">Nivå {turn.question.difficulty}</span>
          </div>
          {turn.transcript && (
            <div style={{ marginBottom: 16 }}>
              {isLowConfidence(turn.stt_confidence) && (
                <span className="badge badge-amber" style={{ marginBottom: 6 }} title="Talegjenkjenningen var usikker på deler av svaret. Sjekk at teksten stemmer.">
                  Usikker transkripsjon
                </span>
              )}
              <div style={{ fontSize: 14, lineHeight: 1.65, color: "var(--ink-muted)", fontStyle: "italic" }}>
                «{turn.transcript}»
              </div>
            </div>
          )}
          <FeedbackPanel
            scores={turn.scores ?? undefined}
            feedbackMd={turn.feedback_md ?? undefined}
            bluffed={turn.bluffed ?? undefined}
            usedShape={turn.used_shape ?? undefined}
            missedPoints={turn.missed_points ?? undefined}
            delivery={{
              duration_ms: turn.duration_ms ?? undefined,
              wpm: turn.wpm ?? undefined,
              filler_count: turn.filler_count ?? undefined,
            }}
          />
        </div>
      )}
    </div>
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
