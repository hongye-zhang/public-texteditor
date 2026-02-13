import React from 'react';
import ApiKeyManager from '../components/settings/ApiKeyManager';
import { ENV_CONFIG } from '../config/env';

/**
 * 设置页面
 * 包含 API 密钥管理和其他设置选项
 */
const Settings: React.FC = () => {
  return (
    <div className="settings-page">
      <div className="settings-container">
        <div className="settings-header">
          <h1>设置</h1>
          <p className="settings-mode-info">
            当前运行模式: <strong>{ENV_CONFIG.runMode === 'electron' ? 'Electron 桌面应用' : 'Web 浏览器'}</strong>
          </p>
        </div>
        
        <div className="settings-section">
          <h2>API 密钥</h2>
          <div className="settings-section-content">
            <ApiKeyManager 
              keyName="openai_api_key" 
              label="OpenAI API 密钥" 
              description="用于 LLM 请求的 OpenAI API 密钥" 
            />
            
            {/* 可以根据需要添加更多 API 密钥管理组件 */}
          </div>
        </div>
        
        <div className="settings-section">
          <h2>后端状态</h2>
          <div className="settings-section-content">
            <BackendStatus />
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .settings-page {
          padding: 24px;
          max-width: 800px;
          margin: 0 auto;
        }
        
        .settings-container {
          background-color: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }
        
        .settings-header {
          padding: 24px;
          background-color: #f8f9fa;
          border-bottom: 1px solid #e9ecef;
        }
        
        .settings-header h1 {
          margin: 0;
          font-size: 24px;
          font-weight: 600;
        }
        
        .settings-mode-info {
          margin: 8px 0 0 0;
          font-size: 14px;
          color: #6c757d;
        }
        
        .settings-section {
          padding: 24px;
          border-bottom: 1px solid #e9ecef;
        }
        
        .settings-section:last-child {
          border-bottom: none;
        }
        
        .settings-section h2 {
          margin: 0 0 16px 0;
          font-size: 20px;
          font-weight: 600;
        }
        
        .settings-section-content {
          margin-top: 16px;
        }
      `}</style>
    </div>
  );
};

/**
 * 后端状态组件
 * 显示后端连接状态和相关信息
 */
const BackendStatus: React.FC = () => {
  const [status, setStatus] = React.useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [apiBaseUrl, setApiBaseUrl] = React.useState<string>('');
  const [mode, setMode] = React.useState<string>('');
  
  React.useEffect(() => {
    const checkBackend = async () => {
      try {
        // 导入 API 客户端
        const { checkBackendStatus, getApiBaseUrl } = await import('../lib/api/apiClient');
        
        // 获取 API 基础 URL
        const baseUrl = await getApiBaseUrl();
        setApiBaseUrl(baseUrl);
        
        // 检查后端状态
        const isConnected = await checkBackendStatus();
        setStatus(isConnected ? 'connected' : 'disconnected');
        
        // 如果连接成功，尝试获取后端模式
        if (isConnected) {
          try {
            const response = await fetch(`${baseUrl}/health`);
            const data = await response.json();
            setMode(data.mode || '未知');
          } catch (err) {
            console.error('Error fetching backend mode:', err);
            setMode('未知');
          }
        }
      } catch (err) {
        console.error('Error checking backend status:', err);
        setStatus('disconnected');
      }
    };
    
    checkBackend();
  }, []);
  
  return (
    <div className="backend-status">
      <div className="backend-status-header">
        <h3>后端连接状态</h3>
      </div>
      
      <div className="backend-status-content">
        <div className="backend-status-item">
          <span className="backend-status-label">状态:</span>
          <span className={`backend-status-badge ${status}`}>
            {status === 'checking' && '检查中...'}
            {status === 'connected' && '已连接'}
            {status === 'disconnected' && '未连接'}
          </span>
        </div>
        
        <div className="backend-status-item">
          <span className="backend-status-label">API 基础 URL:</span>
          <span className="backend-status-value">{apiBaseUrl || '未知'}</span>
        </div>
        
        {status === 'connected' && (
          <div className="backend-status-item">
            <span className="backend-status-label">后端模式:</span>
            <span className="backend-status-value">{mode}</span>
          </div>
        )}
        
        {ENV_CONFIG.isElectron && (
          <div className="backend-status-note">
            <p>在 Electron 模式下，后端作为本地进程运行，由应用自动管理。</p>
          </div>
        )}
      </div>
      
      <style jsx>{`
        .backend-status {
          padding: 16px;
          border-radius: 8px;
          background-color: #f8f9fa;
        }
        
        .backend-status-header {
          margin-bottom: 16px;
        }
        
        .backend-status-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        
        .backend-status-content {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .backend-status-item {
          display: flex;
          align-items: center;
        }
        
        .backend-status-label {
          width: 120px;
          font-weight: 500;
        }
        
        .backend-status-value {
          font-family: monospace;
        }
        
        .backend-status-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 14px;
          font-weight: 500;
        }
        
        .backend-status-badge.checking {
          background-color: #ffc107;
          color: #212529;
        }
        
        .backend-status-badge.connected {
          background-color: #28a745;
          color: white;
        }
        
        .backend-status-badge.disconnected {
          background-color: #dc3545;
          color: white;
        }
        
        .backend-status-note {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #dee2e6;
        }
        
        .backend-status-note p {
          margin: 0;
          font-size: 14px;
          color: #6c757d;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default Settings;
