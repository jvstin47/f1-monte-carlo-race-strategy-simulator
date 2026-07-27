import React from 'react';
import { Trophy, Clock, Activity, BarChart2 } from 'lucide-react';

export default function StatsBanner({ mode, singleSummary, compareData }) {
  const formatTime = (seconds) => {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins}m ${secs.padStart(5, '0')}s`;
  };

  if (mode === 'single' && singleSummary) {
    return (
      <div className="stats-banner">
        <div className="stat-box">
          <div className="stat-label">Expected Total Time</div>
          <div className="stat-value">{formatTime(singleSummary.mean)}</div>
          <div className="stat-sub">Mean: {singleSummary.mean}s</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Median Finish Time</div>
          <div className="stat-value">{formatTime(singleSummary.median)}</div>
          <div className="stat-sub">P50 Benchmark</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Risk & Variability</div>
          <div className="stat-value">±{singleSummary.std_dev}s</div>
          <div className="stat-sub">Standard Deviation</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">90% Confidence Window</div>
          <div className="stat-value" style={{ fontSize: '1.1rem' }}>
            {singleSummary.p5}s - {singleSummary.p95}s
          </div>
          <div className="stat-sub">P5 to P95 Range</div>
        </div>
      </div>
    );
  }

  if (mode === 'compare' && compareData) {
    const isAWinning = compareData.win_probability_a >= 50;

    return (
      <div className="stats-banner">
        <div className="stat-box highlight-win">
          <div className="stat-label">Strategy A Win Rate</div>
          <div className="stat-value" style={{ color: 'var(--strat-a)' }}>
            {compareData.win_probability_a}%
          </div>
          <div className="stat-sub">Head-to-head win probability</div>
        </div>

        <div className="stat-box" style={{ borderColor: 'var(--strat-b)' }}>
          <div className="stat-label">Strategy B Win Rate</div>
          <div className="stat-value" style={{ color: 'var(--strat-b)' }}>
            {compareData.win_probability_b}%
          </div>
          <div className="stat-sub">Head-to-head win probability</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Strategy A Mean Time</div>
          <div className="stat-value">{formatTime(compareData.strategy_a_summary.mean)}</div>
          <div className="stat-sub">Std Dev: ±{compareData.strategy_a_summary.std_dev}s</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Strategy B Mean Time</div>
          <div className="stat-value">{formatTime(compareData.strategy_b_summary.mean)}</div>
          <div className="stat-sub">Std Dev: ±{compareData.strategy_b_summary.std_dev}s</div>
        </div>
      </div>
    );
  }

  return null;
}
