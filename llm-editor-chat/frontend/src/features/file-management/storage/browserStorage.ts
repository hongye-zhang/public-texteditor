/**
 * 浏览器环境下的文件存储实现
 * 使用 IndexedDB 作为主要存储，localStorage 作为回退
 */

export interface EditorFileData {
  id: string;
  title: string;
  content: string;
  editorState: any; // JSON状态
  createdAt: number;
  updatedAt: number;
  isTemporary: boolean;
}

export class BrowserStorage {
  private dbName = 'EditorFiles';
  private dbVersion = 1;
  private storeName = 'files';
  private db: IDBDatabase | null = null;

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, { keyPath: 'id' });
          store.createIndex('updatedAt', 'updatedAt', { unique: false });
          store.createIndex('isTemporary', 'isTemporary', { unique: false });
        }
      };
    });
  }

  async saveFile(fileData: EditorFileData): Promise<void> {
    if (!this.db) await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      
      const request = store.put({
        ...fileData,
        updatedAt: Date.now()
      });
      
      request.onsuccess = () => {
        console.log(`File saved to IndexedDB: ${fileData.id}`);
        // 同时保存到localStorage作为回退（仅保存最后一个文件）
        this.saveToLocalStorageFallback(fileData);
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  async loadFile(id: string): Promise<EditorFileData | null> {
    if (!this.db) await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(id);
      
      request.onsuccess = () => {
        resolve(request.result || null);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async listFiles(): Promise<EditorFileData[]> {
    if (!this.db) await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();
      
      request.onsuccess = () => {
        resolve(request.result || []);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async deleteFile(id: string): Promise<void> {
    if (!this.db) await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(id);
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // localStorage回退机制（用于兼容现有代码）
  private saveToLocalStorageFallback(fileData: EditorFileData): void {
    try {
      localStorage.setItem('tiptap-editor-content', fileData.content);
      localStorage.setItem('tiptap-editor-content_state', JSON.stringify(fileData.editorState));
      localStorage.setItem('tiptap-editor-content_timestamp', fileData.updatedAt.toString());
    } catch (error) {
      console.warn('Failed to save to localStorage fallback:', error);
    }
  }

  // 从localStorage加载（用于兼容现有代码）
  loadFromLocalStorageFallback(): EditorFileData | null {
    try {
      const content = localStorage.getItem('tiptap-editor-content');
      const stateStr = localStorage.getItem('tiptap-editor-content_state');
      const timestamp = localStorage.getItem('tiptap-editor-content_timestamp');
      
      if (!content || !stateStr) return null;
      
      const editorState = JSON.parse(stateStr);
      
      return {
        id: 'localStorage-fallback',
        title: 'Untitled',
        content,
        editorState,
        createdAt: parseInt(timestamp || '0'),
        updatedAt: parseInt(timestamp || '0'),
        isTemporary: true
      };
    } catch (error) {
      console.warn('Failed to load from localStorage fallback:', error);
      return null;
    }
  }

  // 检查IndexedDB是否可用
  static isIndexedDBAvailable(): boolean {
    return typeof indexedDB !== 'undefined';
  }

  // 获取存储使用情况
  async getStorageInfo(): Promise<{used: number, quota: number}> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return {
        used: estimate.usage || 0,
        quota: estimate.quota || 0
      };
    }
    return { used: 0, quota: 0 };
  }
}

// 单例实例
export const browserStorage = new BrowserStorage();
