import { writable, get, derived } from 'svelte/store';
import { toastStore } from '../../../stores/toastStore';
import type { Writable } from 'svelte/store';
import { isAuthenticated } from '../../auth/stores/googleAuthStore';
import * as googleDriveService from '../services/googleDriveService';
import * as localFileSystemService from '../services/localFileSystemService';
import { storageManager } from '../storage/storageManager';
import { recentFilesStore } from './recentFilesStore';

// File interface
export interface EditorFile {
  id: string;
  title: string;
  content: string; // 文件内容，用于保存到磁盘
  createdAt: number;
  updatedAt: number;
  path?: string; // Optional path for files saved to disk
  localFilePath?: string; // Path for files saved to local filesystem via Electron
  folderPath?: string; // Path to the document folder for folder-based storage
  hasLargeContent?: boolean; // Flag for content that's stored in chunks
  isTemporary?: boolean; // Flag for temporary files (not saved to Google Drive or local filesystem)
  isDirty?: boolean; // Flag to indicate file has unsaved changes
  isSaving?: boolean; // Flag to indicate file is currently being saved
  isSavedLocally?: boolean; // Flag to indicate file is saved locally
  lastLocalSave?: number; // Timestamp of last local save
  lastCloudSave?: number; // Timestamp of last Google Drive save
  editorContent?: any; // 编辑器内容，用于显示在编辑器中，与文件内容区分
  assets?: Array<{ id: string; name: string; type: string; path: string; size: number; createdAt: number }>; // Document assets
}

// File store state interface
interface FileStoreState {
  files: EditorFile[];
  activeFileId: string | null;
  isFirstFile: boolean;
  saveLocation: string | null;
  hasFileSystemPermission: boolean;
  isElectronEnvironment: boolean; // Flag to indicate if running in Electron
  defaultSaveDirectory: string | null; // Default directory for saving files
}

// 检查是否在 Electron 环境中
const isElectronEnvironment = () => {
  // 检查是否在浏览器环境中
  const isBrowser = typeof window !== 'undefined';
  return isBrowser && window.environment?.isElectron === true;
};

// 检查 Electron API 是否可用
const isElectronApiAvailable = () => {
  // 检查是否在浏览器环境中
  const isBrowser = typeof window !== 'undefined';
  return isBrowser && isElectronEnvironment() && window.electronAPI?.fileSystem != null;
};

