import { writable, get } from 'svelte/store';

// Recent file interface
export interface RecentFile {
  id: string;
  title: string;
  path?: string;
  localFilePath?: string;
  lastOpened: number;
}

// Recent files store state
interface RecentFilesState {
  files: RecentFile[];
}

const MAX_RECENT_FILES = 10;
const RECENT_FILES_STORAGE_KEY = 'recent-files';

// Create the recent files store
function createRecentFilesStore() {
  // Load initial state from localStorage
  const loadRecentFiles = (): RecentFile[] => {
    try {
      const stored = localStorage.getItem(RECENT_FILES_STORAGE_KEY);
      if (stored) {
        const files = JSON.parse(stored) as RecentFile[];
        
        // Filter out files without localFilePath (cleanup historical data)
        const validFiles = files.filter(file => {
          if (!file.localFilePath) {
            console.warn('Removing recent file without localFilePath:', file);
            return false;
          }
          // Also check for other required fields
          if (!file.id || !file.title || !file.lastOpened) {
            console.warn('Removing recent file with missing required fields:', file);
            return false;
          }
          return true;
        });
        
        // If we cleaned up some files, save the cleaned data back to localStorage
        if (validFiles.length !== files.length) {
          console.log(`Cleaned up recent files: ${files.length} -> ${validFiles.length}`);
          try {
            localStorage.setItem(RECENT_FILES_STORAGE_KEY, JSON.stringify(validFiles));
          } catch (saveError) {
            console.error('Error saving cleaned recent files:', saveError);
          }
        }
        
        // Sort by lastOpened descending and limit to MAX_RECENT_FILES
        return validFiles
          .sort((a, b) => b.lastOpened - a.lastOpened)
          .slice(0, MAX_RECENT_FILES);
      }
    } catch (error) {
      console.error('Error loading recent files:', error);
      // If localStorage is corrupted, clear it
      try {
        localStorage.removeItem(RECENT_FILES_STORAGE_KEY);
        console.log('Cleared corrupted recent files data');
      } catch (clearError) {
        console.error('Error clearing corrupted recent files:', clearError);
      }
    }
    return [];
  };

  const initialState: RecentFilesState = {
    files: loadRecentFiles()
  };

  const { subscribe, update } = writable(initialState);

  // Save recent files to localStorage
  const saveToStorage = (files: RecentFile[]) => {
    try {
      // Strict validation: only save files with valid file paths
      const validFiles = files.filter(file => {
        // Check required fields
        if (!file.id || !file.title || !file.lastOpened) {
          console.error('Skipping recent file with missing required fields:', { id: file.id, title: file.title, hasLastOpened: !!file.lastOpened });
          return false;
        }
        
        // CRITICAL: Check for file path - this is mandatory for recent files
        if (!file.localFilePath) {
          console.error('Skipping recent file without localFilePath - this is required for recent files:', { id: file.id, title: file.title });
          return false;
        }
        
        // Additional validation: ensure localFilePath is not empty string
        if (typeof file.localFilePath === 'string' && file.localFilePath.trim() === '') {
          console.error('Skipping recent file with empty localFilePath:', { id: file.id, title: file.title });
          return false;
        }
        
        return true;
      });
      
      // Log filtering results
      const filteredCount = files.length - validFiles.length;
      if (filteredCount > 0) {
        console.warn(`Filtered out ${filteredCount} invalid files before saving to localStorage`);
        console.log('Valid files being saved:', validFiles.map(f => ({ id: f.id, title: f.title, localFilePath: f.localFilePath })));
      }
      
      localStorage.setItem(RECENT_FILES_STORAGE_KEY, JSON.stringify(validFiles));
      console.log(`Successfully saved ${validFiles.length} valid recent files to localStorage`);
    } catch (error) {
      console.error('Error saving recent files to localStorage:', error);
    }
  };

  // Add or update a recent file
  const addRecentFile = (file: {
    id: string;
    title: string;
    path?: string;
    localFilePath?: string;
  }) => {
    // Strict validation: reject files without required fields
    if (!file.id || !file.title) {
      console.error('Cannot add recent file: missing required fields (id, title)', file);
      return;
    }
    
    // CRITICAL: Reject files without localFilePath - this is mandatory
    if (!file.localFilePath) {
      console.error('Cannot add recent file: localFilePath is required', { id: file.id, title: file.title });
      return;
    }
    
    // Additional validation: ensure localFilePath is not empty string
    if (typeof file.localFilePath === 'string' && file.localFilePath.trim() === '') {
      console.error('Cannot add recent file: localFilePath cannot be empty', { id: file.id, title: file.title });
      return;
    }
    
    console.log('Adding valid recent file:', { id: file.id, title: file.title, localFilePath: file.localFilePath });
    
    update(state => {
      const now = Date.now();
      const recentFile: RecentFile = {
        ...file,
        lastOpened: now
      };
      
      // Double-check that critical fields are preserved
      if (!recentFile.localFilePath && file.localFilePath) {
        console.error('Critical: localFilePath was lost during object creation!');
        recentFile.localFilePath = file.localFilePath;
      }

      // Remove existing entry if it exists (based on file path, not ID)
      // Priority: localFilePath > path > title (for fallback)
      const existingIndex = state.files.findIndex(f => {
        if (file.localFilePath && f.localFilePath) {
          return f.localFilePath === file.localFilePath;
        }
        if (file.path && f.path) {
          return f.path === file.path;
        }
        // Fallback to title comparison (less reliable but better than nothing)
        return f.title === file.title;
      });
      
      let newFiles = [...state.files];
      
      if (existingIndex >= 0) {
        // Update existing entry (keep the same position, just update the data)
        newFiles[existingIndex] = recentFile;
      } else {
        // Add new entry at the beginning
        newFiles.unshift(recentFile);
      }

      // Sort by lastOpened descending and limit to MAX_RECENT_FILES
      newFiles = newFiles
        .sort((a, b) => b.lastOpened - a.lastOpened)
        .slice(0, MAX_RECENT_FILES);

      // Save to localStorage
      saveToStorage(newFiles);

      return { ...state, files: newFiles };
    });
  };

  // Remove a recent file
  const removeRecentFile = (id: string) => {
    update(state => {
      const newFiles = state.files.filter(f => f.id !== id);
      saveToStorage(newFiles);
      return { ...state, files: newFiles };
    });
  };

  // Clear all recent files
  const clearRecentFiles = () => {
    update(state => {
      saveToStorage([]);
      return { ...state, files: [] };
    });
  };

  // Update file title in recent files
  const updateRecentFileTitle = (id: string, title: string) => {
    update(state => {
      const newFiles = state.files.map(f => 
        f.id === id ? { ...f, title } : f
      );
      saveToStorage(newFiles);
      return { ...state, files: newFiles };
    });
  };

  // Data integrity check and repair function
  const checkAndRepairData = () => {
    const state = get({ subscribe });
    const originalCount = state.files.length;
    
    const validFiles = state.files.filter((file: RecentFile) => {
      if (!file.id || !file.title || !file.lastOpened) {
        console.warn('Found and removing invalid recent file:', file);
        return false;
      }
      return true;
    });
    
    if (validFiles.length !== originalCount) {
      console.log(`Data integrity check: repaired ${originalCount - validFiles.length} invalid entries`);
      update(state => ({ ...state, files: validFiles }));
      saveToStorage(validFiles);
    }
    
    return validFiles.length;
  };

  // Get current files array
  const getFiles = (): RecentFile[] => {
    const state = get({ subscribe });
    return state.files;
  };

  return {
    subscribe,
    addRecentFile,
    removeRecentFile,
    clearRecentFiles,
    updateRecentFileTitle,
    checkAndRepairData,
    getFiles
  };
}

// Create and export the recent files store
export const recentFilesStore = createRecentFilesStore();
