import { NavLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import ListSubheader from '@mui/material/ListSubheader';
import Typography from '@mui/material/Typography';

import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined';
import BusinessOutlinedIcon from '@mui/icons-material/BusinessOutlined';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';

import useAuth from '@/hooks/useAuth';
import { APP_NAME } from '@/utils/constants';

export const SIDEBAR_WIDTH = 256;

const NAV_SECTIONS = [
  {
    heading: null,
    items: [{ label: 'Dashboard', to: '/dashboard', icon: DashboardOutlinedIcon }],
  },
  {
    heading: 'Workspace',
    items: [
      { label: 'Members', to: '/members', icon: GroupsOutlinedIcon },
      { label: 'Teams', to: '/teams', icon: AccountTreeOutlinedIcon },
      { label: 'Departments', to: '/departments', icon: BusinessOutlinedIcon },
      { label: 'Invitations', to: '/invitations', icon: MailOutlineIcon, minRole: 'manager' },
    ],
  },
  {
    heading: 'Insights',
    items: [
      { label: 'Activity', to: '/activity', icon: HistoryOutlinedIcon },
      { label: 'Audit log', to: '/audit-log', icon: ShieldOutlinedIcon, minRole: 'admin' },
    ],
  },
  {
    heading: 'Account',
    items: [
      { label: 'Profile', to: '/profile', icon: PersonOutlineIcon },
      { label: 'Settings', to: '/settings', icon: SettingsOutlinedIcon },
    ],
  },
];

function SidebarContent({ onNavigate }) {
  const { isAdmin, isManager, organization } = useAuth();

  const isVisible = (item) => {
    if (item.minRole === 'admin') return isAdmin;
    if (item.minRole === 'manager') return isManager;
    return true;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 2.5, py: 2.25, display: 'flex', alignItems: 'center', gap: 1.25 }}>
        <Box
          sx={{
            width: 30,
            height: 30,
            borderRadius: 1.5,
            bgcolor: 'primary.main',
            color: '#fff',
            display: 'grid',
            placeItems: 'center',
            fontWeight: 700,
            fontSize: 15,
          }}
        >
          N
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" noWrap sx={{ lineHeight: 1.2 }}>
            {APP_NAME}
          </Typography>
          {organization?.name && (
            <Typography variant="caption" color="text.secondary" noWrap component="div">
              {organization.name}
            </Typography>
          )}
        </Box>
      </Box>

      <Divider />

      <Box sx={{ flex: 1, overflowY: 'auto', py: 1 }}>
        {NAV_SECTIONS.map((section, index) => {
          const items = section.items.filter(isVisible);
          if (items.length === 0) return null;

          return (
            <List
              key={section.heading || `section-${index}`}
              dense
              subheader={
                section.heading ? (
                  <ListSubheader
                    disableSticky
                    sx={{
                      bgcolor: 'transparent',
                      fontSize: 11,
                      fontWeight: 700,
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                      color: 'text.secondary',
                      lineHeight: 2.5,
                    }}
                  >
                    {section.heading}
                  </ListSubheader>
                ) : null
              }
              sx={{ px: 1.25 }}
            >
              {items.map(({ label, to, icon: Icon }) => (
                <ListItemButton
                  key={to}
                  component={NavLink}
                  to={to}
                  onClick={onNavigate}
                  sx={{
                    borderRadius: 1.5,
                    mb: 0.25,
                    '&.active': {
                      bgcolor: 'action.selected',
                      color: 'primary.main',
                      '& .MuiListItemIcon-root': { color: 'primary.main' },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <Icon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{ fontSize: 14, fontWeight: 500 }}
                  />
                </ListItemButton>
              ))}
            </List>
          );
        })}
      </Box>
    </Box>
  );
}

export default function Sidebar({ open, mobileOpen, onMobileClose }) {
  return (
    <>
      {/* Mobile: temporary overlay drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', lg: 'none' },
          '& .MuiDrawer-paper': { width: SIDEBAR_WIDTH, boxSizing: 'border-box' },
        }}
      >
        <SidebarContent onNavigate={onMobileClose} />
      </Drawer>

      {/* Desktop: persistent drawer */}
      <Drawer
        variant="persistent"
        open={open}
        sx={{
          display: { xs: 'none', lg: 'block' },
          width: open ? SIDEBAR_WIDTH : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: SIDEBAR_WIDTH,
            boxSizing: 'border-box',
            borderRight: 1,
            borderColor: 'divider',
          },
        }}
      >
        <SidebarContent />
      </Drawer>
    </>
  );
}
