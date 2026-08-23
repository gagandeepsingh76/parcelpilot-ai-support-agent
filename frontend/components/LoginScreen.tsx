"use client";

import { useRef, useState } from "react";
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
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingLabel, setLoadingLabel] = useState<string>('');

// Quick login retained for internal usage, not displayed in UI

  const handleAutoLogin = async (
    username: string,
    password: string,
    label: string,
    loadingMsg: string
  ) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setLoadingLabel(label);
    setError(null);
    try {
      const { token, caller } = await credentialLogin(username, password);
      onSignedIn(sessionFromTokenData(token, caller));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      busyRef.current = false;
      setBusy(false);
      setLoadingLabel('');
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


        

        {error && <div className="error-box login-error">{error}</div>}

        <h2 className="login-subtitle" style={{ marginTop: "1rem", textAlign: "center" }}>
          Choose how you want to continue
        </h2>
        <div className="demo-login-buttons" style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1.5rem" }}>
          <button
            type="button"
            className="enter-btn"
            onClick={() =>
              handleAutoLogin(
                "northstar",
                "demo1234",
                "Demo User",
                "Signing in as Demo User..."
              )
            }
            disabled={busy}
            style={{ padding: "1rem", fontSize: "1.1rem", borderRadius: "0.75rem" }}
          >
            {busy && loadingLabel === "Demo User" ? "Signing in as Demo User..." : "Demo User"}
            <div style={{ fontSize: "0.85rem", opacity: 0.8 }}>Customer Portal</div>
          </button>
          <button
            type="button"
            className="enter-btn"
            onClick={() =>
              handleAutoLogin(
                "agent",
                "staff1234",
                "Evaluator / Staff",
                "Opening Evaluator Console..."
              )
            }
            disabled={busy}
            style={{ padding: "1rem", fontSize: "1.1rem", borderRadius: "0.75rem" }}
          >
            {busy && loadingLabel === "Evaluator / Staff" ? "Opening Evaluator Console..." : "Evaluator / Staff"}
            <div style={{ fontSize: "0.85rem", opacity: 0.8 }}>Support Console</div>
          </button>
        </div>
        <p style={{ marginTop: "1rem", fontSize: "0.85rem", opacity: 0.7, textAlign: "center" }}>
          Demo access is provided for evaluation purposes.
        </p>

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
