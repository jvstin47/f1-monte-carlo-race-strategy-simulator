import React, { useState } from 'react';
import { Play, FastForward, CloudRain, ShieldAlert, RotateCcw } from 'lucide-react';
import MCTSTreeChart from './MCTSTreeChart';
import DriverSelector from './DriverSelector';

const COMPOUND_COLORS = {
  soft: '#ef4444',
  medium: '#eab308',
  hard: '#f8fafc',
  intermediate: '#22c55e',
  wet: '#3b82f6'
};

export default function RaceSimulatorTab({ trackId, driverId, onDriverChange, API_BASE, drivers }) {
  const [currentLap, setCurrentLap] = useState(1);
  const [riskAversion, setRiskAversion] = useState(0.2);
  const [stateOverrides, setStateOverrides] = useState({
    compound: 'medium',
    tire_age: 1,
    weather_state: 'dry',
    is_sc_active: false,
    stops_made: 0
  });

  const [loading, setLoading] = useState(false);
  const [mctsData, setMctsData] = useState(null);
  const [error, setError] = useState(null);

  const handleReplan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/optimize-mcts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track_id: trackId,
          driver_id: driverId,
          available_compounds: ['soft', 'medium', 'hard'],
          max_stops: 2,
          risk_aversion: riskAversion,
          weather_enabled: stateOverrides.weather_state !== 'dry',
          weather_start_state: stateOverrides.weather_state,
          sc_probability: 0.04,
          current_lap: currentLap,
          current_state_overrides: stateOverrides
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'MCTS request failed');
      setMctsData(data);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const advanceLap = () => {
    setCurrentLap(l => l + 1);
    setStateOverrides(prev => ({
      ...prev,
      tire_age: prev.tire_age + 1,
      is_sc_active: false
    }));
  };

  const toggleSC = () => {
    setStateOverrides(prev => ({ ...prev, is_sc_active: !prev.is_sc_active }));
  };

  const cycleWeather = () => {
    const cycle = { dry: 'damp', damp: 'wet', wet: 'dry' };
    setStateOverrides(prev => ({ ...prev, weather_state: cycle[prev.weather_state] }));
  };

  const executePit = (comp) => {
    setStateOverrides(prev => ({
      ...prev,
      compound: comp,
      tire_age: 1,
      stops_made: prev.stops_made + 1
    }));
  };

  const resetRace = () => {
    setCurrentLap(1);
    setStateOverrides({ compound: 'medium', tire_age: 1, weather_state: 'dry', is_sc_active: false, stops_made: 0 });
    setMctsData(null);
    setError(null);
  };

  const compoundColor = COMPOUND_COLORS[stateOverrides.compound] || '#fff';
  const weatherEmoji = stateOverrides.weather_state === 'dry' ? '☀️' : stateOverrides.weather_state === 'damp' ? '🌦️' : '🌧️';

  return (
    <>
      {/* Race State Card */}
      <div className="card race-sim-card">
        <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Play size={16} style={{ color: 'var(--f1-red)' }} />
            Race Simulator
          </span>
          <button onClick={resetRace} className="btn-icon" title="Reset Race">
            <RotateCcw size={14} />
          </button>
        </div>

        {/* 2x2 State Grid */}
        <div className="race-state-grid">
          <div className="race-stat">
            <span className="race-stat-label">Lap</span>
            <span className="race-stat-value">{currentLap}</span>
          </div>
          <div className="race-stat">
            <span className="race-stat-label">Tire</span>
            <span className="race-stat-value" style={{ color: compoundColor }}>
              {stateOverrides.compound.substring(0, 3).toUpperCase()}
              <span className="race-stat-sub">L{stateOverrides.tire_age}</span>
            </span>
          </div>
          <div className="race-stat">
            <span className="race-stat-label">Weather</span>
            <span className="race-stat-value">{weatherEmoji} {stateOverrides.weather_state}</span>
          </div>
          <div className={`race-stat ${stateOverrides.is_sc_active ? 'sc-active' : ''}`}>
            <span className="race-stat-label">Safety Car</span>
            <span className="race-stat-value" style={{ color: stateOverrides.is_sc_active ? '#eab308' : 'inherit' }}>
              {stateOverrides.is_sc_active ? '⚠️ SC' : '—'}
            </span>
          </div>
        </div>

        {/* Stops counter */}
        <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          Stops made: <strong style={{ color: '#fff' }}>{stateOverrides.stops_made}</strong>
        </div>

        {/* Action Buttons */}
        <div className="race-actions-row">
          <button className="btn-primary race-action-btn" onClick={advanceLap}>
            <FastForward size={14} /> Next Lap
          </button>
          <button className={`btn-secondary race-action-btn ${stateOverrides.is_sc_active ? 'sc-btn-active' : ''}`} onClick={toggleSC}>
            <ShieldAlert size={14} /> SC
          </button>
          <button className="btn-secondary race-action-btn" onClick={cycleWeather}>
            <CloudRain size={14} /> Weather
          </button>
        </div>

        {/* Pit Buttons */}
        <div className="pit-buttons-grid">
          {['soft', 'medium', 'hard', 'intermediate'].map(comp => (
            <button
              key={comp}
              className="pit-btn"
              onClick={() => executePit(comp)}
              style={{ borderColor: COMPOUND_COLORS[comp], color: COMPOUND_COLORS[comp] }}
            >
              <span className="pit-dot" style={{ background: COMPOUND_COLORS[comp] }}></span>
              {comp.substring(0, 3).toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Driver Selector */}
      <DriverSelector drivers={drivers} selectedDriver={driverId} onSelectDriver={onDriverChange} />

      {/* Risk Aversion */}
      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="form-group slider-container">
          <div className="form-label">
            <span>Risk Aversion</span>
            <span className="slider-val">{riskAversion.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1.0"
            step="0.1"
            value={riskAversion}
            onChange={(e) => setRiskAversion(parseFloat(e.target.value))}
          />
        </div>
      </div>

      {/* Run MCTS Button */}
      <button className="btn-primary" onClick={handleReplan} disabled={loading} style={{ width: '100%', marginTop: '1rem' }}>
        {loading ? <div className="spinner"></div> : <Play size={18} fill="currentColor" />}
        Run MCTS Re-Optimization
      </button>

      {error && (
        <div style={{ marginTop: '0.75rem', color: '#ef4444', fontSize: '0.8rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.5rem', borderRadius: '6px' }}>
          {error}
        </div>
      )}

      {/* Results */}
      {mctsData && (
        <>
          <div className="card" style={{ marginTop: '1rem' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#06b6d4', fontSize: '0.9rem' }}>📋 Recommended Policy</h4>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
              {mctsData.policy.map((rule, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>
                  <strong>{rule.condition}:</strong> {rule.action}
                </li>
              ))}
            </ul>
          </div>
          <MCTSTreeChart decisionTree={mctsData.decision_tree} />
        </>
      )}
    </>
  );
}
