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
</script>

<div class="message-container {message.sender === 'user' ? 'user-message' : 'assistant-message'}">
  <div class="message {message.thinking ? 'thinking' : ''}">
    <div class="message-content">{message.content}</div>
    {#if message.attachment}
      {#if message.attachment.type.startsWith('image/')}
        <div class="message-attachment">
          <img src={message.attachment.url} alt="附件图片" />
        </div>
      {:else}
        <div class="message-attachment file-item">
          <i class="fas fa-file"></i>
          <span class="file-name">{message.attachment.name}</span>
        </div>
      {/if}
    {/if}
    <!-- 已移除时间戳显示 -->
  </div>
</div>
