<!-- Toast container component -->
<script lang="ts">
  import { onDestroy } from 'svelte';
  import Toast from './Toast.svelte';
  import { toastStore } from '../stores/toastStore';
  
  let toasts = [];
  
  const unsubscribe = toastStore.subscribe(value => {
    toasts = value;
  });
  
  onDestroy(unsubscribe);
  
  function handleRemove(id: string) {
    toastStore.removeToast(id);
  }
</script>

<div class="toast-container">
  {#each toasts as toast (toast.id)}
    <Toast 
      message={toast.message}
      type={toast.type}
      duration={toast.duration}
      showSpinner={toast.showSpinner}
      on:outroend={() => handleRemove(toast.id)}
    />
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    z-index: 1000;
  }
</style>
