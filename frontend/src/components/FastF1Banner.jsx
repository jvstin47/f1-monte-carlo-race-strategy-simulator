import React from 'react';
import { Database, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function FastF1Banner({ calibrationData, simMeanTime }) {
  if (!calibrationData) return null;

  const actualTime = calibrationData.validation_actual_winner_time_seconds || 5635.8;
  const actualFormatted = `${Math.floor(actualTime / 3600)}h ${Math.floor((actualTime % 3600) / 60)}m ${(actualTime % 60).toFixed(1)}s`;
  
  const simFormatted = simMeanTime 
    ? `${Math.floor(simMeanTime / 3600)}h ${Math.floor((simMeanTime % 3600) / 60)}m ${(simMeanTime % 60).toFixed(1)}s`
    : '--';

  const diffSeconds = simMeanTime ? Math.abs(simMeanTime - actualTime).toFixed(1) : null;

  return (
    <div className="card" style={{ borderColor: 'rgba(6, 182, 212, 0.3)', marginBottom: '1.5rem' }}>
      <div className="card-title" style={{ color: 'var(--strat-a)' }}>
        <Database size={18} />
        FastF1 Real Data Calibration (2023 Bahrain Grand Prix)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
        <div className="stat-box">
          <div className="stat-label">Real Recorded Race Winner</div>
          <div className="stat-value" style={{ fontSize: '1.2rem' }}>{actualFormatted}</div>
          <div className="stat-sub">{calibrationData.validation_actual_winner_driver}</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Monte Carlo Predicted Mean</div>
          <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--strat-a)' }}>{simFormatted}</div>
          <div className="stat-sub">{diffSeconds ? `Variance: ±${diffSeconds}s across 57 laps` : 'Run simulation to compare'}</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Calibrated Pit Loss</div>
          <div className="stat-value" style={{ fontSize: '1.2rem' }}>{calibrationData.pit_stop_time_loss}s</div>
          <div className="stat-sub">Real telemetry pit lane delta</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Data Calibration Source</div>
          <div className="stat-value" style={{ fontSize: '1.0rem', color: '#eab308' }}>
            {calibrationData.source || 'FastF1 Empirical Cache'}
          </div>
          <div className="stat-sub">Linear + Quadratic Wear Curves</div>
        </div>
      </div>
    </div>
  );
}
