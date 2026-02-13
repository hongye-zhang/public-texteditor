<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Editor } from '@tiptap/core';
  import Button from '../common/Button.svelte';
  import { getEditorContent } from './EditorUtils';
  
  // 属性
  export let editor: Editor | null = null;
  
  // 调试：显示编辑器内容
  function debugShowContent(): void {
    if (!editor) return;
    
    const html = editor.getHTML();
    const text = editor.getText();
    let markdown = '未获取';
    
    try {
      markdown = editor.storage.markdown?.getMarkdown() || '未获取';
    } catch (error) {
      console.error('获取Markdown时出错:', error);
    }
    
    console.group('编辑器内容');
    console.log('HTML:', html);
    console.log('文本:', text);
    console.log('Markdown:', markdown);
    console.groupEnd();
    
    if (window.editorFeedback) {
      window.editorFeedback.show('内容已输出到控制台', '#3498db');
    }
  }
</script>

<div class="editor-actions">
  <div class="debug-actions">
    <Button 
      primary={false}
      disabled={!editor} 
      on:click={debugShowContent}
      width="auto"
      ariaLabel="显示调试内容"
    >
      调试内容
    </Button>
  </div>
</div>

<style>
  .editor-actions {
    display: flex;
    justify-content: flex-end;
    padding: 0.5rem 1rem;
    background-color: #f8f9fa;
    border-top: 1px solid #e2e8f0;
  }
  
  .debug-actions {
    display: flex;
    gap: 0.5rem;
  }
</style>
