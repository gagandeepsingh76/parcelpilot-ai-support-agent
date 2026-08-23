"use client";

import { useState } from "react";
import { Shield, Lock, Check, X } from "lucide-react";
import { PendingAction } from "../../lib/api";

interface ActionConfirmationCardProps {
  action: PendingAction;
  receipt?: Record<string, any> | null;
  onConfirm: (id: string) => Promise<void>;
  onCancel: (id: string) => Promise<void>;
}

export default function ActionConfirmationCard({
  action,
  receipt,
  onConfirm,
  onCancel,
}: ActionConfirmationCardProps) {
  const [busy, setBusy] = useState<"confirming" | "cancelling" | null>(null);

  const handleConfirm = async () => {
    if (busy || receipt) return;
    setBusy("confirming");
    try {
      await onConfirm(action.pending_action_id);
    } finally {
      setBusy(null);
    }
  };

  const handleCancel = async () => {
    if (busy || receipt) return;
    setBusy("cancelling");
    try {
      await onCancel(action.pending_action_id);
    } finally {
      setBusy(null);
    }
  };

  const getActionLabel = (type?: string) => {
    switch (type) {
      case "create_escalation":
        return "Create Human Escalation Ticket";
      case "update_ticket":
        return "Update Support Ticket";
      case "create_follow_up_task":
        return "Create Follow-up Task";
      default:
        return "State-Changing Action";
    }
  };

  const isExecuted = Boolean(receipt?.created || receipt?.updated || receipt?.executed_at);
  const isCancelled = Boolean(receipt?.cancelled);

  return (
    <div className={`action-card-container ${isExecuted ? "is-executed" : isCancelled ? "is-cancelled" : "is-pending"}`}>
      <div className="action-card-header">
        <div className="action-type-wrap">
          <Shield size={15} strokeWidth={1.75} className="action-shield-icon" aria-hidden="true" />
          <span className="action-type-title">{getActionLabel(action.action_type)}</span>
        </div>
        <div className="action-id-pill">{action.pending_action_id}</div>
      </div>

      <div className="action-summary-box">
        <p className="action-summary-text">{action.summary}</p>
      </div>

      {action.changes && typeof action.changes === "object" && Object.keys(action.changes).length > 0 && (
        <div className="action-changes-preview">
          <div className="action-changes-heading">Proposed Modifications (Preview):</div>
          <div className="action-changes-table">
            {Object.entries(action.changes).map(([field, val]: [string, any]) => {
              const isDiff = typeof val === "object" && val !== null && "from" in val && "to" in val;
              return (
                <div key={field} className="action-change-row">
                  <span className="action-field-name">{field}:</span>
                  {isDiff ? (
                    <span className="action-diff-val">
                      <span className="diff-old">{String(val.from || "none")}</span>
                      <span className="diff-arrow">→</span>
                      <span className="diff-new">{String(val.to)}</span>
                    </span>
                  ) : (
                    <span className="action-field-val">{typeof val === "object" ? JSON.stringify(val) : String(val)}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Confirmation buttons or Execution receipt */}
      {!receipt ? (
        <div className="action-decision-bar">
          <div className="action-safety-notice">
            <Lock size={13} strokeWidth={2} aria-hidden="true" />
            <span><strong>Gated Execution:</strong> This action will only be executed upon explicit confirmation.</span>
          </div>
          <div className="action-btn-group">
            <button
              type="button"
              className="action-confirm-btn"
              onClick={handleConfirm}
              disabled={Boolean(busy)}
            >
              <Check size={14} strokeWidth={2.5} aria-hidden="true" />
              {busy === "confirming" ? "Executing..." : "Confirm & Execute"}
            </button>
            <button
              type="button"
              className="action-cancel-btn"
              onClick={handleCancel}
              disabled={Boolean(busy)}
            >
              {busy === "cancelling" ? "Cancelling..." : "Cancel"}
            </button>
          </div>
        </div>
      ) : isExecuted ? (
        <div className="action-receipt-box success">
          <div className="receipt-head">
            <Check size={14} strokeWidth={2.5} className="receipt-check" aria-hidden="true" />
            <strong>Action Successfully Executed & Audited</strong>
          </div>
          <div className="receipt-details">
            {receipt.created && (
              <div>Created {receipt.created.table}: <code>{receipt.created.ticket_id || receipt.created.task_id}</code></div>
            )}
            {receipt.updated && (
              <div>Updated {receipt.updated.table} <code>{receipt.updated.ticket_id}</code> (Fields: {receipt.updated.fields?.join(", ")})</div>
            )}
            {receipt.executed_at && (
              <div className="receipt-time">Timestamp: {receipt.executed_at} · Audit Log Recorded</div>
            )}
          </div>
        </div>
      ) : (
        <div className="action-receipt-box cancelled">
          <X size={14} strokeWidth={2.5} className="receipt-cancel-icon" aria-hidden="true" />
          <span>Action was cancelled — no changes were made to system records.</span>
        </div>
      )}
    </div>
  );
}
