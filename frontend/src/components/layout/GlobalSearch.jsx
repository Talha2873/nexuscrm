import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import InputAdornment from '@mui/material/InputAdornment';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import SearchIcon from '@mui/icons-material/Search';

import { searchApi } from '@/api/endpoints';
import useDebounce from '@/hooks/useDebounce';

export default function GlobalSearch({ open, onClose }) {
  const navigate = useNavigate();
  const [term, setTerm] = useState('');
  const debounced = useDebounce(term, 300);

  useEffect(() => {
    if (!open) setTerm('');
  }, [open]);

  const { data, isFetching } = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: async () => {
      const { data: payload } = await searchApi.global(debounced);
      return payload;
    },
    enabled: open && debounced.trim().length >= 2,
  });

  const results = data?.results ?? [];

  const openResult = (result) => {
    onClose();
    navigate(result.url);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      slotProps={{ paper: { sx: { position: 'fixed', top: 72, m: 0 } } }}
    >
      <Box sx={{ p: 2, pb: results.length ? 1 : 2 }}>
        <TextField
          autoFocus
          placeholder="Search customers, deals, tickets…"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          size="medium"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
            endAdornment: isFetching ? (
              <InputAdornment position="end">
                <CircularProgress size={18} />
              </InputAdornment>
            ) : null,
          }}
        />
      </Box>

      {debounced.trim().length >= 2 && !isFetching && results.length === 0 && (
        <Box sx={{ px: 3, pb: 3 }}>
          <Typography variant="body2" color="text.secondary">
            No matches for “{debounced}”.
          </Typography>
        </Box>
      )}

      {results.length > 0 && (
        <List dense sx={{ maxHeight: 400, overflowY: 'auto', pt: 0 }}>
          {results.map((result) => (
            <ListItemButton key={`${result.type}-${result.id}`} onClick={() => openResult(result)}>
              <ListItemText primary={result.title} secondary={result.subtitle || undefined} />
              <Chip label={result.type} size="small" variant="outlined" />
            </ListItemButton>
          ))}
        </List>
      )}
    </Dialog>
  );
}
