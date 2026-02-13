<script lang="ts">
  import { Editor } from '@tiptap/core';
  import { onMount } from 'svelte';
  
  export let editor: Editor | null = null;
  
  // 文件输入引用
  let fileInput: HTMLInputElement;
  
  // 插入本地图像函数
  function handleImageUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    
    if (!file || !editor) return;
    
    // 检查是否为图片文件
    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件');
      return;
    }
    
    // 文件大小限制 (5MB)
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('图片大小不能超过5MB');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      editor.chain().focus().setImage({ src: dataUrl }).run();
      
      // 清空文件输入，以便可以再次选择同一文件
      input.value = '';
    };
    
    reader.readAsDataURL(file);
  }
  
  // 触发文件选择对话框
  function openFileDialog() {
    fileInput?.click();
  }
  
  // 插入表格函数
  function insertTable() {
    if (!editor) return;
    
    editor.chain()
      .focus()
      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
      .run();
  }
</script>

<div class="editor-toolbar">
  <div class="toolbar-group">
    <!-- 文本格式化 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleBold().run()}
      title="加粗"
      aria-label="加粗"
    >
      <i class="fas fa-bold"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleHighlight().run()}
      title="文本高亮"
      aria-label="文本高亮"
    >
      <i class="fas fa-highlighter"></i>
    </button>
    
    <!-- 段落按钮 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().setParagraph().run()}
      title="普通段落"
      aria-label="普通段落"
    >
      <i class="fas fa-paragraph"></i>
    </button>
  </div>
  
  <div class="toolbar-group">
    <!-- 标题 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
      title="标题1"
      aria-label="标题1"
    >
      <i class="fas fa-heading"></i><span class="heading-level">1</span>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
      title="标题2"
      aria-label="标题2"
    >
      <i class="fas fa-heading"></i><span class="heading-level">2</span>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
      title="标题3"
      aria-label="标题3"
    >
      <i class="fas fa-heading"></i><span class="heading-level">3</span>
    </button>
  </div>
  
  <div class="toolbar-group">
    <!-- 列表 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleBulletList().run()}
      title="无序列表"
      aria-label="无序列表"
    >
      <i class="fas fa-list-ul"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleOrderedList().run()}
      title="有序列表"
      aria-label="有序列表"
    >
      <i class="fas fa-list-ol"></i>
    </button>
  </div>
  
  <div class="toolbar-group">
    <!-- 插入元素 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().setHorizontalRule().run()}
      title="插入水平线"
      aria-label="插入水平线"
    >
      <i class="fas fa-minus"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleBlockquote().run()}
      title="引用"
      aria-label="引用"
    >
      <i class="fas fa-quote-right"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={insertTable}
      title="插入表格"
      aria-label="插入表格"
    >
      <i class="fas fa-table"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={openFileDialog}
      title="插入图像"
      aria-label="插入图像"
    >
      <i class="fas fa-image"></i>
    </button>
    
    <!-- 隐藏的文件输入元素 -->
    <input 
      type="file" 
      bind:this={fileInput}
      on:change={handleImageUpload}
      accept="image/*"
      style="display: none;"
    />
  </div>
</div>

<style>
  .editor-toolbar {
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    padding: 4px;
    background-color: #f8f9fa;
    border-bottom: 1px solid #e2e8f0;
    position: sticky;
    top: 0;
    z-index: 10;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none; /* Firefox */
  }
  
  .editor-toolbar::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Edge */
  }
  
  .toolbar-group {
    display: flex;
    gap: 1px;
    border-radius: 4px;
    overflow: hidden;
    margin-right: 2px;
  }
  
  .toolbar-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background-color: transparent;
    color: #333;
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 0;
    font-size: 14px;
    padding: 0;
  }
  
  .toolbar-button:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  .heading-level {
    font-size: 10px;
    margin-left: 1px;
    font-weight: bold;
  }
  
  @media (max-width: 600px) {
    .toolbar-button {
      width: 28px;
      height: 28px;
      font-size: 12px;
    }
    
    .heading-level {
      font-size: 8px;
      margin-left: 0;
    }
  }
</style>
