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

export { MOCK_SESSIONS };
