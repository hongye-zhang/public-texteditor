/**
 * TypeScript declarations for Electron API
 * This file provides type definitions for the Electron API used in the application
 */

declare interface Window {
  environment?: {
    isElectron: boolean;
  };
  electronAPI?: {
    fileSystem: {
      // Existing API methods
      saveFileAs: (content: string, suggestedName: string) => Promise<string | null>;
      saveFile: (filePath: string, content: string) => Promise<string>;
      openFile: () => Promise<{ path: string; content: string; name: string } | null>;
      openFolder: () => Promise<string | null>;
      readFile: (filePath: string) => Promise<{ path: string; content: string; name: string }>;
      listFiles: (folderPath: string) => Promise<Array<{
        name: string;
        path: string;
        isDirectory: boolean;
        size?: number;
        modifiedTime: number;
      }>>;
      getRecentFiles: () => Promise<Array<{
        path: string;
        name: string;
        lastOpened: number;
      }>>;
      addToRecentFiles: (filePath: string) => Promise<Array<{
        path: string;
        name: string;
        lastOpened: number;
      }>>;
      getDefaultSaveDirectory: () => Promise<string>;
      setDefaultSaveDirectory: (directoryPath: string) => Promise<string>;
      
      // New API methods for folder-based document storage
      createDirectory: (directoryPath: string) => Promise<string>;
      checkPathExists: (path: string) => Promise<boolean>;
      saveAsset: (filePath: string, content: string | ArrayBuffer) => Promise<string>;
      readAsset: (filePath: string) => Promise<ArrayBuffer>;
      deleteFile: (filePath: string) => Promise<void>;
    };
    onMenuExportPdf: (callback: () => void) => void;
  };
}
