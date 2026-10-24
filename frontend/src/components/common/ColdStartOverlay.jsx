/**
 * Cold-Start UX Overlay Component
 * Informs visitors when backend free-tier hosting is spinning up from idle state.
 */

import React from 'react';

export default function ColdStartOverlay({ isWaking }) {
  if (!isWaking) return null;

  return (
    <div className="cold-start-overlay">
      <div className="cold-start-modal">
        <div className="cold-start-spinner"></div>
        <h3>Waking up the simulation engine...</h3>
        <p>Free hosting takes ~30s to start on first visit</p>
      </div>
    </div>
  );
}
