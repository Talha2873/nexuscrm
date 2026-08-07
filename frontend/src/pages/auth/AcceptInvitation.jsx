import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import toast from 'react-hot-toast';

import { invitationApi } from '@/api/endpoints';
import { loadCurrentUser } from '@/features/authSlice';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { ROLE_LABELS } from '@/utils/constants';
import { formatDate } from '@/utils/format';
import { getErrorMessage } from '@/utils/errors';

export default function AcceptInvitation() {
  useDocumentTitle('Join workspace');
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, user } = useAuth();
  const [accepting, setAccepting] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['invitation-preview', token],
    queryFn: async () => {
      const { data: payload } = await invitationApi.preview(token);
      return payload;
    },
    enabled: Boolean(token),
    retry: false,
  });

  const accept = async () => {
    setAccepting(true);
    try {
      const { data: payload } = await invitationApi.accept(token);
      await dispatch(loadCurrentUser());
      toast.success(payload.message || 'You have joined the workspace.');
      navigate('/dashboard', { replace: true });
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setAccepting(false);
    }
  };

  if (!token) {
    return (
      <Box>
        <Typography variant="h3" gutterBottom>
          Invalid invitation
        </Typography>
        <Alert severity="error" sx={{ my: 2 }}>
          This invitation link is missing its token.
        </Alert>
        <Button component={RouterLink} to="/login" fullWidth variant="contained">
          Back to sign in
        </Button>
      </Box>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <CircularProgress size={32} sx={{ mb: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading invitation…
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Typography variant="h3" gutterBottom>
          Invitation not found
        </Typography>
        <Alert severity="error" sx={{ my: 2 }}>
          {getErrorMessage(error)}
        </Alert>
        <Button component={RouterLink} to="/login" fullWidth variant="contained">
          Back to sign in
        </Button>
      </Box>
    );
  }

  const emailMismatch = isAuthenticated && user?.email !== data.email;

  return (
    <Box>
      <Typography variant="h3" gutterBottom>
        Join {data.organization_name}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {data.invited_by || 'A teammate'} invited <strong>{data.email}</strong> to collaborate.
      </Typography>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Chip label={ROLE_LABELS[data.role] || data.role} color="primary" size="small" />
        <Chip label={`Expires ${formatDate(data.expires_at)}`} variant="outlined" size="small" />
      </Stack>

      {data.message && (
        <Alert severity="info" sx={{ mb: 2 }}>
          “{data.message}”
        </Alert>
      )}

      {!data.is_valid && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          This invitation is no longer valid ({data.status}). Ask for a new one.
        </Alert>
      )}

      {emailMismatch && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You are signed in as {user.email}. Sign out and sign back in as {data.email} to accept.
        </Alert>
      )}

      {data.is_valid && !isAuthenticated && (
        <Stack spacing={1.5}>
          <Button
            component={RouterLink}
            to={`/register?invitation=${token}`}
            variant="contained"
            size="large"
            fullWidth
          >
            Create an account to join
          </Button>
          <Button component={RouterLink} to="/login" variant="outlined" fullWidth>
            I already have an account
          </Button>
        </Stack>
      )}

      {data.is_valid && isAuthenticated && !emailMismatch && (
        <Button variant="contained" size="large" fullWidth onClick={accept} disabled={accepting}>
          {accepting ? 'Joining…' : `Join ${data.organization_name}`}
        </Button>
      )}
    </Box>
  );
}
