import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import SearchIcon from '@mui/icons-material/Search';
import toast from 'react-hot-toast';

import { membershipApi } from '@/api/endpoints';
import DataTable from '@/components/ui/DataTable';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import PageHeader from '@/components/ui/PageHeader';
import UserAvatar from '@/components/ui/UserAvatar';
import useAuth from '@/hooks/useAuth';
import useDebounce from '@/hooks/useDebounce';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import usePagination from '@/hooks/usePagination';
import { ROLE_COLORS, ROLE_LABELS, ROLES } from '@/utils/constants';
import { formatRelative } from '@/utils/format';
import { getErrorMessage } from '@/utils/errors';

const ASSIGNABLE_ROLES = [ROLES.ADMIN, ROLES.MANAGER, ROLES.MEMBER, ROLES.VIEWER];

export default function Members() {
  useDocumentTitle('Members');
  const queryClient = useQueryClient();
  const { user, isAdmin } = useAuth();

  const pagination = usePagination({ initialOrdering: '-created_at' });
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [activeRow, setActiveRow] = useState(null);
  const [removeTarget, setRemoveTarget] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['memberships', { ...pagination.params, search: debouncedSearch }],
    queryFn: async () => {
      const { data: payload } = await membershipApi.list({
        ...pagination.params,
        search: debouncedSearch || undefined,
      });
      return payload;
    },
    keepPreviousData: true,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['memberships'] });

  const changeRole = useMutation({
    mutationFn: ({ id, role }) => membershipApi.changeRole(id, role),
    onSuccess: () => {
      toast.success('Role updated');
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const removeMember = useMutation({
    mutationFn: (id) => membershipApi.remove(id),
    onSuccess: () => {
      toast.success('Member removed');
      setRemoveTarget(null);
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const openMenu = (event, row) => {
    event.stopPropagation();
    setActiveRow(row);
    setMenuAnchor(event.currentTarget);
  };

  const closeMenu = () => {
    setMenuAnchor(null);
    setActiveRow(null);
  };

  const columns = [
    {
      id: 'user',
      label: 'Member',
      render: (row) => (
        <Stack direction="row" spacing={1.5} alignItems="center">
          <UserAvatar user={row.user} size={34} />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" fontWeight={600} noWrap>
              {row.user.full_name || row.user.email}
              {row.user.id === user?.id && (
                <Typography component="span" variant="caption" color="text.secondary">
                  {' '}
                  (you)
                </Typography>
              )}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {row.user.email}
            </Typography>
          </Box>
        </Stack>
      ),
    },
    {
      id: 'role',
      label: 'Role',
      sortable: true,
      render: (row) => (
        <Chip
          size="small"
          label={ROLE_LABELS[row.role] || row.role}
          color={ROLE_COLORS[row.role] || 'default'}
          variant={row.role === ROLES.OWNER ? 'filled' : 'outlined'}
        />
      ),
    },
    { id: 'title', label: 'Title', render: (row) => row.title || '—' },
    { id: 'department_name', label: 'Department', render: (row) => row.department_name || '—' },
    {
      id: 'is_active',
      label: 'Status',
      render: (row) =>
        row.is_active ? (
          <Chip size="small" label="Active" color="success" variant="outlined" />
        ) : (
          <Chip size="small" label="Removed" variant="outlined" />
        ),
    },
    {
      id: 'last_login',
      label: 'Last seen',
      render: (row) => (
        <Typography variant="body2" color="text.secondary">
          {formatRelative(row.last_login)}
        </Typography>
      ),
    },
    {
      id: 'actions',
      label: '',
      align: 'right',
      width: 56,
      render: (row) =>
        isAdmin && row.role !== ROLES.OWNER && row.user.id !== user?.id ? (
          <Tooltip title="Manage member">
            <IconButton size="small" onClick={(event) => openMenu(event, row)}>
              <MoreVertIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ) : null,
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Members"
        description="Everyone with access to this workspace, and what they can do."
      />

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2 }}>
        <TextField
          placeholder="Search by name or email…"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          sx={{ maxWidth: 360 }}
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
        emptyTitle="No members found"
        emptyDescription="Try a different search, or invite someone to the workspace."
      />

      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={closeMenu}>
        <Typography variant="caption" sx={{ px: 2, py: 1, display: 'block', color: 'text.secondary' }}>
          Change role
        </Typography>
        {ASSIGNABLE_ROLES.map((role) => (
          <MenuItem
            key={role}
            selected={activeRow?.role === role}
            disabled={changeRole.isPending}
            onClick={() => {
              changeRole.mutate({ id: activeRow.id, role });
              closeMenu();
            }}
          >
            {ROLE_LABELS[role]}
          </MenuItem>
        ))}
        <MenuItem
          sx={{ color: 'error.main', mt: 0.5 }}
          onClick={() => {
            setRemoveTarget(activeRow);
            setMenuAnchor(null);
          }}
        >
          Remove from workspace
        </MenuItem>
      </Menu>

      <ConfirmDialog
        open={Boolean(removeTarget)}
        title="Remove this member?"
        message={`${
          removeTarget?.user?.full_name || removeTarget?.user?.email
        } will immediately lose access to this workspace. Their records stay intact.`}
        confirmLabel="Remove member"
        destructive
        loading={removeMember.isPending}
        onConfirm={() => removeMember.mutate(removeTarget.id)}
        onClose={() => setRemoveTarget(null)}
      />
    </Box>
  );
}
