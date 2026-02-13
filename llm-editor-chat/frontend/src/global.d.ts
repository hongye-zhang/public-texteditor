interface Window {
  editorFeedback?: {
    show: (message: string, color?: string) => void;
  };
  
  // Editor instance and selection
  editorInstance?: any;
  getCurrentEditorSelection?: () => { text: string, from: number, to: number } | null;
  lastEditorSelection?: { text: string, from: number, to: number } | null;
  
  // LaTeX formulas
  __savedLatexFormulas?: {
    inline: string[];
    block: string[];
  };
  
  // Debug functions
  debugEditor?: () => void;
  forceSaveEditor?: () => void;
  clearEditorStorage?: () => void;
  
  // Heading observer
  _headingObserver?: MutationObserver;
  _headingIntervalId?: number;
  
  // File System Access API
  showDirectoryPicker?: () => Promise<any>;
  showSaveFilePicker?: (options?: any) => Promise<any>;
}
