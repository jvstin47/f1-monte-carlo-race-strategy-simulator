import React from 'react';
import { Activity } from 'lucide-react';

const TRIGGER_LABELS = {
  pit_stop: 'a pit stop being evaluated',
  safety_car: 'an active Safety Car',
  weather: 'non-dry weather',
  late_race: 'the decision being late in the race',
  adaptive_refinement: 'top-candidate refinement',
  classic_mode: 'classic (v4) mode -- every branch simulated'
};

export default function MCTSDiagnosticsPanel({ diagnostics, policy }) {
  if (!diagnostics) return null;

  const { nodes_created, heuristic_evaluations, high_fidelity_rollouts, trigger_counts } = diagnostics;
  const total = (heuristic_evaluations || 0) + (high_fidelity_rollouts || 0);
  const hfPct = total > 0 ? Math.round((high_fidelity_rollouts / total) * 100) : 0;
  const heuristicPct = 100 - hfPct;

  const sortedTriggers = Object.entries(trigger_counts || {}).sort((a, b) => b[1] - a[1]);
  const topTrigger = sortedTriggers[0];
  const recommendedAction = policy && policy[0] ? policy[0].action : null;

  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <div className="card-title">
        <Activity size={18} style={{ color: '#06b6d4' }} />
        Search Diagnostics
      </div>

      {recommendedAction && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          <strong style={{ color: '#fff' }}>{recommendedAction}</strong> was evaluated across{' '}
          <strong style={{ color: '#fff' }}>{nodes_created}</strong> branch{nodes_created === 1 ? '' : 'es'} --{' '}
          {hfPct}% escalated to a real Monte Carlo simulation
          {topTrigger ? `, most often because of ${TRIGGER_LABELS[topTrigger[0]] || topTrigger[0]}` : ''}.
        </p>
      )}

      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
          <span>Cheap heuristic ({heuristicPct}%)</span>
          <span>Real simulation ({hfPct}%)</span>
        </div>
        <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: 'rgba(255,255,255,0.06)' }}>
          <div style={{ width: `${heuristicPct}%`, background: 'var(--strat-a)' }} />
          <div style={{ width: `${hfPct}%`, background: 'var(--f1-red)' }} />
        </div>
      </div>

      {sortedTriggers.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {sortedTriggers.map(([trigger, count]) => (
            <span
              key={trigger}
              style={{
                fontSize: '0.7rem',
                padding: '2px 8px',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--text-muted)'
              }}
              title={TRIGGER_LABELS[trigger] || trigger}
            >
              {trigger}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
