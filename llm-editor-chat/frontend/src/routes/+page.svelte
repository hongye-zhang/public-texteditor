<script lang="ts">
  import { onMount, onDestroy, setContext } from 'svelte';
  import '../app.css';
  import { TiptapEditor } from '../features/editor';
  import ChatPanel from '../features/chat/components/ChatPanel.svelte';
  import { htmlToPdf, captureEditorAsImage } from '../features/editor/utils/imageExport';
  import { writable, derived, get, type Unsubscriber } from 'svelte/store';
  import { FileSidebar, FileSaveDialog, DocumentTree, fileStore, activeFile, isFirstFile, documentTreeVisible } from '../features/file-management';
  import WordStyleNewFileDialog from '../features/ui/WordStyleNewFileDialog.svelte';


  import { fileSidebarCollapsed, chatPanelCollapsed } from '../features/ui';
  import GoogleAuthButton from '../features/auth/components/GoogleAuthButton.svelte';
  import { isAuthenticated } from '../features/auth/stores/googleAuthStore';
  import type { Editor } from '@tiptap/core';
  import type { Node as ProseMirrorNode } from 'prosemirror-model';



  let editorRef: TiptapEditor; // Reference to the editor component
  let chatPanelRef: ChatPanel; // Reference to the chat panel component
  let isExporting = false; // Flag to track export status
  let editorElement: HTMLElement | null = null; // Reference to the editor DOM element
  let copyStatus: string = ''; // Status message for clipboard operations
  let showSaveDialog = false; // Flag to control save dialog visibility
  let fileToSave: string | null = null; // ID of the file to save
  let editor: Editor | null = null; // Editor instance for document tree
  let showNewFileDialog = false; // Flag to control new file dialog visibility
  let isFullscreen = false; // Flag to track fullscreen state
  // 修订工具栏相关变量已移除
  
  // Flag to prevent duplicate event listener registration
  let electronListenersRegistered = false;

  // Create editor context to share with child components
  setContext('editor', {
    acceptAllPendingRevisions: () => {
      if (editorRef && typeof editorRef.acceptAllPendingRevisions === 'function') {
        editorRef.acceptAllPendingRevisions();
        return true;
      }
      return false;
    }
  });

  // 检测是否在 Electron 环境中
  let isElectron = false;
  
  // 处理创建空白文档的事件
  async function handleCreateBlankDocument() {
    try {
      // 创建空的编辑器状态
      const emptyEditorState = {
        type: 'doc',
        content: [
          {
            type: 'paragraph'
          }
        ]
      };
      
      // 将编辑器状态序列化为JSON字符串
      const content = JSON.stringify(emptyEditorState, null, 2);
      
      // 创建一个新文件，设置skipSaveDialog为true以跳过保存对话框
      // 将原始JSON字符串作为文件内容，将emptyEditorState对象作为编辑器内容
      const fileId = await fileStore.createFile('Untitled.json', content, undefined, true, emptyEditorState);
      
      if (fileId) {
        // 将该文件设置为活动文件
        fileStore.setActiveFile(fileId);
        
        // 如果编辑器实例可用，直接设置编辑器状态
        if (editorRef) {
          const editor = editorRef.getEditor();
          if (editor) {
            // 重要：使用setTimeout确保编辑器已完全初始化
            setTimeout(() => {
              editor.commands.setContent(emptyEditorState);
            }, 100);
          } else {
            console.error('编辑器实例不可用');
          }
        } else {
          console.error('editorRef不可用');
        }
      } else {
        console.error('创建新文件失败');
      }
    } catch (error) {
      console.error('创建新文件失败:', error);
    }
  }
  
  // 在客户端初始化时检测 Electron 环境
  onMount(() => {
    isElectron = typeof window !== 'undefined' && window.environment?.isElectron === true;

    
    // 如果是 Electron 环境，添加类名到 HTML 元素
    if (isElectron && document && document.documentElement) {
      document.documentElement.classList.add('electron');
    }
  });

  // Auto-save status
  let saveStatus: 'saved' | 'saving' | 'error' | 'idle' = 'idle';
  let lastSavedTime: string = '';
  let currentSavingFileId: string | null = null; // Track which file is currently being saved
  let saveInProgress = false; // Lock to prevent concurrent saves

  // Create a store to track save status that can be shared with other components
  const saveStatusStore = writable({
    status: 'idle' as 'saved' | 'saving' | 'error' | 'idle',
    fileId: null as string | null,
    inProgress: false
  });

  // Subscribe to changes in the save status store
  let unsubscribeSaveStatus: Unsubscriber;
  onDestroy(() => {
    if (unsubscribeSaveStatus) unsubscribeSaveStatus();
  });

  // 用于存储编辑器内容的store
  const editorContent = writable('');

  // Debounce function implementation
  function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
  ): (...args: Parameters<T>) => void {
    let timeout: ReturnType<typeof setTimeout> | null = null;

    return function(...args: Parameters<T>): void {
      const later = () => {
        timeout = null;
        func(...args);
      };

      if (timeout !== null) {
        clearTimeout(timeout);
      }

      timeout = setTimeout(later, wait);
    };
  }

  // Debounced auto-save function
  const debouncedSave = debounce((content: string) => {
    if ($activeFile && !saveInProgress) {
      try {
        // Set the lock to prevent concurrent saves
        saveInProgress = true;

        // Update the save status store
        saveStatusStore.set({
          status: 'saving',
          fileId: $activeFile.id,
          inProgress: true
        });

        // Store the file ID we're saving to prevent race conditions
        const fileIdToSave = $activeFile.id;
        currentSavingFileId = fileIdToSave;

        saveStatus = 'saving';

        // Use setTimeout to ensure this runs after any pending file switches
        setTimeout(() => {
          // Double-check that we're still saving the same file
          // and that the file still exists in the store
          const currentFiles = get(fileStore).files;
          const fileStillExists = currentFiles.some(f => f.id === fileIdToSave);

          if (fileStillExists) {
            // Save to the specific file ID we captured earlier
            fileStore.updateFileContent(fileIdToSave, content);

            // Update last saved time
            const now = new Date();
            lastSavedTime = now.toLocaleTimeString();

            // Show saved status briefly
            saveStatus = 'saved';

            // Update the save status store
            saveStatusStore.set({
              status: 'saved',
              fileId: fileIdToSave,
              inProgress: false
            });

            // Reset to idle after showing "saved" for a moment
            setTimeout(() => {
              saveStatus = 'idle';
              // Release the lock
              saveInProgress = false;
              currentSavingFileId = null;

              // Update the save status store
              saveStatusStore.set({
                status: 'idle',
                fileId: null,
                inProgress: false
              });
            }, 2000);
          } else {
            console.warn(`File ${fileIdToSave} no longer exists, skipping save`);
            saveStatus = 'idle';
            saveInProgress = false;
            currentSavingFileId = null;

            // Update the save status store
            saveStatusStore.set({
              status: 'idle',
              fileId: null,
              inProgress: false
            });
          }
        }, 100); // Small delay to ensure file switch operations complete first
      } catch (error) {
        console.error('Auto-save failed:', error);
        saveStatus = 'error';

        // Update the save status store
        saveStatusStore.set({
          status: 'error',
          fileId: currentSavingFileId,
          inProgress: false
        });

        setTimeout(() => { 
          saveStatus = 'idle';
          // Release the lock
          saveInProgress = false;
          currentSavingFileId = null;

          // Update the save status store
          saveStatusStore.set({
            status: 'idle',
            fileId: null,
            inProgress: false
          });
        }, 3000);
      }
    }
  }, 2000); // 2-second delay

  // Function to handle editor initialization
  function handleEditorInit(event: CustomEvent<{ editor: Editor }>) {

    editor = event.detail.editor;
    
    // Set up keyboard shortcuts
    document.addEventListener('keydown', handleKeyDown);
  }
  
  // Handle keyboard shortcuts for the editor
  function handleKeyDown(event: KeyboardEvent) {
    // Only process shortcuts if we have an active editor
    if (!editor) return;
    
    // Check if ctrl/cmd key is pressed
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modKey = isMac ? event.metaKey : event.ctrlKey;
    
    // Example shortcuts
    if (modKey) {
      switch (event.key.toLowerCase()) {
        // Add any custom keyboard shortcuts here
        // 已移除: Ctrl+Alt+R 打开修订工具栏的快捷键
      }
    }
  }
  
  // Toggle the revision toolbar
  // 已移除toggleRevisionToolbar函数

  // 获取节点路径
  function getNodePath(editor: Editor, pos: number): string {
    const path = [];
    let $pos = editor.state.doc.resolve(pos);
    
    for (let i = 0; i <= $pos.depth; i++) {
      const index = $pos.index(i);
      path.push(index);
    }
    
    return path.join('/');
  }

  // 获取选中的节点信息
    interface NodeInfo {
    path: string;
    type: string;
    attrs: any;
    text: string | null;
    isFullySelected: boolean;
  }

  function getSelectedNodesInfo(editor: Editor, from: number, to: number): NodeInfo[] {
    const nodeInfos: NodeInfo[] = [];
    const { doc } = editor.state;
    
    doc.nodesBetween(from, to, (node: ProseMirrorNode, pos: number, parent: ProseMirrorNode | null, index: number) => {
      // 只收集叶子节点或包含选择的节点
      if (node.isLeaf || (pos + node.nodeSize > from && pos < to)) {
        // 只有当节点有文本内容时才添加到结果中
        const nodeText = node.isText ? node.text : null;
        if (nodeText !== null) {
          // 获取节点的正确的ID
          // 如果节点是文本节点，则需要使用其父节点的ID
          let nodeId = null;
          if (node.type.name === 'text' && parent) {
            // 文本节点使用父节点的ID
            nodeId = parent.attrs.id;
          } else {
            // 非文本节点使用自己的ID
            nodeId = node.attrs.id;
          }
          
          // 确保节点有ID
          if (nodeId) {
            nodeInfos.push({
              path: getNodePath(editor, pos),
              type: node.type.name,
              attrs: { id: nodeId, ...node.attrs },
              text: nodeText || null,
              isFullySelected: pos >= from && pos + node.nodeSize <= to
            });
          }
        }
      }
      return true; // 继续遍历
    });
    
    return nodeInfos;
  }

  // 获取当前选择的文本及其位置信息
  function getCurrentSelection(): { text: string, from: number, to: number, nodeInfos?: any[] } | null {
    if (!editorRef) return null;

    const editor = editorRef.getEditor();
    if (!editor) return null;

    const { state } = editor;
    const { selection } = state;
    const { from, to } = selection;

    // 检查是否有有效的选择
    if (from === to) {
      // 只有光标，没有选择
      // 获取光标所在的节点
      const $pos = editor.state.doc.resolve(from);
      const node = $pos.parent;
      const path = getNodePath(editor, $pos.before($pos.depth));
      
      return { 
        text: "", 
        from, 
        to,
        nodeInfos: [{
          path,
          type: node ? node.type.name : null,
          attrs: node ? (node.attrs || {}) : {},
          isSelection: false,
          isCursor: true
        }]
      };
    }

    // 获取选中文本
    const selectedText = state.doc.textBetween(from, to, ' ');
    if (!selectedText || !selectedText.trim()) return null;
    
    // 获取选中的节点信息
    const nodeInfos = getSelectedNodesInfo(editor, from, to);
    
    return { text: selectedText, from, to, nodeInfos };
  }

  // 全局函数将在 onMount 中设置

  onMount(() => {
    // 将获取当前选择的函数添加到全局变量中
    // 只在浏览器环境中访问 window 对象
    if (typeof window !== 'undefined') {
      (window as any).getCurrentEditorSelection = getCurrentSelection;
      // Make export functions available globally
      (window as any).handleExportImages = handleExportImages;
      (window as any).handleExportPDF = handleExportPDF;
    }
    
    // 监听菜单事件
    if (isElectron && window.electronAPI && !electronListenersRegistered) {
      electronListenersRegistered = true;
      // 监听保存文件事件
      window.electronAPI?.fileSystem.onMenuSaveFile(() => {

        handleSaveFile();
      });
      
      // 监听另存为事件
      window.electronAPI?.fileSystem.onMenuSaveFileAs(() => {

        if ($activeFile) {
          // 获取编辑器状态为JSON格式
          const editor = editorRef ? editorRef.getEditor() : null;
          if (!editor) {
            console.error('编辑器实例不可用');
            return;
          }
          
          // 获取编辑器完整JSON状态
          const editorState = editor.getJSON();
          const content = JSON.stringify(editorState, null, 2);
          
          // 在Electron环境中，直接使用原生对话框保存文件
          // 使用.json扩展名以反映实际内容格式
          const suggestedName = ($activeFile.title || 'untitled').replace(/\.md$|\.txt$|\.json$/, '') + '.json';
          
          // 更新文件内容并保存，同时保存原始JSON字符串和解析后的编辑器状态对象
          // 这确保了文件内容是JSON字符串（用于保存到磁盘），而editorContent是解析后的对象（用于编辑器显示）
          fileStore.updateFileContent($activeFile.id, content, editorState);
          
          fileStore.saveFileToDisk($activeFile.id, suggestedName)
            .then((path) => {
              if (path) {
                console.log(`文件已保存到: ${path}`);
              }
            })
            .catch(error => {
              console.error('保存文件失败:', error);
            });
        }
      });
      
      // 监听PDF导出事件
      window.electronAPI?.fileSystem.onMenuExportPdf(() => {

        handleExportPdf();
      });
      
      // 监听新建文件事件
      window.electronAPI?.fileSystem.onMenuNewFile(() => {

        // 显示新文件对话框，而不是直接创建文件
        showNewFileDialog = true;
      });
      

      
      // 监听打开文件事件
      window.electronAPI?.fileSystem.onMenuOpenFile(async () => {
        try {
          // 直接处理文件打开逻辑，不调用handleOpenFile函数以避免重复调用
          await handleOpenFileLogic();
        } catch (error) {
          console.error('打开文件失败:', error);
        }
      });
      

      
      // 监听清除最近文件事件
      window.electronAPI?.menu?.onClearRecentFiles(() => {
        console.log('收到清除最近文件事件');
        
        // 清除最近文件列表
        import('../features/file-management/stores/recentFilesStore').then(({ recentFilesStore }) => {
          recentFilesStore.clearRecentFiles();
        });
      });
      
      // 处理文件打开逻辑的函数（从菜单事件调用）
      async function handleOpenFileLogic() {
        try {
          // 调用 Electron API 打开文件
          const fileInfo = await window.electronAPI?.fileSystem.openFile();
          
          if (!fileInfo) {
            return;
          }
          
          await processOpenedFile(fileInfo);
        } catch (error) {
          console.error('打开文件失败:', error);
        }
      }
      
      // 处理文件打开逻辑的函数（从其他地方调用）
      async function handleOpenFile() {
        try {
          // 调用 Electron API 打开文件
          const fileInfo = await window.electronAPI?.fileSystem.openFile();
          
          if (!fileInfo) {
            return;
          }
          
          await processOpenedFile(fileInfo);
        } catch (error) {
          console.error('打开文件失败:', error);
        }
      }
      
      // 处理打开的文件信息
      async function processOpenedFile(fileInfo: { path: string; content: string; name: string }) {
        const { path: filePath, content, name } = fileInfo;
        
        try {
          // 检查是否为JSON格式
          if (filePath.toLowerCase().endsWith('.json')) {
            try {
              // 尝试解析JSON

              const jsonContent = JSON.parse(content);
              
              // 验证JSON是否是有效的编辑器状态
              if (jsonContent && jsonContent.type === 'doc') {
                console.log('解析成功，有效的编辑器JSON状态:', 
                  JSON.stringify(jsonContent.type), '内容长度:', jsonContent.content?.length || 0);
                
                // 重要：在创建文件时，我们保存原始JSON字符串作为文件内容，并将解析后的JSON对象作为编辑器内容
                const fileId = await fileStore.createFile(name, content, filePath, true, jsonContent);
                
                // 设置文件元数据
                fileStore.updateFileMetadata(fileId, {
                  localFilePath: filePath,
                  lastLocalSave: Date.now(),
                  isDirty: false,
                  isTemporary: false // 这个文件已经有路径，不是临时文件
                });
                
                // 将该文件设置为活动文件
                fileStore.setActiveFile(fileId);
                
                // 如果编辑器实例可用，直接设置编辑器状态
                if (editorRef) {
                  const editor = editorRef.getEditor();
                  if (editor) {
                    // 使用解析的JSON状态设置编辑器

                    
                    // 重要：使用setTimeout确保编辑器已完全初始化
                    setTimeout(() => {
                      // 将解析后的JSON对象设置为编辑器的内部状态
                      editor.commands.setContent(jsonContent);

                    }, 100);
                  } else {
                    console.error('编辑器实例不可用');
                  }
                } else {
                  console.error('editorRef不可用');
                }
                
                return;
              } else {
                console.warn('解析的JSON不是有效的编辑器状态，将作为普通文本处理');
              }
            } catch (jsonError) {
              console.error('解析JSON失败，将作为普通文本处理:', jsonError);
              // 如果解析失败，则作为普通文本处理
            }
          }
          
          // 如果不是JSON或解析失败，则作为普通文本处理
          const fileId = await fileStore.createFile(name, content, filePath, true);
          
          // 设置文件元数据
          fileStore.updateFileMetadata(fileId, {
            localFilePath: filePath,
            lastLocalSave: Date.now(),
            isDirty: false,
            isTemporary: false // 这个文件已经有路径，不是临时文件
          });
          
          // 将该文件设置为活动文件
          fileStore.setActiveFile(fileId);
        } catch (error) {
          console.error('打开文件失败:', error);
        }
      }
    }

    // Get the editor element after component is mounted
    setTimeout(() => {
      editorElement = document.querySelector('.ProseMirror');

      // 初始化时获取一次编辑器内容
      if (editorRef) {
        const editor = editorRef.getEditor();
        if (editor) {
          editorContent.set(editor.getHTML());

          // 将编辑器实例存储在全局变量中，以便在其他组件中可以访问它
          if (typeof window !== 'undefined') {
            (window as any).editorInstance = editor;

            // 添加选择变化事件监听器
            editor.on('selectionUpdate', () => {
              // 当选择变化时，更新全局选择状态
              (window as any).lastEditorSelection = getCurrentSelection();
            });
          }
        }
      }
    }, 500);

    // Add event listener for text selection chat
    window.addEventListener('text-selection-chat', ((event: CustomEvent) => {
      if (event.detail && event.detail.text) {
        // Get the selected text and position information
        const { text: selectedText, from, to } = event.detail;

        // Use the chat panel reference to set the message with position information
        if (chatPanelRef && typeof chatPanelRef.setMessageFromSelection === 'function') {
          chatPanelRef.setMessageFromSelection(selectedText, from, to);
        }
      }
    }) as EventListener);

    // Create a default file if none exists
    if ($fileStore.files.length === 0) {
      fileStore.createFile('Untitled', '');
    }

    // Subscribe to changes in the save status store
    unsubscribeSaveStatus = saveStatusStore.subscribe(value => {
      saveStatus = value.status;
      currentSavingFileId = value.fileId;
      saveInProgress = value.inProgress;
    });

    // Make the save status store available globally
    if (typeof window !== 'undefined') {
      (window as any).saveStatusStore = saveStatusStore;
    }
  });

  async function handleExportImages(): Promise<void> {
    if (!editorElement) {
      alert('Editor not ready, please try again later');
      return;
    }

    try {
      isExporting = true;
      copyStatus = '';

      // Capture editor content as image
      const imageDataUrl = await captureEditorAsImage(editorElement, 'desktop');

      // Create download link
      const link = document.createElement('a');
      link.href = imageDataUrl;
      link.download = `Editor Export_${new Date().toISOString().slice(0, 10)}.png`;

      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Copy to clipboard
      try {
        const response = await fetch(imageDataUrl);
        const blob = await response.blob();
        await navigator.clipboard.write([
          new ClipboardItem({
            [blob.type]: blob
          })
        ]);

        // Show success message
        copyStatus = 'Image copied to clipboard';

        // Clear message after 3 seconds
        setTimeout(() => {
          copyStatus = '';
        }, 3000);
      } catch (clipboardError) {
        console.error('Copy to clipboard failed:', clipboardError);
        copyStatus = 'Copy to clipboard failed, please check console for details';
      }

      isExporting = false;
    } catch (error) {
      console.error('Export image failed:', error);
      alert('Export image failed, please check console for details');
      isExporting = false;
    }
  }

  async function handleExportPDF(): Promise<void> {
    if (!editorElement) {
      alert('Editor not ready, please try again later');
      return;
    }

    try {
      isExporting = true;

      // Get the editor HTML content
      const content = getEditorContent();
      if (!content) {
        alert('No content to export');
        isExporting = false;
        return;
      }

      // Generate PDF
      const pdfBlob = await htmlToPdf(content.toString());

      // Create download link
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${$activeFile?.title || 'Editor Export'}_${new Date().toISOString().slice(0, 10)}.pdf`;

      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Cleanup
      URL.revokeObjectURL(url);
      isExporting = false;
    } catch (error) {
      console.error('Export PDF failed:', error);
      alert('Export PDF failed, please check console for details');
      isExporting = false;
    }
  }

  // Handle PDF export for Electron
  async function handleExportPdf(): Promise<void> {
    if (!editorRef) {
      alert('编辑器未准备好，请稍后再试');
      return;
    }

    try {
      isExporting = true;


      // 获取编辑器HTML内容
      const editor = editorRef.getEditor();
      if (!editor) {
        alert('编辑器实例不可用');
        isExporting = false;
        return;
      }

      const htmlContent = editor.getHTML();
      if (!htmlContent || htmlContent.trim() === '<p></p>') {
        alert('没有内容可导出');
        isExporting = false;
        return;
      }

      // 获取文件名作为建议名称
      const suggestedName = $activeFile?.title || 'document';
      
      // 调用Electron API导出PDF
      const result = await window.electronAPI?.fileSystem.exportPdf(htmlContent, suggestedName);
      
      if (result?.success) {

        // 可以显示成功消息
        copyStatus = `PDF已保存到: ${result.filePath}`;
        setTimeout(() => {
          copyStatus = '';
        }, 3000);
      } else if (result && result.canceled) {
        console.log('用户取消了PDF导出');
      } else {
        console.error('PDF导出失败:', result && result.error);
        alert(`PDF导出失败: ${result && result.error}`);
      }
      
    } catch (error) {
      console.error('PDF导出错误:', error);
      alert('导出PDF时发生错误，请查看控制台获取详细信息');
    } finally {
      isExporting = false;
    }
  }

  // Get editor content (优先返回 JSON 格式)
  function getEditorContent(): string {
    if (!editorRef) return '';
    
    try {
      // 尝试获取 JSON 格式的内容
      const jsonContent = editorRef.getEditorJSON();
      if (jsonContent) {

        return jsonContent;
      }
      
      // 如果获取 JSON 失败，回退到 HTML 格式
      const editor = editorRef.getEditor();
      if (!editor) return '';
      

      return editor.getHTML();
    } catch (error) {
      console.error('Error getting editor content:', error);
      return '';
    }
  }
  
  // 获取文档单词数
  function getDocumentWordCount(): number {
    if (!editorRef) return 0;
    return editorRef.getDocumentWordCount();
  }
  
  // 获取文档字符数
  function getDocumentCharCount(): number {
    if (!editorRef) return 0;
    return editorRef.getDocumentCharCount();
  }

  // Handle editor update event
  function handleEditorUpdate(event: CustomEvent): void {
    const content = event.detail.content;
    editorContent.set(content);
    debouncedSave(content);
  }

  /**
   * 处理增量节点更新
   * @param {Editor} editor - Tiptap 编辑器实例
   * @param {Array} updateData - 增量更新数据数组
   */
  function handleIncrementalNodeUpdate(editor: any, updateData: Array<{path: string, content: string, id: string}> | {path: string, content: string, id: string}) {
    // 确保 updateData 是数组
    const updates = Array.isArray(updateData) ? updateData : [updateData];
    
    // 记录日志，便于调试

    
    // 首先找出所有非空的更新
    const nonEmptyUpdates = updates.filter(update => update.content !== "");
    
    // 查找是否有新节点需要插入
    const newNodeUpdate = nonEmptyUpdates.find(update => update.path === 'new');
    
    // 如果有新节点，我们需要确定插入位置
    if (newNodeUpdate) {

      
      // 获取编辑器的JSON结构
      const editorJSON = editor.getJSON();
      
      // 查找新节点的插入位置 - 使用基于ID的方法
      const insertPosition = determineInsertPositionById(editor, updates, editorJSON);
      
      if (insertPosition !== null) {


        
        // 检查内容是否已经是完整的段落结构
        let contentToInsert = newNodeUpdate.content;

        
        // 如果是纯文本，确保包裹在段落标签中
        if (!contentToInsert.trim().startsWith('<p>') && 
            !contentToInsert.trim().startsWith('{"type"') && 
            !contentToInsert.trim().startsWith('"{"type"')) {
          contentToInsert = `<p>${contentToInsert}</p>`;

        } 
        // 如果是 JSON 字符串，需要解析并确保是段落结构
        else if (contentToInsert.trim().startsWith('{') || contentToInsert.trim().startsWith('"{"type"')) {
          try {
            // 处理可能的双引号包裹的 JSON 字符串
            let jsonContent = contentToInsert;
            if (jsonContent.startsWith('"') && jsonContent.endsWith('"')) {
              jsonContent = JSON.parse(jsonContent); // 解析双引号包裹的 JSON 字符串
            }
            
            // 解析 JSON 内容
            const contentObj = typeof jsonContent === 'string' ? JSON.parse(jsonContent) : jsonContent;
            
            // 确保是段落节点
            if (contentObj.type !== 'paragraph' && contentObj.type !== 'doc') {
              // 如果不是段落或文档节点，则将其包裹在段落节点中
              contentToInsert = JSON.stringify({
                type: 'paragraph',
                content: [contentObj]
              });

            } 
            // 如果是文档节点，确保其内容是段落
            else if (contentObj.type === 'doc' && contentObj.content && contentObj.content.length > 0) {
              // 保持原样，因为文档节点已经包含段落结构
              contentToInsert = JSON.stringify(contentObj);

            }
          } catch (e) {
            console.warn('解析 JSON 内容失败，将作为纯文本处理:', e);
            // 如果解析失败，则当作纯文本处理
            contentToInsert = `<p>${contentToInsert}</p>`;
          }
        }
        
        // 确保插入的内容是一个完整的段落
        // 如果是 HTML 格式，确保是完整的段落标签
        if (contentToInsert.startsWith('<') && !contentToInsert.startsWith('<p>')) {
          contentToInsert = `<p>${contentToInsert}</p>`;
        }
        
        // 使用全新的方法来插入内容并确保段落分隔
        // 先在插入位置创建一个新的空段落
        // Importane Note: It seems if insertposition is correct, no need to splitBlock
        //editor.chain().focus()
        //  .setTextSelection(insertPosition)
        //  .splitBlock()
        //  .run();
        
        // 现在我们在插入位置处有了一个新的空段落
        // 将内容插入到这个空段落中
        // Important Note: insert paragraph after the new paragraph
        editor.chain().focus()
          .setTextSelection(insertPosition + 1)
          .insertContent(contentToInsert)
          .run();
        

      } else {
        console.warn('无法确定新节点的插入位置，将插入到文档末尾');
        
        // 如果无法确定位置，插入到文档末尾
        const docEnd = editor.state.doc.content.size;
        editor.chain()
          .focus()
          .insertContentAt(docEnd, newNodeUpdate.content)
          .run();
        

      }
    }
    
    // 处理常规更新（非新节点）
    for (const update of nonEmptyUpdates) {
      const { path, content, id } = update;
      
      // 跳过新节点，因为已经处理过了
      if (path === 'new') continue;
      
      // 查找节点位置（使用ID）
      const nodePosition = findNodePositionById(editor, id);
      
      if (nodePosition) {
        const { from, to } = nodePosition;
        


        
        // 检查编辑器中是否注册了 revision 功能
        const hasRevisionCommands = editor.commands && (editor.commands as any).createRevisionFromSelection;
        
        if (hasRevisionCommands) {
          // 使用修订系统创建变更标记

          
          // 选中要替换的范围
          editor.chain().focus().setTextSelection({ from, to }).run();
          
          // 创建修订节点（替代类型）
          const revisionCreated = (editor.commands as any).createRevisionFromSelection({
            type: 'substitution',
            newContent: content
          });
          

          
          if (revisionCreated) {
            // 创建成功，自动显示修订工具栏
            // 节点更新成功，修订已集成到主工具栏

            
            // 触发自定义事件通知 EditorToolbar 更新修订列表
            document.dispatchEvent(new CustomEvent('revisionUpdated'));
          } else {
            // 如果修订系统失败，回退到直接替换
            console.warn('修订系统失败，回退到直接替换');
            editor.chain()
              .focus()
              .deleteRange({ from, to })
              .insertContentAt(from, content)
              .run();

          }
        } else {
          // 如果没有修订系统，使用原来的直接替换方法

          editor.chain()
            .focus()
            .deleteRange({ from, to })
            .insertContentAt(from, content)
            .run();

        }
      } else {
        console.warn(`无法找到路径 ${path} 对应的节点位置 (ID: ${id})`);
      }
    }
  }

  /**
   * 根据ID查找节点在文档中的位置
   * @param {Editor} editor - Tiptap 编辑器实例
   * @param {string} nodeId - 节点唯一ID
   * @returns {Object|null} - 返回 {from, to} 表示节点的开始和结束位置，或 null 表示未找到
   */
  function findNodePositionById(editor, nodeId) {
    try {
      // 检查参数
      if (!nodeId) {
        console.warn('节点ID为空');
        return null;
      }
      
      // 使用ProseMirror的原生API查找节点
      let position = null;
      
      // 遍历文档中的所有节点
      editor.state.doc.descendants((node, pos) => {
        // 检查节点是否有ID属性并且匹配目标ID
        if (node.attrs?.id === nodeId) {
          position = {
            from: pos,
            to: pos + node.nodeSize
          };
          return false; // 停止遍历
        }
        return true; // 继续遍历
      });

      if (position) {

        return position;
      }

      console.warn(`未找到ID为 ${nodeId} 的节点`);
      return null;
    } catch (error) {
      console.error('查找节点位置时出错:', error);
      return null;
    }
  }
  
  /**
   * 确定新节点的插入位置 - 基于路径
   * @param {Editor} editor - Tiptap 编辑器实例
   * @param {Array} updates - 所有更新数据
   * @returns {number|null} - 返回插入位置的偏移量，或 null 表示无法确定
   */
  function determineInsertPosition(editor: any, updates: Array<{path: string, content: string, id: string}>) {

    
    try {
      // 按照路径排序更新，以便我们可以确定相对位置
      const sortedUpdates = [...updates].filter(u => u.path !== 'new' && u.path !== '');
      
      // 如果没有其他节点更新，则无法确定位置
      if (sortedUpdates.length === 0) {

        return null;
      }
      
      // 分析路径模式，寻找最适合的插入位置
      // 首先尝试找到内容[1]，即第二段的开始位置
      const secondParagraphPath = sortedUpdates.find(u => {
        const match = u.path.match(/content\[(\d+)\]/);
        return match && match[1] === '1'; // 匹配 content[1]
      });
      
      if (secondParagraphPath) {
        const nodePosition = findNodePositionById(editor, secondParagraphPath.id);
        if (nodePosition) {

          return nodePosition.from;
        }
      }
      
      // 如果没有找到第二段，则尝试找到第一段并在其后面插入
      const firstParagraphPath = sortedUpdates.find(u => {
        const match = u.path.match(/content\[(\d+)\]/);
        return match && match[1] === '0'; // 匹配 content[0]
      });
      
      if (firstParagraphPath) {
        const nodePosition = findNodePositionByPath(editor, firstParagraphPath.path);
        if (nodePosition) {

          return nodePosition.to;
        }
      }
      
      // 如果上述特定模式匹配失败，则回退到一般策略
      for (const update of sortedUpdates) {
        const nodePosition = findNodePositionByPath(editor, update.path);
        if (nodePosition) {

          
          // 分析路径以确定是否应该在此节点之前或之后插入
          const pathSegments = update.path.split('.');
          const lastSegment = pathSegments[pathSegments.length - 1];
          const match = lastSegment.match(/(\w+)(?:\[(\d+)\])?/);
          
          if (match) {
            const [, name, indexStr] = match;
            const index = indexStr ? parseInt(indexStr) : 0;
            
            // 如果是第一个内容节点，在其后面插入
            if (index === 0 && name === 'content') {

              return nodePosition.to;
            }
            
            // 否则在节点之前插入

            return nodePosition.from;
          }
          
          // 默认在节点之后插入
          return nodePosition.to;
        }
      }
      
      // 如果没有找到任何有效的节点位置，则返回 null
      console.warn('无法找到任何有效的节点位置作为参考点');
      return null;
    } catch (error) {
      console.error('确定插入位置时出错:', error);
      return null;
    }
  }

  /**
   * 根据ID确定新节点的插入位置
   * @param {Editor} editor - Tiptap 编辑器实例
   * @param {Array} updates - 所有更新数据
   * @param {Object} editorJSON - 编辑器的JSON结构
   * @returns {number|null} - 返回插入位置的偏移量，或 null 表示无法确定
   */
  function determineInsertPositionById(editor: any, updates: Array<{path: string, content: string, id: string}>, editorJSON: any) {

    
    try {
      // 找到非空且有ID的节点
      const nodesWithId = updates.filter(u => u.id && u.id !== '' && u.path !== 'new');
      
      // 如果没有其他节点更新，则无法确定位置
      if (nodesWithId.length === 0) {

        return null;
      }
      
      // 找到新节点在更新数组中的索引
      const newNodeIndex = updates.findIndex(u => u.path === 'new');
      if (newNodeIndex === -1) {

        return null;
      }
      
      // 尝试找到新节点前面的节点ID
      let referenceNodeId = null;
      let insertBefore = false;
      
      // 首先检查新节点前面的节点
      for (let i = newNodeIndex - 1; i >= 0; i--) {
        if (updates[i].id && updates[i].id !== '') {
          referenceNodeId = updates[i].id;
          insertBefore = false; // 在参考节点后面插入

          break;
        }
      }
      
      // 如果前面没有找到，则检查新节点后面的节点
      if (!referenceNodeId) {
        for (let i = newNodeIndex + 1; i < updates.length; i++) {
          if (updates[i].id && updates[i].id !== '') {
            referenceNodeId = updates[i].id;
            insertBefore = true; // 在参考节点前面插入

            break;
          }
        }
      }
      
      // 如果找到了参考节点ID，查找其在编辑器中的位置
      if (referenceNodeId) {
        // 查找节点
        const nodeInfo = findNodeById(editorJSON, referenceNodeId);
        
        if (nodeInfo) {

          
          // 获取节点在文档中的位置
          const nodePosition = findNodePositionInDocument(editor, nodeInfo.node, nodeInfo.path);
          
          if (nodePosition) {
            // 根据是在节点前还是节点后插入，返回相应的位置
            const position = insertBefore ? nodePosition.from : nodePosition.to;

            return position;
          }
        }
      }
      
      // 如果上述方法都失败，尝试使用基于路径的方法作为备选

      return determineInsertPosition(editor, updates);
    } catch (error) {
      console.error('使用ID确定插入位置时出错:', error);
      return null;
    }
  }
  
  /**
   * 根据ID在编辑器JSON中查找节点
   * @param {Object} node - 当前节点
   * @param {string} targetId - 目标节点ID
   * @param {Array} path - 当前路径 (用于递归)
   * @returns {Object|null} - 返回 {node, path} 或 null 表示未找到
   */
  function findNodeById(node: any, targetId: string, path: Array<any> = []) {
    // 检查当前节点是否有匹配的ID
    if (node.attrs && node.attrs.id === targetId) {
      return { node, path: [...path] };
    }
    
    // 递归检查子节点
    if (node.content) {
      for (let i = 0; i < node.content.length; i++) {
        const childPath = [...path, { index: i, parent: node }];
        const found = findNodeById(node.content[i], targetId, childPath);
        if (found) return found;
      }
    }
    
    return null;
  }
  
  /**
   * 使用 Tiptap/ProseMirror 的原生 API 查找节点在文档中的位置
   * @param {Editor} editor - Tiptap 编辑器实例
   * @param {Object} node - 目标节点
   * @param {Array} nodePath - 节点路径信息
   * @returns {Object|null} - 返回 {from, to} 表示节点的开始和结束位置，或 null 表示未找到
   */
  function findNodePositionInDocument(editor: any, node: any, nodePath: Array<any>) {
    try {
      // 获取节点的ID
      const targetId = node.attrs?.id;
      if (!targetId) {
        console.warn('目标节点没有ID属性');
        return null;
      }

      // 使用ProseMirror的原生API查找节点
      let position = null;
      
      // 遍历文档中的所有节点
      editor.state.doc.descendants((node, pos) => {
        // 检查节点是否有ID属性并且匹配目标ID
        if (node.attrs?.id === targetId) {
          position = {
            from: pos,
            to: pos + node.nodeSize - 1  //Important Note: It is necessary to subtract 1 to ensure the node is fully selected
          };
          return false; // 停止遍历
        }
        return true; // 继续遍历
      });

      if (position) {

        return position;
      }

      console.warn(`未找到ID为 ${targetId} 的节点`);
      return null;
    } catch (error) {
      console.error('查找节点位置时出错:', error);
      return null;
    }
  }
  
  // Handle chat message that might affect the editor
  function handleChatMessage(event: CustomEvent) {
    // 详细记录收到的消息





    const { action, content, from, to, partial } = event.detail;

    if (!editorRef) return;

    const editor = editorRef.getEditor();
    if (!editor) return;

    if (action === 'append-text' && content) {
      // 追加文本到编辑器末尾
      const { state } = editor;
      const { doc } = state;
      const endPos = doc.content.size;

      // 检查是否需要添加空行
      if (endPos > 0 && !partial) {
        // 获取最后一个节点
        const lastNode = doc.lastChild;

        // 如果最后一个节点不是空的，添加两个换行
        if (lastNode && lastNode.textContent.trim() !== '') {
          editor.chain().focus().command(({ tr }) => {
            tr.insert(endPos, editor.schema.text('\n\n'));
            return true;
          }).run();
        }
      }

      // 插入新内容
      editor.chain().focus().insertContentAt(endPos, content).run();

      // 滚动到新内容的位置
      setTimeout(() => {
        const editorElement = document.querySelector('.ProseMirror');
        if (editorElement) {
          editorElement.scrollTop = editorElement.scrollHeight;
        }
      }, 200);
    } else if (action === 'insert-text' && content) {
      // 处理插入文本动作，支持position参数
      const { state } = editor;
      const { doc } = state;
      const position = event.detail.position || 'cursor';

      let insertPos;

      // 根据position决定插入位置
      if (position === 'end') {
        // 在文档末尾插入
        insertPos = doc.content.size;

        // 检查是否需要添加空行
        if (insertPos > 0) {
          const lastNode = doc.lastChild;

          // 如果最后一个节点不是空的，添加两个换行
          if (lastNode && lastNode.textContent.trim() !== '') {
            editor.chain().focus().command(({ tr }) => {
              tr.insert(insertPos, editor.schema.text('\n\n'));
              return true;
            }).run();
          }
        }
      } else if (position === 'start') {
        // 在文档开头插入
        insertPos = 0;
      } else {
        // 默认在光标位置插入
        insertPos = editor.state.selection.anchor;
      }

      // 插入内容
      editor.chain().focus().insertContentAt(insertPos, content).run();

      // 如果是在末尾插入，滚动到新内容位置
      if (position === 'end') {
        setTimeout(() => {
          const editorElement = document.querySelector('.ProseMirror');
          if (editorElement) {
            editorElement.scrollTop = editorElement.scrollHeight;
          }
        }, 200);
      }
    } else if (action === 'replace-text' && content) {
      // 记录详细调试信息

      
      try {
        // 首先检查内容是否为JSON格式的增量更新
        if (content.startsWith('[') && content.includes('"path":') || 
            (content.startsWith('"[{') && content.includes('"path":'))) {
          try {
            // 解析JSON增量更新
            let updateData;
            if (content.startsWith('"[{')) {
              // 处理新格式：带引号的JSON字符串
              updateData = JSON.parse(JSON.parse(content));
            } else {
              // 处理旧格式：直接的JSON
              updateData = JSON.parse(content);
            }
            
            // 使用增量JSON节点更新方法
            handleIncrementalNodeUpdate(editor, updateData);

            return; // 已经处理，直接返回
          } catch (jsonError) {
            console.error('JSON解析或处理失败:', jsonError);
          }
        }
        
        // 如果不是JSON格式的增量更新，检查是否有选区
        if (from !== undefined && to !== undefined) {
          // 使用新的JSON节点修订系统
          const docSize = editor.state.doc.content.size;
          
          // 确保位置在文档范围内
          if (from < 0 || to < 0 || from > docSize || to > docSize || from > to) {
            console.error('无效的选区范围:', { from, to, docSize });
            // 如果范围无效，则将内容插入到光标位置
            const insertPos = editor.state.selection.anchor;
            editor.chain().focus().insertContentAt(insertPos, content).run();
            return;
          }
          
          // 获取选中的文本
          const selectedText = editor.state.doc.textBetween(from, to, ' ');

          // 检查是否是多行内容
          const selectedFragment = editor.state.doc.slice(from, to);
          
          // 验证selectedFragment和content属性
          if (!selectedFragment || !selectedFragment.content) {
            console.error('选区片段无效:', selectedFragment);
            // 如果选区无效，则将内容插入到光标位置
            const insertPos = editor.state.selection.anchor;
            editor.chain().focus().insertContentAt(insertPos, content).run();
            return;
          }
          
          const isMultiBlock = selectedFragment.content.childCount > 1;

          // 检查是否包含多个块级节点
          let hasMultipleBlocks = false;
          selectedFragment.content.forEach((node) => {
            if (node.type.name === 'paragraph' || node.type.name.startsWith('heading')) {
              hasMultipleBlocks = true;
            }
          });

          // 检查编辑器中是否注册了 revision 功能
          const hasRevisionCommands = editor.commands && (editor.commands as any).createRevisionFromSelection;

          
          if (hasRevisionCommands) {
            try {

              // 选中要替换的范围
              editor.chain().focus().setTextSelection({ from, to }).run();
              
              // 创建修订节点（替代类型）
              console.log('修订参数:', {
                type: 'substitution',
                newContent: content
              });
              const revisionCreated = (editor.commands as any).createRevisionFromSelection({
                type: 'substitution',
                newContent: content
              });

              
              if (!revisionCreated) {
                console.warn('修订节点创建失败，回退到简单替换');
                editor.chain().focus().deleteRange({ from, to })
                  .insertContentAt(from, content)
                  .run();
              } else {
                // 创建成功，修订已集成到主工具栏

                
                // 触发自定义事件通知 EditorToolbar 更新修订列表
                document.dispatchEvent(new CustomEvent('revisionUpdated'));
                
                // 验证DOM中是否存在修订节点
                setTimeout(() => {
                  const revisionNodes = document.querySelectorAll('.revision');

                  if (revisionNodes.length > 0) {
                    console.log('修订节点样式:', window.getComputedStyle(revisionNodes[0]));
                  }
                }, 100);
              }
            } catch (revisionError) {
              console.error('创建修订节点失败:', revisionError);
              // 回退到简单替换
              editor.chain().focus().deleteRange({ from, to })
                .insertContentAt(from, content)
                .run();
            }
          } else if (isMultiBlock) {
            try {
              // 获取选区内容的片段
              const selectedFragment = editor.state.doc.slice(from, to);
              const selectedHTML = editor.view.dom.ownerDocument.createElement('div');

              // 将 Fragment 转换为 DOM
              if (selectedFragment.content && typeof selectedFragment.content.forEach === 'function') {
                selectedFragment.content.forEach((node: any) => {
                  if (node.toDOM) {
                    selectedHTML.appendChild(node.toDOM());
                  }
                });
              }

              const oldContentHTML = selectedHTML.innerHTML;

              editor.chain().focus()
                .deleteRange({ from, to })
                .insertContentAt(from, content)
                .run();
            } catch (error) {
              console.error('使用块级取代节点失败:', error);
              // 回退到简单替换
              editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, content).run();
            }
          } else {
            // 回退到简单的文本替换
            editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, content).run();
          }
        }
      } catch (replaceError) {
        console.error('替换失败:', replaceError);
        
        // 最后的回退手段：简单替换
        editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, content).run();
      }
      // Update editor content store after insertion
      setTimeout(() => {
        editorContent.set(editor.getHTML());
      }, 100);
    } else if (action === 'insert-image' && content) {
      // 处理插入图片动作

      
      const { state } = editor;
      const { doc } = state;
      const position = event.detail.position || 'cursor';
      
      let insertPos;
      
      // 根据position决定插入位置
      if (position === 'end') {
        // 在文档末尾插入
        insertPos = doc.content.size;
        
        // 检查是否需要添加空行
        if (insertPos > 0) {
          const lastNode = doc.lastChild;
          
          // 如果最后一个节点不是空的，添加两个换行
          if (lastNode && lastNode.textContent.trim() !== '') {
            editor.chain().focus().command(({ tr }) => {
              tr.insert(insertPos, editor.schema.text('\n\n'));
              return true;
            }).run();
          }
        }
      } else if (position === 'start') {
        // 在文档开头插入
        insertPos = 0;
      } else {
        // 默认在光标位置插入
        insertPos = editor.state.selection.anchor;
      }
      
      // 创建图片HTML
      const imageHtml = `<img src="${content}" alt="Generated image" />`;
      
      // 插入图片
      editor.chain().focus().insertContentAt(insertPos, imageHtml).run();
      
      // 如果是在末尾插入，滚动到新内容位置
      if (position === 'end') {
        setTimeout(() => {
          const editorElement = document.querySelector('.ProseMirror');
          if (editorElement) {
            editorElement.scrollTop = editorElement.scrollHeight;
          }
        }, 200);
      }
      
      // 更新编辑器内容store
      setTimeout(() => {
        editorContent.set(editor.getHTML());
      }, 100);
    } else {
      // Optional: Log unknown actions for debugging
      console.warn(`Unknown action type received in handleChatMessage: ${action}`);
    }
  }

  // Handle fullscreen toggle
  function toggleFullscreen() {
    isFullscreen = !isFullscreen;
    
    if (isFullscreen) {
      // Hide sidebars when entering fullscreen
      fileSidebarCollapsed.set(true);
      chatPanelCollapsed.set(true);
    } else {
      // Show sidebars when exiting fullscreen
      fileSidebarCollapsed.set(false);
      chatPanelCollapsed.set(false);
    }
  }

  // Handle save file dialog
  function handleSaveFile() {
    if ($activeFile) {
      // 获取当前编辑器状态为JSON格式，保留完整编辑器状态
      const editor = editorRef ? editorRef.getEditor() : null;
      if (!editor) {
        console.error('编辑器实例不可用');
        return;
      }
      
      // 获取编辑器完整JSON状态
      const editorState = editor.getJSON();
      const content = JSON.stringify(editorState, null, 2); // 美化格式化为可读性更好的JSON
      
      // 检查是否在Electron环境中
      if (isElectron && window.electronAPI) {

        
        // 更新文件内容，同时保存原始JSON字符串和解析后的编辑器状态对象
        // 这确保了文件内容是JSON字符串（用于保存到磁盘），而editorContent是解析后的对象（用于编辑器显示）
        fileStore.updateFileContent($activeFile.id, content, editorState);
        
        // 如果文件已经有本地路径，直接保存
        if ($activeFile.localFilePath) {
          fileStore.saveFile($activeFile.id, content)
            .then(() => {
              console.log(`文件已保存到: ${$activeFile.localFilePath}`);
            })
            .catch(error => {
              console.error('保存文件失败:', error);
            });
        } else {
          // 在Electron环境中，直接使用原生对话框保存文件
          // 使用.json扩展名以反映实际内容格式
          const suggestedName = ($activeFile.title || 'untitled').replace(/\.md$|\.txt$|\.json$/, '') + '.json';
          fileStore.saveFileToDisk($activeFile.id, suggestedName)
            .then((path) => {
              if (path) {
                console.log(`文件已保存到: ${path}`);
              }
            })
            .catch(error => {
              console.error('保存文件失败:', error);
            });
        }
      } else {
        // 非Electron环境，使用原有的保存逻辑
        // 同样更新文件内容，包括editorContent
        fileStore.updateFileContent($activeFile.id, content, editorState);
        fileToSave = $activeFile.id;
        showSaveDialog = true;
      }
    }
  }

  // Handle dialog close
  function handleDialogClose() {
    showSaveDialog = false;
    fileToSave = null;
  }

  // Handle file saved
  function handleFileSaved(event: CustomEvent) {
    const { path } = event.detail;

  }

  // Handle creating a new file
  function handleCreateNewFile() {
    if (!$isAuthenticated) {
      console.error('Not authenticated with Google Drive, cannot create new file');
      return;
    }
    
    // Create a new file with a default name and empty content
    const timestamp = new Date().toISOString().slice(0, 10);
    const fileName = `New Document ${timestamp}`;
    fileStore.createFile(fileName, '');
  }

  // Handle save button click
  function handleSaveClick() {
    if ($activeFile) {
      if ($isAuthenticated) {
        // For Google Drive files, they're already auto-saved
        console.log('File is already saved to Google Drive');
      } else {
        // For temporary files, show a message that they need to sign in
        console.log('Sign in to save files permanently');
        // Could also show a toast or modal here
      }
    }
  }
</script>

<main class="app-container" class:fullscreen={isFullscreen}>
  <!-- Main content directly without the header -->
  <div class="main-content" style="width: 100%;">
    <!-- Left file sidebar -->
    <div class="file-sidebar-container" class:collapsed={$fileSidebarCollapsed} style="display: flex; flex-direction: column;">
      <button class="sidebar-toggle-button left" on:click={() => fileSidebarCollapsed.toggle()}
              title={$fileSidebarCollapsed ? "Expand file sidebar" : "Collapse file sidebar"}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          {#if $fileSidebarCollapsed}
            <!-- Chevron right icon for collapsed state -->
            <polyline points="9 18 15 12 9 6"></polyline>
          {:else}
            <!-- Chevron left icon for expanded state -->
            <polyline points="15 18 9 12 15 6"></polyline>
          {/if}
        </svg>
      </button>

      <div class="sidebar-content-wrapper">
        {#if $isAuthenticated}
        <FileSidebar {editor} />
      {:else}
        <div class="sidebar-container">
          <!-- Tab navigation buttons -->
          <div class="sidebar-tabs">
            <button 
              class="tab-button active" 
              title="File List"
              aria-label="File List"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
            </button>
            <button 
              class="tab-button" 
              on:click={() => $documentTreeVisible = !$documentTreeVisible}
              title="Document Structure"
              aria-label="Document Structure"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="17" y1="10" x2="3" y2="10"></line>
                <line x1="21" y1="6" x2="3" y2="6"></line>
                <line x1="21" y1="14" x2="3" y2="14"></line>
                <line x1="17" y1="18" x2="3" y2="18"></line>
              </svg>
            </button>
            <button 
              class="tab-button" 
              title="New File"
              aria-label="New File"
              on:click={() => showNewFileDialog = true}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="12" y1="18" x2="12" y2="12"></line>
                <line x1="9" y1="15" x2="15" y2="15"></line>
              </svg>
            </button>
            
            <!-- Spacer to push export buttons to the right -->
            <div style="flex-grow: 1;"></div>
            
            <!-- Export buttons - accessible to all users -->
            <button
              class="export-button"
              on:click={handleExportImages}
              disabled={isExporting}
              title="Export to Image"
              aria-label="Export to Image"
            >
              <i class="fas fa-image"></i>
            </button>
            <button
              class="export-button"
              on:click={handleExportPDF}
              disabled={isExporting}
              title="Export to PDF"
              aria-label="Export to PDF"
            >
              <i class="fas fa-file-pdf"></i>
            </button>
          </div>
          
          {#if $documentTreeVisible}
            <div class="document-tree-container">
              {#if editor}
                <DocumentTree {editor} />
              {:else}
                <div class="empty-state">
                  <p>Loading document structure...</p>
                </div>
              {/if}
            </div>
          {:else}
            {#if !isElectron}
              <div class="auth-required-message">
                <p>Please sign in with Google Drive to access your files.</p>
                <GoogleAuthButton buttonClass="sidebar-auth-button" />
              </div>
            {/if}
          {/if}
        </div>
      {/if}
      </div>
    </div>

    <!-- Middle editor area -->
    <div class="editor-wrapper" bind:this={editorElement}>
      <div class="editor-header">
        <h1>{$activeFile ? $activeFile.title.split('.').slice(0, -1).join('.') || $activeFile.title : 'Untitled'}</h1>
        <div class="editor-actions">
          {#if !isElectron}
            {#if $isAuthenticated}
              <button class="save-button" on:click={handleSaveClick} disabled={isExporting || !$activeFile}>
                Save to Drive
              </button>
            {:else if $activeFile?.isTemporary}
              <div class="temp-file-notice" title="This is a temporary file. Sign in with Google Drive to save your work permanently.">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
              </div>
            {/if}
          {/if}
          
          {#if isElectron && $activeFile?.isTemporary}
            <div class="temp-file-notice" title="This is a temporary file.">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
          {/if}
          <!-- Save notification removed as requested -->
          
          <!-- Fullscreen toggle button -->
          <button class="fullscreen-button" on:click={toggleFullscreen} title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              {#if isFullscreen}
                <!-- Minimize icon -->
                <path d="M8 3v3a2 2 0 0 1-2 2H3"></path>
                <path d="M21 8h-3a2 2 0 0 1-2-2V3"></path>
                <path d="M3 16h3a2 2 0 0 1 2 2v3"></path>
                <path d="M16 21v-3a2 2 0 0 1 2-2h3"></path>
              {:else}
                <!-- Maximize icon -->
                <path d="M8 3H5a2 2 0 0 0-2 2v3"></path>
                <path d="M21 8V5a2 2 0 0 0-2-2h-3"></path>
                <path d="M3 16v3a2 2 0 0 0 2 2h3"></path>
                <path d="M16 21h3a2 2 0 0 0 2-2v-3"></path>
              {/if}
            </svg>
          </button>
          
          <!-- 修订工具栏切换按钮已移除 -->
        </div>
      </div>
      
      <TiptapEditor 
        bind:this={editorRef} 
        on:editor-init={handleEditorInit}
        on:update={handleEditorUpdate}
      />
    </div>

    <!-- Right chat panel -->
    <div class="chat-panel-container" class:collapsed={$chatPanelCollapsed}>
      <button class="sidebar-toggle-button right" on:click={() => chatPanelCollapsed.toggle()}
              title={$chatPanelCollapsed ? "Expand chat panel" : "Collapse chat panel"}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          {#if $chatPanelCollapsed}
            <!-- Chevron left icon for collapsed state -->
            <polyline points="15 18 9 12 15 6"></polyline>
          {:else}
            <!-- Chevron right icon for expanded state -->
            <polyline points="9 18 15 12 9 6"></polyline>
          {/if}
        </svg>
      </button>
      <ChatPanel 
        bind:this={chatPanelRef}
        on:message={handleChatMessage} 
        getEditorContent={getEditorContent}
        getDocumentWordCount={getDocumentWordCount}
        getDocumentCharCount={getDocumentCharCount}
        {handleExportImages}
        {handleExportPDF}
        bind:isExporting
        documentId={$activeFile ? $activeFile.id : 'default'}
        getCurrentSelection={getCurrentSelection}
        editor={editorRef ? editorRef.getEditor() : null}
      />
    </div>
  </div>
  
  <!-- File save dialog -->
  <FileSaveDialog 
    bind:show={showSaveDialog}
    fileId={fileToSave}
    suggestedName={$activeFile?.title || 'Untitled.txt'}
    on:close={handleDialogClose}
    on:saved={handleFileSaved}
  />
  
  <!-- Word-style new file dialog -->
  <WordStyleNewFileDialog
    show={showNewFileDialog}
    on:close={() => showNewFileDialog = false}
    on:create-blank={handleCreateBlankDocument}
    editorContent={editorRef ? editorRef.getEditorJSON() : ''}
  />
</main>

<style>
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh; /* 浏览器环境下的高度 */
    margin: 0 auto;
    padding: 0;
  }
  
  /* 针对Electron环境的特殊处理 */
  :global(.electron) .app-container {
    height: 100%; /* Electron环境下使用100%而不是100vh */
  }
  
  .main-content {
    display: flex;
    height: 100%;
    flex: 1;
    overflow: hidden;
    width: 100%;
  }
  
  .file-sidebar-container {
    width: 20%;
    /* overflow: hidden; */ /* Allow button to be visible outside */
    border-right: 1px solid #e9ecef;
    transition: width 0.3s ease;
    position: relative;
    z-index: 15; /* Ensure sidebar is above editor */
  }

  .sidebar-content-wrapper {
    overflow: hidden;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  
  .file-sidebar-container.collapsed {
    width: 50px;
  }
  
  .editor-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-radius: 0.5rem;
    position: relative; /* Create stacking context */
    z-index: 10; /* Lower than sidebars */
  }
  
  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid #e9ecef;
    /*background-color: #f8f9fa;*/
    height: 48px;
    box-sizing: border-box;
  }
  
  .editor-header h1 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .save-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #4a5568;
    color: white;
    border: none;
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .save-button:hover {
    background-color: #2d3748;
  }
  
  .fullscreen-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f8f9fa;
    color: #495057;
    border: 1px solid #dee2e6;
    border-radius: 0.25rem;
    padding: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
    width: 32px;
    height: 32px;
  }
  
  .fullscreen-button:hover {
    background-color: #e9ecef;
    border-color: #adb5bd;
  }
  
  .editor-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  /* Fullscreen mode styles */
  .app-container.fullscreen .file-sidebar-container,
  .app-container.fullscreen .chat-panel-container {
    display: none;
  }
  
  .app-container.fullscreen .editor-wrapper {
    width: 100%;
    max-width: none;
  }
  
  /* 聊天面板容器 */
  :global(.chat-panel-container) {
    width: 30%;
    transition: width 0.3s ease;
    position: relative;
    z-index: 15; /* Ensure sidebar is above editor */
  }
  
  .chat-panel-container.collapsed {
    width: 40px;
  }
  
  .sidebar-toggle-button {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 20;
  }
  
  .sidebar-toggle-button:hover {
    background-color: #e9ecef;
  }
  
  .sidebar-toggle-button.left {
    right: -16px;
  }
  
  .sidebar-toggle-button.right {
    left: -16px;
  }
  
  .auth-required-message {
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    text-align: center;
    margin-top: 1rem;
  }
  
  .auth-required-message p {
    margin-bottom: 1rem;
    color: #6c757d;
  }
  
  /* Removed unused sidebar-auth-button styles */
  
  .temp-file-notice {
    display: none;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;
    /*background-color: #f3f4f6;*/
    padding: 0.5rem 0.75rem;
    border-radius: 0.25rem;
  }
  
  /* Removed unused action-button styles */
  
  /* Sidebar styles */
  .sidebar-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #f8f9fa;
  }
  
  .sidebar-tabs {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem;
    height: 48px;
    box-sizing: border-box;
    align-items: center;
    border-bottom: none;
  }
  
  .tab-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 0.5rem;
    cursor: pointer;
    color: #495057;
    transition: background-color 0.2s, color 0.2s;
  }
  
  .tab-button:hover:not(:disabled) {
    background-color: #e9ecef;
    color: #212529;
  }
  
  .tab-button.active {
    background-color: #e9ecef;
    color: #212529;
  }
  
  .tab-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .export-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: #495057;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s, color 0.2s;
  }
  
  .export-button:hover {
    background-color: #e9ecef;
    color: #212529;
  }
  
  .export-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .document-tree-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    height: calc(100% - 50px); /* Account for the tab buttons */
  }
</style>
