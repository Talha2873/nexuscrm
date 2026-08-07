import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';

import EmptyState from './EmptyState';

/**
 * Presentational table. The parent owns all state (page, ordering, data) so the
 * same component works with server-side pagination from any endpoint.
 *
 * columns: [{ id, label, sortable, align, width, render(row) }]
 */
export default function DataTable({
  columns,
  rows = [],
  loading = false,
  count = 0,
  page = 1,
  pageSize = 25,
  ordering = '',
  onPageChange,
  onPageSizeChange,
  onSort,
  onRowClick,
  emptyTitle = 'No records found',
  emptyDescription,
  emptyAction,
}) {
  const sortField = ordering.replace(/^-/, '');
  const sortDirection = ordering.startsWith('-') ? 'desc' : 'asc';

  if (!loading && rows.length === 0) {
    return (
      <Paper variant="outlined">
        <EmptyState
          title={emptyTitle}
          description={emptyDescription}
          actionLabel={emptyAction?.label}
          onAction={emptyAction?.onClick}
        />
      </Paper>
    );
  }

  return (
    <Paper variant="outlined">
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align || 'left'}
                  sx={{ width: column.width }}
                >
                  {column.sortable && onSort ? (
                    <TableSortLabel
                      active={sortField === column.id}
                      direction={sortField === column.id ? sortDirection : 'asc'}
                      onClick={() => onSort(column.id)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {loading
              ? Array.from({ length: 5 }).map((_, rowIndex) => (
                  <TableRow key={`skeleton-${rowIndex}`}>
                    {columns.map((column) => (
                      <TableCell key={column.id}>
                        <Skeleton height={24} />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : rows.map((row) => (
                  <TableRow
                    key={row.id}
                    hover={Boolean(onRowClick)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    sx={{ cursor: onRowClick ? 'pointer' : 'default' }}
                  >
                    {columns.map((column) => (
                      <TableCell key={column.id} align={column.align || 'left'}>
                        {column.render ? column.render(row) : (row[column.id] ?? '—')}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </TableContainer>

      {onPageChange && (
        <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
          <TablePagination
            component="div"
            count={count}
            page={Math.max(page - 1, 0)}
            rowsPerPage={pageSize}
            rowsPerPageOptions={[10, 25, 50, 100]}
            onPageChange={(_event, nextPage) => onPageChange(nextPage + 1)}
            onRowsPerPageChange={(event) => onPageSizeChange?.(Number(event.target.value))}
          />
        </Box>
      )}
    </Paper>
  );
}
