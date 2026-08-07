import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';

const toDate = (value) => {
  if (!value) return null;
  const date = typeof value === 'string' ? parseISO(value) : value;
  return isValid(date) ? date : null;
};

export const formatDate = (value, pattern = 'd MMM yyyy') => {
  const date = toDate(value);
  return date ? format(date, pattern) : '—';
};

export const formatDateTime = (value) => formatDate(value, 'd MMM yyyy, HH:mm');

export const formatRelative = (value) => {
  const date = toDate(value);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : '—';
};

export const formatCurrency = (amount, currency = 'USD') => {
  const value = Number(amount);
  if (Number.isNaN(value)) return '—';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value);
};

export const formatNumber = (value) => {
  const number = Number(value);
  return Number.isNaN(number) ? '—' : new Intl.NumberFormat().format(number);
};

export const formatBytes = (bytes) => {
  const value = Number(bytes);
  if (Number.isNaN(value) || value === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

export const initialsOf = (nameOrUser) => {
  if (!nameOrUser) return '?';
  const name =
    typeof nameOrUser === 'string'
      ? nameOrUser
      : nameOrUser.full_name ||
        `${nameOrUser.first_name || ''} ${nameOrUser.last_name || ''}`.trim() ||
        nameOrUser.email ||
        '';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};
