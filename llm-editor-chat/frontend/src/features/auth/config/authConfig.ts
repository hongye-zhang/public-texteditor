/**
 * Authentication configuration settings
 * Controls behavior of authentication features
 */

// Set to true to enable automatic login on app start, false to always start logged out
export const AUTO_LOGIN_ENABLED = true;

// Function to check if auto-login is enabled
export function isAutoLoginEnabled(): boolean {
  return AUTO_LOGIN_ENABLED;
}
