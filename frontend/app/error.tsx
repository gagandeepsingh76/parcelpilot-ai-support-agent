"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service if needed
    console.error("Global Error Boundary Caught:", error);
  }, [error]);

  return (
    <div className="shell" style={{ justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: '24px' }}>
      <div className="error-box" style={{ maxWidth: '600px', padding: '32px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h2 style={{ fontSize: '24px', margin: 0, color: 'var(--red)' }}>Something went wrong</h2>
        <p style={{ color: 'var(--text)', opacity: 0.8 }}>
          An unexpected application error occurred. This could be due to a network disruption or an internal rendering fault.
        </p>
        <div style={{ background: 'var(--panel-elevated)', padding: '12px', borderRadius: '8px', fontSize: '13px', color: 'var(--muted)', overflowX: 'auto' }}>
          <code>{error.message || "Unknown Error"}</code>
        </div>
        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <button
            onClick={() => reset()}
            style={{
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            Try Again
          </button>
          <Link href="/">
            <button
              style={{
                background: 'transparent',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                padding: '10px 20px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Return Home
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
