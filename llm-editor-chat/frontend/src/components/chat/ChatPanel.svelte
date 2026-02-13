<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { streamChat, streamModifyText, uploadFile, type StreamResponse } from '$lib/api';
  import ChatMessage from './ChatMessage.svelte';
  import ChatInput from './ChatInput.svelte';
  import './ChatPanel.css';
  
  // 接收从父组件传递的getEditorContent函数
  export let getEditorContent: () => string = () => '';
  
  // 存储选中文本的信息
  let selectedTextInfo: {
    text: string;
    from?: number;
    to?: number;
  } | null = null;

  // 处理从编辑器选择的文本
  export function setMessageFromSelection(selectedText: string, from?: number, to?: number) {
    if (selectedText && selectedText.trim()) {
      // 存储选中文本的完整信息，用于后续替换
      selectedTextInfo = {
        text: selectedText,
        from,
        to
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
  let messages: Array<{
    id: string;
    content: string;
    sender: 'user' | 'assistant';
    timestamp: Date;
    attachment?: {
      type: string;
      name: string;
      url: string;
    };
    thinking?: boolean;
  }> = [];
  
  // UI state
  let chatContainer: HTMLElement;
  let newMessage = '';
  let selectedFile: File | null = null;
  let filePreview: string | null = null;
  
  // 执行编辑器操作
  function executeEditorAction(action: any) {
    
    if (action.type === 'insert') {
      if (selectedTextInfo && selectedTextInfo.from !== undefined && selectedTextInfo.to !== undefined) {
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
          partial: action.payload.partial // 传递partial标志，表示是否为部分内容
        });
      }
    } else if (action.type === 'append') {
      // 处理append类型的操作，用于按Section追加内容
      dispatch('message', {
        action: 'append-text',
        content: action.payload.content,
        partial: action.payload.partial // 传递partial标志，表示是否为部分内容
      });
    } else if (action.type === 'replace') {
      // 处理replace类型的操作
      dispatch('message', {
        action: 'replace-text',
        content: action.payload.content,
        from: action.payload.start,
        to: action.payload.end,
        partial: action.payload.partial // 传递partial标志，表示是否为部分内容
      });
    } else {
      // 未知的操作类型
      console.warn('Unknown action type:', action.type);
    }
  }
  
  // Send message function
  async function sendMessage() {
    if (!newMessage.trim() && !selectedFile) return;
    
    // Add user message
    const userMessage: {
      id: string;
      content: string;
      sender: 'user' | 'assistant';
      timestamp: Date;
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
      id: `user-${Date.now()}`,
      content: newMessage.trim(),
      sender: 'user',
      timestamp: new Date()
    };
    
    // 如果有文件附件
    if (selectedFile) {
      userMessage.attachment = {
        type: selectedFile.type,
        name: selectedFile.name,
        url: filePreview || ''
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
    
    messages = [...messages, userMessage];
    scrollToBottom();
    
    // 不再创建初始占位消息，每个思考内容都会作为新消息添加
    
    // 获取编辑器内容
    const editorContent = getEditorContent();
    
    // 注意：在这里不清空状态，因为我们还需要使用selectedFile进行文件上传
    
    // 用于跟踪当前思考消息的索引
    let currentThinkingMessageIndex: number | null = null;

    // 检查是否是修改模式（消息中包含{{...}}格式）
    const modificationPattern = /{{([^}]+)\[(\d+)-(\d+)\]}}/;
    const isModificationMode = modificationPattern.test(userMessage.content);
    
    // 从消息中解析出位置信息
    let parsedStartPosition: number | undefined;
    let parsedEndPosition: number | undefined;
    
    if (isModificationMode) {
      const match = modificationPattern.exec(userMessage.content);
      if (match && match.length >= 4) {
        parsedStartPosition = parseInt(match[2], 10);
        parsedEndPosition = parseInt(match[3], 10);
        console.log('Parsed position from message:', parsedStartPosition, parsedEndPosition);
      }
    }
    
    // 处理流式响应的回调函数
    const handleStreamResponse = (chunk: StreamResponse) => {
      // 处理流式响应
      if (chunk.type === 'thinking') {
        if (currentThinkingMessageIndex === null) {
          // 首次收到思考内容，创建新消息
          const thinkingMessage = {
            id: `assistant-thinking-${Date.now()}`,
            content: chunk.content,
            sender: 'assistant' as const,
            timestamp: new Date(),
            thinking: true
          };
          
          messages = [...messages, thinkingMessage];
          currentThinkingMessageIndex = messages.length - 1;
        } else {
          // 已有思考消息，更新其内容
          const updatedMessages = [...messages];
          updatedMessages[currentThinkingMessageIndex].content += '\n' + chunk.content;
          messages = updatedMessages;
        }
        scrollToBottom();
      } else if (chunk.type === 'action') {
        // 重置当前思考消息引用
        currentThinkingMessageIndex = null;
        
        // 最终结果作为新消息添加
        const finalMessage = {
          id: `assistant-final-${Date.now()}`,
          content: chunk.content,
          sender: 'assistant' as const,
          timestamp: new Date(),
          thinking: false
        };
        
        messages = [...messages, finalMessage];
        scrollToBottom();
        
        // 执行编辑器操作
        if (chunk.action) {
          executeEditorAction(chunk.action);
        }
      } else if (chunk.type === 'error') {
        // 重置当前思考消息引用
        currentThinkingMessageIndex = null;
        
        // 错误消息作为新消息添加
        const errorMessage = {
          id: `assistant-error-${Date.now()}`,
          content: `错误: ${chunk.content}`,
          sender: 'assistant' as const,
          timestamp: new Date(),
          thinking: false
        };
        
        messages = [...messages, errorMessage];
        scrollToBottom();
      }
    };
    
    // 如果是修改模式，则使用streamModifyText函数
    if (isModificationMode && userMessage.selectedText) {
      // 使用从消息中解析出的位置信息（如果有），否则使用selectedTextInfo中的位置
      const startPosition = parsedStartPosition !== undefined ? parsedStartPosition : userMessage.selectedText.from;
      const endPosition = parsedEndPosition !== undefined ? parsedEndPosition : userMessage.selectedText.to;
      
      console.log('Using position for modification:', startPosition, endPosition);
      
      // 调用流式修改API
      await streamModifyText(
        // 移除消息中的{{...}}格式，只保留实际的指令
        userMessage.content.replace(modificationPattern, '').trim(),
        userMessage.selectedText.text,
        startPosition,
        endPosition,
        editorContent,
        handleStreamResponse
      );
    } else {
      // 非修改模式，使用常规的streamChat函数
      // 如果有文件附件，先上传文件
      let filePath: string | undefined = undefined;
      
      if (selectedFile) {
        try {
          // 添加上传中的消息
          const uploadingMessage = {
            id: `assistant-uploading-${Date.now()}`,
            content: `正在上传文件: ${selectedFile.name}...`,
            sender: 'assistant' as const,
            timestamp: new Date(),
            thinking: true
          };
          
          messages = [...messages, uploadingMessage];
          scrollToBottom();
          
          // 上传文件
          const uploadResponse = await uploadFile(selectedFile);
          filePath = uploadResponse.file_path;
          
          // 更新上传消息
          const updatedMessages = [...messages];
          const uploadMsgIndex = updatedMessages.findIndex(msg => msg.id === uploadingMessage.id);
          if (uploadMsgIndex !== -1 && selectedFile) {
            updatedMessages[uploadMsgIndex].content = `文件上传成功: ${selectedFile.name}`;  
            messages = updatedMessages;
          }
          
        } catch (error) {
          // 添加错误消息
          const errorMessage = {
            id: `assistant-error-${Date.now()}`,
            content: `文件上传失败: ${error instanceof Error ? error.message : '未知错误'}`,
            sender: 'assistant' as const,
            timestamp: new Date(),
            thinking: false
          };
          
          messages = [...messages, errorMessage];
          scrollToBottom();
          return; // 终止处理
        }
      }
      
      await streamChat(
        userMessage.content,
        editorContent,
        // 传递选中文本信息到API
        userMessage.selectedText?.text,
        filePath,
        handleStreamResponse
      );
      
      // 消息发送完成后再清空状态
      newMessage = '';
      selectedFile = null;
      filePreview = null;
    }

  }
  
  // 处理文件上传相关事件
  function handleClearFile() {
    selectedFile = null;
    filePreview = null;
  }
  
  // Scroll chat to bottom
  function scrollToBottom() {
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }
  
  // Initialize with a welcome message
  onMount(() => {
    messages = [
      {
        id: 'welcome',
        content: '',
        sender: 'assistant',
        timestamp: new Date()
      }
    ];
  });
</script>

<div class="chat-panel">
  <div class="chat-header">
    <h2>Chat Assistant</h2>
  </div>
  
  <div class="chat-messages" bind:this={chatContainer}>
    {#each messages as message (message.id)}
      <ChatMessage {message} />
    {/each}
  </div>
  
  <ChatInput 
    bind:newMessage
    bind:selectedFile
    bind:filePreview
    on:send={sendMessage}
    on:clearFile={handleClearFile}
  />
</div>

<style>
  /* 移除未使用的样式 */
</style>
