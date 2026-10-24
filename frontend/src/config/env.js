/**
 * Environment configuration for the frontend application.
 * Reads environment variables configured at build/runtime with fallback defaults.
 */

export const env = {
  /**
   * Base URL for backend API requests.
   * If empty string, uses relative paths which are proxied by Vite in development.
   */
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '',

  /**
   * Flag indicating development mode.
   */
  IS_DEV: import.meta.env.DEV,

  /**
   * Timeout in milliseconds for backend health check wake-up ping.
   */
  HEALTH_CHECK_TIMEOUT_MS: 45000,

  /**
   * Default timeout for simulation API requests.
   */
  REQUEST_TIMEOUT_MS: 30000,
};

export default env;
