/**
 * Custom hook for DP optimization state and dispatchers.
 */

import { useStrategyContext } from './useStrategyContext';

export function useOptimizer() {
  const {
    optimizeResults,
    loading,
    error,
    handleOptimize,
    selectedTrackId,
  } = useStrategyContext();

  return {
    results: optimizeResults,
    loading,
    error,
    optimize: handleOptimize,
    trackId: selectedTrackId,
  };
}

export default useOptimizer;
