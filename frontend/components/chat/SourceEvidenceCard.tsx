"use client";

import { useState } from "react";
import { FileText, Copy, Check } from "lucide-react";
import { Citation } from "../../lib/api";

interface SourceEvidenceProps {
  citations: Citation[];
}

export default function SourceEvidenceCard({ citations }: SourceEvidenceProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  if (!citations || citations.length === 0) return null;

  const copyCitation = (c: Citation, e: React.MouseEvent) => {
    e.stopPropagation();
    const citeText = `[${c.doc_id}] ${c.title} — ${c.section || c.heading || "General"} (${c.status}, Scope: ${c.customer_scope})`;
    navigator.clipboard.writeText(citeText);
    setCopiedId(c.doc_id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getTierInfo = (c: Citation) => {
    if (c.status === "DEPRECATED") {
      return {
        label: "DEPRECATED (Superseded)",
        tierClass: "deprecated",
        description: "Historical document — superseded by current policy",
      };
    }
    if (c.doc_type === "agreement") {
      return {
        label: "Tier 1: Customer Agreement",
        tierClass: "tier-1",
        description: "Authoritative contract terms — overrides general policy",
      };
    }
    if (c.doc_type === "sop") {
      return {
        label: "Tier 2: Current SOP",
        tierClass: "tier-2",
        description: "Standard Operating Procedure & deterministic rules",
      };
    }
    if (c.doc_type === "policy") {
      return {
        label: "Tier 3: Current Policy",
        tierClass: "tier-3",
        description: "Authoritative general support policy",
      };
    }
    return {
      label: "Tier 4: Product Guide",
      tierClass: "tier-4",
      description: "Product behavior and known operations guide",
    };
  };

  return (
    <div className="source-evidence-container">
      <div className="source-evidence-header">
        <div className="source-title-wrap">
          <FileText size={14} strokeWidth={1.75} className="source-icon" aria-hidden="true" />
          <span className="source-heading">Authoritative Source Citations</span>
          <span className="source-count">{citations.length} source{citations.length > 1 ? "s" : ""}</span>
        </div>
        <span className="source-authority-hint">Ranked by Authority Tier</span>
      </div>

      <div className="source-cards-grid">
        {citations.map((c, idx) => {
          const tier = getTierInfo(c);
          const isExpanded = expandedDoc === `${c.doc_id}-${idx}`;
          const isCopied = copiedId === c.doc_id;

          return (
            <div
              key={idx}
              className={`source-card ${tier.tierClass} ${c.status === "DEPRECATED" ? "is-deprecated" : ""}`}
              onClick={() => setExpandedDoc(isExpanded ? null : `${c.doc_id}-${idx}`)}
            >
              <div className="source-card-top">
                <div className="source-id-badge">[{c.doc_id}]</div>
                <div className="source-meta-head">
                  <div className="source-doc-title">{c.title}</div>
                  {(c.section || c.heading) && (
                    <div className="source-section-name">§ {c.section || c.heading}</div>
                  )}
                </div>
                <button
                  type="button"
                  className="source-copy-btn"
                  onClick={(e) => copyCitation(c, e)}
                  title="Copy citation reference"
                  aria-label={isCopied ? "Copied" : "Copy citation"}
                >
                  {isCopied ? (
                    <><Check size={11} strokeWidth={2.5} aria-hidden="true" /> Copied</>
                  ) : (
                    <><Copy size={11} strokeWidth={1.75} aria-hidden="true" /> Copy Cite</>
                  )}
                </button>
              </div>

              <div className="source-tags-row">
                <span className={`source-tier-pill ${tier.tierClass}`}>{tier.label}</span>
                <span className="source-scope-pill">
                  {c.customer_scope === "global" ? "Global Policy" : `Account Scope: ${c.customer_scope}`}
                </span>
                {c.version && <span className="source-version-pill">v{c.version}</span>}
              </div>

              {isExpanded && (
                <div className="source-expanded-drawer">
                  <div className="source-authority-rule-note">
                    <strong>Authority Rule:</strong> {tier.description}
                  </div>
                  {c.filename && <div className="source-filename">Source file: <code>{c.filename}</code></div>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
