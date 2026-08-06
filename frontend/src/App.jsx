import React, { useState, useEffect } from 'react';
import { Play, Sliders, Zap, Database, ShieldAlert, BarChart2 } from 'lucide-react';
import StrategyForm from './components/StrategyForm';
import ResultsChart from './components/ResultsChart';
import StatsBanner from './components/StatsBanner';
import UndercutChart from './components/UndercutChart';
import FastF1Banner from './components/FastF1Banner';
import TrackSelector from './components/TrackSelector';
import WeatherVarianceChart from './components/WeatherVarianceChart';
import OptimizerPanel from './components/OptimizerPanel';
import StintTimeline from './components/StintTimeline';
import AlternativesTable from './components/AlternativesTable';
import DriverSelector from './components/DriverSelector';
import DriverImpactChart from './components/DriverImpactChart';
import RaceSimulatorTab from './components/RaceSimulatorTab';

const DEFAULT_STRATEGY_A = {
  driver_id: 'generic',
  track_id: 'bahrain',
  compound_1: 'soft',
  compound_2: 'medium',
  pit_lap: 18,
  compounds: ['soft', 'medium'],
  pit_laps: [18],
  num_laps: 57,
  base_lap_time: 94.0,
  pit_stop_time_loss: 22.0,
  num_simulations: 10000,
  random_std: 0.15,
  sc_probability: 0.04,
  is_reactive_sc: false,
  reactive_window: 8
};

const DEFAULT_STRATEGY_B = {
  driver_id: 'generic',
  track_id: 'bahrain',
  compound_1: 'medium',
  compound_2: 'hard',
  pit_lap: 30,
  compounds: ['medium', 'hard'],
  pit_laps: [30],
  num_laps: 57,
  base_lap_time: 94.0,
  pit_stop_time_loss: 22.0,
  num_simulations: 10000,
  random_std: 0.15,
  sc_probability: 0.04,
  is_reactive_sc: true,
  reactive_window: 8
};

