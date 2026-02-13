import { writable } from 'svelte/store';

// Editor store for managing editor state
export const editorStore = writable({
  content: '',
  selectedText: '',
  selectionStart: 0,
  selectionEnd: 0,
  wordCount: 0,
  charCount: 0,
  isModified: false
});

// Helper functions for editor store
export function updateEditorContent(content: string) {
  editorStore.update(state => ({
    ...state,
    content,
    isModified: true
  }));
}

export function updateEditorSelection(selectedText: string, selectionStart: number, selectionEnd: number) {
  editorStore.update(state => ({
    ...state,
    selectedText,
    selectionStart,
    selectionEnd
  }));
}

export function updateEditorMetrics(wordCount: number, charCount: number) {
  editorStore.update(state => ({
    ...state,
    wordCount,
    charCount
  }));
}

export function resetEditorModified() {
  editorStore.update(state => ({
    ...state,
    isModified: false
  }));
}
