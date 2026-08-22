"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ChatTurn,
  MOCK_SESSIONS,
  UiMessage,
  decideAction,
  login,
  sendChat,
} from "../lib/api";

type Receipt = Record<string, unknown> | null;

export default function ChatPage() {
  const [token, setToken] = useState<string>("");
  const [sessionKey, setSessionKey] = useState<string>(MOCK_SESSIONS[0].key);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipts, setReceipts] = useState<Record<string, Receipt>>({});
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
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const submit = useCallback(async () => {
    if (!input.trim() || !token || busy) return;
    const userMsg: UiMessage = { role: "user", content: input.trim() };
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
  }, [input, token, busy, messages]);

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

  return (
    <div className="container">
      <header className="topbar">
        <span className="brand">
          <Link href="/">ParcelPilot Agent</Link>
          <Link href="/insights">Insights</Link>
        </span>
        <span className="spacer" />
        <select
          value={sessionKey}
          onChange={(e) => switchSession(e.target.value)}
          aria-label="Mock login"
        >
          {MOCK_SESSIONS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
      </header>

      {!token && (
        <p className="hint">
          Pick a mock session above to start. Customer sessions see only their own
          records; internal roles get cross-account tools with scope limits.
        </p>
      )}

      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
          <p className="hint">
            Try: &quot;Our order ORD-1001 was delivered very late - what compensation do we
            get?&quot; or &quot;Why was I charged a cancellation fee for ORD-1006?&quot;
            {token?.includes("staff") && " As staff you can also ask for escalations."}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
            {"tools_used" in m && m.tools_used && m.tools_used.length > 0 && (
              <div className="meta-row">
                {m.tools_used.map((t, j) => (
                  <span key={j} className="badge tool" title={JSON.stringify(t.input)}>
                    tool: {t.tool}
                  </span>
                ))}
                {m.escalated && <span className="badge esc">escalated to human</span>}
              </div>
            )}
            {m.conflicts && m.conflicts.length > 0 && (
              <div className="conflict-banner">
                Note: sources differ -{" "}
                {m.conflicts.map((c) => c.governs).join("; ")}. Both are shown in the
                citations.
              </div>
            )}
            {m.pending_actions?.map((pa) => {
              const receipt = receipts[pa.pending_action_id];
              return (
                <div key={pa.pending_action_id} className="pending-card">
                  <strong>Pending action</strong>
                  <div>{pa.summary}</div>
                  {!receipt ? (
                    <div className="actions">
                      <button className="confirm" onClick={() => actOnPending(pa.pending_action_id, "confirm")}>
                        Confirm &amp; apply
                      </button>
                      <button className="cancel" onClick={() => actOnPending(pa.pending_action_id, "cancel")}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="receipt">
                      Applied: {JSON.stringify(receipt.created ?? receipt.updated ?? receipt)}
                    </div>
                  )}
                </div>
              );
            })}
            {m.citations && m.citations.length > 0 && (
              <div className="citations">
                Sources:
                <ul>
                  {m.citations.map((c, j) => (
                    <li key={j}>
                      [{c.doc_id}] {c.title} — {c.section} ({c.status}, {c.customer_scope})
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant">thinking…</div>}
        {error && <div className="error-box">{error}</div>}
      </div>

      <div className="composer">
        <input
          type="text"
          placeholder={token ? "Ask about orders, policies, credits…" : "Log in first"}
          value={input}
          disabled={!token || busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <button className="primary" onClick={submit} disabled={!token || busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
