/**
 * Central Strategy and Application State Context.
 * Eliminates prop-drilling by managing active strategies, circuits, drivers, and simulation results.
 */

import React, { createContext, useState, useEffect, useCallback } from 'react';
import {
  DEFAULT_STRATEGY_A,
  DEFAULT_STRATEGY_B,
  DEFAULT_UNDERCUT_INPUT,
} from '../config/constants';
import { simulationService } from '../services/simulationService';
import { optimizationService } from '../services/optimizationService';
import { metadataService } from '../services/metadataService';

export const StrategyContext = createContext(null);

export function StrategyProvider({ children }) {
  const [serverWaking, setServerWaking] = useState(true);
  const [viewTab, setViewTab] = useState('sim');
  const [mode, setMode] = useState('single');
  const [activeSubTab, setActiveSubTab] = useState('a');

  const [tracks, setTracks] = useState({});
  const [selectedTrackId, setSelectedTrackId] = useState('bahrain');
  const [drivers, setDrivers] = useState({});

  const [strategyA, setStrategyA] = useState(DEFAULT_STRATEGY_A);
  const [strategyB, setStrategyB] = useState(DEFAULT_STRATEGY_B);
  const [undercutParams, setUndercutParams] = useState(DEFAULT_UNDERCUT_INPUT);

  const [singleResults, setSingleResults] = useState(null);
  const [compareResults, setCompareResults] = useState(null);
  const [undercutResults, setUndercutResults] = useState(null);
  const [optimizeResults, setOptimizeResults] = useState(null);

  const [weatherDryData, setWeatherDryData] = useState(null);
  const [weatherMixedData, setWeatherMixedData] = useState(null);
  const [calibrationData, setCalibrationData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initial mount: wake up server and fetch metadata
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function initializeApp() {
      try {
        await metadataService.pingHealth(controller.signal);
      } catch {
        // Silently handle wakeup errors; server could still be starting
      } finally {
        if (isMounted) setServerWaking(false);
      }

      if (!isMounted) return;

      try {
        const [tracksData, driversData, calibData] = await Promise.allSettled([
          metadataService.getTracks(),
          metadataService.getDrivers(),
          metadataService.getCalibration(),
        ]);

        if (tracksData.status === 'fulfilled' && tracksData.value) {
          setTracks(tracksData.value);
        }
        if (driversData.status === 'fulfilled' && driversData.value) {
          setDrivers(driversData.value);
        }
        if (calibData.status === 'fulfilled' && calibData.value) {
          setCalibrationData(calibData.value);
        }
      } catch (err) {
        console.warn('Initial metadata load error:', err);
      }
    }

    initializeApp();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  // Track selection updater
  const handleSelectTrack = useCallback(
    (trackId) => {
      setSelectedTrackId(trackId);
      const t = tracks[trackId];
      if (t) {
        const updateObj = {
          track_id: trackId,
          num_laps: t.num_laps,
          base_lap_time: t.base_lap_time,
          pit_stop_time_loss: t.pit_stop_time_loss,
          sc_probability: t.sc_probability,
        };
        setStrategyA((prev) => ({ ...prev, ...updateObj }));
        setStrategyB((prev) => ({ ...prev, ...updateObj }));
      }
    },
    [tracks]
  );

  // Run simulation / comparison / weather sweep
  const handleSimulate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (viewTab === 'weather') {
        const dryStrat = {
          ...strategyA,
          weather_enabled: false,
          num_simulations: 5000,
        };
        const wetStrat = {
          ...strategyA,
          weather_enabled: true,
          weather_start_state: 'mixed',
          num_simulations: 5000,
        };
        const [dryRes, wetRes] = await Promise.all([
          simulationService.simulate(dryStrat),
          simulationService.simulate(wetStrat),
        ]);
        setWeatherDryData(dryRes);
        setWeatherMixedData(wetRes);
        setSingleResults(dryRes);
      } else if (mode === 'single') {
        const data = await simulationService.simulate(strategyA);
        setSingleResults(data);
      } else {
        const data = await simulationService.compare(strategyA, strategyB);
        setCompareResults(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [strategyA, strategyB, mode, viewTab]);

  // Run undercut analysis
  const handleRunUndercut = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await simulationService.analyzeUndercut(undercutParams);
      setUndercutResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [undercutParams]);

  // Run DP optimization
  const handleOptimize = useCallback(
    async (opts) => {
      setLoading(true);
      setError(null);
      try {
        const data = await optimizationService.optimizeDP({
          track_id: selectedTrackId,
          ...opts,
        });
        setOptimizeResults(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [selectedTrackId]
  );

  // Auto-run simulation or undercut when switching view tabs
  useEffect(() => {
    if (serverWaking) return;
    if (viewTab === 'undercut') {
      handleRunUndercut();
    } else if (['sim', 'sc', 'weather'].includes(viewTab)) {
      handleSimulate();
    }
  }, [viewTab, mode, serverWaking]);

  // Demo scenario auto-trigger
  const handleRunDemo = useCallback(async () => {
    setViewTab('sim');
    const demoStrategy = {
      ...DEFAULT_STRATEGY_A,
      track_id: 'bahrain',
      driver_id: 'ver',
      sc_probability: 0.08,
      weather_enabled: true,
      weather_start_state: 'dry',
      num_simulations: 5000,
    };
    setStrategyA(demoStrategy);
    setMode('single');
    setLoading(true);
    setError(null);
    try {
      const data = await simulationService.simulate(demoStrategy);
      setSingleResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const value = {
    serverWaking,
    setServerWaking,
    viewTab,
    setViewTab,
    mode,
    setMode,
    activeSubTab,
    setActiveSubTab,
    tracks,
    setTracks,
    selectedTrackId,
    setSelectedTrackId,
    drivers,
    setDrivers,
    strategyA,
    setStrategyA,
    strategyB,
    setStrategyB,
    undercutParams,
    setUndercutParams,
    singleResults,
    setSingleResults,
    compareResults,
    setCompareResults,
    undercutResults,
    setUndercutResults,
    optimizeResults,
    setOptimizeResults,
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
  };

  return (
    <StrategyContext.Provider value={value}>
      {children}
    </StrategyContext.Provider>
  );
}

export default StrategyContext;
