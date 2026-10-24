/**
 * Root Application Component
 * Coordinates top navigation, active tab views, and global alerts using StrategyContext.
 */

import React from 'react';
import { Play, Zap } from 'lucide-react';

import { StrategyProvider } from './context/StrategyContext';
import { useStrategyContext } from './hooks/useStrategyContext';

import {
  ColdStartOverlay,
  ErrorBanner,
  TrackSelector,
  DriverSelector,
  FastF1Banner,
  StatsBanner,
} from './components/common';

import {
  StrategyForm,
  OptimizerPanel,
  AlternativesTable,
} from './components/strategy';

import {
  ResultsChart,
  UndercutChart,
  WeatherVarianceChart,
  DriverImpactChart,
  StintTimeline,
} from './components/charts';

import { RaceSimulatorTab } from './components/simulator';

function DashboardLayout() {
  const {
    serverWaking,
    viewTab,
    setViewTab,
    mode,
    setMode,
    activeSubTab,
    setActiveSubTab,
    tracks,
    selectedTrackId,
    drivers,
    strategyA,
    setStrategyA,
    strategyB,
    setStrategyB,
    undercutParams,
    setUndercutParams,
    singleResults,
    compareResults,
    undercutResults,
    optimizeResults,
    weatherDryData,
    weatherMixedData,
    calibrationData,
    loading,
    error,
    setError,
    handleSelectTrack,
    handleSimulate,
    handleRunUndercut,
    handleOptimize,
    handleRunDemo,
  } = useStrategyContext();

  return (
    <div className="app-container">
      <ColdStartOverlay isWaking={serverWaking} />

      {/* App Header */}
      <header className="app-header">
        <div className="brand">
          <div className="logo-badge">F1</div>
          <div className="brand-text">
            <h1>Apex Strategy v5</h1>
            <p>
              v5 • Hybrid MCTS • Driver Profiles • Realism Layer{' '}
              {tracks[selectedTrackId] ? `• ${tracks[selectedTrackId].name}` : ''}
            </p>
          </div>
        </div>

        <div className="mode-toggle">
          <button
            className={`mode-btn ${viewTab === 'sim' ? 'active' : ''}`}
            onClick={() => {
              setViewTab('sim');
              setMode('single');
            }}
          >
            Simulator
          </button>
          <button
            className={`mode-btn ${viewTab === 'sc' ? 'active' : ''}`}
            onClick={() => {
              setViewTab('sc');
              setMode('compare');
            }}
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
            onClick={() => {
              setViewTab('weather');
              setMode('single');
            }}
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
      {['sim', 'sc', 'weather'].includes(viewTab) && (
        <StatsBanner
          mode={mode}
          singleSummary={singleResults?.summary}
          compareData={compareResults}
        />
      )}

      {/* Global Error Banner */}
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

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
                    onChange={(e) =>
                      setUndercutParams((p) => ({
                        ...p,
                        base_pit_lap_b: parseInt(e.target.value, 10),
                      }))
                    }
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
                    onChange={(e) =>
                      setUndercutParams((p) => ({
                        ...p,
                        initial_gap_seconds: parseFloat(e.target.value),
                      }))
                    }
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
                    onChange={(e) =>
                      setUndercutParams((p) => ({
                        ...p,
                        dirty_air_penalty: parseFloat(e.target.value),
                      }))
                    }
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
              onDriverChange={(d) => setStrategyA((p) => ({ ...p, driver_id: d }))}
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
                  selectedDriver={
                    mode === 'single' || activeSubTab === 'a'
                      ? strategyA.driver_id
                      : strategyB.driver_id
                  }
                  onSelectDriver={(d) => {
                    if (mode === 'single' || activeSubTab === 'a') {
                      setStrategyA((p) => ({ ...p, driver_id: d }));
                    } else {
                      setStrategyB((p) => ({ ...p, driver_id: d }));
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
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#9ca3af',
              }}
            >
              MCTS Re-Optimization Panel Active (Left Sidebar)
            </div>
          ) : (
            <>
              {mode === 'compare' && compareResults && (
                <DriverImpactChart compareData={compareResults} drivers={drivers} />
              )}
              <ResultsChart
                mode={mode}
                data={
                  mode === 'single'
                    ? singleResults?.summary?.histogram
                    : compareResults?.combined_histogram
                }
                singleSummary={singleResults?.summary}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <StrategyProvider>
      <DashboardLayout />
    </StrategyProvider>
  );
}
