import { useDispatch, useSelector } from 'react-redux';

import { logout as logoutThunk, selectAuth } from '@/features/authSlice';
import { canWrite, isAdmin, isManager, isOwner } from '@/utils/permissions';

/** One hook for everything a component needs to know about the session. */
export default function useAuth() {
  const dispatch = useDispatch();
  const auth = useSelector(selectAuth);

  return {
    ...auth,
    isLoading: auth.status === 'loading',
    isOwner: isOwner(auth.role),
    isAdmin: isAdmin(auth.role),
    isManager: isManager(auth.role),
    canWrite: canWrite(auth.role),
    logout: () => dispatch(logoutThunk()),
  };
}
