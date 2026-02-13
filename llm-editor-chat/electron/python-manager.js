const { spawn } = require('child_process');
const path = require('path');
const { app } = require('electron');
const fs = require('fs');
const waitOn = require('wait-on');

/**
 * Python 后端管理器
 * 负责启动、监控和停止本地 Python 后端
 */
class PythonManager {
  constructor() {
    this.pythonProcess = null;
    this.port = 5000;
    this.isRunning = false;
  }
  
  /**
   * 获取 Python 后端可执行文件路径
   */
  getPythonExecutablePath() {
    const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
    
    if (isDev) {
      // 开发环境：使用系统 Python 解释器
      return process.platform === 'win32' ? 'python' : 'python3';
    } else {
      // 生产环境：使用打包后的 Python 可执行文件
      return path.join(
        process.resourcesPath,
        'python_backend',
        process.platform === 'win32' ? 'backend.exe' : 'backend'
      );
    }
  }
  
  /**
   * 获取 Python 后端脚本路径
   */
  getPythonScriptPath() {
    const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
    
    if (isDev) {
      // 开发环境：使用项目中的 Python 脚本
      return path.join(app.getAppPath(), 'backend', 'app', 'main.py');
    } else {
      // 生产环境：打包后的可执行文件不需要脚本路径
      return null;
    }
  }
  
  /**
   * 启动 Python 后端
   */
  async startPythonBackend() {
    if (this.isRunning) {
      console.log('Python backend is already running');
      return true;
    }

    try {
      const executablePath = this.getPythonExecutablePath();
      const scriptPath = this.getPythonScriptPath();
      
      const args = [];
      
      // 在开发环境中，需要指定脚本路径
      if (scriptPath) {
        args.push(scriptPath);
      }
      
      // 添加命令行参数
      args.push('--port', this.port.toString(), '--mode', 'electron');
      
      console.log(`Starting Python backend: ${executablePath} ${args.join(' ')}`);
      
      // 启动 Python 进程
      this.pythonProcess = spawn(executablePath, args, {
        stdio: 'pipe' // 捕获标准输出和错误
      });
      
      // 处理标准输出
      this.pythonProcess.stdout.on('data', (data) => {
        console.log(`Python backend: ${data.toString()}`);
      });
      
      // 处理标准错误
      this.pythonProcess.stderr.on('data', (data) => {
        console.error(`Python backend error: ${data.toString()}`);
      });
      
      // 处理进程退出
      this.pythonProcess.on('close', (code) => {
        console.log(`Python backend exited with code ${code}`);
        this.pythonProcess = null;
        this.isRunning = false;
      });
      
      // 等待 API 服务器启动
      try {
        await waitOn({
          resources: [`http://localhost:${this.port}/health`],
          timeout: 30000 // 30 秒超时
        });
        console.log('Python backend is ready');
        this.isRunning = true;
        return true;
      } catch (error) {
        console.error('Python backend failed to start:', error);
        this.stopPythonBackend();
        throw new Error('Failed to start Python backend');
      }
    } catch (error) {
      console.error('Error starting Python backend:', error);
      return false;
    }
  }
  
  /**
   * 停止 Python 后端
   */
  async stopPythonBackend() {
    if (this.pythonProcess) {
      console.log('Stopping Python backend...');
      
      // 在 Windows 上需要特殊处理
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', this.pythonProcess.pid, '/f', '/t']);
      } else {
        this.pythonProcess.kill();
      }
      
      this.pythonProcess = null;
      this.isRunning = false;
      console.log('Python backend stopped');
    }
  }
  
  /**
   * 检查 Python 后端是否正在运行
   */
  async isPythonBackendRunning() {
    if (!this.isRunning) {
      return false;
    }
    
    try {
      const response = await fetch(`http://localhost:${this.port}/health`);
      const data = await response.json();
      return data.status === 'ok';
    } catch (error) {
      console.error('Error checking Python backend status:', error);
      return false;
    }
  }
}

module.exports = { PythonManager };
