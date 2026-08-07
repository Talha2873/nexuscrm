import { describe, expect, it } from 'vitest';

import { formatBytes, formatCurrency, initialsOf } from '@/utils/format';
import { canWrite, hasRoleAtLeast, isAdmin } from '@/utils/permissions';
import { getErrorMessage } from '@/utils/errors';
import { ROLES } from '@/utils/constants';

describe('format helpers', () => {
  it('derives initials from a full name', () => {
    expect(initialsOf({ full_name: 'Ada Lovelace' })).toBe('AL');
  });

  it('falls back to the email when no name is present', () => {
    expect(initialsOf({ email: 'casey@example.com' })).toBe('CA');
  });

  it('returns a placeholder for empty input', () => {
    expect(initialsOf(null)).toBe('?');
  });

  it('formats byte sizes into readable units', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
  });

  it('renders currency amounts', () => {
    expect(formatCurrency(1500, 'USD')).toContain('1,500');
  });

  it('returns a dash for unparseable values', () => {
    expect(formatCurrency('not-a-number')).toBe('—');
  });
});

describe('permission helpers', () => {
  it('respects the role hierarchy', () => {
    expect(hasRoleAtLeast(ROLES.ADMIN, ROLES.MANAGER)).toBe(true);
    expect(hasRoleAtLeast(ROLES.MEMBER, ROLES.ADMIN)).toBe(false);
  });

  it('treats owners as admins', () => {
    expect(isAdmin(ROLES.OWNER)).toBe(true);
  });

  it('blocks writes for viewers', () => {
    expect(canWrite(ROLES.VIEWER)).toBe(false);
    expect(canWrite(ROLES.MEMBER)).toBe(true);
  });
});

describe('error helpers', () => {
  it('reads the message out of the API error envelope', () => {
    const error = {
      data: { error: { code: 'invalid_credentials', message: 'Incorrect email or password.' } },
    };
    expect(getErrorMessage(error)).toBe('Incorrect email or password.');
  });

  it('falls back to the first field error', () => {
    const error = { data: { error: { details: { email: ['Enter a valid email address.'] } } } };
    expect(getErrorMessage(error)).toBe('Enter a valid email address.');
  });

  it('uses the fallback when nothing is recognisable', () => {
    expect(getErrorMessage(undefined, 'Fallback')).toBe('Fallback');
  });
});
