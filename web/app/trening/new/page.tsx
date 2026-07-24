"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "@/lib/api";

const CATEGORIES = [
  "Teori og begreper",
  "Metode",
  "Empiri og funn",
  "Analyse",
  "Diskusjon",
  "Metodekritikk",
  "Kildekritikk",
  "Etikk",
  "Bidrag og implikasjoner",
  "Spørsmål om fagfeltet",
  "Praktisk relevans",
  "Fremtidig forskning",
  "Forsvarsrunde",
  "Begrepsavklaring",
];

const PERSONAS = [
  { id: "KS", label: "Kritisk sensor", description: "Utfordrer antagelser og metodikk" },
  { id: "GS", label: "Grundig sensor", description: "Dybdespørsmål om teori og empiri" },
  { id: "VS", label: "Vennlig sensor", description: "Konstruktiv og oppmuntrende" },
];

function TreningNewInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const docId = searchParams.get("docId") ?? "";

  const [categories, setCategories] = useState<string[]>([]);
  const [diffMin, setDiffMin] = useState(1);
  const [diffMax, setDiffMax] = useState(4);
  const [count, setCount] = useState(10);
  const [persona, setPersona] = useState("KS");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function toggleCat(cat: string) {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  }

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
        mode: "drill",
        config: {
          count,
          categories: categories.length > 0 ? categories : undefined,
          difficulty_min: diffMin,
          difficulty_max: diffMax,
          persona,
        },
      }) as { id: string };
      router.push(`/trening/${session.id}`);
    } catch {
      setError("Klarte ikke å starte sesjonen. Prøv igjen.");
      setLoading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-5 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[var(--ink-faint)] text-sm">Trening</span>
          <span className="text-[var(--ink-faint)]">/</span>
          <span className="text-sm text-[var(--ink-muted)]">Ny sesjon</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Konfigurer treningsrunde</h1>
        <p className="text-[var(--ink-muted)] mt-1 text-sm">
          Velg hva du vil øve på. Du får umiddelbar tilbakemelding etter hvert svar.
        </p>
      </div>

      <div className="space-y-6">
        {/* Persona */}
        <section className="card p-5">
          <h2 className="text-base font-semibold mb-3">Sensor-personlighet</h2>
          <div className="grid grid-cols-3 gap-3">
            {PERSONAS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPersona(p.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  persona === p.id
                    ? "border-[var(--ink)] bg-[var(--bg-elevated)]"
                    : "border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)]"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="mono text-xs font-bold text-[var(--ink-faint)]">{p.id}</span>
                  {persona === p.id && (
                    <div className="w-2 h-2 rounded-full bg-[var(--ink)]" />
                  )}
                </div>
                <div className="font-semibold text-sm">{p.label}</div>
                <div className="text-xs text-[var(--ink-muted)] mt-0.5">{p.description}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Count */}
        <section className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold">Antall spørsmål</h2>
            <span className="mono text-lg font-bold">{count}</span>
          </div>
          <input
            type="range"
            min={5}
            max={30}
            step={5}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-full accent-[var(--ink)]"
          />
          <div className="flex justify-between text-xs text-[var(--ink-faint)] mt-1">
            <span>5</span>
            <span>30</span>
          </div>
        </section>

        {/* Difficulty */}
        <section className="card p-5">
          <h2 className="text-base font-semibold mb-3">Vanskelighetsgrad</h2>
          <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((d) => {
              const labels = ["Grunnleggende", "Middels", "Avansert", "Ekspertsnivå"];
              const isInRange = d >= diffMin && d <= diffMax;
              return (
                <button
                  key={d}
                  onClick={() => {
                    if (d === diffMin && d === diffMax) return;
                    if (d < diffMin) setDiffMin(d);
                    else if (d > diffMax) setDiffMax(d);
                    else if (d === diffMin) setDiffMin(d + 1);
                    else if (d === diffMax) setDiffMax(d - 1);
                  }}
                  className={`p-2.5 rounded-lg border text-center transition-all ${
                    isInRange
                      ? "border-[var(--ink)] bg-[var(--bg-elevated)]"
                      : "border-[var(--border)] text-[var(--ink-faint)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <div className="mono text-lg font-bold">{d}</div>
                  <div className="text-[10px] leading-tight mt-0.5">{labels[d - 1]}</div>
                </button>
              );
            })}
          </div>
          <p className="text-xs text-[var(--ink-faint)] mt-2">
            Trykk for å justere intervallet ({diffMin}–{diffMax})
          </p>
        </section>

        {/* Categories */}
        <section className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold">Kategorier</h2>
            <button
              onClick={() => setCategories(categories.length === CATEGORIES.length ? [] : [...CATEGORIES])}
              className="text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
            >
              {categories.length === CATEGORIES.length ? "Fjern alle" : "Velg alle"}
            </button>
          </div>
          <p className="text-xs text-[var(--ink-muted)] mb-3">
            {categories.length === 0
              ? "Alle kategorier er inkludert."
              : `${categories.length} av ${CATEGORIES.length} valgt.`}
          </p>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => toggleCat(cat)}
                className={`pill transition-all ${
                  categories.includes(cat)
                    ? "bg-[var(--ink)] text-[var(--bg)]"
                    : "bg-[var(--bg-elevated)] text-[var(--ink-muted)] hover:text-[var(--ink)]"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </section>

        {/* Error */}
        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleStart}
            disabled={loading}
            className="btn btn-primary flex-1 py-3 text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
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
              "Start treningsrunde"
            )}
          </button>
          <button
            onClick={() => router.back()}
            className="btn btn-ghost px-5 py-3"
          >
            Avbryt
          </button>
        </div>
      </div>
    </main>
  );
}

export default function TreningNewPage() {
  return (
    <Suspense>
      <TreningNewInner />
    </Suspense>
  );
}
