export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'NexusCRM';

export const STORAGE_KEYS = {
  accessToken: 'nexuscrm.access',
  refreshToken: 'nexuscrm.refresh',
  organizationId: 'nexuscrm.organization',
  themeMode: 'nexuscrm.theme',
};

export const ROLES = {
  OWNER: 'owner',
  ADMIN: 'admin',
  MANAGER: 'manager',
  MEMBER: 'member',
  VIEWER: 'viewer',
};

export const ROLE_RANK = {
  [ROLES.OWNER]: 50,
  [ROLES.ADMIN]: 40,
  [ROLES.MANAGER]: 30,
  [ROLES.MEMBER]: 20,
  [ROLES.VIEWER]: 10,
};

export const ROLE_LABELS = {
  [ROLES.OWNER]: 'Owner',
  [ROLES.ADMIN]: 'Administrator',
  [ROLES.MANAGER]: 'Manager',
  [ROLES.MEMBER]: 'Member',
  [ROLES.VIEWER]: 'Viewer',
};

export const ROLE_COLORS = {
  [ROLES.OWNER]: 'secondary',
  [ROLES.ADMIN]: 'primary',
  [ROLES.MANAGER]: 'info',
  [ROLES.MEMBER]: 'default',
  [ROLES.VIEWER]: 'default',
};

export const INVITATION_STATUS_COLORS = {
  pending: 'warning',
  accepted: 'success',
  declined: 'default',
  expired: 'default',
  revoked: 'error',
};

export const DEFAULT_PAGE_SIZE = 25;
