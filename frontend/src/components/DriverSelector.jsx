import React, { useState, useEffect } from 'react';
import { User, Info } from 'lucide-react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? '' 
  : 'http://127.0.0.1:8005';

export default function DriverSelector({ selectedDriver, onSelectDriver }) {
  const [drivers, setDrivers] = useState({});

  useEffect(() => {
    fetch(`${API_BASE}/drivers`)
      .then(res => res.json())
      .then(data => setDrivers(data))
      .catch(err => console.error("Failed to load drivers", err));
  }, []);

  const current = drivers[selectedDriver];

  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <div className="card-title">
        <User size={18} style={{ color: '#06b6d4' }} />
        Driver Profile
      </div>
      
      <div className="form-group">
        <select 
          className="select-box"
          value={selectedDriver}
          onChange={(e) => onSelectDriver(e.target.value)}
        >
          {Object.entries(drivers).map(([key, drv]) => (
            <option key={key} value={key}>
              {drv.name} {drv.team !== "None" ? `(${drv.team})` : ""}
            </option>
          ))}
        </select>
      </div>

      {current && (
        <div className="driver-stats" style={{ display: 'flex', gap: '1rem', marginTop: '1rem', fontSize: '0.85rem' }}>
          <div className="stat-pill" style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px', flex: 1 }}>
            <span style={{ opacity: 0.6, display: 'block', fontSize: '0.75rem' }}>Pace Offset</span>
            <span style={{ fontWeight: '600', color: current.pace_offset < 0 ? '#4ade80' : current.pace_offset > 0 ? '#ef4444' : '#fff' }}>
              {current.pace_offset > 0 ? '+' : ''}{current.pace_offset.toFixed(2)}s / lap
            </span>
          </div>
          <div className="stat-pill" style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px', flex: 1 }}>
            <span style={{ opacity: 0.6, display: 'block', fontSize: '0.75rem' }}>Consistency</span>
            <span style={{ fontWeight: '600' }}>
              {current.consistency < 0.10 ? 'High' : current.consistency > 0.14 ? 'Low' : 'Avg'} (σ={current.consistency.toFixed(2)})
            </span>
          </div>
          {current.data_confidence && current.data_confidence !== 'High' && (
             <div className="stat-pill" style={{ background: 'rgba(234, 179, 8, 0.1)', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '0.5rem', borderRadius: '4px', flex: 0.5, display: 'flex', alignItems: 'center', justifyContent: 'center' }} title={`Data Confidence: ${current.data_confidence} (Due to partial season or high variance)`}>
               <span style={{ color: '#eab308', display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.75rem', fontWeight: 'bold' }}>
                 ⚠️ {current.data_confidence} Conf.
               </span>
             </div>
          )}
        </div>
      )}

      <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: '#9ca3af', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
        <Info size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
        <i>Note: These are illustrative estimates derived from teammate-relative race pace, not official skill ratings. Car performance dominates raw lap time.</i>
      </div>
    </div>
  );
}
