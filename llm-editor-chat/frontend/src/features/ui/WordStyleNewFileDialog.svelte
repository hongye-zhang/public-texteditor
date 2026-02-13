<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { t } from '$lib/i18n';
  import CreateTemplateDialog from './CreateTemplateDialog.svelte';
  import { templateStore, templates as templateList, userTemplates as userTemplateList, categories as categoryList, isLoading } from '../../stores/templateStore';
  
  // Props
  export let show = false;
  export let editorContent = ''; // Current editor content to use as template
  
  // Event dispatcher
  const dispatch = createEventDispatcher();
  
  // Close the dialog
  function closeDialog() {
    dispatch('close');
  }
  
  // Create a blank document
  function createBlankDocument() {
    dispatch('create-blank');
    closeDialog();
  }
  
  // Handle clicking outside the dialog to close it
  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) {
      closeDialog();
    }
  }
  
  // Close on escape key
  function handleKeydown(event) {
    if (event.key === 'Escape' && show && !showCreateTemplateDialog) {
      closeDialog();
    }
  }
  
  // Categories mapping for the sidebar
  const categoryMapping = [
    { id: 'featured', name: 'dialog.category.featured' },
    { id: 'mytemplates', name: 'dialog.category.mytemplates' },
    { id: 'personal', name: 'dialog.category.personal' },
    { id: 'business', name: 'dialog.category.business' },
    { id: 'education', name: 'dialog.category.education' },
    { id: 'premium', name: 'dialog.category.premium' }
  ];
  
  // Selected category
  let selectedCategory = 'featured';
  
  // Search query
  let searchQuery = '';
  let showCreateTemplateDialog = false;
  
  // Initialize template store on mount
  onMount(() => {
    templateStore.init();
  });
  
  // Open create template dialog
  function openCreateTemplateDialog() {
    // Get the latest editor content from the main editor
    try {
      // Import the main editor to get its content
      import('../editor/components/TiptapEditor.svelte').then(module => {
        if (typeof module.getEditorJSON === 'function') {
          const currentContent = module.getEditorJSON();
          if (currentContent) {
            editorContent = currentContent;
            console.log('Updated editor content for template preview:', editorContent);
          }
        }
        showCreateTemplateDialog = true;
      }).catch(error => {
        console.error('Error importing editor module:', error);
        showCreateTemplateDialog = true;
      });
    } catch (error) {
      console.error('Error getting editor content:', error);
      showCreateTemplateDialog = true;
    }
  }
  
  // Close create template dialog
  function closeCreateTemplateDialog() {
    showCreateTemplateDialog = false;
  }
  
  // Handle save template
  async function handleSaveTemplate(event) {
    const template = event.detail;
    await templateStore.createTemplate(template);
  }
  
  // Use a user template
  async function useTemplate(template) {
    // Record template usage
    await templateStore.useTemplate(template.id);
    dispatch('use-template', template);
    closeDialog();
  }
  
  // Handle category selection
  function handleCategorySelect(categoryId) {
    selectedCategory = categoryId;
    
    if (categoryId !== 'mytemplates') {
      templateStore.setCategory(categoryId === 'featured' ? null : categoryId);
    }
  }
  
  // Handle search
  function handleSearch() {
    if (searchQuery.trim()) {
      templateStore.searchTemplates(searchQuery);
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <div class="modal-backdrop" on:click={handleBackdropClick} role="dialog" aria-modal="true">
    <div class="modal-container">
      <div class="modal-header">
        <h2>{$t('file.new')}</h2>
        <button class="close-button" on:click={closeDialog} aria-label={$t('confirm.cancel')}>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="modal-search">
        <div class="search-container">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="text" 
            placeholder={$t('dialog.searchTemplates')} 
            bind:value={searchQuery}
            class="search-input"
            on:keydown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>
      </div>
      
      <div class="modal-content">
        <div class="sidebar">
          <ul class="category-list">
            {#each categoryMapping as category}
              <li 
                class="category-item" 
                class:active={selectedCategory === category.id}
                on:click={() => handleCategorySelect(category.id)}
              >
                {$t(category.name)}
              </li>
            {/each}
          </ul>
        </div>
        
        <div class="templates-container">
          <div class="section-header">
            <h3 class="section-title">
              {$t(categoryMapping.find(c => c.id === selectedCategory)?.name || 'dialog.category.featured')}
            </h3>
            
            {#if selectedCategory === 'mytemplates'}
              <button class="new-template-button" on:click={openCreateTemplateDialog}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                {$t('dialog.newTemplate')}
              </button>
            {/if}
          </div>
          
          <div class="templates-grid">
            {#if selectedCategory !== 'mytemplates'}
              <!-- Blank document option - only show if not already in template list -->
              {#if !$templateList.some(template => template.id === 'blank')}
              <div class="template-card" on:click={createBlankDocument} role="button" tabindex="0">
                <div class="template-preview blank">
                  <div class="template-content">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="12" y1="18" x2="12" y2="12"></line>
                      <line x1="9" y1="15" x2="15" y2="15"></line>
                    </svg>
                    <p>{$t('dialog.blankDocument')}</p>
                  </div>
                </div>
                <div class="template-metadata">
                  <div class="template-name">{$t('dialog.blankDocument')}</div>
                  <div class="template-info">
                    <div class="template-description">{$t('dialog.startFromScratch')}</div>
                    <div class="template-buttons">
                      <button class="template-button primary">Use Template</button>
                    </div>
                  </div>
                </div>
              </div>
              {/if}
              
              <!-- System templates -->
              {#if $isLoading && $templateList.length === 0}
                <!-- Loading skeleton -->
                {#each Array(6) as _, i}
                  <div class="template-card skeleton">
                    <div class="template-preview">
                      <div class="template-content">
                        <div class="skeleton-line"></div>
                        <div class="skeleton-line"></div>
                        <div class="skeleton-line"></div>
                      </div>
                    </div>
                    <div class="template-metadata">
                      <div class="skeleton-title"></div>
                      <div class="skeleton-info"></div>
                    </div>
                  </div>
                {/each}
              {:else if $templateList.length > 0}
                {#each $templateList as template (template.id)}
                  <div class="template-card" role="button" tabindex="0" on:click={() => useTemplate(template)}>
                    <div class="template-preview">
                      <div class="template-content">
                        {#if template.preview}
                          <img src={template.preview} alt={template.name} />
                        {:else}
                          <p>{template.name}</p>
                          <p>Created from prompt: "{template.prompt.substring(0, 50)}..."</p>
                        {/if}
                      </div>
                    </div>
                    <div class="template-metadata">
                      <div class="template-name">{template.name}</div>
                      <div class="template-info">
                        <div class="template-description">
                          {#if template.use_count}
                            <span class="template-stats">Used {template.use_count} times</span>
                          {/if}
                          {#if template.avg_rating}
                            <span class="template-stats">Rating: {template.avg_rating.toFixed(1)}/5</span>
                          {/if}
                        </div>
                        <div class="template-buttons">
                          <button class="template-button primary">Use Template</button>
                        </div>
                      </div>
                    </div>
                  </div>
                {/each}
              {:else}
                <div class="empty-templates">
                  <p>{$t('dialog.noTemplatesFound')}</p>
                </div>
              {/if}
            {/if}
            
            {#if selectedCategory === 'mytemplates'}
              <!-- User templates -->
              {#if $userTemplateList.length > 0}
                {#each $userTemplateList as template (template.id)}
                  <div class="template-card" role="button" tabindex="0" on:click={() => useTemplate(template)}>
                    <div class="template-preview">
                      <div class="template-content">
                        {#if template.preview}
                          <img src={template.preview} alt={template.name} />
                        {:else}
                          <p>{template.name}</p>
                          <p>Created from prompt: "{template.prompt.substring(0, 50)}..."</p>
                        {/if}
                      </div>
                    </div>
                    <div class="template-metadata">
                      <div class="template-name">{template.name}</div>
                      <div class="template-info">
                        <span>{new Date(template.createdAt).toLocaleDateString()}</span>
                        {#if template.category}
                          <span>• {template.category}</span>
                        {/if}
                      </div>
                      <div class="template-hover-content">
                        {#if template.requiredFields && template.requiredFields.length > 0}
                          <div class="template-required">Required: {template.requiredFields.join(', ')}</div>
                        {/if}
                        <div class="template-buttons">
                          <button class="template-button primary">Use Template</button>
                        </div>
                      </div>
                    </div>
                  </div>
                {/each}
              {:else}
                <div class="empty-templates">
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                  <p>{$t('dialog.noTemplates')}</p>
                  <button class="primary-button" on:click={openCreateTemplateDialog}>
                    {$t('dialog.createFirstTemplate')}
                  </button>
                </div>
              {/if}
            {:else}
              <!-- Business Email Template -->
              <div class="template-card" role="button" tabindex="0">
                <div class="template-preview">
                  <div class="template-content">
                    <p><strong>Subject:</strong> Following up on our meeting</p>
                    <p>Hi [Name],</p>
                    <p>I hope this email finds you well. I wanted to follow up on our meeting last week about [topic].</p>
                    <p>As discussed, I've attached the [document] for your review.</p>
                  </div>
                </div>
                <div class="template-metadata">
                  <div class="template-name">Business Email</div>
                  <div class="template-info">
                    <span>★★★★☆</span>
                    <span>📧</span>
                    <span>Used 1.2k times</span>
                  </div>
                  <div class="template-hover-content">
                    <div class="template-required">Required: Name, Topic, Document</div>
                    <div class="template-buttons">
                      <button class="template-button">Preview</button>
                      <button class="template-button primary">Use Template</button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Report Template -->
              <div class="template-card" role="button" tabindex="0">
                <div class="template-preview">
                  <div class="template-content">
                    <h1>Quarterly Report</h1>
                    <h2>Executive Summary</h2>
                    <p>This report provides an overview of our performance during Q3 2023.</p>
                    <p>Key metrics:</p>
                    <ul>
                      <li>Revenue: $1.2M</li>
                      <li>Growth: 15%</li>
                    </ul>
                  </div>
                </div>
                <div class="template-metadata">
                  <div class="template-name">Quarterly Report</div>
                  <div class="template-info">
                    <span>★★★★★</span>
                    <span>📊</span>
                    <span>Used 876 times</span>
                  </div>
                  <div class="template-hover-content">
                    <div class="template-required">Required: Quarter, Year, Metrics</div>
                    <div class="template-buttons">
                      <button class="template-button">Preview</button>
                      <button class="template-button primary">Use Template</button>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
            
            {#if selectedCategory !== 'mytemplates'}
              <!-- Skeleton loading cards -->
              {#each Array(3) as _}
                <div class="template-card skeleton" role="presentation">
                  <div class="template-preview">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line"></div>
                  </div>
                  <div class="template-metadata">
                    <div class="skeleton-title"></div>
                    <div class="skeleton-info"></div>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<CreateTemplateDialog 
  show={showCreateTemplateDialog} 
  on:close={closeCreateTemplateDialog}
  editorContent={editorContent}
  on:save={handleSaveTemplate}
/>

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
    background-color: white;
    border-radius: 8px;
    width: 80%;
    max-width: 900px;
    height: 80%;
    max-height: 600px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
  
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid #e0e0e0;
  }
  
  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
  
  .close-button {
    background: none;
    border: none;
    cursor: pointer;
    color: #666;
    padding: 4px;
    border-radius: 4px;
  }
  
  .close-button:hover {
    background-color: #f0f0f0;
  }
  
  .modal-search {
    padding: 16px 24px;
    border-bottom: 1px solid #e0e0e0;
  }
  
  .search-container {
    display: flex;
    align-items: center;
    background-color: #f5f5f5;
    border-radius: 4px;
    padding: 8px 12px;
  }
  
  .search-icon {
    color: #666;
    margin-right: 8px;
  }
  
  .search-input {
    border: none;
    background: none;
    outline: none;
    width: 100%;
    font-size: 14px;
  }
  
  .modal-content {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
  
  .sidebar {
    width: 200px;
    border-right: 1px solid #e0e0e0;
    overflow-y: auto;
  }
  
  .category-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  .category-item {
    padding: 12px 16px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .category-item:hover {
    background-color: #f5f5f5;
  }
  
  .category-item.active {
    background-color: #e6f7ff;
    color: #1890ff;
    font-weight: 500;
  }
  
  .templates-container {
    flex: 1;
    padding: 16px 24px;
    overflow-y: auto;
  }
  
  .section-title {
    margin-top: 0;
    margin-bottom: 16px;
    font-size: 16px;
    font-weight: 500;
  }
  
  .templates-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    background-color: #F9FAFB;
    padding: 16px;
    border-radius: 8px;
  }
  
  .template-card {
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    background-color: white;
    border: 1px solid #E5E7EB;
    display: flex;
    flex-direction: column;
    height: 380px;
  }
  
  .template-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    border-color: #d0d5dd;
  }
  
  .template-preview {
    height: 65%;
    background-color: #f0f0f0;
    display: flex;
    flex-direction: column;
    padding: 16px;
    position: relative;
    overflow: hidden;
    color: #333;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  }
  
  .template-preview.blank {
    background-color: #e6f7ff;
    color: #1890ff;
  }
  
  .template-preview::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 40px;
    background: linear-gradient(to bottom, transparent, rgba(240, 240, 240, 0.9));
    pointer-events: none;
  }
  
  .template-preview.blank::after {
    background: linear-gradient(to bottom, transparent, rgba(230, 247, 255, 0.9));
  }
  
  .template-content {
    font-size: 14px;
    line-height: 1.5;
  }
  
  .template-metadata {
    height: 35%;
    padding: 16px;
    border-top: 1px solid #E5E7EB;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  
  .template-name {
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 4px;
  }
  
  .template-info {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #666;
  }
  
  .template-hover-content {
    display: none;
    margin-top: 8px;
  }
  
  .template-card:hover .template-hover-content {
    display: block;
  }
  
  .template-required {
    font-size: 12px;
    color: #666;
    margin-bottom: 8px;
  }
  
  .template-buttons {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
  
  .template-button {
    background: none;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .template-button:hover {
    background-color: #f5f5f5;
  }
  
  .template-button.primary {
    background-color: #1890ff;
    color: white;
    border-color: #1890ff;
  }
  
  .template-button.primary:hover {
    background-color: #40a9ff;
    border-color: #40a9ff;
  }
  
  /* Skeleton loading styles */
  .template-card.skeleton {
    cursor: default;
  }
  
  .skeleton-line {
    height: 14px;
    background-color: #e0e0e0;
    border-radius: 4px;
    margin-bottom: 12px;
    animation: shimmer 1.5s infinite linear;
    background-image: linear-gradient(90deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);
    background-size: 200% 100%;
  }
  
  .skeleton-line:nth-child(2) {
    width: 85%;
  }
  
  .skeleton-line:nth-child(3) {
    width: 70%;
  }
  
  .skeleton-title {
    height: 16px;
    width: 70%;
    background-color: #e0e0e0;
    border-radius: 4px;
    margin-bottom: 8px;
    animation: shimmer 1.5s infinite linear;
    background-image: linear-gradient(90deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);
    background-size: 200% 100%;
  }
  
  .skeleton-info {
    height: 12px;
    width: 90%;
    background-color: #e0e0e0;
    border-radius: 4px;
    animation: shimmer 1.5s infinite linear;
    background-image: linear-gradient(90deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);
    background-size: 200% 100%;
  }
  
  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }
  
  .placeholder {
    opacity: 0.7;
  }
  
  /* Dark mode support */
  .empty-templates {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 64px 0;
    text-align: center;
    color: #888;
  }
  
  .empty-templates svg {
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  .empty-templates p {
    margin-bottom: 24px;
  }
  
  .primary-button {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .primary-button:hover {
    background-color: #40a9ff;
  }
  
  @media (prefers-color-scheme: dark) {
    .modal-container {
      background-color: #1f1f1f;
      color: #e0e0e0;
    }
    
    .modal-header {
      border-bottom-color: #333;
    }
    
    .close-button {
      color: #ccc;
    }
    
    .close-button:hover {
      background-color: #333;
    }
    
    .modal-search {
      border-bottom-color: #333;
    }
    
    .search-container {
      background-color: #333;
    }
    
    .search-input {
      color: #e0e0e0;
    }
    
    .sidebar {
      border-right-color: #333;
    }
    
    .category-item:hover {
      background-color: #2a2a2a;
    }
    
    .category-item.active {
      background-color: #177ddc22;
      color: #177ddc;
    }
    
    .templates-grid {
      background-color: #1a1a1a;
    }
    
    .template-card {
      background-color: #2a2a2a;
      border-color: #444;
    }
    
    .template-preview {
      background-color: #333;
      color: #e0e0e0;
    }
    
    .template-preview.blank {
      background-color: #177ddc22;
      color: #177ddc;
    }
    
    .template-preview::after {
      background: linear-gradient(to bottom, transparent, rgba(51, 51, 51, 0.9));
    }
    
    .template-preview.blank::after {
      background: linear-gradient(to bottom, transparent, rgba(23, 125, 220, 0.1));
    }
    
    .new-template-button {
      background-color: #177ddc;
    }
    
    .new-template-button:hover {
      background-color: #3c9ae8;
    }
    
    .empty-templates {
      color: #aaa;
    }
    
    .primary-button {
      background-color: #177ddc;
    }
    
    .primary-button:hover {
      background-color: #3c9ae8;
    }
    
    .template-metadata {
      border-top-color: #444;
    }
    
    .template-info {
      color: #aaa;
    }
  }
</style>
