"use client";

import { use, useEffect, useState, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { nb } from "@/lib/nb";

interface Turn {
  id: string;
  ordinal: number;
  question?: { text: string; category: string; difficulty: number };
  audioUrl?: string;
}

type Phase = "loading" | "running" | "ending" | "ended" | "error";

const EXAM_DURATION_MINUTES = 45;

export default function EksamenPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);

  const [phase, setPhase] = useState<Phase>("loading");
  const [turn, setTurn] = useState<Turn | null>(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [elapsed, setElapsed] = useState(0); // seconds since session start
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef = useRef(0);

  // Tick timer
  useEffect(() => {
    if (phase === "running") {
      startRef.current = Date.now();
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
      }, 1000);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [phase]);

  const loadNextTurn = useCallback(async () => {
    try {
      const data = await api.sessions.next(sessionId) as any;
      if (!data || data.status === "done") {
        endSession();
        return;
      }
      setTurn({ id: data.turn_id, ordinal: data.ordinal, question: data.question, audioUrl: data.audio_url });
      setQuestionCount(c => c + 1);

      // Autoplay question
      if (audioRef.current && data.audio_url) {
        audioRef.current.src = data.audio_url;
        audioRef.current.load();
        audioRef.current.play().catch(() => {});
      }
    } catch {
      setPhase("error");
    }
  }, [sessionId]);

  useEffect(() => {
    const init = async () => {
      // Arm microphone on session load
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        });
        streamRef.current = stream;
        setPhase("running");
        await loadNextTurn();
      } catch {
        setPhase("error");
      }
    };
    init();
    return () => { streamRef.current?.getTracks().forEach(t => t.stop()); };
  }, [loadNextTurn]);

  const startRecording = useCallback(() => {
    if (!streamRef.current || isRecording) return;
    const mr = new MediaRecorder(streamRef.current, { mimeType: "audio/webm;codecs=opus" });
    chunksRef.current = [];
    mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    mr.start(250);
    mrRef.current = mr;
    setIsRecording(true);
  }, [isRecording]);

  const stopRecording = useCallback(async () => {
    if (!mrRef.current || !turn) return;
    setIsRecording(false);
    setIsUploading(true);
    mrRef.current.stop();
    mrRef.current.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      try {
        await api.turns.answer(turn.id, blob);
      } catch {/* keep going */}
      setIsUploading(false);
      await loadNextTurn();
    };
  }, [turn, loadNextTurn]);

  const endSession = useCallback(async () => {
    setPhase("ending");
    if (timerRef.current) clearInterval(timerRef.current);
    try {
      await api.sessions.end(sessionId);
    } catch {/* ok */}
    setPhase("ended");
  }, [sessionId]);

  const fmtElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  // Full screen exam UI — dark background
  return (
    <div className="exam-surface">
      {/* Hidden audio */}
      <audio ref={audioRef} onEnded={startRecording} style={{ display: "none" }} />

      {phase === "loading" && (
        <div style={{ color: "rgba(255,255,255,0.5)" }}>Forbereder eksamen…</div>
      )}

      {phase === "error" && (
        <div style={{ color: "#E8918A", textAlign: "center" }}>
          <div style={{ fontSize: 24, marginBottom: 12 }}>!</div>
          <div>{nb.errors.mic}</div>
        </div>
      )}

      {(phase === "running" || phase === "ending") && (
        <div style={{ width: "100%", maxWidth: 640, padding: "0 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: 40 }}>
          {/* Status bar */}
          <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 13 }}>
              Spørsmål {questionCount}
            </div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 500, color: elapsed > EXAM_DURATION_MINUTES * 60 ? "#E8918A" : "rgba(255,255,255,0.7)" }}>
              {fmtElapsed(elapsed)}
            </div>
            <button
              className="btn"
              style={{ background: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.15)", fontSize: 13 }}
              onClick={endSession}
            >
              {nb.exam.end}
            </button>
          </div>

          {/* Question (small — meant to be heard) */}
          {turn?.question && (
            <div style={{ textAlign: "center", maxWidth: 480 }}>
              <p style={{ fontSize: 15, color: "rgba(255,255,255,0.55)", lineHeight: 1.6 }}>
                {turn.question.text}
              </p>
            </div>
          )}

          {/* Record button */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isUploading}
              style={{
                width: 80, height: 80,
                borderRadius: "50%",
                border: "none",
                cursor: isUploading ? "default" : "pointer",
                background: isRecording ? "#8A90E8" : "rgba(255,255,255,0.08)",
                boxShadow: isRecording ? "0 0 0 12px rgba(138,144,232,0.2), 0 0 0 24px rgba(138,144,232,0.08)" : "none",
                transition: "all 0.3s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {isUploading ? (
                <div style={{ width: 24, height: 24, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "rgba(255,255,255,0.8)", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
              ) : isRecording ? (
                <svg width={28} height={28} viewBox="0 0 24 24" fill="rgba(255,255,255,0.9)">
                  <rect x="5" y="5" width="14" height="14" rx="2" />
                </svg>
              ) : (
                <svg width={28} height={28} viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="2" width="6" height="12" rx="3" />
                  <path d="M5 10a7 7 0 0 0 14 0" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                  <line x1="9" y1="21" x2="15" y2="21" />
                </svg>
              )}
            </button>

            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", textAlign: "center" }}>
              {isUploading ? "Laster opp…" : isRecording ? "Spiller inn — klikk for å stoppe" : "Klikk for å ta opp"}
            </div>
          </div>

          {/* No scores shown in exam mode */}
          <p style={{ fontSize: 11, color: "rgba(255,255,255,0.2)", textAlign: "center" }}>
            {nb.exam.running}
          </p>
        </div>
      )}

      {phase === "ended" && (
        <div style={{ textAlign: "center", color: "rgba(255,255,255,0.7)", maxWidth: 400, padding: "0 24px" }}>
          <div style={{ fontSize: 48, marginBottom: 20, color: "rgba(255,255,255,0.3)" }}>✓</div>
          <p style={{ fontSize: 16, lineHeight: 1.7 }}>{nb.exam.ended}</p>
          <p className="mono" style={{ marginTop: 16, fontSize: 13, color: "rgba(255,255,255,0.3)" }}>
            {questionCount} spørsmål · {fmtElapsed(elapsed)}
          </p>
          <a href="/oversikt" style={{ display: "inline-block", marginTop: 32, padding: "10px 24px", background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "var(--radius)", color: "rgba(255,255,255,0.7)", textDecoration: "none", fontSize: 14 }}>
            Se oversikt
          </a>
        </div>
      )}
    </div>
  );
}
