import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { CloudRain } from 'lucide-react';

const CustomTooltip = ({ active, payload }) => {
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
            <span>{entry.value ? entry.value.toLocaleString() : 0} runs</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function WeatherVarianceChart({ dryData, weatherData }) {
  // Merge the two arrays by bin_center
  const mergedData = useMemo(() => {
    if (!dryData || !weatherData) return [];
    
    const map = new Map();
    dryData.forEach(d => {
      map.set(d.bin_center, { bin_center: d.bin_center, count_dry: d.count, count_weather: 0 });
    });
    
    weatherData.forEach(d => {
      if (map.has(d.bin_center)) {
        map.get(d.bin_center).count_weather = d.count;
      } else {
        map.set(d.bin_center, { bin_center: d.bin_center, count_dry: 0, count_weather: d.count });
      }
    });
    
    return Array.from(map.values()).sort((a, b) => a.bin_center - b.bin_center);
  }, [dryData, weatherData]);

  if (mergedData.length === 0) {
    return (
      <div className="card" style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Configure weather parameters and click Simulate to view variance.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">
        <CloudRain size={18} />
        Weather Variance Analysis (10,000 Runs)
      </div>

      <div style={{ width: '100%', height: '380px', marginTop: '1rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={mergedData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
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
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => <span style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{value}</span>}
            />
            <Bar dataKey="count_dry" fill="#06b6d4" opacity={0.75} radius={[4, 4, 0, 0]} name="Guaranteed Dry" />
            <Bar dataKey="count_weather" fill="#8b5cf6" opacity={0.75} radius={[4, 4, 0, 0]} name="Weather Uncertainty" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
