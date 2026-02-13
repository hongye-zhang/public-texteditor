<script lang="ts">
  export let message: {
    id: string;
    content: string;
    sender: 'user' | 'assistant';
    attachment?: {
      type: string;
      name: string;
      url: string;
    };
    thinking?: boolean;
  };
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import hljs from 'highlight.js';
  import 'highlight.js/styles/github.css';
  import { copyToClipboard } from '../utils/clipboard';
  import { t } from '../../../lib/i18n/index';
  
  // 在组件初始化时配置代码高亮
  onMount(() => {
    // 使用marked的默认渲染器
    const renderer = new marked.Renderer();
    
    // 使用marked的API配置markdown渲染
    marked.use({
      renderer,
      // 添加代码高亮支持
      walkTokens(token: any) {
        if (token.type === 'code') {
          const lang = token.lang || 'plaintext';
          if (hljs.getLanguage(lang)) {
            try {
              token.text = hljs.highlight(token.text, { language: lang }).value;
            } catch (e) {
              console.error('Error highlighting code:', e);
            }
          }
        }
      },
      gfm: true,
      breaks: true
    });
  });

  // 检查是否是初始的thinking消息
  const isInitialThinking = message.thinking && message.content.trim() === 'Figuring out what you want...';

  function handleCopyCode(codeBlock: string) {
    copyToClipboard(codeBlock);
  }
</script>

<div class="message-container {message.sender === 'user' ? 'user-message' : 'assistant-message'}">
  <div class="message {message.thinking ? 'thinking' : ''}">
    {#if message.thinking}
      {#if isInitialThinking}
        <!-- 初始的thinking消息只显示忙光标，不显示文本 -->
        <div class="loading-spinner-container">
          <div class="loading-spinner"></div>
        </div>
      {:else}
        <!-- 其他thinking消息正常显示文本 -->
        <div class="message-content">{@html marked.parse(message.content)}</div>
      {/if}
    {:else}
      <div class="message-content">{@html marked.parse(message.content)}</div>
    {/if}
    {#if message.attachment}
      {#if message.attachment.type.startsWith('image/')}
        <div class="message-attachment">
          <img src={message.attachment.url} alt={$t('editor.attachment_image')} />
        </div>
      {:else}
        <div class="message-attachment file-item">
          <i class="fas fa-file"></i>
          <span class="file-name">{message.attachment.name}</span>
          <button class="copy-button" on:click={() => handleCopyCode(message.attachment?.url || '')} title={$t('editor.copy')} aria-label={$t('editor.copy')}>
            <i class="fas fa-copy"></i>
          </button>
        </div>
      {/if}
    {/if}
    <!-- 已移除时间戳显示 -->
  </div>
</div>

<style>
  .loading-spinner-container {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    min-height: 24px;
    gap: 10px;
  }
  

  
  .loading-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-radius: 50%;
    border-top-color: #333;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
