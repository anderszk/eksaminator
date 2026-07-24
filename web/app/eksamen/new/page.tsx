"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "@/lib/api";

function EksamenNewInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const docId = searchParams.get("docId") ?? "";

  const [count, setCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleStart() {
    if (!docId) {
      setError("Ingen oppgave valgt. Gå til Oversikt og velg en oppgave.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const session = await api.sessions.create({
        document_id: docId,
        mode: "exam",
        config: { count },
      }) as { id: string };
      router.push(`/eksamen/${session.id}`);
    } catch {
      setError("Klarte ikke å starte sesjonen. Prøv igjen.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-5">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[var(--bg-elevated)] border border-[var(--border)] mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-[var(--ink-muted)]">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" fill="currentColor"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight mb-2">Eksamenssimulering</h1>
          <p className="text-[var(--ink-muted)] text-sm leading-relaxed">
            Du svarer på spørsmål uten tilbakemelding underveis — akkurat som i en ekte muntlig eksamen.
            Rapporten er klar når sesjonen er ferdig.
          </p>
        </div>

        <div className="card p-6 space-y-6">
          {/* Rules */}
          <div className="space-y-2.5">
            {[
              "Ingen tilbakemelding under sesjonen",
              "Mikrofonen starter automatisk etter hvert spørsmål",
              "Du har 90 sekunder per svar",
              "AI-vurdering av alle svar etter avslutning",
            ].map((rule, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-[var(--bg-elevated)] border border-[var(--border)] flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 3" stroke="var(--ink-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <span className="text-sm text-[var(--ink-muted)]">{rule}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-[var(--border)]" />

          {/* Question count */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Antall spørsmål</label>
              <span className="mono text-base font-bold">{count}</span>
            </div>
            <input
              type="range"
              min={10}
              max={40}
              step={5}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-full accent-[var(--ink)]"
            />
            <div className="flex justify-between text-xs text-[var(--ink-faint)] mt-1">
              <span>10</span>
              <span>40</span>
            </div>
            <p className="text-xs text-[var(--ink-faint)] mt-1">
              Estimert tid: {Math.round(count * 1.5)} – {count * 2} minutter
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={handleStart}
              disabled={loading}
              className="btn btn-primary w-full py-3 text-base font-semibold disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  Starter …
                </span>
              ) : (
                "Start eksamen"
              )}
            </button>
            <button
              onClick={() => router.back()}
              className="btn btn-ghost w-full py-2.5"
            >
              Avbryt
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function EksamenNewPage() {
  return (
    <Suspense>
      <EksamenNewInner />
    </Suspense>
  );
}
