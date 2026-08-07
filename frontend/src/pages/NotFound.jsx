import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

import useDocumentTitle from '@/hooks/useDocumentTitle';

export default function NotFound() {
  useDocumentTitle('Page not found');
  return (
    <Box sx={{ textAlign: 'center', py: 10 }}>
      <Typography variant="h1" sx={{ fontSize: '4rem', color: 'text.disabled' }}>
        404
      </Typography>
      <Typography variant="h3" gutterBottom>
        Page not found
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        The page you&apos;re looking for doesn&apos;t exist or has moved.
      </Typography>
      <Button component={RouterLink} to="/dashboard" variant="contained">
        Back to dashboard
      </Button>
    </Box>
  );
}
