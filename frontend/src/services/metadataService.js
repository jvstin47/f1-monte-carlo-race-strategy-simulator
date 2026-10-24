/**
 * Metadata and Telemetry Service
 * Retrieves track presets, driver profiles, health checks, and FastF1 calibration data.
 */

import { api } from './api';
import { env } from '../config/env';

export const metadataService = {
  /**
   * Ping backend /health to check server availability and pre-warm cold starts.
   *
   * @param {AbortSignal} [signal] - Optional abort signal
   * @returns {Promise<boolean>} True if server responds with ok
   */
  async pingHealth(signal) {
    try {
      const res = await api.get('/health', {
        signal,
        timeout: env.HEALTH_CHECK_TIMEOUT_MS,
      });
      return res?.status === 'ok';
    } catch {
      return false;
    }
  },

  /**
   * Fetch all available track presets.
   *
   * @returns {Promise<Object>} Map of track_id to circuit configuration
   */
  async getTracks() {
    return api.get('/tracks');
  },

  /**
   * Fetch all driver profiles with teammate-delta calibration.
   *
   * @returns {Promise<Object>} Map of driver_id to driver profile
   */
  async getDrivers() {
    return api.get('/drivers');
  },

  /**
   * Fetch FastF1 empirical telemetry calibration.
   *
   * @param {number} [year=2023]
   * @param {string} [grandPrix='Bahrain']
   * @param {string} [sessionType='R']
   * @returns {Promise<Object>} Calibrated parameters and baseline race paces
   */
  async getCalibration(year = 2023, grandPrix = 'Bahrain', sessionType = 'R') {
    return api.get(
      `/fastf1/calibrate?year=${year}&grand_prix=${grandPrix}&session_type=${sessionType}`
    );
  },
};

export default metadataService;
