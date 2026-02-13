<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { ENV_CONFIG } from '../../config/env';
  
  // 状态变量
  let isElectron = ENV_CONFIG.runMode === 'electron';
  let backendStatus = '检查中...';
  let apiBaseUrl = ENV_CONFIG.apiBaseUrl;
  let activeSection = '';
  
  // API 密钥状态
  let openaiKeyExists = false;
  let openaiKeyInput = '';
  let openaiKeyStatus = '';
  let isLoading = false;
  
  // 在组件挂载后检查后端状态和 API 密钥
  onMount(async () => {
    if (browser) {
      // 检查是否有来自菜单的导航请求
      if (isElectron && window.electronAPI) {
        window.electronAPI.onNavigateSettings((section) => {
          activeSection = section;
          scrollToSection(section);
        });
      }
      
      // 检查后端状态
      await checkBackendStatus();
      
      // 检查 API 密钥
      await checkApiKey('openai_api_key');
    }
  });
  
  // 滚动到指定部分
  function scrollToSection(section) {
    if (section && browser) {
      const element = document.getElementById(section);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }
  
  // 检查后端状态
  async function checkBackendStatus() {
    if (!isElectron) {
      // Web 模式下，直接使用 fetch 检查后端状态
      try {
        const response = await fetch(`${apiBaseUrl}/health`);
        if (response.ok) {
          const data = await response.json();
          backendStatus = `连接正常 (${data.mode} 模式)`;
        } else {
          backendStatus = '连接失败';
        }
      } catch (error) {
        backendStatus = `连接错误: ${error.message}`;
      }
    } else if (window.electronAPI) {
      // Electron 模式下，使用 IPC 检查后端状态
      try {
        const status = await window.electronAPI.checkBackendStatus();
        backendStatus = status.running ? `连接正常 (${status.mode} 模式)` : '未运行';
        apiBaseUrl = await window.electronAPI.getApiBaseUrl();
      } catch (error) {
        backendStatus = `检查失败: ${error.message}`;
      }
    }
  }
  
  // 检查 API 密钥是否存在
  async function checkApiKey(keyName) {
    isLoading = true;
    
    try {
      if (isElectron && window.electronAPI) {
        // Electron 模式下，使用系统密钥链
        const keyExists = await window.electronAPI.getApiKey(keyName);
        if (keyName === 'openai_api_key') {
          openaiKeyExists = !!keyExists;
        }
      } else {
        // Web 模式下，使用 localStorage
        const keyExists = localStorage.getItem(keyName);
        if (keyName === 'openai_api_key') {
          openaiKeyExists = !!keyExists;
        }
      }
    } catch (error) {
      console.error(`检查 API 密钥失败: ${error.message}`);
    } finally {
      isLoading = false;
    }
  }
  
  // 保存 API 密钥
  async function saveApiKey(keyName, value) {
    isLoading = true;
    openaiKeyStatus = '保存中...';
    
    try {
      if (isElectron && window.electronAPI) {
        // Electron 模式下，使用系统密钥链
        await window.electronAPI.saveApiKey(keyName, value);
      } else {
        // Web 模式下，使用 localStorage
        localStorage.setItem(keyName, value);
      }
      
      if (keyName === 'openai_api_key') {
        openaiKeyExists = true;
        openaiKeyInput = '';
        openaiKeyStatus = '保存成功';
      }
    } catch (error) {
      openaiKeyStatus = `保存失败: ${error.message}`;
    } finally {
      isLoading = false;
      setTimeout(() => {
        openaiKeyStatus = '';
      }, 3000);
    }
  }
  
  // 删除 API 密钥
  async function deleteApiKey(keyName) {
    isLoading = true;
    openaiKeyStatus = '删除中...';
    
    try {
      if (isElectron && window.electronAPI) {
        // Electron 模式下，使用系统密钥链
        await window.electronAPI.deleteApiKey(keyName);
      } else {
        // Web 模式下，使用 localStorage
        localStorage.removeItem(keyName);
      }
      
      if (keyName === 'openai_api_key') {
        openaiKeyExists = false;
        openaiKeyStatus = '已删除';
      }
    } catch (error) {
      openaiKeyStatus = `删除失败: ${error.message}`;
    } finally {
      isLoading = false;
      setTimeout(() => {
        openaiKeyStatus = '';
      }, 3000);
    }
  }
  
  // 处理 OpenAI API 密钥表单提交
  function handleOpenAIKeySubmit() {
    if (openaiKeyInput.trim()) {
      saveApiKey('openai_api_key', openaiKeyInput.trim());
    }
  }
</script>

<svelte:head>
  <title>设置 - LLM 文本编辑器</title>
</svelte:head>

<div class="settings-page">
  <div class="settings-container">
    <div class="settings-header">
      <h1>设置</h1>
      <p class="settings-mode-info">
        当前运行模式: <strong>{isElectron ? 'Electron 桌面应用' : 'Web 浏览器'}</strong>
      </p>
    </div>
    
    <div class="settings-section" id="api-keys">
      <h2>API 密钥</h2>
      <div class="settings-section-content">
        <!-- OpenAI API 密钥管理 -->
        <div class="api-key-manager">
          <div class="api-key-header">
            <h3>OpenAI API 密钥</h3>
            <div class="api-key-storage-info">
              {#if isElectron}
                <span class="storage-badge secure">安全存储在系统密钥链</span>
              {:else}
                <span class="storage-badge warning">存储在浏览器 localStorage（不安全）</span>
              {/if}
            </div>
          </div>
          
          <p class="api-key-description">用于 LLM 请求的 OpenAI API 密钥</p>
          
          {#if openaiKeyExists}
            <div class="api-key-status">
              <span class="key-exists">API 密钥已设置</span>
              <button 
                class="delete-key-button" 
                on:click={() => deleteApiKey('openai_api_key')}
                disabled={isLoading}
              >
                删除密钥
              </button>
            </div>
          {:else}
            <div class="api-key-input-container">
              <input 
                type="password"
                placeholder="输入 OpenAI API 密钥" 
                bind:value={openaiKeyInput}
                disabled={isLoading}
              />
              <button 
                class="save-key-button" 
                on:click={handleOpenAIKeySubmit}
                disabled={!openaiKeyInput.trim() || isLoading}
              >
                保存
              </button>
            </div>
          {/if}
          
          {#if openaiKeyStatus}
            <p class="api-key-message">{openaiKeyStatus}</p>
          {/if}
        </div>
      </div>
    </div>
    
    <div class="settings-section" id="backend-status">
      <h2>后端状态</h2>
      <div class="settings-section-content">
        <div class="backend-status-container">
          <div class="status-item">
            <span class="status-label">连接状态:</span>
            <span class="status-value">{backendStatus}</span>
          </div>
          
          <div class="status-item">
            <span class="status-label">API 基础 URL:</span>
            <span class="status-value">{apiBaseUrl}</span>
          </div>
          
          <div class="status-item">
            <span class="status-label">运行模式:</span>
            <span class="status-value">{isElectron ? 'Electron' : 'Web'}</span>
          </div>
          
          {#if isElectron}
            <div class="backend-actions">
              <button 
                class="restart-backend-button" 
                on:click={() => {
                  if (window.electronAPI) {
                    window.electronAPI.onRestartBackend();
                    backendStatus = '重启中...';
                    setTimeout(checkBackendStatus, 2000);
                  }
                }}
              >
                重启后端
              </button>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .settings-page {
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
  }
  
  .settings-container {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 24px;
  }
  
  .settings-header {
    margin-bottom: 24px;
    border-bottom: 1px solid #eee;
    padding-bottom: 16px;
  }
  
  .settings-header h1 {
    font-size: 24px;
    margin: 0 0 8px 0;
  }
  
  .settings-mode-info {
    color: #666;
    margin: 0;
  }
  
  .settings-section {
    margin-bottom: 32px;
  }
  
  .settings-section h2 {
    font-size: 20px;
    margin: 0 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #eee;
  }
  
  .settings-section-content {
    padding: 0 8px;
  }
  
  /* API 密钥管理样式 */
  .api-key-manager {
    margin-bottom: 24px;
    padding: 16px;
    border: 1px solid #eee;
    border-radius: 4px;
  }
  
  .api-key-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  
  .api-key-header h3 {
    margin: 0;
    font-size: 16px;
  }
  
  .storage-badge {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
  }
  
  .storage-badge.secure {
    background-color: #e6f7e6;
    color: #2e7d32;
  }
  
  .storage-badge.warning {
    background-color: #fff8e1;
    color: #ff8f00;
  }
  
  .api-key-description {
    color: #666;
    margin: 0 0 16px 0;
    font-size: 14px;
  }
  
  .api-key-status {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .key-exists {
    color: #2e7d32;
    font-weight: 500;
  }
  
  .api-key-input-container {
    display: flex;
    gap: 8px;
  }
  
  .api-key-input-container input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
  }
  
  button {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
  }
  
  .save-key-button {
    background-color: #1976d2;
    color: white;
  }
  
  .save-key-button:hover {
    background-color: #1565c0;
  }
  
  .save-key-button:disabled {
    background-color: #bbdefb;
    cursor: not-allowed;
  }
  
  .delete-key-button {
    background-color: #f44336;
    color: white;
  }
  
  .delete-key-button:hover {
    background-color: #d32f2f;
  }
  
  .delete-key-button:disabled {
    background-color: #ffcdd2;
    cursor: not-allowed;
  }
  
  .api-key-message {
    margin: 8px 0 0 0;
    font-size: 14px;
    color: #666;
  }
  
  /* 后端状态样式 */
  .backend-status-container {
    padding: 16px;
    border: 1px solid #eee;
    border-radius: 4px;
  }
  
  .status-item {
    display: flex;
    margin-bottom: 12px;
  }
  
  .status-label {
    width: 120px;
    font-weight: 500;
    color: #666;
  }
  
  .status-value {
    flex: 1;
  }
  
  .backend-actions {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #eee;
  }
  
  .restart-backend-button {
    background-color: #ff9800;
    color: white;
  }
  
  .restart-backend-button:hover {
    background-color: #f57c00;
  }
</style>
