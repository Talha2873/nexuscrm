import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';

import { authApi } from '@/api/endpoints';
import {
  clearSession,
  getAccessToken,
  setOrganizationId,
  setTokens,
} from '@/api/tokenStorage';
import { getErrorMessage } from '@/utils/errors';

const initialState = {
  user: null,
  organization: null,
  organizations: [],
  role: null,
  isAuthenticated: Boolean(getAccessToken()),
  // Start in "loading" when a token exists: we must verify it before deciding
  // whether to show the app or bounce to /login.
  status: getAccessToken() ? 'loading' : 'idle',
  error: null,
};

const persistSession = ({ tokens, organization }) => {
  if (tokens) setTokens(tokens);
  if (organization?.id) setOrganizationId(organization.id);
};

export const login = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const { data } = await authApi.login(credentials);
      persistSession(data);
      return data;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to sign in.'));
    }
  },
);

export const register = createAsyncThunk(
  'auth/register',
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await authApi.register(payload);
      persistSession(data);
      return data;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to create your account.'));
    }
  },
);

export const googleLogin = createAsyncThunk(
  'auth/googleLogin',
  async (idToken, { rejectWithValue }) => {
    try {
      const { data } = await authApi.googleLogin(idToken);
      persistSession(data);
      return data;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Google sign-in failed.'));
    }
  },
);

/** Called once on boot to turn a stored token into a hydrated session. */
export const loadCurrentUser = createAsyncThunk(
  'auth/loadCurrentUser',
  async (_arg, { rejectWithValue }) => {
    try {
      const { data } = await authApi.me();
      if (data.user?.active_organization?.id) {
        setOrganizationId(data.user.active_organization.id);
      }
      return data.user;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error));
    }
  },
);

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await authApi.updateMe(payload);
      return data.user;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error));
    }
  },
);

export const switchOrganization = createAsyncThunk(
  'auth/switchOrganization',
  async (organizationId, { rejectWithValue }) => {
    try {
      const { data } = await authApi.switchOrganization(organizationId);
      setOrganizationId(organizationId);
      return data;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Could not switch workspace.'));
    }
  },
);

export const logout = createAsyncThunk('auth/logout', async (_arg, { getState }) => {
  const refresh = localStorage.getItem('nexuscrm.refresh');
  try {
    if (refresh) await authApi.logout({ refresh });
  } catch {
    // A failed logout call must never trap the user in the app.
  }
  clearSession();
  return getState().auth.user?.id ?? null;
});

const applyUser = (state, user) => {
  state.user = user;
  state.role = user?.role ?? null;
  state.organization = user?.active_organization ?? null;
  state.organizations = user?.organizations ?? [];
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    sessionExpired(state) {
      Object.assign(state, {
        ...initialState,
        isAuthenticated: false,
        status: 'idle',
        error: 'Your session has expired. Please sign in again.',
      });
    },
    clearAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    const authFulfilled = (state, action) => {
      state.status = 'succeeded';
      state.isAuthenticated = true;
      state.error = null;
      applyUser(state, action.payload.user);
      if (action.payload.organization) state.organization = action.payload.organization;
    };

    builder
      .addCase(login.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(login.fulfilled, authFulfilled)
      .addCase(login.rejected, (state, action) => {
        state.status = 'failed';
        state.isAuthenticated = false;
        state.error = action.payload;
      })

      .addCase(register.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(register.fulfilled, authFulfilled)
      .addCase(register.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })

      .addCase(googleLogin.fulfilled, authFulfilled)
      .addCase(googleLogin.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })

      .addCase(loadCurrentUser.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(loadCurrentUser.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.isAuthenticated = true;
        applyUser(state, action.payload);
      })
      .addCase(loadCurrentUser.rejected, (state) => {
        Object.assign(state, initialState, { isAuthenticated: false, status: 'idle' });
      })

      .addCase(updateProfile.fulfilled, (state, action) => {
        applyUser(state, action.payload);
      })

      .addCase(switchOrganization.fulfilled, (state, action) => {
        applyUser(state, action.payload.user);
        state.organization = action.payload.organization;
      })

      .addCase(logout.fulfilled, (state) => {
        Object.assign(state, initialState, { isAuthenticated: false, status: 'idle' });
      });
  },
});

export const { sessionExpired, clearAuthError } = authSlice.actions;

export const selectAuth = (state) => state.auth;
export const selectUser = (state) => state.auth.user;
export const selectRole = (state) => state.auth.role;
export const selectOrganization = (state) => state.auth.organization;
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated;

export default authSlice.reducer;
