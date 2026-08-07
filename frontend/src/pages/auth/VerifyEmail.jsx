import { useEffect, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';

import { authApi } from '@/api/endpoints';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { getErrorMessage } from '@/utils/errors';

export default function VerifyEmail() {
  useDocumentTitle('Verify email');
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [status, setStatus] = useState(token ? 'verifying' : 'missing');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) return;

    let cancelled = false;
    (async () => {
      try {
        await authApi.verifyEmail(token);
        if (!cancelled) setStatus('verified');
      } catch (error) {
        if (!cancelled) {
          setMessage(getErrorMessage(error));
          setStatus('failed');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (status === 'verifying') {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <CircularProgress size={32} sx={{ mb: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Verifying your email address…
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h3" gutterBottom>
        {status === 'verified' ? 'Email verified' : 'Verification failed'}
      </Typography>

      <Alert severity={status === 'verified' ? 'success' : 'error'} sx={{ my: 2 }}>
        {status === 'verified'
          ? 'Thanks — your email address is confirmed. You now have full access.'
          : message || 'This verification link is missing, invalid or has expired.'}
      </Alert>

      <Button
        component={RouterLink}
        to={status === 'verified' ? '/dashboard' : '/login'}
        fullWidth
        variant="contained"
      >
        {status === 'verified' ? 'Go to dashboard' : 'Back to sign in'}
      </Button>
    </Box>
  );
}
