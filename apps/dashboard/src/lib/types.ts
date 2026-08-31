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

export interface SSEEvent {
  type: "start" | "token" | "done" | "result";
  token?: string;
  explanation?: string;
  sql?: string;
  data?: Record<string, unknown>[];
  error?: boolean;
}