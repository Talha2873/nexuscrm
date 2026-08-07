import { configureStore } from '@reduxjs/toolkit';

import authReducer, { sessionExpired } from '@/features/authSlice';
import uiReducer from '@/features/uiSlice';
import { onSessionExpired } from '@/api/client';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: { ignoredActions: ['auth/uploadAvatar/pending'] },
    }),
});

// The axios layer cannot import the store (circular), so it broadcasts instead.
onSessionExpired(() => store.dispatch(sessionExpired()));

export default store;
