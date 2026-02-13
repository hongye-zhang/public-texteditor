<script lang="ts">
  import { onMount } from 'svelte';
  import { googleAuthStore, isAuthenticated, user, isInitialized, authError } from '../stores/googleAuthStore';
  import GoogleSignInButton from './GoogleSignInButton.svelte';
  
  // Local state
  let showRetry = false;
  let isProxyEnvironment = false;
  
  // Check if we're in a proxy environment
  function checkProxyEnvironment() {
    if (typeof window === 'undefined') return false;
    
    const currentOrigin = window.location.origin;
    isProxyEnvironment = currentOrigin.includes('127.0.0.1');
    console.log(`Current origin: ${currentOrigin}, Proxy environment: ${isProxyEnvironment}`);
    return isProxyEnvironment;
  }
  
  // Initialize Google Auth on mount
  onMount(async () => {
    try {
      // Check if we're in a proxy environment, but don't change authentication behavior
      checkProxyEnvironment();
      // Initialize auth (will respect AUTO_LOGIN_ENABLED setting)
      console.log('Initializing Google Auth with auto-login disabled');
      await googleAuthStore.initialize();
    } catch (error) {
      console.error('Error initializing Google Auth:', error);
      showRetry = true;
    }
  });
  
  // Handle retry
  const handleRetry = async () => {
    showRetry = false;
    try {
      await googleAuthStore.initialize();
    } catch (error) {
      console.error('Error retrying Google Auth initialization:', error);
      showRetry = true;
    }
  };
  
  // Handle sign out
  const handleSignOut = async () => {
    try {
      await googleAuthStore.signOut();
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };
</script>

<div class="auth-controls">
  {#if !$isInitialized}
    <button class="auth-button loading" disabled aria-label="Loading authentication status">
      <span class="loading-spinner"></span>
    </button>
  {:else if $authError}
    <button class="auth-button error" title="{$authError}" on:click={handleRetry} aria-label="Authentication error: {$authError}. Click to retry.">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 16l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-10a10 10 0 11-20 0 10 10 0 0120 0z"></path>
      </svg>
    </button>
  {:else if $isAuthenticated}
    <button class="auth-button signout" title="Sign out {$user?.name || 'User'}" on:click={handleSignOut} aria-label="Sign out {$user?.name || 'User'}">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
        <polyline points="16 17 21 12 16 7"></polyline>
        <line x1="21" y1="12" x2="9" y2="12"></line>
      </svg>
    </button>
  {:else}
    <GoogleSignInButton minimalist={true} />
  {/if}
</div>

<style>
  .auth-controls {
    display: flex;
    justify-content: flex-end;
    align-items: center;
  }
  
  .auth-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 4px;
    background-color: #f0f0f0;
    color: #333;
    cursor: pointer;
    transition: background-color 0.2s;
    padding: 0;
  }
  
  .auth-button:hover {
    background-color: #e0e0e0;
  }
  
  .auth-button.signout {
    background-color: #f5f5f5;
    color: #333;
  }
  
  .auth-button.error {
    background-color: #ffebee;
    color: #c62828;
  }
  
  .loading-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-radius: 50%;
    border-top-color: #333;
    animation: spin 1s ease-in-out infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
