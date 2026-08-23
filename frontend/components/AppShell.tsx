"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AppSession } from "./LoginScreen";
import ThemeToggle from "./ThemeToggle";
import { MOCK_SESSIONS, MockSessionSpec, login } from "../lib/api";
import ContextDrawer from "./chat/ContextDrawer";
import {
  Menu,
  X,
  MessageSquare,
  BarChart3,
  BookOpen,
  Building2,
  Wrench,
} from "lucide-react";

interface AppShellProps {
  children: ReactNode;
  session: AppSession;
  onSwitchSession: (newSession: AppSession) => void;
  onSignOut: () => void;
}

export default function AppShell({
  children,
  session,
  onSwitchSession,
  onSignOut,
}: AppShellProps) {
  const pathname = usePathname();
  const [showSwitcherModal, setShowSwitcherModal] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [switcherBusy, setSwitcherBusy] = useState(false);

  const isStaff = session.kind === "internal";
  const activeSessionSpec = MOCK_SESSIONS.find((s) => s.key === session.sessionKey);

  const handleFastSwitch = async (spec: MockSessionSpec) => {
    setSwitcherBusy(true);
    try {
      const token = await login(spec.key);
      onSwitchSession({
        token,
        callerName: spec.company || spec.label,
        kind: spec.kind,
        sessionKey: spec.key,
      });
      setShowSwitcherModal(false);
      setIsSidebarOpen(false);
    } catch (e) {
      console.error("Switch failed", e);
    } finally {
      setSwitcherBusy(false);
    }
  };

  return (
    <div className="shell">
      {/* Mobile Topbar */}
      <div className="mobile-topbar">
        <button
          type="button"
          className="hamburger-btn"
          onClick={() => setIsSidebarOpen(true)}
          aria-label="Open navigation menu"
        >
          <Menu size={20} strokeWidth={1.75} />
        </button>
        <Link href="/" className="logo mobile-logo">
          Parcel<span>Pilot</span>
        </Link>
      </div>

      {/* Sidebar Overlay for Mobile */}
      {isSidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-brand-block">
          <div className="sidebar-brand-top">
            <Link href="/" className="logo">
              Parcel<span>Pilot</span>
            </Link>
            <button
              type="button"
              className="mobile-close-sidebar"
              onClick={() => setIsSidebarOpen(false)}
              aria-label="Close navigation menu"
            >
              <X size={16} strokeWidth={2} />
            </button>
          </div>
          <p className="tagline">Grounded AI Support &amp; Operations</p>
        </div>

        <nav className="nav" aria-label="Main Navigation">
          <Link
            href="/"
            className={`navlink ${pathname === "/" ? "active" : ""}`}
          >
            <MessageSquare size={16} strokeWidth={1.75} className="nav-icon" aria-hidden="true" />
            <span>AI Assistant</span>
          </Link>
          <Link
            href="/insights"
            className={`navlink ${pathname === "/insights" ? "active" : ""}`}
          >
            <BarChart3 size={16} strokeWidth={1.75} className="nav-icon" aria-hidden="true" />
            <span>Operations Insights</span>
          </Link>
          <button
            type="button"
            className="navlink nav-btn"
            onClick={() => setIsDrawerOpen(true)}
          >
            <BookOpen size={16} strokeWidth={1.75} className="nav-icon" aria-hidden="true" />
            <span>Knowledge &amp; Context</span>
          </button>
        </nav>

        {/* User Identity Card */}
        <div className="sessions">
          <div className="session-card-header">
            <h4>Active Context</h4>
            <button
              type="button"
              className="quick-switch-btn"
              onClick={() => setShowSwitcherModal(true)}
              title="Switch persona for testing"
            >
              Switch
            </button>
          </div>
          <div className={`identity-card ${isStaff ? "staff" : ""}`}>
            <span className={`session-dot ${isStaff ? "staff" : "customer"}`} />
            <div className="identity-text-wrap">
              <div className="who">
                {session.callerName || activeSessionSpec?.label || session.sessionKey}
              </div>
              <div className="what-row">
                <span className="role-tag">
                  {isStaff ? (activeSessionSpec?.badge || "Staff") : (activeSessionSpec?.badge || "Customer")}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="theme-row">
          <ThemeToggle />
        </div>

        <div className="sidebar-bottom-actions">
          <button type="button" className="sidebar-logout-btn" onClick={onSignOut}>
            Sign Out
          </button>
        </div>

        <footer className="sidefoot">
          <span>Security enforced in data layer</span>
          <span className="snapshot-tag">Snapshot: 2026-03-15</span>
        </footer>
      </aside>

      {/* Main content wrapper */}
      <div className="main-wrapper">
        {children}
      </div>

      {/* Fast Persona Switcher Modal for Reviewers */}
      {showSwitcherModal && (
        <div className="modal-overlay" onClick={() => setShowSwitcherModal(false)}>
          <div className="persona-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">Switch Test Persona</h3>
                <p className="modal-sub">Instantly toggle roles to test access-control boundaries &amp; entitlements.</p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowSwitcherModal(false)}
                aria-label="Close persona switcher"
              >
                <X size={14} strokeWidth={2} />
              </button>
            </div>

            <div className="persona-sections-wrap">
              <div className="persona-group">
                <div className="group-title">
                  <Building2 size={13} strokeWidth={1.75} aria-hidden="true" />
                  Customer Portals (Scoped Access)
                </div>
                <div className="persona-grid">
                  {MOCK_SESSIONS.filter((s) => s.kind === "customer").map((spec) => {
                    const isCurrent = spec.key === session.sessionKey;
                    return (
                      <button
                        key={spec.key}
                        type="button"
                        className={`persona-card ${isCurrent ? "current" : ""}`}
                        onClick={() => handleFastSwitch(spec)}
                        disabled={switcherBusy}
                      >
                        <div className="persona-card-top">
                          <span className="persona-name">{spec.company}</span>
                          <span className="persona-badge-pill">{spec.badge}</span>
                        </div>
                        <p className="persona-desc">{spec.description}</p>
                        {isCurrent && <span className="active-tag">● Currently active</span>}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="persona-group">
                <div className="group-title">
                  <Wrench size={13} strokeWidth={1.75} aria-hidden="true" />
                  Internal Staff (Multi-Account RBAC)
                </div>
                <div className="persona-grid">
                  {MOCK_SESSIONS.filter((s) => s.kind === "internal").map((spec) => {
                    const isCurrent = spec.key === session.sessionKey;
                    return (
                      <button
                        key={spec.key}
                        type="button"
                        className={`persona-card staff ${isCurrent ? "current" : ""}`}
                        onClick={() => handleFastSwitch(spec)}
                        disabled={switcherBusy}
                      >
                        <div className="persona-card-top">
                          <span className="persona-name">{spec.label.replace("Internal — ", "")}</span>
                          <span className="persona-badge-pill staff">{spec.badge}</span>
                        </div>
                        <p className="persona-desc">{spec.description}</p>
                        {isCurrent && <span className="active-tag">● Currently active</span>}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Slide-out Context Drawer */}
      <ContextDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        callerKind={session.kind}
        callerAccount={session.kind === "customer" ? activeSessionSpec?.accountId : null}
      />
    </div>
  );
}
