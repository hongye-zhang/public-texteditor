import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';

export interface TextSelectionOptions {
  // Add any options here if needed
}

export const TextSelectionExtension = Extension.create<TextSelectionOptions>({
  name: 'textSelection',

  addProseMirrorPlugins() {
    const extensionThis = this;

    return [
      new Plugin({
        key: new PluginKey('textSelection'),
        props: {
          handleKeyDown(view, event) {
            // Handle Ctrl+L shortcut for Chat
            if (event.ctrlKey && event.key === 'l') {
              const { state } = view;
              const { selection } = state;
              
              // Only trigger if there's a text selection
              if (!selection.empty) {
                // Get the selected text
                const selectedText = state.doc.textBetween(
                  selection.from,
                  selection.to,
                  ' '
                );
                
                if (selectedText) {
                  // Dispatch a custom event that can be handled in the Svelte component
                  const customEvent = new CustomEvent('text-selection-chat', {
                    detail: { 
                      text: selectedText,
                      from: selection.from,
                      to: selection.to,
                      source: 'keyboard' // 标记该事件来自键盘快捷键
                    }
                  });
                  window.dispatchEvent(customEvent);
                  
                  return true; // Prevent default behavior
                }
              }
            }
            return false;
          }
        }
      })
    ];
  },
});
