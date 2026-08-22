"use client";

import { useState } from "react";
import { CallerInfo, MOCK_SESSIONS, MockSessionSpec, credentialLogin, login } from "../lib/api";

export interface AppSession {
  token: string;
  callerName: string;
  kind: string;
  sessionKey: string;
}

export function mockKeyForCaller(caller: CallerInfo): string {
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
  return caller.kind === "customer"
    ? ACCOUNT_TO_KEY[caller.account_id ?? ""] ?? "cust-northstar"
    : ROLE_TO_KEY[caller.role ?? ""] ?? "staff-agent";
}

export function sessionFromTokenData(
  token: string,
  caller: CallerInfo
): AppSession {
  return {
    token,
    callerName: caller.display_name,
    kind: caller.kind,
    sessionKey: mockKeyForCaller(caller),
  };
}

export default function LoginScreen({
  existing,
  onSignedIn,
}: {
  existing: AppSession | null;
  onSignedIn: (s: AppSession) => void;
}) {
  const [tab, setTab] = useState<"quick" | "cred">("quick");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleQuickLogin = async (spec: MockSessionSpec) => {
    setBusy(true);
    setError(null);
    try {
      const token = await login(spec.key);
      onSignedIn({
        token,
        callerName: spec.company || spec.label,
        kind: spec.kind,
        sessionKey: spec.key,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleCredentialLogin = async () => {
    if (!username.trim() || !password || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { token, caller } = await credentialLogin(username.trim(), password);
      onSignedIn(sessionFromTokenData(token, caller));
      setPassword("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="gate">
      <div className="orb orb-a" />
      <div className="orb orb-b" />
      <div className="orb orb-c" />
      <div className="route" />

      <main className="login-card-wide">
        <div className="login-header-area">
          <h1 className="wordmark">
            Parcel<span>Pilot</span>
          </h1>
          <p className="gate-tagline">
            AI Support &amp; Operations Agent — Grounded in Contract Agreements &amp; Operational Data
          </p>
        </div>

        {existing && (
          <button
            type="button"
            className="continue-chip"
            onClick={() => onSignedIn(existing)}
          >
            ➔ Continue as {existing.callerName || existing.sessionKey}
          </button>
        )}

        {/* Tab switcher */}
        <div className="login-tabs-nav">
          <button
            type="button"
            className={`login-tab-btn ${tab === "quick" ? "active" : ""}`}
            onClick={() => setTab("quick")}
          >
            ⚡ 1-Click Evaluation Personas
          </button>
          <button
            type="button"
            className={`login-tab-btn ${tab === "cred" ? "active" : ""}`}
            onClick={() => setTab("cred")}
          >
            🔑 Credentials Login
          </button>
        </div>

        {error && <div className="error-box login-error">{error}</div>}

        {tab === "quick" ? (
          <div className="quick-personas-container">
            <div className="persona-category-section">
              <div className="category-title">
                <span>🏢 Customer Portals</span>
                <span className="category-subtitle">Enforced scoped access (only own orders &amp; tickets)</span>
              </div>
              <div className="quick-persona-grid">
                {MOCK_SESSIONS.filter((s) => s.kind === "customer").map((spec) => (
                  <div key={spec.key} className="quick-persona-card">
                    <div className="quick-card-head">
                      <strong className="quick-card-name">{spec.company}</strong>
                      <span className="quick-badge">{spec.badge}</span>
                    </div>
                    <p className="quick-card-desc">{spec.description}</p>
                    <button
                      type="button"
                      className="quick-enter-btn"
                      onClick={() => handleQuickLogin(spec)}
                      disabled={busy}
                    >
                      {busy ? "Loading..." : "Enter Portal →"}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="persona-category-section">
              <div className="category-title">
                <span>🛠️ Internal Operations &amp; Support Staff</span>
                <span className="category-subtitle">Multi-account lookup, action staging &amp; proactive insights</span>
              </div>
              <div className="quick-persona-grid">
                {MOCK_SESSIONS.filter((s) => s.kind === "internal").map((spec) => (
                  <div key={spec.key} className="quick-persona-card staff">
                    <div className="quick-card-head">
                      <strong className="quick-card-name">{spec.label.replace("Internal — ", "")}</strong>
                      <span className="quick-badge staff">{spec.badge}</span>
                    </div>
                    <p className="quick-card-desc">{spec.description}</p>
                    <button
                      type="button"
                      className="quick-enter-btn staff"
                      onClick={() => handleQuickLogin(spec)}
                      disabled={busy}
                    >
                      {busy ? "Loading..." : "Enter Console →"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="cred-login-form">
            <label className="field">
              <span>Username</span>
              <input
                type="text"
                placeholder="e.g. northstar, lumenworks, agent, ops"
                value={username}
                autoComplete="username"
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCredentialLogin()}
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCredentialLogin()}
              />
            </label>

            <button
              type="button"
              className="enter-btn"
              onClick={handleCredentialLogin}
              disabled={busy || !username.trim() || !password}
            >
              {busy ? "Verifying Credentials…" : "Authenticate & Enter"}
            </button>

            <div className="cred-note">
              <div>
                <strong>Customer accounts:</strong> <code>northstar</code>, <code>lumenworks</code>, <code>brightcart</code> — password: <code>demo1234</code>
              </div>
              <div>
                <strong>Internal staff:</strong> <code>agent</code>, <code>ops</code>, <code>admin</code>, <code>viewer</code> — password: <code>staff1234</code>
              </div>
            </div>
          </div>
        )}

        <div className="trust-strip">
          <span>Tiered Authority RAG</span>
          <i />
          <span>Confirmation-Gated Actions</span>
          <i />
          <span>Data-Layer RBAC</span>
          <i />
          <span>Deterministic Calcs</span>
        </div>
      </main>
    </div>
  );
}
