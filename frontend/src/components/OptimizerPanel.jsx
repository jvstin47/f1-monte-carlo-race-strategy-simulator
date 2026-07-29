import React, { useState } from 'react';
import { Cpu, Settings, Activity } from 'lucide-react';

export default function OptimizerPanel({ trackId, onOptimize, loading }) {
  const [availableCompounds, setAvailableCompounds] = useState(['soft', 'medium', 'hard']);
  const [maxStops, setMaxStops] = useState(2);
  const [riskAversion, setRiskAversion] = useState(0.0);

  const toggleCompound = (comp) => {
    if (availableCompounds.includes(comp)) {
      if (availableCompounds.length > 1) { // must have at least one
        setAvailableCompounds(availableCompounds.filter(c => c !== comp));
      }
    } else {
      setAvailableCompounds([...availableCompounds, comp]);
    }
  };

  const handleOptimizeClick = () => {
    onOptimize({
      track_id: trackId,
      available_compounds: availableCompounds,
      max_stops: maxStops,
      risk_aversion: riskAversion
    });
  };

  return (
    <div className="card optimizer-panel">
      <div className="card-title">
        <Cpu size={18} />
        Dynamic Programming Optimizer
      </div>
      
      <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Uses backward induction to find the theoretically optimal strategy for <strong>{trackId}</strong>, then runs Monte Carlo to evaluate risk.
      </p>

      <div className="form-group">
        <div className="form-label">Available Compounds</div>
        <div className="compound-selector" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(60px, 1fr))' }}>
          {['soft', 'medium', 'hard'].map(comp => (
            <div 
              key={comp} 
              className={`compound-pill ${availableCompounds.includes(comp) ? `selected-${comp}` : ''}`}
              onClick={() => toggleCompound(comp)}
              style={{ opacity: availableCompounds.includes(comp) ? 1 : 0.4 }}
            >
              {comp.charAt(0).toUpperCase()}
            </div>
          ))}
        </div>
      </div>

      <div className="form-group slider-container">
        <div className="form-label">
          <span>Max Stops</span>
          <span className="slider-val">{maxStops}</span>
        </div>
        <input 
          type="range" 
          min="1" 
          max="3" 
          step="1"
          value={maxStops} 
          onChange={(e) => setMaxStops(parseInt(e.target.value))} 
        />
      </div>

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
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
          0 = Maximize pure pace, 1 = Maximize predictability
        </div>
      </div>

      <button 
        className="btn-primary" 
        onClick={handleOptimizeClick}
        disabled={loading}
      >
        {loading ? (
          <div className="spinner"></div>
        ) : (
          <>
            <Activity size={18} />
            Find Optimal Strategy
          </>
        )}
      </button>
    </div>
  );
}
