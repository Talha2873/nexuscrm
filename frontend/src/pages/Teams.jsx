import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import AvatarGroup from '@mui/material/AvatarGroup';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import toast from 'react-hot-toast';

import { departmentApi, teamApi } from '@/api/endpoints';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import DataTable from '@/components/ui/DataTable';
import PageHeader from '@/components/ui/PageHeader';
import UserAvatar from '@/components/ui/UserAvatar';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import usePagination from '@/hooks/usePagination';
import { getErrorMessage } from '@/utils/errors';

export default function Teams() {
  useDocumentTitle('Teams');
  const queryClient = useQueryClient();
  const { isManager } = useAuth();
  const pagination = usePagination({ initialOrdering: 'name' });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const {
    register: field,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: { name: '', description: '', department: '', color: '#2563eb' } });

  const { data, isLoading } = useQuery({
    queryKey: ['teams', pagination.params],
    queryFn: async () => {
      const { data: payload } = await teamApi.list(pagination.params);
      return payload;
    },
    keepPreviousData: true,
  });

  const { data: departments } = useQuery({
    queryKey: ['departments', 'all'],
    queryFn: async () => {
      const { data: payload } = await departmentApi.list({ page_size: 100 });
      return payload.results ?? [];
    },
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['teams'] });

  const createTeam = useMutation({
    mutationFn: (payload) => teamApi.create(payload),
    onSuccess: () => {
      toast.success('Team created');
      setDialogOpen(false);
      reset();
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const deleteTeam = useMutation({
    mutationFn: (id) => teamApi.remove(id),
    onSuccess: () => {
      toast.success('Team deleted');
      setDeleteTarget(null);
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values) => {
    createTeam.mutate({
      name: values.name,
      description: values.description || '',
      color: values.color,
      ...(values.department ? { department: values.department } : {}),
    });
  };

  const columns = [
    {
      id: 'name',
      label: 'Team',
      sortable: true,
      render: (row) => (
        <Stack direction="row" spacing={1.25} alignItems="center">
          <Box
            sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: row.color, flexShrink: 0 }}
          />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" fontWeight={600} noWrap>
              {row.name}
            </Typography>
            {row.description && (
              <Typography variant="caption" color="text.secondary" noWrap component="div">
                {row.description}
              </Typography>
            )}
          </Box>
        </Stack>
      ),
    },
    {
      id: 'department_name',
      label: 'Department',
      render: (row) =>
        row.department_name ? (
          <Chip size="small" label={row.department_name} variant="outlined" />
        ) : (
          '—'
        ),
    },
    {
      id: 'lead',
      label: 'Lead',
      render: (row) =>
        row.lead ? (
          <Stack direction="row" spacing={1} alignItems="center">
            <UserAvatar user={row.lead} size={26} />
            <Typography variant="body2" noWrap>
              {row.lead.full_name}
            </Typography>
          </Stack>
        ) : (
          '—'
        ),
    },
    {
      id: 'team_members',
      label: 'Members',
      render: (row) =>
        row.team_members?.length ? (
          <AvatarGroup max={5} sx={{ justifyContent: 'flex-start' }}>
            {row.team_members.map((membership) => (
              <UserAvatar key={membership.id} user={membership.user} size={26} />
            ))}
          </AvatarGroup>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No members
          </Typography>
        ),
    },
    {
      id: 'actions',
      label: '',
      align: 'right',
      width: 56,
      render: (row) =>
        isManager && (
          <IconButton
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              setDeleteTarget(row);
            }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        ),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Teams"
        description="Group people so work can be assigned and reported on together."
        action={
          isManager && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
              New team
            </Button>
          )
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
        emptyTitle="No teams yet"
        emptyDescription="Create your first team to start organising people around your work."
        emptyAction={isManager ? { label: 'New team', onClick: () => setDialogOpen(true) } : null}
      />

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="xs">
        <Box component="form" onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>Create a team</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Team name"
                autoFocus
                error={Boolean(errors.name)}
                helperText={errors.name?.message}
                {...field('name', { required: 'Team name is required' })}
              />
              <TextField label="Description" multiline rows={2} {...field('description')} />
              <TextField label="Department" select defaultValue="" {...field('department')}>
                <MenuItem value="">No department</MenuItem>
                {(departments ?? []).map((department) => (
                  <MenuItem key={department.id} value={department.id}>
                    {department.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField label="Colour" type="color" {...field('color')} />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setDialogOpen(false)} color="inherit">
              Cancel
            </Button>
            <Button type="submit" variant="contained" disabled={createTeam.isPending}>
              {createTeam.isPending ? 'Creating…' : 'Create team'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete this team?"
        message={`“${deleteTarget?.name}” will be removed. Members keep their workspace access.`}
        confirmLabel="Delete team"
        destructive
        loading={deleteTeam.isPending}
        onConfirm={() => deleteTeam.mutate(deleteTarget.id)}
        onClose={() => setDeleteTarget(null)}
      />
    </Box>
  );
}
