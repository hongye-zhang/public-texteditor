import React, { useState, useEffect } from 'react';
import { saveApiKey, getApiKey, deleteApiKey } from '../../lib/api/apiClient';
import { ENV_CONFIG } from '../../config/env';

interface ApiKeyManagerProps {
  keyName: string;
  label: string;
  description?: string;
}

/**
 * API 密钥管理组件
 * 用于设置、查看和删除 API 密钥
 */
const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({ keyName, label, description }) => {
  const [apiKey, setApiKey] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [hasKey, setHasKey] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 获取当前 API 密钥
  useEffect(() => {
    const fetchApiKey = async () => {
      try {
        setIsLoading(true);
        const key = await getApiKey(keyName);
        setHasKey(key !== null);
        setApiKey(''); // 出于安全考虑，不显示实际密钥
        setError(null);
      } catch (err) {
        setError('获取 API 密钥时出错');
        console.error('Error fetching API key:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchApiKey();
  }, [keyName]);

  // 保存 API 密钥
  const handleSaveApiKey = async () => {
    if (!apiKey.trim()) {
      setError('API 密钥不能为空');
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      setSuccess(null);
      
      await saveApiKey(keyName, apiKey);
      
      setHasKey(true);
      setApiKey(''); // 清空输入框
      setSuccess('API 密钥已保存');
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('保存 API 密钥时出错');
      console.error('Error saving API key:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // 删除 API 密钥
  const handleDeleteApiKey = async () => {
    try {
      setIsDeleting(true);
      setError(null);
      setSuccess(null);
      
      await deleteApiKey(keyName);
      
      setHasKey(false);
      setApiKey('');
      setSuccess('API 密钥已删除');
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('删除 API 密钥时出错');
      console.error('Error deleting API key:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="api-key-manager">
      <div className="api-key-header">
        <h3>{label}</h3>
        {description && <p className="api-key-description">{description}</p>}
      </div>
      
      {isLoading ? (
        <div className="api-key-loading">加载中...</div>
      ) : (
        <div className="api-key-content">
          {hasKey ? (
            <div className="api-key-status">
              <div className="api-key-info">
                <span className="api-key-badge success">已设置</span>
                <span className="api-key-storage-info">
                  {ENV_CONFIG.isElectron 
                    ? '密钥安全存储在系统密钥链中' 
                    : '密钥存储在浏览器本地存储中（不安全）'}
                </span>
              </div>
              <button 
                className="api-key-delete-btn" 
                onClick={handleDeleteApiKey}
                disabled={isDeleting}
              >
                {isDeleting ? '删除中...' : '删除密钥'}
              </button>
            </div>
          ) : (
            <div className="api-key-form">
              <input
                type="password"
                className="api-key-input"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={`输入 ${label}`}
                disabled={isSaving}
              />
              <button 
                className="api-key-save-btn" 
                onClick={handleSaveApiKey}
                disabled={isSaving || !apiKey.trim()}
              >
                {isSaving ? '保存中...' : '保存密钥'}
              </button>
            </div>
          )}
          
          {error && <div className="api-key-error">{error}</div>}
          {success && <div className="api-key-success">{success}</div>}
        </div>
      )}
      
      <style jsx>{`
        .api-key-manager {
          margin-bottom: 24px;
          padding: 16px;
          border-radius: 8px;
          background-color: #f8f9fa;
        }
        
        .api-key-header {
          margin-bottom: 16px;
        }
        
        .api-key-header h3 {
          margin: 0 0 8px 0;
          font-size: 18px;
          font-weight: 600;
        }
        
        .api-key-description {
          margin: 0;
          font-size: 14px;
          color: #6c757d;
        }
        
        .api-key-loading {
          color: #6c757d;
          font-style: italic;
        }
        
        .api-key-content {
          margin-top: 16px;
        }
        
        .api-key-form {
          display: flex;
          gap: 8px;
        }
        
        .api-key-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-size: 16px;
        }
        
        .api-key-save-btn {
          padding: 8px 16px;
          background-color: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        
        .api-key-save-btn:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
        }
        
        .api-key-status {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .api-key-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .api-key-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
        }
        
        .api-key-badge.success {
          background-color: #28a745;
          color: white;
        }
        
        .api-key-storage-info {
          font-size: 12px;
          color: #6c757d;
        }
        
        .api-key-delete-btn {
          padding: 6px 12px;
          background-color: #dc3545;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }
        
        .api-key-delete-btn:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
        }
        
        .api-key-error {
          margin-top: 12px;
          color: #dc3545;
          font-size: 14px;
        }
        
        .api-key-success {
          margin-top: 12px;
          color: #28a745;
          font-size: 14px;
        }
      `}</style>
    </div>
  );
};

export default ApiKeyManager;
