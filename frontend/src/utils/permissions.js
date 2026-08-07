import { ROLE_RANK, ROLES } from './constants';

export const rankOf = (role) => ROLE_RANK[role] ?? 0;

export const hasRoleAtLeast = (role, required) => rankOf(role) >= rankOf(required);

export const isOwner = (role) => role === ROLES.OWNER;
export const isAdmin = (role) => hasRoleAtLeast(role, ROLES.ADMIN);
export const isManager = (role) => hasRoleAtLeast(role, ROLES.MANAGER);
export const canWrite = (role) => Boolean(role) && role !== ROLES.VIEWER;
