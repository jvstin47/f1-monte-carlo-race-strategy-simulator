/**
 * Custom hook to safely consume StrategyContext.
 */

import { useContext } from 'react';
import { StrategyContext } from '../context/StrategyContext';

export function useStrategyContext() {
  const context = useContext(StrategyContext);
  if (!context) {
    throw new Error('useStrategyContext must be used within a StrategyProvider');
  }
  return context;
}

export default useStrategyContext;
