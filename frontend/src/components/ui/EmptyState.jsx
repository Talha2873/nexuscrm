import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import InboxOutlinedIcon from '@mui/icons-material/InboxOutlined';

export default function EmptyState({
  icon: Icon = InboxOutlinedIcon,
  title = 'Nothing here yet',
  description,
  actionLabel,
  onAction,
}) {
  return (
    <Box sx={{ textAlign: 'center', py: 8, px: 3 }}>
      <Icon sx={{ fontSize: 48, color: 'text.disabled', mb: 1.5 }} />
      <Typography variant="h5" gutterBottom>
        {title}
      </Typography>
      {description && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ maxWidth: 420, mx: 'auto', mb: 3 }}
        >
          {description}
        </Typography>
      )}
      {actionLabel && onAction && (
        <Button variant="contained" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
