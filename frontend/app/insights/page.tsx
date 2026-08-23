"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { InsightsReport, fetchInsights, login } from "../../lib/api";
import LoginScreen, { AppSession } from "../../components/LoginScreen";
import AppShell from "../../components/AppShell";
import {
  Ticket,
  Clock,
  Package,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  Truck,
  Lock,
  ArrowRight,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

function MetricCard({
  title,
  value,
  subtext,
  delta,
  icon,
  badge,
}: {
  title: string;
  value: string | number;
  subtext?: string;
  delta?: { value: number; label: string };
  icon?: ReactNode;
  badge?: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <span className="metric-card-title">{title}</span>
        {icon && <span className="metric-card-icon" aria-hidden="true">{icon}</span>}
      </div>
      <div className="metric-card-value-row">
        <div className="metric-card-value">{value}</div>
        {badge && <span className="metric-badge">{badge}</span>}
      </div>
      {delta && (
        <div className={`metric-delta ${delta.value > 0 ? "up" : delta.value < 0 ? "down" : "neutral"}`}>
          {delta.value > 0 ? (
            <TrendingUp size={12} strokeWidth={2} aria-hidden="true" />
          ) : delta.value < 0 ? (
            <TrendingDown size={12} strokeWidth={2} aria-hidden="true" />
          ) : (
            <Minus size={12} strokeWidth={2} aria-hidden="true" />
          )}
          {delta.value > 0 ? " +" : " "}
          {delta.value}% {delta.label}
        </div>
      )}
      {subtext && !delta && <div className="metric-subtext">{subtext}</div>}
    </div>
  );
}

function SectionCard({
  title,
  icon,
  badge,
  children,
}: {
  title: string;
  icon?: ReactNode;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="dashboard-section-card">
      <div className="section-card-header">
        <div className="section-title-wrap">
          {icon && <span className="section-icon" aria-hidden="true">{icon}</span>}
          <h3>{title}</h3>
        </div>
        {badge && <span className="section-header-badge">{badge}</span>}
      </div>
      <div className="section-card-body">{children}</div>
    </section>
  );
}

export default function InsightsPage() {
  const router = useRouter();
  const [session, setSession] = useState<AppSession | null | undefined>(undefined);
  const [report, setReport] = useState<InsightsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const token = sessionStorage.getItem("pp_token");
      if (!token) {
        setSession(null);
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
  }, []);

  const isStaff = session?.kind === "internal";

  const loadData = (tok: string) => {
    setLoading(true);
    setError(null);
    fetchInsights(tok)
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!session || !isStaff) return;
    loadData(session.token);
  }, [session, isStaff]);

  const onSignedIn = (s: AppSession) => {
    sessionStorage.setItem("pp_token", s.token);
    sessionStorage.setItem("pp_user", s.callerName);
    sessionStorage.setItem("pp_kind", s.kind);
    sessionStorage.setItem("pp_session", s.sessionKey);
    setSession(s);
  };

  const signOut = () => {
    ["pp_token", "pp_user", "pp_kind", "pp_session"].forEach((k) =>
      sessionStorage.removeItem(k)
    );
    setSession(null);
    router.replace("/");
  };

  const switchToStaff = async () => {
    try {
      const token = await login("staff-agent");
      const s: AppSession = {
        token,
        callerName: "Avery (support agent)",
        kind: "internal",
        sessionKey: "staff-agent",
      };
      onSignedIn(s);
    } catch (e) {
      setError(String(e));
    }
  };

  const investigateTicket = (ticketId: string) => {
    router.push(`/?prompt=${encodeURIComponent(`Investigate SLA status and root cause for ticket ${ticketId}`)}`);
  };

  const weekDelta =
    report && report.ticket_volume.totals.prev_week > 0
      ? Math.round(
          ((report.ticket_volume.totals.this_week - report.ticket_volume.totals.prev_week) /
            report.ticket_volume.totals.prev_week) *
            100
        )
      : null;

  if (session === undefined) return null;
  if (session === null) return <LoginScreen existing={null} onSignedIn={onSignedIn} />;

  return (
    <AppShell session={session} onSwitchSession={onSignedIn} onSignOut={signOut}>
      <main className="insights-main-container">
        {/* Insights Top Header */}
        <header className="insights-topbar">
          <div className="topbar-left">
            <div className="topbar-title-row">
              <h2 className="topbar-title">Operations Insights &amp; Anomaly Detection</h2>
              <span className="pill-badge staff">INTERNAL CONSOLE</span>
            </div>
            <p className="topbar-desc">
              Proactive issue clustering, SLA risk monitoring, and credit exposure grounded in snapshot data.
            </p>
          </div>

          <div className="topbar-right">
            {report && (
              <span className="snapshot-timestamp-pill">
                Anchor Time: {report.generated_at.replace("T", " ").slice(0, 16)}Z
              </span>
            )}
            <button
              type="button"
              className="refresh-btn"
              onClick={() => session && isStaff && loadData(session.token)}
              disabled={loading || !isStaff}
              aria-label="Refresh metrics"
            >
              <RefreshCw size={13} strokeWidth={2} aria-hidden="true" className={loading ? "spin-icon" : ""} />
              {loading ? "Refreshing..." : "Refresh Metrics"}
            </button>
          </div>
        </header>

        {/* Customer Access Restriction State */}
        {!isStaff ? (
          <div className="restricted-notice-card">
            <div className="restricted-icon">
              <Lock size={36} strokeWidth={1.5} aria-hidden="true" />
            </div>
            <h3>Operations Insights is an Internal-Only Dashboard</h3>
            <p>
              Customer sessions are strictly limited to viewing their own account records to prevent cross-account leakage.
              To explore SLA risk monitoring and cross-account anomaly detection, switch to an internal staff session.
            </p>
            <button type="button" className="switch-staff-btn" onClick={switchToStaff}>
              <ArrowRight size={15} strokeWidth={2} aria-hidden="true" />
              Switch to Internal Support Agent (Avery)
            </button>
          </div>
        ) : error ? (
          <div className="error-box insights-error">
            <AlertCircle size={15} strokeWidth={2} aria-hidden="true" />
            <strong>Error loading insights:</strong> {error}
          </div>
        ) : report ? (
          <div className="dashboard-content">
            {/* KPI Metric Overview Row */}
            <div className="kpi-grid">
              <MetricCard
                title="Tickets This Week"
                value={report.ticket_volume.totals.this_week}
                delta={weekDelta != null ? { value: weekDelta, label: "vs prior week" } : undefined}
                icon={<Ticket size={16} strokeWidth={1.75} />}
              />
              <MetricCard
                title="SLA Breaches / Risks"
                value={report.sla_watchlist.length}
                subtext="Open tickets requiring immediate attention"
                badge={report.sla_watchlist.length > 0 ? "Action Required" : "Healthy"}
                icon={<Clock size={16} strokeWidth={1.75} />}
              />
              <MetricCard
                title="Service Quality Anomalies"
                value={report.service_quality.late_delivery_count + report.service_quality.late_pickup_count}
                subtext={`${report.service_quality.late_delivery_count} late deliveries, ${report.service_quality.late_pickup_count} late pickups`}
                icon={<Package size={16} strokeWidth={1.75} />}
              />
              <MetricCard
                title="Total Credit Exposure"
                value={`$${report.credit_exposure.total_claimable_usd.toFixed(0)}`}
                subtext="Claimable today across customer accounts"
                icon={<DollarSign size={16} strokeWidth={1.75} />}
              />
            </div>

            {/* Main Insight Grid */}
            <div className="dashboard-sections-grid">
              {/* SLA Watchlist Section */}
              <SectionCard
                title={`SLA Watchlist (${report.sla_watchlist.length} Tickets)`}
                icon={<AlertTriangle size={15} strokeWidth={1.75} />}
                badge={report.sla_watchlist.length > 0 ? "Urgent" : "Cleared"}
              >
                {report.sla_watchlist.length === 0 ? (
                  <div className="empty-state-block">
                    <CheckCircle2 size={32} strokeWidth={1.5} className="empty-state-icon green" aria-hidden="true" />
                    <strong className="empty-state-title">All Clear</strong>
                    <span className="empty-state-desc">All active tickets are within their contractual SLA window.</span>
                  </div>
                ) : (
                  <div className="sla-watchlist-table">
                    {report.sla_watchlist.map((t) => {
                      const isOverdue = t.problems.some((p) => p.includes("overdue"));
                      return (
                        <div key={t.ticket_id} className={`sla-ticket-row ${isOverdue ? "is-overdue" : "is-near"}`}>
                          <div className="sla-ticket-top">
                            <div className="sla-priority-pill" data-priority={t.priority}>
                              {t.priority}
                            </div>
                            <span className="sla-ticket-id">{t.ticket_id}</span>
                            <span className="sla-account-name">{t.account_name}</span>
                            <button
                              type="button"
                              className="investigate-ticket-btn"
                              onClick={() => investigateTicket(t.ticket_id)}
                              title="Ask AI to investigate this ticket"
                            >
                              Investigate with AI
                              <ArrowRight size={11} strokeWidth={2} aria-hidden="true" />
                            </button>
                          </div>
                          <div className="sla-ticket-subject">{t.subject || "No subject provided"}</div>
                          <ul className="sla-problems-list">
                            {t.problems.map((p, pIdx) => (
                              <li key={pIdx}>
                                <AlertCircle size={11} strokeWidth={2} aria-hidden="true" />
                                {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                  </div>
                )}
              </SectionCard>

              {/* Cross-Customer Patterns */}
              {report.cross_customer_patterns.length > 0 && (
                <SectionCard
                  title="Cross-Customer Pattern Detection"
                  icon={<Search size={15} strokeWidth={1.75} />}
                  badge={`${report.cross_customer_patterns.length} Systemic Clusters`}
                >
                  <div className="patterns-list">
                    {report.cross_customer_patterns.map((p, idx) => (
                      <div key={idx} className="pattern-item-card">
                        <div className="pattern-card-head">
                          <strong className="pattern-category">{p.category}</strong>
                          <span className="pattern-accounts-pill">{p.accounts_affected} Accounts Affected</span>
                        </div>
                        <p className="pattern-hint">{p.hint}</p>
                        <div className="pattern-keywords-row">
                          <span className="keywords-label">Keywords:</span>
                          {p.shared_keywords.map((kw, kIdx) => (
                            <span key={kIdx} className="keyword-chip">{kw}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Ticket Volume & Spikes */}
              <SectionCard title="Ticket Volume & Spikes" icon={<TrendingUp size={15} strokeWidth={1.75} />}>
                <div className="volume-categories-list">
                  {report.ticket_volume.by_category.slice(0, 6).map((c) => (
                    <div key={c.category} className="category-volume-row">
                      <span className="cat-name">{c.category}</span>
                      <div className="cat-bar-wrap">
                        <div
                          className="cat-bar"
                          style={{
                            width: `${Math.min(100, Math.max(10, (c.count / (report.ticket_volume.totals.this_week || 1)) * 100))}%`,
                          }}
                        />
                      </div>
                      <span className="cat-count">{c.count}</span>
                    </div>
                  ))}
                </div>

                {report.ticket_volume.spikes.length > 0 && (
                  <div className="spikes-notice-area">
                    <div className="spikes-heading">
                      <Zap size={12} strokeWidth={2} aria-hidden="true" />
                      Significant Volume Spikes (&gt;2x prior week):
                    </div>
                    {report.ticket_volume.spikes.map((s) => (
                      <div key={s.account_id} className="spike-card">
                        <span className="spike-name"><strong>{s.account_name}</strong> ({s.account_id})</span>
                        <span className="spike-stat">
                          {s.this_week} tickets this week vs {s.prev_week} prior
                        </span>
                        <span className="spike-top-cat">
                          Top: {s.top_categories.map((t) => `${t.category} (${t.count})`).join(", ")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>

              {/* Service Quality */}
              <SectionCard title={`Service Quality (${report.service_quality.window_days}-Day Window)`} icon={<Truck size={15} strokeWidth={1.75} />}>
                <div className="service-quality-summary">
                  <div><strong>In-Flight Shipments:</strong> {report.service_quality.orders_in_flight}</div>
                  <div><strong>Late Pickups:</strong> {report.service_quality.late_pickup_count}</div>
                  <div><strong>Late Deliveries:</strong> {report.service_quality.late_delivery_count}</div>
                </div>

                <div className="quality-tables-split">
                  <div className="quality-sublist">
                    <div className="sublist-heading">Late Pickups (&gt;10 min):</div>
                    {report.service_quality.late_pickups.length === 0 ? (
                      <div className="empty-state-block compact">
                        <CheckCircle2 size={20} strokeWidth={1.5} className="empty-state-icon green" aria-hidden="true" />
                        <span className="empty-state-desc">None recorded in window</span>
                      </div>
                    ) : (
                      <ul>
                        {report.service_quality.late_pickups.slice(0, 5).map((o) => (
                          <li key={o.order_id}>
                            <code>{o.order_id}</code>: +{o.delay_minutes} min late pickup
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="quality-sublist">
                    <div className="sublist-heading">Late Deliveries:</div>
                    {report.service_quality.late_deliveries.length === 0 ? (
                      <div className="empty-state-block compact">
                        <CheckCircle2 size={20} strokeWidth={1.5} className="empty-state-icon green" aria-hidden="true" />
                        <span className="empty-state-desc">None recorded in window</span>
                      </div>
                    ) : (
                      <ul>
                        {report.service_quality.late_deliveries.slice(0, 5).map((o) => (
                          <li key={o.order_id}>
                            <code>{o.order_id}</code>: {o.delay_hours != null ? `+${o.delay_hours} hrs` : o.note}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </SectionCard>

              {/* Credit Exposure & Manual Review */}
              <SectionCard title="Service Credit Exposure" icon={<DollarSign size={15} strokeWidth={1.75} />}>
                <div className="exposure-by-account-grid">
                  {Object.entries(report.credit_exposure.claimable_now_usd_by_account).map(([acc, amt]) => (
                    <div key={acc} className="exposure-account-chip">
                      <span className="acc-code">{acc}</span>
                      <span className="acc-amt">${amt.toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                {report.credit_exposure.manual_review.length > 0 && (
                  <div className="manual-review-box">
                    <div className="manual-review-title">
                      <AlertTriangle size={13} strokeWidth={2} aria-hidden="true" />
                      Flagged for Operations Review (Missing Contract Fields):
                    </div>
                    {report.credit_exposure.manual_review.map((m, idx) => (
                      <div key={idx} className="manual-item">
                        <span><code>{m.order_id}</code>: {m.kind}</span>
                        <span className="manual-basis">{m.basis}</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="exposure-basis-note">{report.credit_exposure.basis}</p>
              </SectionCard>
            </div>
          </div>
        ) : (
          <div className="insights-skeleton-container">
            <div className="skeleton-kpi-row">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="skeleton-kpi-card" />
              ))}
            </div>
            <div className="skeleton-sections-grid">
              <div className="skeleton-section-card" />
              <div className="skeleton-section-card" />
            </div>
          </div>
        )}
      </main>
    </AppShell>
  );
}
