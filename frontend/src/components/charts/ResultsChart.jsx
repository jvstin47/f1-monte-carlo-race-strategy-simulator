import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine
} from 'recharts';
import { BarChart3 } from 'lucide-react';

const CustomTooltipSingle = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const mins = Math.floor(data.bin_center / 60);
    const secs = (data.bin_center % 60).toFixed(2);
    return (
      <div className="custom-tooltip">
        <div className="tooltip-title">Race Time: {mins}m {secs}s ({data.bin_center}s)</div>
        <div className="tooltip-row" style={{ color: '#06b6d4' }}>
          <span>Simulations:</span>
          <span>{data.count.toLocaleString()} runs</span>
        </div>
      </div>
    );
  }
  return null;
};

const CustomTooltipCompare = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const mins = Math.floor(data.bin_center / 60);
    const secs = (data.bin_center % 60).toFixed(2);
    return (
      <div className="custom-tooltip">
        <div className="tooltip-title">Race Time: {mins}m {secs}s ({data.bin_center}s)</div>
        {payload.map((entry, idx) => (
          <div key={idx} className="tooltip-row" style={{ color: entry.color }}>
            <span>{entry.name}:</span>
            <span>{entry.value.toLocaleString()} runs</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function ResultsChart({ mode, data, singleSummary }) {
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return (
      <div className="card" style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Configure parameters and click Simulate to view distributions.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">
        <BarChart3 size={18} />
        {mode === 'single' ? 'Monte Carlo Race Time Distribution (10,000 Runs)' : 'Strategy Outcome Comparison Overlay'}
      </div>

      <div style={{ width: '100%', height: '380px', marginTop: '1rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          {mode === 'single' ? (
            <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <defs>
                <linearGradient id="singleGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.9} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.2} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="bin_center"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                tickFormatter={(val) => `${Math.floor(val / 60)}m ${(val % 60).toFixed(0)}s`}
                label={{ value: 'Total Race Duration (Seconds)', position: 'insideBottom', offset: -10, fill: '#94a3b8', fontSize: 12 }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                label={{ value: 'Frequency (Runs)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltipSingle />} />
              {singleSummary && (
                <ReferenceLine
                  x={singleSummary.mean}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{ value: `Mean: ${singleSummary.mean}s`, fill: '#ef4444', fontSize: 12, position: 'top' }}
                />
              )}
              <Bar dataKey="count" fill="url(#singleGradient)" radius={[4, 4, 0, 0]} name="Frequency" />
            </BarChart>
          ) : (
            <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="bin_center"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                tickFormatter={(val) => `${Math.floor(val / 60)}m ${(val % 60).toFixed(0)}s`}
                label={{ value: 'Total Race Duration (Seconds)', position: 'insideBottom', offset: -10, fill: '#94a3b8', fontSize: 12 }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                label={{ value: 'Frequency (Runs)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltipCompare />} />
              <Legend
                wrapperStyle={{ paddingTop: '10px' }}
                formatter={(value) => <span style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{value}</span>}
              />
              <Bar dataKey="count_a" fill="#06b6d4" opacity={0.75} radius={[4, 4, 0, 0]} name="Strategy A" />
              <Bar dataKey="count_b" fill="#ec4899" opacity={0.75} radius={[4, 4, 0, 0]} name="Strategy B" />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
