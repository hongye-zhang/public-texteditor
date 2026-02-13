<script lang="ts">
  import { Editor } from '@tiptap/core';
  import { onMount, onDestroy } from 'svelte';
  import { t } from '$lib/i18n';
  import SaveStatusIndicator from '../../../components/SaveStatusIndicator.svelte';
  
  export let editor: Editor | null = null;
  
  // 标题下拉菜单状态
  let isHeadingDropdownOpen = false;
  let selectedHeading = 'Paragraph'; // 默认为段落
  
  // 修订系统状态
  let revisions: any[] = [];
  
  // 响应式更新修订列表
  $: if (editor) {
    updateRevisionsList();
  }
  
  // 监听自定义事件，用于外部组件（如ChatPanel）触发修订列表更新
  onMount(() => {
    const handleRevisionsUpdated = () => {
      console.log('EditorToolbar: 收到 revisions-updated 事件');
      if (editor) {
        updateRevisionsList();
      }
    };
    
    // 添加事件监听器
    document.addEventListener('revisions-updated', handleRevisionsUpdated);
    
    // 组件销毁时移除事件监听器
    return () => {
      document.removeEventListener('revisions-updated', handleRevisionsUpdated);
    };
  });
  
  // 更新修订列表
  function updateRevisionsList() {
    if (!editor) return;
    
    const newRevisions: any[] = [];
    const { doc } = editor.state;
    
    doc.descendants((node, pos) => {
      if (node.type.name === 'revisionNode' && node.attrs.status === 'pending') {
        newRevisions.push({
          id: node.attrs.id,
          type: node.attrs.type,
          originalContent: node.attrs.originalContent || '',
          newContent: node.attrs.newContent || '',
          position: pos
        });
      }
    });
    
    revisions = newRevisions;
  }
  
  // 接受修订
  function acceptRevision(id: string) {
    console.log(`尝试接受修订: ${id}`);
    if (!editor || !(editor.commands as any).acceptRevision) {
      console.warn('接受修订失败: editor 或 acceptRevision 命令不可用');
      return;
    }
    // 修复: 直接传递id参数而不是包装在对象中
    (editor.commands as any).acceptRevision(id);
    updateRevisionsList();
  }
  
  // 拒绝修订
  function rejectRevision(id: string) {
    console.log(`尝试拒绝修订: ${id}`);
    if (!editor || !(editor.commands as any).rejectRevision) {
      console.warn('拒绝修订失败: editor 或 rejectRevision 命令不可用');
      return;
    }
    // 修复: 直接传递id参数而不是包装在对象中
    (editor.commands as any).rejectRevision(id);
    
    // 强制更新修订列表
    updateRevisionsList();
    
    // 延迟一点时间再次更新，确保状态已更新
    setTimeout(() => {
      updateRevisionsList();
    }, 50);
  }
  
  // 接受所有修订
  function acceptAllRevisions() {
    console.log(`尝试接受所有修订, 修订数量: ${revisions.length}`);
    const revisionIds = revisions.map(rev => rev.id);
    
    // 一次接受一个修订，确保更新修订列表
    if (revisionIds.length > 0) {
      const processNextRevision = (index = 0) => {
        if (index >= revisionIds.length) {
          console.log('所有修订已接受');
          return;
        }
        
        acceptRevision(revisionIds[index]);
        // 延迟处理下一个，确保当前修订已处理完成
        setTimeout(() => processNextRevision(index + 1), 50);
      };
      
      processNextRevision();
    }
  }
  
  // 拒绝所有修订
  function rejectAllRevisions() {
    console.log(`尝试拒绝所有修订, 修订数量: ${revisions.length}`);
    const revisionIds = revisions.map(rev => rev.id);
    
    // 一次拒绝一个修订，确保更新修订列表
    if (revisionIds.length > 0) {
      const processNextRevision = (index = 0) => {
        if (index >= revisionIds.length) {
          console.log('所有修订已拒绝');
          
          // 强制更新编辑器状态
          if (editor) {
            // 1. 强制执行一个文档更新操作
            editor.commands.focus();
            
            // 2. 强制重新渲染编辑器
            editor.view.updateState(editor.view.state);
            
            // 3. 触发自定义事件，通知工具栏更新
            const event = new CustomEvent('revisions-updated', { detail: { count: 0 } });
            document.dispatchEvent(event);
            
            // 4. 再次更新修订列表
            updateRevisionsList();
          }
          
          return;
        }
        
        rejectRevision(revisionIds[index]);
        // 延迟处理下一个，确保当前修订已处理完成
        setTimeout(() => processNextRevision(index + 1), 50);
      };
      
      processNextRevision();
    }
  }
  
  // 更新选中的标题格式
  function updateSelectedHeading() {
    if (!editor) return;
    
    try {
      // 获取当前活动节点的类型
      const { state } = editor;
      const { selection } = state;
      const { $from } = selection;
      
      // 获取当前节点的父节点，处理嵌套情况
      let node = $from.node();
      let depth = $from.depth;
      
      // 如果当前节点不是标题，尝试获取父节点
      while (depth > 0 && node.type.name !== 'heading') {
        depth--;
        node = $from.node(depth);
      }
      
      // 检查当前节点的类型
      if (node.type.name === 'heading') {
        const level = node.attrs.level;
        selectedHeading = `Heading ${level}`;
      } else {
        // 检查当前是否在标题中
        const isHeading = editor.isActive('heading');
        if (isHeading) {
          const headingLevel = editor.getAttributes('heading').level;
          if (headingLevel) {
            selectedHeading = `Heading ${headingLevel}`;
            return;
          }
        }
        
        selectedHeading = 'Paragraph';
      }
    } catch (error) {
      console.error('Error updating heading selection:', error);
      selectedHeading = 'Paragraph'; // 出错时默认为段落
    }
  }
  
  // 关闭下拉菜单的函数
  function closeHeadingDropdown() {
    isHeadingDropdownOpen = false;
  }
  
  // 切换下拉菜单的函数
  function toggleHeadingDropdown(event: MouseEvent) {
    // 阻止事件冒泡，防止立即触发handleClickOutside
    event.stopPropagation();
    isHeadingDropdownOpen = !isHeadingDropdownOpen;
  }
  
  // 设置标题的函数
  function setHeading(level: 1 | 2 | 3 | null) {
    if (!editor) return;
    
    if (level === null) {
      // 设置为普通段落
      editor.chain().focus().setParagraph().run();
      selectedHeading = 'Paragraph';
    } else {
      // 设置为标题，使用setHeading而非toggleHeading
      // 这样就不会在已经是某个标题级别的段落上切换标题状态
      editor.chain().focus().setHeading({ level }).run();
      selectedHeading = `Heading ${level}`;
    }
    
    // 关闭下拉菜单
    closeHeadingDropdown();
  }
  
  // 点击文档其他地方时关闭下拉菜单
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    const dropdown = document.querySelector('.heading-dropdown');
    
    // 检查点击的元素是否在下拉菜单内
    if (dropdown && !dropdown.contains(target) && isHeadingDropdownOpen) {
      closeHeadingDropdown();
    }
  }
  
  // 初始化时更新选中的标题格式
  function initializeHeadingSelection() {
    if (!editor) return;
    
    // 使用延时确保编辑器已完全加载
    setTimeout(() => {
      updateSelectedHeading();
    }, 100);
  }
  
  // 创建一个不会与气泡菜单冲突的更新函数
  function setupHeadingUpdateListeners() {
    if (!editor) return;
    
    // 使用 MutationObserver 监听 DOM 变化
    // 这样可以避免与编辑器的原生事件冲突
    const editorElement = editor.view.dom;
    
    // 创建一个观察器实例
    const observer = new MutationObserver((mutations) => {
      // 当DOM变化时更新标题选择
      updateSelectedHeading();
    });
    
    // 配置观察选项
    const config = { 
      childList: true,  // 观察子节点变化
      subtree: true,    // 观察所有后代节点
      characterData: true  // 观察文本变化
    };
    
    // 开始观察编辑器元素
    observer.observe(editorElement, config);
    
    // 存储观察器实例以便后续清理
    window._headingObserver = observer;
    
    // 添加一个定时器，定期检查标题状态
    const intervalId = setInterval(() => {
      if (editor && editor.view && !isHeadingDropdownOpen) {
        updateSelectedHeading();
      }
    }, 1000); // 每秒检查一次
    
    // 存储定时器ID以便后续清理
    window._headingIntervalId = intervalId;
  }
  
  // 添加事件监听器
  onMount(() => {
    // 添加点击外部事件监听
    document.addEventListener('click', handleClickOutside);
    
    // 添加自定义修订更新事件监听器
    document.addEventListener('revisionUpdated', updateRevisionsList);
    
    // 初始化标题选择并设置监听器
    if (editor) {
      initializeHeadingSelection();
      setupHeadingUpdateListeners();
      
      // 监听编辑器的光标位置变化
      // 使用一个不会干扰气泡菜单的事件
      editor.on('focus', () => {
        updateSelectedHeading();
      });
      
      // 初始化修订列表并设置监听器
      updateRevisionsList();
      editor.on('transaction', updateRevisionsList);
    }
    
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('revisionUpdated', updateRevisionsList);
      
      // 清理观察器和定时器
      if (window._headingObserver) {
        window._headingObserver.disconnect();
        window._headingObserver = null;
      }
      
      if (window._headingIntervalId) {
        clearInterval(window._headingIntervalId);
        window._headingIntervalId = null;
      }
      
      // 移除编辑器事件监听
      if (editor) {
        editor.off('focus');
        editor.off('transaction');
      }
    };
  });
  
  // 当编辑器变化时重新设置监听器
  $: if (editor) {
    // 清理旧的观察器和定时器
    if (window._headingObserver) {
      window._headingObserver.disconnect();
      window._headingObserver = null;
    }
    
    if (window._headingIntervalId) {
      clearInterval(window._headingIntervalId);
      window._headingIntervalId = null;
    }
    
    // 重新初始化
    setTimeout(() => {
      initializeHeadingSelection();
      setupHeadingUpdateListeners();
    }, 100);
  }
  
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
    
    // 文件大小限制 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('图片大小不能超过10MB');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      
      // Insert the image into the editor
      editor.chain().focus().setImage({ src: dataUrl }).run();
      
      // Clear the file input so the same file can be selected again
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
  <div class="toolbar-left">
    <!-- 标题下拉菜单 -->
    <div class="toolbar-group heading-dropdown">
      <button 
        class="toolbar-button heading-dropdown-toggle"
        on:click={(e) => toggleHeadingDropdown(e)}
        title={$t('editor.heading1')}
        aria-label={$t('editor.heading1')}
        aria-haspopup="true"
        aria-expanded={isHeadingDropdownOpen}
      >
        <span class="heading-text">{selectedHeading}</span>
        <i class="fas fa-chevron-down dropdown-icon"></i>
      </button>
      
      {#if isHeadingDropdownOpen}
        <div class="dropdown-menu">
          <button 
            class="dropdown-item" 
            on:click={(e) => { e.stopPropagation(); setHeading(1); }}
            class:active={selectedHeading === 'Heading 1'}
          >
            <i class="fas fa-heading"></i><span class="heading-level">1</span>
            <span class="item-text">Heading 1</span>
          </button>
          <button 
            class="dropdown-item" 
            on:click={(e) => { e.stopPropagation(); setHeading(2); }}
            class:active={selectedHeading === 'Heading 2'}
          >
            <i class="fas fa-heading"></i><span class="heading-level">2</span>
            <span class="item-text">Heading 2</span>
          </button>
          <button 
            class="dropdown-item" 
            on:click={(e) => { e.stopPropagation(); setHeading(3); }}
            class:active={selectedHeading === 'Heading 3'}
          >
            <i class="fas fa-heading"></i><span class="heading-level">3</span>
            <span class="item-text">Heading 3</span>
          </button>
          <button 
            class="dropdown-item" 
            on:click={(e) => { e.stopPropagation(); setHeading(null); }}
            class:active={selectedHeading === 'Paragraph'}
          >
            <i class="fas fa-paragraph"></i>
            <span class="item-text">Paragraph</span>
          </button>
        </div>
      {/if}
    </div>
    
    <div class="toolbar-group">
      <!-- 文本格式化 -->
      <button 
        class="toolbar-button"
        on:click={() => editor?.chain().focus().toggleBold().run()}
        title={$t('editor.bold')}
        aria-label={$t('editor.bold')}
      >
        <i class="fas fa-bold"></i>
      </button>
      
      <button 
        class="toolbar-button"
        on:click={() => editor?.chain().focus().toggleHighlight().run()}
        title={$t('editor.highlight') || 'Highlight'}
        aria-label={$t('editor.highlight') || 'Highlight'}
      >
        <i class="fas fa-highlighter"></i>
      </button>
    </div>
  
  <div class="toolbar-group">
    <!-- 列表 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleBulletList().run()}
      title={$t('editor.bulletList')}
      aria-label={$t('editor.bulletList')}
    >
      <i class="fas fa-list-ul"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleOrderedList().run()}
      title={$t('editor.orderedList')}
      aria-label={$t('editor.orderedList')}
    >
      <i class="fas fa-list-ol"></i>
    </button>
  </div>
  
  <div class="toolbar-group">
    <!-- 插入元素 -->
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().setHorizontalRule().run()}
      title={$t('editor.horizontalRule')}
      aria-label={$t('editor.horizontalRule')}
    >
      <i class="fas fa-minus"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={() => editor?.chain().focus().toggleBlockquote().run()}
      title={$t('editor.blockquote')}
      aria-label={$t('editor.blockquote')}
    >
      <i class="fas fa-quote-right"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={insertTable}
      title={$t('editor.table')}
      aria-label={$t('editor.table')}
    >
      <i class="fas fa-table"></i>
    </button>
    
    <button 
      class="toolbar-button"
      on:click={openFileDialog}
      title={$t('editor.image')}
      aria-label={$t('editor.image')}
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
    
    <!-- 已移除修订工具栏切换按钮 -->
  </div>
  
  <div class="toolbar-right">
    <!-- Save Status Indicator -->
    <div class="save-status-container">
      <SaveStatusIndicator />
    </div>
    
    {#if revisions.length > 0}
    <div class="toolbar-group revision-group">
      <button 
        class="toolbar-button revision-button accept-all"
        on:click={acceptAllRevisions}
        title={$t('editor.acceptAllRevisions') || 'Accept All Revisions'}
        aria-label={$t('editor.acceptAllRevisions') || 'Accept All Revisions'}
        disabled={!editor}
      >
        <i class="fas fa-check"></i>
      </button>
      
      <button 
        class="toolbar-button revision-button reject-all"
        on:click={rejectAllRevisions}
        title={$t('editor.rejectAllRevisions') || 'Reject All Revisions'}
        aria-label={$t('editor.rejectAllRevisions') || 'Reject All Revisions'}
        disabled={!editor}
      >
        <i class="fas fa-xmark"></i>
      </button>
    </div>
    {/if}
  </div>
</div>

<style>
  .editor-toolbar {
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    padding: 4px 8px;
    background-color: white;
    position: sticky;
    top: 0;
    z-index: 10;
    overflow: visible; /* 改为 visible 以允许下拉菜单超出工具栏 */
    justify-content: space-between;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none; /* Firefox */
    height: 41px;
    align-items: center;
  }
  
  /* 标题下拉菜单样式 */
  .heading-dropdown {
    position: relative;
    margin-right: 8px;
    z-index: 1000; /* 确保下拉菜单在其他元素之上 */
  }
  
  .editor-toolbar::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Edge */
  }
  
  .toolbar-left {
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    overflow: visible; /* 确保下拉菜单可以超出容器 */
  }
  
  .toolbar-right {
    display: flex;
    margin-left: auto;
  }
  
  .toolbar-group {
    display: flex;
    gap: 2px;
    margin-right: 8px;
    overflow: visible; /* 确保下拉菜单可以超出容器 */
  }
  
  .revision-button {
    font-weight: 500;
    width: auto;
  }
  
  .toolbar-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background-color: transparent;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 4px;
    font-size: 14px;
    padding: 0;
  }
  
  .toolbar-button:hover {
    background-color: #f3f4f6;
  }
  
  /* 标题下拉按钮样式 */
  .heading-dropdown-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: auto;
    min-width: 120px;
    padding: 0 8px;
    height: 32px;
    border-radius: 4px;
    background-color: white;
  }
  
  .heading-text {
    font-size: 14px;
    margin-right: 4px;
  }
  
  .dropdown-icon {
    font-size: 10px;
    margin-left: 4px;
  }
  
  /* 下拉菜单样式 */
  .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    width: 160px;
    background-color: white;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    z-index: 1001; /* 确保菜单在所有其他元素之上 */
    margin-top: 4px;
    max-height: 300px; /* 防止菜单过长 */
    overflow-y: auto; /* 如果菜单项过多允许滚动 */
  }
  
  .dropdown-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 8px 12px;
    border: none;
    background-color: transparent;
    color: #6b7280;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .dropdown-item:hover {
    background-color: #f3f4f6;
  }
  
  .dropdown-item.active {
    background-color: #f3f4f6;
    font-weight: 500;
  }
  
  .item-text {
    margin-left: 8px;
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
  
  /* 修订工具栏样式 */
  .revision-group {
    display: flex;
    align-items: center;
    gap: 8px;
    border-left: 1px solid #e5e7eb;
    padding-left: 8px;
    margin-left: 8px;
  }
  

  .revision-button.accept-all {
    background-color: #10b981;
    color: white;
  }
  
  .revision-button.accept-all:hover {
    background-color: #059669;
  }
  
  .revision-button.reject-all {
    background-color: #ef4444;
    color: white;
  }
  
  .revision-button.reject-all:hover {
    background-color: #dc2626;
  }
  
  /* Save status indicator container */
  .save-status-container {
    margin-right: 12px;
    display: flex;
    align-items: center;
  }
</style>
