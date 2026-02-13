<script lang="ts">
  import { onMount } from 'svelte';
  
  let feedbackElement: HTMLElement;
  let feedbackTimeout: ReturnType<typeof setTimeout> | null = null;
  
  // 显示反馈信息
  export function showFeedback(message: string, color: string = '#07C160'): void {
    if (!feedbackElement) return;
    
    // 清除之前的超时
    if (feedbackTimeout) {
      clearTimeout(feedbackTimeout);
    }
    
    // 设置反馈消息和颜色
    feedbackElement.textContent = message;
    feedbackElement.style.backgroundColor = color;
    feedbackElement.style.opacity = '1';
    
    // 设置新的超时，3秒后隐藏反馈
    feedbackTimeout = setTimeout(() => {
      if (feedbackElement) {
        feedbackElement.style.opacity = '0';
      }
    }, 3000);
  }
  
  // 组件挂载后设置全局函数
  onMount(() => {
    // 将反馈函数暴露给全局，以便其他组件可以使用
    window.editorFeedback = {
      show: showFeedback
    };
    
    return () => {
      // 清理
      if (feedbackTimeout) {
        clearTimeout(feedbackTimeout);
      }
      
      // 移除全局引用
      if (window.editorFeedback) {
        delete window.editorFeedback;
      }
    };
  });
</script>

<div class="editor-feedback" bind:this={feedbackElement}></div>

<style>
  .editor-feedback {
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 10px 15px;
    background-color: #07C160;
    color: white;
    border-radius: 5px;
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 1000;
    pointer-events: none;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    /* 添加微信风格的磨砂玻璃效果 */
    backdrop-filter: blur(5px);
  }
</style>
