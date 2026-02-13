<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { t } from '../../../lib/i18n';
  import { getContext } from 'svelte';
  import { logger } from '../../../lib/debug/logger';
  
  // Define the editor context type
  interface EditorContext {
    acceptAllPendingRevisions?: () => void;
  }
  
  const dispatch = createEventDispatcher();
  const CHAT_MESSAGE_KEY = 'unsentChatMessage'; // Key for localStorage
  
  // Get editor instance from context if available
  const editorContext = getContext<EditorContext>('editor') || {};
  
  export let newMessage = '';
  export let selectedFiles: File[] = [];
  export let filePreviews: Map<string, string> = new Map();
  
  // 文本框展开状态
  let isExpanded = false;
  
  // 文件上传限制
  const MAX_FILES = 16; // 最多允许16个文件
  const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB
  
  // 错误消息
  let errorMessage = '';
  let showError = false;
  let errorTimeout: ReturnType<typeof setTimeout> | null = null;
  
  let fileInput: HTMLInputElement;

  // Load message from localStorage on component mount
  onMount(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      const savedMessage = localStorage.getItem(CHAT_MESSAGE_KEY);
      if (savedMessage) {
        newMessage = savedMessage;
      }
    }
  });

  // Save message to localStorage whenever it changes
  $: {
    if (typeof window !== 'undefined' && window.localStorage) {
      if (newMessage && newMessage.trim() !== '') {
        localStorage.setItem(CHAT_MESSAGE_KEY, newMessage);
      } else {
        // Clear from localStorage if message is empty (e.g., after sending or cleared by user)
        localStorage.removeItem(CHAT_MESSAGE_KEY);
      }
    }
  }
  
  // Handle key press for sending messages
  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      // 只有在非展开状态下，Enter键才触发发送
      if (!isExpanded) {
        event.preventDefault();
        // Accept all pending revisions before sending
        acceptPendingRevisions();
        dispatch('send');
      }
      // 在展开状态下，Enter键正常插入换行，不需要特殊处理
    }
  }
  
  function acceptPendingRevisions() {
    // Try to get editor instance from context
    if (typeof editorContext.acceptAllPendingRevisions === 'function') {
      const result = editorContext.acceptAllPendingRevisions();
    } else {
      // Log that we couldn't find the method
      logger.error('ChatInput: Could not find acceptAllPendingRevisions method in editor context');
    }
  }
  
  // 显示错误消息的函数
  function showErrorMessage(message: string) {
    errorMessage = message;
    showError = true;
    
    // 5秒后自动隐藏错误消息
    if (errorTimeout) {
      clearTimeout(errorTimeout);
    }
    
    errorTimeout = setTimeout(() => {
      showError = false;
      errorMessage = '';
    }, 5000);
  }
  
  // Handle file upload
  function handleFileUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) {
      return;
    }
    
    // 将FileList转换为数组
    const newFiles = Array.from(input.files);
    
    // 检查文件数量限制
    if (selectedFiles.length + newFiles.length > MAX_FILES) {
      showErrorMessage($t('chat.maxFilesError', { max: MAX_FILES, current: selectedFiles.length }));
      if (fileInput) {
        fileInput.value = '';
      }
      return;
    }
    
    // 检查文件大小限制
    const oversizedFiles = newFiles.filter(file => file.size > MAX_FILE_SIZE);
    if (oversizedFiles.length > 0) {
      const fileNames = oversizedFiles.map(f => f.name).join(', ');
      showErrorMessage($t('chat.fileSizeError', { files: fileNames, size: '25MB' }));
      if (fileInput) {
        fileInput.value = '';
      }
      return;
    }
    
    // 添加到已选文件列表
    selectedFiles = [...selectedFiles, ...newFiles];
    
    // 为每个文件生成唯一ID并存储到文件对象上
    newFiles.forEach(file => {
      // 为文件添加一个唯一ID属性
      (file as any).uniqueId = `${file.name}-${file.size}-${Date.now()}`;
      
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          filePreviews.set((file as any).uniqueId, e.target?.result as string);
          filePreviews = new Map(filePreviews); // 触发Svelte更新
        };
        reader.readAsDataURL(file);
      } else {
        // 非图片文件不需要预览
        filePreviews.set((file as any).uniqueId, '');
        filePreviews = new Map(filePreviews); // 触发Svelte更新
      }
    });
    
    // 清空input的value，允许再次选择相同的文件
    if (fileInput) {
      fileInput.value = '';
    }
  }
  
  // 清除所有选中的文件
  function clearAllFiles() {
    selectedFiles = [];
    filePreviews = new Map();
    if (fileInput) {
      fileInput.value = '';
    }
    dispatch('clearFile');
  }
  
  // 移除单个文件
  function removeFile(index: number) {
    const fileToRemove = selectedFiles[index];
    
    // 移除文件和预览
    selectedFiles = selectedFiles.filter((_, i) => i !== index);
    
    // 如果没有文件了，通知父组件
    if (selectedFiles.length === 0) {
      dispatch('clearFile');
    }
  }
  
  // 切换输入框的展开/收起状态
  function toggleExpand() {
    isExpanded = !isExpanded;
    
    // 获取文本区域元素
    const textarea = document.getElementById('chat-input-textarea') as HTMLTextAreaElement;
    const buttonBar = document.querySelector('.button-bar') as HTMLElement;
    
    if (textarea) {
      if (isExpanded) {
        // 展开状态：设置更大的高度
        textarea.style.minHeight = '30rem';
        textarea.style.maxHeight = '50rem';
        
        // 确保按钮栏在展开状态下保持可见
        if (buttonBar) {
          buttonBar.style.position = 'sticky';
          buttonBar.style.bottom = '0';
          buttonBar.style.backgroundColor = 'white';
          buttonBar.style.zIndex = '10';
        }
      } else {
        // 恢复默认高度
        textarea.style.minHeight = '2.5rem';
        textarea.style.maxHeight = '10rem';
        
        // 恢复按钮栏的默认样式
        if (buttonBar) {
          buttonBar.style.position = '';
          buttonBar.style.bottom = '';
          buttonBar.style.backgroundColor = '';
          buttonBar.style.zIndex = '';
        }
      }
      
      // 聚焦到文本区域
      textarea.focus();
    }
  }
