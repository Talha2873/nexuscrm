import client from './client';

/**
 * One function per REST endpoint. Components never build URLs themselves, so a
 * route change is a single edit here.
 */

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------
export const authApi = {
  register: (payload) => client.post('/auth/register/', payload),
  login: (payload) => client.post('/auth/login/', payload),
  googleLogin: (idToken) => client.post('/auth/google/', { id_token: idToken }),
  logout: (payload) => client.post('/auth/logout/', payload),
  refresh: (refresh) => client.post('/auth/token/refresh/', { refresh }),

  me: () => client.get('/auth/me/'),
  updateMe: (payload) => client.patch('/auth/me/', payload),
  uploadAvatar: (file) => {
    const form = new FormData();
    form.append('avatar', file);
    return client.post('/auth/me/avatar/', form);
  },
  removeAvatar: () => client.delete('/auth/me/avatar/'),
  deactivate: () => client.post('/auth/me/deactivate/'),
  switchOrganization: (organizationId) =>
    client.post('/auth/me/switch-organization/', { organization_id: organizationId }),

  verifyEmail: (token) => client.post('/auth/email/verify/', { token }),
  resendVerification: (email) => client.post('/auth/email/resend/', { email }),

  forgotPassword: (email) => client.post('/auth/password/forgot/', { email }),
  resetPassword: (payload) => client.post('/auth/password/reset/', payload),
  changePassword: (payload) => client.post('/auth/password/change/', payload),

  listSessions: () => client.get('/auth/sessions/'),
  revokeSession: (id) => client.delete(`/auth/sessions/${id}/`),
  listSocialAccounts: () => client.get('/auth/social-accounts/'),
  unlinkSocialAccount: (id) => client.delete(`/auth/social-accounts/${id}/`),
};

// ---------------------------------------------------------------------------
// Organizations
// ---------------------------------------------------------------------------
export const organizationApi = {
  list: (params) => client.get('/organizations/', { params }),
  current: () => client.get('/organizations/current/'),
  retrieve: (id) => client.get(`/organizations/${id}/`),
  create: (payload) => client.post('/organizations/', payload),
  update: (id, payload) => client.patch(`/organizations/${id}/`, payload),

  getSettings: (id) => client.get(`/organizations/${id}/settings/`),
  updateSettings: (id, payload) => client.patch(`/organizations/${id}/settings/`, payload),
  stats: (id) => client.get(`/organizations/${id}/stats/`),
  transferOwnership: (id, newOwnerId) =>
    client.post(`/organizations/${id}/transfer-ownership/`, { new_owner_id: newOwnerId }),
  completeOnboarding: (id) => client.post(`/organizations/${id}/complete-onboarding/`),
  leave: (id) => client.post(`/organizations/${id}/leave/`),
};

export const membershipApi = {
  list: (params) => client.get('/organizations/members/', { params }),
  me: () => client.get('/organizations/members/me/'),
  retrieve: (id) => client.get(`/organizations/members/${id}/`),
  update: (id, payload) => client.patch(`/organizations/members/${id}/`, payload),
  changeRole: (id, role) =>
    client.post(`/organizations/members/${id}/change-role/`, { role }),
  reactivate: (id) => client.post(`/organizations/members/${id}/reactivate/`),
  remove: (id) => client.delete(`/organizations/members/${id}/`),
};

export const teamApi = {
  list: (params) => client.get('/organizations/teams/', { params }),
  mine: () => client.get('/organizations/teams/my-teams/'),
  retrieve: (id) => client.get(`/organizations/teams/${id}/`),
  create: (payload) => client.post('/organizations/teams/', payload),
  update: (id, payload) => client.patch(`/organizations/teams/${id}/`, payload),
  remove: (id) => client.delete(`/organizations/teams/${id}/`),
  addMember: (id, payload) => client.post(`/organizations/teams/${id}/add-member/`, payload),
  removeMember: (id, userId) =>
    client.post(`/organizations/teams/${id}/remove-member/`, { user_id: userId }),
};

export const departmentApi = {
  list: (params) => client.get('/organizations/departments/', { params }),
  retrieve: (id) => client.get(`/organizations/departments/${id}/`),
  create: (payload) => client.post('/organizations/departments/', payload),
  update: (id, payload) => client.patch(`/organizations/departments/${id}/`, payload),
  remove: (id) => client.delete(`/organizations/departments/${id}/`),
};

export const invitationApi = {
  list: (params) => client.get('/organizations/invitations/', { params }),
  create: (payload) => client.post('/organizations/invitations/', payload),
  bulkCreate: (invitations) =>
    client.post('/organizations/invitations/bulk/', { invitations }),
  resend: (id) => client.post(`/organizations/invitations/${id}/resend/`),
  revoke: (id) => client.post(`/organizations/invitations/${id}/revoke/`),
  remove: (id) => client.delete(`/organizations/invitations/${id}/`),
  preview: (token) => client.get(`/organizations/invitations/preview/${token}/`),
  accept: (token) => client.post('/organizations/invitations/accept/', { token }),
};

// ---------------------------------------------------------------------------
// Shared resources
// ---------------------------------------------------------------------------
export const tagApi = {
  list: (params) => client.get('/tags/', { params }),
  create: (payload) => client.post('/tags/', payload),
  update: (id, payload) => client.patch(`/tags/${id}/`, payload),
  remove: (id) => client.delete(`/tags/${id}/`),
};

export const documentApi = {
  list: (params) => client.get('/documents/', { params }),
  upload: (file, extra = {}) => {
    const form = new FormData();
    form.append('file', file);
    form.append('name', extra.name || file.name);
    Object.entries(extra).forEach(([key, value]) => {
      if (key !== 'name' && value !== undefined && value !== null) form.append(key, value);
    });
    return client.post('/documents/', form);
  },
  remove: (id) => client.delete(`/documents/${id}/`),
};

export const noteApi = {
  list: (params) => client.get('/notes/', { params }),
  create: (payload) => client.post('/notes/', payload),
  update: (id, payload) => client.patch(`/notes/${id}/`, payload),
  remove: (id) => client.delete(`/notes/${id}/`),
};

export const activityApi = {
  list: (params) => client.get('/activities/', { params }),
};

export const auditApi = {
  list: (params) => client.get('/audit-logs/', { params }),
};

export const searchApi = {
  global: (q, params = {}) => client.get('/search/', { params: { q, ...params } }),
  targets: () => client.get('/search/targets/'),
};
