<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { clickOutside } from '../lib/actions/clickOutside';
  import { menuConfig, toFrontendMenuConfig } from '../lib/menu-config.js';
  import { recentFilesStore } from '../features/file-management/stores/recentFilesStore';
  import { fileStore } from '../features/file-management/stores/fileStore';
  
  // 窗口控制功能
  let isMaximized = false;
  
  // 检查是否在 Electron 环境中
  let isElectron = false;
  let electronAPI: any = null;
  
  // 菜单状态
  let activeMenu: string | null = null;
  
  // 菜单配置，在 onMount 中初始化
  let menus: any[] = [];
  
  // 最近文件订阅取消函数
  let unsubscribeRecentFiles: () => void;
  
  // 更新菜单配置的函数
  function updateMenuConfig(recentFiles?: any[]) {
    // 如果没有传入参数，则从 store 中获取
    if (!recentFiles) {
      recentFiles = $recentFilesStore.files;
    }
    
    // 创建菜单配置的副本
    const updatedMenuConfig = JSON.parse(JSON.stringify(menuConfig));
    
    // 在副本上更新最近文件菜单
    const fileMenu = updatedMenuConfig.menus.find((menu: any) => menu.id === 'file');
    if (fileMenu && recentFiles && recentFiles.length > 0) {
      // 移除所有现有的最近文件项
      fileMenu.items = fileMenu.items.filter((item: any) => 
        !item.id || (!item.id.startsWith('recent-file-') && item.id !== 'clear-recent-files')
      );
      
      // 找到导出PDF的位置
      const exportPdfIndex = fileMenu.items.findIndex((item: any) => item.id === 'exportPdf');
      if (exportPdfIndex !== -1) {
        const insertIndex = exportPdfIndex + 2; // exportPdf + separator
        
        // 创建最近文件项
        const recentFileItems: any[] = [];
        recentFiles.forEach((file: any, index: number) => {
          // 移除文件扩展名
          const displayName = file.title ? file.title.replace(/\.[^/.]+$/, '') : file.title;
          recentFileItems.push({
            id: `recent-file-${file.id}`,
            label: `${index + 1}. ${displayName}`,
            action: `open-recent-file:${file.id}`
          });
        });
        
        // 添加清除选项
        recentFileItems.push({
          id: 'clear-recent-files',
          label: '清除最近文件列表',
          action: 'clear-recent-files'
        });
        
        // 插入到菜单中
        fileMenu.items.splice(insertIndex, 0, ...recentFileItems);
      }
    }
    
    // 重新生成菜单
    menus = toFrontendMenuConfig(updatedMenuConfig, triggerMenuAction, closeWindow);
  }
  
  // 处理打开最近文件
  async function handleOpenRecentFile(fileId: string) {
    try {
      // 直接从最近文件列表中获取文件信息，不尝试使用文件ID
      const recentFilesState = get(recentFilesStore);
      const recentFile = recentFilesState.files.find((f: any) => f.id === fileId);
      
      if (!recentFile) {
        throw new Error(`在最近文件列表中找不到ID为 ${fileId} 的文件`);
      }
      
      if (!recentFile.localFilePath) {
        console.warn('最近文件缺少localFilePath，将从列表中移除:', recentFile);
        throw new Error(`文件 "${recentFile.title}" 缺少文件路径信息，可能是历史数据问题`);
      }
      
      if (recentFile && recentFile.localFilePath) {
        // 检查是否已经是当前活动文件
        const currentFileStore = get(fileStore);
        const currentActiveFile = currentFileStore.files.find(f => f.id === currentFileStore.activeFileId);
        
        // 如果要打开的文件已经是当前活动文件（通过文件路径比较），则只关闭菜单
        if (currentActiveFile && currentActiveFile.localFilePath === recentFile.localFilePath) {
          activeMenu = null;
          return;
        }
        
        // 从文件系统加载文件
        const fileInfo = await window.electronAPI?.fileSystem.readFile(recentFile.localFilePath!);
        
        if (fileInfo) {
          // 使用fileStore的createFile方法重新创建文件条目
          const newFileId = await fileStore.createFile(
            recentFile.title,
            fileInfo.content,
            recentFile.localFilePath,
            true // skipSaveDialog
          );
          
          // 设置为活动文件
          if (newFileId) {
            await fileStore.setActiveFile(newFileId);
          }
        } else {
          throw new Error('文件读取失败');
        }
      } else {
        throw new Error('在最近文件列表中找不到文件信息或没有文件路径');
      }
      
      activeMenu = null; // 关闭菜单
    } catch (error) {
      console.error('打开最近文件失败:', error);
      // 文件不存在或无法访问，从最近文件列表中移除
      recentFilesStore.removeRecentFile(fileId);
      activeMenu = null; // 关闭菜单
      
      // 显示错误信息
      const recentFilesState = get(recentFilesStore);
      const recentFile = recentFilesState.files.find((f: any) => f.id === fileId);
      if (recentFile?.localFilePath) {
        alert(`文件不存在或无法访问: ${recentFile.localFilePath}`);
      }
    }
  }
  
  // 处理清除最近文件
  function handleClearRecentFiles() {
    recentFilesStore.clearRecentFiles();
    activeMenu = null; // 关闭菜单
  }

  onMount(() => {
    
    // 初始化菜单配置
    updateMenuConfig();
    
    // 检查是否在 Electron 环境中
    isElectron = typeof window !== 'undefined' && window.environment?.isElectron === true;
    electronAPI = window.electronAPI;
    
    // 监听窗口最大化状态变化
    if (isElectron && electronAPI) {
      electronAPI.onWindowMaximizeChange((maximized: boolean) => {
        isMaximized = maximized;
      });
      
      // 获取初始窗口状态
      electronAPI.isWindowMaximized().then((maximized: boolean) => {
        isMaximized = maximized;
      });
    }
    
    // 订阅最近文件变化
    unsubscribeRecentFiles = recentFilesStore.subscribe((state) => {
      updateMenuConfig(state.files);
    });
    
    // 添加全局点击事件监听器，在点击其他地方时关闭菜单
    document.addEventListener('click', handleGlobalClick);
    
    return () => {
      document.removeEventListener('click', handleGlobalClick);
    };
  });
  
  onDestroy(() => {
    // 取消最近文件订阅
    if (unsubscribeRecentFiles) {
      unsubscribeRecentFiles();
    }
  });
  
  // 处理全局点击事件
  function handleGlobalClick(event: MouseEvent) {
    // 如果点击的不是菜单项，则关闭菜单
    const target = event.target as HTMLElement;
    if (!target.closest('.menu-item') && !target.closest('.dropdown-menu')) {
      activeMenu = null;
    }
  }
  
  // 切换菜单显示状态
  function toggleMenu(menuId: string, event: MouseEvent | KeyboardEvent) {
    event.stopPropagation();
    activeMenu = activeMenu === menuId ? null : menuId;
  }
  
  // 处理键盘事件
  function handleKeyDown(menuId: string, event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleMenu(menuId, event);
    } else if (event.key === 'Escape' && activeMenu) {
      event.preventDefault();
      activeMenu = null;
    }
  }
  
  // 处理下拉菜单项的键盘事件
  function handleMenuItemKeyDown(item: any, event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (typeof item.action === 'function') {
        item.action();
      }
    }
  }
  
  // 触发菜单动作
  function triggerMenuAction(action: string) {
    // 处理最近文件动作
    if (action.startsWith('open-recent-file:')) {
      const fileId = action.replace('open-recent-file:', '');
      handleOpenRecentFile(fileId);
    } else if (action === 'clear-recent-files') {
      handleClearRecentFiles();
    } else if (isElectron && electronAPI) {
      electronAPI.triggerMenuAction(action);
    }
    // 执行动作后关闭菜单
    activeMenu = null;
  }
  
  // 窗口控制函数
  function minimizeWindow() {
    if (isElectron && electronAPI) {
      electronAPI.minimizeWindow();
    }
  }
  
  function maximizeWindow() {
    if (isElectron && electronAPI) {
      electronAPI.maximizeWindow();
    }
  }
  
  function restoreWindow() {
    if (isElectron && electronAPI) {
      electronAPI.restoreWindow();
    }
  }
  
  function closeWindow() {
    if (isElectron && electronAPI) {
      electronAPI.closeWindow();
    }
  }
