// Admin authentication utilities for frontend

/**
 * Get admin token from localStorage
 * Set this in browser console: localStorage.setItem('hive-admin-token', 'your-admin-token-here')
 */
export function getAdminToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('hive-admin-token');
}

/**
 * Create headers object with admin token if available
 */
export function createAdminHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
  const headers = { ...additionalHeaders };

  const adminToken = getAdminToken();
  if (adminToken) {
    headers['x-admin-token'] = adminToken;
    console.log('[Admin] Using admin token from localStorage');
  }

  return headers;
}

/**
 * Check if admin token is configured
 */
export function isAdminModeEnabled(): boolean {
  return getAdminToken() !== null;
}

/**
 * Instructions for setting up admin access
 */
export function getAdminInstructions(): string {
  return `To enable admin access, set the admin token in browser localStorage:
localStorage.setItem('hive-admin-token', 'hive-admin-2024-secure-token-change-me')

Then refresh the page to see all strategies without authentication.`;
}
