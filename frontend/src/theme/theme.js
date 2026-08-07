import { createTheme } from '@mui/material/styles';

const shared = {
  typography: {
    fontFamily: "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
    h1: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontSize: '1.25rem', fontWeight: 600 },
    h4: { fontSize: '1.125rem', fontWeight: 600 },
    h5: { fontSize: '1rem', fontWeight: 600 },
    h6: { fontSize: '0.9375rem', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
};

const components = (mode) => ({
  MuiButton: {
    styleOverrides: {
      root: { borderRadius: 8, paddingInline: 16 },
      containedPrimary: { boxShadow: 'none', '&:hover': { boxShadow: 'none' } },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: { backgroundImage: 'none' },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        border: `1px solid ${mode === 'dark' ? '#1e293b' : '#e2e8f0'}`,
        boxShadow: 'none',
      },
    },
  },
  MuiTextField: {
    defaultProps: { size: 'small', fullWidth: true },
  },
  MuiTableCell: {
    styleOverrides: {
      head: { fontWeight: 600, whiteSpace: 'nowrap' },
    },
  },
  MuiChip: {
    styleOverrides: { root: { fontWeight: 500 } },
  },
  MuiTooltip: {
    defaultProps: { arrow: true },
  },
});

export const buildTheme = (mode) =>
  createTheme({
    ...shared,
    palette:
      mode === 'dark'
        ? {
            mode: 'dark',
            primary: { main: '#60a5fa', dark: '#3b82f6', light: '#93c5fd' },
            secondary: { main: '#a78bfa' },
            background: { default: '#0b1220', paper: '#111827' },
            text: { primary: '#e2e8f0', secondary: '#94a3b8' },
            divider: '#1e293b',
            success: { main: '#4ade80' },
            warning: { main: '#fbbf24' },
            error: { main: '#f87171' },
            info: { main: '#38bdf8' },
          }
        : {
            mode: 'light',
            primary: { main: '#2563eb', dark: '#1d4ed8', light: '#60a5fa' },
            secondary: { main: '#7c3aed' },
            background: { default: '#f8fafc', paper: '#ffffff' },
            text: { primary: '#0f172a', secondary: '#64748b' },
            divider: '#e2e8f0',
            success: { main: '#16a34a' },
            warning: { main: '#d97706' },
            error: { main: '#dc2626' },
            info: { main: '#0284c7' },
          },
    components: components(mode),
  });

export default buildTheme;
