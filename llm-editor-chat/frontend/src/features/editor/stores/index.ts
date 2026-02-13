// Re-export all store exports
export { 
  editorStore, 
  updateEditorContent, 
  updateEditorSelection, 
  updateEditorMetrics,
  resetEditorModified 
} from './editorStore';

// Export any additional store types or functions from EditorState if needed
export * from './EditorState';
