<script lang="ts">
  import { onMount, createEventDispatcher, onDestroy } from 'svelte';
  import { streamChat, uploadFile, uploadFiles, type StreamResponse } from '../services/chatApi';
  import ChatMessage from './ChatMessage.svelte';
  import ChatInput from './ChatInput.svelte';
  import '../styles/ChatPanel.css';
  import { chatPanelCollapsed } from '../../ui';
  import { ChatSessionManager } from './ChatSessionManager';
  import type { Editor } from '@tiptap/core';
  import { v4 as uuidv4 } from 'uuid';
  import type { ChatMessage as ChatHistoryMessage } from '../../editor/extensions/ChatHistoryExtension';
  import SettingsButton from '../../ui/SettingsButton.svelte';
  import { t, locale } from '../../../lib/i18n/index';
  import { marked } from 'marked';
  import hljs from 'highlight.js';
  import 'highlight.js/styles/github.css';
  import { systemPrompt } from '../services/systemPromptService';
  import { getLanguageName } from '../../../lib/i18n/languageUtils';
  import { logger } from '../../../lib/debug/logger';
  import { selectedModelId, apiKey, isConfigValid } from '../../../lib/stores/modelStore';
  
  // Detect if running in Electron environment
  let isElectron = false;
  if (typeof window !== 'undefined') {
    isElectron = window.environment?.isElectron === true;
  }
  
  // 导出函数，用于从父组件接收
  export const handleExportImages: () => Promise<void> = async () => { logger.info('Export Images requested'); };
  export const handleExportPDF: () => Promise<void> = async () => { logger.info('Export PDF requested'); };
  export const isExporting: boolean = false;
  
  // 接收从父组件传递的函数
  export let getEditorContent: () => string = () => '';
  export let getDocumentWordCount: () => number = () => 0;
  export let getDocumentCharCount: () => number = () => 0;
  export let getCurrentSelection: () => { text: string, from: number, to: number, nodeInfos?: any[] } | null = () => null;
  
  // Tiptap editor reference for accessing chat history
  export let editor: Editor | null = null;
  
  // 存储选中文本的信息
  let selectedTextInfo: {
    text: string;
    from?: number;
    to?: number;
    selectedNodesInfo?: any[]; // Added selectedNodesInfo
  } | null = null;

  // 处理从编辑器选择的文本
  export function setMessageFromSelection(selectedText: string, from?: number, to?: number, nodesInfo?: any[]) { // Added nodesInfo parameter
    if (selectedText && selectedText.trim()) {
      // 存储选中文本的完整信息，用于后续替换
      selectedTextInfo = {
        text: selectedText,
        from,
        to,
        selectedNodesInfo: nodesInfo // Store selectedNodesInfo
      };
      
      // 提取前6个字符作为摘要
      const summary = selectedText.length > 8 ? selectedText.substring(0, 8) + '...' : selectedText;
      
      // 构建包含摘要和位置信息的消息
      const positionInfo = from !== undefined && to !== undefined ? `[${from}-${to}]` : '';
      
      // 设置新消息
      newMessage = `{{${summary}${positionInfo}}}`;
      
      // 聚焦输入框
      setTimeout(() => {
        // 查找输入框元素
        const inputElement = document.querySelector('.chat-input-card textarea') as HTMLTextAreaElement;
        if (inputElement) {
          inputElement.focus();
        } else {
          // 备用方案：尝试查找任何文本区域
          const alternativeInput = document.querySelector('textarea');
          if (alternativeInput) {
            (alternativeInput as HTMLTextAreaElement).focus();
          }
        }
      }, 0);
    }
  }
  
  const dispatch = createEventDispatcher();
  
  // Chat messages
  let messages: ChatHistoryMessage[] = [];
  
  // Chat session manager
  let chatSessionManager: ChatSessionManager | null = null;
  
  // Track current language for chat responses
  let currentLanguage = $locale;
  let currentSystemPrompt = $systemPrompt;
  
  // Subscribe to language changes
  $: currentLanguage = $locale;
  $: currentSystemPrompt = $systemPrompt;
  
  // 添加新消息到历史记录
  function addMessage(message: ChatHistoryMessage) {
    messages = [...messages, message];
    logger.debug('addMessage: added message to local messages array:', message);
    // Save to document chat history
    // 如果是初始的thinking消息"Figuring out what you want..."，则不保存到历史记录
    if (message.thinking && message.content.trim() === 'Figuring out what you want...') {
      return;
    }
    
    if (chatSessionManager) {
      const result = chatSessionManager.addMessage(message);
      console.log('addMessage: saved to document chat history, result:', result);
    } else {
      console.log('addMessage: chatSessionManager is null, message not saved to document');
    }
  }
  
  // UI state
  let chatContainer: HTMLElement;
  const CHAT_MESSAGE_KEY = 'unsentChatMessage'; // Key for localStorage
  let newMessage = ''; // Default value
  if (typeof window !== 'undefined' && window.localStorage) {
    const savedMessage = window.localStorage.getItem(CHAT_MESSAGE_KEY);
    if (savedMessage) {
      newMessage = savedMessage;
    }
  }
  
  let selectedFiles: File[] = [];
  let filePreviews: Map<string, string> = new Map();
  let isUploading = false;
  
  // 执行编辑器操作
  function executeEditorAction(action: any) {
    // 记录接收到的action对象，便于调试
    logger.debug('执行编辑器动作:', action);
    
    // 验证action对象是否有效
    if (!action || typeof action !== 'object' || !action.type) {
      logger.error('无效的action对象:', action);
      return;
    }
    
    // 使用统一的action类型字符串处理不同类型的动作
    if (action.type === 'insert-text' || action.type === 'append-text') {
      if (selectedTextInfo && selectedTextInfo.from !== undefined && selectedTextInfo.to !== undefined && action.payload.position === 'cursor') {
        // 如果有选中的文本，则替换选中的文本
        dispatch('message', {
          action: 'replace-text',
          content: action.payload.content,
          from: selectedTextInfo.from,
          to: selectedTextInfo.to,
          partial: action.payload.partial // 传递partial标志，表示是否为部分内容
        });
        // 如果不是部分内容，替换完成后清空选中文本信息
        if (!action.payload.partial) {
          selectedTextInfo = null;
        }
      } else {
        // 如果没有选中文本，则直接插入内容
        dispatch('message', {
          action: 'insert-text',
          content: action.payload.content,
          position: action.payload.position,
          partial: action.payload.partial // 传递partial标志，表示是否为部分内容
        });
      }
    } else if (action.type === 'append-text') {
      // 处理append-text类型的操作，用于追加内容到编辑器末尾
      dispatch('message', {
        action: 'append-text',
        content: action.payload.content,
        partial: action.payload.partial // 传递partial标志，表示是否为部分内容
      });
    } else if (action.type === 'replace-text') {
      // 处理replace-text类型的操作，用于替换选中文本
      // 使用from和to属性，如果不存在则尝试使用start和end属性（向后兼容）
      const from = action.payload.from !== undefined ? action.payload.from : action.payload.start;
      const to = action.payload.to !== undefined ? action.payload.to : action.payload.end;
      
      console.log('替换文本动作参数:', {
        content: action.payload.content,
        from: from,
        to: to,
        'payload.from': action.payload.from,
        'payload.to': action.payload.to,
        'payload.start': action.payload.start,
        'payload.end': action.payload.end
      });
      
      dispatch('message', {
        action: 'replace-text',
        content: action.payload.content,
        from: from,
        to: to,
        partial: action.payload.partial // 传递partial标志，表示是否为部分内容
      });
    } else if (action.type === 'replace-all') {
      // 处理replace-all类型的操作，用于替换所有内容
      dispatch('message', {
        action: 'replace-all',
        content: action.payload.content,
        partial: action.payload.partial
      });
    } else if (action.type === 'insert-image') {
      // 处理insert-image类型的操作，用于插入图片
      logger.debug('处理图片插入动作:', action.payload);
      
      // 检查是否是base64格式
      const isBase64 = action.payload.is_base64 === true;
      let imageContent;
      
      if (isBase64 && action.payload.data) {
        // 如果是base64格式，构建完整的data URL
        const mimeType = action.payload.mime_type || 'image/png';
        imageContent = `data:${mimeType};base64,${action.payload.data}`;
        console.log('使用base64图片数据');
      } else if (action.payload.url) {
        // 如果是URL格式，直接使用URL
        imageContent = action.payload.url;
        console.log('使用URL图片数据');
      } else {
        console.error('图片数据格式错误:', action.payload);
        return;
      }
      
      dispatch('message', {
        action: 'insert-image',
        content: imageContent,
        position: action.payload.position || 'cursor',
        partial: action.payload.partial || false
      });
    } else {
      // 未知的操作类型
      logger.warn('Unknown action type:', action.type);
    }
  }
  
  // 获取编辑器当前选中的文本及其位置信息
  function getEditorSelection(): { text: string, from: number, to: number, selectedNodesInfo?: any[] } | null { // Modified return type
    try {
      // 直接使用从父组件传递的 getCurrentSelection 函数
      const selection = getCurrentSelection();
      
      if (selection) {
        // 转换属性名 nodeInfos 到 selectedNodesInfo
        return {
          text: selection.text,
          from: selection.from,
          to: selection.to,
          selectedNodesInfo: selection.nodeInfos // 注意属性名的变化
        };
      }
      
      return null;
    } catch (error) {
      logger.error('获取编辑器选择时出错:', error);
      return null;
    }
  }

  // 获取选中文本信息
  function getSelectedTextInfo() {
    if (!editor) return null;
    
    const { state } = editor;
    const { from, to } = state.selection;
    
    if (from === to) return null; // 没有选中文本
    
    const selectedText = state.doc.textBetween(from, to);
    
    // 获取选中文本所在的节点信息
    const nodeInfos: any[] = [];
    state.doc.nodesBetween(from, to, (node, pos) => {
      if (node.type.name !== 'text') {
        nodeInfos.push({
          type: node.type.name,
          attrs: node.attrs,
          position: pos
        });
      }
      return true;
    });
    
    return {
      text: selectedText,
      from,
      to,
      nodeInfos
    };
  }
  
  // 接受所有待处理的修订
  function acceptAllPendingRevisions() {
    if (!editor) return;
    
    try {
      // 遍历文档中的所有节点，找到所有修订节点并接受它们
      const { state } = editor;
      const { doc } = state;
      const revisionIds: string[] = [];
      
      // 首先收集所有待处理修订的ID
      doc.descendants((node: any) => {
        if (node.type.name === 'revisionNode' && node.attrs.status === 'pending') {
          console.log('MATCH! Attempting to push ID:', node.attrs.id, 'Type of ID:', typeof node.attrs.id);
          revisionIds.push(node.attrs.id);
        }
        return true;
      });
      
      // 然后接受所有收集到的修订
      revisionIds.forEach(id => {
        try {
          // @ts-ignore
          if (typeof editor.commands.acceptRevision === 'function') {
            editor.commands.acceptRevision(id);
          }
        } catch (e) {
          logger.error(`接受修订 ${id} 时出错:`, e);
        }
      });
      
      // 如果有修订被接受，强制更新编辑器状态
      if (revisionIds.length > 0) {
        // 1. 强制执行一个文档更新操作
        editor.commands.focus();
        
        // 2. 强制重新渲染编辑器
        editor.view.updateState(editor.view.state);
        
        // 3. 触发自定义事件，通知工具栏更新
        const event = new CustomEvent('revisions-updated', { detail: { count: 0 } });
        document.dispatchEvent(event);
        
        // 4. 延迟一点时间再次检查并更新
        setTimeout(() => {
          // 再次检查是否还有待处理的修订
          let hasPending = false;
          editor.state.doc.descendants((node: any) => {
            if (node.type.name === 'revisionNode' && node.attrs.status === 'pending') {
              hasPending = true;
              return false;
            }
            return true;
          });
          
          if (!hasPending) {
            // 如果没有待处理的修订，再次触发事件
            const event = new CustomEvent('revisions-updated', { detail: { count: 0 } });
            document.dispatchEvent(event);
          }
        }, 100);
      }
      
      console.log(`已自动接受 ${revisionIds.length} 个待处理修订`);
    } catch (e) {
      console.error('接受所有修订时出错:', e);
    }
  }
  
  // 发送消息的函数
  async function sendMessage() {
    if (!newMessage.trim() && selectedFiles.length === 0) return;
    
    // 检查是否有待处理的修订
    // 使用 try-catch 来安全地调用可能不存在的命令
    try {
      // @ts-ignore - 忽略类型检查，因为我们已经添加了这个命令但TypeScript可能还没有更新类型定义
      if (editor && typeof editor.commands.hasPendingRevisions === 'function' && editor.commands.hasPendingRevisions()) {
        // 如果有待处理的修订，自动接受所有修订
        acceptAllPendingRevisions();
      }
    } catch (e) {
      console.error('检查待处理修订时出错:', e);
      // 如果出错，继续执行，不阻止发送消息
    }
    
    let messageToSend = newMessage.trim();
    
    // 不再自动添加选中文本信息到用户消息
    // 仍然获取当前选择，以便传递给API
    const currentSelection = getEditorSelection();
    
    if (currentSelection) {
      // 获取选中文本信息
      selectedTextInfo = {
        text: currentSelection.text,
        from: currentSelection.from,
        to: currentSelection.to,
        selectedNodesInfo: currentSelection.selectedNodesInfo
      };
    } else {
      selectedTextInfo = null; // Explicitly nullify if no selection
    }
    
    // Add user message
    const userMessage: {
      id: string;
      content: string;
      sender: 'user' | 'assistant';
      timestamp: string;
      attachment?: {
        type: string;
        name: string;
        url: string;
      };
      selectedText?: {
        text: string;
        from: number;
        to: number;
      };
    } = {
      id: uuidv4(),
      content: messageToSend,
      sender: 'user' as const,
      timestamp: new Date().toISOString()
    };
    
    // 如果有文件附件
    if (selectedFiles.length > 0) {
      // 创建文件ID
      const fileId = `${selectedFiles[0].name}-${selectedFiles[0].size}-${Date.now()}`;
      userMessage.attachment = {
        type: selectedFiles[0].type,
        name: selectedFiles[0].name,
        url: filePreviews.get(fileId) || ''
      };
    }
    
    // 如果有选中的文本，添加到用户消息中，但不显示在消息内容中
    if (selectedTextInfo && selectedTextInfo.from !== undefined && selectedTextInfo.to !== undefined) {
      userMessage.selectedText = {
        text: selectedTextInfo.text,
        from: selectedTextInfo.from,
        to: selectedTextInfo.to
      };
    }
    
    addMessage(userMessage);
    scrollToBottom();
    
    // 立即清空输入框，避免用户误解
    const originalMessage = newMessage;
    newMessage = '';
    
    // 获取编辑器内容
    const editorContent = getEditorContent();
    const cleanMessage = userMessage.content;
    
    // 用于跟踪当前思考消息的索引
    let currentThinkingMessageIndex: number | null = null;
    // Track streaming message index separately
    let currentStreamMessageIndex: number | null = null;

    // 不再需要从消息中解析位置信息，因为我们不再自动添加选中文本信息到用户消息
    
    // 处理流式响应的回调函数
    const handleStreamResponse = (chunk: StreamResponse) => {
      // 处理流式响应
      if (chunk.type === 'thinking' as const) {
        // 每次收到新的thinking消息时，创建一个新的消息对象
        // 如果已有thinking消息，先删除它
        if (currentThinkingMessageIndex !== null) {
          const updatedMessages = [...messages];
          updatedMessages.splice(currentThinkingMessageIndex, 1);
          messages = updatedMessages;
        }
        
        // 创建新的thinking消息
        const thinkingMessage = {
          id: uuidv4(),
          content: chunk.content,
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: true
        };
        
        addMessage(thinkingMessage);
        currentThinkingMessageIndex = messages.length - 1;
        scrollToBottom();
      } else if (chunk.type === 'stream') {
        // Streaming a new assistant message
        if (currentStreamMessageIndex === null) {
          const streamMsg = {
            id: uuidv4(),
            content: chunk.content,
            sender: 'assistant' as const,
            timestamp: new Date().toISOString(),
            thinking: false
          };
          addMessage(streamMsg);
          currentStreamMessageIndex = messages.length - 1;
        } else {
          const updated = [...messages];
          updated[currentStreamMessageIndex].content += chunk.content;
          messages = updated;
        }
        scrollToBottom();
      } else if (chunk.type === 'action' as const) {
        // 重置当前思考消息引用
        currentThinkingMessageIndex = null;
        // Reset streaming index when done
        currentStreamMessageIndex = null;
        
        // 处理消息块中的动作
        let messageContent = chunk.content;
        
        // 检查是否是插入图片的动作
        if (chunk.action && typeof chunk.action === 'object' && 'type' in chunk.action) {
          if (chunk.action.type === 'insert-image' && 'payload' in chunk.action && 
              chunk.action.payload && 'url' in chunk.action.payload) {
            // 使用图片的Markdown语法
            messageContent = $t('chat.imageGenerated') + `\n![${$t('chat.generatedImage')}](${chunk.action.payload.url})`;
          }
        }
        
        // 最终结果作为新消息添加
        const finalMessage = {
          id: uuidv4(),
          content: messageContent,
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: false
        };
        
        addMessage(finalMessage);
        scrollToBottom();
        
        // 执行编辑器操作
        if (chunk.action) {
          executeEditorAction(chunk.action);
        }
      } else if (chunk.type === 'message' as const) {
        // Append regular assistant message
        const normalMsg = {
          id: uuidv4(),
          content: chunk.content,
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: false
        };
        addMessage(normalMsg);
        scrollToBottom();
      } else if (chunk.type === 'error' as const) {
        // 处理错误消息重置当前思考消息引用
        currentThinkingMessageIndex = null;
        
        // 错误消息作为新消息添加
        const errorMessage = {
          id: uuidv4(),
          content: $t('chat.error', { message: chunk.content }),
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: false
        };
        
        addMessage(errorMessage);
        scrollToBottom();
      }
    };
    
    // 如果有文件附件，先上传文件
    let filePaths: string[] = [];
    
    if (selectedFiles.length > 0) {
      try {
        // 添加上传中的消息
        const uploadingMessage = {
          id: uuidv4(),
          content: $t('chat.uploadingFiles', { count: selectedFiles.length }),
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: true
        };
        
        addMessage(uploadingMessage);
        scrollToBottom();
        
        // 使用新的uploadFiles函数一次性上传所有文件
        const uploadResponses = await uploadFiles(selectedFiles);
        filePaths = uploadResponses.map(response => response.file_path);
        
        // 更新上传消息
        const updatedMessages = [...messages];
        const uploadMsgIndex = updatedMessages.findIndex(msg => msg.id === uploadingMessage.id);
        if (uploadMsgIndex !== -1) {
          updatedMessages[uploadMsgIndex].content = $t('chat.uploadSuccess', { count: selectedFiles.length });  
          messages = updatedMessages;
          if (chatSessionManager) {
            chatSessionManager.addMessage(uploadingMessage); // 添加新消息到历史记录
            chatSessionManager.setMessages(messages);
          }
        }
        
      } catch (error) {
        // 添加错误消息
        const errorMessage = {
          id: uuidv4(),
          content: $t('chat.uploadError', { error: error instanceof Error ? error.message : $t('chat.unknownError') }),
          sender: 'assistant' as const,
          timestamp: new Date().toISOString(),
          thinking: false
        };
        
        addMessage(errorMessage);
        scrollToBottom();
        return; // 终止处理
      }
    }
    
    // 获取选中文本的节点信息 and 确定选择位置信息
    const localSelectedText = selectedTextInfo?.text;
    const localSelectionStart = selectedTextInfo?.from;
    const localSelectionEnd = selectedTextInfo?.to;
    const localSelectedNodesInfo = selectedTextInfo?.selectedNodesInfo;
    
    // 获取文档字数和字符数
    const documentWordCount = getDocumentWordCount();
    const documentCharCount = getDocumentCharCount();
    
    console.log(`文档单词数: ${documentWordCount}, 字符数: ${documentCharCount}`);
    
    // Note: selectionStart and selectionEnd are now localSelectedStart, localSelectedEnd
    
    // 获取当前会话的聊天历史记录
    let chatHistory = [];
    if (chatSessionManager) {
      // 获取当前会话的所有消息
      const sessionMessages = chatSessionManager.getMessages();
      console.log('sendMessage: raw session messages:', sessionMessages);
      
      // 将消息格式化为API需要的格式
      chatHistory = sessionMessages.map(msg => ({
        sender: msg.sender,
        content: msg.content
      }));
      console.log('sendMessage: formatted chat history for API:', chatHistory);
    } else {
      console.log('sendMessage: chatSessionManager is null, chat history will be empty');
    }
    
    console.log('发送聊天历史记录:', chatHistory);
    
    // Add language information to chat history for the API
    const chatHistoryWithLanguage = chatHistory ? [...chatHistory, {
      sender: 'system',
      content: `Please respond in ${getLanguageName(currentLanguage)}.`
    }] : [{
      sender: 'system',
      content: currentSystemPrompt
    }];
    
    // 统一使用 streamChat API 处理所有请求
    await streamChat(
      cleanMessage, // 使用清理后的消息内容
      editorContent,
      // 传递选中文本信息到API
      localSelectedText, // Use consistently sourced data
      filePaths.length > 0 ? JSON.stringify(filePaths) : undefined,
      localSelectedNodesInfo, // Use consistently sourced data
      localSelectionStart, // Use consistently sourced data
      localSelectionEnd, // Use consistently sourced data
      documentWordCount,
      documentCharCount,
      handleStreamResponse,
      chatHistoryWithLanguage, // 传递包含语言指令的聊天历史记录
      currentSystemPrompt, // 传递当前系统提示，包含语言指令
      $selectedModelId, // 传递用户选择的模型ID
      $apiKey // 传递用户的API密钥（如果有）
    );
    
    // 消息发送完成后清空文件状态
    selectedFiles = [];
    filePreviews = new Map();
  }
  
  // 处理文件上传相关事件
  function handleClearFile() {
    selectedFiles = [];
    filePreviews = new Map();
  }
  
  // 平滑滚动到底部
  function scrollToBottom() {
    if (chatContainer) {
      // 使用 requestAnimationFrame 确保 DOM 已更新
      requestAnimationFrame(() => {
        chatContainer.scrollTo({
          top: chatContainer.scrollHeight,
          behavior: 'smooth'
        });
      });
    }
  }
  
  // 当消息变化时自动滚动到底部
  $: if (messages.length > 0) {
    scrollToBottom();
  }
  
  // Initialize chat session manager when editor is available
  $: if (editor && !chatSessionManager) {
    logger.debug('Initializing ChatSessionManager with editor:', editor);
    chatSessionManager = new ChatSessionManager(editor);
    logger.debug('ChatSessionManager initialized:', chatSessionManager);
    loadChatHistory();
  }
  
  // Load chat history from the editor document
  function loadChatHistory() {
    if (!chatSessionManager) {
      logger.debug('loadChatHistory: chatSessionManager is null');
      return;
    }
    
    // Get messages from active session
    const sessionMessages = chatSessionManager.getMessages();
    logger.debug('loadChatHistory: retrieved messages from session:', sessionMessages);
    
    if (sessionMessages.length > 0) {
      messages = sessionMessages;
      logger.debug('loadChatHistory: using existing session messages');
    } else {
      // Initialize with a welcome message if no history exists
      const welcomeMessage: ChatHistoryMessage = {
        id: 'welcome',
        content: '',
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      
      messages = [welcomeMessage];
      logger.debug('loadChatHistory: initialized with welcome message');
      
      // Save initial message to document
      chatSessionManager.addMessage(welcomeMessage);
      logger.debug('loadChatHistory: added welcome message to session');
    }
  }
  
  // Cleanup when component is destroyed
  onDestroy(() => {
    chatSessionManager = null;
  });
</script>

<div class="chat-panel" class:collapsed={$chatPanelCollapsed}>
  {#if $chatPanelCollapsed}
    <!-- Show minimal content when collapsed -->
    <div class="collapsed-content">
      <span class="vertical-text">{$t('chat.title')}</span>
    </div>
  {:else}
    <!-- Full chat panel content -->
    <div class="chat-header">
      <div class="settings-button-container">
        <SettingsButton />
      </div>
      {#if !isElectron}
        <h2>{$t('app.title')}</h2>
      {/if}
    </div>
    
    <div class="chat-messages" bind:this={chatContainer}>
      {#each messages as message (message.id)}
        <ChatMessage {message} />
      {/each}
    </div>
    
    <ChatInput 
      bind:newMessage 
      bind:selectedFiles 
      bind:filePreviews 
      on:send={sendMessage} 
      on:clearFile={handleClearFile}
    />
  {/if}
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #f9fafb;
    border-left: 1px solid #e9ecef;
    width: 100%;
    transition: width 0.3s ease;
  }
  
  .chat-panel.collapsed {
    width: 40px;
    overflow: hidden;
  }
  
  .collapsed-content {
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  .vertical-text {
    writing-mode: vertical-rl;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 1px;
    color: #6c757d;
  }
  
  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background-color: #f8f9fa;
    height: 48px;
    box-sizing: border-box;
  }
  
  .chat-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  }
  
  .settings-button-container {
    display: flex;
    align-items: center;
  }
  
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    scroll-behavior: smooth;
  }
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    scroll-behavior: smooth;
  }
</style>
