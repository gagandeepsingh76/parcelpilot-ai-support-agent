export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Citation {
  doc_id: string;
  title: string;
  section: string;
  status: string;
  doc_type: string;
  customer_scope: string;
}

export interface PendingAction {
  pending_action_id: string;
  summary: string;
  changes?: unknown;
}

export interface ChatTurn {
  reply: string;
  tools_used: { tool: string; input: Record<string, unknown> }[];
  citations: Citation[];
  conflicts: { kind: string; governs: string; sources: Citation[] }[];
  pending_actions: PendingAction[];
  escalated: boolean;
}

export interface UiMessage extends Partial<ChatTurn> {
  role: "user" | "assistant";
  content: string;
}

const MOCK_SESSIONS = [
  { key: "cust-northstar", label: "Customer - Northstar Logistics" },
  { key: "cust-lumenworks", label: "Customer - LumenWorks Ltd" },
  { key: "cust-brightcart", label: "Customer - BrightCart Commerce" },
  { key: "staff-agent", label: "Internal - Support agent" },
  { key: "staff-ops", label: "Internal - Ops" },
  { key: "staff-viewer", label: "Internal - Viewer (read-only)" },
];

export interface CallerInfo {
  kind: "customer" | "internal";
  display_name: string;
  account_id?: string | null;
  role?: string | null;
  session_id: string;
}

export async function login(sessionKey: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/session/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_key: sessionKey }),
  });
  if (!res.ok) throw new Error(`login failed (${res.status})`);
  const body = await res.json();
  return body.token as string;
}

/** Resolve the caller behind a token (works for mock and signed tokens). */
export async function fetchMe(token: string): Promise<CallerInfo> {
  const res = await fetch(`${API_BASE}/api/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`me failed (${res.status})`);
  return res.json();
}

/** Username/password sign-in for both customer and staff accounts. */
export async function credentialLogin(
  username: string,
  password: string
): Promise<{ token: string; caller: CallerInfo }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || `sign-in failed (${res.status})`);
  return body;
}

export async function sendChat(
  token: string,
  message: string,
  history: { role: string; content: string }[]
): Promise<ChatTurn> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`chat failed (${res.status}): ${detail.slice(0, 200)}`);
  }
  return res.json();
}

export async function decideAction(
  token: string,
  pendingId: string,
  decision: "confirm" | "cancel"
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/actions/${pendingId}/${decision}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || `${decision} failed (${res.status})`);
  return body;
}

export interface InsightsReport {
  generated_at: string;
  ticket_volume: {
    totals: { this_week: number; prev_week: number };
    by_category: { category: string; count: number }[];
    spikes: {
      account_id: string;
      account_name: string;
      this_week: number;
      prev_week: number;
      top_categories: { category: string; count: number }[];
    }[];
  };
  sla_watchlist: {
    ticket_id: string;
    account_name: string;
    subject: string | null;
    priority: string;
    created_at: string;
    problems: string[];
  }[];
  service_quality: {
    window_days: number;
    late_pickup_count: number;
    late_pickups: { order_id: string; delay_minutes: number }[];
    late_delivery_count: number;
    late_deliveries: { order_id: string; delay_minutes: number | null; delay_hours?: number | null; note?: string }[];
    orders_in_flight: number;
  };
  credit_exposure: {
    claimable_now_usd_by_account: Record<string, number>;
    total_claimable_usd: number;
    manual_review: { kind: string; order_id: string; basis: string | null }[];
    basis: string;
  };
  cross_customer_patterns: {
    category: string;
    accounts_affected: number;
    shared_keywords: string[];
    hint: string;
  }[];
}

export async function fetchInsights(token: string): Promise<InsightsReport> {
  const res = await fetch(`${API_BASE}/api/insights/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`insights failed (${res.status})`);
  return res.json();
}

export { MOCK_SESSIONS };
