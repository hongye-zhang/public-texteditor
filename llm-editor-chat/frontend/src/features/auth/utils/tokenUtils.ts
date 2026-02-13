/**
 * Utility functions for secure token handling
 */

// Token storage key
const TOKEN_STORAGE_KEY = 'gapi-token';

// Expiration buffer (in seconds) - refresh token if it expires within this time
const TOKEN_EXPIRATION_BUFFER = 300; // 5 minutes

// Interface for decoded token payload
interface TokenPayload {
  sub: string;
  name: string;
  email: string;
  picture: string;
  exp?: number;
  iat?: number;
}

/**
 * Store token securely
 */
export const storeToken = (token: string): void => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
};

/**
 * Retrieve stored token
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
};

/**
 * Remove stored token
 */
export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};

/**
 * Safely decode a JWT token
 * This handles both standard JWT tokens and OAuth access tokens
 */
export const decodeToken = (token: string): TokenPayload | null => {
  try {
    // Check if this is a JWT token (should have 3 parts separated by dots)
    if (token.split('.').length === 3) {
      // Get the payload part (second part) of the JWT
      const base64Url = token.split('.')[1];
      // Convert base64url to base64
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      // Decode the base64 string
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      // Parse the JSON payload
      return JSON.parse(jsonPayload);
    } else {
      // This might be an OAuth access token, not a JWT
      // We can't decode it client-side, so we'll create a minimal payload
      console.warn('Token is not in JWT format, using minimal payload');
      return {
        sub: 'oauth-user',
        name: 'OAuth User',
        email: 'oauth@example.com',
        picture: ''
      };
    }
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
};

/**
 * Validate token and check if it's expired
 */
export const isTokenValid = (token: string | null): boolean => {
  if (!token) return false;
  
  try {
    const payload = decodeToken(token);
    if (!payload) return false;
    
    // Check if token is expired (if it has an expiration time)
    if (payload.exp) {
      const currentTime = Math.floor(Date.now() / 1000);
      if (payload.exp < currentTime) {
        console.log('Token has expired');
        return false;
      }
    }
    
    return true;
  } catch (error) {
    console.error('Error validating token:', error);
    return false;
  }
};

/**
 * Check if token needs refreshing (will expire soon)
 */
export const tokenNeedsRefresh = (token: string | null): boolean => {
  if (!token) return true;
  
  try {
    const payload = decodeToken(token);
    if (!payload) return true;
    
    // If token has an expiration time, check if it will expire soon
    if (payload.exp) {
      const currentTime = Math.floor(Date.now() / 1000);
      const timeUntilExpiration = payload.exp - currentTime;
      
      // If token will expire within the buffer time, it needs refreshing
      if (timeUntilExpiration < TOKEN_EXPIRATION_BUFFER) {
        console.log(`Token will expire soon (${timeUntilExpiration}s), needs refresh`);
        return true;
      }
    }
    
    return false;
  } catch (error) {
    console.error('Error checking token refresh status:', error);
    return true; // If there's an error, better to refresh
  }
};

/**
 * Get user info from token
 */
export const getUserInfoFromToken = (token: string): { 
  id: string; 
  name: string; 
  email: string; 
  imageUrl: string;
} | null => {
  try {
    const payload = decodeToken(token);
    if (!payload) return null;
    
    return {
      id: payload.sub,
      name: payload.name,
      email: payload.email,
      imageUrl: payload.picture
    };
  } catch (error) {
    console.error('Error getting user info from token:', error);
    return null;
  }
};