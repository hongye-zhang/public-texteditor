<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { t } from '$lib/i18n';
  import SettingsModal from './SettingsModal.svelte';
  
  const dispatch = createEventDispatcher();
  
  let isModalOpen = false;
  
  function toggleModal() {
    isModalOpen = !isModalOpen;
  }
  
  function closeModal() {
    isModalOpen = false;
  }
</script>

<div class="settings-container">
  <button 
    class="settings-button" 
    on:click={toggleModal} 
    aria-label={$t('settings.title')}
    title={$t('settings.title')}
  >
    <!-- SVG Gear Icon -->
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
    </svg>
  </button>
</div>

<SettingsModal isOpen={isModalOpen} on:close={closeModal} />

<style>
  .settings-container {
    display: inline-block;
  }
  
  .settings-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #4b5563;
    transition: background-color 0.2s, color 0.2s;
  }
  
  .settings-button:hover {
    background-color: rgba(0, 0, 0, 0.05);
    color: #000;
  }
  
  .settings-button:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.4);
  }
  
  /* Dark mode support */
  :global(body.dark-theme) .settings-button {
    color: #d1d5db;
  }
  
  :global(body.dark-theme) .settings-button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
</style>
