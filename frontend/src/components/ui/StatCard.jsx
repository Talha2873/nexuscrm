import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

export default function StatCard({ label, value, icon: Icon, color = 'primary', hint, loading }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary" noWrap>
              {label}
            </Typography>
            {loading ? (
              <Skeleton width={90} height={40} />
            ) : (
              <Typography variant="h2" sx={{ mt: 0.5 }}>
                {value}
              </Typography>
            )}
            {hint && (
              <Typography variant="caption" color="text.secondary">
                {hint}
              </Typography>
            )}
          </Box>
          {Icon && (
            <Box
              sx={{
                display: 'grid',
                placeItems: 'center',
                width: 44,
                height: 44,
                borderRadius: 2,
                bgcolor: `${color}.main`,
                opacity: 0.12,
                position: 'relative',
                flexShrink: 0,
              }}
            >
              <Icon sx={{ color: `${color}.main`, opacity: 1, position: 'absolute' }} />
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
