import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { authApi } from '@/api/endpoints';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { getErrorMessage } from '@/utils/errors';

export default function ForgotPassword() {
  useDocumentTitle('Reset password');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register: field,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm({ defaultValues: { email: '' } });

  const onSubmit = async ({ email }) => {
    setSubmitting(true);
    setError(null);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <Box>
        <Typography variant="h3" gutterBottom>
          Check your inbox
        </Typography>
        <Alert severity="success" sx={{ my: 2 }}>
          If an account exists for <strong>{getValues('email')}</strong>, we&apos;ve sent a
          password reset link. It expires in two hours.
        </Alert>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Nothing arrived? Check your spam folder, or try again in a few minutes.
        </Typography>
        <Button component={RouterLink} to="/login" fullWidth variant="outlined">
          Back to sign in
        </Button>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h3" gutterBottom>
        Forgot your password?
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Enter the email you signed up with and we&apos;ll send you a reset link.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Stack spacing={2}>
        <TextField
          label="Email address"
          type="email"
          autoComplete="email"
          autoFocus
          error={Boolean(errors.email)}
          helperText={errors.email?.message}
          {...field('email', {
            required: 'Email is required',
            pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' },
          })}
        />

        <Button type="submit" variant="contained" size="large" disabled={submitting}>
          {submitting ? 'Sending…' : 'Send reset link'}
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
