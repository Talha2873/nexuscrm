import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import InputAdornment from '@mui/material/InputAdornment';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import SearchIcon from '@mui/icons-material/Search';

import { auditApi } from '@/api/endpoints';
import DataTable from '@/components/ui/DataTable';
import PageHeader from '@/components/ui/PageHeader';
import useDebounce from '@/hooks/useDebounce';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import usePagination from '@/hooks/usePagination';
import { formatDateTime } from '@/utils/format';

const ACTION_COLORS = {
  create: 'success',
  update: 'info',
  delete: 'error',
  login: 'default',
  login_failed: 'warning',
  logout: 'default',
  password_change: 'warning',
  export: 'secondary',
};

export default function AuditLog() {
  useDocumentTitle('Audit log');
  const pagination = usePagination({ initialOrdering: '-created_at' });
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', { ...pagination.params, search: debouncedSearch }],
    queryFn: async () => {
      const { data: payload } = await auditApi.list({
        ...pagination.params,
        search: debouncedSearch || undefined,
      });
      return payload;
    },
    keepPreviousData: true,
  });

  const columns = [
    {
      id: 'created_at',
      label: 'When',
      sortable: true,
      width: 180,
      render: (row) => (
        <Typography variant="body2" color="text.secondary" noWrap>
          {formatDateTime(row.created_at)}
        </Typography>
      ),
    },
    {
      id: 'actor_email',
      label: 'Actor',
      render: (row) => row.actor?.full_name || row.actor_email || 'System',
    },
    {
      id: 'action',
      label: 'Action',
      sortable: true,
      render: (row) => (
        <Chip
          size="small"
          label={row.action_display}
          color={ACTION_COLORS[row.action] || 'default'}
          variant="outlined"
        />
      ),
    },
    {
      id: 'resource_repr',
      label: 'Resource',
      render: (row) => (
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" noWrap>
            {row.resource_repr || '—'}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap component="div">
            {row.resource_type}
          </Typography>
        </Box>
      ),
    },
    {
      id: 'ip_address',
      label: 'IP address',
      render: (row) => (
        <Typography variant="body2" color="text.secondary">
          {row.ip_address || '—'}
        </Typography>
      ),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Audit log"
        description="An immutable record of security-relevant events. Administrators only."
      />

      <Stack sx={{ mb: 2 }}>
        <TextField
          placeholder="Search by actor, resource or path…"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          sx={{ maxWidth: 380 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
          }}
        />
      </Stack>

      <DataTable
        columns={columns}
        rows={data?.results ?? []}
        loading={isLoading}
        count={data?.count ?? 0}
        page={pagination.page}
        pageSize={pagination.pageSize}
        ordering={pagination.ordering}
        onPageChange={pagination.setPage}
        onPageSizeChange={pagination.setPageSize}
        onSort={pagination.setOrdering}
        emptyTitle="No audit entries"
        emptyDescription="Logins, data changes and exports will be recorded here."
      />
    </Box>
  );
}
