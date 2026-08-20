/* API client for FloorMind backend with JWT auth and SSE support. */

import type { SSEEvent } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

let _token: string | null = null;

export function setToken(token: string) {
  _token = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("fm_token", token);
  }
}

export function getToken(): string | null {
  if (_token) return _token;
  if (typeof window !== "undefined") {
    _token = localStorage.getItem("fm_token");
  }
  return _token;
}

export function clearToken() {
  _token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("fm_token");
  }
}

// ---------------------------------------------------------------------------
// Fetch wrapper with auth
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function login(
  username: string,
  password: string
): Promise<{ access_token: string }> {
  const data = await apiFetch<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  return apiFetch<{ username: string; role: string }>("/api/auth/me");
}

// ---------------------------------------------------------------------------
// Chat API (SSE streaming)
// ---------------------------------------------------------------------------

export async function chatStream(
  message: string,
  history: { role: string; content: string }[],
  onToken: (token: string) => void,
  onResult?: (result: SSEEvent) => void,
  onDone?: () => void
): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ message, history, stream: true }),
  });

  if (!res.ok) throw new Error(`Chat error: ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") {
        onDone?.();
        return;
      }
      try {
        const event: SSEEvent = JSON.parse(payload);
        if (event.type === "token" && event.token) {
          onToken(event.token);
        } else if (event.type === "result") {
          onResult?.(event);
        }
      } catch {
        // skip malformed lines
      }
    }
  }
  onDone?.();
}

// ---------------------------------------------------------------------------
// Chat API (non-streaming)
// ---------------------------------------------------------------------------

export async function chatSync(message: string, history: { role: string; content: string }[]) {
  return apiFetch<{
    explanation: string;
    sql?: string;
    data?: Record<string, unknown>[];
    error: boolean;
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, stream: false }),
  });
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function getDashboardStats() {
  return apiFetch<{
    production_runs_7d: number;
    waste_kg_7d: number;
    waste_cost_7d: number;
    pending_orders: number;
  }>("/api/dashboard/stats");
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export async function getAlerts() {
  return apiFetch<
    { level: string; icon: string; title: string; message: string; category: string }[]
  >("/api/alerts");
}

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------

export async function getComplianceScores() {
  return apiFetch<{ scores: Record<string, number> }>("/api/compliance/scores");
}

export async function traceBatch(batchCode: string) {
  return apiFetch<{
    batch_code: string;
    raw_materials: Record<string, unknown>[];
    production: Record<string, unknown>[];
    orders: Record<string, unknown>[];
  }>(`/api/compliance/trace/${encodeURIComponent(batchCode)}`);
}

export async function getAllergens() {
  return apiFetch<{ product: string; allergens: string }[]>("/api/compliance/allergens");
}

export async function getTemperatureExcursions(days = 7) {
  return apiFetch<
    { location: string; reading_time: string; temp_celsius: number; in_range: boolean }[]
  >(`/api/compliance/temperature?days=${days}`);
}

// ---------------------------------------------------------------------------
// Waste
// ---------------------------------------------------------------------------

export async function getWasteSummary(days = 7) {
  return apiFetch<{ waste_type: string; total_kg: number; total_cost: number }[]>(
    `/api/waste/summary?days=${days}`
  );
}

export async function getYieldByProduct(days = 30) {
  return apiFetch<{ product: string; avg_yield: number; waste_cost_gbp: number }[]>(
    `/api/waste/yield?days=${days}`
  );
}

export async function predictWaste(product: string, inputKg: number) {
  return apiFetch<{
    product: string;
    input_kg: number;
    expected_output_kg: number;
    expected_waste_kg: number;
    expected_yield_pct: number;
  } | null>(`/api/waste/predict?product=${encodeURIComponent(product)}&input_kg=${inputKg}`);
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function uploadDocument(file: File) {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json() as Promise<{ filename: string; chunk_count: number }>;
}

export async function searchDocuments(query: string, topK = 5) {
  const token = getToken();
  const formData = new FormData();
  formData.append("query", query);
  formData.append("top_k", String(topK));

  const res = await fetch(`${API_BASE}/api/documents/search`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json() as Promise<
    { text: string; score: number; source: string; category: string }[]
  >;
}

export async function getDocumentCount() {
  return apiFetch<{ count: number }>("/api/documents/count");
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export async function getAuditEvents(limit = 50) {
  return apiFetch<{ event_type: string; timestamp?: string; fields: Record<string, unknown> }[]>(
    `/api/audit/events?limit=${limit}`
  );
}
