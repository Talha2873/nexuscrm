import { Outlet } from 'react-router-dom';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

import { APP_NAME } from '@/utils/constants';

/** Centered card shell used by every unauthenticated page. */
export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        background: (theme) =>
          theme.palette.mode === 'dark'
            ? 'linear-gradient(160deg, #0b1220 0%, #111827 100%)'
            : 'linear-gradient(160deg, #eff6ff 0%, #f8fafc 60%)',
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 440 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 2,
              bgcolor: 'primary.main',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
              fontWeight: 700,
              fontSize: 22,
              mx: 'auto',
              mb: 1.5,
            }}
          >
            N
          </Box>
          <Typography variant="h2">{APP_NAME}</Typography>
          <Typography variant="body2" color="text.secondary">
            AI-powered customer relationship management
          </Typography>
        </Box>

        <Paper variant="outlined" sx={{ p: { xs: 3, sm: 4 } }}>
          <Outlet />
        </Paper>
      </Box>
    </Box>
  );
}
