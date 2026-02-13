/**
 * 环境配置
 * 管理不同环境和运行模式下的配置参数
 */

// 默认 API URL 配置
const DEFAULT_API_URLS = {
  // 开发环境
  development: {
    web: '/api', // Web 模式下的开发环境 API URL（使用代理解决 CORS 问题）
    electron: 'http://localhost:8000' // Electron 模式下的开发环境 API URL
  },
  // 生产环境
  production: {
    web: '/api', // Web 模式下的生产环境 API URL (相对路径，通常由反向代理处理)
    electron: 'http://localhost:8000' // Electron 模式下的生产环境 API URL
  }
};

/**
 * 获取当前环境
 * @returns 'development' | 'production'
 */
export function getEnvironment(): 'development' | 'production' {
  return import.meta.env.PROD ? 'production' : 'development';
}

/**
 * 获取当前运行模式
 * @returns 'web' | 'electron'
 */
export function getRunMode(): 'web' | 'electron' {
  // Check if we're in a browser environment
  const isBrowser = typeof window !== 'undefined';
  
  // 检测是否在 Electron 环境中运行
  const isElectron = isBrowser && window.electronAPI && window.electronAPI.appInfo && window.electronAPI.appInfo.isElectron;
  return isElectron ? 'electron' : 'web';
}

/**
 * 获取 API 基础 URL
 * 优先使用环境变量中配置的 URL，如果没有则使用默认配置
 * @returns API 基础 URL
 */
export function getApiBaseUrl(): string {
  const env = getEnvironment();
  const mode = getRunMode();
  
  // 尝试从环境变量获取
  const envKey = `VITE_API_BASE_URL_${env.toUpperCase()}_${mode.toUpperCase()}`;
  const envApiUrl = import.meta.env[envKey];
  if (envApiUrl) {
    return envApiUrl as string;
  }
  
  // 如果环境变量中没有配置，则使用默认配置
  return DEFAULT_API_URLS[env][mode];
}

/**
 * 环境配置对象
 * Wrapped in a function to ensure it's evaluated in the browser context
 */
const createEnvConfig = () => {
  // For SSR safety, default to web mode and get actual values on client
  const environment = getEnvironment();
  const runMode = typeof window !== 'undefined' ? getRunMode() : 'web';
  const apiBaseUrl = typeof window !== 'undefined' ? getApiBaseUrl() : DEFAULT_API_URLS[environment]['web'];
  
  return {
    apiBaseUrl,
    environment,
    runMode,
    isElectron: runMode === 'electron',
    isProduction: environment === 'production',
    isDevelopment: environment === 'development'
  };
};

export const ENV_CONFIG = createEnvConfig();

export default ENV_CONFIG;
