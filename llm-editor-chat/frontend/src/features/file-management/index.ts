// Export components
export { default as FileSidebar } from './components/FileSidebar.svelte';
export { default as FileSaveDialog } from './components/FileSaveDialog.svelte';
export { default as DocumentTree } from './components/DocumentTree.svelte';

// Export services
export {
  getAppFolder,
  listFiles,
  getFileContent,
  createFile,
  updateFileContent,
  deleteFile,
  updateFileMetadata,
  type DriveFile
} from './services/googleDriveService';

export {
  sendDocumentTree
} from './services/documentTreeApi';

// Export stores
export {
  fileStore,
  activeFile,
  isFirstFile,
  hasFileSystemPermission
} from './stores/fileStore';

export {
  documentTree,
  documentTreeVisible,
  updateDocumentTree,
  type TreeItem
} from './stores/documentTreeStore';
