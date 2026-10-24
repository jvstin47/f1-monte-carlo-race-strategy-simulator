import React from 'react';
import { Sliders, Plus, Trash2 } from 'lucide-react';

const ALL_COMPOUNDS = [
  { id: 'soft', name: 'Soft', colorClass: 'selected-soft', dotClass: 'dot-soft' },
  { id: 'medium', name: 'Medium', colorClass: 'selected-medium', dotClass: 'dot-medium' },
  { id: 'hard', name: 'Hard', colorClass: 'selected-hard', dotClass: 'dot-hard' },
  { id: 'intermediate', name: 'Inter', colorClass: 'selected-intermediate', dotClass: 'dot-intermediate' },
  { id: 'wet', name: 'Wet', colorClass: 'selected-wet', dotClass: 'dot-wet' },
];

export default function StrategyForm({ strategy, setStrategy, title = "Strategy Settings", accentColor, showSafetyCarControls = true, weatherEnabled = false }) {
  const visibleCompounds = weatherEnabled ? ALL_COMPOUNDS : ALL_COMPOUNDS.filter(c => ['soft', 'medium', 'hard'].includes(c.id));
  // Ensure strategy has compounds array & pit_laps array
  const compounds = strategy.compounds || [strategy.compound_1 || 'soft', strategy.compound_2 || 'medium'];
  const pitLaps = strategy.pit_laps || [strategy.pit_lap || 18];

  const updateCompounds = (newComps) => {
    setStrategy(prev => ({
      ...prev,
      compounds: newComps,
      compound_1: newComps[0] || 'soft',
      compound_2: newComps[1] || 'medium'
    }));
  };

  const updatePitLaps = (newLaps) => {
    setStrategy(prev => ({
      ...prev,
      pit_laps: newLaps,
      pit_lap: newLaps[0] || 18
    }));
  };

  const handleCompoundChange = (idx, val) => {
    const next = [...compounds];
    next[idx] = val;
    updateCompounds(next);
  };

  const handlePitLapChange = (idx, val) => {
    const next = [...pitLaps];
    next[idx] = val;
    updatePitLaps(next);
  };

  const addStint = () => {
    if (pitLaps.length >= 4) return; // Max 4 pit stops (5 stints)
    const lastPit = pitLaps[pitLaps.length - 1] || 18;
    const nextPit = Math.min(strategy.num_laps - 2, lastPit + 14);
    updatePitLaps([...pitLaps, nextPit]);
    updateCompounds([...compounds, 'hard']);
  };

  const removeStint = (idx) => {
    if (pitLaps.length <= 1) return; // Minimum 1 pit stop
    const nextLaps = pitLaps.filter((_, i) => i !== idx);
    const nextComps = compounds.filter((_, i) => i !== idx + 1);
    updatePitLaps(nextLaps);
    updateCompounds(nextComps);
  };

  const handleChange = (field, val) => {
    setStrategy(prev => ({ ...prev, [field]: val }));
  };

  return (
    <div className="card" style={{ borderColor: accentColor ? accentColor : undefined }}>
      <div className="card-title" style={{ color: accentColor, justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sliders size={18} />
          {title}
        </div>
        <span style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px', color: 'var(--text-muted)' }}>
          {pitLaps.length}-Stop Strategy
        </span>
      </div>

      {/* Stints & Pit Stops Builder */}
      {compounds.map((comp, idx) => {
        const isLast = idx === compounds.length - 1;
        const currentPitLap = pitLaps[idx];

        return (
          <div key={idx} style={{ marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: isLast ? 'none' : '1px dashed rgba(255,255,255,0.08)' }}>
            <div className="form-group">
              <label className="form-label">
                Stint {idx + 1} Compound
              </label>
              <div className="compound-selector">
                {visibleCompounds.map(c => (
                  <button
                    key={c.id}
                    type="button"
                    className={`compound-pill ${comp === c.id ? c.colorClass : ''}`}
                    onClick={() => handleCompoundChange(idx, c.id)}
                  >
                    <span className={`tire-dot ${c.dotClass}`}></span>
                    {c.name}
                  </button>
                ))}
              </div>
            </div>

            {!isLast && (
              <div className="form-group" style={{ marginTop: '0.75rem' }}>
                <div className="form-label" style={{ color: 'var(--f1-red)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>Pit Stop {idx + 1}</span>
                    {pitLaps.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeStint(idx)}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: 0 }}
                        title="Remove pit stop"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                  <span className="slider-val">Lap {currentPitLap}</span>
                </div>
                <div className="slider-container">
                  <input
                    type="range"
                    min={idx === 0 ? 2 : pitLaps[idx - 1] + 2}
                    max={strategy.num_laps - 2}
                    value={currentPitLap}
                    onChange={(e) => handlePitLapChange(idx, parseInt(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Add Pit Stop Button */}
      {pitLaps.length < 4 && (
        <button
          type="button"
          onClick={addStint}
          style={{
            width: '100%',
            padding: '0.5rem',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px dashed var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-muted)',
            fontWeight: 600,
            fontSize: '0.85rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem',
            marginBottom: '1.25rem'
          }}
        >
          <Plus size={14} />
          Add Pit Stop ({pitLaps.length + 1}-Stop)
        </button>
      )}

      {/* Safety Car Controls (v2) */}
      {showSafetyCarControls && (
        <div style={{ marginTop: '0.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div className="form-group">
            <div className="form-label">
              <span>Safety Car Prob / Lap</span>
              <span className="slider-val">{(strategy.sc_probability * 100).toFixed(0)}%</span>
            </div>
            <div className="slider-container">
              <input
                type="range"
                min={0}
                max={0.15}
                step={0.01}
                value={strategy.sc_probability}
                onChange={(e) => handleChange('sc_probability', parseFloat(e.target.value))}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={strategy.is_reactive_sc}
                onChange={(e) => handleChange('is_reactive_sc', e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--f1-red)' }}
              />
              <span>Pit Reactively Under Safety Car</span>
            </label>
          </div>
        </div>
      )}

      {/* Weather Controls */}
      {weatherEnabled && (
        <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={strategy.weather_enabled || false}
                onChange={(e) => handleChange('weather_enabled', e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--f1-red)' }}
              />
              <span>Enable Weather Simulation</span>
            </label>
          </div>

          {(strategy.weather_enabled) && (
            <>
              <div className="form-group">
                <label className="form-label">Start State</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {['dry', 'wet', 'mixed'].map(state => (
                    <button
                      key={state}
                      type="button"
                      onClick={() => handleChange('weather_start_state', state)}
                      style={{
                        flex: 1,
                        padding: '0.4rem',
                        background: strategy.weather_start_state === state ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.03)',
                        border: `1px solid ${strategy.weather_start_state === state ? 'var(--tire-wet)' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-sm)',
                        color: strategy.weather_start_state === state ? 'var(--tire-wet)' : 'var(--text-muted)',
                        textTransform: 'capitalize',
                        fontSize: '0.85rem'
                      }}
                    >
                      {state}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <div className="form-label">
                  <span>Weather Pit Threshold</span>
                  <span className="slider-val">{strategy.weather_pit_threshold || 2} Laps</span>
                </div>
                <div className="slider-container">
                  <input
                    type="range"
                    min={1}
                    max={6}
                    step={1}
                    value={strategy.weather_pit_threshold || 2}
                    onChange={(e) => handleChange('weather_pit_threshold', parseInt(e.target.value))}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Race Setup Parameters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginTop: '1.25rem' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Total Laps</label>
          <input
            type="number"
            className="form-input"
            min={10}
            max={100}
            value={strategy.num_laps}
            onChange={(e) => handleChange('num_laps', parseInt(e.target.value) || 57)}
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Base Lap (s)</label>
          <input
            type="number"
            step="0.1"
            className="form-input"
            value={strategy.base_lap_time}
            onChange={(e) => handleChange('base_lap_time', parseFloat(e.target.value) || 94.0)}
          />
        </div>
      </div>
    </div>
  );
}
