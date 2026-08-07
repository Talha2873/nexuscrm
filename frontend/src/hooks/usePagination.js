import { useCallback, useState } from 'react';

import { DEFAULT_PAGE_SIZE } from '@/utils/constants';

/**
 * Table state (page, size, ordering, search) in a shape that can be spread
 * straight into an API call's `params`.
 */
export default function usePagination({
  initialPageSize = DEFAULT_PAGE_SIZE,
  initialOrdering = '-created_at',
} = {}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [ordering, setOrdering] = useState(initialOrdering);
  const [search, setSearch] = useState('');

  const changePageSize = useCallback((size) => {
    setPageSize(size);
    setPage(1);
  }, []);

  const changeSearch = useCallback((term) => {
    setSearch(term);
    setPage(1);
  }, []);

  const changeOrdering = useCallback((field) => {
    setOrdering((current) => (current === field ? `-${field}` : field));
    setPage(1);
  }, []);

  return {
    page,
    pageSize,
    ordering,
    search,
    setPage,
    setPageSize: changePageSize,
    setSearch: changeSearch,
    setOrdering: changeOrdering,
    params: {
      page,
      page_size: pageSize,
      ordering,
      ...(search ? { search } : {}),
    },
  };
}