// Create the file store
const createFileStore = () => {
  // Track current save operations by file ID
  const savePromises: Record<string, Promise<void>> = {};
  // Temporary file for unauthenticated users
  const TEMP_FILE_ID = 'temp-file-' + Date.now();
  
  // Try to load content from localStorage if available
  let savedContent = '';
  if (typeof localStorage !== 'undefined') {
    try {
      const storedContent = localStorage.getItem('tiptap-editor-content');
      if (storedContent) {
        savedContent = storedContent;

      }
    } catch (error) {
      console.error('Error loading content from localStorage:', error);
    }
  }
  
  const temporaryFile: EditorFile = {
    id: TEMP_FILE_ID,
    title: 'Untitled Document',
    content: savedContent, // Use content from localStorage if available
    createdAt: Date.now(),
    updatedAt: Date.now(),
    isTemporary: true
  };

  // Initialize the store with default values
  const initialState: FileStoreState = {
    files: [temporaryFile],
    activeFileId: TEMP_FILE_ID,
    isFirstFile: true,
    saveLocation: null,
    hasFileSystemPermission: false,
    isElectronEnvironment: isElectronEnvironment(),
    defaultSaveDirectory: null
  };
  
  // Create the writable store
  const { subscribe, set, update } = writable<FileStoreState>(initialState);
  
  // Load files from Google Drive
  const loadFromDrive = async () => {
    try {
      // Check if we're authenticated
      if (!get(isAuthenticated)) {

        return;
      }
      
      // Get files from Google Drive
      const driveFiles = await googleDriveService.listFiles();
      
      // Log all files returned from Google Drive for debugging
      console.log(`Found ${driveFiles.length} files in Google Drive:`, 
        driveFiles.map(f => ({ name: f.name, mimeType: f.mimeType })));
      
      // Convert to our file format
      const files: EditorFile[] = [];
      
      for (const file of driveFiles) {
        // Only include JSON files
        if (file.mimeType === 'application/json' || file.name.endsWith('.json')) {
          files.push({
            id: file.id,
            title: file.name,
            content: '', // We'll load content on demand when the file is selected
            createdAt: new Date(file.createdTime).getTime(),
            updatedAt: new Date(file.modifiedTime).getTime(),
            path: file.name
          });
        }
      }

      // Get the current temporary file if it exists
      const currentState = get({ subscribe });
      const tempFile = currentState.files.find(f => f.isTemporary);
      
      // If we have a temporary file, add it to the list
      if (tempFile) {
        files.push(tempFile);
      }
      
      // Update the store
      set({
        files,
        activeFileId: files.length > 0 ? files[0].id : null,
        isFirstFile: files.length === 0,
        saveLocation: 'Google Drive',
        hasFileSystemPermission: true,
        isElectronEnvironment: isElectronEnvironment(),
        defaultSaveDirectory: null
      });
      

    } catch (error) {
      console.error('Error loading files from Google Drive:', error);
    }
  };
  
  // Load files from unified storage manager
  const loadFromUnifiedStorage = async () => {
    try {

      
      // Initialize storage manager if not already done
      await storageManager.init();
      
      // Get files from unified storage
      const storageFiles = await storageManager.listFiles();
      

      
      // Convert to our file format
      const files: EditorFile[] = storageFiles.map(file => ({
        id: file.id,
        title: file.title,
        content: file.content,
        createdAt: file.createdAt,
        updatedAt: file.updatedAt,
        isTemporary: file.isTemporary,
        editorContent: file.editorState // Map editorState to editorContent
      }));
      
      // Update the store with loaded files
      update(state => {
        // Keep temporary files but add loaded files
        const tempFiles = state.files.filter(f => f.isTemporary);
        const nonTempFiles = files.filter(f => !f.isTemporary);
        
        return {
          ...state,
          files: [...tempFiles, ...nonTempFiles]
        };
      });
      

    } catch (error) {
      console.error('Error loading files from unified storage:', error);
    }
  };
  
  // Create a new file
  const createFile = async (title: string, content: string = '', path?: string, skipSaveDialog: boolean = false, editorContent?: any) => {
    try {
      // 检查是否在 Electron 环境中
      if (isElectronApiAvailable()) {
        let filePath = null;
        let documentFolderPath = null;
        
        if (!skipSaveDialog) {
          // 获取默认保存目录
          const defaultSaveDir = await localFileSystemService.getDefaultSaveDirectory();
          if (!defaultSaveDir) {
            throw new Error('Default save directory not available');
          }
          
          // 创建文档ID
          const documentId = `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          
          // 创建文档文件夹结构
          documentFolderPath = await localFileSystemService.createDocumentFolderStructure(defaultSaveDir, documentId);
          
          // 保存文档到文件夹
          const documentData = {
            id: documentId,
            title: title,
            content: content,
            createdAt: Date.now(),
            updatedAt: Date.now()
          };
          
          filePath = await localFileSystemService.saveDocumentToFolder(documentFolderPath, documentId, documentData);
          if (!filePath) {
            return null;
          }
          
          // 添加到最近文件列表
          await localFileSystemService.addToRecentFiles(filePath);
        }
        
        // 读取文件名称（从路径中提取）
        const fileName = filePath ? filePath.split(/[\\/]/).pop() || title : title;
        
        // 创建新文件对象
        const newFile: EditorFile = {
          id: `local-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          title: fileName,
          content: content, // 这是文件内容，用于保存到磁盘
          createdAt: Date.now(),
          updatedAt: Date.now(),
          localFilePath: filePath || undefined, // 修复类型错误，filePath可能为null，需要转换为undefined
          folderPath: documentFolderPath || undefined, // 文档文件夹路径
          isTemporary: skipSaveDialog, // 如果跳过保存对话框，标记为临时文件
          editorContent: editorContent, // 这是编辑器内容，用于显示在编辑器中
          assets: [] // 初始化空的资源列表
        };
        
        // 更新存储
        update(state => {
          const newState = {
            ...state,
            files: [newFile, ...state.files.filter(f => !f.isTemporary || skipSaveDialog)],
            activeFileId: newFile.id,
            isFirstFile: false
          };
          return newState;
        });
        
        return newFile.id;
      } else {
        // 在 Web 环境中使用 Google Drive
        // Check if we're authenticated
        if (!get(isAuthenticated)) {
          console.error('Not authenticated with Google Drive, cannot create file');
          return null;
        }
        
        // Create file in Google Drive
        const newDriveFile = await googleDriveService.createFile(title, content);
        
        // Add to our store
        const newFile: EditorFile = {
          id: newDriveFile.id,
          title: newDriveFile.name,
          content: content,
          createdAt: new Date(newDriveFile.createdTime).getTime(),
          updatedAt: new Date(newDriveFile.modifiedTime).getTime(),
          path: newDriveFile.name
        };
        
        update(state => {
          const newState = {
            ...state,
            files: [newFile, ...state.files.filter(f => !f.isTemporary)],
            activeFileId: newFile.id,
            isFirstFile: false
          };
          return newState;
        });
        
        return newFile.id;
      }
    } catch (error) {
      console.error('Error creating file:', error);
      toastStore.showErrorToast('创建文件失败', error instanceof Error ? error.message : '未知错误');
      return null;
    }
  };
  
  // Select a save location
  const selectSaveLocation = async (): Promise<string | null> => {
    // In Electron environment, we use the native file dialog
    if (isElectronApiAvailable()) {
      try {
        const directory = await localFileSystemService.getDefaultSaveDirectory();
        if (directory) {
          // Update the default save directory in the store
          update(state => ({ ...state, defaultSaveDirectory: directory }));
          return directory;
        }
        return null;
      } catch (error) {
        console.error('Error selecting save location:', error);
        return null;
      }
    }
    
    // For web environment, return Google Drive
    return 'Google Drive';
  };
  
  // Check if we have file system access
  const checkFileSystemAccess = async (): Promise<boolean> => {
    // In Electron environment, we always have file system access
    if (isElectronApiAvailable()) {
      return true;
    }
    
    // For web environment, check if authenticated with Google Drive
    return get(isAuthenticated);
  };
  
  // Save file to disk
  const saveFileToDisk = async (id: string, suggestedName: string): Promise<string | null> => {
    try {
      // Get the current state
      const state = get({ subscribe });
      const file = state.files.find(f => f.id === id);
      
      // If the file doesn't exist, do nothing
      if (!file) {
        console.error('File not found:', id);
        return null;
      }
      
      // Check if we're in Electron environment
      if (!isElectronApiAvailable()) {
        throw new Error('Electron API not available, cannot save file');
      }
      
      // Get default save directory
      const defaultSaveDir = await localFileSystemService.getDefaultSaveDirectory();
      if (!defaultSaveDir) {
        throw new Error('Default save directory not available');
      }
      
      // Create document folder structure
      const documentId = id.replace(/[^a-zA-Z0-9-_]/g, '-');
      const documentFolderPath = await localFileSystemService.createDocumentFolderStructure(defaultSaveDir, documentId);
      
      // Save document to folder
      const documentData = {
        id: documentId,
        title: suggestedName,
        content: file.content,
        createdAt: file.createdAt,
        updatedAt: Date.now()
      };
      
      const filePath = await localFileSystemService.saveDocumentToFolder(documentFolderPath, documentId, documentData);
      
      if (!filePath) {
        return null;
      }
      
      // 从文件路径中提取文件名
      const fileName = suggestedName;
      
      // Update the file metadata in the store
      update(state => {
        const newFiles = state.files.map(f => 
          f.id === id 
            ? { 
                ...f, 
                title: fileName, // 更新文件标题为新文件名
                localFilePath: filePath,
                folderPath: documentFolderPath,
                lastLocalSave: Date.now(),
                isDirty: false,
                assets: [] // Initialize empty assets array
              } 
            : f
        );
        return { ...state, files: newFiles };
      });
      
      // Add to recent files list
      await localFileSystemService.addToRecentFiles(filePath);

      return filePath;
    } catch (error) {
      console.error('Error saving file to disk:', error);
      throw error;
    }
  };
  
  // Update a file's content
  const updateFileContent = async (id: string, content: string, editorContent?: any): Promise<void> => {
    try {
      // Get the current state
      const state = get({ subscribe });
      const file = state.files.find(f => f.id === id);
      
      // If the file doesn't exist, do nothing
      if (!file) {
        console.error('File not found:', id);
        return;
      }
      
      // Update the content and mark as dirty
      const updatedContent = content; // Store content in a variable to avoid reference issues
      
      // First update the content in the store without marking dirty yet
      update(state => {
        const newFiles = state.files.map(f => 
          f.id === id 
            ? { 
                ...f, 
                content: updatedContent, 
                isDirty: true,
                // 如果提供了editorContent，则更新它
                ...(editorContent !== undefined ? { editorContent } : {})
              } 
            : f
        );
        return { ...state, files: newFiles };
      });
      
      // 记录日志，便于调试
      if (editorContent !== undefined) {
        console.log(`Updated file ${id} with editorContent:`, typeof editorContent);
      }
      
      // If this is a temporary file, update it locally and save to localStorage
      if (file.isTemporary) {
        update(state => {
          const newFiles = state.files.map(file => 
            file.id === id 
              ? { ...file, content, updatedAt: Date.now(), isDirty: false } 
              : file
          );
          
          return { ...state, files: newFiles };
        });
        
        // Save to localStorage if available
        if (typeof localStorage !== 'undefined') {
          try {
            // Use the same key as in TiptapEditor.svelte
            localStorage.setItem('tiptap-editor-content', content);
            localStorage.setItem('tiptap-editor-content_timestamp', Date.now().toString());
            // Note: tiptap-editor-content_state is managed by TiptapEditor.svelte
          } catch (error) {
            console.error('Error saving temporary file to localStorage:', error);
          }
        }
        
        return;
      }
      
      // 检查是否在 Electron 环境中
      if (isElectronApiAvailable()) {
        // Mark file as saving
        update(state => {
          const newFiles = state.files.map(f => 
            f.id === id 
              ? { ...f, isSaving: true } 
              : f
          );
          return { ...state, files: newFiles };
        });
        
        // Create a save promise and track it
        const savePromise = (async () => {
          try {
            let filePath = file.localFilePath;
            
            // 如果文件没有本地路径，则弹出保存对话框并创建文件夹结构
            if (!filePath) {
              // 使用saveFileToDisk函数，它会创建文件夹结构并保存文档
              const newPath = await saveFileToDisk(id, file.title);
              if (!newPath) {
                throw new Error('用户取消了保存操作');
              }
              filePath = newPath; // 如果不为 null，才赋值
            } else if (file.folderPath) {
              // 如果有文件夹路径，使用文件夹结构保存
              const documentData = {
                id: id.replace(/[^a-zA-Z0-9-_]/g, '-'),
                title: file.title,
                content: content,
                createdAt: file.createdAt,
                updatedAt: Date.now()
              };
              
              await localFileSystemService.saveDocumentToFolder(file.folderPath, documentData.id, documentData);
            } else {
              // 如果只有文件路径但没有文件夹路径，使用旧方法保存
              await localFileSystemService.saveFile(filePath, content);
            }
            
            // 添加到最近文件列表
            await localFileSystemService.addToRecentFiles(filePath);
            
            // Update our store after successful save
            const now = Date.now();
            update(state => {
              const newFiles = state.files.map(file => 
                file.id === id 
                  ? { 
                      ...file, 
                      content, 
                      updatedAt: now, 
                      isDirty: false, 
                      isSaving: false,
                      lastLocalSave: now,
                      localFilePath: filePath
                    } 
                  : file
              );
              
              return { ...state, files: newFiles };
            });
            

          } catch (error) {
            console.error('保存文件失败:', error);
            toastStore.showErrorToast('保存失败', error instanceof Error ? error.message : '未知错误');
            
            // Keep dirty flag but remove saving flag on error
            update(state => {
              const newFiles = state.files.map(file => 
                file.id === id 
                  ? { ...file, isSaving: false } 
                  : file
              );
              
              return { ...state, files: newFiles };
            });
          } finally {
            // Clean up the promise when done
            delete savePromises[id];
          }
        })();
        
        // Store the promise for tracking
        savePromises[id] = savePromise;
        
        // Return the promise so caller can await it if needed
        return savePromise;
      }
      
      // 如果不是 Electron 环境，则使用 Google Drive
      // Otherwise, check if we're authenticated for Google Drive files
      if (!get(isAuthenticated)) {
        console.error('Not authenticated with Google Drive, cannot update file');
        return;
      }
      
      // Mark file as saving
      update(state => {
        const newFiles = state.files.map(f => 
          f.id === id 
            ? { ...f, isSaving: true } 
            : f
        );
        return { ...state, files: newFiles };
      });
      
      // Create a save promise and track it
      const savePromise = (async () => {
        try {
          // Update file in Google Drive
          await googleDriveService.updateFileContent(id, content);
          
          // Update our store after successful save
          const now = Date.now();
          update(state => {
            const newFiles = state.files.map(file => 
              file.id === id 
                ? { 
                    ...file, 
                    content, 
                    updatedAt: now, 
                    isDirty: false, 
                    isSaving: false,
                    lastCloudSave: now
                  } 
                : file
            );
            
            return { ...state, files: newFiles };
          });
          

        } catch (error) {
          console.error('Error updating file content:', error);
          
          // Keep dirty flag but remove saving flag on error
          update(state => {
            const newFiles = state.files.map(file => 
              file.id === id 
                ? { ...file, isSaving: false } 
                : file
            );
            
            return { ...state, files: newFiles };
          });
        } finally {
          // Clean up the promise when done
          delete savePromises[id];
        }
      })();
      
      // Store the promise for tracking
      savePromises[id] = savePromise;
      
      // Return the promise so caller can await it if needed
      return savePromise;
    } catch (error) {
      console.error('Error in updateFileContent:', error);
    }
  };
  
  // Update a file's metadata
  const updateFileMetadata = async (id: string, metadata: Partial<EditorFile>) => {
    try {
      // Get the current state
      const state = get({ subscribe });
      const file = state.files.find(f => f.id === id);
      
      // If the file doesn't exist, do nothing
      if (!file) {
        console.error('File not found:', id);
        return;
      }
      
      // If this is a temporary file, just update it locally
      if (file.isTemporary) {
        update(state => {
          const newFiles = state.files.map(file => 
            file.id === id 
              ? { ...file, ...metadata, updatedAt: Date.now() } 
              : file
          );
          
          return { ...state, files: newFiles };
        });
        return;
      }
      
      // Otherwise, check if we're authenticated for Google Drive files
      if (!get(isAuthenticated)) {
        console.error('Not authenticated with Google Drive, cannot update file metadata');
        return;
      }
      
      // If title is being updated, update in Google Drive
      if (metadata.title) {
        await googleDriveService.updateFileMetadata(id, { name: metadata.title });
      }
      
      // Update our store
      update(state => {
        const newFiles = state.files.map(file => 
          file.id === id 
            ? { ...file, ...metadata, updatedAt: Date.now() } 
            : file
        );
        
        return { ...state, files: newFiles };
      });
    } catch (error) {
      console.error('Error updating file metadata:', error);
    }
  };
  
  // Set the active file
  const setActiveFile = async (id: string): Promise<void> => {
    const state = get({ subscribe });
    const file = state.files.find((f: EditorFile) => f.id === id);
    
    // If file not found, do nothing
    if (!file) {
      console.error(`File with id ${id} not found`);
      return;
    }
    
    // 更新最近文件列表（只有有localFilePath的文件才添加）
    if (file.localFilePath) {
      recentFilesStore.addRecentFile({
        id: file.id,
        title: file.title,
        path: file.path,
        localFilePath: file.localFilePath
      });
    }
    
    // If file is already active, do nothing else
    if (state.activeFileId === id) {
      return;
    }
    
    // Check if current file is dirty and needs saving
    const currentFile = state.files.find((f: EditorFile) => f.id === state.activeFileId);
    if (currentFile && currentFile.isDirty) {
      // Show toast notification that we're saving before switching
      const toastId = toastStore.showSavingToast(currentFile.title);
      
      try {
        // Set cursor to wait state
        document.body.style.cursor = 'wait';
        
        if (currentFile.isSaving) {
          // If the file is currently being saved, wait for the save to complete

          
          // Wait for the save promise to complete if it exists
          const savePromise = savePromises[currentFile.id];
          if (savePromise) {
            await savePromise;

          }
        } else {
          // If dirty but not saving, force an immediate save

          await forceSaveFile(currentFile.id);
        }
      } finally {
        // Hide the toast and restore cursor
        toastStore.hideSavingToast(toastId);
        document.body.style.cursor = 'default';
      }
    }
    
    // If content is not loaded yet, load it
    if (!file.content) {
      try {
        // Show loading toast
        const toastId = toastStore.showLoadingToast(file.title);
        document.body.style.cursor = 'wait';
        
        try {
          let content = '';
          
          // 检查是否在 Electron 环境中并且有本地文件路径
          if (isElectronApiAvailable() && file.localFilePath) {
            // 检查是否是文件夹结构
            if (file.folderPath) {
              // 从文件夹结构加载文档
              try {
                const documentData = await localFileSystemService.loadDocumentFromFolder(file.folderPath);
                content = documentData.content;
                
                // 加载文档资源列表
                const assets = await localFileSystemService.listDocumentAssets(file.folderPath);
                
                // 更新文件的资源列表
                update((state: FileStoreState) => {
                  const newFiles = state.files.map((f: EditorFile) => 
                    f.id === id 
                      ? { ...f, assets } 
                      : f
                  );
                  return { ...state, files: newFiles };
                });
              } catch (folderError) {
                console.error('从文件夹加载文档失败，尝试使用传统方式:', folderError);
                // 如果文件夹加载失败，尝试使用传统方式
                const fileInfo = await localFileSystemService.readFile(file.localFilePath);
                content = fileInfo.content;
              }
            } else {
              // 使用传统方式从单个文件加载
              const fileInfo = await localFileSystemService.readFile(file.localFilePath);
              content = fileInfo.content;
            }
          } else {
            // 从 Google Drive 加载文件
            content = await googleDriveService.getFileContent(id);
          }
          
          // Validate content is not empty
          if (!content || content.trim() === '') {
            toastStore.showErrorToast('加载文件失败', '文件内容为空');
            throw new Error('文件内容为空');
          }
          
          // Update the file with content
          update((state: FileStoreState) => {
            const newFiles = state.files.map((f: EditorFile) => 
              f.id === id 
                ? { ...f, content } 
                : f
            );
            
            return {
              ...state,
              files: newFiles,
              activeFileId: id
            };
          });
        } finally {
          // Hide loading toast and restore cursor
          toastStore.hideLoadingToast(toastId);
          document.body.style.cursor = 'default';
        }
      } catch (loadError) {
        console.error('加载文件内容失败:', loadError);
        toastStore.showErrorToast('加载文件失败', loadError instanceof Error ? loadError.message : '未知错误');
        // Don't change the active file if loading failed
        return;
      }
    } else {
      // Just update the active file ID
      update((state: FileStoreState) => ({
        ...state,
        activeFileId: id
      }));
    }
    
    // 最近文件列表已在函数开始时更新

  };



  // Delete a file
  const deleteFile = async (id: string) => {
    try {
      // Get the current state
      const state = get({ subscribe });
      const file = state.files.find(f => f.id === id);
      
      // If the file doesn't exist, do nothing
      if (!file) {
        console.error('File not found:', id);
        return;
      }
      
      // Don't allow deleting the temporary file
      if (file.isTemporary) {
        console.error('Cannot delete temporary file');
        return;
      }
      
      // Check if we're authenticated
      if (!get(isAuthenticated)) {
        console.error('Not authenticated with Google Drive, cannot delete file');
        return;
      }
      
      // Delete file from Google Drive
      await googleDriveService.deleteFile(id);
      
      // Update our store
      update(state => {
        const newFiles = state.files.filter(file => file.id !== id);
        
        // If we deleted the active file, set a new active file
        let newActiveFileId = state.activeFileId;
        if (state.activeFileId === id) {
          newActiveFileId = newFiles.length > 0 ? newFiles[0].id : null;
        }
        
        return {
          ...state,
          files: newFiles,
          activeFileId: newActiveFileId,
          isFirstFile: newFiles.length === 0
        };
      });
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  };

  // Initialize Google Drive integration
  const initializeDrive = async () => {
    // Load files if authenticated
    if (get(isAuthenticated)) {
      await loadFromDrive();
    }
    
    // Listen for authentication changes
    isAuthenticated.subscribe(async (authenticated) => {
      if (authenticated) {

        
        // Add retry mechanism for loading files after login
        let retryCount = 0;
        const maxRetries = 3;
        const retryDelay = 1000; // 1 second delay between retries
        
        const attemptLoadFiles = async (): Promise<boolean> => {
          try {
            await loadFromDrive();
            const currentState = get({ subscribe });
            const filesLoaded = currentState.files.filter(f => !f.isTemporary).length > 0;
            
            if (filesLoaded) {

              return true;
            } else {

              return false;
            }
          } catch (error) {
            console.error('Error loading files from Drive:', error);
            return false;
          }
        };
        
        // First attempt
        let success = await attemptLoadFiles();
        
        // Retry if needed
        while (!success && retryCount < maxRetries) {
          retryCount++;

          
          // Wait before retrying
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          success = await attemptLoadFiles();
        }
        
        if (!success) {
          console.warn(`Failed to load files after ${maxRetries} attempts`);
        }
      } else {
        // When logging out, keep only the temporary file

        update(state => {
          // Find or create a temporary file
          let tempFile = state.files.find(f => f.isTemporary);
          
          if (!tempFile) {
            tempFile = {
              id: TEMP_FILE_ID,
              title: 'Untitled Document',
              content: '',
              createdAt: Date.now(),
              updatedAt: Date.now(),
              isTemporary: true
            };
          }
          
          return {
            files: [tempFile],
            activeFileId: tempFile.id,
            isFirstFile: true,
            saveLocation: null,
            hasFileSystemPermission: false,
            isElectronEnvironment: isElectronEnvironment(),
            defaultSaveDirectory: null
          };
        });
      }
    });
  };
  
  // 加载本地文件
  const loadLocalFiles = async () => {
    try {
      // 获取最近文件列表
      const recentFiles = await localFileSystemService.getRecentFiles();
      const files: EditorFile[] = [];
      
      for (const recentFile of recentFiles) {
        files.push({
          id: `local-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          title: recentFile.name,
          content: '', // 内容将在文件被选中时加载
          createdAt: recentFile.lastOpened,
          updatedAt: recentFile.lastOpened,
          localFilePath: recentFile.path,
          isTemporary: false
        });
      }
      
      // 获取当前临时文件
      const currentState = get({ subscribe });
      const tempFile = currentState.files.find(f => f.isTemporary);
      
      // 如果有临时文件，添加到列表
      if (tempFile) {
        files.push(tempFile);
      }
      
      // 获取默认保存目录
      let defaultSaveDirectory = null;
      try {
        defaultSaveDirectory = await localFileSystemService.getDefaultSaveDirectory();
      } catch (error) {
        console.log('未设置默认保存目录');
      }
      
      // 更新存储
      set({
        ...currentState,
        files,
        activeFileId: files.length > 0 ? files[0].id : currentState.activeFileId,
        isFirstFile: files.length === 0,
        saveLocation: '本地文件系统',
        hasFileSystemPermission: true,
        isElectronEnvironment: true,
        defaultSaveDirectory
      });
      

    } catch (error) {
      console.error('从本地文件系统加载文件失败:', error);
    }
  };
  
  // 初始化
  const initialize = async () => {
    // 检查是否在浏览器环境中
    const isBrowser = typeof window !== 'undefined';

    
    // 只在浏览器环境中执行后续代码
    if (!isBrowser) {

      return;
    }
    
    // 添加调试信息



    
    // 直接检查 window.environment.isElectron
    const isElectron = window.environment?.isElectron === true;

    
    // 检查是否在 Electron 环境中
    if (isElectron && window.electronAPI?.fileSystem) {

      await loadLocalFiles();
    } else {

      await initializeDrive();
    }
  };
  
  // Initialize on creation
  setTimeout(() => {
    initialize();
  }, 0);
  
  // Force save a file immediately
  const forceSaveFile = async (id: string): Promise<void> => {
    try {
      // Get the current state using the store's subscribe method
      const state = get({ subscribe });
      const file = state.files.find((f: EditorFile) => f.id === id);
      
      // If the file doesn't exist, do nothing
      if (!file) {
        console.error('File not found:', id);
        return;
      }
      
      // If the file is already saving, wait for that save to complete
      if (file.isSaving && id in savePromises) {

        await savePromises[id];
        return;
      }
      
      // If the file isn't dirty, no need to save
      if (!file.isDirty) {

        return;
      }
      
      // Mark file as saving
      update((state: FileStoreState) => {
        const newFiles = state.files.map((f: EditorFile) => 
          f.id === id 
            ? { ...f, isSaving: true } 
            : f
        );
        return { ...state, files: newFiles };
      });
      
      // Create a save promise and track it
      const savePromise = (async () => {
        try {
          // Check if file is local or on Google Drive
          if (isElectronApiAvailable() && file.localFilePath) {
            // Save to local filesystem
            await localFileSystemService.saveFile(file.localFilePath, file.content);
            
            // Update our store after successful save
            const now = Date.now();
            update((state: FileStoreState) => {
              const newFiles = state.files.map((f: EditorFile) => 
                f.id === id 
                  ? { 
                      ...f, 
                      updatedAt: now, 
                      isDirty: false, 
                      isSaving: false,
                      lastLocalSave: now
                    } 
                  : f
              );
              
              return { ...state, files: newFiles };
            });
          } else if (get(isAuthenticated) && !file.isTemporary) {
            // Save to Google Drive
            await googleDriveService.updateFileContent(id, file.content);
            
            // Update our store after successful save
            const now = Date.now();
            update((state: FileStoreState) => {
              const newFiles = state.files.map((f: EditorFile) => 
                f.id === id 
                  ? { 
                      ...f, 
                      updatedAt: now, 
                      isDirty: false, 
                      isSaving: false,
                      lastCloudSave: now
                    } 
                  : f
              );
              
              return { ...state, files: newFiles };
            });
          } else if (file.isTemporary) {
            // Save temporary file to localStorage
            if (typeof localStorage !== 'undefined') {
              try {
                localStorage.setItem('tiptap-editor-content', file.content);
                localStorage.setItem('tiptap-editor-content_timestamp', Date.now().toString());
                // Note: tiptap-editor-content_state is managed by TiptapEditor.svelte
              } catch (error) {
                console.error('Error saving temporary file to localStorage:', error);
              }
            }
            
            // Update our store
            const now = Date.now();
            update((state: FileStoreState) => {
              const newFiles = state.files.map((f: EditorFile) => 
                f.id === id 
                  ? { 
                      ...f, 
                      updatedAt: now, 
                      isDirty: false, 
                      isSaving: false
                    } 
                  : f
              );
              
              return { ...state, files: newFiles };
            });
          } else {
            console.error('Cannot save file: not authenticated or no valid save location');
            // Reset the saving flag
            update((state: FileStoreState) => {
              const newFiles = state.files.map((f: EditorFile) => 
                f.id === id 
                  ? { ...f, isSaving: false } 
                  : f
              );
              
              return { ...state, files: newFiles };
            });
          }
        } catch (error) {
          console.error('Error saving file:', error);
          toastStore.showErrorToast('保存失败', error instanceof Error ? error.message : '未知错误');
          
          // Reset the saving flag on error
          update((state: FileStoreState) => {
            const newFiles = state.files.map((f: EditorFile) => 
              f.id === id 
                ? { ...f, isSaving: false } 
                : f
            );
            
            return { ...state, files: newFiles };
          });
        } finally {
          // Clean up the promise when done
          delete savePromises[id];
        }
      })();
      
      // Store the promise for tracking
      savePromises[id] = savePromise;
      
      // Return the promise so caller can await it if needed
      return savePromise;
    } catch (error) {
      console.error('Error in forceSaveFile:', error);
    }
  };

  // Check if any file is currently being saved
  const isAnySaving = (): boolean => {
    const state = get({ subscribe });
    return state.files.some(file => file.isSaving);
  };

  // Wait for all saves to complete
  const waitForSaves = async (): Promise<void> => {
    const pendingSaves = Object.values(savePromises);
    if (pendingSaves.length > 0) {
      await Promise.all(pendingSaves);
    }
  };

  return {
    subscribe,
    createFile,
    updateFileContent,
    updateFileMetadata,
    setActiveFile,
    deleteFile,
    initializeDrive,
    loadFromUnifiedStorage,
    forceSaveFile,
    isAnySaving,
    waitForSaves,
    // These methods are kept for API compatibility but now use Google Drive
    setSaveLocation: (location: string) => {
      update(state => ({ ...state, saveLocation: location }));
    },
    setDirectoryHandle: () => {
      console.log('Directory handles not used with Google Drive integration');
    },
    getDirectoryHandle: () => null,
    setFileSystemPermission: (hasPermission: boolean) => {
      update(state => ({ ...state, hasFileSystemPermission: hasPermission }));
    },
    saveFileToDisk,
    selectSaveLocation,
    checkFileSystemAccess,
    scanDirectoryForFiles: async () => {
      await loadFromDrive();
    },
    restoreDirectoryHandle: async () => get(isAuthenticated),
    refreshFiles: async () => {
      await loadFromDrive();
    }
  };
};

// Create and export the file store
export const fileStore = createFileStore();

// Derived store for the active file
export const activeFile = derived(
  fileStore,
  $fileStore => $fileStore.files.find(file => file.id === $fileStore.activeFileId) || null
);

// Derived store for whether this is the first file
export const isFirstFile = derived(
  fileStore,
  $fileStore => $fileStore.isFirstFile
);

// Derived store for whether we have file system permission
export const hasFileSystemPermission = derived(
  fileStore,
  $fileStore => $fileStore.hasFileSystemPermission
);
