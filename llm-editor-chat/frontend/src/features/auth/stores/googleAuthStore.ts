// Import necessary modules
import { writable, derived } from 'svelte/store';
import type { Writable } from 'svelte/store';

// Import token utilities
import { decodeToken, storeToken as saveToken, getToken, removeToken, getUserInfoFromToken, isTokenValid, tokenNeedsRefresh } from '../utils/tokenUtils';

// Import auth configuration
import { AUTO_LOGIN_ENABLED } from '../config/authConfig';

// Define types
export interface GoogleUser {
  id: string;
  name: string;
  email: string;
  imageUrl: string;
}

export interface GoogleAuthState {
  isAuthenticated: boolean;
  user: GoogleUser | null;
  isInitialized: boolean;
  isInitializing: boolean;
  error: string | null;
}

export interface GoogleAuthStore {
  subscribe: (run: (value: GoogleAuthState) => void, invalidate?: (value?: GoogleAuthState) => void) => () => void;
  initialize: () => Promise<boolean>;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
  refreshToken: () => Promise<string | null>;
  renderButton: (elementId: string) => void;
  handleAuthError: (error: any) => Promise<boolean>;
}

interface GoogleCredentialResponse {
  credential: string;
}

// Environment variables
const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';
const ALLOWED_ORIGINS = (import.meta.env.VITE_ALLOWED_ORIGINS || 'http://localhost:5173,http://localhost:5174').split(',');
const GOOGLE_API_KEY = import.meta.env.VITE_GOOGLE_API_KEY || '';
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
const GOOGLE_API_SCOPES = 'https://www.googleapis.com/auth/drive.file';

