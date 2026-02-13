<script lang="ts">
  import { onMount } from 'svelte';
  import { googleAuthStore, isAuthenticated, user } from '../stores/googleAuthStore';

  // Props
  export let buttonClass = '';
  export let showUserInfo = true;

  // Local state
  let isInitializing = false;
  let error: string | null = null;
  let isOriginError = false;
  let currentOrigin = '';

  onMount(async () => {
    currentOrigin = window.location.origin;
    try {
      isInitializing = true;
      await googleAuthStore.initialize();
    } catch (err) {
      console.error('Error initializing Google Auth:', err);
      const errorMessage = err instanceof Error ? err.message : String(err);
      
      // Check if this is an origin error
      if (typeof errorMessage === 'string' && 
          (errorMessage.includes('Not a valid origin') || 
           errorMessage.includes('idpiframe_initialization_failed'))) {
        isOriginError = true;
      } else {
        error = errorMessage;
      }
    } finally {
      isInitializing = false;
    }
  });

  // Handle sign in
  async function handleSignIn() {
    try {
      isInitializing = true;
      error = null;
      await googleAuthStore.signIn();
    } catch (err) {
      console.error('Error signing in:', err);
      const errorMessage = err instanceof Error ? err.message : String(err);
      
      // Check if this is an origin error
      if (typeof errorMessage === 'string' && 
          (errorMessage.includes('Not a valid origin') || 
           errorMessage.includes('idpiframe_initialization_failed'))) {
        isOriginError = true;
      } else {
        error = errorMessage;
      }
    } finally {
      isInitializing = false;
    }
  }

  // Handle sign out
  async function handleSignOut() {
    try {
      isInitializing = true;
      error = null;
      await googleAuthStore.signOut();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to sign out';
      console.error('Error signing out:', err);
    } finally {
      isInitializing = false;
    }
  }
</script>

<div class="google-auth-container">
  {#if isOriginError}
    <div class="origin-error">
      <h3>Origin Not Authorized</h3>
      <p>The current origin <code>{currentOrigin}</code> is not registered as an authorized JavaScript origin in your Google Cloud Console.</p>
      <div class="instructions">
        <p>To fix this:</p>
        <ol>
          <li>Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank">Google Cloud Console</a></li>
          <li>Navigate to "APIs & Services" > "Credentials"</li>
          <li>Find and edit your OAuth 2.0 Client ID</li>
          <li>Under "Authorized JavaScript origins", add: <code>{currentOrigin}</code></li>
          <li>Save your changes</li>
          <li>Reload this page</li>
        </ol>
      </div>
      <p class="note">Note: When testing locally, you'll need to add each origin you use (e.g., <code>http://localhost:5174</code>, <code>http://127.0.0.1:5174</code>, etc.)</p>
    </div>
  {:else if $isAuthenticated}
    <button 
      on:click={handleSignOut}
      class="google-auth-button sign-out {buttonClass}"
      disabled={isInitializing}
    >
      <span class="button-content">
        {#if isInitializing}
          <span class="loading-spinner"></span>
        {:else}
          <span class="google-icon">G</span>
        {/if}
        Sign Out
      </span>
    </button>
    {#if showUserInfo && $user}
      <div class="user-info">
        <img src={$user.imageUrl} alt={$user.name} class="user-avatar" />
        <span class="user-name">{$user.name}</span>
      </div>
    {/if}
  {:else}
    <button 
      on:click={handleSignIn}
      class="google-auth-button sign-in {buttonClass}"
      disabled={isInitializing}
    >
      <span class="button-content">
        {#if isInitializing}
          <span class="loading-spinner"></span>
        {:else}
          <span class="google-icon">G</span>
        {/if}
        Sign in with Google Drive
      </span>
    </button>
  {/if}
  
  {#if error}
    <div class="error-message">
      {error}
    </div>
  {/if}
</div>

<style>
  .google-auth-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  
  .google-auth-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s, box-shadow 0.2s;
    border: 1px solid #dadce0;
    background-color: white;
    color: #3c4043;
    min-width: 180px;
  }
  
  .google-auth-button:hover {
    background-color: #f8f9fa;
    box-shadow: 0 1px 2px rgba(60, 64, 67, 0.3);
  }
  
  .google-auth-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .button-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .google-icon {
    font-size: 1.2rem;
    font-weight: bold;
    color: #4285F4;
  }
  
  .loading-spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-top-color: #4285F4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  
  .user-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  
  .user-avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
  }
  
  .user-name {
    font-size: 0.9rem;
    color: #3c4043;
  }
  
  .error-message {
    color: #d93025;
    font-size: 0.8rem;
    margin-top: 0.5rem;
    text-align: center;
  }

  .origin-error {
    border: 1px solid #f8d7da;
    border-radius: 4px;
    padding: 1rem;
    margin: 0.5rem 0;
    background-color: #fff3f3;
    max-width: 500px;
    color: #721c24;
  }

  .origin-error h3 {
    margin-top: 0;
    font-size: 1rem;
    color: #d93025;
  }

  .origin-error code {
    background-color: #f1f3f4;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-family: monospace;
    color: #333;
  }

  .instructions {
    margin: 1rem 0;
  }

  .instructions ol {
    padding-left: 1.5rem;
    margin: 0.5rem 0;
  }

  .instructions li {
    margin-bottom: 0.25rem;
  }

  .note {
    font-size: 0.8rem;
    font-style: italic;
    margin-top: 0.5rem;
  }

  .origin-error a {
    color: #0366d6;
    text-decoration: none;
  }

  .origin-error a:hover {
    text-decoration: underline;
  }
</style>
