<script lang="ts">
  import { fileStore, activeFile, isFirstFile, hasFileSystemPermission } from '../stores/fileStore';
  import { onMount, onDestroy, afterUpdate } from 'svelte';
  import { writable, get } from 'svelte/store';
  import { fileSidebarCollapsed } from '../../ui';
  import { isAuthenticated } from '../../auth/stores/googleAuthStore';
  import { documentTreeVisible } from '../stores/documentTreeStore';
  import DocumentTree from './DocumentTree.svelte';
  import AuthStatusManager from '../../auth/components/AuthStatusManager.svelte';
  import { t } from '../../../lib/i18n';
  
  // Reference to the global save status store
  let saveStatusStore: any;
  let saveInProgress = false;
  let unsubscribeSaveStatus: Function | undefined;
  
  // Track authentication state for refreshing files
  let wasAuthenticated = false;
  let unsubscribeAuth: Function | undefined;
  
  // Check if File System Access API is supported
  let isFileSystemAccessSupported = false;
  
  // Track directory selection state
  let isSelectingDirectory = false;
  let directorySelectionError = '';
  let isRestoringDirectory = false;

  // Track active tab for sidebar navigation (simplified to string for compatibility)
  let activeTab = 'files';
  
  // Track expanded file items to show assets
  let expandedFileIds = new Set();
  
  // Function to set active tab
  function setActiveTab(tab: string) {
    activeTab = tab;
    
    // If "new" tab is clicked, handle new file creation
    if (tab === 'new') {
      handleNewFile();
      // Reset back to files tab after clicking new
      activeTab = 'files';
    } else if (tab === 'tree') {
      // Synchronize with documentTreeVisible store
      documentTreeVisible.set(true);
    } else {
      // If switching to files tab, hide document tree
      documentTreeVisible.set(false);
    }
  }
  
  // Format date for display
  function formatDate(timestamp: number): string {
    const date = new Date(timestamp);
    return date.toLocaleString();
  }
  
  // Format file size (e.g., "1.5 MB")
  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  // Format relative time (e.g., "2 hours ago")
  function formatRelativeTime(timestamp: number): string {
    const now = Date.now();
    const diff = now - timestamp;
    
    // Convert to seconds
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) {
      return $t('file.justNow');
    }
    
    // Convert to minutes
    const minutes = Math.floor(seconds / 60);
    
    if (minutes < 60) {
      return `${minutes} ${minutes === 1 ? $t('time.minute') : $t('time.minutes')} ${$t('time.ago')}`;
    }
    
    // Convert to hours
    const hours = Math.floor(minutes / 60);
    
    if (hours < 24) {
      return `${hours} ${hours === 1 ? $t('time.hour') : $t('time.hours')} ${$t('time.ago')}`;
    }
    
    // Convert to days
    const days = Math.floor(hours / 24);
    
    if (days < 30) {
      return `${days} ${days === 1 ? $t('time.day') : $t('time.days')} ${$t('time.ago')}`;
    }
    
    // Just return the date for older files
    return formatDate(timestamp);
  }
  
  // Function to request file system permission
  async function requestFileSystemPermission() {
    try {
      isSelectingDirectory = true;
      directorySelectionError = '';
      
      const result = await fileStore.checkFileSystemAccess();
      
      // If permission was granted and we have a save location, the directory handle is already restored
      if (result && $fileStore.saveLocation) {
        console.log('Permission granted and directory handle restored');
        console.log('Current files in state:', $fileStore.files.length);
        
        // Scan for files in the directory
        const dirHandle = fileStore.getDirectoryHandle();
        if (dirHandle) {
          try {
            await fileStore.scanDirectoryForFiles(dirHandle);
            console.log('Directory scan complete');
            console.log('Current files in state after directory scan:', $fileStore.files.length);
          } catch (scanError) {
            console.warn('Error scanning directory:', scanError);
          }
        }
      }
      
      isSelectingDirectory = false;
      return result;
    } catch (error) {
      console.error('Error requesting file system permission:', error);
      isSelectingDirectory = false;
      directorySelectionError = $t('file.permissionError');
      return false;
    }
  }
  
  // Function to select save location
  async function selectSaveLocation() {
    try {
      isSelectingDirectory = true;
      directorySelectionError = '';
      
      console.log('Selecting save location...');
      const location = await fileStore.selectSaveLocation();
      
      if (location) {
        console.log('Save location selected:', location);
      } else {
        console.log('Save location selection cancelled or failed');
        directorySelectionError = 'Failed to select a save location.';
      }
      
      isSelectingDirectory = false;
      return location;
    } catch (error) {
      console.error('Error selecting save location:', error);
      isSelectingDirectory = false;
      directorySelectionError = $t('file.locationError');
      return null;
    }
  }
  
  // Handle creating a new file
  async function handleNewFile() {
    // Check if this is the first file or not
    if ($isFirstFile) {
      // For the first file, just create it in local storage
      fileStore.createFile('New Document', '');
    } else {
      try {
        // If we don't have permission yet, request it
        if (!$hasFileSystemPermission && $fileStore.saveLocation === 'File System') {
          const hasPermission = await requestFileSystemPermission();
          if (!hasPermission) {
            console.log('User denied file system permission');
            // Fall back to local storage
            fileStore.createFile('New Document', '');
            return;
          }
        }
        
        fileStore.createFile('New Document', '');
        
        // Refresh files after creating a new file
        if ($isAuthenticated) {
          console.log('New file created, refreshing file list');
          await refreshFiles();
        }
      } catch (error) {
        console.error('Error creating new file:', error);
        alert($t('file.createError'));
      }
    }
  }
  
  // Handle clicking on a file to open it
  function handleFileClick(id: string) {
    // Don't allow switching files if a save is in progress
    if (saveInProgress) {
      console.log('Save in progress, cannot switch files');
      alert($t('file.saveInProgress'));
      return;
    }
    
    // Don't switch if we're already on this file
    if ($activeFile && $activeFile.id === id) {
      return;
    }
    
    // Refresh files when switching to another file
    if ($isAuthenticated) {
      console.log('Switching files, refreshing file list');
      refreshFiles();
    }
    
    // Force an immediate save of the current file before switching
    if ($activeFile && window.forceSaveCurrentFile) {
      try {
        // Set the save in progress flag via the store
        if (saveStatusStore) {
          saveStatusStore.update((state: any) => ({
            ...state,
            status: 'saving',
            inProgress: true,
            fileId: $activeFile.id
          }));
        }
        
        console.log('Forcing save before switching files');
        window.forceSaveCurrentFile(() => {
          // After save completes, switch to the new file
          console.log('Save completed, now switching to file:', id);
          fileStore.setActiveFile(id);
          
          // Reset the save status
          if (saveStatusStore) {
            saveStatusStore.update((state: any) => ({
              ...state,
              status: 'idle',
              inProgress: false,
              fileId: null
            }));
          }
        });
      } catch (error) {
        console.error('Error saving file before switch:', error);
        // If save fails, still allow switching but warn the user
        if (confirm($t('file.saveFailedConfirm'))) {
          fileStore.setActiveFile(id);
        }
        
        // Reset the save status
        if (saveStatusStore) {
          saveStatusStore.update((state: any) => ({
            ...state,
            status: 'idle',
            inProgress: false,
            fileId: null
          }));
        }
      }
    } else {
      // If no active file or no force save function, just switch
      fileStore.setActiveFile(id);
    }
  }
  
  // Handle deleting a file
  function handleDeleteFile(event: Event, id: string) {
    event.stopPropagation(); // Prevent opening the file
    
    if (confirm($t('confirm.delete'))) {
      fileStore.deleteFile(id);
    }
  }

  // Handle renaming a file
  function handleRenameFile(event: Event, id: string) {
    event.stopPropagation(); // Prevent opening the file
    
    // Find the file to rename
    const file = $fileStore.files.find(f => f.id === id);
    if (!file) return;
    
    // Prompt for new name
    const newName = prompt('Enter new file name:', file.title);
    
    // If user cancels or enters empty name, do nothing
    if (!newName || newName.trim() === '') return;
    
    // Update file metadata with new name
    fileStore.updateFileMetadata(id, { title: newName });
  }
  
  // Function to refresh files from Google Drive
  async function refreshFiles() {
    try {
      console.log('Manually refreshing files from Google Drive');
      await fileStore.refreshFiles();
      console.log('File refresh complete, current files:', $fileStore.files.length);
    } catch (error) {
      console.error('Error refreshing files:', error);
    }
  }

  onMount(() => {
    try {
      // Check if File System Access API is supported
      isFileSystemAccessSupported = 'showDirectoryPicker' in window && 'showSaveFilePicker' in window;
      
      // Get reference to the global save status store
      if (typeof window !== 'undefined' && (window as any).saveStatusStore) {
        saveStatusStore = (window as any).saveStatusStore;
        
        // Subscribe to the save status store
        unsubscribeSaveStatus = saveStatusStore.subscribe((value: any) => {
          saveInProgress = value.inProgress;
        });
      }
      
      // Subscribe to documentTreeVisible store to sync with activeTab
      const unsubscribeDocumentTree = documentTreeVisible.subscribe(visible => {
        if (visible && activeTab !== 'tree') {
          activeTab = 'tree';
        } else if (!visible && activeTab === 'tree') {
          activeTab = 'files';
        }
      });
      
      // Subscribe to authentication state changes to refresh files when needed
      wasAuthenticated = get(isAuthenticated);
      unsubscribeAuth = isAuthenticated.subscribe(async (authenticated) => {
        console.log('Auth state changed in FileSidebar:', authenticated);
        
        // If user just logged in, refresh the files
        if (authenticated && !wasAuthenticated) {
          console.log('User just logged in, refreshing files');
          // Wait a moment for auth to fully complete
          setTimeout(async () => {
            await refreshFiles();
          }, 1000);
        }
        
        wasAuthenticated = authenticated;
      });
      
      // If the API is supported and we have a save location, attempt to restore the directory handle
      if (isFileSystemAccessSupported && $fileStore.saveLocation) {
        isRestoringDirectory = true;
        
        // Attempt to restore the directory handle without showing a picker
        fileStore.restoreDirectoryHandle()
          .then(restored => {
            if (restored) {
              console.log('Successfully restored directory handle on mount');
              // Scan for files in the directory
              const dirHandle = fileStore.getDirectoryHandle();
              if (dirHandle) {
                fileStore.scanDirectoryForFiles(dirHandle)
                  .then(() => {
                    console.log('Directory scan complete after restore');
                  })
                  .catch(scanError => {
                    console.warn('Error scanning directory after restore:', scanError);
                  });
              }
            } else {
              console.log('Could not restore directory handle automatically');
            }
            isRestoringDirectory = false;
          })
          .catch(error => {
            console.error('Error restoring directory handle on mount:', error);
            isRestoringDirectory = false;
          });
      }
    } catch (error) {
      console.error('Error checking File System Access API support:', error);
      isRestoringDirectory = false;
    }
  });
  
  // We no longer refresh files on every afterUpdate
  // Files are only refreshed when:
  // 1. User first logs into Google Drive (handled in the auth subscription)
  // 2. User switches to another file (handled in handleFileClick)
  // 3. User creates a new file (handled in handleNewFile)
  
  onDestroy(() => {
    if (unsubscribeSaveStatus) {
      unsubscribeSaveStatus();
    }
    if (unsubscribeAuth) {
      unsubscribeAuth();
    }
    unsubscribeDocumentTree();
  });
  
  // Export props
  export let editor = null;
