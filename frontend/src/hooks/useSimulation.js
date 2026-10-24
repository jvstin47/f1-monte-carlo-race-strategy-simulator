/**
 * Custom hook for simulation operations and state.
 */

import { useStrategyContext } from './useStrategyContext';

export function useSimulation() {
  const {
    strategyA,
    setStrategyA,
    strategyB,
    setStrategyB,
    mode,
    setMode,
    singleResults,
    compareResults,
    undercutResults,
    undercutParams,
    setUndercutParams,
    weatherDryData,
    weatherMixedData,
    loading,
    error,
    handleSimulate,
    handleRunUndercut,
    handleRunDemo,
  } = useStrategyContext();

  return {
    strategyA,
    setStrategyA,
    strategyB,
    setStrategyB,
    mode,
    setMode,
    singleResults,
    compareResults,
    undercutResults,
    undercutParams,
    setUndercutParams,
    weatherDryData,
    weatherMixedData,
    loading,
    error,
    simulate: handleSimulate,
    runUndercut: handleRunUndercut,
    runDemo: handleRunDemo,
  };
}

export default useSimulation;
