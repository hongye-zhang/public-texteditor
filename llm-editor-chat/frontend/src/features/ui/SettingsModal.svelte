<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { t } from '$lib/i18n';
  import LanguageSelector from './LanguageSelector.svelte';
  import { availableModels, getModelById } from '$lib/config/models';
  import { selectedModelId, apiKey, apiKeyRequired } from '$lib/stores/modelStore';
  
  export let isOpen = false;
  
  const dispatch = createEventDispatcher();
  
  // Get the description for the currently selected model
  $: selectedModelDescription = getModelById($selectedModelId)?.description || '';
  
  // Handle model change
  function handleModelChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedModelId.set(select.value);
  }
  
  // Handle API key change
  function handleApiKeyChange(event: Event) {
    const input = event.target as HTMLInputElement;
    apiKey.set(input.value);
  }
  
  function closeModal() {
    dispatch('close');
  }
  
  // Close modal when clicking outside the content
  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeModal();
    }
  }
  
  // 处理背景的键盘事件
  function handleBackdropKeydown(event: KeyboardEvent) {
    // 当按下 Enter 或 Space 键时，关闭模态窗口
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      closeModal();
    }
  }
  
  // Close modal when pressing Escape key
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      closeModal();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <div class="modal-backdrop" role="presentation" on:click={handleBackdropClick} on:keydown={handleBackdropKeydown}>
    <div class="modal-content" role="dialog" aria-labelledby="settings-title">
      <div class="modal-header">
        <h2 id="settings-title">{$t('settings.title')}</h2>
        <button class="close-button" on:click={closeModal} aria-label={$t('settings.cancel')}>×</button>
      </div>
      
      <div class="modal-body">
        <div class="settings-section">
          <h3>{$t('settings.language')}</h3>
          <div class="setting-item">
            <div class="setting-with-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="settings-icon">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              <LanguageSelector />
            </div>
          </div>
        </div>
        
        <!-- Additional settings sections can be added here -->
        <div class="settings-section">
          <h3>{$t('settings.theme')}</h3>
          <div class="setting-item">
            <label class="setting-label">
              <input type="checkbox" /> {$t('settings.darkMode')}
            </label>
          </div>
        </div>
        
        <div class="settings-section">
          <h3>{$t('settings.fontSize')}</h3>
          <div class="setting-item">
            <input type="range" min="12" max="24" value="16" />
            <span class="font-size-value">16px</span>
          </div>
        </div>

        <div class="settings-section">
          <h3>{$t('settings.llmModel')}</h3>
          <div class="setting-item">
            <div class="setting-with-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="settings-icon">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
              <select class="model-selector" value={$selectedModelId} on:change={handleModelChange}>
                {#each availableModels as model}
                  <option value={model.id}>{model.name}</option>
                {/each}
              </select>
            </div>
            {#if selectedModelDescription}
              <div class="model-description">{selectedModelDescription}</div>
            {/if}
            
            {#if $apiKeyRequired}
              <div class="api-key-section">
                <label for="api-key">{$t('settings.apiKey')}</label>
                <input 
                  id="api-key"
                  type="password" 
                  class="api-key-input" 
                  placeholder={$t('settings.apiKeyPlaceholder')} 
                  value={$apiKey} 
                  on:input={handleApiKeyChange}
                />
                <div class="api-key-help">{$t('settings.apiKeyHelp')}</div>
              </div>
            {/if}
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeModal}>{$t('settings.cancel')}</button>
        <button class="save-button" on:click={closeModal}>{$t('settings.save')}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }
  
  .modal-content {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
  
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #eee;
  }
  
  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
  }
  
  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  
  .close-button:hover {
    background-color: #f0f0f0;
  }
  
  .modal-body {
    padding: 1rem;
    flex-grow: 1;
  }
  
  .settings-section {
    margin-bottom: 1.5rem;
  }
  
  .settings-section h3 {
    margin-top: 0;
    margin-bottom: 0.75rem;
    font-size: 1.1rem;
    color: #333;
  }
  
  .setting-item {
    padding: 0.5rem 0;
  }
  
  .setting-with-icon {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .settings-icon {
    color: #6b7280;
    flex-shrink: 0;
  }
  
  .model-selector {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: white;
  }
  
  .model-description {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.25rem;
    margin-left: 2.5rem;
  }
  
  .api-key-section {
    margin-top: 0.5rem;
    margin-left: 2.5rem;
  }
  
  .api-key-input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: 0.25rem;
  }
  
  .api-key-help {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.25rem;
  }
  
  :global(body.dark-theme) .model-selector,
  :global(body.dark-theme) .api-key-input {
    background-color: #374151;
    border-color: #4b5563;
    color: #f3f4f6;
  }
  
  .setting-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }
  
  .font-size-value {
    margin-left: 1rem;
  }
  
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1rem;
    border-top: 1px solid #eee;
  }
  
  .cancel-button, .save-button {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
  }
  
  .cancel-button {
    background-color: #f0f0f0;
    border: 1px solid #ddd;
  }
  
  .save-button {
    background-color: #4f46e5;
    color: white;
    border: none;
  }
  
  .save-button:hover {
    background-color: #4338ca;
  }
  
  /* Dark mode support */
  :global(body.dark-theme) .modal-content {
    background-color: #1f2937;
    color: #f3f4f6;
  }
  
  :global(body.dark-theme) .modal-header,
  :global(body.dark-theme) .modal-footer {
    border-color: #374151;
  }
  
  :global(body.dark-theme) .close-button:hover {
    background-color: #374151;
  }
  
  :global(body.dark-theme) .cancel-button {
    background-color: #374151;
    border-color: #4b5563;
    color: #f3f4f6;
  }
  
  :global(body.dark-theme) .settings-section h3 {
    color: #d1d5db;
  }
</style>
