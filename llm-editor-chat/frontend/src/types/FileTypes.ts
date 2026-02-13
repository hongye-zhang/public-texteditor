/**
 * File interface representing a document in the editor
 */
export interface EditorFile {
  /** Unique identifier for the file */
  id: string;
  /** Name of the file */
  name: string;
  /** Content of the file */
  content: string;
  /** When the file was created */
  created: Date;
  /** When the file was last modified */
  lastModified: Date;
  /** File type/format (e.g., 'markdown', 'html', etc.) */
  type: string;
  /** File path or location */
  path?: string;
}

/**
 * File store state interface for managing files in the sidebar
 */
export interface FileStoreState {
  /** List of files */
  files: EditorFile[];
  /** Currently active file */
  activeFile: EditorFile | null;
  /** Flag indicating if this is the first file */
  isFirstFile: boolean;
  /** Last error message, if any */
  error: string | null;
}

/**
 * File sidebar state interface
 */
export interface FileSidebarState {
  /** Whether the sidebar is collapsed */
  collapsed: boolean;
  /** Previous width before collapse */
  previousWidth?: number;
  /** Whether the sidebar is currently being resized */
  isResizing: boolean;
}

/**
 * File save dialog state
 */
export interface FileSaveDialogState {
  /** Whether the dialog is visible */
  isVisible: boolean;
  /** ID of the file to save, if any */
  fileToSaveId: string | null;
  /** Default filename to suggest */
  defaultFilename: string;
  /** Whether this is a new file or existing file */
  isNewFile: boolean;
}

/**
 * File operation result
 */
export interface FileOperationResult {
  /** Whether the operation was successful */
  success: boolean;
  /** Error message if operation failed */
  error?: string;
  /** ID of the affected file */
  fileId?: string;
}

/**
 * File save options
 */
export interface FileSaveOptions {
  /** Whether to create a new file */
  createNew?: boolean;
  /** Whether to overwrite an existing file */
  overwrite?: boolean;
  /** Format to save the file in */
  format?: 'html' | 'markdown' | 'text';
}
