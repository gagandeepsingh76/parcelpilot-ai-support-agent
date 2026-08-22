"use client";

import { Citation } from "../../lib/api";

interface ConflictBannerProps {
  conflicts: { kind: string; governs: string; sources: Citation[] }[];
}

export default function ConflictBanner({ conflicts }: ConflictBannerProps) {
  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="conflict-banner-container">
      {conflicts.map((c, idx) => {
        const isAgreementConflict = c.kind === "agreement_vs_general_policy";
        const isDeprecatedConflict = c.kind === "current_vs_deprecated";

        return (
          <div key={idx} className="conflict-banner-card">
            <div className="conflict-banner-icon-wrap">
              <span className="conflict-icon">⚠️</span>
            </div>
            <div className="conflict-banner-content">
              <div className="conflict-banner-title">
                <strong>Source Authority Conflict Detected</strong>
                <span className="conflict-kind-tag">
                  {isAgreementConflict
                    ? "Customer Agreement vs General Policy"
                    : isDeprecatedConflict
                    ? "Current vs Deprecated Policy"
                    : c.kind}
                </span>
              </div>
              <div className="conflict-governance-statement">
                <strong>Resolution Precedence:</strong>{" "}
                {isAgreementConflict
                  ? "The customer's signed enterprise agreement contains explicit contractual exceptions and strictly supersedes general support policy terms."
                  : isDeprecatedConflict
                  ? "CURRENT policies and SOPs supersede all DEPRECATED documents."
                  : c.governs}
              </div>
              {c.sources && c.sources.length > 0 && (
                <div className="conflict-sources-list">
                  <span className="conflict-sources-label">Compromising documents:</span>
                  <div className="conflict-source-chips">
                    {c.sources.map((s, sIdx) => (
                      <span
                        key={sIdx}
                        className={`conflict-chip ${s.status === "DEPRECATED" ? "chip-deprecated" : "chip-active"}`}
                      >
                        [{s.doc_id}] {s.title} ({s.status})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
