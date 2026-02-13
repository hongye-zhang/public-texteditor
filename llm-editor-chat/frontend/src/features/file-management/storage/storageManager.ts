/**
 * 统一的存储管理器
 * 根据环境自动选择最合适的存储方式
 */

import { browserStorage, type EditorFileData } from './browserStorage';

export interface StorageManager {
  saveFile(fileData: EditorFileData): Promise<void>;
  loadFile(id: string): Promise<EditorFileData | null>;
  listFiles(): Promise<EditorFileData[]>;
  deleteFile(id: string): Promise<void>;
  init(): Promise<void>;
}

class UnifiedStorageManager implements StorageManager {
  private storage: any = null;
  private isInitialized = false;

  async init(): Promise<void> {
    if (this.isInitialized) return;

    // 检测环境并选择存储方式
    if (this.isElectronEnvironment()) {
      // Electron环境：暂时使用浏览器存储作为回退

      this.storage = browserStorage;
      await this.storage.init();
    } else if (this.isBrowserEnvironment()) {
      // 浏览器环境：使用IndexedDB

      this.storage = browserStorage;
      await this.storage.init();
    } else {
      // 未知环境：使用浏览器存储作为默认回退

      this.storage = browserStorage;
      await this.storage.init();
    }

    this.isInitialized = true;
  }

  async saveFile(fileData: EditorFileData): Promise<void> {
    await this.ensureInitialized();
    



    
    return this.storage.saveFile(fileData);
  }

  async loadFile(id: string): Promise<EditorFileData | null> {
    await this.ensureInitialized();
    
    const fileData = await this.storage.loadFile(id);
    if (fileData) {


      console.log(`Has editor state: ${!!fileData.editorState}`);
    }
    
    return fileData;
  }

  async listFiles(): Promise<EditorFileData[]> {
    await this.ensureInitialized();
    return this.storage.listFiles();
  }

  async deleteFile(id: string): Promise<void> {
    await this.ensureInitialized();
    return this.storage.deleteFile(id);
  }

  // 特殊方法：从localStorage加载（用于迁移现有数据）
  async loadFromLegacyStorage(): Promise<EditorFileData | null> {
    if (this.isBrowserEnvironment()) {
      return browserStorage.loadFromLocalStorageFallback();
    }
    return null;
  }

  // 特殊方法：保存当前编辑器状态
  async saveCurrentEditorState(content: string, editorState: any, title: string = 'Untitled'): Promise<string> {
    const fileData: EditorFileData = {
      id: `temp-${Date.now()}`,
      title,
      content,
      editorState,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isTemporary: true
    };

    await this.saveFile(fileData);
    return fileData.id;
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.isInitialized) {
      await this.init();
    }
  }

  private isElectronEnvironment(): boolean {
    return typeof window !== 'undefined' && 
           window.environment?.isElectron === true;
  }

  private isBrowserEnvironment(): boolean {
    return typeof window !== 'undefined' && 
           typeof indexedDB !== 'undefined';
  }
}

// 导出单例
export const storageManager = new UnifiedStorageManager();

// 便捷函数
export async function saveEditorContent(content: string, editorState: any, title?: string): Promise<string> {
  return storageManager.saveCurrentEditorState(content, editorState, title);
}

export async function loadEditorContent(id?: string): Promise<EditorFileData | null> {
  if (id) {
    return storageManager.loadFile(id);
  } else {
    // 如果没有指定ID，尝试从遗留存储加载
    return storageManager.loadFromLegacyStorage();
  }
}
