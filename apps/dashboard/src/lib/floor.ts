/* Merged FloorMind client for the Governed Agent Stack dashboard.
   All calls go through the server-side /api/floorapi proxy, so the
   browser never hits FloorMind's API directly and CORS is not in play. */

import type { SSEEvent } from "./types";

const API_BASE = "/api/floorapi";

// ---------------------------------------------------------------------------
// Auth helpers (dev-mode aware)
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

export async function isDevMode(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.username === "dev" || data.role === "admin";
  } catch {
    return false;
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
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
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- lib code without router access
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function login(
  username: string,
  password: string
): Promise<{ access_token: string }> {
  const data = await apiFetch<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  return apiFetch<{ username: string; role: string }>("/auth/me");
}

// ---------------------------------------------------------------------------
// Chat (SSE streaming)
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

  const res = await fetch(`${API_BASE}/chat`, {
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

export async function chatSync(
  message: string,
  history: { role: string; content: string }[]
) {
  return apiFetch<{
    explanation: string;
    sql?: string;
    data?: Record<string, unknown>[];
    error: boolean;
  }>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, stream: false }),
  });
}

// ---------------------------------------------------------------------------
// Factory dashboard
// ---------------------------------------------------------------------------

export async function getDashboardStats() {
  return apiFetch<{
    production_runs_7d: number;
    waste_kg_7d: number;
    waste_cost_7d: number;
    pending_orders: number;
  }>("/dashboard/stats");
}

export async function getAlerts() {
  return apiFetch<
    { level: string; icon: string; title: string; message: string; category: string }[]
  >("/alerts");
}

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------

export async function getComplianceScores() {
  return apiFetch<{ scores: Record<string, number> }>("/compliance/scores");
}

export async function traceBatch(batchCode: string) {
  return apiFetch<{
    batch_code: string;
    raw_materials: Record<string, unknown>[];
    production: Record<string, unknown>[];
    orders: Record<string, unknown>[];
  }>(`/compliance/trace/${encodeURIComponent(batchCode)}`);
}

export async function getAllergens() {
  return apiFetch<{ product: string; allergens: string }[]>("/compliance/allergens");
}

export async function getTemperatureExcursions(days = 7) {
  return apiFetch<
    { location: string; reading_time: string; temp_celsius: number; in_range: boolean }[]
  >(`/compliance/temperature?days=${days}`);
}

// ---------------------------------------------------------------------------
// Waste
// ---------------------------------------------------------------------------

export async function getWasteSummary(days = 7) {
  return apiFetch<{ waste_type: string; total_kg: number; total_cost: number }[]>(
    `/waste/summary?days=${days}`
  );
}

export async function getYieldByProduct(days = 30) {
  return apiFetch<{ product: string; avg_yield: number; waste_cost_gbp: number }[]>(
    `/waste/yield?days=${days}`
  );
}

export async function predictWaste(product: string, inputKg: number) {
  return apiFetch<{
    product: string;
    input_kg: number;
    expected_output_kg: number;
    expected_waste_kg: number;
    expected_yield_pct: number;
  } | null>(`/waste/predict?product=${encodeURIComponent(product)}&input_kg=${inputKg}`);
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function uploadDocument(file: File) {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
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

  const res = await fetch(`${API_BASE}/documents/search`, {
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
  return apiFetch<{ count: number }>("/documents/count");
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export async function getAuditEvents(limit = 50) {
  return apiFetch<{ event_type: string; timestamp?: string; fields: Record<string, unknown> }[]>(
    `/audit/events?limit=${limit}`
  );
}