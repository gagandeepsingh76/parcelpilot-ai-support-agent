"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { InsightsReport, fetchInsights, fetchMe } from "../../lib/api";
import LoginScreen, { AppSession, sessionFromTokenData } from "../../components/LoginScreen";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export default function InsightsPage() {
  const router = useRouter();
  const [session, setSession] = useState<AppSession | null | undefined>(undefined);
  const [report, setReport] = useState<InsightsReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const token = sessionStorage.getItem("pp_token");
      if (!token) {
        router.replace("/");
        return;
      }
      setSession({
        token,
        callerName: sessionStorage.getItem("pp_user") || "",
        kind: sessionStorage.getItem("pp_kind") || "customer",
        sessionKey: sessionStorage.getItem("pp_session") || "",
      });
    } catch {
      setSession(null);
    }
  }, [router]);

  const isStaff = session?.kind === "internal";

  const onSignedIn = (s: AppSession) => {
    sessionStorage.setItem("pp_token", s.token);
    sessionStorage.setItem("pp_user", s.callerName);
    sessionStorage.setItem("pp_kind", s.kind);
    sessionStorage.setItem("pp_session", s.sessionKey);
    setSession(s);
  };

  useEffect(() => {
    if (!session || !isStaff) return;
    fetchMe(session.token)
      .then(() =>
        fetchInsights(session.token)
          .then(setReport)
          .catch((e) => setError(String(e)))
      )
      .catch((e) => setError(String(e)));
  }, [session, isStaff]);

  const weekDelta =
    report && report.ticket_volume.totals.prev_week > 0
      ? Math.round(
          ((report.ticket_volume.totals.this_week - report.ticket_volume.totals.prev_week) /
            report.ticket_volume.totals.prev_week) *
            100
        )
      : null;

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="logo">
          Parcel<span>Pilot</span>
        </Link>
        <p className="tagline">Internal operations console.</p>
        <nav className="nav">
          <Link href="/" className="navlink">
            Chat
          </Link>
          <Link href="/insights" className="navlink active">
            Insights
          </Link>
        </nav>
        <footer className="sidefoot">Internal-only. Customer sessions are denied here.</footer>
      </aside>

      <main className="main insights-scroll">
        {session === undefined ? null : session === null ? (
          <LoginScreen existing={null} onSignedIn={onSignedIn} />
        ) : !isStaff && !error ? (
          <div className="center-note">
            <div className="script">Insights are internal</div>
            Switch to a staff session on the chat page to view this dashboard.
          </div>
        ) : error ? (
          <div className="insights-inner">
            <div className="error-box">
              {error.includes("403")
                ? "Insights are internal-only. Switch to a staff session on the chat page."
                : error}
            </div>
          </div>
        ) : report ? (
          <div className="insights-inner">
            <div className="insights-header">
              <span className="script">Operations Insights</span>
              <span className="asof">
                as of {report.generated_at.replace("T", " ").slice(0, 16)}Z
              </span>
            </div>

            <div className="kpi-row">
              <div className="kpi">
                <div className="kpi-label">Tickets this week</div>
                <div className="kpi-value">{report.ticket_volume.totals.this_week}</div>
                {weekDelta != null && (
                  <div className={`kpi-delta ${weekDelta > 0 ? "up" : "down"}`}>
                    {weekDelta > 0 ? "+" : ""}
                    {weekDelta}% vs prior week
                  </div>
                )}
              </div>
              <div className="kpi">
                <div className="kpi-label">SLA breaches</div>
                <div className="kpi-value">{report.sla_watchlist.length}</div>
                <div className="kpi-delta">open tickets needing attention</div>
              </div>
              <div className="kpi">
                <div className="kpi-label">Late deliveries</div>
                <div className="kpi-value">{report.service_quality.late_delivery_count}</div>
                <div className="kpi-delta">
                  {report.service_quality.window_days}-day window ·{" "}
                  {report.service_quality.orders_in_flight} in flight
                </div>
              </div>
              <div className="kpi">
                <div className="kpi-label">Credit exposure</div>
                <div className="kpi-value">
                  ${report.credit_exposure.total_claimable_usd.toFixed(0)}
                </div>
                <div className="kpi-delta">claimable today across accounts</div>
              </div>
            </div>

            <div className="insights-grid">
              <Card title="Ticket volume by category (trailing week)">
                <ul>
                  {report.ticket_volume.by_category.slice(0, 6).map((c) => (
                    <li key={c.category}>
                      {c.category}: <strong>{c.count}</strong>
                    </li>
                  ))}
                </ul>
                {report.ticket_volume.spikes.map((s) => (
                  <div key={s.account_id} className="notice-row">
                    Spike: {s.account_name} ({s.account_id}) — {s.this_week} this week vs{" "}
                    {s.prev_week} prior ({s.top_categories.map((t) => t.category).join(", ")}).
                  </div>
                ))}
              </Card>

              <Card title={`SLA watchlist (${report.sla_watchlist.length})`}>
                {report.sla_watchlist.length === 0 && <p>All open tickets within SLA.</p>}
                {report.sla_watchlist.map((t) => (
                  <div key={t.ticket_id} className="alert-row">
                    <strong>
                      [{t.priority}] {t.ticket_id} — {t.account_name}
                    </strong>
                    <div>{t.subject}</div>
                    <ul>
                      {t.problems.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </Card>

              <Card title={`Service quality (${report.service_quality.window_days}-day window)`}>
                <ul>
                  {report.service_quality.late_pickups.slice(0, 5).map((o) => (
                    <li key={o.order_id}>
                      <span className="mono">{o.order_id}</span>: pickup +{o.delay_minutes} min
                    </li>
                  ))}
                  {report.service_quality.late_deliveries.slice(0, 5).map((o) => (
                    <li key={o.order_id}>
                      <span className="mono">{o.order_id}</span>:{" "}
                      {o.delay_hours != null ? `delivery +${o.delay_hours} h` : o.note}
                    </li>
                  ))}
                </ul>
              </Card>

              <Card title="Credit exposure (if claimed today)">
                <ul>
                  {Object.entries(report.credit_exposure.claimable_now_usd_by_account).map(
                    ([account, amount]) => (
                      <li key={account}>
                        <span className="mono">{account}</span>: ${amount.toFixed(2)}
                      </li>
                    )
                  )}
                </ul>
                {report.credit_exposure.manual_review.map((m, i) => (
                  <div key={i} className="notice-row">
                    Manual review: {m.kind} on <span className="mono">{m.order_id}</span>
                  </div>
                ))}
                <p className="hint">{report.credit_exposure.basis}</p>
              </Card>

              {report.cross_customer_patterns.length > 0 && (
                <Card title="Cross-customer patterns">
                  <ul>
                    {report.cross_customer_patterns.map((p) => (
                      <li key={p.category}>
                        <strong>{p.category}</strong> at {p.accounts_affected} accounts —{" "}
                        {p.hint}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        ) : (
          <div className="center-note">
            <span className="typing" style={{ marginTop: 40 }}>
              <i />
              <i />
              <i />
            </span>
          </div>
        )}
      </main>
    </div>
  );
}
