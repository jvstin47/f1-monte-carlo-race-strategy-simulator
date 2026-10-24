import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Cell
} from 'recharts';
import { Zap } from 'lucide-react';

const CustomTooltipUndercut = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const deltaText = data.pit_delta_laps < 0 
      ? `Pitted ${Math.abs(data.pit_delta_laps)} lap(s) BEFORE rival (Undercut)`
      : data.pit_delta_laps === 0 
      ? `Pitted on SAME lap as rival`
      : `Pitted ${data.pit_delta_laps} lap(s) AFTER rival (Overcut)`;

    return (
      <div className="custom-tooltip">
        <div className="tooltip-title">{deltaText}</div>
        <div className="tooltip-row" style={{ color: '#06b6d4' }}>
          <span>Track Position Win Rate:</span>
          <span>{data.undercut_win_pct}%</span>
        </div>
        <div className="tooltip-row" style={{ color: '#cbd5e1' }}>
          <span>Mean Finish Gap:</span>
          <span>{data.mean_gap_seconds > 0 ? `+${data.mean_gap_seconds}s ahead` : `${data.mean_gap_seconds}s behind`}</span>
        </div>
      </div>
    );
  }
  return null;
};

export default function UndercutChart({ curveData }) {
  if (!curveData || curveData.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <div className="card-title">
        <Zap size={18} style={{ color: '#06b6d4' }} />
        Undercut Effectiveness Curve (Track Position Gain %)
      </div>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
        Probability of coming out ahead after both pit stops based on pitting $X$ laps before or after your rival.
      </p>

      <div style={{ width: '100%', height: '360px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={curveData} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="pit_delta_laps"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickFormatter={(val) => val === 0 ? 'Same Lap' : `${val > 0 ? '+' : ''}${val} Laps`}
              label={{ value: 'Pit Timing Relative to Rival (Laps)', position: 'insideBottom', offset: -10, fill: '#94a3b8', fontSize: 12 }}
            />
            <YAxis
              stroke="#64748b"
              domain={[0, 100]}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickFormatter={(val) => `${val}%`}
              label={{ value: 'Track Position Win Probability (%)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltipUndercut />} />
            <ReferenceLine y={50} stroke="rgba(255,255,255,0.2)" strokeDasharray="3 3" label={{ value: "50% Break-Even", fill: "#64748b", fontSize: 11 }} />
            
            <Bar dataKey="undercut_win_pct" radius={[4, 4, 0, 0]} name="Win %">
              {curveData.map((entry, index) => {
                const isUndercutWin = entry.undercut_win_pct >= 50;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={isUndercutWin ? '#06b6d4' : '#ec4899'}
                    opacity={entry.pit_delta_laps === 0 ? 0.4 : 0.85}
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