// Create the authentication store
const createGoogleAuthStore = () => {
  // Initial state
  const initialState: GoogleAuthState = {
    isAuthenticated: false,
    user: null,
    isInitialized: false,
    isInitializing: false,
    error: null
  };
  
  const { subscribe, set, update } = writable<GoogleAuthState>(initialState);

  // Track initialization state to prevent multiple initializations
  let _isInitializing = false;

  // Load the Google API client library
  const loadGoogleApiScript = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (typeof window !== 'undefined' && window.gapi) {
        // If already loaded, resolve immediately
        resolve();
        return;
      }
      
      // Create script element
      const script = document.createElement('script');
      script.src = 'https://apis.google.com/js/api.js';
      script.async = true;
      script.defer = true;
      
      // Set up callbacks
      script.onload = () => {
        // Initialize the client
        if (window.gapi) {
          window.gapi.load('client', {
            callback: async () => {
              try {
                await window.gapi.client.init({
                  apiKey: GOOGLE_API_KEY,
                  discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest']
                });
                console.log('Google API client loaded successfully');
                resolve();
              } catch (error) {
                console.error('Error initializing Google API client:', error);
                reject(error);
              }
            },
            onerror: () => {
              reject(new Error('Failed to load Google API client'));
            }
          });
        } else {
          reject(new Error('Failed to load Google API'));
        }
      };
      
      script.onerror = () => {
        reject(new Error('Failed to load Google API script'));
      };
      
      // Add to document
      document.head.appendChild(script);
    });
  };
  
  // Load the Google Identity Services script
  const loadGoogleIdentityScript = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (typeof window !== 'undefined' && window.google && window.google.accounts) {
        resolve();
        return;
      }
      
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      
      script.onload = () => {
        resolve();
      };
      
      script.onerror = () => {
        reject(new Error('Failed to load Google Identity Services'));
      };
      
      document.head.appendChild(script);
    });
  };
  
  // Load both scripts at once
  const loadGoogleScript = async (): Promise<void> => {
    await Promise.all([loadGoogleApiScript(), loadGoogleIdentityScript()]);
  };

  // Initialize the Google Auth client
  const initializeAuth = async (): Promise<boolean> => {
    if (_isInitializing) return false;
    
    _isInitializing = true;
    
    try {
      update(state => ({ ...state, isInitializing: true }));
      
      // Load both Google API and Google Identity Services
      await Promise.all([loadGoogleApiScript(), loadGoogleIdentityScript()]);
      
      // Check if we have a stored token
      const token = getToken();
      
      if (token) {
        try {
          // Always try to use the token if it exists
          console.log('Found stored token, attempting to use it');
          if (isTokenValid(token)) {
            await setupUserFromToken(token);
            console.log('Successfully authenticated with stored token');
          } else {
            console.log('Token is invalid, removing it');
            removeToken();
            update(state => ({ 
              ...state, 
              isAuthenticated: false,
              user: null
            }));
          }
        } catch (tokenError) {
          console.error('Error using stored token:', tokenError);
          // If token usage fails, remove it and set user to logged out
          removeToken();
          update(state => ({ 
            ...state, 
            isAuthenticated: false,
            user: null
          }));
        }
      } else {
        console.log('No stored token found, user starts logged out');
      }
      
      update(state => ({ 
        ...state, 
        isInitialized: true,
        isInitializing: false,
        error: null
      }));
      
      return true;
    } catch (error) {
      console.error('Error initializing auth:', error);
      update(state => ({ 
        ...state, 
        isInitialized: true,
        isInitializing: false,
        error: error instanceof Error ? error.message : 'Failed to initialize authentication'
      }));
      
      return false;
    } finally {
      _isInitializing = false;
    }
  };
  
  // Handle the credential response from Google Identity Services
  const handleCredentialResponse = async (response: GoogleCredentialResponse) => {
    try {
      if (response.credential) {
        // Store the token
        saveToken(response.credential);
        
        // Set up user info from token
        await setupUserFromToken(response.credential);
      }
    } catch (error) {
      console.error('Error handling credential response:', error);
      update(state => ({ 
        ...state, 
        error: error instanceof Error ? error.message : 'Failed to handle credential response'
      }));
    }
  };
  
  // Set up user info from token
  const setupUserFromToken = async (token: string) => {
    try {
      // Use our token utilities to get user info
      const userInfo = getUserInfoFromToken(token);
      
      if (!userInfo) {
        throw new Error('Failed to get user info from token');
      }
      
      update(state => ({
        ...state,
        isAuthenticated: true,
        user: userInfo,
        error: null
      }));
      
      // Set up the token for API requests if GAPI is available
      if (typeof window !== 'undefined' && window.gapi) {
        try {
          // Ensure client is loaded
          if (!window.gapi.client) {
            await new Promise<void>((resolve, reject) => {
              window.gapi.load('client', {
                callback: () => {
                  resolve();
                },
                onerror: () => {
                  reject(new Error('Failed to load GAPI client'));
                }
              });
            });
          }
          
          // Set token
          window.gapi.client.setToken({
            access_token: token
          });
          
          // Load the Drive API if it's not already loaded
          if (!window.gapi.client.drive) {
            await window.gapi.client.init({
              apiKey: GOOGLE_API_KEY,
              discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest']
            });
            console.log('Drive API loaded successfully');
          }
        } catch (gapiError) {
          console.error('Error setting up GAPI client:', gapiError);
          // Don't throw here, we still want to consider the user authenticated
          // even if the Drive API setup fails
        }
      }
      
      return true;
    } catch (error) {
      console.error('Error setting up user from token:', error);
      update(state => ({ 
        ...state, 
        error: error instanceof Error ? error.message : 'Failed to set up user from token'
      }));
      return false;
    }
  };

  // Sign in the user
  const signIn = async (): Promise<void> => {
    if (!window.google || !window.google.accounts) {
      await initializeAuth();
    }
    
    try {
      // Use FedCM-compatible approach for authentication
      if (typeof window !== 'undefined' && window.google && window.google.accounts && window.google.accounts.id) {
        // Initialize OAuth client for FedCM compatibility
        const client = window.google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: GOOGLE_API_SCOPES,
          callback: (tokenResponse: { access_token: string }) => {
            if (tokenResponse && tokenResponse.access_token) {
              // Store the token
              saveToken(tokenResponse.access_token);
              
              // Set up user info from token
              setupUserFromToken(tokenResponse.access_token);
            }
          },
          error_callback: (error: { message?: string }) => {
            console.error('Error during OAuth flow:', error);
            update(state => ({ 
              ...state, 
              error: 'Failed to sign in: ' + (error.message || 'Unknown error')
            }));
          }
        });
        
        // Request the token
        client.requestAccessToken();
      } else {
        console.error('Google Identity Services not available');
        throw new Error('Google Identity Services not available');
      }
    } catch (error) {
      console.error('Error signing in:', error);
      update(state => ({ 
        ...state, 
        error: error instanceof Error ? error.message : 'Failed to sign in'
      }));
      throw error;
    }
  };

  // Refresh the token if needed
  const refreshToken = async (): Promise<string | null> => {
    try {
      console.log('Attempting to refresh token');
      update(state => ({ ...state, error: null }));
      
      if (typeof window !== 'undefined' && window.google && window.google.accounts && window.google.accounts.oauth2) {
        // Create a promise that will resolve when we get a new token
        return new Promise((resolve, reject) => {
          // Using non-null assertion since we've already checked for existence
          const client = window.google!.accounts!.oauth2!.initTokenClient({
            client_id: GOOGLE_CLIENT_ID,
            scope: GOOGLE_API_SCOPES,
            callback: (tokenResponse: { access_token: string }) => {
              try {
                const token = tokenResponse.access_token;
                // Store the new token
                storeToken(token);
                // Set up the user from the new token
                setupUserFromToken(token);
                console.log('Token refreshed successfully');
                resolve(token);
              } catch (error) {
                console.error('Error processing refreshed token:', error);
                reject(error);
              }
            },
            error_callback: (error: { message?: string }) => {
              console.error('Error refreshing token:', error);
              update(state => ({ 
                ...state, 
                error: 'Failed to refresh token: ' + (error.message || 'Unknown error')
              }));
              reject(error);
            }
          });
          
          // Request a new token
          client.requestAccessToken();
        });
      } else {
        console.error('Google Identity Services not available for token refresh');
        throw new Error('Google Identity Services not available');
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
      update(state => ({ 
        ...state, 
        error: error instanceof Error ? error.message : 'Failed to refresh token'
      }));
      return null;
    }
  };
  
  // Sign out the user
  const signOut = async (): Promise<void> => {
    try {
      // Remove the token
      removeToken();
      
      // Reset the state
      update(state => ({
        ...state,
        isAuthenticated: false,
        user: null,
        error: null
      }));
      
      // Sign out of Google
      if (typeof window !== 'undefined' && window.google && window.google.accounts) {
        window.google.accounts.id.disableAutoSelect();
      }
    } catch (error) {
      console.error('Error signing out:', error);
      update(state => ({ 
        ...state, 
        error: error instanceof Error ? error.message : 'Failed to sign out'
      }));
    }
  };

  // Helper to get the auth token - use the getToken function from tokenUtils
  // This enhanced version checks if the token needs refreshing
  const getAuthToken = async (): Promise<string | null> => {
    const token = getToken();
    
    // If no token, return null
    if (!token) return null;
    
    // If token is invalid or about to expire, try to refresh it
    if (!isTokenValid(token) || tokenNeedsRefresh(token)) {
      console.log('Token needs refreshing, attempting to get a new one');
      return await refreshToken();
    }
    
    return token;
  };

  // Render the Google Sign-In button
  const renderButton = (elementId: string): void => {
    if (typeof window !== 'undefined' && window.google && window.google.accounts) {
      const element = document.getElementById(elementId);
      if (element) {
        window.google.accounts.id.renderButton(element, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
        });
      }
    }
  };

  // Helper to store the auth token
  const storeToken = (token: string): void => {
    saveToken(token);
  };

  // Handle authentication errors (401/403) by logging the user out
  const handleAuthError = async (error: any): Promise<boolean> => {
    const errorCode = error?.status || error?.result?.error?.code || 
                      (error?.message && error.message.includes('401')) ? 401 : null;
    
    if (errorCode === 401 || errorCode === 403) {
      console.log('Authentication error detected, signing out user');
      
      // Sign out the user
      await signOut();
      
      // Update the error state to inform the user
      update(state => ({
        ...state,
        error: 'Your session has expired. Please sign in again.'
      }));
      
      return false;
    }
    
    return true;
  };

  return {
    subscribe,
    initialize: initializeAuth,
    signIn,
    signOut,
    getToken: getAuthToken,
    refreshToken,
    renderButton,
    handleAuthError
  };
};

