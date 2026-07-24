"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Document } from "@/lib/api";

export default function EksamenIndexPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<Document[] | null>(null);

  useEffect(() => {
    api.documents.list()
      .then((list) => {
        setDocs(list);
        if (list.length > 0) router.replace(`/eksamen/new?docId=${list[0].id}`);
      })
      .catch(() => setDocs([]));
  }, [router]);

  if (docs === null || docs.length > 0) {
    return (
      <main className="page" style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
        <div className="spinner" style={{ width: 28, height: 28 }} />
      </main>
    );
  }

  return (
    <main className="page" style={{ maxWidth: 560, textAlign: "center", paddingTop: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 20 }}>⏱️</div>
      <h2 style={{ marginBottom: 8 }}>Ingen oppgave lastet opp</h2>
      <p style={{ color: "var(--ink-muted)", marginBottom: 28 }}>Last opp masteroppgaven din før du kan starte en eksamenssimulering.</p>
      <Link href="/opplasting" className="btn btn-primary btn-lg">Last opp oppgave</Link>
    </main>
  );
}
