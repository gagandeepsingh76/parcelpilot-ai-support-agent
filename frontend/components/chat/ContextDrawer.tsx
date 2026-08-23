"use client";

import { useEffect, useState } from "react";
import { KnowledgeDocument, SystemMetadata, fetchDocuments, fetchMetadata } from "../../lib/api";
import { FolderOpen, X } from "lucide-react";

interface ContextDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  callerKind: string;
  callerAccount?: string | null;
}

export default function ContextDrawer({
  isOpen,
  onClose,
  callerKind,
  callerAccount,
}: ContextDrawerProps) {
  const [activeTab, setActiveTab] = useState<"docs" | "accounts" | "security">("docs");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [metadata, setMetadata] = useState<SystemMetadata | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    Promise.all([fetchDocuments().catch(() => []), fetchMetadata().catch(() => null)])
      .then(([docs, meta]) => {
        setDocuments(docs);
        setMetadata(meta);
        if (docs.length > 0 && !selectedDoc) {
          setSelectedDoc(docs[0]);
        }
      })
      .finally(() => setLoading(false));
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="drawer-title-wrap">
            <FolderOpen size={16} strokeWidth={1.75} className="drawer-icon" aria-hidden="true" />
            <h3>System Knowledge & Context</h3>
          </div>
          <button type="button" className="drawer-close-btn" onClick={onClose} aria-label="Close panel">
            <X size={14} strokeWidth={2} />
          </button>
        </div>

        <div className="drawer-tabs">
          <button
            type="button"
            className={`drawer-tab-btn ${activeTab === "docs" ? "active" : ""}`}
            onClick={() => setActiveTab("docs")}
          >
            Authoritative Docs ({documents.length})
          </button>
          <AccountsTabBtn active={activeTab === "accounts"} onClick={() => setActiveTab("accounts")} count={metadata?.accounts.length || 0} />
          <button
            type="button"
            className={`drawer-tab-btn ${activeTab === "security" ? "active" : ""}`}
            onClick={() => setActiveTab("security")}
          >
            Access & RBAC
          </button>
        </div>

        <div className="drawer-body">
          {loading ? (
            <div className="drawer-loading">
              <span className="typing">
                <i />
                <i />
                <i />
              </span>
              <span>Loading context registry...</span>
            </div>
          ) : activeTab === "docs" ? (
            <div className="drawer-docs-view">
              <div className="drawer-doc-selector">
                {documents.map((doc) => (
                  <button
                    key={doc.doc_id}
                    type="button"
                    className={`drawer-doc-pill ${selectedDoc?.doc_id === doc.doc_id ? "selected" : ""} ${doc.status === "DEPRECATED" ? "deprecated" : ""}`}
                    onClick={() => setSelectedDoc(doc)}
                  >
                    <span className="doc-num">[{doc.doc_id}]</span>
                    <span className="doc-short-name">{doc.title}</span>
                    <span className={`doc-status-badge ${doc.status === "DEPRECATED" ? "dep" : "cur"}`}>
                      {doc.status}
                    </span>
                  </button>
                ))}
              </div>

              {selectedDoc && (
                <div className="drawer-doc-detail">
                  <div className="doc-detail-head">
                    <div className="doc-detail-title">{selectedDoc.title}</div>
                    <div className="doc-detail-meta-row">
                      <span className="detail-tag">ID: {selectedDoc.doc_id}</span>
                      <span className="detail-tag">Type: {selectedDoc.doc_type}</span>
                      <span className="detail-tag">Scope: {selectedDoc.customer_scope}</span>
                      <span className={`detail-tag ${selectedDoc.status === "DEPRECATED" ? "dep" : "cur"}`}>
                        {selectedDoc.status}
                      </span>
                    </div>
                  </div>

                  <div className="doc-sections-list">
                    <div className="sections-heading">Document Sections:</div>
                    {selectedDoc.sections && selectedDoc.sections.length > 0 ? (
                      selectedDoc.sections.map((s, i) => (
                        <div key={i} className="doc-section-row">
                          <span className="sec-num">{i + 1}.</span>
                          <span className="sec-title">{s.heading}</span>
                        </div>
                      ))
                    ) : (
                      <div className="no-sections">Standard document structure indexed in vector store.</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : activeTab === "accounts" ? (
            <div className="drawer-accounts-view">
              <p className="accounts-intro">
                Operational accounts in ParcelPilot logistics dataset (snapshot time:{" "}
                <code>{metadata?.snapshot_utc ? metadata.snapshot_utc.slice(0, 16).replace("T", " ") : "2026-03-15"}</code>):
              </p>
              <div className="accounts-cards-list">
                {metadata?.accounts.map((acc) => {
                  const isCurrent = acc.account_id === callerAccount;
                  return (
                    <div key={acc.account_id} className={`account-info-card ${isCurrent ? "current-user-account" : ""}`}>
                      <div className="acc-card-top">
                        <span className="acc-name">{acc.account_name}</span>
                        <span className="acc-id-badge">{acc.account_id}</span>
                      </div>
                      <div className="acc-card-bottom">
                        <span className="acc-tier-tag">Tier: {acc.tier || "Standard"}</span>
                        <span className={`acc-standing-tag ${acc.good_standing ? "good" : "bad"}`}>
                          {acc.good_standing ? "Good Standing" : "Payment Overdue"}
                        </span>
                        {isCurrent && <span className="active-session-indicator">Active Session</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="drawer-security-view">
              <div className="security-section">
                <h4>Data-Layer Access Control</h4>
                <p>
                  Security is enforced inside Python database wrappers (<code>access.py</code>) — never via prompt instructions alone.
                </p>
                <div className="security-rule-box">
                  <div><strong>Customer Scoping:</strong> Customer tokens only resolve records matching their account ID. Cross-account queries are physically denied with 403.</div>
                  <div><strong>Internal RBAC:</strong> Support agents and ops managers can query across accounts but must pass explicit account IDs.</div>
                  <div><strong>Action Gating:</strong> Read-only viewers and customers cannot stage state-changing actions. Staged actions require explicit confirmation tokens before execution.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function AccountsTabBtn({ active, onClick, count }: { active: boolean; onClick: () => void; count: number }) {
  return (
    <button
      type="button"
      className={`drawer-tab-btn ${active ? "active" : ""}`}
      onClick={onClick}
    >
      Accounts ({count})
    </button>
  );
}
