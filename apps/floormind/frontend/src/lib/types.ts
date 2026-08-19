/* TypeScript types matching the FloorMind API schemas. */

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserInfo {
  username: string;
  role: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error?: boolean;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  stream: boolean;
}

export interface ChatResponse {
  explanation: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error: boolean;
}

export interface SSEEvent {
  type: "start" | "token" | "done" | "result";
  token?: string;
  explanation?: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error?: boolean;
}

export interface DashboardStats {
  production_runs_7d: number;
  waste_kg_7d: number;
  waste_cost_7d: number;
  pending_orders: number;
}

export interface Alert {
  level: "critical" | "warning" | "info";
  icon: string;
  title: string;
  message: string;
  category: string;
}

export interface ComplianceScores {
  scores: Record<string, number>;
}

export interface BatchTrace {
  batch_code: string;
  raw_materials: Record<string, unknown>[];
  production: Record<string, unknown>[];
  orders: Record<string, unknown>[];
}

export interface AllergenRow {
  product: string;
  allergens: string;
}

export interface TemperatureReading {
  location: string;
  reading_time: string;
  temp_celsius: number;
  in_range: boolean;
  recorded_by: string;
}

export interface WasteSummary {
  waste_type: string;
  total_kg: number;
  total_cost: number;
}

export interface YieldByProduct {
  product: string;
  avg_yield: number;
  waste_cost_gbp: number;
}

export interface WastePrediction {
  product: string;
  input_kg: number;
  expected_output_kg: number;
  expected_waste_kg: number;
  expected_yield_pct: number;
}

export interface DocumentUploadResponse {
  filename: string;
  chunk_count: number;
}

export interface DocumentSearchResult {
  text: string;
  score: number;
  source: string;
  category: string;
  page?: number;
}

export interface DocumentCount {
  count: number;
}

export interface AuditEvent {
  event_type: string;
  timestamp?: string;
  fields: Record<string, unknown>;
}
