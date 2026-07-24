"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { nb } from "@/lib/nb";

type State = "idle" | "armed" | "recording" | "uploading" | "done" | "error";

interface Props {
  turnId: string;
  onDone: (turnId: string) => void;
  timeLimit?: number;
}

const RADIUS = 58;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function Recorder({ turnId, onDone, timeLimit = 90 }: Props) {
  const [state, setState] = useState<State>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [level, setLevel] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");

  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rafRef = useRef<number>(0);
  const silenceRef = useRef(0);
  const noiseFloorRef = useRef(0.01);
  const startTimeRef = useRef(0);
  const stoppedRef = useRef(false);

  const cleanup = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    analyserRef.current = null;
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  const progress = Math.min(elapsed / timeLimit, 1);
  const dashOffset = CIRCUMFERENCE * (1 - progress);
  const ringColor = elapsed < 75 ? "var(--timer-ok)" : elapsed < 90 ? "var(--timer-amber)" : "var(--timer-danger)";

  // ── Arm: request mic permission ──────────────────────────────
  const arm = useCallback(async () => {
    setErrorMsg("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 48000,
          channelCount: 1,
        },
      });
      streamRef.current = stream;

      const ctx = new AudioContext();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      src.connect(analyser);
      analyserRef.current = analyser;

      setState("armed");
    } catch {
      setErrorMsg(nb.errors.mic);
      setState("error");
    }
  }, []);

  // ── Stop recording ───────────────────────────────────────────
  const stop = useCallback(() => {
    if (stoppedRef.current) return;
    stoppedRef.current = true;
    if (timerRef.current) clearInterval(timerRef.current);
    cancelAnimationFrame(rafRef.current);
    mrRef.current?.stop();
    setState("uploading");
  }, []);

  // ── Start recording ──────────────────────────────────────────
  const start = useCallback(() => {
    if (!streamRef.current) return;
    stoppedRef.current = false;

    const mr = new MediaRecorder(streamRef.current, {
      mimeType: "audio/webm;codecs=opus",
    });
    chunksRef.current = [];
    mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };

    mr.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      cleanup();
      try {
        await api.turns.answer(turnId, blob);
        setState("done");
        onDone(turnId);
      } catch {
        setState("error");
        setErrorMsg("Opplasting feilet. Prøv igjen.");
      }
    };

    mr.start(250);
    mrRef.current = mr;
    startTimeRef.current = Date.now();
    setState("recording");
    setElapsed(0);

    // Timer
    timerRef.current = setInterval(() => {
      const s = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setElapsed(s);
      // Hard stop at limit + 30s grace
      if (s >= timeLimit + 30) stop();
    }, 200);

    // Calibrate noise floor from first 500 ms
    setTimeout(() => {
      if (!analyserRef.current) return;
      const buf = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteTimeDomainData(buf);
      const rms = Math.sqrt(buf.reduce((s, v) => s + (v - 128) ** 2, 0) / buf.length) / 128;
      noiseFloorRef.current = Math.max(rms, 0.005);
    }, 500);

    // VAD loop
    const vadLoop = () => {
      if (!analyserRef.current || stoppedRef.current) return;
      const buf = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteTimeDomainData(buf);
      const rms = Math.sqrt(buf.reduce((s, v) => s + (v - 128) ** 2, 0) / buf.length) / 128;
      setLevel(Math.min(rms * 6, 1));

      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      if (elapsed > 3) {
        if (rms < noiseFloorRef.current * 4) {
          silenceRef.current += 20;
          if (silenceRef.current >= 2500) { stop(); return; }
        } else {
          silenceRef.current = 0;
        }
      }
      rafRef.current = requestAnimationFrame(vadLoop);
    };
    rafRef.current = requestAnimationFrame(vadLoop);
  }, [stop, cleanup, turnId, onDone, timeLimit]);

  const handleMainClick = () => {
    if (state === "idle") arm();
    else if (state === "armed") start();
    else if (state === "recording") stop();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      {/* Timer ring + button */}
      <div style={{ position: "relative", width: 148, height: 148 }}>
        <svg
          width={148}
          height={148}
          viewBox="0 0 148 148"
          style={{ position: "absolute", inset: 0, transform: "rotate(-90deg)" }}
        >
          {/* Track */}
          <circle cx={74} cy={74} r={RADIUS} fill="none" stroke="var(--border)" strokeWidth={5} />
          {/* Fill */}
          {state === "recording" && (
            <circle
              cx={74}
              cy={74}
              r={RADIUS}
              fill="none"
              stroke={ringColor}
              strokeWidth={5}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              style={{ transition: "stroke-dashoffset 0.25s linear, stroke 0.5s ease" }}
            />
          )}
          {/* Ambient glow ring when recording */}
          {state === "recording" && (
            <circle
              cx={74}
              cy={74}
              r={RADIUS + 6}
              fill="none"
              stroke={ringColor}
              strokeWidth={1}
              opacity={0.2}
              strokeDasharray={CIRCUMFERENCE * 1.25}
              strokeDashoffset={dashOffset * 1.25}
            />
          )}
        </svg>

        {/* Centre button */}
        <button
          onClick={handleMainClick}
          disabled={state === "uploading" || state === "done"}
          className={state === "recording" ? "recording-glow" : ""}
          style={{
            position: "absolute",
            inset: 14,
            borderRadius: "50%",
            border: "none",
            cursor: state === "uploading" || state === "done" ? "default" : "pointer",
            background: state === "recording"
              ? "var(--accent)"
              : state === "armed"
              ? "#f0f0ec"
              : "var(--bg-card)",
            boxShadow: state === "recording"
              ? "var(--accent-glow), var(--shadow-md)"
              : "var(--shadow-md)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.3s, box-shadow 0.3s",
          }}
        >
          {state === "idle" && <MicIcon color="var(--ink-muted)" />}
          {state === "armed" && <MicIcon color="var(--accent)" />}
          {state === "recording" && <StopIcon />}
          {state === "uploading" && <div className="spinner" />}
          {state === "done" && <CheckIcon />}
          {state === "error" && <span style={{ fontSize: 22 }}>!</span>}
        </button>
      </div>

      {/* Elapsed */}
      {state === "recording" && (
        <div className="mono" style={{ fontSize: 18, fontWeight: 500, letterSpacing: "0.02em", color: elapsed >= 90 ? "var(--timer-danger)" : elapsed >= 75 ? "var(--timer-amber)" : "var(--ink-muted)" }}>
          {fmtTime(elapsed)}<span style={{ color: "var(--border-strong)", margin: "0 4px" }}>/</span>{fmtTime(timeLimit)}
        </div>
      )}

      {/* Level meter */}
      {state === "recording" && (
        <div className="level-meter" style={{ width: 120 }}>
          <div className="level-fill" style={{ width: `${level * 100}%` }} />
        </div>
      )}

      {/* State label */}
      <div style={{ fontSize: 13, color: "var(--ink-muted)", textAlign: "center", minHeight: 20 }}>
        {state === "idle"      && <span>Klikk for å klargjøre mikrofon</span>}
        {state === "armed"     && <span style={{ color: "var(--accent)", fontWeight: 500 }}>{nb.drill.record}</span>}
        {state === "recording" && <span style={{ color: "var(--accent)", fontWeight: 500 }}>{nb.drill.listening}</span>}
        {state === "uploading" && <span>{nb.drill.transcribing}</span>}
        {state === "done"      && <span style={{ color: "var(--timer-ok)" }}>Svar mottatt</span>}
        {state === "error"     && <span style={{ color: "var(--timer-danger)" }}>{errorMsg}</span>}
      </div>

      {/* Manual stop */}
      {state === "recording" && (
        <button className="btn btn-secondary btn-sm" onClick={stop}>{nb.drill.stop}</button>
      )}
    </div>
  );
}

function fmtTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function MicIcon({ color = "#fff", size = 28 }: { color?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="17" x2="12" y2="21" />
      <line x1="9" y1="21" x2="15" y2="21" />
    </svg>
  );
}

function StopIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#fff">
      <rect x="5" y="5" width="14" height="14" rx="2" />
    </svg>
  );
}

function CheckIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="var(--timer-ok)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4,12 9,17 20,6" />
    </svg>
  );
}
