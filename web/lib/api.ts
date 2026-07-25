// Typed API client for the FastAPI backend.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Document { id: string; filename: string; uploaded_at: string; page_count: number; title?: string | null }

export interface SessionSummary {
  id: string;
  document_id: string;
  mode: "drill" | "exam";
  started_at: string;
  ended_at: string | null;
  question_count: number;
  graded_count: number;
  mean_score: number | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  documents: {
    list: () => request<Document[]>("/documents"),
    upload: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request("/documents", { method: "POST", body: fd });
    },
    get: (id: string) => request(`/documents/${id}`),
    rename: (id: string, title: string) =>
      request<Document>(`/documents/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) }),
    delete: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  },

  pipeline: {
    status: (docId: string) => request(`/pipeline/${docId}/status`),
    run: (docId: string, stages?: string, force = false) =>
      request(`/pipeline/${docId}/run?${new URLSearchParams({ ...(stages ? { stages } : {}), force: String(force) })}`, { method: "POST" }),
  },

  questions: {
    list: (docId: string, params?: Record<string, string>) =>
      request(`/documents/${docId}/questions?${new URLSearchParams(params)}`),
    patch: (id: string, body: object) =>
      request(`/questions/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    audioUrl: (id: string) => request<{ url: string }>(`/questions/${id}/audio`),
  },

  sessions: {
    list: (docId: string) => request<SessionSummary[]>(`/sessions?document_id=${docId}`),
    create: (body: object) =>
      request("/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    get: (id: string) => request(`/sessions/${id}`),
    next: (id: string) => request(`/sessions/${id}/next`),
    end: (id: string) => request(`/sessions/${id}/end`, { method: "POST" }),
    report: (id: string) => request(`/sessions/${id}/report`),
  },

  turns: {
    answer: (id: string, audio: Blob) => {
      const fd = new FormData();
      fd.append("audio", audio, "answer.webm");
      return request(`/turns/${id}/answer`, { method: "POST", body: fd });
    },
    answerText: (id: string, text: string) =>
      request(`/turns/${id}/answer-text`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }),
    get: (id: string) => request(`/turns/${id}`),
    skip: (id: string) => request(`/turns/${id}/skip`, { method: "POST" }),
    followUp: (id: string) => request(`/turns/${id}/follow-up`, { method: "POST" }),
    gradeStream: (id: string) => new EventSource(`${BASE}/turns/${id}/grade/stream`),
  },

  stats: {
    coverage: (docId: string) => request(`/stats/coverage?document_id=${docId}`),
    weakest: (docId: string, limit = 10) => request(`/stats/weakest?document_id=${docId}&limit=${limit}`),
    progress: (docId: string) => request(`/stats/progress?document_id=${docId}`),
  },

  plan: {
    get: (docId: string) => request(`/plan?document_id=${docId}`),
    patch: (id: string, body: object) =>
      request(`/plan/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  },
};
