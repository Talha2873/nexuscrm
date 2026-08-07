import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import LinearProgress from '@mui/material/LinearProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import BusinessOutlinedIcon from '@mui/icons-material/BusinessOutlined';
import EventSeatOutlinedIcon from '@mui/icons-material/EventSeatOutlined';

import { activityApi, organizationApi } from '@/api/endpoints';
import PageHeader from '@/components/ui/PageHeader';
import StatCard from '@/components/ui/StatCard';
import UserAvatar from '@/components/ui/UserAvatar';
import EmptyState from '@/components/ui/EmptyState';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { formatBytes, formatNumber, formatRelative } from '@/utils/format';

export default function Dashboard() {
  useDocumentTitle('Dashboard');
  const navigate = useNavigate();
  const { user, organization, isManager } = useAuth();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['organization-stats', organization?.id],
    queryFn: async () => {
      const { data } = await organizationApi.stats(organization.id);
      return data;
    },
    enabled: Boolean(organization?.id),
  });

  const { data: activityPage, isLoading: activityLoading } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: async () => {
      const { data } = await activityApi.list({ page_size: 8 });
      return data;
    },
  });

  const activities = activityPage?.results ?? [];
  const storagePercent = stats?.storage_limit_bytes
    ? Math.min((stats.storage_used_bytes / stats.storage_limit_bytes) * 100, 100)
    : 0;
  const seatPercent = stats?.seats_total
    ? Math.min((stats.member_count / stats.seats_total) * 100, 100)
    : 0;

  return (
    <Box>
      <PageHeader
        title={`Welcome back, ${user?.first_name || 'there'}`}
        description={
          organization
            ? `Here's what's happening in ${organization.name}.`
            : 'You are not currently in a workspace.'
        }
        action={
          isManager && (
            <Button variant="contained" onClick={() => navigate('/invitations')}>
              Invite teammates
            </Button>
          )
        }
      />

      {user && !user.is_email_verified && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Your email address is not verified yet. Check your inbox for the confirmation link —
          some features stay locked until you confirm.
        </Alert>
      )}

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            label="Team members"
            value={formatNumber(stats?.member_count ?? 0)}
            hint={stats ? `${stats.seats_remaining} seats remaining` : undefined}
            icon={GroupsOutlinedIcon}
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            label="Teams"
            value={formatNumber(stats?.team_count ?? 0)}
            icon={AccountTreeOutlinedIcon}
            color="secondary"
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            label="Departments"
            value={formatNumber(stats?.department_count ?? 0)}
            icon={BusinessOutlinedIcon}
            color="info"
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            label="Plan"
            value={(stats?.plan || 'free').replace(/^./, (c) => c.toUpperCase())}
            hint={stats?.is_on_trial ? 'Trial active' : undefined}
            icon={EventSeatOutlinedIcon}
            color="success"
            loading={statsLoading}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={5}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h4" gutterBottom>
                Usage
              </Typography>

              <Stack spacing={3} sx={{ mt: 2 }}>
                <Box>
                  <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.75 }}>
                    <Typography variant="body2">Seats</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {stats?.member_count ?? 0} / {stats?.seats_total ?? 0}
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={seatPercent}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                <Box>
                  <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.75 }}>
                    <Typography variant="body2">Storage</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatBytes(stats?.storage_used_bytes)} /{' '}
                      {formatBytes(stats?.storage_limit_bytes)}
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={storagePercent}
                    color={storagePercent > 85 ? 'warning' : 'primary'}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ pb: 1 }}>
              <Typography variant="h4">Recent activity</Typography>
            </CardContent>

            {activityLoading ? (
              <Box sx={{ px: 3, pb: 3 }}>
                <LinearProgress />
              </Box>
            ) : activities.length === 0 ? (
              <EmptyState
                title="No activity yet"
                description="Actions across your workspace will appear here as your team gets going."
              />
            ) : (
              <List dense sx={{ pt: 0 }}>
                {activities.map((activity) => (
                  <ListItem key={activity.id} sx={{ alignItems: 'flex-start', gap: 1.5 }}>
                    <UserAvatar user={activity.actor} size={30} />
                    <ListItemText
                      primary={activity.description}
                      secondary={formatRelative(activity.created_at)}
                      primaryTypographyProps={{ fontSize: 14 }}
                      secondaryTypographyProps={{ fontSize: 12 }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
