import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
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

import { departmentApi } from '@/api/endpoints';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import DataTable from '@/components/ui/DataTable';
import PageHeader from '@/components/ui/PageHeader';
import useAuth from '@/hooks/useAuth';
import useDocumentTitle from '@/hooks/useDocumentTitle';
import usePagination from '@/hooks/usePagination';
import { getErrorMessage } from '@/utils/errors';

export default function Departments() {
  useDocumentTitle('Departments');
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
  } = useForm({ defaultValues: { name: '', code: '', description: '', parent: '', color: '#64748b' } });

  const { data, isLoading } = useQuery({
    queryKey: ['departments', pagination.params],
    queryFn: async () => {
      const { data: payload } = await departmentApi.list(pagination.params);
      return payload;
    },
    keepPreviousData: true,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['departments'] });

  const createDepartment = useMutation({
    mutationFn: (payload) => departmentApi.create(payload),
    onSuccess: () => {
      toast.success('Department created');
      setDialogOpen(false);
      reset();
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const deleteDepartment = useMutation({
    mutationFn: (id) => departmentApi.remove(id),
    onSuccess: () => {
      toast.success('Department deleted');
      setDeleteTarget(null);
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values) =>
    createDepartment.mutate({
      name: values.name,
      code: values.code || '',
      description: values.description || '',
      color: values.color,
      ...(values.parent ? { parent: values.parent } : {}),
    });

  const columns = [
    {
      id: 'name',
      label: 'Department',
      sortable: true,
      render: (row) => (
        <Stack direction="row" spacing={1.25} alignItems="center">
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: row.color }} />
          <Box>
            <Typography variant="body2" fontWeight={600}>
              {row.name}
            </Typography>
            {row.description && (
              <Typography variant="caption" color="text.secondary" component="div">
                {row.description}
              </Typography>
            )}
          </Box>
        </Stack>
      ),
    },
    { id: 'code', label: 'Code', render: (row) => row.code || '—' },
    { id: 'parent_name', label: 'Parent', render: (row) => row.parent_name || '—' },
    { id: 'member_count', label: 'Members', align: 'right' },
    {
      id: 'actions',
      label: '',
      align: 'right',
      width: 56,
      render: (row) =>
        isManager && (
          <IconButton size="small" onClick={() => setDeleteTarget(row)}>
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        ),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Departments"
        description="The organisational structure your teams and members roll up into."
        action={
          isManager && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
              New department
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
        emptyTitle="No departments yet"
        emptyDescription="Departments let you group teams and report on the business by function."
        emptyAction={
          isManager ? { label: 'New department', onClick: () => setDialogOpen(true) } : null
        }
      />

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="xs">
        <Box component="form" onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>Create a department</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Name"
                autoFocus
                error={Boolean(errors.name)}
                helperText={errors.name?.message}
                {...field('name', { required: 'Name is required' })}
              />
              <TextField label="Code" placeholder="SALES" {...field('code')} />
              <TextField label="Description" multiline rows={2} {...field('description')} />
              <TextField label="Parent department" select defaultValue="" {...field('parent')}>
                <MenuItem value="">Top level</MenuItem>
                {(data?.results ?? []).map((department) => (
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
            <Button type="submit" variant="contained" disabled={createDepartment.isPending}>
              {createDepartment.isPending ? 'Creating…' : 'Create'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete this department?"
        message={`“${deleteTarget?.name}” will be removed. Teams and members are not deleted.`}
        confirmLabel="Delete"
        destructive
        loading={deleteDepartment.isPending}
        onConfirm={() => deleteDepartment.mutate(deleteTarget.id)}
        onClose={() => setDeleteTarget(null)}
      />
    </Box>
  );
}
