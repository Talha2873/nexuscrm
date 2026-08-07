import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Chip from '@mui/material/Chip';
import LinearProgress from '@mui/material/LinearProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { activityApi } from '@/api/endpoints';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import UserAvatar from '@/components/ui/UserAvatar';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import { formatDateTime, formatRelative } from '@/utils/format';

export default function Activity() {
  useDocumentTitle('Activity');

  const { data, isLoading } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: async () => {
      const { data: payload } = await activityApi.list({ page_size: 50 });
      return payload;
    },
  });

  const activities = data?.results ?? [];

  return (
    <Box>
      <PageHeader
        title="Activity"
        description="A chronological record of what has changed across the workspace."
      />

      <Card>
        {isLoading && <LinearProgress />}

        {!isLoading && activities.length === 0 ? (
          <EmptyState
            title="No activity recorded"
            description="Once your team starts creating and updating records, their actions appear here."
          />
        ) : (
          <List sx={{ py: 0 }}>
            {activities.map((activity, index) => (
              <ListItem
                key={activity.id}
                sx={{
                  alignItems: 'flex-start',
                  gap: 1.5,
                  borderBottom: index === activities.length - 1 ? 0 : 1,
                  borderColor: 'divider',
                  py: 1.5,
                }}
              >
                <UserAvatar user={activity.actor} size={34} />
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                      <Typography variant="body2">{activity.description}</Typography>
                      <Chip size="small" label={activity.verb_display} variant="outlined" />
                    </Stack>
                  }
                  secondary={
                    <Typography variant="caption" color="text.secondary" title={formatDateTime(activity.created_at)}>
                      {formatRelative(activity.created_at)}
                      {activity.actor ? ` · ${activity.actor.full_name || activity.actor.email}` : ''}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Card>
    </Box>
  );
}
