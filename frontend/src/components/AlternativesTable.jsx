import React from 'react';

export default function AlternativesTable({ alternatives, optimalTime }) {
  if (!alternatives || alternatives.length === 0) return null;

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-title">Top Strategy Alternatives</div>
      
      <table className="alternatives-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Strategy</th>
            <th>Expected Time</th>
            <th>Delta to Optimal</th>
          </tr>
        </thead>
        <tbody>
          {alternatives.map((alt, idx) => {
            const mins = Math.floor(alt.expected_time / 60);
            const secs = (alt.expected_time % 60).toFixed(2);
            
            const isOptimal = idx === 0; // The first item should be the optimal one, or we highlight rank 1
            
            return (
              <tr key={idx} className={isOptimal ? 'optimal' : ''}>
                <td>#{alt.rank}</td>
                <td>
                  {alt.stints.map((stint, sIdx) => (
                    <React.Fragment key={sIdx}>
                      <span className={`strat-pill ${stint.compound.charAt(0).toUpperCase()}`}>
                        {stint.compound.charAt(0).toUpperCase()}
                      </span>
                      {sIdx < alt.stints.length - 1 && <span style={{color: 'var(--text-muted)', margin: '0 4px'}}>→</span>}
                    </React.Fragment>
                  ))}
                  <span style={{color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: '8px'}}>
                    ({alt.stints.length - 1}-Stop)
                  </span>
                </td>
                <td>{mins}m {secs}s</td>
                <td style={{ color: isOptimal ? 'var(--strat-a)' : 'var(--text-muted)' }}>
                  {alt.delta_to_optimal > 0 ? `+${alt.delta_to_optimal.toFixed(2)}s` : '-'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
