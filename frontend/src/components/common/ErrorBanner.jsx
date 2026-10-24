/**
 * Error Banner Component
 * Displays human-friendly simulation error alerts with dismiss controls.
 */

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.85rem 1.25rem',
        marginBottom: '1.25rem',
        borderRadius: '8px',
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        border: '1px solid rgba(239, 68, 68, 0.35)',
        color: '#fca5a5',
        fontSize: '0.9rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <AlertTriangle size={18} color="#ef4444" />
        <span>{error}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#fca5a5',
            cursor: 'pointer',
            padding: '2px',
          }}
          aria-label="Dismiss error"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
