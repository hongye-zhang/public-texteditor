<script>
  import '../app.css';
  import { initI18n } from '../lib/i18n';
  import ToastContainer from '../components/ToastContainer.svelte';
  import CustomTitleBar from '../components/CustomTitleBar.svelte';
  import { onMount } from 'svelte';
  import { storageManager } from '../features/file-management/storage/storageManager';
  import { fileStore } from '../features/file-management/stores/fileStore';
  import { recentFilesStore } from '../features/file-management/stores/recentFilesStore';
  
  // 检查是否在 Electron 环境中
  let isElectron = false;
  
  // 保存最后活动文件的键
  const LAST_ACTIVE_FILE_KEY = 'last-active-file';
  
  // 保存最后活动文件信息
  function saveLastActiveFile(fileId, filePath) {
    try {
      const lastActiveFile = {
        fileId,
        filePath,
        timestamp: Date.now()
      };
      localStorage.setItem(LAST_ACTIVE_FILE_KEY, JSON.stringify(lastActiveFile));
    } catch (error) {
      console.error('保存最后活动文件失败:', error);
    }
  }
  
  // 恢复最后活动文件
  async function restoreLastActiveFile() {
    try {
      const stored = localStorage.getItem(LAST_ACTIVE_FILE_KEY);
      if (!stored) return false;
      
      const lastActiveFile = JSON.parse(stored);
      const { fileId, filePath, timestamp } = lastActiveFile;
      
      // 检查时间戳，如果超过7天就不自动恢复
      const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
      if (timestamp < sevenDaysAgo) {
        console.log('最后活动文件时间过久，不自动恢复');
        return false;
      }
      
      // 如果是 Electron 环境且有文件路径，尝试打开文件
      if (isElectron && filePath && window.electronAPI?.fileSystem) {
        try {
          // 检查文件是否存在
          const fileData = await window.electronAPI.fileSystem.readFile(filePath);
          const fileContent = typeof fileData === 'string' ? fileData : fileData.content;
          
          // 创建文件并设置为活动文件
          const fileName = filePath.split(/[\\\/]/).pop() || `文件-${Date.now()}`;
          const newFileId = await fileStore.createFile(fileName, fileContent, filePath, true);
          if (newFileId) {
            await fileStore.setActiveFile(newFileId);
          }
          
          console.log('成功恢复最后活动文件:', filePath);
          return true;
        } catch (error) {
          console.warn('无法打开最后活动文件，可能已被删除或移动:', filePath, error);
          // 文件不存在，尝试从最近文件列表恢复
          return await restoreFromRecentFiles();
        }
      } else {
        // 非 Electron 环境，尝试从最近文件列表恢复
        return await restoreFromRecentFiles();
      }
    } catch (error) {
      console.error('恢复最后活动文件失败:', error);
      return false;
    }
  }
  
  // 从最近文件列表恢复第一个文件
  async function restoreFromRecentFiles() {
    try {
      const recentFiles = recentFilesStore.getFiles();
      if (recentFiles.length === 0) {
        console.log('没有最近文件可以恢复');
        return false;
      }
      
      const firstRecentFile = recentFiles[0];
      
      // 如果是 Electron 环境，尝试打开第一个最近文件
      if (isElectron && firstRecentFile.localFilePath && window.electronAPI?.fileSystem) {
        try {
          const fileData = await window.electronAPI.fileSystem.readFile(firstRecentFile.localFilePath);
          const fileContent = typeof fileData === 'string' ? fileData : fileData.content;
          const newFileId = await fileStore.createFile(firstRecentFile.title, fileContent, firstRecentFile.localFilePath, true);
          if (newFileId) {
            await fileStore.setActiveFile(newFileId);
          }
          
          console.log('成功从最近文件列表恢复文件:', firstRecentFile.title);
          return true;
        } catch (error) {
          console.warn('无法打开最近文件:', firstRecentFile.title, error);
          // 从最近文件列表中移除无效文件
          recentFilesStore.removeRecentFile(firstRecentFile.id);
          return false;
        }
      }
      
      return false;
    } catch (error) {
      console.error('从最近文件列表恢复失败:', error);
      return false;
    }
  }

  onMount(() => {
    // 在客户端检测是否为 Electron 环境
    isElectron = typeof window !== 'undefined' && window.environment?.isElectron === true;
    
    // 异步初始化函数
    async function initializeApp() {
      try {
        await storageManager.init();
        
        // Load files from unified storage
        await fileStore.loadFromUnifiedStorage();
        
        // Check and repair recent files data integrity
        const repairedCount = recentFilesStore.checkAndRepairData();
        console.log(`Recent files data integrity check completed. ${repairedCount} valid files.`);
        
        // 尝试恢复最后活动文件
        const restored = await restoreLastActiveFile();
        if (!restored) {
          console.log('未能恢复最后活动文件，使用默认新文件');
        }
        
      } catch (error) {
        console.error('Failed to initialize application storage:', error);
      }
    }
    
    // 启动异步初始化
    initializeApp();
    
    // 监听文件切换事件，保存最后活动文件
    const unsubscribe = fileStore.subscribe((state) => {
      if (state.activeFileId) {
        const activeFile = state.files.find(f => f.id === state.activeFileId);
        if (activeFile && !activeFile.isTemporary) {
          saveLastActiveFile(activeFile.id, activeFile.localFilePath);
        }
      }
    });
    
    // 清理订阅
    return unsubscribe;
  });
  
  // Initialize the i18n system
  initI18n();
</script>

<svelte:head>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
</svelte:head>

<div class="app-container" class:electron-app={isElectron}>
  {#if isElectron}
    <CustomTitleBar />
  {/if}
  <div class="app-content">
    <slot></slot>
  </div>
</div>
<ToastContainer />

<style>
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
  
  .app-content {
    flex: 1;
    overflow: auto;
  }
  
  .electron-app .app-content {
    /* 为 Electron 应用添加特定样式 */
    border-top: none;
  }
</style>
