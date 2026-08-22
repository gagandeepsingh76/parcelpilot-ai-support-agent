"use client";

import { useState } from "react";
import { CallerInfo, credentialLogin } from "../lib/api";

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
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const attempt = async () => {
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

      <main className="login-card">
        <h1 className="wordmark">
          Parcel<span>Pilot</span>
        </h1>
        <p className="gate-tagline">AI support, grounded in your contracts.</p>

        {existing && (
          <button
            type="button"
            className="continue-chip"
            onClick={() => onSignedIn(existing)}
          >
            Continue as {existing.callerName || existing.sessionKey}
          </button>
        )}

        <label className="field">
          <span>Username</span>
          <input
            type="text"
            placeholder="your-handle"
            value={username}
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && attempt()}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            placeholder="************"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && attempt()}
          />
        </label>

        {error && <div className="error-box">{error}</div>}

        <button
          type="button"
          className="enter-btn"
          onClick={attempt}
          disabled={busy || !username.trim() || !password}
        >
          {busy ? "Verifying…" : "Enter the console"}
        </button>

        <div className="cred-note">
          <div>
            Customers · <b>northstar</b>, <b>lumenworks</b>, <b>brightcart</b>{" "}
            — password <b>demo1234</b>
          </div>
          <div>
            Staff · <b>agent</b>, <b>ops</b>, <b>viewer</b> — password{" "}
            <b>staff1234</b>
          </div>
        </div>

        <div className="trust-strip">
          <span>Cited answers</span>
          <i />
          <span>Gated actions</span>
          <i />
          <span>Role-scoped RBAC</span>
        </div>
      </main>
    </div>
  );
}
