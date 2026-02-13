<script lang="ts">
  import { createEventDispatcher, onMount, afterUpdate } from 'svelte';
  import { t } from '$lib/i18n';
  import { templateStore } from '../../stores/templateStore';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import EditorContent from '../../features/editor/components/EditorContent.svelte';
  
  // Check if we're running in Electron
  const isElectron = typeof window !== 'undefined' && window.environment && window.environment.isElectron;

  // Props
  export let show = false;
  export let editorContent = ''; // Current editor content to use as template

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Preview editor instance
  let previewEditor: Editor | null = null;
  let previewElement: HTMLElement | null = null;
  
  // Initialize preview editor when dialog is shown
  $: if (show && previewElement) {
    initPreviewEditor();
    if (isElectron) {
      loadTemplatesDirectory();
    }
  }
  
  // Initialize the preview editor with read-only mode
  function initPreviewEditor() {
    console.log('Initializing preview editor, element exists:', !!previewElement);
    
    // Ensure we have a preview element
    if (!previewElement) {
      console.error('Preview element is not available');
      return;
    }
    
    // Destroy existing editor if it exists
    if (previewEditor) {
      previewEditor.destroy();
      previewEditor = null;
    }
    
    try {
      // Parse the editor content
      let content;
      
      if (editorContent && editorContent.trim()) {
        console.log('Editor content available:', typeof editorContent, editorContent.substring(0, 100) + '...');
        
        try {
          // Try to parse as JSON first
          content = JSON.parse(editorContent);
          console.log('Successfully parsed editor content as JSON');
        } catch (e) {
          console.log('Failed to parse as JSON, trying as HTML:', e);
          
          // If it's not valid JSON, check if it looks like HTML
          if (typeof editorContent === 'string' && editorContent.trim().startsWith('<')) {
            // It's likely HTML content
            content = editorContent;
            console.log('Using editor content as HTML');
          } else {
            // Use a fallback document structure
            content = {
              type: 'doc',
              content: [
                {
                  type: 'paragraph',
                  content: [
                    {
                      type: 'text',
                      text: editorContent || 'No content available'
                    }
                  ]
                }
              ]
            };
            console.log('Using fallback content structure with text');
          }
        }
      } else {
        // No content available, use a placeholder
        content = {
          type: 'doc',
          content: [
            {
              type: 'paragraph',
              content: [{ type: 'text', text: 'No content available' }]
            }
          ]
        };
        console.log('No editor content, using placeholder');
      }
      
      console.log('Creating preview editor with content');
      
      // Create the editor with appropriate extensions
      previewEditor = new Editor({
        element: previewElement,
        extensions: [StarterKit],
        content: content,
        editable: false, // Make it read-only
      });
      
      // Force update the editor content to ensure it's visible
      setTimeout(() => {
        if (previewEditor) {
          // Force a content update
          previewEditor.commands.focus();
          previewEditor.commands.blur();
          
          console.log('Preview editor initialized and content updated');
        }
      }, 100);
    } catch (error) {
      console.error('Error initializing preview editor:', error);
    }
  }
  
  // Load templates directory
  async function loadTemplatesDirectory() {
    if (isElectron && window.electronAPI) {
      console.log('Electron API available:', window.electronAPI);
      console.log('FileSystem API:', window.electronAPI.fileSystem);
      console.log('Available methods:', Object.keys(window.electronAPI.fileSystem || {}));
      
      if (window.electronAPI.fileSystem) {
        try {
          templatesDirectory = await window.electronAPI.fileSystem.getTemplatesDirectory();
          console.log('Templates directory:', templatesDirectory);
        } catch (error) {
          console.error('Error loading templates directory:', error);
        }
      }
    }
  }
  
  // Change templates directory
  async function changeTemplatesDirectory() {
    console.log('Change templates directory clicked');
    if (!isElectron) {
      console.log('Not running in Electron');
      return;
    }
    
    isChangingDirectory = true;
    
    try {
      // Use the openFolder method instead, which should be available
      if (window.electronAPI && window.electronAPI.fileSystem && window.electronAPI.fileSystem.openFolder) {
        console.log('Using openFolder method...');
        const folderPath = await window.electronAPI.fileSystem.openFolder();
        
        if (folderPath) {
          // Now set this as the templates directory
          console.log('Selected folder:', folderPath);
          
          // Use setDefaultSaveDirectory as a workaround if available
          if (window.electronAPI.fileSystem.setDefaultSaveDirectory) {
            await window.electronAPI.fileSystem.setDefaultSaveDirectory(folderPath);
          }
          
          // Update the displayed path
          templatesDirectory = folderPath;
          console.log('Templates directory changed to:', templatesDirectory);
          
          // Reload templates from the new location
          await templateStore.loadTemplates();
        } else {
          console.log('Folder selection was canceled');
        }
      } else {
        console.error('openFolder method not available');
      }
    } catch (error) {
      console.error('Error changing templates directory:', error);
    } finally {
      isChangingDirectory = false;
    }
  }
  
  // Handle preview element ready
  function handlePreviewElementReady(event: CustomEvent<{ element: HTMLElement }>) {
    previewElement = event.detail.element;
    console.log('Preview element ready:', previewElement);
    // Always initialize the preview editor when the element is ready and dialog is shown
    if (show) {
      setTimeout(() => initPreviewEditor(), 0); // Use setTimeout to ensure DOM is ready
    }
  }
  
  // Clean up editor on dialog close
  $: if (!show && previewEditor) {
    previewEditor.destroy();
    previewEditor = null;
  }

  // Template data
  let templateName = '';
  let selectedCategory = '';
  let requiredInfo = '';
  let visibility = 'private'; // Default to private
  let isSaving = false;
  let templatesDirectory = '';
  let isChangingDirectory = false;
  
  // Get categories from the template store
  $: categories = $templateStore.categories.map(category => ({ 
    id: category, 
    name: category.charAt(0).toUpperCase() + category.slice(1) 
  }));
  
  // Add default categories if none exist in the store
  $: {
    if (categories.length === 0) {
      categories = [
        { id: 'business', name: 'Business' },
        { id: 'personal', name: 'Personal' },
        { id: 'education', name: 'Education' },
        { id: 'marketing', name: 'Marketing' },
        { id: 'legal', name: 'Legal' },
        { id: 'technical', name: 'Technical' }
      ];
    }
  }
  
  // Close the dialog
  function closeDialog() {
    resetForm();
    dispatch('close');
  }
  
  // Reset form data
  function resetForm() {
    templateName = '';
    selectedCategory = '';
    requiredInfo = '';
    visibility = 'private';
  }
  
  // Handle clicking outside the dialog to close it
  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) {
      closeDialog();
    }
  }
  
  // Close on escape key
  function handleKeydown(event) {
    if (event.key === 'Escape' && show) {
      closeDialog();
    }
  }
  
  // Save template
  async function saveTemplate() {
    if (!templateName.trim() || !editorContent.trim()) return;
    
    isSaving = true;
    
    try {
      const template = {
        name: templateName.trim(),
        prompt: '', // Empty prompt as we're using editor content directly
        category: selectedCategory || 'general',
        required_fields: requiredInfo.split(',').map(field => field.trim()).filter(Boolean),
        preview_content: editorContent.trim(), // Use editor content as preview
        content: editorContent.trim(), // Store the actual editor content
        visibility: visibility
      };
      
      await templateStore.createTemplate(template);
      closeDialog();
    } catch (error) {
      console.error('Error saving template:', error);
    } finally {
      isSaving = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <div class="modal-backdrop" on:click={handleBackdropClick} role="dialog" aria-modal="true">
    <div class="modal-container">
      <div class="modal-header">
        <h2>{$t('dialog.createTemplate')}</h2>
        <button class="close-button" on:click={closeDialog} aria-label={$t('confirm.cancel')}>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="modal-content">
        <div class="form-container">
          <div class="form-section">
            <label for="template-name">
              {$t('dialog.templateName')}
            </label>
            <input 
              id="template-name"
              type="text" 
              bind:value={templateName}
              placeholder="e.g., Sales Follow-up Email"
              class="form-input"
            />
          </div>
          
          <div class="form-section">
            <label for="template-category">
              {$t('dialog.category')} ({$t('common.optional')})
            </label>
            <div class="category-buttons">
              {#each categories as category}
                <button 
                  class="category-button" 
                  class:selected={selectedCategory === category.id}
                  on:click={() => selectedCategory = category.id}
                >
                  {category.id === 'business' || category.id === 'personal' || category.id === 'education' 
                    ? $t(category.name) 
                    : category.name}
                </button>
              {/each}
            </div>
          </div>
          
          <div class="form-section">
            <label for="template-required-info">
              {$t('dialog.requiredInfo')} ({$t('common.optional')})
            </label>
            <input
              id="template-required-info"
              bind:value={requiredInfo}
              placeholder="e.g., Company Name, Product, Meeting Date"
              class="form-input"
            />
            <small class="form-hint">{$t('dialog.requiredInfoHint')}</small>
          </div>
          
          <div class="form-section">
            <label class="visibility-label">
              {$t('dialog.visibility')}
            </label>
            <div class="radio-options">
              <label class="radio-label">
                <input type="radio" bind:group={visibility} value="private" />
                <span>{$t('dialog.private')}</span>
                <small>{$t('dialog.privateHint')}</small>
              </label>
              <label class="radio-label">
                <input type="radio" bind:group={visibility} value="public" />
                <span>{$t('dialog.public')}</span>
                <small>{$t('dialog.publicHint')}</small>
              </label>
            </div>
          </div>
          
          {#if isElectron && visibility === 'private'}
            <div class="form-section storage-location">
              <label>
                Storage Location
              </label>
              <div class="storage-path">
                <span class="path-text" title={templatesDirectory}>{templatesDirectory || 'Loading...'}</span>
                <button 
                  type="button" 
                  class="change-location-button" 
                  on:click={changeTemplatesDirectory}
                  disabled={isChangingDirectory}
                >
                  {isChangingDirectory ? 'Changing...' : 'Change Location'}
                </button>
              </div>
              <small class="form-hint">Private templates will be saved to this location</small>
            </div>
          {/if}
        </div>
        
        <div class="preview-container">
          <div class="preview-header">
            <h3>{$t('dialog.preview')}</h3>
            <p class="preview-info">{$t('dialog.currentEditorContent')}</p>
          </div>
          
          <div class="preview-content">
            <div class="preview-document">
              <EditorContent on:elementReady={handlePreviewElementReady} />
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeDialog}>{$t('confirm.cancel')}</button>
        <button 
          class="save-button" 
          on:click={saveTemplate} 
          disabled={!templateName.trim() || !editorContent.trim() || isSaving}
        >
          {isSaving ? 
            `<div class="spinner-small"></div> ${$t('common.saving')}` : 
            $t('common.save')}
        </button>
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
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  
  .modal-container {
    width: 90%;
    max-width: 1000px;
    max-height: 90vh;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  
  .modal-header {
    padding: 16px 24px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 500;
  }
  
  .close-button {
    background: none;
    border: none;
    cursor: pointer;
    color: #999;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .close-button:hover {
    background-color: #f5f5f5;
    color: #666;
  }
  
  .modal-content {
    padding: 0;
    display: flex;
    overflow: auto;
    flex: 1;
  }
  
  .form-container {
    width: 50%;
    padding: 24px;
    border-right: 1px solid #f0f0f0;
    overflow-y: auto;
  }
  
  .preview-container {
    width: 50%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  
  .form-section {
    margin-bottom: 20px;
  }
  
  .form-section label {
    display: block;
    font-weight: 500;
    margin-bottom: 8px;
  }
  
  .form-input, .preview-document {
    height: 100%;
    overflow-y: auto;
    padding: 16px;
    border: 1px solid #f0f0f0;
    border-radius: 4px;
    background-color: white;
  }
  
  /* Ensure TipTap editor content is visible in preview */
  :global(.preview-document .ProseMirror) {
    min-height: 200px;
    padding: 8px;
    outline: none;
    white-space: pre-wrap;
  }
  
  :global(.preview-document .ProseMirror h1) {
    font-size: 1.5em;
    margin-bottom: 0.5em;
  }
  
  :global(.preview-document .ProseMirror p) {
    margin-bottom: 0.5em;
  }
  
  .form-input:focus, .form-textarea:focus {
    border-color: #40a9ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
    outline: none;
  }
  
  .form-textarea {
    resize: vertical;
    min-height: 100px;
  }
  
  .form-hint {
    font-size: 12px;
    color: #888;
    margin-top: 4px;
  }
  
  .visibility-options {
    display: flex;
    gap: 16px;
    margin-top: 8px;
  }
  
  .radio-label {
    display: flex;
    flex-direction: column;
    cursor: pointer;
  }
  
  .radio-label input {
    margin-right: 8px;
  }
  
  .radio-label span {
    font-weight: 500;
    margin-bottom: 4px;
  }
  
  .radio-label small {
    font-size: 12px;
    color: #888;
  }
  
  .storage-location {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px dashed #eee;
  }
  
  .storage-path {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 4px;
  }
  
  .path-text {
    flex: 1;
    background-color: #f5f5f5;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 13px;
    color: #555;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    border: 1px solid #e0e0e0;
  }
  
  .change-location-button {
    background-color: #f0f0f0;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.3s;
  }
  
  .change-location-button:hover {
    border-color: #40a9ff;
    color: #40a9ff;
  }
  
  .change-location-button:disabled {
    background-color: #f5f5f5;
    border-color: #d9d9d9;
    color: #bbb;
    cursor: not-allowed;
  }
  
  .visibility-label {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  .category-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .category-button {
    background: none;
    border: 1px solid #d9d9d9;
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
  }
  
  .category-button:hover {
    border-color: #40a9ff;
    color: #40a9ff;
  }
  
  .category-button.selected {
    background-color: #e6f7ff;
    border-color: #1890ff;
    color: #1890ff;
  }
  
  .preview-header {
    padding: 16px 24px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .preview-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
  }
  
  .preview-button {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
  }
  
  .preview-button:hover {
    background-color: #40a9ff;
  }
  
  .preview-button:disabled {
    background-color: #d9d9d9;
    cursor: not-allowed;
  }
  
  .preview-content {
    flex: 1;
    padding: 24px;
    overflow-y: auto;
    background-color: #f9f9f9;
  }
  
  .preview-placeholder {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #999;
    text-align: center;
  }
  
  .preview-placeholder svg {
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  .preview-loading {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  
  .spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #1890ff;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  .spinner-small {
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top: 2px solid #ffffff;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 8px;
    vertical-align: middle;
  }
  
  .preview-document {
    background-color: white;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    padding: 24px;
    min-height: 300px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
  
  /* Editor content styling for preview */
  :global(.preview-document .editor-content) {
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-radius: 0.25rem;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
    font-size: 0.9rem;
  }
  
  :global(.preview-document .ProseMirror) {
    outline: none;
  }
  
  .preview-markdown {
    white-space: pre-wrap;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
  }
  
  .preview-email .email-subject {
    font-weight: bold;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
    margin-bottom: 16px;
  }
  
  .preview-email .email-body {
    white-space: pre-wrap;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
  }
  
  .modal-footer {
    padding: 16px 24px;
    border-top: 1px solid #f0f0f0;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
  
  .cancel-button {
    background: none;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
  }
  
  .cancel-button:hover {
    border-color: #40a9ff;
    color: #40a9ff;
  }
  
  .save-button {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
  }
  
  .save-button:hover {
    background-color: #40a9ff;
  }
  
  .save-button:disabled {
    background-color: #d9d9d9;
    cursor: not-allowed;
  }
  
  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .modal-container {
      background-color: #1f1f1f;
      color: #e0e0e0;
    }
    
    .modal-header, .preview-header {
      border-bottom-color: #333;
    }
    
    .modal-footer {
      border-top-color: #333;
    }
    
    .form-container {
      border-right-color: #333;
    }
    
    .close-button {
      color: #ccc;
    }
    
    .close-button:hover {
      background-color: #333;
      color: #fff;
    }
    
    .form-input, .form-textarea {
      background-color: #2a2a2a;
      border-color: #444;
      color: #e0e0e0;
    }
    
    .form-input:focus, .form-textarea:focus {
      border-color: #177ddc;
      box-shadow: 0 0 0 2px rgba(23, 125, 220, 0.2);
    }
    
    .form-hint {
      color: #aaa;
    }
    
    .category-button {
      background-color: #2a2a2a;
      border-color: #444;
      color: #e0e0e0;
    }
    
    .category-button:hover {
      border-color: #177ddc;
      color: #177ddc;
    }
    
    .category-button.selected {
      background-color: #111b26;
      border-color: #177ddc;
      color: #177ddc;
    }
    
    .preview-content {
      background-color: #141414;
    }
    
    .preview-document {
      background-color: #1f1f1f;
      border-color: #333;
    }
    
    .preview-email .email-subject {
      border-bottom-color: #333;
    }
    
    .cancel-button {
      border-color: #444;
      color: #e0e0e0;
    }
    
    .cancel-button:hover {
      border-color: #177ddc;
      color: #177ddc;
    }
    
    .preview-button, .save-button {
      background-color: #177ddc;
    }
    
    .preview-button:hover, .save-button:hover {
      background-color: #3c9ae8;
    }
    
    .preview-button:disabled, .save-button:disabled {
      background-color: #444;
    }
    
    .spinner {
      border-color: #333;
      border-top-color: #177ddc;
    }
  }
</style>
