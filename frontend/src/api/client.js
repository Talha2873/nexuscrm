import axios from 'axios';

import { API_BASE_URL } from '@/utils/constants';
import {
  clearSession,
  getAccessToken,
  getOrganizationId,
  getRefreshToken,
  setTokens,
} from './tokenStorage';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

/** Endpoints that must never trigger a refresh-and-retry cycle. */
const AUTH_PATHS = ['/auth/login/', '/auth/register/', '/auth/token/refresh/', '/auth/google/'];
const isAuthPath = (url = '') => AUTH_PATHS.some((path) => url.includes(path));

// ---------------------------------------------------------------------------
// Request: attach the bearer token and the active tenant
// ---------------------------------------------------------------------------
client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && !isAuthPath(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const organizationId = getOrganizationId();
  if (organizationId) {
    config.headers['X-Organization-Id'] = organizationId;
  }

  // Let the browser set the multipart boundary itself.
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

// ---------------------------------------------------------------------------
// Response: transparently refresh an expired access token, once
// ---------------------------------------------------------------------------
let refreshPromise = null;
const sessionExpiredListeners = new Set();

export const onSessionExpired = (listener) => {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
};

const broadcastSessionExpired = () => {
  clearSession();
  sessionExpiredListeners.forEach((listener) => listener());
};

const refreshAccessToken = async () => {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token available');

  // A bare axios call: using `client` here would recurse through this very
  // interceptor and deadlock on a second 401.
  const { data } = await axios.post(
    `${API_BASE_URL}/auth/token/refresh/`,
    { refresh },
    { headers: { 'Content-Type': 'application/json' } },
  );
  setTokens({ access: data.access, refresh: data.refresh });
  return data.access;
};

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;

    if (!response) {
      // Network failure, CORS rejection or timeout.
      return Promise.reject({
        status: 0,
        data: {
          error: {
            code: 'network_error',
            message: 'Cannot reach the server. Check your connection and try again.',
            details: {},
          },
        },
      });
    }

    const shouldRefresh =
      response.status === 401 && config && !config._retried && !isAuthPath(config.url);

    if (shouldRefresh) {
      config._retried = true;
      try {
        // Concurrent 401s share a single refresh request.
        refreshPromise = refreshPromise || refreshAccessToken();
        const access = await refreshPromise;
        refreshPromise = null;
        config.headers.Authorization = `Bearer ${access}`;
        return client(config);
      } catch (refreshError) {
        refreshPromise = null;
        broadcastSessionExpired();
        return Promise.reject({ status: 401, data: response.data, cause: refreshError });
      }
    }

    return Promise.reject({ status: response.status, data: response.data });
  },
);

export default client;
