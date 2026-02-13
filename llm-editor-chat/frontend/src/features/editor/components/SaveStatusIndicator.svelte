<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  // Props from parent component
  export let editorComponent: any = null;

  // 保存状态变量
  let saveState = 'idle';
  let lastSavedTime: number | null = null;
  let errorMessage = '';
  let hasUnsavedChanges = false;
  let isSaving = false;
  
  // 定时器用于更新状态
  let statusUpdateInterval: ReturnType<typeof setInterval>;

  // 更新状态的函数
  function updateStatus() {
    if (editorComponent && editorComponent.getAutoSaveStatus) {
      const status = editorComponent.getAutoSaveStatus();
      hasUnsavedChanges = status.hasUnsavedChanges;
      isSaving = status.isSaving;
      
      if (isSaving) {
        saveState = 'saving';
      } else if (hasUnsavedChanges) {
        saveState = 'unsaved';
      } else {
        saveState = 'saved';
        lastSavedTime = Date.now();
      }
    }
  }

  // 格式化最后保存时间
  function formatLastSaved(timestamp: number): string {
    if (!timestamp) return '';
    
    const now = Date.now();
    const diff = now - timestamp;
    
    if (diff < 1000) return '刚刚保存';
    if (diff < 60000) return `${Math.floor(diff / 1000)}秒前保存`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前保存`;
    
    const date = new Date(timestamp);
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')} 保存`;
  }

  // 获取状态显示文本
  function getStatusText(state: string): string {
    switch (state) {
      case 'saved':
        return '已保存';
      case 'unsaved':
        return '有未保存更改';
      case 'saving':
        return '保存中...';
      case 'error':
        return '保存失败';
      default:
        return '';
    }
  }

  // 获取状态图标
  function getStatusIcon(state: string): string {
    switch (state) {
      case 'saved':
        return '✓';
      case 'unsaved':
        return '●';
      case 'saving':
        return '💾';
      case 'error':
        return '❌';
      default:
        return '';
    }
  }

  // 获取状态颜色
  function getStatusColor(state: string): string {
    switch (state) {
      case 'saved':
        return '#27ae60';
      case 'unsaved':
        return '#f39c12';
      case 'saving':
        return '#3498db';
      case 'error':
        return '#e74c3c';
      default:
        return '#95a5a6';
    }
  }

  // 手动保存
  function handleManualSave() {
    if (editorComponent && editorComponent.triggerManualSave) {
      editorComponent.triggerManualSave();
    }
  }

  onMount(() => {
    // 启动状态更新定时器
    statusUpdateInterval = setInterval(updateStatus, 1000);
    updateStatus(); // 立即更新一次
  });

  onDestroy(() => {
    // 清理定时器
    if (statusUpdateInterval) {
      clearInterval(statusUpdateInterval);
    }
  });

  // 实时更新时间显示
  let timeUpdateInterval: ReturnType<typeof setInterval>;
  
  onMount(() => {
    // 每秒更新时间显示
    timeUpdateInterval = setInterval(() => {
      // 触发响应式更新 - 使用get函数获取值
      const currentLastSaved = autoSaveManager.lastSaved;
      // 强制触发响应式更新
    }, 1000);
  });

  onDestroy(() => {
    if (timeUpdateInterval) {
      clearInterval(timeUpdateInterval);
    }
  });
</script>

<div class="save-status-container">
  <div class="save-status-indicator">
    <span class="status-icon" style="color: {getStatusColor(saveState)}">
      {getStatusIcon(saveState)}
    </span>
    <span class="status-text">
      {getStatusText(saveState)}
    </span>
  </div>
  
  {#if lastSavedTime}
    <div class="last-saved-time">
      {formatLastSaved(lastSavedTime)}
    </div>
  {/if}
  
  {#if errorMessage}
    <div class="error-message" title={errorMessage}>
      错误: {errorMessage}
    </div>
  {/if}
  
  <button 
    class="manual-save-btn" 
    on:click={handleManualSave}
    disabled={isSaving}
    title="手动保存 (Ctrl+S)"
  >
    💾 保存
  </button>
</div>

<style>
  .save-status-container {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #666;
    user-select: none;
  }

  .save-status {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    border-radius: 4px;
    transition: all 0.2s ease;
  }

  .status-icon {
    font-size: 10px;
    line-height: 1;
  }

  .status-text {
    font-size: 11px;
    font-weight: 500;
  }

  /* 状态样式 */
  .status-saved {
    color: #22c55e;
    background-color: rgba(34, 197, 94, 0.1);
  }

  .status-unsaved {
    color: #f59e0b;
    background-color: rgba(245, 158, 11, 0.1);
  }

  .status-pending {
    color: #3b82f6;
    background-color: rgba(59, 130, 246, 0.1);
  }

  .status-saving {
    color: #3b82f6;
    background-color: rgba(59, 130, 246, 0.1);
    animation: pulse 1.5s ease-in-out infinite;
  }

  .status-success {
    color: #22c55e;
    background-color: rgba(34, 197, 94, 0.1);
  }

  .status-error {
    color: #ef4444;
    background-color: rgba(239, 68, 68, 0.1);
  }

  .status-retrying {
    color: #f59e0b;
    background-color: rgba(245, 158, 11, 0.1);
    animation: spin 1s linear infinite;
  }

  .last-saved-time {
    color: #9ca3af;
    font-size: 11px;
  }

  .time-button {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 3px;
    transition: background-color 0.2s ease;
  }

  .time-button:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .error-message {
    color: #ef4444;
    font-size: 11px;
  }

  .retry-button {
    background: #ef4444;
    color: white;
    border: none;
    padding: 2px 6px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 10px;
    transition: background-color 0.2s ease;
  }

  .retry-button:hover {
    background: #dc2626;
  }

  /* 动画 */
  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .save-status-container {
      font-size: 11px;
    }
    
    .status-text {
      display: none;
    }
    
    .last-saved-time {
      font-size: 10px;
    }
  }
</style>
