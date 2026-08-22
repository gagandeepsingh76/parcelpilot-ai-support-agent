"use client";

import { useState } from "react";
import { ToolUsed } from "../../lib/api";

interface ToolActivityTimelineProps {
  tools: ToolUsed[];
}

export default function ToolActivityTimeline({ tools }: ToolActivityTimelineProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(true);

  if (!tools || tools.length === 0) return null;

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const getToolIcon = (tool: string) => {
    switch (tool) {
      case "search_documents":
        return "📚";
      case "data_lookup":
        return "⚡";
      case "stage_action":
        return "🛡️";
      default:
        return "⚙️";
    }
  };

  const getToolCategory = (tool: string) => {
    switch (tool) {
      case "search_documents":
        return "Document Retrieval (RAG)";
      case "data_lookup":
        return "Structured Data & Calculations";
      case "stage_action":
        return "Action Staging (Gated)";
      default:
        return "System Tool";
    }
  };

  return (
    <div className="tool-timeline-container">
      <div className="tool-timeline-header" onClick={() => setShowAll(!showAll)}>
        <div className="tool-timeline-title">
          <span className="tool-pulse-dot" />
          <span>Agent Activity Timeline</span>
          <span className="tool-count-badge">{tools.length} step{tools.length > 1 ? "s" : ""} executed</span>
        </div>
        <button
          type="button"
          className="tool-toggle-btn"
          aria-label={showAll ? "Collapse tool activity" : "Expand tool activity"}
        >
          {showAll ? "Hide details" : "Show details"}
        </button>
      </div>

      {showAll && (
        <div className="tool-steps-list">
          {tools.map((t, idx) => {
            const isError = t.status === "error" || (typeof t.output === "object" && t.output !== null && "error" in t.output);
            const isExpanded = expandedIndex === idx;

            return (
              <div key={idx} className={`tool-step-item ${isError ? "has-error" : "success"}`}>
                <div className="tool-step-main" onClick={() => toggleExpand(idx)}>
                  <div className="tool-step-icon-wrap">
                    <span className="tool-step-icon">{getToolIcon(t.tool)}</span>
                  </div>
                  <div className="tool-step-info">
                    <div className="tool-step-label-row">
                      <span className="tool-step-label">{t.label || t.tool}</span>
                      <span className={`tool-step-status-tag ${isError ? "error" : "success"}`}>
                        {isError ? "Denied / Error" : "Completed"}
                      </span>
                    </div>
                    <div className="tool-step-meta">
                      <span className="tool-step-category">{getToolCategory(t.tool)}</span>
                      <span className="tool-step-inspect-hint">
                        {isExpanded ? "Click to collapse" : "Click to inspect parameters & payload"}
                      </span>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="tool-step-detail-panel">
                    <div className="tool-detail-section">
                      <div className="tool-detail-heading">Input Parameters:</div>
                      <pre className="tool-code-block">{JSON.stringify(t.input, null, 2)}</pre>
                    </div>
                    {t.output && (
                      <div className="tool-detail-section">
                        <div className="tool-detail-heading">Structured Output:</div>
                        <pre className="tool-code-block">{typeof t.output === "string" ? t.output : JSON.stringify(t.output, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
