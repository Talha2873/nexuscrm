import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useDispatch } from 'react-redux';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import toast from 'react-hot-toast';

import { clearAuthError, register as registerThunk } from '@/features/authSlice';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import GoogleButton from './GoogleButton';

export default function Register() {
  useDocumentTitle('Create account');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const invitationToken = searchParams.get('invitation') || '';
  const { error, isLoading } = useAuth();

  const {
    register: field,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      organization_name: '',
      password: '',
      password_confirm: '',
    },
  });

  useEffect(() => () => dispatch(clearAuthError()), [dispatch]);

  const onSubmit = async (values) => {
    const payload = { ...values, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone };
    if (invitationToken) {
      payload.invitation_token = invitationToken;
      delete payload.organization_name;
    }

    const result = await dispatch(registerThunk(payload));
    if (registerThunk.fulfilled.match(result)) {
      toast.success('Account created. Check your inbox to verify your email.');
      navigate('/dashboard', { replace: true });
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h3" gutterBottom>
        Create your account
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {invitationToken
          ? 'Complete your details to join the workspace you were invited to.'
          : 'Set up a new workspace in under a minute.'}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Stack spacing={2}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="First name"
              autoComplete="given-name"
              autoFocus
              error={Boolean(errors.first_name)}
              helperText={errors.first_name?.message}
              {...field('first_name', { required: 'First name is required' })}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Last name" autoComplete="family-name" {...field('last_name')} />
          </Grid>
        </Grid>

        <TextField
          label="Work email"
          type="email"
          autoComplete="email"
          error={Boolean(errors.email)}
          helperText={errors.email?.message}
          {...field('email', {
            required: 'Email is required',
            pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' },
          })}
        />

        {!invitationToken && (
          <TextField
            label="Workspace name"
            placeholder="Acme Corporation"
            error={Boolean(errors.organization_name)}
            helperText={
              errors.organization_name?.message ||
              'You can rename this later in workspace settings.'
            }
            {...field('organization_name', { required: 'Workspace name is required' })}
          />
        )}

        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          error={Boolean(errors.password)}
          helperText={
            errors.password?.message ||
            'At least 8 characters, with upper and lower case, a number and a symbol.'
          }
          {...field('password', {
            required: 'Password is required',
            minLength: { value: 8, message: 'Use at least 8 characters' },
            validate: {
              upper: (v) => /[A-Z]/.test(v) || 'Include an uppercase letter',
              lower: (v) => /[a-z]/.test(v) || 'Include a lowercase letter',
              digit: (v) => /\d/.test(v) || 'Include a number',
              symbol: (v) => /[^A-Za-z0-9]/.test(v) || 'Include a symbol',
            },
          })}
        />

        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={Boolean(errors.password_confirm)}
          helperText={errors.password_confirm?.message}
          {...field('password_confirm', {
            required: 'Please confirm your password',
            validate: (value) => value === watch('password') || 'The passwords do not match',
          })}
        />

        <Button type="submit" variant="contained" size="large" disabled={isLoading}>
          {isLoading ? 'Creating account…' : 'Create account'}
        </Button>
      </Stack>

      <Divider sx={{ my: 3 }}>
        <Typography variant="caption" color="text.secondary">
          OR
        </Typography>
      </Divider>

      <GoogleButton label="Sign up with Google" />

      <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: 'center' }}>
        Already have an account?{' '}
        <Link component={RouterLink} to="/login" underline="hover" fontWeight={600}>
          Sign in
        </Link>
      </Typography>
    </Box>
  );
}
