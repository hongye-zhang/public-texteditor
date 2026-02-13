<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  // 属性
  export let disabled: boolean = false;
  export let width: string = '100%';
  export let height: string = '40px';
  export let primary: boolean = true;
  export let icon: string = '';
  export let ariaLabel: string = '';
  
  // 事件分发器
  const dispatch = createEventDispatcher<{
    click: void;
  }>();
  
  // 点击处理
  function handleClick() {
    if (!disabled) {
      dispatch('click');
    }
  }
</script>

<button 
  class="gaofen-button" 
  class:primary={primary} 
  class:disabled={disabled}
  style="width: {width}; height: {height};"
  on:click={handleClick}
  type="button"
  aria-label={ariaLabel}
  aria-disabled={disabled}
>
  {#if icon}
    <span class="icon">{@html icon}</span>
  {/if}
  <slot>按钮</slot>
</button>

<style>
  .gaofen-button {
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
    padding: 0 15px;
    /* 微信风格的磨砂玻璃效果 */
    backdrop-filter: blur(15px);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
  
  .gaofen-button:active:not(.disabled) {
    transform: scale(0.98);
  }
  
  .primary {
    background-color: #07C160;
    color: white;
  }
  
  .primary:hover:not(.disabled) {
    background-color: #06AE56;
  }
  
  .gaofen-button:not(.primary) {
    background-color: rgba(255, 255, 255, 0.8);
    color: #333;
    border: 1px solid rgba(0, 0, 0, 0.05);
  }
  
  .gaofen-button:not(.primary):hover:not(.disabled) {
    background-color: rgba(255, 255, 255, 0.9);
  }
  
  .disabled {
    background-color: rgba(245, 245, 245, 0.8) !important;
    color: #888888 !important;
    cursor: not-allowed;
    border: 1px solid rgba(0, 0, 0, 0.05) !important;
  }
  
  .icon {
    margin-right: 8px;
    display: flex;
    align-items: center;
  }
</style>
