import React from 'react';

export default function StintTimeline({ stints, expectedTime, numLaps }) {
  if (!stints || stints.length === 0) return null;

  const mins = Math.floor(expectedTime / 60);
  const secs = (expectedTime % 60).toFixed(2);

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-title" style={{ marginBottom: '0.5rem' }}>Optimal Strategy Timeline</div>
      <div className="timeline-info">
        <span>Expected Total Time: {mins}m {secs}s</span>
        <span>{numLaps} Laps</span>
      </div>
      
      <div className="stint-timeline">
        {stints.map((stint, idx) => {
          const stintLaps = stint.end_lap - stint.start_lap + 1;
          const widthPct = (stintLaps / numLaps) * 100;
          return (
            <div 
              key={idx} 
              className={`stint-bar ${stint.compound}`} 
              style={{ width: `${widthPct}%` }}
              title={`Lap ${stint.start_lap} - ${stint.end_lap} (${stint.compound})`}
            >
              {stint.compound.charAt(0).toUpperCase()}
              {idx < stints.length - 1 && (
                <div className="pit-marker" />
              )}
            </div>
          );
        })}
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <span>Lap 1</span>
        <span>Lap {numLaps}</span>
      </div>
    </div>
  );
}
