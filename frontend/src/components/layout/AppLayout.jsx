import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';

import Sidebar, { SIDEBAR_WIDTH } from './Sidebar';
import Topbar from './Topbar';
import LoadingScreen from '@/components/ui/LoadingScreen';
import { setMobileSidebar } from '@/features/uiSlice';

export default function AppLayout() {
  const dispatch = useDispatch();
  const { sidebarOpen, mobileSidebarOpen } = useSelector((state) => state.ui);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Sidebar
        open={sidebarOpen}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => dispatch(setMobileSidebar(false))}
      />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          // Shift content when the persistent drawer is open on desktop.
          ml: { lg: sidebarOpen ? 0 : `-${SIDEBAR_WIDTH}px` },
          transition: (theme) =>
            theme.transitions.create('margin', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
        }}
      >
        <Topbar />
        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Suspense fallback={<LoadingScreen fullHeight={false} />}>
            <Outlet />
          </Suspense>
        </Container>
      </Box>
    </Box>
  );
}
