/**
 * Python 后端打包脚本
 * 用于将 Python 后端打包为可执行文件，并集成到 Electron 应用中
 */

const { execSync } = require('child_process');
const fs = require('fs-extra');
const path = require('path');
const os = require('os');

// 项目根目录
const rootDir = path.resolve(__dirname, '../..');
// Python 后端目录
const backendDir = path.join(rootDir, 'backend');
// 打包输出目录
const outputDir = path.join(rootDir, 'electron', 'python_backend');
// 临时目录
const tempDir = path.join(os.tmpdir(), 'llm-editor-python-build');

/**
 * 打包 Python 后端
 */
async function packagePythonBackend() {
  try {
    console.log('开始打包 Python 后端...');
    
    // 确保输出目录存在
    await fs.ensureDir(outputDir);
    await fs.emptyDir(outputDir);
    
    // 确保临时目录存在
    await fs.ensureDir(tempDir);
    await fs.emptyDir(tempDir);
    
    // 复制 Python 后端代码到临时目录
    console.log('复制 Python 后端代码到临时目录...');
    await fs.copy(backendDir, path.join(tempDir, 'backend'));
    
    // 创建 requirements.txt 文件（如果不存在）
    const requirementsPath = path.join(tempDir, 'requirements.txt');
    if (!await fs.pathExists(requirementsPath)) {
      console.log('创建 requirements.txt 文件...');
      const requirements = [
        'fastapi==0.95.0',
        'uvicorn==0.21.1',
        'pydantic==1.10.7',
        'python-multipart==0.0.6',
        'httpx==0.24.0',
        'openai==0.27.4',
        'python-dotenv==1.0.0'
      ];
      await fs.writeFile(requirementsPath, requirements.join('\n'));
    }
    
    // 创建入口点脚本
    console.log('创建入口点脚本...');
    const entryPointPath = path.join(tempDir, 'main.py');
    const entryPointContent = `
import sys
import os
import argparse

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 解析命令行参数
parser = argparse.ArgumentParser(description="LLM Editor Backend Server")
parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the server on")
parser.add_argument("--mode", type=str, default="electron", choices=["web", "electron"], 
                    help="Running mode: 'web' for traditional web server, 'electron' for embedded in Electron")

args = parser.parse_args()

# 导入并运行后端
from backend.app.main import create_app
import uvicorn

# 创建应用实例
app = create_app(mode=args.mode)

if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
`;
    await fs.writeFile(entryPointPath, entryPointContent);
    
    // 使用 PyInstaller 打包 Python 后端
    console.log('使用 PyInstaller 打包 Python 后端...');
    const platform = process.platform;
    let pyinstallerCmd;
    
    if (platform === 'win32') {
      // Windows
      pyinstallerCmd = `cd "${tempDir}" && python -m pip install -r requirements.txt && python -m pip install pyinstaller && python -m PyInstaller --onefile --name backend main.py`;
    } else {
      // macOS 和 Linux
      pyinstallerCmd = `cd "${tempDir}" && python3 -m pip install -r requirements.txt && python3 -m pip install pyinstaller && python3 -m PyInstaller --onefile --name backend main.py`;
    }
    
    console.log('执行命令:', pyinstallerCmd);
    execSync(pyinstallerCmd, { stdio: 'inherit' });
    
    // 复制打包后的可执行文件到输出目录
    const distDir = path.join(tempDir, 'dist');
    const executableName = platform === 'win32' ? 'backend.exe' : 'backend';
    const executablePath = path.join(distDir, executableName);
    
    console.log(`复制 ${executablePath} 到 ${outputDir}...`);
    await fs.copy(executablePath, path.join(outputDir, executableName));
    
    console.log('Python 后端打包完成！');
    return true;
  } catch (error) {
    console.error('打包 Python 后端时出错:', error);
    return false;
  } finally {
    // 清理临时目录
    try {
      await fs.remove(tempDir);
      console.log('已清理临时目录');
    } catch (cleanupError) {
      console.error('清理临时目录时出错:', cleanupError);
    }
  }
}

// 如果直接运行此脚本，则执行打包
if (require.main === module) {
  packagePythonBackend()
    .then(success => {
      if (success) {
        console.log('Python 后端打包成功');
        process.exit(0);
      } else {
        console.error('Python 后端打包失败');
        process.exit(1);
      }
    })
    .catch(error => {
      console.error('打包过程中发生错误:', error);
      process.exit(1);
    });
}

module.exports = { packagePythonBackend };
