import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useDispatch } from 'react-redux';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import PhotoCameraOutlinedIcon from '@mui/icons-material/PhotoCameraOutlined';
import toast from 'react-hot-toast';

import { authApi } from '@/api/endpoints';
import PageHeader from '@/components/ui/PageHeader';
import UserAvatar from '@/components/ui/UserAvatar';
import { loadCurrentUser, updateProfile } from '@/features/authSlice';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { formatDateTime, formatRelative } from '@/utils/format';
import { getErrorMessage } from '@/utils/errors';

export default function Profile() {
  useDocumentTitle('Profile');
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const profileForm = useForm({
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      phone: user?.phone || '',
      job_title: user?.job_title || '',
      bio: user?.bio || '',
      timezone: user?.timezone || 'UTC',
    },
  });

  const passwordForm = useForm({
    defaultValues: { current_password: '', new_password: '', new_password_confirm: '' },
  });

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: async () => {
      const { data } = await authApi.listSessions();
      return data.results ?? [];
    },
  });

  const saveProfile = async (values) => {
    const result = await dispatch(updateProfile(values));
    if (updateProfile.fulfilled.match(result)) toast.success('Profile updated');
    else toast.error(result.payload || 'Could not update your profile');
  };

  const changePassword = useMutation({
    mutationFn: (payload) => authApi.changePassword(payload),
    onSuccess: () => {
      toast.success('Password changed. Other sessions were signed out.');
      passwordForm.reset();
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const revokeSession = useMutation({
    mutationFn: (id) => authApi.revokeSession(id),
    onSuccess: () => {
      toast.success('Session revoked');
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const onAvatarSelected = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Please choose an image under 5 MB.');
      return;
    }

    setUploading(true);
    try {
      await authApi.uploadAvatar(file);
      await dispatch(loadCurrentUser());
      toast.success('Photo updated');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  return (
    <Box>
      <PageHeader title="Profile" description="Your personal details and account security." />

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Box sx={{ position: 'relative', display: 'inline-block', mb: 1.5 }}>
                <UserAvatar user={user} size={96} />
                <IconButton
                  size="small"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  sx={{
                    position: 'absolute',
                    right: -4,
                    bottom: -4,
                    bgcolor: 'background.paper',
                    border: 1,
                    borderColor: 'divider',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <PhotoCameraOutlinedIcon fontSize="small" />
                </IconButton>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={onAvatarSelected}
                />
              </Box>

              <Typography variant="h4">{user?.full_name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {user?.email}
              </Typography>
              {user?.job_title && (
                <Typography variant="body2" color="text.secondary">
                  {user.job_title}
                </Typography>
              )}

              {!user?.is_email_verified && (
                <Alert severity="warning" sx={{ mt: 2, textAlign: 'left' }}>
                  Email not verified.
                  <Button
                    size="small"
                    sx={{ ml: 0.5 }}
                    onClick={async () => {
                      await authApi.resendVerification(user.email);
                      toast.success('Verification email sent');
                    }}
                  >
                    Resend
                  </Button>
                </Alert>
              )}

              <Divider sx={{ my: 2 }} />
              <Typography variant="caption" color="text.secondary" component="div">
                Joined {formatDateTime(user?.date_joined)}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div">
                {user?.login_count ?? 0} sign-ins
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Stack spacing={2.5}>
            <Card component="form" onSubmit={profileForm.handleSubmit(saveProfile)}>
              <CardContent>
                <Typography variant="h4" gutterBottom>
                  Personal details
                </Typography>

                <Grid container spacing={2} sx={{ mt: 0.5 }}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="First name"
                      error={Boolean(profileForm.formState.errors.first_name)}
                      helperText={profileForm.formState.errors.first_name?.message}
                      {...profileForm.register('first_name', { required: 'First name is required' })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField label="Last name" {...profileForm.register('last_name')} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField label="Phone" {...profileForm.register('phone')} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField label="Job title" {...profileForm.register('job_title')} />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField label="Timezone" {...profileForm.register('timezone')} />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField label="Bio" multiline rows={3} {...profileForm.register('bio')} />
                  </Grid>
                </Grid>

                <Box sx={{ mt: 2, textAlign: 'right' }}>
                  <Button type="submit" variant="contained">
                    Save changes
                  </Button>
                </Box>
              </CardContent>
            </Card>

            <Card
              component="form"
              onSubmit={passwordForm.handleSubmit((values) => changePassword.mutate(values))}
            >
              <CardContent>
                <Typography variant="h4" gutterBottom>
                  Change password
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Changing your password signs you out of every other device.
                </Typography>

                <Stack spacing={2}>
                  <TextField
                    label="Current password"
                    type="password"
                    autoComplete="current-password"
                    error={Boolean(passwordForm.formState.errors.current_password)}
                    helperText={passwordForm.formState.errors.current_password?.message}
                    {...passwordForm.register('current_password', {
                      required: 'Enter your current password',
                    })}
                  />
                  <TextField
                    label="New password"
                    type="password"
                    autoComplete="new-password"
                    error={Boolean(passwordForm.formState.errors.new_password)}
                    helperText={
                      passwordForm.formState.errors.new_password?.message ||
                      'At least 8 characters, with upper and lower case, a number and a symbol.'
                    }
                    {...passwordForm.register('new_password', {
                      required: 'Enter a new password',
                      minLength: { value: 8, message: 'Use at least 8 characters' },
                    })}
                  />
                  <TextField
                    label="Confirm new password"
                    type="password"
                    autoComplete="new-password"
                    error={Boolean(passwordForm.formState.errors.new_password_confirm)}
                    helperText={passwordForm.formState.errors.new_password_confirm?.message}
                    {...passwordForm.register('new_password_confirm', {
                      required: 'Confirm your new password',
                      validate: (value) =>
                        value === passwordForm.watch('new_password') ||
                        'The passwords do not match',
                    })}
                  />
                </Stack>

                <Box sx={{ mt: 2, textAlign: 'right' }}>
                  <Button type="submit" variant="contained" disabled={changePassword.isPending}>
                    {changePassword.isPending ? 'Updating…' : 'Change password'}
                  </Button>
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent sx={{ pb: 0 }}>
                <Typography variant="h4">Active sessions</Typography>
                <Typography variant="body2" color="text.secondary">
                  Devices currently signed in to your account.
                </Typography>
              </CardContent>

              <List>
                {(sessions ?? []).map((session) => (
                  <ListItem
                    key={session.id}
                    secondaryAction={
                      <Button
                        size="small"
                        color="error"
                        onClick={() => revokeSession.mutate(session.id)}
                      >
                        Revoke
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={session.device || 'Unknown device'}
                      secondary={`${session.ip_address || 'Unknown IP'} · last seen ${formatRelative(
                        session.last_seen_at,
                      )}`}
                      primaryTypographyProps={{ fontSize: 14, noWrap: true }}
                      secondaryTypographyProps={{ fontSize: 12 }}
                    />
                  </ListItem>
                ))}
                {(sessions ?? []).length === 0 && (
                  <ListItem>
                    <ListItemText
                      secondary="No other active sessions."
                      secondaryTypographyProps={{ fontSize: 13 }}
                    />
                  </ListItem>
                )}
              </List>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
