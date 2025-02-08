/**
 * Authentication service for managing API keys and headers
 */

// Get API key from environment variable
const API_KEY = import.meta.env.VITE_API_KEY;

/**
 * Get headers with API key for requests
 * @returns {Object} Headers object with API key
 */
export const getAuthHeaders = () => {
  return {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  };
};

/**
 * Add auth headers to fetch options
 * @param {Object} options - Fetch options object
 * @returns {Object} Updated options with auth headers
 */
export const withAuth = (options = {}) => {
  return {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  };
};
