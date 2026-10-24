/**
 * Centralized API Client Module
 * Provides consistent error handling, cold-start detection, and request timeouts.
 */

import { env } from '../config/env';

export class ApiError extends Error {
  constructor(message, status = null, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.isColdStart = status === 502 || status === 503 || status === 504;
  }
}

/**
 * Perform a generic fetch with timeout and structured JSON response handling.
 *
 * @param {string} endpoint - API path or full URL
 * @param {RequestInit} [options={}] - Fetch options
 * @returns {Promise<any>} Parsed response data
 */
export async function apiClient(endpoint, options = {}) {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${env.API_BASE_URL}${endpoint}`;

  const timeoutMs = options.timeout || env.REQUEST_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const fetchOptions = {
    ...options,
    signal: options.signal || controller.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  };

  try {
    const response = await fetch(url, fetchOptions);
    clearTimeout(timeoutId);

    const text = await response.text();
    if (!text || text.trim().length === 0) {
      if (!response.ok) {
        throw new ApiError(
          `Server returned status ${response.status}: ${response.statusText}`,
          response.status
        );
      }
      return null;
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch {
      if (!response.ok) {
        throw new ApiError(
          `Server error (HTTP ${response.status}). If the service is waking up from sleep, please wait ~30 seconds and try again.`,
          response.status
        );
      }
      throw new ApiError('Received non-JSON response from server.');
    }

    if (!response.ok) {
      const detailMessage =
        data?.detail || data?.message || `Request failed (HTTP ${response.status})`;
      throw new ApiError(detailMessage, response.status, data);
    }

    return data;
  } catch (err) {
    clearTimeout(timeoutId);

    if (err.name === 'AbortError') {
      throw new ApiError(
        'Request timed out. The backend server might be cold-starting or under heavy load.',
        408
      );
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      `Cannot connect to server (${err.message}). Please verify the backend is running.`
    );
  }
}

export const api = {
  get: (endpoint, options) =>
    apiClient(endpoint, { method: 'GET', ...options }),
  post: (endpoint, payload, options) =>
    apiClient(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
      ...options,
    }),
};

export default api;
