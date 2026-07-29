import React from 'react';
import { GitMerge } from 'lucide-react';

export default function MCTSTreeChart({ decisionTree }) {
  if (!decisionTree || !decisionTree.candidates) return null;

  const totalVisits = decisionTree.candidates.reduce((sum, cand) => sum + cand.visit_count, 0);

  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <div className="card-title">
        <GitMerge size={18} style={{ color: '#06b6d4' }} />
        MCTS Decision Evaluation
      </div>
      <div style={{ marginBottom: '1rem', fontSize: '0.85rem', color: '#9ca3af' }}>
        Current State: {decisionTree.state_description}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {decisionTree.candidates.map((cand, idx) => {
          const confidence = ((cand.visit_count / totalVisits) * 100).toFixed(1);
          
          return (
            <div key={idx} style={{ 
              background: idx === 0 ? 'rgba(74, 222, 128, 0.1)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${idx === 0 ? 'rgba(74, 222, 128, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
              padding: '0.75rem', 
              borderRadius: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontWeight: '600', color: idx === 0 ? '#4ade80' : '#fff' }}>
                  {cand.action === 'stay_out' ? 'Stay Out' : `Pit for ${cand.action.split('_')[1].toUpperCase()}`}
                  {idx === 0 && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', background: '#4ade80', color: '#000', padding: '2px 6px', borderRadius: '12px' }}>Recommended</span>}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                  Expected Time: {cand.expected_time.toFixed(1)}s
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#fff' }}>
                  {confidence}%
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                  confidence ({cand.visit_count} rollouts)
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
