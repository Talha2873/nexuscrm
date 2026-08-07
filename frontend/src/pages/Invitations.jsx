import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';
import toast from 'react-hot-toast';

import { invitationApi } from '@/api/endpoints';
import DataTable from '@/components/ui/DataTable';
import PageHeader from '@/components/ui/PageHeader';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import usePagination from '@/hooks/usePagination';
import { INVITATION_STATUS_COLORS, ROLE_LABELS, ROLES } from '@/utils/constants';
import { formatDate, formatRelative } from '@/utils/format';
import { getErrorMessage } from '@/utils/errors';

const INVITABLE_ROLES = [ROLES.ADMIN, ROLES.MANAGER, ROLES.MEMBER, ROLES.VIEWER];

export default function Invitations() {
  useDocumentTitle('Invitations');
  const queryClient = useQueryClient();
  const pagination = usePagination();
  const [dialogOpen, setDialogOpen] = useState(false);

  const {
    register: field,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: { email: '', role: ROLES.MEMBER, message: '' } });

  const { data, isLoading } = useQuery({
    queryKey: ['invitations', pagination.params],
    queryFn: async () => {
      const { data: payload } = await invitationApi.list(pagination.params);
      return payload;
    },
    keepPreviousData: true,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['invitations'] });

  const sendInvitation = useMutation({
    mutationFn: (payload) => invitationApi.create(payload),
    onSuccess: () => {
      toast.success('Invitation sent');
      setDialogOpen(false);
      reset();
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const resend = useMutation({
    mutationFn: (id) => invitationApi.resend(id),
    onSuccess: () => {
      toast.success('Invitation resent');
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const revoke = useMutation({
    mutationFn: (id) => invitationApi.revoke(id),
    onSuccess: () => {
      toast.success('Invitation revoked');
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const columns = [
    {
      id: 'email',
      label: 'Invitee',
      render: (row) => (
        <Box>
          <Typography variant="body2" fontWeight={600}>
            {row.email}
          </Typography>
          {row.message && (
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              “{row.message}”
            </Typography>
          )}
        </Box>
      ),
    },
    {
      id: 'role',
      label: 'Role',
      render: (row) => <Chip size="small" variant="outlined" label={ROLE_LABELS[row.role] || row.role} />,
    },
    {
      id: 'status',
      label: 'Status',
      sortable: true,
      render: (row) => (
        <Chip
          size="small"
          label={row.status_display}
          color={INVITATION_STATUS_COLORS[row.status] || 'default'}
          variant="outlined"
        />
      ),
    },
    {
      id: 'invited_by',
      label: 'Invited by',
      render: (row) => row.invited_by?.full_name || '—',
    },
    {
      id: 'expires_at',
      label: 'Expires',
      sortable: true,
      render: (row) => (
        <Typography variant="body2" color="text.secondary">
          {formatDate(row.expires_at)}
        </Typography>
      ),
    },
    {
      id: 'created_at',
      label: 'Sent',
      sortable: true,
      render: (row) => (
        <Typography variant="body2" color="text.secondary">
          {formatRelative(row.created_at)}
        </Typography>
      ),
    },
    {
      id: 'actions',
      label: '',
      align: 'right',
      width: 170,
      render: (row) =>
        row.status === 'pending' ? (
          <Stack direction="row" spacing={0.5} justifyContent="flex-end">
            <Button size="small" onClick={() => resend.mutate(row.id)} disabled={resend.isPending}>
              Resend
            </Button>
            <Button
              size="small"
              color="error"
              onClick={() => revoke.mutate(row.id)}
              disabled={revoke.isPending}
            >
              Revoke
            </Button>
          </Stack>
        ) : null,
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Invitations"
        description="Pending and past invitations to this workspace."
        action={
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Invite someone
          </Button>
        }
      />

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
        emptyTitle="No invitations yet"
        emptyDescription="Invite colleagues by email and choose what they can do."
        emptyAction={{ label: 'Invite someone', onClick: () => setDialogOpen(true) }}
      />

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="xs">
        <Box component="form" onSubmit={handleSubmit((values) => sendInvitation.mutate(values))}>
          <DialogTitle>Invite to workspace</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Email address"
                type="email"
                autoFocus
                error={Boolean(errors.email)}
                helperText={errors.email?.message}
                {...field('email', {
                  required: 'Email is required',
                  pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' },
                })}
              />
              <TextField label="Role" select defaultValue={ROLES.MEMBER} {...field('role')}>
                {INVITABLE_ROLES.map((role) => (
                  <MenuItem key={role} value={role}>
                    {ROLE_LABELS[role]}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Personal message"
                placeholder="Optional — shown in the invitation email"
                multiline
                rows={3}
                {...field('message')}
              />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setDialogOpen(false)} color="inherit">
              Cancel
            </Button>
            <Button type="submit" variant="contained" disabled={sendInvitation.isPending}>
              {sendInvitation.isPending ? 'Sending…' : 'Send invitation'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}
