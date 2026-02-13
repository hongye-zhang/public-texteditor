// Export components
export { default as GoogleAuthButton } from './components/GoogleAuthButton.svelte';
export { default as AuthStatusManager } from './components/AuthStatusManager.svelte';
export { default as GoogleSignInButton } from './components/GoogleSignInButton.svelte';

// Export stores
export {
  googleAuthStore,
  isAuthenticated,
  user,
  isInitialized,
  authError
} from './stores/googleAuthStore';

// Export utilities
export {
  decodeToken,
  storeToken,
  getToken,
  removeToken,
  getUserInfoFromToken,
  isTokenValid
} from './utils/tokenUtils';
