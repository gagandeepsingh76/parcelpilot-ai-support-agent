"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChatTurn,
  MOCK_SESSIONS,
  UiMessage,
  decideAction,
  sendChat,
} from "../lib/api";
import LoginScreen, { AppSession } from "../components/LoginScreen";
import Markdown from "../components/Markdown";
import AppShell from "../components/AppShell";
import ToolActivityTimeline from "../components/chat/ToolActivityTimeline";
import SourceEvidenceCard from "../components/chat/SourceEvidenceCard";
import ConflictBanner from "../components/chat/ConflictBanner";
import ActionConfirmationCard from "../components/chat/ActionConfirmationCard";
import EscalationNotice from "../components/chat/EscalationNotice";
import { Sparkles, Shield, ArrowRight, AlertCircle, Send, Square, RotateCcw } from "lucide-react";

type Receipt = Record<string, any> | null;

const CUSTOMER_SUGGESTIONS = [
  "Can I cancel ORD-1001 without paying a cancellation fee?",
  "Why was our order ORD-1006 charged an $80 cancellation fee?",
  "Our order ORD-1001 was 10 hours late — what service credit or compensation do we get?",
  "What does our signed agreement say about late delivery and cancellation rules?",
  "Can you show me the status of LumenWorks order ORD-1026?",
];

const STAFF_SUGGESTIONS = [
  "Which open tickets are currently breaching or approaching their SLA deadline?",
  "Check late pickup service credit eligibility for SwiftMed order ORD-1003.",
  "Check cancellation fee for Northstar order ORD-1001 vs standard policy.",
  "Look up past resolved tickets for ACC-001 regarding late pickups.",
  "Stage a P1 human escalation for order ORD-1001 due to carrier delay.",
];

