<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  
  export let editor: Editor;
  
  let selectionMenuElement: HTMLElement;
  let isVisible = false;
  let selectionCoords = { x: 0, y: 0 };
  
  function updateSelectionMenu() {
    if (!editor || !editor.view) return;
    
    const { state } = editor.view;
    const { selection } = state;
    
    // Hide menu if there's no selection
    if (selection.empty) {
      isVisible = false;
      return;
    }
    
    // Get selected text
    const selectedText = state.doc.textBetween(
      selection.from,
      selection.to,
      ' '
    );
    
    // Only show menu if there's actual text selected
    if (selectedText.trim().length === 0) {
      isVisible = false;
      return;
    }
    
    // Calculate position for the menu
    const { ranges } = selection;
    const from = Math.min(ranges[0].$from.pos, ranges[0].$to.pos);
    const to = Math.max(ranges[0].$from.pos, ranges[0].$to.pos);
    
    // Get coordinates of the selection
    const start = editor.view.coordsAtPos(from);
    const end = editor.view.coordsAtPos(to);
    
    // Position the menu above the selection
    selectionCoords = {
      x: (start.left + end.right) / 2,
      y: start.top - 10
    };
    
    isVisible = true;
  }
  
  function handleChat() {
    if (!editor || !editor.view) return;
    
    const { state } = editor.view;
    const { selection } = state;
    
    // Get selected text
    const selectedText = state.doc.textBetween(
      selection.from,
      selection.to,
      ' '
    );
    
    if (selectedText) {
      // Dispatch a custom event with the selected text and position information
      const customEvent = new CustomEvent('text-selection-chat', {
        detail: { 
          text: selectedText,
          from: selection.from,
          to: selection.to,
          source: 'button' // 标记该事件来自按钮点击
        }
      });
      window.dispatchEvent(customEvent);
    }
  }
  
  // Update menu position when selection changes
  function setupSelectionListener() {
    if (!editor) return;
    
    editor.on('selectionUpdate', updateSelectionMenu);
    editor.on('focus', updateSelectionMenu);
    editor.on('blur', () => {
      // Small delay to allow for button clicks
      setTimeout(() => {
        isVisible = false;
      }, 100);
    });
  }
  
  onMount(() => {
    setupSelectionListener();
    
    // Handle keyboard shortcut event from the extension
    const handleKeyboardShortcut = (event: CustomEvent) => {
      // 检查事件是否来自键盘快捷键（通过TextSelectionExtension触发）
      // 我们添加一个标记来区分键盘快捷键和按钮点击
      if (event.detail && event.detail.text && event.detail.source === 'keyboard') {
        handleChat();
      }
    };
    
    window.addEventListener('text-selection-chat', handleKeyboardShortcut as EventListener);
    
    return () => {
      window.removeEventListener('text-selection-chat', handleKeyboardShortcut as EventListener);
    };
  });
  
  onDestroy(() => {
    if (editor) {
      editor.off('selectionUpdate', updateSelectionMenu);
      editor.off('focus', updateSelectionMenu);
    }
  });
</script>

<div 
  class="selection-menu" 
  class:visible={isVisible} 
  bind:this={selectionMenuElement}
  style="left: {selectionCoords.x}px; top: {selectionCoords.y}px"
>
  <button 
    on:click|stopPropagation|preventDefault={handleChat}
    on:mousedown|stopPropagation|preventDefault
  >Chat</button>
</div>

<style>
  .selection-menu {
    position: absolute;
    z-index: 50;
    display: flex;
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    transform: translateX(-50%) translateY(-100%);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
  }
  
  .selection-menu.visible {
    opacity: 1;
    pointer-events: all;
  }
  
  button {
    padding: 4px 8px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    color: #333;
    border-radius: 4px;
  }
  
  button:hover {
    background-color: #f3f4f6;
  }
</style>
