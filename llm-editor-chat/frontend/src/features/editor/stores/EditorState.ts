import { writable } from 'svelte/store';
import type { Editor } from '@tiptap/core';

// 编辑器状态接口
export interface EditorState {
  editor: Editor | null;
  isReady: boolean;
  selectedText: string;
  lastAction: string;
}

// 创建可写存储
const createEditorStore = () => {
  // 初始状态
  const initialState: EditorState = {
    editor: null,
    isReady: false,
    selectedText: '',
    lastAction: '',
  };

  // 创建可写存储
  const { subscribe, set, update } = writable<EditorState>(initialState);

  return {
    subscribe,
    
    // 设置编辑器实例
    setEditor: (editor: Editor | null) => update(state => ({ ...state, editor })),
    
    // 设置编辑器就绪状态
    setReady: (isReady: boolean) => update(state => ({ ...state, isReady })),
    
    // 设置选中的文本
    setSelectedText: (selectedText: string) => update(state => ({ ...state, selectedText })),
    
    // 记录最后一次操作
    setLastAction: (lastAction: string) => update(state => ({ ...state, lastAction })),
    
    // 重置状态
    reset: () => set(initialState),
  };
};

// 导出编辑器存储实例
export const editorStore = createEditorStore();

// 辅助函数：获取编辑器内容
export function getEditorContent(format: 'html' | 'markdown' | 'text' = 'html'): string {
  let content = '';
  
  editorStore.subscribe(state => {
    if (!state.editor) return;
    
    try {
      if (format === 'html') {
        content = state.editor.getHTML();
      } else if (format === 'markdown') {
        // 假设编辑器有一个getMarkdown方法或类似的功能
        content = state.editor.storage.markdown?.getMarkdown() || '';
      } else if (format === 'text') {
        content = state.editor.getText();
      }
    } catch (error) {
      console.error(`获取${format}内容时出错:`, error);
      content = '';
    }
  })();
  
  return content;
}
