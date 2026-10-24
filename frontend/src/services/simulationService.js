/**
 * Simulation Service
 * Handles Monte Carlo strategy runs, head-to-head comparisons, and undercut analysis.
 */

import { api } from './api';

export const simulationService = {
  /**
   * Run a single strategy Monte Carlo simulation.
   *
   * @param {Object} strategy - StrategyInput payload
   * @returns {Promise<Object>} Simulation response with race times, summary, and SC stats
   */
  async simulate(strategy) {
    return api.post('/simulate', strategy);
  },

  /**
   * Run a head-to-head paired Monte Carlo strategy comparison.
   *
   * @param {Object} strategyA - Strategy A input
   * @param {Object} strategyB - Strategy B input
   * @param {number} [numSimulations=10000] - Total simulations per strategy
   * @returns {Promise<Object>} Comparison results with win probabilities and combined histogram
   */
  async compare(strategyA, strategyB, numSimulations = 10000) {
    return api.post('/compare', {
      strategy_a: strategyA,
      strategy_b: strategyB,
      num_simulations: numSimulations,
    });
  },

  /**
   * Execute two-car undercut probability curve analysis.
   *
   * @param {Object} params - UndercutInput payload
   * @returns {Promise<Object>} Undercut curve data across pit deltas
   */
  async analyzeUndercut(params) {
    return api.post('/undercut-analysis', params);
  },
};

export default simulationService;
