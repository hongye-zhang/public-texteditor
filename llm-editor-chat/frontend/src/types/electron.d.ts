/**
 * Electron API 类型声明
 */

interface ElectronAPI {
  appInfo: {
    isElectron: boolean;
    version: string;
  };
  
  fileSystem: {
    // 保存文件（首次保存，会弹出保存对话框）
    saveFileAs: (content: string, suggestedName: string) => Promise<string | null>;
    
    // 保存文件（使用已知路径）
    saveFile: (filePath: string, content: string) => Promise<string>;
    
    // 打开文件
    openFile: () => Promise<{ path: string; content: string; name: string } | null>;
    
    // 打开文件夹
    openFolder: () => Promise<string | null>;
    
    // 读取文件
    readFile: (filePath: string) => Promise<{ path: string; content: string; name: string }>;
    
    // 列出目录中的文件
    listFiles: (folderPath: string) => Promise<Array<{
      name: string;
      path: string;
      isDirectory: boolean;
      size?: number;
      modifiedTime: number;
    }>>;
    
    // 获取最近文件列表
    getRecentFiles: () => Promise<Array<{
      path: string;
      name: string;
      lastOpened: number;
    }>>;
    
    // 添加到最近文件列表
    addToRecentFiles: (filePath: string) => Promise<Array<{
      path: string;
      name: string;
      lastOpened: number;
    }>>;
    
    // 获取默认保存目录
    getDefaultSaveDirectory: () => Promise<string>;
    
    // 设置默认保存目录
    setDefaultSaveDirectory: (directoryPath: string) => Promise<string>;
    
    // 导出为PDF
    exportPdf: (content: string, suggestedName: string) => Promise<{
      success: boolean;
      filePath?: string;
      canceled?: boolean;
      error?: string;
    }>;
    
    // 菜单事件监听
    onMenuNewFile: (callback: () => void) => void;
    onMenuOpenFile: (callback: () => void) => void;
    onMenuSaveFile: (callback: () => void) => void;
    onMenuSaveFileAs: (callback: () => void) => void;
    onMenuExportPdf: (callback: () => void) => void;
  };
  
  // API 密钥管理
  apiKeys: {
    // 保存 API 密钥
    saveApiKey: (keyName: string, keyValue: string) => Promise<{ success: boolean; error?: string }>;
    
    // 获取 API 密钥
    getApiKey: (keyName: string) => Promise<{ success: boolean; keyValue?: string; error?: string }>;
    
    // 删除 API 密钥
    deleteApiKey: (keyName: string) => Promise<{ success: boolean; error?: string }>;
  };
  
  // 后端相关
  backend: {
    // 获取 API 后端 URL
    getApiBaseUrl: () => Promise<string>;
    
    // 检查 Python 后端状态
    checkBackendStatus: () => Promise<{ success: boolean; isRunning?: boolean; error?: string }>;
  };
  
  // 菜单相关
  menu: {
    // 更新最近文件菜单
    updateRecentFiles: (recentFiles: Array<{
      id: string;
      title: string;
      path?: string;
      localFilePath?: string;
      lastOpened: number;
    }>) => void;
    
    // 监听最近文件打开事件
    onOpenRecentFile: (callback: (fileId: string) => void) => void;
    
    // 监听清除最近文件事件
    onClearRecentFiles: (callback: () => void) => void;
  };
}

interface Environment {
  isElectron: boolean;
}

interface Window {
  electronAPI?: ElectronAPI;
  environment?: Environment;
}
