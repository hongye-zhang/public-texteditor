const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 应用信息
  appInfo: {
    isElectron: true,
    version: process.versions.electron
  },
  
  // 窗口控制 API
  minimizeWindow: () => ipcRenderer.invoke('window-minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window-maximize'),
  restoreWindow: () => ipcRenderer.invoke('window-restore'),
  closeWindow: () => ipcRenderer.invoke('window-close'),
  isWindowMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  onWindowMaximizeChange: (callback) => ipcRenderer.on('window-maximize-change', (_, maximized) => callback(maximized)),
  
  // 菜单操作 API
  triggerMenuAction: (action) => ipcRenderer.invoke('menu-action', action),
  
  // 文件操作相关的 API
  fileSystem: {
    // 保存文件（首次保存，会弹出保存对话框）
    saveFileAs: (content, suggestedName) => ipcRenderer.invoke('save-file-as', content, suggestedName),
    
    // 保存文件（使用已知路径）
    saveFile: (filePath, content) => ipcRenderer.invoke('save-file', filePath, content),
    
    // 检查后端状态
    checkBackendStatus: () => ipcRenderer.invoke('check-backend-status'),
  
    // 获取 API 基础 URL
    getApiBaseUrl: () => ipcRenderer.invoke('get-api-base-url'),
  
    // 获取运行模式
    getRunMode: () => ipcRenderer.invoke('get-run-mode'),
  
    // 菜单事件监听器
    onMenuNewFile: (callback) => ipcRenderer.on('menu-new-file', callback),
    onMenuOpenFile: (callback) => ipcRenderer.on('menu-open-file', callback),
    onMenuSaveFile: (callback) => ipcRenderer.on('menu-save-file', callback),
    onMenuSaveFileAs: (callback) => ipcRenderer.on('menu-save-file-as', callback),
    onMenuExportPdf: (callback) => ipcRenderer.on('menu-export-pdf', callback),
  
    // 设置导航
    onNavigateSettings: (callback) => ipcRenderer.on('navigate-settings', (_, section) => callback(section)),
  
    // 后端管理
    onRestartBackend: (callback) => ipcRenderer.on('restart-backend', callback),
    
    // 打开文件
    openFile: () => ipcRenderer.invoke('open-file'),
    
    // 打开文件夹
    openFolder: () => ipcRenderer.invoke('open-folder'),
    
    // 读取文件
    readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
    
    // 列出目录中的文件
    listFiles: (folderPath) => ipcRenderer.invoke('list-files', folderPath),
    
    // 获取最近文件列表
    getRecentFiles: () => ipcRenderer.invoke('get-recent-files'),
    
    // 添加到最近文件列表
    addToRecentFiles: (filePath) => ipcRenderer.invoke('add-to-recent-files', filePath),
    
    // 获取默认保存目录
    getDefaultSaveDirectory: () => ipcRenderer.invoke('get-default-save-directory'),
    
    // 设置默认保存目录
    setDefaultSaveDirectory: (directoryPath) => ipcRenderer.invoke('set-default-save-directory', directoryPath),
    
    // 导出为PDF
    exportPdf: (content, suggestedName) => ipcRenderer.invoke('export-pdf', content, suggestedName),
    
    // 模板文件操作
    getTemplatesDirectory: () => ipcRenderer.invoke('get-templates-directory'),
    selectTemplatesDirectory: () => ipcRenderer.invoke('select-templates-directory'),
    saveTemplateFile: (templateId, templateData) => ipcRenderer.invoke('save-template-file', templateId, templateData),
    readTemplateFile: (templateId) => ipcRenderer.invoke('read-template-file', templateId),
    deleteTemplateFile: (templateId) => ipcRenderer.invoke('delete-template-file', templateId),
    listTemplateFiles: () => ipcRenderer.invoke('list-template-files'),
    
    // 文件夹操作
    createDirectory: (directoryPath) => ipcRenderer.invoke('create-directory', directoryPath),
    checkPathExists: (path) => ipcRenderer.invoke('check-path-exists', path),
    deleteFile: (filePath) => ipcRenderer.invoke('delete-file', filePath)
  },
  
  // API 密钥管理相关的 API
  apiKeys: {
    // 保存 API 密钥
    saveApiKey: (keyName, keyValue) => ipcRenderer.invoke('save-api-key', keyName, keyValue),
    
    // 获取 API 密钥
    getApiKey: (keyName) => ipcRenderer.invoke('get-api-key', keyName),
    
    // 删除 API 密钥
    deleteApiKey: (keyName) => ipcRenderer.invoke('delete-api-key', keyName)
  },
  
  // 后端相关的 API
  backend: {
    // 获取 API 后端 URL
    getApiBaseUrl: () => ipcRenderer.invoke('get-api-base-url'),
    
    // 检查 Python 后端状态
    checkBackendStatus: () => ipcRenderer.invoke('check-backend-status')
  },
  
  // 菜单相关的 API
  menu: {
    // 更新最近文件菜单
    updateRecentFiles: (recentFiles) => ipcRenderer.send('update-recent-files', recentFiles),
    
    // 监听最近文件打开事件
    onOpenRecentFile: (callback) => ipcRenderer.on('menu-open-recent-file', (_, fileId) => callback(fileId)),
    
    // 监听清除最近文件事件
    onClearRecentFiles: (callback) => ipcRenderer.on('menu-clear-recent-files', callback)
  }
});

// 添加环境检测辅助函数
contextBridge.exposeInMainWorld('environment', {
  isElectron: true
});
