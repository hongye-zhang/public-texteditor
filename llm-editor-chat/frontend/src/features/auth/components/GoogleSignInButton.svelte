<script lang="ts">
  import { onMount } from 'svelte';
  import { googleAuthStore, isAuthenticated } from '../stores/googleAuthStore';
  
  // Props
  export let buttonText = 'Sign in with Google';
  export let theme = 'filled_blue'; // Options: 'outline', 'filled_blue', 'filled_black'
  export let size = 'large'; // Options: 'large', 'medium', 'small'
  export let shape = 'rectangular'; // Options: 'rectangular', 'pill', 'circle', 'square'
  export let width: string | undefined = undefined;
  export let locale = 'en';
  export let minimalist = false; // New prop for minimalist mode
  export let buttonClass = ''; // Class to apply to the container
  
  // Local state
  let buttonContainer: HTMLDivElement;
  let buttonInitialized = false;
  let isProxyEnvironment = false;
  
  // Check if we're in a proxy environment
  function checkProxyEnvironment() {
    if (typeof window === 'undefined') return false;
    
    const currentOrigin = window.location.origin;
    isProxyEnvironment = currentOrigin.includes('127.0.0.1');
    console.log(`Current origin: ${currentOrigin}, Proxy environment: ${isProxyEnvironment}`);
    return isProxyEnvironment;
  }
  
  // Initialize the Google Sign-In button
  function initializeButton() {
    if (!buttonContainer || buttonInitialized) {
      return;
    }
    
    // If minimalist mode is enabled, use a simple icon button
    if (minimalist) {
      buttonContainer.innerHTML = `
        <button class="minimalist-button" title="Sign in with Google">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14M5 12h14"></path>
          </svg>
        </button>
      `;
      
      // Add click event listener to the minimalist button
      const minimalistButton = buttonContainer.querySelector('.minimalist-button');
      if (minimalistButton) {
        minimalistButton.addEventListener('click', () => {
          googleAuthStore.signIn();
        });
      }
      
      buttonInitialized = true;
      return;
    }
    
    // If we're in a proxy environment, use a custom button
    if (checkProxyEnvironment()) {
      buttonContainer.innerHTML = `
        <button class="custom-google-button ${theme} ${size}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="24" height="24">
            <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
            <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
            <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
            <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
          </svg>
          <span>${buttonText}</span>
        </button>
      `;
      
      // Add click event listener to the custom button
      const customButton = buttonContainer.querySelector('.custom-google-button');
      if (customButton) {
        customButton.addEventListener('click', () => {
          console.log('Custom Google button clicked in proxy environment');
          // Trigger normal sign-in flow instead of automatic authentication
          googleAuthStore.signIn();
        });
      }
      
      buttonInitialized = true;
      return;
    }
    
    try {
      // Only try to render the Google button if the API is available
      if (window.google && window.google.accounts) {
        // Render the Google Sign-In button
        window.google.accounts.id.renderButton(
          buttonContainer,
          {
            type: 'standard',
            theme,
            size,
            text: buttonText === 'Sign in with Google' ? 'signin_with' : buttonText,
            shape,
            width: width ? width : undefined,
            locale
          }
        );
        
        buttonInitialized = true;
      } else {
        console.warn('Google Identity Services not available');
        // Fallback to a basic button
        buttonContainer.innerHTML = `
          <button class="custom-google-button ${theme} ${size}">
            <span>${buttonText}</span>
          </button>
        `;
      }
    } catch (error) {
      console.error('Error initializing Google Sign-In button:', error);
    }
  }
  
  // Initialize Google Auth and the button on mount
  onMount(async () => {
    try {
      // Initialize Google Auth
      await googleAuthStore.initialize();
      
      // Initialize the button after a short delay to ensure Google API is fully loaded
      setTimeout(() => {
        initializeButton();
      }, 100);
    } catch (error) {
      console.error('Error initializing Google Auth:', error);
    }
  });
  
  // Re-initialize the button when the authenticated state changes
  $: if (!$isAuthenticated && buttonContainer && !buttonInitialized) {
    initializeButton();
  }
</script>

<div class="google-signin-container {buttonClass}" class:minimalist>
  {#if !$isAuthenticated}
    <div id="google-signin-button" bind:this={buttonContainer}></div>
  {/if}
</div>

<style>
  .google-signin-container {
    display: flex;
    justify-content: center;
    margin: 0.5rem 0;
  }
  
  .google-signin-container.minimalist {
    margin: 0;
  }
  
  .minimalist-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 4px;
    background-color: #f0f0f0;
    color: #1a73e8;
    cursor: pointer;
    transition: background-color 0.2s;
    padding: 0;
  }
  
  .minimalist-button:hover {
    background-color: #e0e0e0;
  }
  
  .custom-google-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 4px;
    font-family: 'Roboto', sans-serif;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border: 1px solid #dadce0;
    background-color: white;
    color: #3c4043;
    transition: background-color 0.2s;
  }
  
  .custom-google-button:hover {
    background-color: #f8f9fa;
  }
  
  .custom-google-button.filled_blue {
    background-color: #1a73e8;
    color: white;
    border: none;
  }
  
  .custom-google-button.filled_blue:hover {
    background-color: #1765cc;
  }
  
  .custom-google-button.filled_black {
    background-color: #202124;
    color: white;
    border: none;
  }
  
  .custom-google-button.filled_black:hover {
    background-color: #333438;
  }
  
  .custom-google-button.large {
    padding: 12px 24px;
    font-size: 16px;
  }
  
  .custom-google-button.medium {
    padding: 8px 16px;
    font-size: 14px;
  }
  
  .custom-google-button.small {
    padding: 6px 12px;
    font-size: 12px;
  }
</style>
