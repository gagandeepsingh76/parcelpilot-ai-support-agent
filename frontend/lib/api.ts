export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export interface Citation {
  doc_id: string;
  title: string;
  section?: string;
  heading?: string;
  status: string;
  doc_type: string;
  customer_scope: string;
  version?: string;
  filename?: string;
}

export interface PendingAction {
  pending_action_id: string;
  summary: string;
  changes?: Record<string, any>;
  affects?: {
    table?: string;
    record_id?: string;
    account_id?: string;
    linked_order_id?: string;
    linked_ticket_id?: string;
    new_record?: boolean;
  };
  action_type?: string;
  created_at?: string;
  status?: string;
}

export interface ToolUsed {
  tool: string;
  input: Record<string, any>;
  output?: Record<string, any> | string;
  status?: "success" | "error";
  label?: string;
}

export interface ChatTurn {
  reply: string;
  tools_used: ToolUsed[];
  citations: Citation[];
  conflicts: { kind: string; governs: string; sources: Citation[] }[];
  pending_actions: PendingAction[];
  escalated: boolean;
}

export interface UiMessage extends Partial<ChatTurn> {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface MockSessionSpec {
  key: string;
  label: string;
  company: string;
  kind: "customer" | "internal";
  role?: string;
  accountId?: string;
  description: string;
  badge: string;
}

export const MOCK_SESSIONS: MockSessionSpec[] = [
  {
    key: "cust-northstar",
    label: "Customer — Northstar Logistics",
    company: "Northstar Logistics",
    kind: "customer",
    accountId: "ACC-001",
    description: "Enterprise tier with signed agreement ($75 flat cancellation fee, 4h delivery compensation clause)",
    badge: "Enterprise (ACC-001)",
  },
  {
    key: "cust-lumenworks",
    label: "Customer — LumenWorks Ltd",
    company: "LumenWorks Ltd",
    kind: "customer",
    accountId: "ACC-002",
    description: "Mid-market tier ($50 late pickup credit, cancellation min of $100 / 20%)",
    badge: "Mid-Market (ACC-002)",
  },
  {
    key: "cust-brightcart",
    label: "Customer — BrightCart Commerce",
    company: "BrightCart Commerce",
    kind: "customer",
    accountId: "ACC-003",
    description: "Standard policy tier ($25 pickup credit, standard cancellation rules)",
    badge: "Standard (ACC-003)",
  },
  {
    key: "staff-agent",
    label: "Internal — Support Agent (Avery)",
    company: "ParcelPilot Operations",
    kind: "internal",
    role: "support_agent",
    description: "Can investigate across all accounts, look up past context, and stage escalations/updates",
    badge: "Support Agent",
  },
  {
    key: "staff-ops",
    label: "Internal — Operations Manager (Priya)",
    company: "ParcelPilot Operations",
    kind: "internal",
    role: "ops",
    description: "Full operations monitoring, SLA oversight, proactive issue resolution & action staging",
    badge: "Ops Manager",
  },
  {
    key: "staff-admin",
    label: "Internal — Administrator (Root)",
    company: "ParcelPilot IT",
    kind: "internal",
    role: "admin",
    description: "Full system administration and configuration",
    badge: "Admin",
  },
  {
    key: "staff-viewer",
    label: "Internal — Read-Only Viewer (Intern)",
    company: "ParcelPilot Operations",
    kind: "internal",
    role: "viewer",
    description: "Internal read-only access — cannot stage state-changing actions",
    badge: "Viewer (Read-Only)",
  },
];

export interface CallerInfo {
  kind: "customer" | "internal";
  display_name: string;
  account_id?: string | null;
  role?: string | null;
  session_id: string;
}

export interface SystemAccount {
  account_id: string;
  account_name: string;
  tier?: string;
  good_standing: boolean;
}

export interface KnowledgeDocument {
  doc_id: string;
  filename: string;
  title: string;
  version?: string;
  status: "CURRENT" | "DEPRECATED";
  doc_type: string;
  customer_scope: string;
  page_count: number;
  sections?: { seq: number; level: number; heading: string }[];
}

export interface SystemMetadata {
  app_name: string;
  snapshot_utc: string;
  accounts: SystemAccount[];
  documents: KnowledgeDocument[];
}

export interface RecordsSummary {
  kind: "customer" | "internal";
  account_id?: string;
  role?: string;
  orders_count?: number;
  tickets_count?: number;
  open_tickets_count?: number;
  total_accounts?: number;
  total_orders?: number;
  total_tickets?: number;
  recent_orders?: any[];
  recent_tickets?: any[];
}

/**
 * Robust fetch wrapper that catches network/CORS failures and translates them
 * into clean, user-friendly error messages rather than raw "Failed to fetch".
 */
async function safeFetch(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (err: any) {
    if (err.name === "AbortError" || init?.signal?.aborted) {
      throw err;
    }
    throw new Error(
      `Unable to connect to ParcelPilot backend (${API_BASE}). Please check your connection and ensure the backend server is running.`
    );
  }
}

/**
 * Parses HTTP error response details and maps them to appropriate user messages.
 */
async function parseErrorResponse(res: Response, fallbackPrefix: string): Promise<Error> {
  let detail = "";
  try {
    const json = await res.json();
    detail = json.detail || JSON.stringify(json);
  } catch {
    detail = await res.text().catch(() => "");
  }

  const normalized = (detail || "").toLowerCase();

  if (
    res.status === 429 ||
    normalized.includes("429") ||
    normalized.includes("quota") ||
    normalized.includes("resource_exhausted")
  ) {
    return new Error(
      "AI service is temporarily unavailable because the current API quota has been exhausted. Please try again later."
    );
  }

  if (res.status === 401 || res.status === 403) {
    return new Error(detail || "Access denied or session expired. Please sign in again.");
  }

  if (res.status === 503 || normalized.includes("503") || normalized.includes("service unavailable")) {
    return new Error(detail || "AI service is temporarily unavailable. Please try again later.");
  }

  return new Error(detail || `${fallbackPrefix} (status ${res.status})`);
}

export async function login(sessionKey: string): Promise<string> {
  const res = await safeFetch(`${API_BASE}/api/session/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_key: sessionKey }),
  });
  if (!res.ok) throw await parseErrorResponse(res, "Session login failed");
  const body = await res.json();
  return body.token as string;
}

export async function fetchMe(token: string): Promise<CallerInfo> {
  const res = await safeFetch(`${API_BASE}/api/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw await parseErrorResponse(res, "Failed to load user profile");
  return res.json();
}

export async function credentialLogin(
  username: string,
  password: string
): Promise<{ token: string; caller: CallerInfo }> {
  const res = await safeFetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw await parseErrorResponse(res, "Sign-in failed");
  return res.json();
}

export async function sendChat(
  token: string,
  message: string,
  history: { role: string; content: string }[],
  signal?: AbortSignal
): Promise<ChatTurn> {
  const res = await safeFetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message, history }),
    signal,
  });
  if (!res.ok) throw await parseErrorResponse(res, "Chat request failed");
  return res.json();
}

export async function decideAction(
  token: string,
  pendingId: string,
  decision: "confirm" | "cancel"
): Promise<Record<string, unknown>> {
  const res = await safeFetch(`${API_BASE}/api/actions/${pendingId}/${decision}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw await parseErrorResponse(res, `${decision} action failed`);
  return res.json();
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
    governing_source?: { doc_id?: string; title?: string; note?: string };
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
  const res = await safeFetch(`${API_BASE}/api/insights/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw await parseErrorResponse(res, "Insights fetch failed");
  return res.json();
}

export async function fetchMetadata(): Promise<SystemMetadata> {
  const res = await safeFetch(`${API_BASE}/api/metadata`);
  if (!res.ok) throw await parseErrorResponse(res, "Metadata fetch failed");
  return res.json();
}

export async function fetchDocuments(): Promise<KnowledgeDocument[]> {
  const res = await safeFetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw await parseErrorResponse(res, "Documents fetch failed");
  return res.json();
}

export async function fetchRecordsSummary(token: string): Promise<RecordsSummary> {
  const res = await safeFetch(`${API_BASE}/api/records/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw await parseErrorResponse(res, "Records summary fetch failed");
  return res.json();
}
