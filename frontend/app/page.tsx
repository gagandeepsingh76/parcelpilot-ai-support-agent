"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ChatTurn,
  MOCK_SESSIONS,
  UiMessage,
  CallerInfo,
  credentialLogin,
  decideAction,
  login,
  sendChat,
} from "../lib/api";

type Receipt = Record<string, unknown> | null;

const ACCOUNT_TO_KEY: Record<string, string> = {
  "ACC-001": "cust-northstar",
  "ACC-002": "cust-lumenworks",
  "ACC-003": "cust-brightcart",
};
const ROLE_TO_KEY: Record<string, string> = {
  support_agent: "staff-agent",
  ops: "staff-ops",
  admin: "staff-admin",
  viewer: "staff-viewer",
};

const TOOL_LABELS: Record<string, string> = {
  data_lookup: "record lookup",
  search_documents: "policy search",
  stage_action: "action staged",
};

const CUSTOMER_SUGGESTIONS = [
  "Our order ORD-1001 arrived almost ten hours late - what compensation do we get?",
  "Why was I charged a cancellation fee for ORD-1006?",
  "What does my agreement say about pickup credits?",
];

const STAFF_SUGGESTIONS = [
  "Which open tickets have breached their SLA?",
  "Show me late pickups this week across accounts.",
  "Issue the pickup credit for order ORD-1003.",
];

