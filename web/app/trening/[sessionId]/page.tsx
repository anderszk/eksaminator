"use client";

import { use, useEffect, useState, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { nb } from "@/lib/nb";
import Examiner from "@/components/examiner";
import Recorder from "@/components/recorder";
import FeedbackPanel from "@/components/feedback";

interface Turn {
  id: string;
  ordinal: number;
  status: string;
  question?: Question;
  audioUrl?: string;
  transcript?: string;
  scores?: Record<string, number>;
  feedbackMd?: string;
  bluffed?: boolean;
  usedShape?: string;
  missedPoints?: string[];
  delivery?: Record<string, number>;
}

interface Question {
  id: string;
  text: string;
  why_asked: string;
  category: string;
  difficulty: number;
  expected_shape: string;
  source_refs: Array<{ page: number; section_path?: string }>;
  follow_ups: string[];
  model_answer?: string;
  rubric?: Record<string, unknown>;
}

type Phase = "loading" | "question" | "armed" | "recording" | "grading" | "feedback" | "done" | "error";

export default function TreningPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);

  const [phase, setPhase] = useState<Phase>("loading");
  const [turn, setTurn] = useState<Turn | null>(null);
  const [error, setError] = useState("");
  const [questionCount, setQuestionCount] = useState(0);
  const [totalScore, setTotalScore] = useState(0);
  const [sessionScores, setSessionScores] = useState<number[]>([]);
  const sseRef = useRef<EventSource | null>(null);

  const loadNextTurn = useCallback(async () => {
    setPhase("loading");
    try {
      const data = await api.sessions.next(sessionId) as any;
      if (!data || data.status === "done") {
        setPhase("done");
        return;
      }
      setTurn({
        id: data.turn_id,
        ordinal: data.ordinal,
        status: "pending",
        question: data.question,
        audioUrl: data.audio_url,
      });
      setPhase("question");
    } catch {
      setError("Kunne ikke laste neste spørsmål.");
      setPhase("error");
    }
  }, [sessionId]);

  useEffect(() => { loadNextTurn(); }, [loadNextTurn]);

  const handleAnswerDone = useCallback((turnId: string) => {
    setPhase("grading");
    // Open SSE stream for grade
    const es = api.turns.gradeStream(turnId);
    sseRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "transcript") {
          setTurn(t => t ? { ...t, transcript: data.text } : t);
        } else if (data.type === "grade") {
          setTurn(t => t ? {
            ...t,
            scores: data.scores,
            feedbackMd: data.feedback_md,
            bluffed: data.bluffed,
            usedShape: data.used_shape,
            missedPoints: data.missed_points,
            delivery: {
              duration_ms: data.duration_ms,
              wpm: data.wpm,
              filler_count: data.filler_count,
              longest_pause_ms: data.longest_pause_ms,
            },
          } : t);
          const mean = Object.values(data.scores as Record<string, number>).reduce((s, v) => s + v, 0) / 4;
          setSessionScores(ss => [...ss, mean]);
          setTotalScore(ts => ts + mean);
          setQuestionCount(c => c + 1);
          es.close();
          setPhase("feedback");
        } else if (data.type === "error") {
          es.close();
          setPhase("feedback"); // show what we have
        }
      } catch {/* ignore parse errors */}
    };

    es.onerror = () => {
      es.close();
      setPhase("feedback");
    };
  }, []);

  const handleFollowUp = async () => {
    if (!turn) return;
    setPhase("loading");
    try {
      const data = await api.turns.followUp(turn.id) as any;
      setTurn({
        id: data.turn_id,
        ordinal: data.ordinal,
        status: "pending",
        question: data.question,
        audioUrl: data.audio_url,
      });
      setPhase("question");
    } catch { setPhase("feedback"); }
  };

  const handleNext = () => { loadNextTurn(); };

  const handleSkip = async () => {
    if (!turn) return;
    try { await api.turns.skip(turn.id); } catch {/* ok */}
    loadNextTurn();
  };

  if (phase === "error") {
    return (
      <main className="page" style={{ maxWidth: 680 }}>
        <div style={{ padding: "48px 0", textAlign: "center", color: "var(--ink-muted)" }}>
          {error || "Noe gikk galt."}
        </div>
      </main>
    );
  }

  if (phase === "done") {
    const avgScore = questionCount > 0 ? totalScore / questionCount : 0;
    return (
      <main className="page" style={{ maxWidth: 680, textAlign: "center" }}>
        <div style={{ padding: "64px 0" }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>✓</div>
          <h1 style={{ marginBottom: 8 }}>Treningsøkt fullført</h1>
          <p style={{ color: "var(--ink-muted)", marginBottom: 32 }}>
            {questionCount} spørsmål · Snittskår {avgScore.toFixed(1)}/4
          </p>
          <ScoreTrend scores={sessionScores} />
        </div>
      </main>
    );
  }

  return (
    <main className="page" style={{ maxWidth: 780 }}>
      {/* Session meta */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <div>
          <h2 style={{ marginBottom: 2 }}>Trening</h2>
          <div style={{ fontSize: 13, color: "var(--ink-muted)" }}>
            {questionCount > 0 && `${questionCount} svar · snitt ${(totalScore / questionCount).toFixed(1)}/4`}
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={handleSkip} disabled={phase === "loading"}>
          Hopp over
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 200px", gap: 32, alignItems: "start" }}>
        {/* Left: question + feedback */}
        <div style={{ minWidth: 0 }}>
          {/* Question */}
          {phase !== "loading" && turn?.question && (
            <Examiner
              questionText={turn.question.text}
              audioUrl={turn.audioUrl}
              whyAsked={turn.question.why_asked}
              category={turn.question.category}
              difficulty={turn.question.difficulty}
              onAudioEnd={() => setPhase(p => p === "question" ? "armed" : p)}
            />
          )}

          {phase === "loading" && (
            <div style={{ padding: "48px 0", display: "flex", justifyContent: "center" }}>
              <div className="spinner" style={{ width: 28, height: 28 }} />
            </div>
          )}

          {/* Transcript (while grading) */}
          {turn?.transcript && (
            <div className="fade-up" style={{ marginTop: 20, padding: "14px 16px", background: "var(--bg-elevated)", borderRadius: "var(--radius)", fontSize: 13.5, color: "var(--ink-muted)", lineHeight: 1.6, borderLeft: "3px solid var(--border-strong)" }}>
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6, color: "var(--ink-faint)" }}>Ditt svar</div>
              {turn.transcript}
            </div>
          )}

          {/* Feedback */}
          {phase === "feedback" && turn && (
            <div style={{ marginTop: 24 }}>
              <FeedbackPanel
                scores={turn.scores as any}
                feedbackMd={turn.feedbackMd}
                bluffed={turn.bluffed}
                usedShape={turn.usedShape}
                missedPoints={turn.missedPoints}
                modelAnswer={turn.question?.model_answer}
                sourceRefs={turn.question?.source_refs}
                delivery={turn.delivery}
                onFollowUp={turn.question?.follow_ups?.length ? handleFollowUp : undefined}
                onNext={handleNext}
              />
            </div>
          )}
        </div>

        {/* Right: recorder */}
        <div style={{ position: "sticky", top: 80, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          {(phase === "armed" || phase === "recording" || phase === "grading") && turn && (
            <Recorder
              turnId={turn.id}
              onDone={handleAnswerDone}
            />
          )}
          {phase === "question" && (
            <div style={{ textAlign: "center", color: "var(--ink-faint)", fontSize: 13 }}>
              <div style={{ marginBottom: 8 }}>Hører på spørsmålet…</div>
              <div className="spinner" />
            </div>
          )}
          {phase === "feedback" && (
            <div style={{ textAlign: "center" }}>
              <button className="btn btn-primary" onClick={handleNext} style={{ width: "100%", justifyContent: "center" }}>
                {nb.drill.next}
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function ScoreTrend({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null;
  const w = 300, h = 80;
  const pad = 8;
  const min = 0, max = 4;
  const pts = scores.map((s, i) => ({
    x: pad + (i / (scores.length - 1)) * (w - pad * 2),
    y: h - pad - ((s - min) / (max - min)) * (h - pad * 2),
  }));
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  return (
    <div style={{ margin: "0 auto", width: w }}>
      <div style={{ fontSize: 12, color: "var(--ink-faint)", marginBottom: 4, textAlign: "center" }}>Utvikling per svar</div>
      <svg width={w} height={h} style={{ overflow: "visible" }}>
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" />
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={3.5} fill="var(--accent)" />
        ))}
      </svg>
    </div>
  );
}
