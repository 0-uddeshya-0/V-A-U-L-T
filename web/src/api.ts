import type {
  Contradiction,
  Gap,
  HealthStatus,
  IngestResponse,
  IngestStatus,
  QuarantineUnit,
  QueryResult,
} from "./types";

const STORAGE_KEY = "vault_api_base";

export function getApiBase(): string {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) return stored.replace(/\/$/, "");
  const env = import.meta.env.VITE_API_URL;
  if (env) return String(env).replace(/\/$/, "");
  return "";
}

export function setApiBase(url: string): void {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/$/, ""));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getApiBase();
  const url = `${base}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export async function queryKnowledge(task: string, limit = 10): Promise<QueryResult[]> {
  return request<QueryResult[]>("/query", {
    method: "POST",
    body: JSON.stringify({ task, limit }),
  });
}

export async function ingestUrl(url: string, sync = true): Promise<IngestResponse> {
  return request<IngestResponse>(`/ingest?sync=${sync}`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function getIngestStatus(workflowId: string): Promise<IngestStatus> {
  return request<IngestStatus>(`/ingest/${encodeURIComponent(workflowId)}`);
}

export async function listQuarantine(): Promise<QuarantineUnit[]> {
  return request<QuarantineUnit[]>("/api/quarantine");
}

export async function approveUnit(id: string): Promise<{ ok: boolean }> {
  return request(`/api/quarantine/${id}/approve`, { method: "POST" });
}

export async function rejectUnit(id: string): Promise<{ ok: boolean }> {
  return request(`/api/quarantine/${id}/reject`, { method: "POST" });
}

export async function listGaps(): Promise<Gap[]> {
  return request<Gap[]>("/gaps");
}

export async function listContradictions(concept?: string): Promise<Contradiction[]> {
  const q = concept ? `?concept=${encodeURIComponent(concept)}` : "";
  return request<Contradiction[]>(`/api/contradictions${q}`);
}
