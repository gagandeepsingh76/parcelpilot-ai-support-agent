"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { InsightsReport, fetchInsights } from "../../lib/api";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export default function InsightsPage() {
  const [token, setToken] = useState<string>("");
  const [report, setReport] = useState<InsightsReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(window.localStorage.getItem("pp_token") || "");
    window.addEventListener("storage", () =>
      setToken(window.localStorage.getItem("pp_token") || "")
    );
  }, []);

  useEffect(() => {
    if (!token) return;
    fetchInsights(token)
      .then(setReport)
      .catch((e) => setError(String(e)));
  }, [token]);

  const isStaff = token.includes("staff");
  return (
    <div className="container">
      <header className="topbar">
        <span className="brand">
          <Link href="/">ParcelPilot Agent</Link>
          <Link href="/insights" className="active">
            Insights
          </Link>
        </span>
        <span className="spacer" />
        {report && (
          <span className="badge">as of {report.generated_at.replace("T", " ").slice(0, 16)}Z</span>
        )}
      </header>

      {!token && (
        <p className="hint">Log in with an internal session on the chat page first.</p>
      )}
      {token && !isStaff && !error && (
        <p className="hint">Insights are internal-only. Switch to a staff session.</p>
      )}
      {error && (
        <div className="error-box">
          {error.includes("403")
            ? "Insights are internal-only. Switch to a staff session on the chat page."
            : error}
        </div>
      )}

      {report && isStaff && (
        <div className="insights-grid">
          <Card title="Ticket volume (trailing week)">
            <p>
              {report.ticket_volume.totals.this_week} tickets this week vs{" "}
              {report.ticket_volume.totals.prev_week} the prior week.
            </p>
            <ul>
              {report.ticket_volume.by_category.slice(0, 5).map((c) => (
                <li key={c.category}>
                  {c.category}: {c.count}
                </li>
              ))}
            </ul>
            {report.ticket_volume.spikes.map((s) => (
              <div key={s.account_id} className="conflict-banner">
                Spike: {s.account_name} ({s.account_id}) — {s.this_week} this week vs{" "}
                {s.prev_week} prior ({s.top_categories.map((t) => t.category).join(", ")}).
              </div>
            ))}
          </Card>

          <Card title={`SLA watchlist (${report.sla_watchlist.length})`}>
            {report.sla_watchlist.length === 0 && <p>All open tickets within SLA.</p>}
            {report.sla_watchlist.map((t) => (
              <div key={t.ticket_id} className="pending-card" style={{ borderColor: "#f85149" }}>
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
            <p>
              Late pickups: {report.service_quality.late_pickup_count} · Late deliveries:{" "}
              {report.service_quality.late_delivery_count} · In flight:{" "}
              {report.service_quality.orders_in_flight}
            </p>
            <ul>
              {report.service_quality.late_pickups.slice(0, 5).map((o) => (
                <li key={o.order_id}>
                  {o.order_id}: pickup +{o.delay_minutes} min
                </li>
              ))}
              {report.service_quality.late_deliveries.slice(0, 5).map((o) => (
                <li key={o.order_id}>
                  {o.order_id}:{" "}
                  {o.delay_hours != null ? `delivery +${o.delay_hours} h` : o.note}
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Credit exposure (if claimed today)">
            <p>Total claimable: ${report.credit_exposure.total_claimable_usd.toFixed(2)}</p>
            <ul>
              {Object.entries(report.credit_exposure.claimable_now_usd_by_account).map(
                ([account, amount]) => (
                  <li key={account}>
                    {account}: ${amount.toFixed(2)}
                  </li>
                )
              )}
            </ul>
            {report.credit_exposure.manual_review.map((m, i) => (
              <div key={i} className="conflict-banner">
                Manual review: {m.kind} on {m.order_id}
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
      )}
    </div>
  );
}
