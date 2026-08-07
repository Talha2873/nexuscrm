import { Navigate, Outlet, useLocation } from 'react-router-dom';

import useAuth from '@/hooks/useAuth';
import LoadingScreen from '@/components/ui/LoadingScreen';
import { hasRoleAtLeast } from '@/utils/permissions';

/**
 * Gate for authenticated routes.
 *
 * `requiredRole` additionally enforces the role hierarchy, mirroring
 * `HasRoleAtLeast` on the backend so the UI never offers an action the API
 * would reject.
 */
export default function ProtectedRoute({ requiredRole }) {
  const { isAuthenticated, status, role } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <LoadingScreen message="Restoring your session…" />;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !hasRoleAtLeast(role, requiredRole)) {
    return <Navigate to="/403" replace />;
  }

  return <Outlet />;
}

/** Inverse gate: keeps signed-in users away from /login and /register. */
export function PublicOnlyRoute() {
  const { isAuthenticated, status } = useAuth();

  if (status === 'loading') return <LoadingScreen message="Loading…" />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
