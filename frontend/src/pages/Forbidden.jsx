import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';

import useDocumentTitle from '@/hooks/useDocumentTitle';

export default function Forbidden() {
  useDocumentTitle('Access denied');
  return (
    <Box sx={{ textAlign: 'center', py: 10 }}>
      <LockOutlinedIcon sx={{ fontSize: 56, color: 'text.disabled', mb: 1 }} />
      <Typography variant="h3" gutterBottom>
        You don&apos;t have access to this page
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Your role in this workspace doesn&apos;t include this area. Ask an administrator if you
        think that&apos;s a mistake.
      </Typography>
      <Button component={RouterLink} to="/dashboard" variant="contained">
        Back to dashboard
      </Button>
    </Box>
  );
}
