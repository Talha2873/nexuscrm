import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import toast from 'react-hot-toast';

import { authApi } from '@/api/endpoints';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { getErrorMessage } from '@/utils/errors';

export default function ResetPassword() {
  useDocumentTitle('Choose a new password');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register: field,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({ defaultValues: { password: '', password_confirm: '' } });

  const onSubmit = async (values) => {
    setSubmitting(true);
    setError(null);
    try {
      await authApi.resetPassword({ token, ...values });
      toast.success('Password updated. Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <Box>
        <Typography variant="h3" gutterBottom>
          Invalid link
        </Typography>
        <Alert severity="error" sx={{ my: 2 }}>
          This password reset link is missing its token. Request a new one.
        </Alert>
        <Button component={RouterLink} to="/forgot-password" fullWidth variant="contained">
          Request a new link
        </Button>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h3" gutterBottom>
        Choose a new password
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        For your security, you&apos;ll be signed out everywhere else.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Stack spacing={2}>
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          autoFocus
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
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={Boolean(errors.password_confirm)}
          helperText={errors.password_confirm?.message}
          {...field('password_confirm', {
            required: 'Please confirm your password',
            validate: (value) => value === watch('password') || 'The passwords do not match',
          })}
        />

        <Button type="submit" variant="contained" size="large" disabled={submitting}>
          {submitting ? 'Updating…' : 'Update password'}
        </Button>

        <Typography variant="body2" sx={{ textAlign: 'center' }}>
          <Link component={RouterLink} to="/login" underline="hover">
            Back to sign in
          </Link>
        </Typography>
      </Stack>
    </Box>
  );
}
