"use client";

import { AlertOctagon } from "lucide-react";

interface EscalationNoticeProps {
  reason?: string;
}

export default function EscalationNotice({ reason }: EscalationNoticeProps) {
  return (
    <div className="escalation-notice-container">
      <div className="escalation-notice-icon-wrap">
        <AlertOctagon size={18} strokeWidth={1.75} className="escalation-icon" aria-hidden="true" />
      </div>
      <div className="escalation-notice-content">
        <div className="escalation-title">
          <strong>Escalated to Human Support / Operations Specialist</strong>
        </div>
        <p className="escalation-text">
          {reason ||
            "This inquiry involves complex contractual provisions, missing dataset fields, or policy exceptions requiring human judgment."}
        </p>
        <div className="escalation-badge-strip">
          <span className="escalation-pill">SLA Clock Preserved</span>
          <span className="escalation-pill">Operations Queue Notified</span>
        </div>
      </div>
    </div>
  );
}
