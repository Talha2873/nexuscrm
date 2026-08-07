import Avatar from '@mui/material/Avatar';

import { initialsOf } from '@/utils/format';

/** Deterministic colour so the same person always gets the same swatch. */
const PALETTE = ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#dc2626', '#db2777'];

const colorFor = (seed = '') => {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
};

export default function UserAvatar({ user, size = 36, ...props }) {
  const seed = user?.email || user?.full_name || '';
  return (
    <Avatar
      src={user?.avatar_url || undefined}
      alt={user?.full_name || user?.email || 'User'}
      sx={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        fontWeight: 600,
        bgcolor: colorFor(seed),
      }}
      {...props}
    >
      {initialsOf(user)}
    </Avatar>
  );
}