export default function ChatPage() {
  const [session, setSession] = useState<AppSession | null>(null);
  const [booted, setBooted] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipts, setReceipts] = useState<Record<string, Receipt>>({});
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      const token = sessionStorage.getItem("pp_token");
      if (token) {
        setSession({
          token,
          callerName: sessionStorage.getItem("pp_user") || "",
          kind: sessionStorage.getItem("pp_kind") || "customer",
          sessionKey: sessionStorage.getItem("pp_session") || "cust-northstar",
        });
      }
    } finally {
      setBooted(true);
    }
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, receipts, busy]);

  useEffect(() => {
    if (!booted || !session) return;
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("prompt");
      if (q) {
        setInput(q);
        window.history.replaceState({}, "", "/");
      }
    } catch {}
  }, [booted, session]);

  const onSignedIn = useCallback((s: AppSession) => {
    sessionStorage.setItem("pp_token", s.token);
    sessionStorage.setItem("pp_user", s.callerName);
    sessionStorage.setItem("pp_kind", s.kind);
    sessionStorage.setItem("pp_session", s.sessionKey);
    setSession(s);
    setMessages([]);
    setReceipts({});
    setError(null);
  }, []);

  const signOut = useCallback(() => {
    ["pp_token", "pp_user", "pp_kind", "pp_session"].forEach((k) =>
      sessionStorage.removeItem(k)
    );
    setSession(null);
    setMessages([]);
    setReceipts({});
    setInput("");
    setError(null);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setReceipts({});
    setError(null);
  }, []);

  const cancelChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setBusy(false);
      setError("Request cancelled.");
    }
  }, []);

  const submit = useCallback(
    async (raw?: string) => {
      const text = (raw ?? input).trim();
      if (!text || !session || busy) return;
      const nowIso = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const userMsg: UiMessage = { role: "user", content: text, timestamp: nowIso };
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setBusy(true);
      setError(null);
      const controller = new AbortController();
      abortControllerRef.current = controller;
      try {
        const turn: ChatTurn = await sendChat(session.token, userMsg.content, history, controller.signal);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: turn.reply,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            ...turn,
          },
        ]);
      } catch (e: any) {
        if (e.name === 'AbortError') return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
          setBusy(false);
        }
      }
    },
    [input, session, busy, messages]
  );

  const actOnPending = useCallback(
    async (pendingId: string, decision: "confirm" | "cancel") => {
      if (!session) return;
      try {
        const receipt = await decideAction(session.token, pendingId, decision);
        setReceipts((prev) => ({ ...prev, [pendingId]: receipt }));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [session]
  );

  if (!booted) return null;
  if (!session) return <LoginScreen existing={null} onSignedIn={onSignedIn} />;

  const isStaff = session.kind === "internal";
  const activeSessionSpec = MOCK_SESSIONS.find((s) => s.key === session.sessionKey);
  const suggestions = isStaff ? STAFF_SUGGESTIONS : CUSTOMER_SUGGESTIONS;

  return (
    <AppShell
      session={session}
      onSwitchSession={onSignedIn}
      onSignOut={signOut}
    >
      <main className="chat-main-container">
        {/* Chat Header */}
        <header className="chatbar">
          <div className="chatbar-left">
            <div className="chatbar-title-wrap">
              <h2 className="chat-title">
                {session.callerName || activeSessionSpec?.label || "AI Support Console"}
              </h2>
              <span className={`pill-badge ${isStaff ? "staff" : "customer"}`}>
                {isStaff ? (activeSessionSpec?.badge || "INTERNAL") : (activeSessionSpec?.badge || "CUSTOMER")}
              </span>
            </div>
            <div className="chat-sub">
              {isStaff
                ? "Cross-account operational copilot with tiered authority RAG and confirmation gating"
                : `Account Scoped (${activeSessionSpec?.accountId || "Own Account"}) · Strictly filtered in data layer`}
            </div>
          </div>

          <div className="chatbar-right">
            <button
              type="button"
              className="ghost-btn"
              onClick={clearChat}
              title="Clear current conversation"
            >
              Clear Conversation
            </button>
          </div>
        </header>

        {/* Chat Thread */}
        <div className="thread-wrap">
          <div className="messages" ref={listRef}>
            <div className="thread">
              {/* Empty / Welcome State */}
              {messages.length === 0 && (
                <div className="welcome-state-card">
                  <div className="welcome-icon-glow">
                    <Sparkles size={32} strokeWidth={1.5} aria-hidden="true" className="welcome-sparkle" />
                  </div>
                  <h3 className="welcome-title">
                    {isStaff
                      ? `Welcome to ParcelPilot Operations, ${session.callerName || "Specialist"}`
                      : `Welcome to ${session.callerName || "Customer Support"}`}
                  </h3>
                  <p className="welcome-desc">
                    {isStaff
                      ? "Investigate customer orders, verify contract overrides, calculate deterministic SLA credits, and stage audited actions."
                      : "Ask questions about your orders, contract entitlements, cancellation fees, or compensation — all answers are backed by authoritative sources."}
                  </p>

                  <div className="welcome-security-card">
                    <Shield size={13} strokeWidth={1.75} className="sec-icon" aria-hidden="true" />
                    <span>
                      {isStaff
                        ? "Active Identity: Internal Operations (RBAC Enforced) · Multi-Account Data Scoping"
                        : `Active Account: ${activeSessionSpec?.accountId || "Customer"} · Access to other accounts is physically blocked in the data layer.`}
                    </span>
                  </div>

                  <div className="suggestions-container">
                    <div className="suggestions-label">Suggested Inquiries to Test:</div>
                    <div className="suggestions-grid">
                      {suggestions.map((s) => (
                        <button
                          key={s}
                          type="button"
                          className="suggestion-card"
                          onClick={() => submit(s)}
                        >
                          <ArrowRight size={14} strokeWidth={2} className="suggestion-arrow" aria-hidden="true" />
                          <span className="suggestion-text">{s}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Message List */}
              {messages.map((m, i) => (
                <div key={i} className={`msg-wrapper ${m.role === "user" ? "user-msg" : "assistant-msg"}`}>
                  <div className={m.role === "user" ? "bubble-user" : "bubble-assistant"}>
                    {m.role === "assistant" && (
                      <div className="assistant-header-bar">
                        <div className="assistant-avatar-pill">
                          <span className="avatar-dot" />
                          <strong>ParcelPilot Agent</strong>
                        </div>
                        {m.timestamp && <span className="msg-timestamp">{m.timestamp}</span>}
                      </div>
                    )}

                    {m.role === "user" && m.timestamp && (
                      <div className="user-msg-time">{m.timestamp}</div>
                    )}

                    <div className="msg-body">
                      {m.role === "assistant" ? <Markdown text={m.content} /> : m.content}
                    </div>

                    {/* Step-by-Step Tool Activity Timeline */}
                    {m.tools_used && m.tools_used.length > 0 && (
                      <ToolActivityTimeline tools={m.tools_used} />
                    )}

                    {/* Source Authority Conflict Resolution Banner */}
                    {m.conflicts && m.conflicts.length > 0 && (
                      <ConflictBanner conflicts={m.conflicts} />
                    )}

                    {/* Human Escalation Alert Banner */}
                    {m.escalated && <EscalationNotice />}

                    {/* State-Changing Pending Actions Preview & Confirmation Card */}
                    {m.pending_actions && m.pending_actions.length > 0 && (
                      <div className="pending-actions-wrap">
                        {m.pending_actions.map((pa) => (
                          <ActionConfirmationCard
                            key={pa.pending_action_id}
                            action={pa}
                            receipt={receipts[pa.pending_action_id]}
                            onConfirm={(id) => actOnPending(id, "confirm")}
                            onCancel={(id) => actOnPending(id, "cancel")}
                          />
                        ))}
                      </div>
                    )}

                    {/* Authoritative Source Citations with Tier Badges */}
                    {m.citations && m.citations.length > 0 && (
                      <SourceEvidenceCard citations={m.citations} />
                    )}
                  </div>
                </div>
              ))}

              {/* Busy / Typing Indicator */}
              {busy && (
                <div className="msg-wrapper assistant-msg">
                  <div className="bubble-assistant typing-bubble">
                    <div className="typing-header">
                      <div className="typing-status">
                        <span className="typing-dot" />
                        <span>Reasoning across policies, agreements &amp; database...</span>
                      </div>
                      <button
                        type="button"
                        className="stop-btn"
                        onClick={cancelChat}
                        aria-label="Stop generation"
                        title="Stop generation"
                      >
                        <Square size={11} strokeWidth={0} fill="currentColor" aria-hidden="true" />
                        Stop
                      </button>
                    </div>
                    <span className="typing">
                      <i />
                      <i />
                      <i />
                    </span>
                  </div>
                </div>
              )}

              {/* Error Box */}
              {error && (
                <div className="error-box chat-error">
                  <AlertCircle size={15} strokeWidth={2} className="error-icon" aria-hidden="true" />
                  <div className="error-text" style={{ flex: 1 }}>
                    <strong>Request Failed:</strong> {error}
                  </div>
                  {messages.length > 0 && messages[messages.length - 1].role === 'user' && (
                    <button
                      type="button"
                      className="retry-btn"
                      onClick={() => submit(messages[messages.length - 1].content)}
                      aria-label="Retry last request"
                    >
                      <RotateCcw size={12} strokeWidth={2} aria-hidden="true" />
                      Retry
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Composer */}
          <div className="composer">
            <div className="composer-inner">
              <textarea
                ref={inputRef as any}
                rows={1}
                placeholder={
                  isStaff
                    ? "Ask about any account's orders, SLA breaches, credit entitlements, or stage an action..."
                    : "Ask about your orders, contract terms, cancellation fees, or service credits..."
                }
                aria-label="Message to ParcelPilot Agent"
                value={input}
                disabled={!session || busy}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                    e.currentTarget.style.height = "auto";
                  }
                }}
                style={{ resize: "none", overflowY: "auto" }}
              />
              <button
                type="button"
                className="send"
                onClick={() => submit()}
                disabled={!session || busy || !input.trim()}
                aria-label="Send message"
              >
                <span>Send</span>
                <Send size={14} strokeWidth={2} aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
