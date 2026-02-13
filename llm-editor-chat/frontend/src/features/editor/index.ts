// Export main editor component
export { default as TiptapEditor } from './components/TiptapEditor.svelte';

// Export editor components
export { default as EditorToolbar } from './components/EditorToolbar.svelte';
export { default as EditorContent } from './components/EditorContent.svelte';
export { default as EditorActions } from './components/EditorActions.svelte';
export { default as EditorFeedback } from './components/EditorFeedback.svelte';
export { default as SelectionMenu } from './components/SelectionMenu.svelte';

// Export editor extensions
export { TextSelectionExtension } from './extensions/TextSelectionExtension';
export { InlineMath, BlockMath } from './extensions/LaTeXExtensions';

// Export editor utilities
export { processLatexInPastedContent } from './utils/EditorUtils';
export { HeadingButtons } from './utils/HeadingButtons';

// Export editor stores
export { editorStore, updateEditorContent, updateEditorSelection, updateEditorMetrics, resetEditorModified } from './stores';

// Export editor API functions
export { streamModifyText } from './services';