</script>

<!-- 自定义标题栏 -->
<div class="title-bar" class:electron={isElectron}>
  <!-- 应用图标和标题 -->
  <div class="title-bar-drag-area">
    <div class="app-icon">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Background documents -->
      <path d="M5 3H15V5H7V17H5V3Z" fill="#94a3b8" />
      <path d="M9 7H19V19H9V7Z" fill="#cbd5e1" stroke="#64748b" stroke-width="1.5" />
      <path d="M11 11H17V13H11V11Z" fill="#64748b" />
      <path d="M11 15H15V17H11V15Z" fill="#64748b" />
      <!-- Letter A -->
      <path d="M13 9H15L16 12H14L13 9Z" fill="#3b82f6" />
    </svg>
    </div>
    <div class="app-title">{menuConfig.appInfo.name}</div>
  </div>
  
  <!-- 菜单区域 -->
  <div class="menu-bar" role="menubar">
    {#each menus as menu}
      <div 
        class="menu-item" 
        class:active={activeMenu === menu.id}
        on:click={(e) => toggleMenu(menu.id, e)}
        on:keydown={(e) => handleKeyDown(menu.id, e)}
        aria-haspopup="true"
        aria-expanded={activeMenu === menu.id}
        role="menuitem"
        tabindex="0"
      >
        {menu.label}
        
        {#if activeMenu === menu.id}
          <div 
            class="dropdown-menu" 
            use:clickOutside={() => activeMenu = null}
            role="menu"
            aria-label={`${menu.label} menu`}
          >
            {#each menu.items as item}
              {#if item.type === 'separator'}
                <div class="menu-separator" role="separator"></div>
              {:else if item.submenu && item.submenu.length > 0}
                <!-- 子菜单项 -->
                <div 
                  class="dropdown-item submenu-item" 
                  class:disabled={item.enabled === false}
                  role="menuitem"
                  tabindex="0"
                >
                  <span class="item-label">{item.label}</span>
                  <span class="submenu-arrow">▶</span>
                  
                  <!-- 子菜单 -->
                  <div class="submenu" role="menu">
                    {#each item.submenu as subItem}
                      {#if subItem.type === 'separator'}
                        <div class="menu-separator" role="separator"></div>
                      {:else}
                        <div 
                          class="dropdown-item" 
                          class:disabled={subItem.enabled === false}
                          on:click|stopPropagation={subItem.action}
                          on:keydown={(e) => handleMenuItemKeyDown(subItem, e)}
                          role="menuitem"
                          tabindex="0"
                        >
                          <span class="item-label">{subItem.label}</span>
                          {#if subItem.shortcut}
                            <span class="item-shortcut">{subItem.shortcut}</span>
                          {/if}
                        </div>
                      {/if}
                    {/each}
                  </div>
                </div>
              {:else}
                <!-- 普通菜单项 -->
                <div 
                  class="dropdown-item" 
                  class:disabled={item.enabled === false}
                  on:click|stopPropagation={item.action}
                  on:keydown={(e) => handleMenuItemKeyDown(item, e)}
                  role="menuitem"
                  tabindex="0"
                >
                  <span class="item-label">{item.label}</span>
                  {#if item.shortcut}
                    <span class="item-shortcut">{item.shortcut}</span>
                  {/if}
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
  
  <!-- 窗口控制按钮 -->
  {#if isElectron}
    <div class="window-controls">
      <button 
        class="window-control minimize" 
        on:click={minimizeWindow} 
        title="最小化" 
        aria-label="最小化窗口">
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <rect fill="currentColor" width="10" height="1" x="1" y="6"></rect>
        </svg>
        <span class="sr-only">最小化</span>
      </button>
      
      {#if isMaximized}
        <button 
          class="window-control restore" 
          on:click={restoreWindow} 
          title="向下还原" 
          aria-label="向下还原窗口">
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <path fill="currentColor" d="M2,4v4h4v2h4V6H6V4H2z M4,8V6h2v2H4z M8,8V6h2v2H8z"></path>
          </svg>
          <span class="sr-only">向下还原</span>
        </button>
      {:else}
        <button 
          class="window-control maximize" 
          on:click={maximizeWindow} 
          title="最大化" 
          aria-label="最大化窗口">
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <rect fill="currentColor" width="9" height="9" x="1.5" y="1.5"></rect>
          </svg>
          <span class="sr-only">最大化</span>
        </button>
      {/if}
      
      <button 
        class="window-control close" 
        on:click={closeWindow} 
        title="关闭" 
        aria-label="关闭窗口">
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path fill="currentColor" d="M6,5.3L9.3,2L10,2.7L6.7,6L10,9.3L9.3,10L6,6.7L2.7,10L2,9.3L5.3,6L2,2.7L2.7,2L6,5.3z"></path>
        </svg>
        <span class="sr-only">关闭</span>
      </button>
    </div>
  {/if}
</div>

<style>
  .title-bar {
    display: flex;
    align-items: center;
    height: 38px;
    background-color: #f0f0f0;
    border-bottom: 1px solid #e0e0e0;
    user-select: none;
    -webkit-app-region: no-drag;
    padding: 0 8px;
    box-sizing: border-box;
  }
  
  /* 屏幕阅读器专用样式 */
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }
  
  .title-bar.electron {
    -webkit-app-region: drag;
  }
  
  .title-bar-drag-area {
    display: flex;
    align-items: center;
    flex: 0 0 auto;
    margin-right: 16px;
    -webkit-app-region: drag;
  }
  
  .app-icon {
    width: 16px;
    height: 16px;
    margin-right: 8px;
  }
  
  
  .app-title {
    font-size: 13px;
    font-weight: 500;
    color: #333;
  }
  
  .menu-bar {
    display: flex;
    flex: 1;
    height: 100%;
    -webkit-app-region: no-drag;
  }
  
  .menu-item {
    display: flex;
    align-items: center;
    padding: 0 10px;
    height: 100%;
    font-size: 13px;
    cursor: pointer;
    position: relative;
  }
  
  .menu-item:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  .menu-item.active {
    background-color: rgba(0, 0, 0, 0.1);
  }
  
  /* 下拉菜单样式 */
  .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 200px;
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    -webkit-app-region: no-drag;
    padding: 4px 0;
  }
  
  .dropdown-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 12px;
    font-size: 13px;
    color: #333;
    cursor: pointer;
  }
  
  .dropdown-item:hover {
    background-color: #f0f0f0;
  }
  
  .item-label {
    flex: 1;
  }
  
  .item-shortcut {
    color: #777;
    margin-left: 16px;
    font-size: 12px;
  }
  
  .menu-separator {
    height: 1px;
    background-color: #e0e0e0;
    margin: 4px 0;
  }
  
  /* 子菜单样式 */
  .submenu-item {
    position: relative;
  }
  
  .submenu-arrow {
    margin-left: 8px;
    font-size: 10px;
    color: #666;
  }
  
  .submenu {
    position: absolute;
    top: 0;
    left: 100%;
    min-width: 200px;
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    z-index: 1001;
    padding: 4px 0;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.2s ease, visibility 0.2s ease;
  }
  
  .submenu-item:hover .submenu {
    opacity: 1;
    visibility: visible;
  }
  
  /* 禁用状态 */
  .dropdown-item.disabled {
    color: #999;
    cursor: default;
    pointer-events: none;
  }
  
  .dropdown-item.disabled:hover {
    background-color: transparent;
  }
  
  .window-controls {
    display: flex;
    -webkit-app-region: no-drag;
  }
  
  .window-control {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 32px;
    border: none;
    background: transparent;
    outline: none;
    cursor: pointer;
    color: #555;
  }
  
  .window-control:hover {
    background-color: rgba(0, 0, 0, 0.1);
  }
  
  .window-control.close:hover {
    background-color: #e81123;
    color: white;
  }
</style>