export default function ChatPage() {
  const [token, setToken] = useState<string>("");
  const [sessionKey, setSessionKey] = useState<string>(MOCK_SESSIONS[0].key);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipts, setReceipts] = useState<Record<string, Receipt>>({});
  const [callerName, setCallerName] = useState("");
  const [authUser, setAuthUser] = useState("");
  const [authPass, setAuthPass] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem("pp_token");
    const savedSession = window.localStorage.getItem("pp_session");
    if (saved && savedSession) {
      setToken(saved);
      setSessionKey(savedSession);
    }
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, receipts]);

  const switchSession = useCallback(async (key: string) => {
    setSessionKey(key);
    try {
      const tok = await login(key);
      setToken(tok);
      setError(null);
      window.localStorage.setItem("pp_token", tok);
      window.localStorage.setItem("pp_session", key);
      setMessages([]);
      setReceipts({});
      setCallerName(
        MOCK_SESSIONS.find((s) => s.key === key)?.label.replace(/^.* - /, "") || ""
      );
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const signIn = useCallback(async () => {
    if (!authUser.trim() || !authPass || authBusy) return;
    setAuthBusy(true);
    setAuthError(null);
    try {
      const { token, caller } = await credentialLogin(authUser.trim(), authPass);
      const mapped =
        caller.kind === "customer"
          ? ACCOUNT_TO_KEY[caller.account_id ?? ""]
          : ROLE_TO_KEY[caller.role ?? ""];
      const key = mapped ?? sessionKey;
      setToken(token);
      setSessionKey(key);
      setCallerName(caller.display_name);
      setError(null);
      setMessages([]);
      setReceipts({});
      window.localStorage.setItem("pp_token", token);
      window.localStorage.setItem("pp_session", key);
      window.localStorage.setItem("pp_user", caller.display_name);
      setAuthPass("");
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
    } finally {
      setAuthBusy(false);
    }
  }, [authUser, authPass, authBusy, sessionKey]);

  const submit = useCallback(
    async (raw?: string) => {
      const text = (raw ?? input).trim();
      if (!text || !token || busy) return;
      const userMsg: UiMessage = { role: "user", content: text };
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setBusy(true);
      setError(null);
      try {
        const turn: ChatTurn = await sendChat(token, userMsg.content, history);
        setMessages((prev) => [...prev, { role: "assistant", content: turn.reply, ...turn }]);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [input, token, busy, messages]
  );

  const actOnPending = useCallback(
    async (pendingId: string, decision: "confirm" | "cancel") => {
      try {
        const receipt = await decideAction(token, pendingId, decision);
        setReceipts((prev) => ({ ...prev, [pendingId]: receipt }));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [token]
  );

  const isStaff = sessionKey.startsWith("staff");
  const activeSession = MOCK_SESSIONS.find((s) => s.key === sessionKey);
  const customerSessions = MOCK_SESSIONS.filter((s) => !s.key.startsWith("staff"));
  const staffSessions = MOCK_SESSIONS.filter((s) => s.key.startsWith("staff"));
  const suggestions = isStaff ? STAFF_SUGGESTIONS : CUSTOMER_SUGGESTIONS;

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="logo">
          Parcel<span>Pilot</span>
        </Link>
        <p className="tagline">AI support, grounded in your contracts.</p>

        <nav className="nav">
          <Link href="/" className="navlink active">
            Chat
          </Link>
          <Link href="/insights" className="navlink">
            Insights
          </Link>
        </nav>

        <div className="sessions">
          <h4>Customer portals</h4>
          {customerSessions.map((s) => (
            <button
              key={s.key}
              className={`session-card ${sessionKey === s.key ? "active" : ""}`}
              onClick={() => switchSession(s.key)}
            >
              <span className="session-dot" />
              {s.label.replace("Customer - ", "")}
            </button>
          ))}
          <h4>Internal console</h4>
          {staffSessions.map((s) => (
            <button
              key={s.key}
              className={`session-card staff ${sessionKey === s.key ? "active" : ""}`}
              onClick={() => switchSession(s.key)}
            >
              <span className="session-dot" />
              {s.label.replace("Internal - ", "")}
            </button>
          ))}
        </div>

        <footer className="sidefoot">
          Mock auth - access control enforced server-side on every tool call.
        </footer>
      </aside>

      <main className="main">
        {!token ? (
          <div className="hero">
            <div className="script">
              Parcel<span>Pilot</span>
            </div>
            <p className="sub">
              A B2B logistics support agent that answers from signed agreements,
              cites every source, and never applies a change without explicit
              confirmation.
            </p>
            <div className="feature-row">
              <span className="feature-pill">Cited answers only</span>
              <span className="feature-pill">Confirmation-gated actions</span>
              <span className="feature-pill">Role-scoped access</span>
              <span className="feature-pill">Internal insights</span>
            </div>

            <div className="signin-card">
              <div className="signin-title">Sign in</div>
              <div className="signin-row">
                <input
                  type="text"
                  placeholder="username"
                  value={authUser}
                  autoComplete="username"
                  onChange={(e) => setAuthUser(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && signIn()}
                />
                <input
                  type="password"
                  placeholder="password"
                  value={authPass}
                  autoComplete="current-password"
                  onChange={(e) => setAuthPass(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && signIn()}
                />
                <button className="send" onClick={signIn} disabled={authBusy || !authUser.trim() || !authPass}>
                  {authBusy ? "Signing in…" : "Sign in"}
                </button>
              </div>
              {authError && <div className="error-box" style={{ marginTop: 10 }}>{authError}</div>}
              <div className="signin-hint">
                Customers: northstar / demo1234 · Staff: agent / staff1234
              </div>
            </div>

            <p className="or-divider">or explore with one click</p>

            <div className="session-grid">
              {MOCK_SESSIONS.map((s) => (
                <button
                  key={s.key}
                  className={`pick-card ${s.key.startsWith("staff") ? "staff-pick" : ""}`}
                  onClick={() => switchSession(s.key)}
                >
                  <div className="who">{s.label.split(" - ")[1]}</div>
                  <div className="what">{s.label.split(" - ")[0]} session</div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            <header className="chatbar">
              <div>
                <div className="chat-title">{callerName || activeSession?.label}</div>
                <div className="chat-sub">
                  {isStaff
                    ? "Cross-account tools with scope limits"
                    : "You can only see your own records"}
                </div>
              </div>
              <span className={`pill ${isStaff ? "internal" : "customer"}`}>
                {isStaff ? "INTERNAL" : "CUSTOMER"}
              </span>
            </header>

            <div className="thread-wrap">
              <div className="messages" ref={listRef}>
                <div className="thread">
                  {messages.length === 0 && (
                    <div className="empty-state">
                      <div className="script">How can we help?</div>
                      <p>
                        Ask about orders, contract terms, service credits or SLAs -
                        every answer comes with citations.
                      </p>
                      <div className="suggestions">
                        {suggestions.map((s) => (
                          <button key={s} className="suggestion-chip" onClick={() => submit(s)}>
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {messages.map((m, i) => (
                    <div key={i} className="msg">
                      <div className={m.role === "user" ? "bubble-user" : "bubble-assistant"}>
                        {m.content}

                        {"tools_used" in m && m.tools_used && m.tools_used.length > 0 && (
                          <div className="meta-row">
                            {m.tools_used.map((t, j) => (
                              <span
                                key={j}
                                className="badge tool"
                                title={JSON.stringify(t.input)}
                              >
                                {TOOL_LABELS[t.tool] ?? t.tool}
                              </span>
                            ))}
                          </div>
                        )}

                        {m.escalated && (
                          <div className="escalation-banner">
                            Escalated to a human agent - this needs manual review.
                          </div>
                        )}

                        {m.conflicts && m.conflicts.length > 0 && (
                          <div className="conflict-banner">
                            <strong>Sources differ.</strong>{" "}
                            {m.conflicts.map((c, i) => (
                              <span key={i}>
                                {c.kind === "agreement_vs_general_policy"
                                  ? "The customer's signed agreement governs over general policy. "
                                  : c.kind === "current_vs_deprecated"
                                    ? "CURRENT documents supersede DEPRECATED ones. "
                                    : `${c.governs}. `}
                              </span>
                            ))}
                            Both positions are shown in the sources below.
                          </div>
                        )}

                        {m.pending_actions?.map((pa) => {
                          const receipt = receipts[pa.pending_action_id];
                          return (
                            <div key={pa.pending_action_id} className="pending-card">
                              <div className="pc-head">
                                Pending action
                                <span className="pc-id">{pa.pending_action_id}</span>
                              </div>
                              <div className="pc-summary">{pa.summary}</div>
                              {!receipt ? (
                                <div className="actions">
                                  <button
                                    className="confirm"
                                    onClick={() =>
                                      actOnPending(pa.pending_action_id, "confirm")
                                    }
                                  >
                                    Confirm &amp; apply
                                  </button>
                                  <button
                                    className="cancel"
                                    onClick={() =>
                                      actOnPending(pa.pending_action_id, "cancel")
                                    }
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <div className="receipt">
                                  Applied:{" "}
                                  {JSON.stringify(
                                    receipt.created ?? receipt.updated ?? receipt
                                  ).slice(0, 160)}
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {m.citations && m.citations.length > 0 && (
                          <div className="citations">
                            <div className="cite-label">Sources</div>
                            <ul>
                              {m.citations.map((c, j) => (
                                <li key={j}>
                                  <span
                                    className={`doc-chip ${
                                      c.status === "DEPRECATED" ? "deprecated" : ""
                                    }`}
                                  >
                                    [{c.doc_id}]
                                  </span>
                                  <span>
                                    {c.title} — {c.section}{" "}
                                    <span className="mono">
                                      ({c.doc_type}, {c.customer_scope})
                                    </span>
                                  </span>
                                  {c.status === "DEPRECATED" && (
                                    <span className="badge warn">DEPRECATED - superseded</span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {busy && (
                    <div className="msg">
                      <div className="bubble-assistant" style={{ maxWidth: 90 }}>
                        <span className="typing">
                          <i />
                          <i />
                          <i />
                        </span>
                      </div>
                    </div>
                  )}

                  {error && <div className="error-box">{error}</div>}
                </div>
              </div>

              <div className="composer">
                <div className="composer-inner">
                  <input
                    type="text"
                    placeholder={
                      token ? "Ask about orders, policies, credits…" : "Pick a session first"
                    }
                    value={input}
                    disabled={!token || busy}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && submit()}
                  />
                  <button
                    className="send"
                    onClick={() => submit()}
                    disabled={!token || busy || !input.trim()}
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
