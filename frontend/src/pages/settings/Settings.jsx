import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import toast from 'react-hot-toast';

import { organizationApi } from '@/api/endpoints';
import LoadingScreen from '@/components/ui/LoadingScreen';
import PageHeader from '@/components/ui/PageHeader';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { getErrorMessage } from '@/utils/errors';

const CURRENCIES = ['USD', 'EUR', 'GBP', 'PKR', 'AED', 'INR', 'CAD', 'AUD'];

const FEATURE_TOGGLES = [
  {
    name: 'ai_assistant_enabled',
    label: 'AI assistant',
    hint: 'Chat, email drafting, summaries and proposals.',
  },
  {
    name: 'lead_scoring_enabled',
    label: 'AI lead scoring',
    hint: 'Automatically rank leads by likelihood to convert.',
  },
  {
    name: 'email_notifications_enabled',
    label: 'Email notifications',
    hint: 'Send notification emails in addition to in-app alerts.',
  },
  {
    name: 'realtime_notifications_enabled',
    label: 'Real-time notifications',
    hint: 'Push updates to the browser over WebSockets.',
  },
  {
    name: 'require_email_verification',
    label: 'Require email verification',
    hint: 'New members must confirm their address before full access.',
  },
  {
    name: 'audit_logging_enabled',
    label: 'Audit logging',
    hint: 'Record security-relevant events in an immutable log.',
  },
];

export default function Settings() {
  useDocumentTitle('Settings');
  const queryClient = useQueryClient();
  const { organization, isAdmin } = useAuth();
  const [tab, setTab] = useState(0);

  const organizationId = organization?.id;

  const { data: org, isLoading: orgLoading } = useQuery({
    queryKey: ['organization', organizationId],
    queryFn: async () => {
      const { data } = await organizationApi.retrieve(organizationId);
      return data;
    },
    enabled: Boolean(organizationId),
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['organization-settings', organizationId],
    queryFn: async () => {
      const { data } = await organizationApi.getSettings(organizationId);
      return data;
    },
    enabled: Boolean(organizationId) && isAdmin,
  });

  const profileForm = useForm();
  const isLoading = orgLoading || (isAdmin && settingsLoading);

  const saveOrganization = useMutation({
    mutationFn: (payload) => organizationApi.update(organizationId, payload),
    onSuccess: () => {
      toast.success('Workspace updated');
      queryClient.invalidateQueries({ queryKey: ['organization', organizationId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const saveSettings = useMutation({
    mutationFn: (payload) => organizationApi.updateSettings(organizationId, payload),
    onSuccess: () => {
      toast.success('Settings saved');
      queryClient.invalidateQueries({ queryKey: ['organization-settings', organizationId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  if (!organizationId) {
    return (
      <Alert severity="info">
        You are not currently in a workspace. Create or join one to manage settings.
      </Alert>
    );
  }

  if (isLoading) return <LoadingScreen fullHeight={false} message="Loading settings…" />;

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Settings" description="Your workspace details." />
        <Card>
          <CardContent>
            <Stack spacing={1.5}>
              <Typography variant="h4">{org?.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {org?.full_address || 'No address on file'}
              </Typography>
              <Divider />
              <Typography variant="body2">
                Plan: <strong>{org?.plan}</strong> · {org?.member_count} members ·{' '}
                {org?.seats_remaining} seats remaining
              </Typography>
              <Alert severity="info" sx={{ mt: 1 }}>
                Only administrators can change workspace settings.
              </Alert>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Settings"
        description="Workspace profile, regional defaults and feature switches."
      />

      <Tabs value={tab} onChange={(_event, value) => setTab(value)} sx={{ mb: 2.5 }}>
        <Tab label="General" />
        <Tab label="Regional" />
        <Tab label="Features" />
      </Tabs>

      {tab === 0 && (
        <Card
          component="form"
          onSubmit={profileForm.handleSubmit((values) => saveOrganization.mutate(values))}
        >
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Workspace name"
                  defaultValue={org?.name}
                  {...profileForm.register('name')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Legal name"
                  defaultValue={org?.legal_name}
                  {...profileForm.register('legal_name')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Contact email"
                  type="email"
                  defaultValue={org?.email}
                  {...profileForm.register('email')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Phone"
                  defaultValue={org?.phone}
                  {...profileForm.register('phone')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Website"
                  defaultValue={org?.website}
                  {...profileForm.register('website')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Description"
                  multiline
                  rows={3}
                  defaultValue={org?.description}
                  {...profileForm.register('description')}
                />
              </Grid>
              <Grid item xs={12} sm={8}>
                <TextField
                  label="Address"
                  defaultValue={org?.address_line1}
                  {...profileForm.register('address_line1')}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="City"
                  defaultValue={org?.city}
                  {...profileForm.register('city')}
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 2.5, textAlign: 'right' }}>
              <Button type="submit" variant="contained" disabled={saveOrganization.isPending}>
                {saveOrganization.isPending ? 'Saving…' : 'Save changes'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {tab === 1 && (
        <Card
          component="form"
          onSubmit={profileForm.handleSubmit((values) => saveOrganization.mutate(values))}
        >
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Timezone"
                  defaultValue={org?.timezone}
                  helperText="IANA name, e.g. Asia/Karachi"
                  {...profileForm.register('timezone')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Currency"
                  select
                  defaultValue={org?.currency || 'USD'}
                  {...profileForm.register('currency')}
                >
                  {CURRENCIES.map((currency) => (
                    <MenuItem key={currency} value={currency}>
                      {currency}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Fiscal year starts in month"
                  type="number"
                  inputProps={{ min: 1, max: 12 }}
                  defaultValue={org?.fiscal_year_start_month || 1}
                  {...profileForm.register('fiscal_year_start_month', { valueAsNumber: true })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Tax number"
                  defaultValue={org?.tax_number}
                  {...profileForm.register('tax_number')}
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 2.5, textAlign: 'right' }}>
              <Button type="submit" variant="contained" disabled={saveOrganization.isPending}>
                {saveOrganization.isPending ? 'Saving…' : 'Save changes'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {tab === 2 && (
        <Card>
          <CardContent>
            <Stack divider={<Divider />} spacing={0}>
              {FEATURE_TOGGLES.map(({ name, label, hint }) => (
                <Box
                  key={name}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 2,
                    py: 1.5,
                  }}
                >
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      {label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {hint}
                    </Typography>
                  </Box>
                  <FormControlLabel
                    sx={{ m: 0 }}
                    control={
                      <Switch
                        checked={Boolean(settings?.[name])}
                        onChange={(event) =>
                          saveSettings.mutate({ [name]: event.target.checked })
                        }
                      />
                    }
                    label=""
                  />
                </Box>
              ))}
            </Stack>

            <Divider sx={{ my: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Default deal probability (%)"
                  type="number"
                  inputProps={{ min: 0, max: 100 }}
                  defaultValue={settings?.default_deal_probability ?? 20}
                  onBlur={(event) =>
                    saveSettings.mutate({
                      default_deal_probability: Number(event.target.value),
                    })
                  }
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Ticket SLA (hours)"
                  type="number"
                  inputProps={{ min: 1 }}
                  defaultValue={settings?.ticket_sla_hours ?? 24}
                  onBlur={(event) =>
                    saveSettings.mutate({ ticket_sla_hours: Number(event.target.value) })
                  }
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