</script>

<div class="file-sidebar" class:collapsed={$fileSidebarCollapsed}>
  {#if $fileSidebarCollapsed}
    <!-- Show minimal content when collapsed -->
    <div class="collapsed-content">
      <span class="vertical-text">{$t('sidebar.files')}</span>
    </div>
  {:else}
    <!-- Full sidebar content -->
    <div class="sidebar-container">
      <!-- Tab navigation buttons -->
      <div class="sidebar-tabs">
        <button 
          class="tab-button" 
          class:active={activeTab === 'files'} 
          on:click={() => setActiveTab('files')} 
          title={$t('sidebar.fileList')}
          aria-label={$t('sidebar.fileList')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </button>
        <button 
          class="tab-button" 
          on:click={() => setActiveTab('new')} 
          disabled={!$isAuthenticated} 
          title={$t('file.new')}
          aria-label={$t('file.new')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="18" x2="12" y2="12"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
          </svg>
        </button>
        <button 
          class="tab-button" 
          class:active={activeTab === 'tree'} 
          on:click={() => setActiveTab('tree')} 
          title={$t('sidebar.documentStructure')}
          aria-label={$t('sidebar.documentStructure')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="17" y1="10" x2="3" y2="10"></line>
            <line x1="21" y1="6" x2="3" y2="6"></line>
            <line x1="21" y1="14" x2="3" y2="14"></line>
            <line x1="17" y1="18" x2="3" y2="18"></line>
          </svg>
        </button>
        
        <!-- Spacer to push export buttons to the right -->
        <div style="flex-grow: 1;"></div>
        
        <!-- Export buttons -->
        <button
          class="export-button"
          on:click={() => window.handleExportImages && window.handleExportImages()}
          title={$t('export.toImage')}
          aria-label={$t('export.toImage')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
        </button>
        <button
          class="export-button"
          on:click={() => window.handleExportPDF && window.handleExportPDF()}
          title={$t('export.toPDF')}
          aria-label={$t('export.toPDF')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </button>
      </div>

      <div class="sidebar-header">
        <div class="header-content">
          <h2>{activeTab === 'files' ? $t('sidebar.files') : $t('sidebar.documentStructure')}</h2>
          <AuthStatusManager />
        </div>
      </div>
    
      {#if !isFileSystemAccessSupported}
        <div class="api-warning">
          <p>{$t('file.browserStorageOnly')}</p>
        </div>
      {:else if !$hasFileSystemPermission}
        <div class="api-warning">
          <p>{$t('file.grantPermissionPrompt')}</p>
          <button 
            class="permission-button" 
            on:click={requestFileSystemPermission}
            disabled={isSelectingDirectory || isRestoringDirectory}
          >
            {#if isSelectingDirectory || isRestoringDirectory}
              <span class="loading-spinner"></span>
              {isRestoringDirectory ? $t('file.restoring') : $t('file.selecting')}
            {:else}
              {$t('file.grantPermission')}
            {/if}
          </button>
        </div>
      {:else if $fileStore.saveLocation}
        <div class="save-location">
          <p>{$t('file.currentSaveLocation')}:</p>
          <span class="location-path">Google Drive</span>
        </div>
      {/if}
    
      {#if directorySelectionError}
        <div class="error-message">
          <p>{directorySelectionError}</p>
        </div>
      {/if}
    
      {#if activeTab === 'files'}
        <div class="file-list" role="listbox">
          {#if $fileStore.files.length === 0}
            <div class="empty-state">
              <p>{$t('file.noFilesYet')}</p>
            </div>
          {:else}
            {#each $fileStore.files as file (file.id)}
              <div 
                class="file-item" 
                class:active={$activeFile && $activeFile.id === file.id}
                on:click={() => handleFileClick(file.id)}
                on:keydown={(e) => e.key === 'Enter' && handleFileClick(file.id)}
                role="option"
                tabindex="0"
                aria-selected={$activeFile && $activeFile.id === file.id}
                data-file-id={file.id}
                class:disabled={saveInProgress}
              >
                <div class="file-info">
                  <div class="file-title-row">
                    {#if file.assets && file.assets.length > 0}
                      <button 
                        class="toggle-assets-button"
                        on:click={(e) => {
                          e.stopPropagation();
                          if (expandedFileIds.has(file.id)) {
                            expandedFileIds.delete(file.id);
                          } else {
                            expandedFileIds.add(file.id);
                          }
                          expandedFileIds = expandedFileIds; // Trigger reactivity
                        }}
                        aria-label={expandedFileIds.has(file.id) ? $t('file.hideAssets') : $t('file.showAssets')}
                        title={expandedFileIds.has(file.id) ? $t('file.hideAssets') : $t('file.showAssets')}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          {#if expandedFileIds.has(file.id)}
                            <polyline points="18 15 12 9 6 15"></polyline>
                          {:else}
                            <polyline points="6 9 12 15 18 9"></polyline>
                          {/if}
                        </svg>
                      </button>
                    {/if}
                    <div class="file-title">{file.title || 'Untitled'}</div>
                  </div>
                  <div class="file-meta">
                    <span class="file-date">{formatRelativeTime(file.updatedAt)}</span>
                    {#if file.folderPath}
                      <span class="file-path" title={file.folderPath}>📁 {file.folderPath}</span>
                    {:else if file.path}
                      <span class="file-path" title={file.path}>{file.path}</span>
                    {/if}
                  </div>
                </div>
                <div class="file-actions">
                  <button 
                    class="action-button rename-button" 
                    on:click={(e) => handleRenameFile(e, file.id)}
                    aria-label={$t('file.rename')}
                    title={$t('file.rename')}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                  </button>
                  <button 
                    class="action-button delete-button" 
                    on:click={(e) => handleDeleteFile(e, file.id)}
                    aria-label={$t('file.delete')}
                    title={$t('file.delete')}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </div>
              
              {#if expandedFileIds.has(file.id) && file.assets && file.assets.length > 0}
                <div class="assets-container">
                  <div class="assets-header">{$t('file.assets')} ({file.assets.length})</div>
                  <div class="assets-list">
                    {#each file.assets as asset (asset.id)}
                      <div class="asset-item">
                        <div class="asset-icon">
                          {#if asset.type.startsWith('image/')}
                            🖼️
                          {:else if asset.type.startsWith('video/')}
                            🎬
                          {:else if asset.type.startsWith('audio/')}
                            🎵
                          {:else if asset.type.includes('pdf')}
                            📄
                          {:else if asset.type.includes('document') || asset.type.includes('text/')}
                            📝
                          {:else}
                            📎
                          {/if}
                        </div>
                        <div class="asset-info">
                          <div class="asset-name">{asset.name}</div>
                          <div class="asset-meta">
                            <span class="asset-type">{asset.type}</span>
                            <span class="asset-size">{formatFileSize(asset.size)}</span>
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            {/each}
          {/if}
        </div>
      {:else if activeTab === 'tree'}
        <div class="document-tree-container">
          {#if editor}
            <DocumentTree {editor} />
          {:else}
            <div class="empty-state">
              <p>{$t('sidebar.documentStructureNotAvailable')}</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .file-sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow-y: auto;
    transition: width 0.3s ease;
  }
  
  .file-sidebar.collapsed {
    width: 40px;
    overflow: hidden;
  }
  
  .collapsed-content {
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  .vertical-text {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 1px;
    color: #6c757d;
  }
  
  .sidebar-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
  }
  
  .sidebar-tabs {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem;
    border-bottom: 1px solid #e9ecef;
  }
  
  .tab-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #f8f9fa;
    color: #6c757d;
    border: none;
    border-radius: 0.25rem;
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .tab-button:hover {
    background-color: #e9ecef;
  }
  
  .tab-button.active {
    background-color: #e2e8f0;
    border-color: #cbd5e0;
  }
  
  .sidebar-header {
    padding: 0.5rem;
    border-bottom: 1px solid #e9ecef;
  }
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-content h2 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    color: #495057;
  }
  
  .api-warning {
    padding: 0.75rem;
    background-color: #fff3cd;
    color: #856404;
    font-size: 0.875rem;
    margin: 0.5rem;
    border-radius: 0.25rem;
  }
  
  .permission-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #4a5568;
    color: white;
    border: none;
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    margin-top: 0.5rem;
    width: 100%;
    justify-content: center;
  }
  
  .permission-button:hover {
    background-color: #2d3748;
  }
  
  .save-location {
    padding: 0.75rem;
    background-color: #e6f7ff;
    color: #0c5460;
    font-size: 0.875rem;
    margin: 0.5rem;
    border-radius: 0.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .location-path {
    font-weight: 600;
    word-break: break-all;
  }
  
  /* 删除未使用的 .change-location-button 相关样式 */
  
  .error-message {
    padding: 0.75rem;
    background-color: #f8d7da;
    color: #721c24;
    font-size: 0.875rem;
    margin: 0.5rem;
    border-radius: 0.25rem;
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
  
  .file-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
    width: 100%;
  }
  
  .document-tree-container {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
    width: 100%;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
    text-align: center;
    color: #6c757d;
  }
  
  .file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    border-radius: 0.25rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: background-color 0.2s;
    border: 1px solid transparent;
  }
  
  .file-item:hover {
    background-color: #e9ecef;
  }
  
  .file-item.active {
    background-color: #e2e8f0;
    border-color: #cbd5e0;
  }
  
  .file-item.disabled {
    opacity: 0.6;
    cursor: not-allowed;
    pointer-events: none;
  }
  
  .file-info {
    flex: 1;
    overflow: hidden;
  }
  
  .file-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }
  
  .toggle-assets-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    color: #6c757d;
    transition: color 0.2s;
  }
  
  .toggle-assets-button:hover {
    color: #495057;
  }
  
  .file-title {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .file-meta {
    display: flex;
    flex-direction: column;
    font-size: 0.75rem;
    color: #6c757d;
  }
  
  .file-date {
    margin-right: 0.5rem;
  }
  
  .file-path {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }
  
  .assets-container {
    margin-left: 1rem;
    margin-bottom: 0.75rem;
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-radius: 0.25rem;
    border-left: 3px solid #dee2e6;
  }
  
  .assets-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
  }
  
  .assets-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .asset-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s;
  }
  
  .asset-item:hover {
    background-color: #e9ecef;
  }
  
  .asset-icon {
    font-size: 1rem;
  }
  
  .asset-info {
    flex: 1;
    overflow: hidden;
  }
  
  .asset-name {
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .asset-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    color: #6c757d;
  }
  
  .asset-type {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 60%;
  }
  
  .file-actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .action-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: #6c757d;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    opacity: 0.5;
    transition: opacity 0.2s, background-color 0.2s;
  }
  
  .file-item:hover .action-button {
    opacity: 1;
  }
  
  .rename-button:hover {
    background-color: #e2e8f0;
    color: #2d3748;
  }

  .delete-button:hover {
    background-color: #f8d7da;
    color: #721c24;
  }
  
  .export-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: #495057;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s, color 0.2s;
  }
  
  .export-button:hover {
    background-color: #e9ecef;
    color: #212529;
  }
  
  .export-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
