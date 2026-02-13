<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher();
  
  export let newMessage = '';
  export let selectedFile: File | null = null;
  export let filePreview: string | null = null;
  
  let fileInput: HTMLInputElement;
  
  // Handle key press for sending messages
  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      dispatch('send');
    }
  }
  
  // Handle file upload
  function handleFileUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) {
      selectedFile = null;
      filePreview = null;
      return;
    }
    
    selectedFile = input.files[0];
    
    // 如果是图片，创建预览
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        filePreview = e.target?.result as string;
      };
      reader.readAsDataURL(selectedFile);
    } else {
      // 非图片文件，显示文件名
      filePreview = null;
    }
  }
  
  // 清除选中的文件
  function clearSelectedFile() {
    selectedFile = null;
    filePreview = null;
    if (fileInput) {
      fileInput.value = '';
    }
    dispatch('clearFile');
  }
</script>

<div class="chat-input-card">
  <div class="input-area">
    {#if filePreview && selectedFile?.type.startsWith('image/')}
      <div class="file-preview">
        <img src={filePreview} alt="文件预览" />
        <button class="remove-file" on:click={clearSelectedFile} aria-label="移除文件">
          <i class="fas fa-times"></i>
        </button>
      </div>
    {:else if selectedFile}
      <div class="file-preview file-item">
        <i class="fas fa-file"></i>
        <span class="file-name">{selectedFile.name}</span>
        <button class="remove-file" on:click={clearSelectedFile} aria-label="移除文件">
          <i class="fas fa-times"></i>
        </button>
      </div>
    {/if}
    <textarea 
      bind:value={newMessage} 
      on:keydown={handleKeyPress}
      placeholder="输入消息..."
      rows="1"
    ></textarea>
  </div>
  <div class="button-bar">
    <input 
      type="file"
      bind:this={fileInput}
      on:change={handleFileUpload}
      style="display: none;"
      accept="image/*,.pdf,.doc,.docx,.txt"
    />
    <button 
      class="attachment-button"
      on:click={() => fileInput.click()}
      aria-label="添加附件"
    >
      <i class="fas fa-plus"></i>
    </button>
    <button 
      class="send-button"
      on:click={() => dispatch('send')}
      disabled={!newMessage.trim() && !selectedFile}
      aria-label="发送消息"
    >
      <i class="fas fa-arrow-up"></i>
    </button>
  </div>
</div>