// Create and export the store
export const googleAuthStore: GoogleAuthStore = createGoogleAuthStore();

// Derived stores for convenience
export const isAuthenticated = derived(
  googleAuthStore,
  $store => $store.isAuthenticated
);

export const user = derived(
  googleAuthStore,
  $store => $store.user
);

export const isInitialized = derived(
  googleAuthStore,
  $store => $store.isInitialized
);

export const authError = derived(
  googleAuthStore,
  $store => $store.error
);

// Add type definitions for the Google API
declare global {
  interface Window {
    gapi: {
      load: (apiName: string, options: {
        callback: () => void;
        onerror: () => void;
      }) => void;
      client: {
        init: (config: {
          apiKey: string;
          clientId?: string;
          discoveryDocs: string[];
          scope?: string;
        }) => Promise<void>;
        setToken: (token: { access_token: string }) => void;
        drive?: any;
        load: (api: string, version: string) => Promise<any>;
      };
    };
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          prompt: (callback: (notification: any) => void) => void;
          renderButton: (element: HTMLElement, options: any) => void;
          disableAutoSelect: () => void;
        };
        oauth2: {
          initTokenClient: (config: {
            client_id: string;
            scope: string;
            callback: (response: { access_token: string }) => void;
            error_callback?: (error: { message?: string }) => void;
          }) => {
            requestAccessToken: () => void;
          };
        };
      };
    };
  }
}
