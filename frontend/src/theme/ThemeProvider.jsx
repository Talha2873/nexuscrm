import { useEffect, useMemo } from 'react';
import { useSelector } from 'react-redux';
import CssBaseline from '@mui/material/CssBaseline';
import useMediaQuery from '@mui/material/useMediaQuery';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { Toaster } from 'react-hot-toast';

import { selectThemeMode } from '@/features/uiSlice';
import buildTheme from './theme';

/**
 * Resolves the user's preference ('light' | 'dark' | 'system') into a concrete
 * mode, applies it to MUI, and mirrors it onto <html class="dark"> so Tailwind
 * utility variants work too.
 */
export default function ThemeProvider({ children }) {
  const preference = useSelector(selectThemeMode);
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');

  const mode = preference === 'system' ? (prefersDark ? 'dark' : 'light') : preference;
  const theme = useMemo(() => buildTheme(mode), [mode]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', mode === 'dark');
    root.style.colorScheme = mode;
  }, [mode]);

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: mode === 'dark' ? '#111827' : '#ffffff',
            color: mode === 'dark' ? '#e2e8f0' : '#0f172a',
            border: `1px solid ${mode === 'dark' ? '#1e293b' : '#e2e8f0'}`,
            fontSize: '0.875rem',
          },
          success: { iconTheme: { primary: '#16a34a', secondary: '#fff' } },
          error: { iconTheme: { primary: '#dc2626', secondary: '#fff' } },
        }}
      />
    </MuiThemeProvider>
  );
}
