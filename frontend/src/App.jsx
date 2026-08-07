import { lazy, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { Navigate, Route, Routes } from 'react-router-dom';

import { getAccessToken } from '@/api/tokenStorage';
import { loadCurrentUser } from '@/features/authSlice';
import AppLayout from '@/components/layout/AppLayout';
import AuthLayout from '@/components/layout/AuthLayout';
import ProtectedRoute, { PublicOnlyRoute } from '@/components/layout/ProtectedRoute';
import { ROLES } from '@/utils/constants';

// Auth pages load eagerly: they are the first thing an anonymous visitor sees.
import Login from '@/pages/auth/Login';
import Register from '@/pages/auth/Register';
import ForgotPassword from '@/pages/auth/ForgotPassword';
import ResetPassword from '@/pages/auth/ResetPassword';
import VerifyEmail from '@/pages/auth/VerifyEmail';
import AcceptInvitation from '@/pages/auth/AcceptInvitation';

// Everything behind the login wall is code-split.
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Members = lazy(() => import('@/pages/Members'));
const Teams = lazy(() => import('@/pages/Teams'));
const Departments = lazy(() => import('@/pages/Departments'));
const Invitations = lazy(() => import('@/pages/Invitations'));
const Activity = lazy(() => import('@/pages/Activity'));
const AuditLog = lazy(() => import('@/pages/AuditLog'));
const Profile = lazy(() => import('@/pages/Profile'));
const Settings = lazy(() => import('@/pages/settings/Settings'));
const NotFound = lazy(() => import('@/pages/NotFound'));
const Forbidden = lazy(() => import('@/pages/Forbidden'));

export default function App() {
  const dispatch = useDispatch();

  // A stored token is only a claim; verify it against /auth/me/ on boot.
  useEffect(() => {
    if (getAccessToken()) dispatch(loadCurrentUser());
  }, [dispatch]);

  return (
    <Routes>
      {/* Public: reachable whether or not you are signed in */}
      <Route element={<AuthLayout />}>
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/accept-invitation" element={<AcceptInvitation />} />
      </Route>

      {/* Public only: bounce signed-in users to the dashboard */}
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
        </Route>
      </Route>

      {/* Authenticated */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/members" element={<Members />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/departments" element={<Departments />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/403" element={<Forbidden />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>

      {/* Authenticated, manager and above */}
      <Route element={<ProtectedRoute requiredRole={ROLES.MANAGER} />}>
        <Route element={<AppLayout />}>
          <Route path="/invitations" element={<Invitations />} />
        </Route>
      </Route>

      {/* Authenticated, admin and above */}
      <Route element={<ProtectedRoute requiredRole={ROLES.ADMIN} />}>
        <Route element={<AppLayout />}>
          <Route path="/audit-log" element={<AuditLog />} />
        </Route>
      </Route>
    </Routes>
  );
}
