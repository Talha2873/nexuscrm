import { STORAGE_KEYS } from '@/utils/constants';

/**
 * Small wrapper over localStorage so token handling lives in exactly one place
 * and never throws in private-browsing modes where storage is unavailable.
 */
const safeGet = (key) => {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = (key, value) => {
  try {
    if (value === null || value === undefined) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable — session becomes memory-only */
  }
};

export const getAccessToken = () => safeGet(STORAGE_KEYS.accessToken);
export const getRefreshToken = () => safeGet(STORAGE_KEYS.refreshToken);
export const getOrganizationId = () => safeGet(STORAGE_KEYS.organizationId);

export const setTokens = ({ access, refresh }) => {
  if (access) safeSet(STORAGE_KEYS.accessToken, access);
  if (refresh) safeSet(STORAGE_KEYS.refreshToken, refresh);
};

export const setOrganizationId = (id) => safeSet(STORAGE_KEYS.organizationId, id);

export const clearSession = () => {
  safeSet(STORAGE_KEYS.accessToken, null);
  safeSet(STORAGE_KEYS.refreshToken, null);
  safeSet(STORAGE_KEYS.organizationId, null);
};
