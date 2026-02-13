<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fileStore, activeFile, hasFileSystemPermission } from '../stores/fileStore';
  
  export let show = false;
  export let fileId: string | null = null;
  export let suggestedName = 'Untitled.txt';
  
  const dispatch = createEventDispatcher();
  
  let fileName = suggestedName;
  let saving = false;
  let errorMessage = '';
  let isCheckingPermission = false;
  
  // Reset the dialog state when it's shown
  $: if (show) {
    fileName = suggestedName;
    saving = false;
    errorMessage = '';
    isCheckingPermission = false;
  }
  
  // Close the dialog
  function close() {
    show = false;
    dispatch('close');
  }
  
  // Handle saving the file
  async function handleSave() {
    if (!fileId) {
      errorMessage = 'No file selected';
      return;
    }
    
    if (!fileName.trim()) {
      errorMessage = 'Please enter a file name';
      return;
    }
    
    saving = true;
    errorMessage = '';
    
    try {
      // Check if we have file system permission
      if (!$hasFileSystemPermission) {
        isCheckingPermission = true;
        const hasPermission = await fileStore.checkFileSystemAccess();
        isCheckingPermission = false;
        
        if (!hasPermission) {
          errorMessage = 'Please grant permission to access your file system to save files locally.';
          saving = false;
          return;
        }
      }
      
      // Try to save the file to disk
      const path = await fileStore.saveFileToDisk(fileId, fileName);
      
      if (path) {
        // Update the file title
        fileStore.updateFileMetadata(fileId, { title: fileName });
        close();
        dispatch('saved', { path });
      } else {
        errorMessage = 'Failed to save file. Please try again.';
      }
    } catch (error) {
      console.error('Error saving file:', error);
      errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
    } finally {
      saving = false;
    }
  }
  
  // Handle selecting a save location
  async function handleSelectLocation() {
    try {
      isCheckingPermission = true;
      const location = await fileStore.selectSaveLocation();
      isCheckingPermission = false;
      
      if (location) {
        dispatch('locationSelected', { location });
      }
    } catch (error) {
      console.error('Error selecting save location:', error);
      errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      isCheckingPermission = false;
    }
  }
</script>

{#if show}
  <div class="dialog-backdrop">
    <div class="dialog">
      <div class="dialog-header">
        <h2>Save File</h2>
        <button class="close-button" on:click={close} aria-label="Close dialog">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="dialog-content">
        <div class="form-group">
          <label for="file-name">File Name</label>
          <input 
            type="text" 
            id="file-name" 
            bind:value={fileName} 
            placeholder="Enter file name"
            disabled={saving || isCheckingPermission}
          />
        </div>
        
        <div class="form-group">
          <button 
            class="location-button" 
            on:click={handleSelectLocation}
            disabled={saving || isCheckingPermission}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            {#if isCheckingPermission}
              <span class="loading-spinner"></span>
              Checking Permission...
            {:else if $hasFileSystemPermission && $fileStore.saveLocation}
              Save to: {$fileStore.saveLocation}
            {:else}
              Select Save Location
            {/if}
          </button>
        </div>
        
        {#if errorMessage}
          <div class="error-message">
            {errorMessage}
          </div>
        {/if}
      </div>
      
      <div class="dialog-footer">
        <button class="cancel-button" on:click={close} disabled={saving || isCheckingPermission}>
          Cancel
        </button>
        <button 
          class="save-button" 
          on:click={handleSave}
          disabled={saving || isCheckingPermission || !fileName.trim()}
        >
          {#if saving}
            Saving...
          {:else if isCheckingPermission}
            Checking Permission...
          {:else}
            Save
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .dialog-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  
  .dialog {
    background-color: white;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 500px;
    overflow: hidden;
  }
  
  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e9ecef;
  }
  
  .dialog-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  }
  
  .close-button {
    background: none;
    border: none;
    color: #6c757d;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s;
  }
  
  .close-button:hover {
    background-color: #f8f9fa;
  }
  
  .dialog-content {
    padding: 1rem;
  }
  
  .form-group {
    margin-bottom: 1rem;
  }
  
  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }
  
  .form-group input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    font-size: 1rem;
  }
  
  .location-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #f8f9fa;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    width: 100%;
    justify-content: center;
  }
  
  .location-button:hover {
    background-color: #e9ecef;
  }
  
  .error-message {
    padding: 0.75rem;
    background-color: #f8d7da;
    color: #721c24;
    border-radius: 0.25rem;
    margin-top: 1rem;
    font-size: 0.875rem;
  }
  
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid #e9ecef;
  }
  
  .cancel-button {
    padding: 0.5rem 1rem;
    background-color: #f8f9fa;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .cancel-button:hover {
    background-color: #e9ecef;
  }
  
  .save-button {
    padding: 0.5rem 1rem;
    background-color: #4a5568;
    color: white;
    border: none;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .save-button:hover {
    background-color: #2d3748;
  }
  
  .save-button:disabled,
  .cancel-button:disabled,
  .location-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .loading-spinner {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: #fff;
    animation: spin 1s ease-in-out infinite;
    margin-right: 0.25rem;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
