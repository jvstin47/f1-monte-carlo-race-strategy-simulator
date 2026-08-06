import React from 'react';
import { User } from 'lucide-react';

export default function DriverImpactChart({ compareData, drivers = {} }) {
  if (!compareData || !compareData.strategy_a || !compareData.strategy_b) return null;

  // Calculate impact only if strategies are identical but drivers are different
  const a = compareData.strategy_a;
  const b = compareData.strategy_b;

  const sameStrat = a.compound_1 === b.compound_1 && a.compound_2 === b.compound_2 && a.pit_lap === b.pit_lap;
  const diffDriver = a.driver_id !== b.driver_id;

  if (!sameStrat || !diffDriver) {
    return null; // Not a driver impact comparison
  }

  const meanA = compareData.strategy_a_summary.mean;
  const meanB = compareData.strategy_b_summary.mean;
  const diff = meanB - meanA;

  const driverA = drivers[a.driver_id];
  const driverB = drivers[b.driver_id];
  const driverNameA = driverA?.name || a.driver_id.toUpperCase();
  const driverNameB = driverB?.name || b.driver_id.toUpperCase();

  const winProbA = compareData.win_probability_a;

  const characterLine = (drv) => {
    if (!drv) return null;
    const pace = drv.pace_offset < 0 ? `${drv.pace_offset.toFixed(2)}s/lap (quicker)` : drv.pace_offset > 0 ? `+${drv.pace_offset.toFixed(2)}s/lap (slower)` : 'Neutral pace';
    const consistency = drv.consistency < 0.10 ? 'high consistency' : drv.consistency > 0.14 ? 'low consistency' : 'average consistency';
    return `${pace}, ${consistency} (σ=${drv.consistency.toFixed(2)})`;
  };

  return (
    <div className="card" style={{ marginTop: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)' }}>
      <div className="card-title">
        <User size={18} style={{ color: '#06b6d4' }} />
        Driver Impact Analysis
      </div>

      <div style={{ textAlign: 'center', margin: '1rem 0' }}>
        <h3 style={{ margin: 0, fontSize: '1.5rem', color: diff > 0 ? '#4ade80' : '#ef4444' }}>
          {Math.abs(diff).toFixed(1)}s Difference
        </h3>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#9ca3af' }}>
          {diff > 0 ? `${driverNameA} is faster than ${driverNameB} on the same strategy.` : `${driverNameB} is faster than ${driverNameA} on the same strategy.`}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <div style={{ flex: 1, padding: '1rem', background: 'var(--strat-a)', borderRadius: '8px', color: '#000', textAlign: 'center' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>{winProbA}%</div>
          <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>Win Prob ({driverNameA})</div>
        </div>
        <div style={{ flex: 1, padding: '1rem', background: 'var(--strat-b)', borderRadius: '8px', color: '#000', textAlign: 'center' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>{(100 - winProbA).toFixed(1)}%</div>
          <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>Win Prob ({driverNameB})</div>
        </div>
      </div>

      {(driverA || driverB) && (
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', fontSize: '0.75rem', color: '#9ca3af' }}>
          <div style={{ flex: 1, textAlign: 'center' }}>{characterLine(driverA)}</div>
          <div style={{ flex: 1, textAlign: 'center' }}>{characterLine(driverB)}</div>
        </div>
      )}
    </div>
  );
}
