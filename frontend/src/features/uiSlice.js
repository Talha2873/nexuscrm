import { createSlice } from '@reduxjs/toolkit';

import { STORAGE_KEYS } from '@/utils/constants';

const readThemeMode = () => {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.themeMode) || 'system';
  } catch {
    return 'system';
  }
};

const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    themeMode: readThemeMode(),
    sidebarOpen: true,
    mobileSidebarOpen: false,
    searchOpen: false,
  },
  reducers: {
    setThemeMode(state, action) {
      state.themeMode = action.payload;
      try {
        window.localStorage.setItem(STORAGE_KEYS.themeMode, action.payload);
      } catch {
        /* storage unavailable */
      }
    },
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setMobileSidebar(state, action) {
      state.mobileSidebarOpen = action.payload;
    },
    setSearchOpen(state, action) {
      state.searchOpen = action.payload;
    },
  },
});

export const { setThemeMode, toggleSidebar, setMobileSidebar, setSearchOpen } =
  uiSlice.actions;

export const selectThemeMode = (state) => state.ui.themeMode;
export const selectSidebarOpen = (state) => state.ui.sidebarOpen;

export default uiSlice.reducer;
