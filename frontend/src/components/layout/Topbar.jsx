import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import SettingsBrightnessOutlinedIcon from '@mui/icons-material/SettingsBrightnessOutlined';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import LogoutIcon from '@mui/icons-material/Logout';
import CheckIcon from '@mui/icons-material/Check';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';

import useAuth from '@/hooks/useAuth';
import UserAvatar from '@/components/ui/UserAvatar';
import GlobalSearch from './GlobalSearch';
import {
  selectThemeMode,
  setMobileSidebar,
  setThemeMode,
  toggleSidebar,
} from '@/features/uiSlice';
import { switchOrganization } from '@/features/authSlice';
import { ROLE_LABELS } from '@/utils/constants';

const THEME_OPTIONS = [
  { value: 'light', label: 'Light', icon: LightModeOutlinedIcon },
  { value: 'dark', label: 'Dark', icon: DarkModeOutlinedIcon },
  { value: 'system', label: 'System', icon: SettingsBrightnessOutlinedIcon },
];

export default function Topbar() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user, role, organization, organizations, logout } = useAuth();
  const themeMode = useSelector(selectThemeMode);

  const [userMenu, setUserMenu] = useState(null);
  const [themeMenu, setThemeMenu] = useState(null);
  const [orgMenu, setOrgMenu] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);

  const handleLogout = async () => {
    setUserMenu(null);
    await logout();
    navigate('/login', { replace: true });
  };

  const handleSwitchOrganization = (id) => {
    setOrgMenu(null);
    if (id !== organization?.id) dispatch(switchOrganization(id));
  };

  const ActiveThemeIcon =
    THEME_OPTIONS.find((option) => option.value === themeMode)?.icon ??
    SettingsBrightnessOutlinedIcon;

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        color="inherit"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Toolbar sx={{ gap: 1 }}>
          <IconButton
            edge="start"
            onClick={() => dispatch(setMobileSidebar(true))}
            sx={{ display: { lg: 'none' } }}
            aria-label="Open navigation"
          >
            <MenuIcon />
          </IconButton>
          <IconButton
            edge="start"
            onClick={() => dispatch(toggleSidebar())}
            sx={{ display: { xs: 'none', lg: 'inline-flex' } }}
            aria-label="Toggle navigation"
          >
            <MenuIcon />
          </IconButton>

          {organizations.length > 1 ? (
            <Tooltip title="Switch workspace">
              <Box
                onClick={(event) => setOrgMenu(event.currentTarget)}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  px: 1,
                  py: 0.5,
                  borderRadius: 1.5,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <Typography variant="body2" fontWeight={600} noWrap>
                  {organization?.name || 'No workspace'}
                </Typography>
                <SwapHorizIcon fontSize="small" color="action" />
              </Box>
            </Tooltip>
          ) : (
            <Typography variant="body2" fontWeight={600} noWrap sx={{ px: 1 }}>
              {organization?.name || ''}
            </Typography>
          )}

          <Box sx={{ flex: 1 }} />

          <Tooltip title="Search (⌘K)">
            <IconButton onClick={() => setSearchOpen(true)} aria-label="Search">
              <SearchIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Appearance">
            <IconButton onClick={(event) => setThemeMenu(event.currentTarget)} aria-label="Theme">
              <ActiveThemeIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Account">
            <IconButton onClick={(event) => setUserMenu(event.currentTarget)} sx={{ ml: 0.5 }}>
              <UserAvatar user={user} size={32} />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Workspace switcher */}
      <Menu anchorEl={orgMenu} open={Boolean(orgMenu)} onClose={() => setOrgMenu(null)}>
        {organizations.map((org) => (
          <MenuItem
            key={org.id}
            selected={org.id === organization?.id}
            onClick={() => handleSwitchOrganization(org.id)}
          >
            <ListItemIcon>
              {org.id === organization?.id ? <CheckIcon fontSize="small" /> : null}
            </ListItemIcon>
            <ListItemText primary={org.name} secondary={ROLE_LABELS[org.role] || org.role} />
          </MenuItem>
        ))}
      </Menu>

      {/* Theme picker */}
      <Menu anchorEl={themeMenu} open={Boolean(themeMenu)} onClose={() => setThemeMenu(null)}>
        {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
          <MenuItem
            key={value}
            selected={value === themeMode}
            onClick={() => {
              dispatch(setThemeMode(value));
              setThemeMenu(null);
            }}
          >
            <ListItemIcon>
              <Icon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary={label} />
          </MenuItem>
        ))}
      </Menu>

      {/* Account menu */}
      <Menu
        anchorEl={userMenu}
        open={Boolean(userMenu)}
        onClose={() => setUserMenu(null)}
        slotProps={{ paper: { sx: { minWidth: 230 } } }}
      >
        <Box sx={{ px: 2, py: 1.25 }}>
          <Typography variant="body2" fontWeight={600} noWrap>
            {user?.full_name || user?.email}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap component="div">
            {user?.email}
          </Typography>
          {role && (
            <Typography variant="caption" color="primary.main" fontWeight={600}>
              {ROLE_LABELS[role] || role}
            </Typography>
          )}
        </Box>
        <Divider />
        <MenuItem
          onClick={() => {
            setUserMenu(null);
            navigate('/profile');
          }}
        >
          <ListItemIcon>
            <PersonOutlineIcon fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        <MenuItem
          onClick={() => {
            setUserMenu(null);
            navigate('/settings');
          }}
        >
          <ListItemIcon>
            <SettingsOutlinedIcon fontSize="small" />
          </ListItemIcon>
          Settings
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Sign out
        </MenuItem>
      </Menu>

      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