const DEFAULT_UNDERCUT_INPUT = {
  base_pit_lap_b: 22,
  car_a_compound_1: 'medium',
  car_a_compound_2: 'hard',
  car_b_compound_1: 'medium',
  car_b_compound_2: 'hard',
  initial_gap_seconds: 1.0,
  dirty_air_penalty: 0.25,
  num_simulations: 5000
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [serverWaking, setServerWaking] = useState(true);
  const [viewTab, setViewTab] = useState('sim'); // 'sim' | 'sc' | 'weather' | 'undercut' | 'fastf1' | 'optimize'
  const [mode, setMode] = useState('single'); // 'single' | 'compare'
  const [activeSubTab, setActiveSubTab] = useState('a');

  const [tracks, setTracks] = useState({});
  const [selectedTrackId, setSelectedTrackId] = useState('bahrain');
  const [drivers, setDrivers] = useState({});

  const [strategyA, setStrategyA] = useState(DEFAULT_STRATEGY_A);
  const [strategyB, setStrategyB] = useState(DEFAULT_STRATEGY_B);
  const [undercutParams, setUndercutParams] = useState(DEFAULT_UNDERCUT_INPUT);

  const [optimizeResults, setOptimizeResults] = useState(null);
  const [weatherDryData, setWeatherDryData] = useState(null);
  const [weatherMixedData, setWeatherMixedData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Simulation results
  const [singleResults, setSingleResults] = useState(null);
  const [compareResults, setCompareResults] = useState(null);
  const [undercutResults, setUndercutResults] = useState(null);
  const [calibrationData, setCalibrationData] = useState(null);

  useEffect(() => {
    const wakeServerAndLoad = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000);
        await fetch(`${API_BASE}/health`, { signal: controller.signal });
        clearTimeout(timeoutId);
      } catch (e) {
        // Server might be waking up or offline
      } finally {
        setServerWaking(false);
      }
      // Load initial data after health check attempt completes
      await Promise.all([fetchCalibration(), fetchTracks(), fetchDrivers()]);
    };
    wakeServerAndLoad();
  }, []);

  const fetchTracks = async () => {
    try {
      const res = await fetch(`${API_BASE}/tracks`);
      if (res.ok) {
        const data = await res.json();
        setTracks(data);
      }
    } catch (err) {
      console.error("Failed to fetch tracks", err);
    }
  };

  const fetchDrivers = async () => {
    try {
      const res = await fetch(`${API_BASE}/drivers`);
      if (res.ok) {
        const data = await res.json();
        setDrivers(data);
      }
    } catch (err) {
      console.error("Failed to fetch drivers", err);
    }
  };

  const handleSelectTrack = (trackId) => {
    setSelectedTrackId(trackId);
    const t = tracks[trackId];
    if (t) {
      const updateObj = {
        track_id: trackId,
        num_laps: t.num_laps,
        base_lap_time: t.base_lap_time,
        pit_stop_time_loss: t.pit_stop_time_loss,
        sc_probability: t.sc_probability
      };
      setStrategyA(prev => ({ ...prev, ...updateObj }));
      setStrategyB(prev => ({ ...prev, ...updateObj }));
    }
  };

  const fetchCalibration = async () => {
    try {
      const res = await fetch(`${API_BASE}/fastf1/calibrate`);
      if (res.ok) {
        const text = await res.text();
        if (text && text.trim().length > 0) {
          setCalibrationData(JSON.parse(text));
        }
      }
    } catch (err) {
      console.warn("FastF1 calibration fetch skipped/fallback used:", err);
    }
  };

  const safeFetchJson = async (url, payload) => {
    let response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (fetchErr) {
      throw new Error(`Cannot connect to server: ${fetchErr.message}`);
    }

    const text = await response.text();
    if (!text || text.trim().length === 0) {
      throw new Error(`Server returned an empty response (HTTP ${response.status}).`);
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch (jsonErr) {
      if (!response.ok) {
        throw new Error(`Server error (HTTP ${response.status}: ${response.statusText}). If the backend is waking up from sleep, please wait ~30 seconds and try again.`);
      }
      throw new Error("Received non-JSON response from server.");
    }

    if (!response.ok) {
      throw new Error(data.detail || `Simulation request failed (HTTP ${response.status})`);
    }

    return data;
  };

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      if (viewTab === 'weather') {
        // Run Dry Baseline
        const dataDry = await safeFetchJson(`${API_BASE}/simulate`, { ...strategyA, track_id: selectedTrackId, weather_enabled: false });
        setWeatherDryData(dataDry.summary?.histogram || []);
        
        // Run Mixed Weather
        const dataMixed = await safeFetchJson(`${API_BASE}/simulate`, { ...strategyA, track_id: selectedTrackId, weather_enabled: true });
        setWeatherMixedData(dataMixed.summary?.histogram || []);
      } else {
        const endpoint = mode === 'single' ? `${API_BASE}/simulate` : `${API_BASE}/compare`;
        const payload = mode === 'single' ? { ...strategyA, track_id: selectedTrackId } : { strategy_a: { ...strategyA, track_id: selectedTrackId }, strategy_b: { ...strategyB, track_id: selectedTrackId } };

        const data = await safeFetchJson(endpoint, payload);

        if (mode === 'single') {
          setSingleResults(data);
        } else {
          setCompareResults(data);
        }
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Failed to connect to backend server');
    } finally {
      setLoading(false);
    }
  };

  const handleRunUndercut = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await safeFetchJson(`${API_BASE}/undercut-analysis`, undercutParams);
      setUndercutResults(data);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Failed to execute undercut analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleRunDemo = async () => {
    setViewTab('sim');
    const demoStrategy = {
      ...DEFAULT_STRATEGY_A,
      track_id: 'bahrain',
      driver_id: 'ver',
      sc_probability: 0.08,
      weather_enabled: true,
      weather_start_state: 'dry',
      num_simulations: 5000
    };
    setStrategyA(demoStrategy);
    setMode('single');
    setLoading(true);
    try {
      const data = await safeFetchJson(`${API_BASE}/simulate`, demoStrategy);
      setSingleResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async (opts) => {
    setLoading(true);
    setError(null);
    try {
      const data = await safeFetchJson(`${API_BASE}/optimize`, opts);
      setOptimizeResults(data);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (viewTab === 'undercut') {
      handleRunUndercut();
    } else if (viewTab === 'optimize' || viewTab === 'fastf1') {
      // Do nothing on mount
    } else {
      handleSimulate();
    }
  }, [viewTab, mode]);

  return (
    <div className="app-container">
      {serverWaking && (
        <div className="cold-start-overlay">
          <div className="cold-start-modal">
            <div className="cold-start-spinner"></div>
            <h3>Waking up the simulation engine...</h3>
            <p>Free hosting takes ~30s to start on first visit</p>
          </div>
        </div>
      )}
      {/* App Header */}
      <header className="app-header">
        <div className="brand">
          <div className="logo-badge">F1</div>
          <div className="brand-text">
            <h1>Apex Strategy v4</h1>
            <p>v4 • MCTS Engine • Driver Profiles • Realism Layer {tracks[selectedTrackId] ? `• ${tracks[selectedTrackId].name}` : ''}</p>
          </div>
        </div>

        <div className="mode-toggle">
          <button
            className={`mode-btn ${viewTab === 'sim' ? 'active' : ''}`}
            onClick={() => { setViewTab('sim'); setMode('single'); }}
          >
            Simulator
          </button>
          <button
            className={`mode-btn ${viewTab === 'sc' ? 'active' : ''}`}
            onClick={() => { setViewTab('sc'); setMode('compare'); }}
          >
            Safety Car
          </button>
          <button
            className={`mode-btn ${viewTab === 'racesim' ? 'active' : ''}`}
            onClick={() => setViewTab('racesim')}
          >
            Race Sim (MCTS)
          </button>
          <button className="demo-btn" onClick={handleRunDemo} disabled={loading}>
            ▶ Run Demo Scenario
          </button>
            <button
              className={`mode-btn ${viewTab === 'weather' ? 'active' : ''}`}
              onClick={() => { setViewTab('weather'); setMode('single'); }}
            >
              Weather
            </button>
            <button
              className={`mode-btn ${viewTab === 'undercut' ? 'active' : ''}`}
              onClick={() => setViewTab('undercut')}
            >
              Undercut Battle
            </button>
            <button
              className={`mode-btn ${viewTab === 'fastf1' ? 'active' : ''}`}
              onClick={() => setViewTab('fastf1')}
            >
              FastF1
            </button>
            <button
              className={`mode-btn ${viewTab === 'optimize' ? 'active' : ''}`}
              onClick={() => setViewTab('optimize')}
            >
              Optimize
            </button>
          </div>
      </header>

      {/* FastF1 Validation Banner */}
      {viewTab === 'fastf1' && (
        <FastF1Banner
          calibrationData={calibrationData}
          simMeanTime={singleResults?.summary?.mean}
        />
      )}

      {/* Main Stats Banner */}
      {(viewTab === 'sim' || viewTab === 'sc' || viewTab === 'weather') && (
        <StatsBanner
          mode={mode}
          singleSummary={singleResults?.summary}
          compareData={compareResults}
        />
      )}

      {/* Track Selector */}
      {['sim', 'sc', 'weather'].includes(viewTab) && (
        <TrackSelector 
          tracks={tracks} 
          selectedTrackId={selectedTrackId} 
          onSelectTrack={handleSelectTrack} 
        />
      )}

      {/* Main Layout Grid */}
      <main className="dashboard-grid">
        {/* Left Sidebar */}
        <div className="sidebar">
          {viewTab === 'undercut' ? (
            <div className="card">
              <div className="card-title">
                <Zap size={18} style={{ color: '#06b6d4' }} />
                Undercut Battle Parameters
              </div>

              <div className="form-group">
                <div className="form-label">
                  <span>Defender (Car B) Pit Lap</span>
                  <span className="slider-val">Lap {undercutParams.base_pit_lap_b}</span>
                </div>
                <div className="slider-container">
                  <input
                    type="range"
                    min={10}
                    max={40}
                    value={undercutParams.base_pit_lap_b}
                    onChange={(e) => setUndercutParams(p => ({ ...p, base_pit_lap_b: parseInt(e.target.value) }))}
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="form-label">
                  <span>Initial Gap (Car A Behind B)</span>
                  <span className="slider-val">{undercutParams.initial_gap_seconds.toFixed(1)}s</span>
                </div>
                <div className="slider-container">
                  <input
                    type="range"
                    min={0.2}
                    max={3.0}
                    step={0.1}
                    value={undercutParams.initial_gap_seconds}
                    onChange={(e) => setUndercutParams(p => ({ ...p, initial_gap_seconds: parseFloat(e.target.value) }))}
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="form-label">
                  <span>Dirty Air Penalty / Lap</span>
                  <span className="slider-val">+{undercutParams.dirty_air_penalty.toFixed(2)}s</span>
                </div>
                <div className="slider-container">
                  <input
                    type="range"
                    min={0.0}
                    max={0.6}
                    step={0.05}
                    value={undercutParams.dirty_air_penalty}
                    onChange={(e) => setUndercutParams(p => ({ ...p, dirty_air_penalty: parseFloat(e.target.value) }))}
                  />
                </div>
              </div>

              <button className="btn-primary" onClick={handleRunUndercut} disabled={loading}>
                {loading ? <div className="spinner"></div> : <Play size={18} fill="currentColor" />}
                Analyze Undercut Curve
              </button>
            </div>
          ) : viewTab === 'racesim' ? (
            <RaceSimulatorTab
              trackId={selectedTrackId}
              driverId={strategyA.driver_id}
              onDriverChange={(d) => setStrategyA(p => ({ ...p, driver_id: d }))}
              API_BASE={API_BASE}
              drivers={drivers}
            />
          ) : (
            <>
              {mode === 'compare' && (
                <div className="strategy-tabs">
                  <button
                    className={`tab-btn ${activeSubTab === 'a' ? 'active-a' : ''}`}
                    onClick={() => setActiveSubTab('a')}
                  >
                    Strategy A ({strategyA.compounds?.length || 2}-Stop)
                  </button>
                  <button
                    className={`tab-btn ${activeSubTab === 'b' ? 'active-b' : ''}`}
                    onClick={() => setActiveSubTab('b')}
                  >
                    Strategy B ({strategyB.compounds?.length || 2}-Stop)
                  </button>
                </div>
              )}

              {viewTab === 'weather' ? (
                <StrategyForm
                  strategy={strategyA}
                  setStrategy={setStrategyA}
                  title="Weather Configuration"
                  showSafetyCarControls={false}
                  weatherEnabled={true}
                />
              ) : viewTab === 'optimize' ? (
                <OptimizerPanel
                  trackId={selectedTrackId}
                  onOptimize={handleOptimize}
                  loading={loading}
                />
              ) : mode === 'single' ? (
                <StrategyForm
                  strategy={strategyA}
                  setStrategy={setStrategyA}
                  title="Strategy Configuration"
                  showSafetyCarControls={viewTab === 'sc'}
                  weatherEnabled={false}
                />
              ) : activeSubTab === 'a' ? (
                <StrategyForm
                  strategy={strategyA}
                  setStrategy={setStrategyA}
                  title="Strategy A Setup"
                  accentColor="var(--strat-a)"
                  showSafetyCarControls={true}
                  weatherEnabled={false}
                />
              ) : (
                <StrategyForm
                  strategy={strategyB}
                  setStrategy={setStrategyB}
                  title="Strategy B Setup"
                  accentColor="var(--strat-b)"
                  showSafetyCarControls={true}
                  weatherEnabled={false}
                />
              )}
              
              {['sim', 'sc', 'weather'].includes(viewTab) && (
                <DriverSelector
                  drivers={drivers}
                  selectedDriver={mode === 'single' || activeSubTab === 'a' ? strategyA.driver_id : strategyB.driver_id}
                  onSelectDriver={(d) => {
                    if (mode === 'single' || activeSubTab === 'a') {
                      setStrategyA(p => ({ ...p, driver_id: d }));
                    } else {
                      setStrategyB(p => ({ ...p, driver_id: d }));
                    }
                  }} 
                />
              )}

              {viewTab !== 'optimize' && viewTab !== 'racesim' && (
                <button className="btn-primary" onClick={handleSimulate} disabled={loading}>
                  {loading ? (
                    <>
                      <div className="spinner"></div>
                      Simulating Laps...
                    </>
                  ) : (
                    <>
                      <Play size={18} fill="currentColor" />
                      Run Monte Carlo (10k)
                    </>
                  )}
                </button>
              )}
            </>
          )}

          {error && (
            <div style={{ marginTop: '1rem', color: '#ef4444', fontSize: '0.85rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              {error}
            </div>
          )}
        </div>

        {/* Right Output Panel */}
        <div className="chart-panel">
          {viewTab === 'undercut' ? (
            <UndercutChart curveData={undercutResults?.curve_data} />
          ) : viewTab === 'weather' ? (
            <WeatherVarianceChart dryData={weatherDryData} weatherData={weatherMixedData} />
          ) : viewTab === 'optimize' ? (
            <>
              {optimizeResults && (
                <>
                  <StintTimeline 
                    stints={optimizeResults.optimal_strategy} 
                    expectedTime={optimizeResults.expected_time} 
                    numLaps={tracks[selectedTrackId]?.num_laps || 57}
                  />
                  <AlternativesTable 
                    alternatives={optimizeResults.top_5_alternatives} 
                    optimalTime={optimizeResults.expected_time}
                  />
                  <ResultsChart
                    mode="single"
                    data={optimizeResults.monte_carlo_distribution?.summary?.histogram}
                    singleSummary={optimizeResults.monte_carlo_distribution?.summary}
                  />
                </>
              )}
            </>
          ) : viewTab === 'racesim' ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9ca3af' }}>
              MCTS Re-Optimization Panel Active (Left Sidebar)
            </div>
          ) : (
            <>
              {mode === 'compare' && compareResults && (
                <DriverImpactChart compareData={compareResults} drivers={drivers} />
              )}
              <ResultsChart
                mode={mode}
                data={mode === 'single' ? singleResults?.summary?.histogram : compareResults?.combined_histogram}
                singleSummary={singleResults?.summary}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
