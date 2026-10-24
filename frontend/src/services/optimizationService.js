/**
 * Optimization Service
 * Handles Dynamic Programming strategy searches and Monte Carlo Tree Search replanning.
 */

import { api } from './api';

export const optimizationService = {
  /**
   * Run Dynamic Programming backward induction to find the optimal strategy.
   *
   * @param {Object} options - OptimizeInput parameters
   * @returns {Promise<Object>} Optimal stint plan and alternative strategies
   */
  async optimizeDP(options) {
    return api.post('/optimize', options);
  },

  /**
   * Trigger an MCTS search to generate optimal mid-race pit wall policy rules.
   *
   * @param {Object} request - MCTSRequest payload
   * @returns {Promise<Object>} Policy rules, candidate decision tree, and search diagnostics
   */
  async optimizeMCTS(request) {
    return api.post('/optimize-mcts', request);
  },
};

export default optimizationService;
