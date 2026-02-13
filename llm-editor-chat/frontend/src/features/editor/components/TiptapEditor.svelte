<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import Placeholder from '@tiptap/extension-placeholder';
  import Link from '@tiptap/extension-link';
  import Image from '@tiptap/extension-image';
  import Highlight from '@tiptap/extension-highlight';
  import Table from '@tiptap/extension-table';
  import TableRow from '@tiptap/extension-table-row';
  import TableCell from '@tiptap/extension-table-cell';
  import TableHeader from '@tiptap/extension-table-header';
  import BubbleMenu from '@tiptap/extension-bubble-menu';
  import { Markdown } from 'tiptap-markdown';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  import { ChatHistory } from '../extensions/ChatHistoryExtension';
  
  import '../extensions/PersistentSelection.css';
  
  // Import Revision extensions
  import { Revision } from '../extensions/RevisionExtension';
  import '../styles/revision.css';
  
  // Import our custom components
  import EditorToolbar from './EditorToolbar.svelte';
  import EditorContent from './EditorContent.svelte';
  import EditorFeedback from './EditorFeedback.svelte';
  import SelectionMenu from './SelectionMenu.svelte';
  // RevisionToolbar import已移除
  import { InlineMath, BlockMath } from '../extensions/LaTeXExtensions';
  import { processLatexInPastedContent, fixLatexHtmlEscaping } from '../utils/EditorUtils';
  import { HeadingButtons } from '../utils/HeadingButtons';
  import { TextSelectionExtension } from '../extensions/TextSelectionExtension';
  import { UniqueNodeId } from '../extensions/UniqueNodeIdExtension';
  import { activeFile, fileStore } from '../../file-management';
  import { storageManager } from '../../file-management/storage/storageManager';
  
  // State variables
  export let editor: Editor | null = null;
  let element: HTMLElement | null = null;
  let editorInitialized = false;
  
  // 已移除: showRevisionToolbar变量和toggleRevisionToolbar函数
  
  let bubbleMenuElement: HTMLElement;
  let currentEditingFileId: string | null = null; // Track which file is currently being edited
  let contentUpdateInProgress = false; // Lock to prevent concurrent content updates
  let saveTimeout: ReturnType<typeof setTimeout>; // For debouncing saves
  
  // 简化的自动保存系统
  let autoSaveTimeout: ReturnType<typeof setTimeout> | null = null;
  let periodicSaveInterval: ReturnType<typeof setInterval> | null = null;
  let lastSavedContent: string = '';
  let lastSaveTime: number = 0;
  let saveInProgress: boolean = false;
  let hasUnsavedChanges: boolean = false;
  
  // 自动保存配置
  const AUTO_SAVE_CONFIG = {
    userInputDelay: 2500,      // 用户输入延迟 2.5秒
    aiContentDelay: 500,       // AI内容延迟 0.5秒
    periodicInterval: 30000,   // 定期保存间隔 30秒
    maxRetries: 3,             // 最大重试次数
    retryDelay: 1000          // 重试延迟 1秒
  };
  
  // Local storage key for editor content
  const EDITOR_STORAGE_KEY = 'tiptap-editor-content';
  
  // Create event dispatcher
  const dispatch = createEventDispatcher();
  
  // Export editor instance
  export function getEditor(): Editor | null {
    return editor;
  }
  
  // Export editor content as JSON string
  export function getEditorJSON(): string | null {
    if (!editor) return null;
    try {
      const jsonContent = editor.getJSON();
      return JSON.stringify(jsonContent);
    } catch (error) {
      console.error('Error getting editor JSON:', error);
      return null;
    }
  }
  
  // Get document word count
  export function getDocumentWordCount(): number {
    if (!editor) return 0;
    
    try {
      // 如果使用了 CharacterCount 扩展
      if (editor.storage && editor.storage.characterCount) {
        return editor.storage.characterCount.words();
      }
      
      // 备选方案：手动计算
      const text = editor.getText();
      return text.split(/\s+/).filter(word => word.length > 0).length;
    } catch (error) {
      console.error('Error calculating word count:', error);
      return 0;
    }
  }
  
  // Get document character count
  export function getDocumentCharCount(): number {
    if (!editor) return 0;
    
    try {
      // 如果使用了 CharacterCount 扩展
      if (editor.storage && editor.storage.characterCount) {
        return editor.storage.characterCount.characters();
      }
      
      // 备选方案：手动计算
      return editor.getText().length;
    } catch (error) {
      console.error('Error calculating character count:', error);
      return 0;
    }
  }
  
  // Function to save editor content to localStorage and unified storage
  async function saveEditorContent(content: string, state: any): Promise<void> {
    // Save to localStorage for immediate access
    if (typeof localStorage !== 'undefined') {
      try {
        // 保存HTML内容
        localStorage.setItem(EDITOR_STORAGE_KEY, content);
        localStorage.setItem(EDITOR_STORAGE_KEY + '_timestamp', Date.now().toString());
        
        // 安全地保存编辑器状态
        if (state) {
          try {
            const stateString = JSON.stringify(state);

            
            // 检查JSON字符串是否完整
            if (!stateString.endsWith('}')) {
              console.warn('生成的JSON状态可能不完整，最后字符不是 "}"');

            }
            
            // 验证JSON是否可以被解析
            try {
              JSON.parse(stateString);
              localStorage.setItem(EDITOR_STORAGE_KEY + '_state', stateString);

            } catch (parseError) {
              console.error('生成的JSON状态无法解析:', parseError);


              // 不保存无效的JSON状态
            }
          } catch (stringifyError) {
            console.error('JSON.stringify失败:', stringifyError);
            console.error('状态对象类型:', typeof state);
            console.error('状态对象键:', state ? Object.keys(state) : 'null');
            // 尝试保存一个简化的状态
            try {
              const simplifiedState = {
                type: state?.type || 'doc',
                content: state?.content || []
              };
              const simplifiedString = JSON.stringify(simplifiedState);
              localStorage.setItem(EDITOR_STORAGE_KEY + '_state', simplifiedString);

            } catch (fallbackError) {
              console.error('连简化状态都无法保存:', fallbackError);
            }
          }
        } else {
          console.warn('编辑器状态为空，不保存状态');
        }
      } catch (error) {
        console.error('保存到localStorage时发生错误:', error);
      }
    }
    
    // Also save to unified storage manager
    try {
      const currentFile = $activeFile;
      
      if (currentFile) {
        await storageManager.saveFile({
          id: currentFile.id,
          title: currentFile.title,
          content: content,
          editorState: state,
          createdAt: currentFile.createdAt || Date.now(),
          updatedAt: Date.now(),
          isTemporary: currentFile.isTemporary || false
        });
      } else {
        // Save as temporary file if no active file
        const tempId = 'temp_' + Date.now();
        await storageManager.saveFile({
          id: tempId,
          title: 'Untitled Document',
          content: content,
          editorState: state,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          isTemporary: true
        });
      }
    } catch (error) {
      console.error('Error saving to unified storage:', error);
    }
  }

  // 简化的自动保存核心函数
  async function performAutoSave(triggerType: string = 'user_input'): Promise<void> {
    if (!editor || saveInProgress || contentUpdateInProgress) {
      return;
    }

    const currentContent = editor.getHTML();
    
    // 检查内容是否真正发生变化
    if (currentContent === lastSavedContent) {
      hasUnsavedChanges = false;
      return;
    }

    try {
      saveInProgress = true;
      const editorState = editor.getJSON();
      
      await saveEditorContent(currentContent, editorState);
      
      lastSavedContent = currentContent;
      lastSaveTime = Date.now();
      hasUnsavedChanges = false;
      
      console.log(`自动保存成功 [${triggerType}]`);
    } catch (error) {
      console.error(`自动保存失败 [${triggerType}]:`, error);
      hasUnsavedChanges = true;
    } finally {
      saveInProgress = false;
    }
  }

  // 调度自动保存（防抖）
  function scheduleAutoSave(delay: number = AUTO_SAVE_CONFIG.userInputDelay, triggerType: string = 'user_input'): void {
    // 清除之前的定时器
    if (autoSaveTimeout) {
      clearTimeout(autoSaveTimeout);
    }

    // 设置新的定时器
    autoSaveTimeout = setTimeout(() => {
      performAutoSave(triggerType);
      autoSaveTimeout = null;
    }, delay);
  }

  // AI内容保存（高优先级，短延迟）
  export function saveAIContent(): void {
    scheduleAutoSave(AUTO_SAVE_CONFIG.aiContentDelay, 'ai_content');
  }

  // 文件切换时立即保存
  export function saveOnFileSwitch(): Promise<void> {
    if (autoSaveTimeout) {
      clearTimeout(autoSaveTimeout);
      autoSaveTimeout = null;
    }
    return performAutoSave('file_switch');
  }

  // 手动强制保存
  export function forceSave(): Promise<void> {
    if (autoSaveTimeout) {
      clearTimeout(autoSaveTimeout);
      autoSaveTimeout = null;
    }
    return performAutoSave('manual');
  }

  // Export force save function with callback support
  export async function forceSaveCurrentFile(callback?: () => void): Promise<void> {
    if (!editor) {
      console.error('Cannot force save: editor not initialized');
      if (callback) callback();
      return;
    }
    
    try {
      // Store the current file ID to prevent race conditions when switching files
      const currentFileId = $activeFile ? $activeFile.id : null;
      
      const content = editor.getHTML();
      const state = editor.getJSON();
      
      // Save to unified storage (includes localStorage)
      await saveEditorContent(content, state);
      
      // If there's an active file, also save to the file store for compatibility
      if (currentFileId) {
        fileStore.updateFileContent(currentFileId, content);

      }
      
      // Call the callback after save completes
      if (callback) {
        callback();
      }
    } catch (error) {
      console.error('Error during force save:', error);
      if (callback) callback();
    }
  }
  
  // Handle editor content element ready
  function handleElementReady(event: CustomEvent<{ element: HTMLElement }>): void {
    element = event.detail.element;
    initEditor();
    
    // 添加直接的焦点事件监听
    if (element) {
      element.addEventListener('focus', () => {
        // 通知编辑器焦点变化
        if (editor) {
          const tr = editor.state.tr.setMeta('editorFocus', true);
          editor.view.dispatch(tr);
        }
      }, true);
      
      element.addEventListener('blur', () => {
        // 通知编辑器焦点变化
        if (editor) {
          const tr = editor.state.tr.setMeta('editorFocus', false);
          editor.view.dispatch(tr);
        }
      }, true);
    }
  }
  
  // Initialize editor
  function initEditor(): void {
    if (!element || editorInitialized) {
      return;
    }
    
    try {

      // 检查是否有保存的编辑器状态
      const savedState = localStorage.getItem(EDITOR_STORAGE_KEY + '_state');
      const savedContent = localStorage.getItem(EDITOR_STORAGE_KEY);
      let initialContent = null;
      
      // 如果有保存的状态，尝试使用它初始化编辑器
      if (savedState) {
        try {
          const parsedState = JSON.parse(savedState);
          const stateString = JSON.stringify(parsedState);
          
          // 检查是否包含修订节点
          const hasRevisions = stateString.includes('revisionNode');
          // 检查是否包含LaTeX
          const hasLatex = stateString.includes('inlineMath') || stateString.includes('blockMath');
          
          // 如果包含修订节点或LaTeX，使用状态初始化编辑器
          if (hasRevisions || hasLatex) {
            initialContent = parsedState;

          }
        } catch (error) {
          console.error('Error parsing saved state during initialization:', error);
        }
      }
      
      editor = new Editor({
        element: element,
        extensions: [
          UniqueNodeId.configure({
            types: ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'listItem', 'codeBlock', 'image', 'table'],
            attributeName: 'id',
            addIdOnInit: true,
          }),
          StarterKit.configure({
            // Configure to preserve whitespace
            paragraph: {
              HTMLAttributes: {
                class: 'paragraph',
              },
            },
          }),
          Placeholder.configure({
            placeholder: 'Start writing or paste your content...',
          }),
          Link.configure({
            openOnClick: false,
          }),
          Image.configure({
            allowBase64: true,
          }),
          Highlight,
          Table.configure({
            resizable: true,
          }),
          TableRow,
          TableCell,
          TableHeader,
          Markdown.configure({
            transformPastedText: true,
            transformCopiedText: true,
            html: true,
            tightLists: true,
            bulletListMarker: '-',
            linkify: true
          }),
          InlineMath,
          BlockMath,
          HeadingButtons,
          TextSelectionExtension,
          Revision,
          ChatHistory,
        ],
        content: initialContent || loadEditorContentFromLocalStorage() || '',
        // 编辑器生命周期钩子
        onBeforeCreate({ editor }) {
          // 编辑器初始化前的处理
        },
        onCreate: async ({ editor }) => {
          // 编辑器创建后的处理
          try {
            // Try to load content from unified storage
            const storageContent = await loadEditorContentFromStorage();
            if (storageContent && storageContent !== loadEditorContentFromLocalStorage()) {

              editor.commands.setContent(storageContent);
            }
          } catch (error) {
            console.error('Error loading content from unified storage:', error);
          }
        },
        onUpdate: ({ editor }) => {
          // When content changes, save it
          if (!editor || contentUpdateInProgress) return;
          
          // Get the current file ID
          const currentFileId = $activeFile ? $activeFile.id : null;
          if (!currentFileId) return;
          
          // Get the current content
          const content = editor.getHTML();
          const state = editor.getJSON();
          
          // TIER 1: Immediate local save
          // Save to localStorage and unified storage immediately
          saveEditorContent(content, state).catch(error => {
            console.error('Error in auto-save:', error);
          });
          
          // Mark the file as locally saved in the store
          //fileStore.markFileLocalSaved(currentFileId, content);
          
          // TIER 2: Delayed cloud save after 30 seconds of inactivity
          clearTimeout(saveTimeout);
          saveTimeout = setTimeout(() => {
            // If we have an active file that's not temporary, save to Google Drive
            if (currentFileId && $activeFile && !$activeFile.isTemporary) {
              contentUpdateInProgress = true;
              
              // Use the updated updateFileContent method that tracks save promises
              fileStore.updateFileContent(currentFileId, content)
                .finally(() => {
                  contentUpdateInProgress = false;
                });

            }
          }, 30000); // 30 second delay for cloud save
        },
        editorProps: {
          handlePaste: (view, event) => {
            if (!editor) return false;
            
            const text = event.clipboardData?.getData('text/plain');
            if (!text) return false;
            
            // Check for LaTeX syntax
            if (text.includes('$$') || text.includes('$')) {
              processLatexInPastedContent(editor, event);
              return true; // We've handled this event, don't continue processing
            }
            return false; // Let Tiptap handle regular text paste
          },
          // Simple handler for space key
          handleKeyDown: (view, event) => {
            // Log the key being pressed for debugging
            //
            
            // Handle space key at end of line
            if (event.key === ' ' || event.keyCode === 32) {
              const { state } = view;
              const { selection } = state;
              const { empty, $cursor } = selection;
              
              // Only handle when we have a cursor
              if (empty && $cursor) {
                const node = $cursor.parent;
                const isAtEnd = $cursor.parentOffset === node.content.size;
                
                if (isAtEnd) {

                  
                  // Get the current cursor position
                  const pos = $cursor.pos;
                  
                  // Insert a non-breaking space at the end and preserve cursor position
                  const tr = state.tr.insertText('\u00A0');
                  
                  // Set the cursor position explicitly
                  tr.setSelection(state.tr.selection.constructor.near(
                    tr.doc.resolve(pos + 1)
                  ));
                  
                  view.dispatch(tr);
                  
                  // We've handled this event
                  return true;
                }
              }
            }
            
            // Let the editor handle all other events normally
            return false;
          },
          attributes: {
            spellcheck: 'true',
            autocorrect: 'off',
            autocapitalize: 'off',
            class: 'preserve-whitespace'
          }
        },
      });
      
      //just for chrome dev test
      //window.tiptapEditor = editor;
      //
    
      // Dispatch the editor-init event
      dispatch('editor-init', { editor });
      
      // Mark editor as initialized
      editorInitialized = true;
      
      // Set bubble menu element
      if (bubbleMenuElement) {
        editor.view.dom.parentElement?.appendChild(bubbleMenuElement);
        const bubbleMenuExtension = editor.extensionManager.extensions.find(
          extension => extension.name === 'bubbleMenu'
        );
        if (bubbleMenuExtension) {
          bubbleMenuExtension.options.element = bubbleMenuElement;
        }
      }
      
      // Set up content change listener for auto-save
      editor.on('update', ({ editor, transaction }) => {
        try {
          // If we're in the middle of a file switch, don't trigger auto-save
          if (contentUpdateInProgress) {

            return;
          }
          
          // 使用更安全的方式获取HTML和状态
          let content = '';
          let editorState = null;
          
          // Store the current file ID to prevent race conditions when switching files
          const currentFileId = $activeFile ? $activeFile.id : null;
          
          // If no active file or file ID has changed unexpectedly, don't try to save
          if (!currentFileId || (currentEditingFileId && currentFileId !== currentEditingFileId)) {

            return;
          }
          
          // Update our tracking of which file is being edited
          currentEditingFileId = currentFileId;
          
          try {
            // 尝试获取HTML
            content = editor.getHTML();
            
            // Dispatch an event to notify parent components of content update
            dispatch('update', { content, fileId: currentFileId });
          } catch (htmlError) {
            console.error('Error getting HTML during auto-save:', htmlError);
            // 如果无法获取HTML，尝试使用纯文本
            try {
              content = editor.getText();
            } catch (textError) {
              console.error('Error getting text during auto-save:', textError);
              content = '<p>Error retrieving content</p>';
            }
          }
          
          try {
            // 尝试获取状态
            editorState = editor.getJSON();
          } catch (stateError) {
            console.error('Error getting editor state for auto-save:', stateError);
          }
          
          // 检查是否包含LaTeX节点
          const hasLatex = content.includes('data-type="inline-math"') || 
                          content.includes('data-type="block-math"');
          
          // Check if content contains images
          const hasImages = content.includes('<img');
          
          // 使用新的自动保存系统
          hasUnsavedChanges = true;
          scheduleAutoSave(); // 使用默认的用户输入延迟
        } catch (error) {
          console.error('Error during auto-save:', error);
        }
      });
      
      // 如果有保存的LaTeX公式，尝试恢复它们
      if ((window as any).__savedLatexFormulas) {
        try {
          const latexFormulas = (window as any).__savedLatexFormulas;
          
          // 给编辑器一些时间来初始化
          setTimeout(() => {
            try {
              // 恢复行内LaTeX公式
              if (latexFormulas.inline && latexFormulas.inline.length > 0) {
                latexFormulas.inline.forEach((formula: string) => {
                  editor.commands.insertContent({
                    type: 'inlineMath',
                    attrs: { formula }
                  });
                  // 添加空格分隔
                  editor.commands.insertContent(' ');
                });
              }
              
              // 恢复块级LaTeX公式
              if (latexFormulas.block && latexFormulas.block.length > 0) {
                latexFormulas.block.forEach((formula: string) => {
                  editor.commands.insertContent({
                    type: 'blockMath',
                    attrs: { formula }
                  });
                });
              }
              
              // 清除保存的公式
              delete (window as any).__savedLatexFormulas;
            } catch (restoreError) {
              console.error('Error restoring LaTeX formulas:', restoreError);
            }
          }, 500);
        } catch (error) {
          console.error('Error processing saved LaTeX formulas:', error);
        }
      }
      
      // 添加特殊的处理来确保LaTeX内容能够正确保存
      editor.on('selectionUpdate', ({ editor }) => {
        // 当选择变化时，也触发保存，以确保在编辑LaTeX后能保存
        const selection = editor.state.selection;
        if (selection && !selection.empty) {
          // 使用新的自动保存系统
          hasUnsavedChanges = true;
          scheduleAutoSave(); // 使用默认的用户输入延迟
        }
      });
      
    } catch (error) {
      console.error('Error initializing editor:', error);
      editorInitialized = false;
      
      // Show error feedback
      if (window.editorFeedback) {
        window.editorFeedback.show('Editor initialization failed', '#e74c3c');
      }
    }
  }
  
  // Function to accept all pending revisions
  export function acceptAllPendingRevisions(): boolean {
    if (!editor) {
      console.error('TiptapEditor: Cannot accept revisions - editor not initialized');
      return false;
    }
    // This function previously handled CriticMarkup revisions.
    // Since CriticMarkup has been removed, it no longer finds or processes those specific marks/nodes.
    // If a separate 'Revision' system (non-CriticMarkup) needs an 'accept all' functionality,
    // that would be handled by its own command, likely provided by the RevisionExtension.
    return false; // Indicate no CriticMarkup revisions were found or processed.
  }

  // Cleanup
  onDestroy(() => {
    if (editor) {
      editor.destroy();
    }
  });
  
  // Get editor content
  export function getEditorContent(): string | null {
    if (!editor) return null;
    // 获取HTML内容并修复可能的LaTeX标签转义问题
    const html = editor.getHTML();
    return fixLatexHtmlEscaping(html);
  }
  
  // Get editor Markdown content
  export function getEditorMarkdown(): string | null {
    if (!editor) return null;
    try {
      return editor.storage.markdown?.getMarkdown() || null;
    } catch (error) {
      console.error('Error getting Markdown:', error);
      return null;
    }
  }
  
  // 导出自动保存相关函数供其他组件使用
  export function triggerAIContentSave() {
    saveAIContent();
  }
  
  export function triggerFileSwitch() {
    saveOnFileSwitch();
  }
  
  export function triggerManualSave() {
    return forceSave();
  }
  
  export function getAutoSaveStatus() {
    return {
      hasUnsavedChanges,
      isSaving,
      lastSavedContent
    };
  }
  
  // 辅助函数：处理被错误转义的HTML标签，特别是LaTeX公式标签
  function processEscapedHtml(content: string): string {
    if (!content) return content;
    
    // 使用更完整的fixLatexHtmlEscaping函数处理所有LaTeX标签的转义问题
    return fixLatexHtmlEscaping(content);
  }
  
  // Load content from unified storage manager
  async function loadEditorContentFromStorage(): Promise<any> {
    try {
      // Try to load from unified storage first
      const currentFile = $activeFile;
      if (currentFile) {
        const fileData = await storageManager.loadFile(currentFile.id);
        if (fileData && fileData.editorState) {

          return fileData.editorState;
        }
      }
      
      // Fallback to localStorage if unified storage doesn't have the content
      return loadEditorContentFromLocalStorage();
    } catch (error) {
      console.error('Error loading from unified storage:', error);
      return loadEditorContentFromLocalStorage();
    }
  }
  
  // Load content from localStorage (fallback)
  function loadEditorContentFromLocalStorage(): string | null {
    try {
      if (typeof localStorage !== 'undefined') {
        // 检查是否有保存的内容
        const savedContent = localStorage.getItem(EDITOR_STORAGE_KEY);
        const savedState = localStorage.getItem(EDITOR_STORAGE_KEY + '_state');
        const savedLatex = localStorage.getItem(EDITOR_STORAGE_KEY + '_latex');
        const savedTimestamp = localStorage.getItem(EDITOR_STORAGE_KEY + '_timestamp');

        
        // 检查是否有单独保存的LaTeX公式
        if (savedLatex && savedContent) {
          try {
            // 解析保存的LaTeX公式
            const latexFormulas = JSON.parse(savedLatex);
            
            // 检查内容中是否已经包含LaTeX标记
            const contentHasLatex = savedContent.includes('data-type="inline-math"') || 
                                    savedContent.includes('data-type="block-math"');
            
            if (contentHasLatex) {
              // 内容已经包含LaTeX标记，但可能被转义了，需要处理
              return processEscapedHtml(savedContent);
            } else {
              // 尝试将LaTeX公式添加回内容
              
              // 我们先返回原始内容，然后在编辑器初始化后才添加LaTeX公式
              // 在window对象上保存LaTeX公式，以便在编辑器初始化后使用
              (window as any).__savedLatexFormulas = latexFormulas;
              return savedContent;
            }
          } catch (parseError) {
            console.error('Error parsing saved LaTeX formulas:', parseError);
          }
        }
        
        // 如果没有LaTeX公式或解析失败，尝试使用状态
        if (savedState && savedContent) {
          try {
            // 解析保存的状态
            const parsedState = JSON.parse(savedState);
            
            // 检查是否包含LaTeX节点
            const stateJson = JSON.stringify(parsedState);
            const hasLatex = stateJson.includes('inlineMath') || 
                            stateJson.includes('blockMath');
            
            if (hasLatex) {
              // 检查内容中是否也包含LaTeX标记
              const contentHasLatex = savedContent.includes('data-type="inline-math"') || 
                                      savedContent.includes('data-type="block-math"');
              
              if (contentHasLatex) {
                return processEscapedHtml(savedContent);
              } else {
                
                // 在这里我们返回内容，但在初始化编辑器时将使用状态
                if (hasLatex) {
                  return processEscapedHtml(savedContent);
                }
                return savedContent;
              }
            } else {
              
              return savedContent;
            }
          } catch (parseError) {
            console.error('Error parsing saved state:', parseError);
            // 如果解析失败，回退到使用内容
            return savedContent;
          }
        }
        
        // 如果没有状态或解析失败，尝试加载HTML内容
        if (savedContent) {
          // 检查是否包含LaTeX内容或修订内容
          const hasLatex = savedContent.includes('data-type="inline-math"') || 
                          savedContent.includes('data-type="block-math"');
          const hasRevisions = savedContent.includes('data-revision');
          
          // 如果包含修订内容，尝试从状态恢复
          if (hasRevisions && savedState) {
            try {
              // 尝试再次解析状态，确保修订节点属性正确恢复
              const parsedState = JSON.parse(savedState);

              return parsedState;
            } catch (error) {
              console.error('无法从状态恢复修订内容:', error);
            }
          }
          
          if (hasLatex) {
            // 处理可能被转义的LaTeX标签
            return processEscapedHtml(savedContent);
          }
          
          return savedContent;
        } else {
          return null;
        }
      }
      return null;
    } catch (error) {
      console.error('Error loading content from localStorage:', error);
      return null;
    }
  }
  
  // Save content to localStorage with debug info
  // 添加强制保存函数，可以在控制台手动调用
  export function forceSaveContent(): void {
    if (!editor) {
      console.error('Cannot force save: editor not initialized');
      return;
    }
    
    try {
      // Store the current file ID to prevent race conditions when switching files
      const currentFileId = $activeFile ? $activeFile.id : null;
      
      // If no active file, just save to localStorage
      if (!currentFileId) {

        const content = editor.getHTML();
        const state = editor.getJSON();
        saveEditorContent(content, state);
        return;
      }
      
      // Only save if we're editing the file we think we are
      if (currentEditingFileId && currentFileId !== currentEditingFileId) {
        console.warn('File ID mismatch, not saving to prevent overwrite');
        return;
      }
      
      // Get content and state
      const content = editor.getHTML();
      const state = editor.getJSON();
      
      // Save to localStorage
      saveEditorContent(content, state);
      
      // Save to the file that was active when the force save was triggered
      // This prevents race conditions when quickly switching between files
      fileStore.updateFileContent(currentFileId, content);

      
      // 验证保存是否成功
      debugLocalStorage();
    } catch (error) {
      console.error('Error during force save:', error);
    }
  }
  
  // This function is now defined earlier in the file
  
  // Clear content from localStorage
  export function clearEditorContent(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(EDITOR_STORAGE_KEY);
        if (editor) {
          editor.commands.setContent('');
        }
      }
    } catch (error) {
      console.error('Error clearing content from localStorage:', error);
    }
  }
  
  // 添加调试函数来显示当前的localStorage状态
  function debugLocalStorage(): void {

    
    // 检查localStorage总使用情况
    let totalSize = 0;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      const value = localStorage.getItem(key);
      if (key && value) {
        const itemSize = key.length + value.length;
        totalSize += itemSize;
      }
    }

    
    // 检查特定键
    const content = localStorage.getItem(EDITOR_STORAGE_KEY);
    const state = localStorage.getItem(EDITOR_STORAGE_KEY + '_state');
    const timestamp = localStorage.getItem(EDITOR_STORAGE_KEY + '_timestamp');
    
    if (state) {
      try {
        const parsedState = JSON.parse(state);

      } catch (error) {
        console.error('Failed to parse state:', error);

      }
    }
    
    if (timestamp) {
      const date = new Date(parseInt(timestamp));

    }
    

  }
  
  // 添加调试函数来检查编辑器状态
  function debugEditorState(): void {
    if (!editor) {
      console.error('Editor not initialized');
      return;
    }
    
    try {
      const html = editor.getHTML();
      
       try {
        const editorState = editor.getJSON();
        const stateString = JSON.stringify(editorState);
      } catch (error) {
        console.error('Error during debug:', error);
      }
    } catch (error) {
      console.error('Error getting editor content:', error);
    }
  }
  
  // 强制保存函数
  function forceEditorSave(): void {
    if (!editor) {
      console.error('Cannot force save: editor not initialized');
      return;
    }
    
    try {
      // 使用更安全的方式获取HTML和状态
      let content = '';
      let state = null;
      
      try {
        // 尝试获取HTML
        content = editor.getHTML();
      } catch (htmlError) {
        console.error('Error getting HTML content:', htmlError);
        // 如果无法获取HTML，尝试使用纯文本
        try {
          content = editor.getText();
        } catch (textError) {
          console.error('Error getting text content:', textError);
          content = '<p>Error retrieving content</p>';
        }
      }
      
      try {
        // 尝试获取状态
        state = editor.getJSON();
      } catch (stateError) {
        console.error('Error getting editor state:', stateError);
      }
      
      saveEditorContent(content, state);
      
      // 验证保存是否成功
      debugLocalStorage();
    } catch (error) {
      console.error('Error during force save:', error);
    }
  }
  
  // 将调试函数添加到全局空间
  onMount(() => {
    
    // 添加全局调试函数
    (window as any).debugEditor = () => {
      debugLocalStorage();
      debugEditorState();
    };
    
    (window as any).forceSaveEditor = () => {
      forceEditorSave();
    };
    
    (window as any).clearEditorStorage = () => {
      clearEditorContent();
      debugLocalStorage();
    };
    
    return () => {
      // 清理资源（如果需要）
    };
  });
  
  // Track the last active file ID to avoid unnecessary updates
  let lastActiveFileId = '';

  // Watch for changes to the active file and update editor content
  $: if ($activeFile && editor && editorInitialized) {
    // Only update if the file ID has changed
    if (currentEditingFileId !== $activeFile.id) {
      console.log('文件变化检测:', {
        fileId: $activeFile.id,
        title: $activeFile.title,
        hasContent: !!$activeFile.content,
        contentLength: $activeFile.content?.length || 0
      });
      
      // 检查文件内容是否可用，如果为空且不是临时文件，跳过处理
      if (!$activeFile.content && !$activeFile.isTemporary) {
        console.log('文件内容为空，等待异步加载完成...');
      } else {
      
      // 检查编辑器是否已经有LaTeX内容（优先保护localStorage中的内容）
      const currentContent = editor.getHTML();
      const hasLatexContent = currentContent.includes('data-type="inline-math"') || currentContent.includes('data-type="block-math"');
      
      // 检查文件内容中的LaTeX节点是否有有效的formula属性
      let fileHasValidLatex = false;
      if ($activeFile.content && ($activeFile.content.includes('data-type="inline-math"') || $activeFile.content.includes('data-type="block-math"'))) {
        const hasNonEmptyFormula = $activeFile.content.includes('data-formula="') && 
                                  !$activeFile.content.includes('data-formula=""') &&
                                  !$activeFile.content.includes('data-formula="\"');
        fileHasValidLatex = hasNonEmptyFormula;
      }
      
      // 如果编辑器已有LaTeX内容且文件内容没有有效LaTeX，跳过文件加载
      const shouldSkipFileLoad = hasLatexContent && 
                                (!$activeFile.content || 
                                 $activeFile.content.trim() === '' || 
                                 $activeFile.content === '<p></p>' ||
                                 !fileHasValidLatex);
      
      if (shouldSkipFileLoad) {

        currentEditingFileId = $activeFile.id;
      }
      
      // 只有在不跳过文件加载时才执行内容设置
      if (!shouldSkipFileLoad) {
        // Set the lock to prevent auto-save during content loading
        contentUpdateInProgress = true;
        
        // Small delay to ensure any pending auto-saves complete
        setTimeout(() => {
        try {
          // Update our tracking of which file is being edited
          currentEditingFileId = $activeFile.id;
          
          // 检查是否有editorContent属性，如果有，使用它而不是文件内容
          if ($activeFile.editorContent) {
            // 使用editorContent属性设置编辑器内容
            editor.commands.setContent($activeFile.editorContent);
          } else {
            // 如果没有editorContent，尝试解析JSON内容
            const fileContent = $activeFile.content || '';
            
            // 检查是否为JSON格式的文件
            if ($activeFile.title && $activeFile.title.toLowerCase().endsWith('.json')) {
              // 检查文件内容是否为空
              if (!fileContent || fileContent.trim().length === 0) {
                console.warn('JSON文件内容为空，跳过解析，设置为空编辑器');
                editor.commands.setContent('');
              } else {
                try {
                  // 调试信息已移除
                  // 检查文件内容是否被截断
                  const trimmedContent = fileContent.trim();
                  if (!trimmedContent.endsWith('}')) {
                    console.warn('JSON文件内容可能被截断，最后字符不是 "}"');

                  }
                  
                  // 尝试解析JSON
                  const jsonContent = JSON.parse(trimmedContent);
                  
                  // 验证JSON是否是有效的编辑器状态
                  if (jsonContent && jsonContent.type === 'doc') {

                    // 设置编辑器内容
                    editor.commands.setContent(jsonContent);
                  } else {

                    // 如果不是有效的编辑器状态，作为普通文本处理
                    editor.commands.setContent(fileContent);
                  }
                } catch (error) {
                  console.error('解析JSON失败，作为普通文本处理:', error);
                  console.error('错误详情:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                  });

                  // 如果解析失败，作为普通文本处理
                  editor.commands.setContent(fileContent);
                }
              }
            } else {
              // 非JSON文件，直接设置内容
              editor.commands.setContent(fileContent);
            }
          }
          

        } catch (error) {
          console.error('Error loading file content into editor:', error);
        } finally {
          // Release the lock after a short delay to ensure the content is fully loaded
          setTimeout(() => {
            contentUpdateInProgress = false;
          }, 200);
        }
        }, 100);
      }
    }
  } // 闭合 else 语句
    } // 闭合 if (currentEditingFileId !== $activeFile.id)
  // 闭合 $: if ($activeFile && editor && editorInitialized)
  
  // Initialize storage manager on component mount
  onMount(async () => {
    try {
      await storageManager.init();

    } catch (error) {
      console.error('Failed to initialize storage manager:', error);
    }
  });
</script>

<div class="editor-panel">
  <!-- Editor toolbar -->
  <EditorToolbar 
    {editor} 
  />
  
  
  <!-- Revision toolbar已移除 -->
  
  <!-- Editor content area is now inside editor-content-wrapper -->
  
  <!-- Selection menu (隐藏) -->
  <!-- 由于统一使用 streamChat API，不再需要特别处理选中文本，因此隐藏选择菜单 -->
  <!-- {#if editor}
    <SelectionMenu {editor} />
  {/if} -->
  
  <!-- Editor feedback -->
  <EditorFeedback />
  
  <!-- Editor content area -->
  <div class="editor-content-wrapper">
    <EditorContent on:elementReady={handleElementReady} />
  </div>
</div>

<style>
  .editor-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    background-color: white;
    box-shadow: none;
    padding: 1rem;
  }
  
  /* 已移除 .editor-actions 和 .action-button 相关样式 */
  
  .editor-content-wrapper {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  

  /* Tiptap editor styles */
  :global(.ProseMirror) {
    outline: none;
    height: calc(100% - 52px); /* subtract toolbar height */
    overflow-y: auto;
    padding: 1rem;
    max-height: calc(100vh - 250px);
    line-height: 1.75rem;
  }
  
  :global(.ProseMirror p) {
    margin-bottom: 0.75rem;
    line-height: 1.75rem;
  }
  
  :global(.ProseMirror h1) {
    font-size: 1.7em;
    font-weight: 700;
    letter-spacing: -.04rem;
    margin-bottom: 1rem;
    line-height: 2.5rem;
  }
  
  :global(.ProseMirror h2) {
    font-size: 1.4em;
    font-weight: 600;
    margin-bottom: 1rem;
    margin-top: 2rem;
    line-height: normal;
  }
  
  :global(.ProseMirror h3) {
    font-size: 1.25rem;
    font-weight: bold;
    margin-bottom: .5rem;
    margin-top: 1rem;
    line-height: normal;
  }
  
  :global(.ProseMirror h4) {
    font-size: 1rem;
    font-weight: bold;
    margin-bottom: .5rem;
    margin-top: 1rem;
    line-height: normal;
  }
  
  :global(.ProseMirror hr) {
    margin-bottom: 3em;
    margin-top: 3em;
    border: none;
    border-top: 1px solid #e2e8f0;
  }
  
  /* Heading button styles */
  :global(.heading-button) {
    display: inline-block;
    margin-left: 8px;
    color: #979797;
    cursor: pointer;
    font-size: 0.5em;
    user-select: none;
    transition: color 0.2s;
  }
  
  :global(.heading-button:hover) {
    color: #333;
  }
  
  /* Print styles - hide collapse buttons */
  @media print {
    :global(.heading-button) {
      display: none !important;
    }
  }
  
  /* Folded content styles */
  :global(.folded-content) {
    display: none !important;
  }
  
  /* LaTeX styles */
  :global([data-type="inline-math"]) {
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    padding: 0 2px;
    border-radius: 2px;
  }
  
  :global([data-type="inline-math"]:hover) {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  :global([data-type="block-math"]) {
    display: flex;
    justify-content: center;
    margin: 1rem 0;
    cursor: pointer;
    border-radius: 4px;
  }
  
  :global([data-type="block-math"]:hover) {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  :global(.math-block) {
    display: flex;
    justify-content: center;
    width: 100%;
  }
  
  :global(.katex) {
    font-size: 1.1em;
  }
  
  /* Table styles */
  :global(.ProseMirror table) {
    border-collapse: collapse;
    width: 100%;
    font-size: .875em;
    margin-bottom: .25rem;
    margin-top: .25rem;
  }
  
  :global(.ProseMirror th) {
    background-color: #f0f0f0;
    padding: 0.5rem;
    border: 1px solid #ddd;
  }
  
  :global(.ProseMirror th p) {
    margin-bottom: 0;
  }
  
  :global(.ProseMirror td) {
    padding: 0.5rem;
    border: 1px solid #ddd;
  }
  
  :global(.ProseMirror td p) {
    margin-bottom: 0;
  }
  
  /* List styles */
  :global(.ProseMirror ul) {
    list-style-type: disc;
    padding-left: 1.625em;
    margin-bottom: 1.25em;
  }
  
  :global(.ProseMirror ol) {
    list-style-type: decimal;
    padding-left: 1.625em;
    margin-bottom: 1.25em;
  }
  
  :global(.ProseMirror li) {
    margin-bottom: 0.5rem;
    margin-top: .5em;
    padding-left: .375em;
  }
  
  :global(.ProseMirror li p) {
    margin: 0;
  }
  
  /* Blockquote styles */
  :global(.ProseMirror blockquote) {
    border-left: 3px solid #e2e8f0;
    padding-left: 1rem;
    margin-left: 0;
    margin-right: 0;
    margin-top: 1rem;
    margin-bottom: 1rem;
    color: #4a5568;
    font-style: italic;
  }
  
  /* Preserve whitespace styles */

  /* This class is applied programmatically to the editor in the attributes configuration */
  :global(.preserve-whitespace) {
    white-space: pre-wrap;
  }

  /* This class is applied programmatically to paragraph nodes in the StarterKit configuration */
  :global(.paragraph) {
    white-space: pre-wrap;
  }

  /* Ensure spaces are visible */
  :global(.ProseMirror) {
    white-space: pre-wrap;
  }
</style>