</script>

<div class="chat-input-card">
  {#if showError}
    <div class="error-message">
      <i class="fas fa-exclamation-circle"></i>
      <span>{errorMessage}</span>
      <button class="close-error" on:click={() => showError = false} aria-label={$t('chat.closeError')}>
        <i class="fas fa-times"></i>
      </button>
    </div>
  {/if}
  
  <div class="input-area">
    {#if selectedFiles.length > 0}
      <div class="file-previews-container">
        {#each selectedFiles as file, index}
          <div class="file-preview-item" title={file.name}>
            {#if file.type.startsWith('image/')}
              {#if filePreviews.get((file as any).uniqueId)}
                <div class="file-preview">
                  <img src={filePreviews.get((file as any).uniqueId)} alt={$t('chat.filePreview')} />
                </div>
              {:else}
                <div class="file-preview loading">
                  <i class="fas fa-image"></i>
                </div>
              {/if}
            {:else}
              <div class="file-preview file-item">
                <i class="fas fa-file"></i>
                <span class="file-name">{file.name.length > 10 ? file.name.substring(0, 10) + '...' : file.name}</span>
              </div>
            {/if}
            <button class="remove-file" on:click={() => removeFile(index)} aria-label={$t('chat.removeFile')}>
              <i class="fas fa-times"></i>
            </button>
          </div>
        {/each}
      </div>
    {/if}
    <textarea
      id="chat-input-textarea"
      class="chat-input"
      placeholder={$t('chat.placeholder')}
      bind:value={newMessage}
      on:keydown={handleKeyPress}
      on:input={() => acceptPendingRevisions()}
      rows="1"
      style="min-height: 2.5rem; max-height: 10rem;"
    ></textarea>
  </div>
  <div class="button-bar">
    <input 
      type="file"
      bind:this={fileInput}
      on:change={handleFileUpload}
      style="display: none;"
      accept="image/*,.pdf,.doc,.docx,.txt"
      multiple
    />
    <button 
      class="attachment-button"
      on:click={() => fileInput.click()}
      aria-label={$t('chat.attachFile')}
    >
      <i class="fas fa-plus"></i>
    </button>
    <div style="flex-grow: 1;"></div>
    <button 
      class="expand-button"
      on:click={toggleExpand}
      aria-label={isExpanded ? $t('chat.shrinkInput') : $t('chat.expandInput')}
      class:expanded={isExpanded}
    >
      <i class="fas {isExpanded ? 'fa-compress-alt' : 'fa-expand-alt'}"></i>
    </button>
    <button 
      class="send-button"
      on:click={() => {
        acceptPendingRevisions();
        dispatch('send');
      }}
      disabled={!newMessage.trim() && selectedFiles.length === 0}
      aria-label={$t('chat.send')}
    >
      <i class="fas fa-arrow-up"></i>
    </button>
  </div>
</div>

<style>
  .error-message {
    background-color: #fee2e2;
    color: #b91c1c;
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    font-size: 0.85rem;
  }
  
  .error-message i {
    margin-right: 8px;
  }
  
  .error-message .close-error {
    margin-left: auto;
    background: none;
    border: none;
    color: #b91c1c;
    cursor: pointer;
    padding: 0;
    font-size: 0.85rem;
  }
  
  .file-previews-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
    max-height: 120px;
    overflow-y: auto;
  }
  
  .file-preview-item {
    position: relative;
    width: 80px;
    height: 80px;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #ddd;
    background-color: #f9f9f9;
  }
  
  .file-preview {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .file-preview img {
    max-width: 100%;
    max-height: 100%;
    object-fit: cover;
  }
  
  .file-preview.loading {
    background-color: #f0f0f0;
  }
  
  .file-preview.file-item {
    flex-direction: column;
    font-size: 0.8rem;
  }
  
  .file-preview.file-item i {
    font-size: 1.5rem;
    margin-bottom: 4px;
  }
  
  .file-name {
    font-size: 0.7rem;
    max-width: 70px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .remove-file {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: rgba(0, 0, 0, 0.5);
    color: white;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.7rem;
    padding: 0;
  }
  
  .remove-file:hover {
    background-color: rgba(0, 0, 0, 0.7);
  }
</style>
