import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { DecorationSet, Decoration } from 'prosemirror-view';

export interface TextSelectionOptions {
  // 是否在失去焦点时保持选择高亮
  persistSelectionOnBlur?: boolean;
  // 持久化选择的高亮颜色
  persistentSelectionColor?: string;
}

export const TextSelectionExtension = Extension.create<TextSelectionOptions>({
  name: 'textSelection',

  addOptions() {
    return {
      persistSelectionOnBlur: true,
      persistentSelectionColor: 'rgba(0, 100, 255, 0.2)',
    };
  },

  addProseMirrorPlugins() {
    const extensionThis = this;

    return [
      // 快捷键插件 - 处理 Ctrl+M 和 Ctrl+L 快捷键
      new Plugin({
        key: new PluginKey('textSelectionShortcut'),
        props: {
          handleKeyDown(view, event) {
            // 由于我们已经隐藏了选择菜单，这里只保留 Ctrl+M 快捷键
            // 注释掉 Ctrl+L 快捷键，保持与UI一致性
            if (event.ctrlKey && event.key === 'm') {
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
                      source: 'keyboard'
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
      }),
      
      // 选择持久化插件 - 非常简单直接的实现
      new Plugin({
        key: new PluginKey('persistentSelection'),
        
        state: {
          init() {
            return {
              from: 0,
              to: 0,
              active: false,
              editorHasFocus: true, // 编辑器控件是否有焦点
              windowHasFocus: true  // 窗口是否有焦点
            };
          },
          
          apply(tr, prev) {
            // 如果编辑器内容变化，清除持久化选择
            if (tr.docChanged) {
              return {
                from: 0,
                to: 0,
                active: false,
                editorHasFocus: prev.editorHasFocus,
                windowHasFocus: prev.windowHasFocus
              };
            }
            
            // 处理编辑器控件焦点变化
            let editorHasFocus = prev.editorHasFocus;
            if (tr.getMeta('editorFocus') !== undefined) {
              editorHasFocus = tr.getMeta('editorFocus');
            }
            
            // 处理窗口焦点变化
            let windowHasFocus = prev.windowHasFocus;
            if (tr.getMeta('windowFocus') !== undefined) {
              windowHasFocus = tr.getMeta('windowFocus');
            }
            
            // 处理选择变化
            const { selection } = tr;
            if (!selection.empty) {
              return { from: selection.from, to: selection.to, active: true, editorHasFocus, windowHasFocus };
            }
            // 只在有选区时激活装饰，无选区时不激活
            return { from: selection.from, to: selection.to, active: selection.from !== selection.to, editorHasFocus, windowHasFocus };
          }
        },
        
        props: {
          // 处理编辑器焦点切换
          handleDOMEvents: {
            focus(view) {
              view.dispatch(view.state.tr.setMeta('editorFocus', true));
              return false;
            },
            blur(view) {
              view.dispatch(view.state.tr.setMeta('editorFocus', false));
              return false;
            }
          },
          // 添加装饰
          decorations(state) {
            const pluginState = this.getState(state);
            
            // 只在窗口有焦点但编辑器控件失去焦点时显示装饰
            if (!pluginState || !pluginState.active) {
              return null;
            }
            
            const showDecoration = pluginState.windowHasFocus && !pluginState.editorHasFocus;
            if (!showDecoration) {
              return null;
            }
            
            const { from, to } = pluginState;
            const decorationsArray: Decoration[] = [];
            
            // 只在有实际选区时才添加装饰
            if (from !== to) {
              decorationsArray.push(
                Decoration.inline(from, to, {
                  class: 'persistent-selection',
                  style: `background-color: ${extensionThis.options.persistentSelectionColor}`
                })
              );
            }
            return DecorationSet.create(state.doc, decorationsArray);
          }
        },
        
        // 监听窗口焦点以更新状态
        view(view) {
          setTimeout(() => view.dispatch(view.state.tr.setMeta('windowFocus', document.hasFocus())), 0);
          const onWinFocus = () => view.dispatch(view.state.tr.setMeta('windowFocus', true));
          const onWinBlur = () => view.dispatch(view.state.tr.setMeta('windowFocus', false));
          window.addEventListener('focus', onWinFocus);
          window.addEventListener('blur', onWinBlur);
          return {
            destroy() {
              window.removeEventListener('focus', onWinFocus);
              window.removeEventListener('blur', onWinBlur);
            }
          };
        }
      })
    ];
  }
});
