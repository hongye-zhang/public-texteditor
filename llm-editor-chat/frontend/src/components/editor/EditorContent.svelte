<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  
  // 状态
  let element: HTMLElement;
  
  // 事件分发器
  const dispatch = createEventDispatcher<{
    elementReady: { element: HTMLElement };
  }>();
  
  // 当元素就绪时通知父组件
  onMount(() => {
    if (element) {
      dispatch('elementReady', { element });
    }
  });
</script>

<div class="editor-content-wrapper">
  <div class="editor-content" bind:this={element}></div>
</div>

<style>
  .editor-content-wrapper {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    height: calc(100% - 52px); /* 减去工具栏的高度 */
  }
  
  .editor-content {
    flex-grow: 1;
    overflow-y: auto;
    padding: 0.5rem 1rem;
    background-color: white;
    border-radius: 0.25rem;
    height: 100%;
  }
  
  /* 添加微信风格的滚动条样式 */
  .editor-content::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  
  .editor-content::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
  }
  
  .editor-content::-webkit-scrollbar-track {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
  }
</style>
