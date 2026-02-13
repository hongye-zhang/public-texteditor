<!-- Toast notification component -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  
  export let message: string;
  export let duration: number = 3000; // Default duration in ms
  export let type: 'info' | 'success' | 'warning' | 'error' = 'info';
  export let showSpinner: boolean = false;
  
  let visible = true;
  let timeoutId: ReturnType<typeof setTimeout>;
  
  onMount(() => {
    if (duration > 0) {
      timeoutId = setTimeout(() => {
        visible = false;
      }, duration);
    }
    
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  });
  
  export function hide() {
    visible = false;
    if (timeoutId) clearTimeout(timeoutId);
  }
</script>

{#if visible}
  <div 
    class="toast {type}" 
    transition:fade={{ duration: 200 }}
    role="alert"
  >
    {#if showSpinner}
      <div class="spinner"></div>
    {/if}
    <span class="message">{message}</span>
  </div>
{/if}

<style>
  .toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 16px;
    border-radius: 4px;
    color: white;
    font-size: 14px;
    z-index: 1000;
    display: flex;
    align-items: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    max-width: 300px;
  }
  
  .info {
    background-color: #3498db;
  }
  
  .success {
    background-color: #2ecc71;
  }
  
  .warning {
    background-color: #f39c12;
  }
  
  .error {
    background-color: #e74c3c;
  }
  
  .message {
    margin-left: 8px;
  }
  
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
