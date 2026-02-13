/**
 * Electron 主进程
 */
const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const url = require('url');
const fs = require('fs');
const { promisify } = require('util');
const keytar = require('keytar');
const { PythonManager } = require('./python-manager');
// 菜单系统已移除，使用自定义标题栏

// 将 fs 的异步方法转换为 Promise 版本
const readFile = promisify(fs.readFile);
const writeFile = promisify(fs.writeFile);
const readdir = promisify(fs.readdir);
const stat = promisify(fs.stat);

// 检测是否为开发模式
const isDev = process.argv.includes('--dev');

// 创建 Python 后端管理器实例
const pythonManager = new PythonManager({
  isDev,
  pythonPath: isDev ? null : path.join(process.resourcesPath, 'python_backend', process.platform === 'win32' ? 'backend.exe' : 'backend'),
  appPath: app.getAppPath(),
  port: 8000
});

// 保持对窗口对象的全局引用，如果不这样做，
// 当 JavaScript 对象被垃圾回收时，窗口将自动关闭
let mainWindow;

// 检查是否是开发模式
const frontendUrl = isDev 
  ? 'http://localhost:5174' // 开发模式：加载本地开发服务器
  : url.format({            // 生产模式：加载打包后的前端文件
      pathname: path.join(__dirname, '../frontend/dist/index.html'),
      protocol: 'file:',
      slashes: true
    });

// API 后端 URL
const apiBaseUrl = isDev
  ? 'http://localhost:8000'  // 开发模式：使用本地开发服务器
  : 'http://localhost:8000'; // 生产模式：使用内嵌的 Python 后端

// 存储最近文件列表和默认保存目录的路径
const userDataPath = app.getPath('userData');
const recentFilesPath = path.join(userDataPath, 'recentFiles.json');
const settingsPath = path.join(userDataPath, 'settings.json');

// 模板存储路径
const templatesDir = path.join(app.getPath('documents'), 'LLM Editor Templates');
// 确保模板目录存在
if (!fs.existsSync(templatesDir)) {
  try {
    fs.mkdirSync(templatesDir, { recursive: true });
  } catch (error) {
    console.error('创建模板目录失败:', error);
  }
}

// 最近文件列表（最多保存10个）
let recentFiles = [];
// 默认保存目录
let defaultSaveDirectory = app.getPath('documents');

// 加载最近文件列表
async function loadRecentFiles() {
  try {
    if (fs.existsSync(recentFilesPath)) {
      const data = await readFile(recentFilesPath, 'utf8');
      recentFiles = JSON.parse(data);
      // 确保是数组并且最多包含10个文件
      if (!Array.isArray(recentFiles)) {
        recentFiles = [];
      } else {
        recentFiles = recentFiles.slice(0, 10);
      }
    }
  } catch (error) {
    console.error('加载最近文件列表失败:', error);
    recentFiles = [];
  }
}

// 保存最近文件列表
async function saveRecentFiles() {
  try {
    await writeFile(recentFilesPath, JSON.stringify(recentFiles), 'utf8');
  } catch (error) {
    console.error('保存最近文件列表失败:', error);
  }
}

// 添加到最近文件列表
async function addToRecentFiles(filePath) {
  try {
    // 获取文件名
    const fileName = path.basename(filePath);
    
    // 当前时间戳
    const now = Date.now();
    
    // 先移除相同路径的文件（如果存在）
    recentFiles = recentFiles.filter(file => file.path !== filePath);
    
    // 添加到最近文件列表的开头
    recentFiles.unshift({
      path: filePath,
      name: fileName,
      lastOpened: now
    });
    
    // 保持最近文件列表最多10个
    if (recentFiles.length > 10) {
      recentFiles = recentFiles.slice(0, 10);
    }
    
    // 保存到文件
    await saveRecentFiles();
    
    return recentFiles;
  } catch (error) {
    console.error('添加到最近文件列表失败:', error);
    return recentFiles;
  }
}

// 更新最近文件的时间戳
async function updateRecentFileTimestamp(filePath) {
  try {
    // 查找文件在列表中的索引
    const index = recentFiles.findIndex(file => file.path === filePath);
    
    // 如果找到了，更新时间戳
    if (index !== -1) {
      recentFiles[index].lastOpened = Date.now();
      await saveRecentFiles();
    }
    
    return recentFiles;
  } catch (error) {
    console.error('更新最近文件时间戳失败:', error);
    return recentFiles;
  }
}

// 加载设置
async function loadSettings() {
  try {
    if (fs.existsSync(settingsPath)) {
      const data = await readFile(settingsPath, 'utf8');
      const settings = JSON.parse(data);
      if (settings.defaultSaveDirectory && fs.existsSync(settings.defaultSaveDirectory)) {
        defaultSaveDirectory = settings.defaultSaveDirectory;
      }
    }
  } catch (error) {
    console.error('加载设置失败:', error);
  }
}

// 保存设置
async function saveSettings() {
  try {
    const settings = {
      defaultSaveDirectory
    };
    await writeFile(settingsPath, JSON.stringify(settings), 'utf8');
  } catch (error) {
    console.error('保存设置失败:', error);
  }
}

async function createWindow() {
  // 启动 Python 后端（仅在生产模式下）
  if (!isDev) {
    try {
      console.log('Starting Python backend...');
      await pythonManager.startPythonBackend();
      console.log('Python backend started successfully');
    } catch (error) {
      console.error('Failed to start Python backend:', error);
      dialog.showErrorBox(
        'Backend Error',
        'Failed to start the Python backend. The application may not function correctly.'
      );
    }
  }

  // 创建浏览器窗口 - 使用无框架窗口样式
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false, 
    titleBarStyle: 'hidden', 
    backgroundColor: '#FFFFFF',
    webPreferences: {
      nodeIntegration: false, 
      contextIsolation: true, 
      preload: path.join(__dirname, 'preload.js') 
    }
  });

  // 加载前端应用
  mainWindow.loadURL(frontendUrl);
  
  // 菜单样式注入已移除，使用自定义标题栏

  // 打开开发者工具
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // 当窗口关闭时触发
  mainWindow.on('closed', function () {
    // 取消引用窗口对象，通常你会把多个窗口存储在一个数组里，
    // 这时你应该删除相应的元素
    mainWindow = null;
  });
}

// 当 Electron 完成初始化并准备创建浏览器窗口时调用此方法
app.whenReady().then(async () => {
  try {
    // 菜单系统已移除，使用自定义标题栏
    
    // 注册 IPC 处理程序
    registerIpcHandlers();
    registerApiKeyHandlers();
    
    // 加载最近文件列表和设置
    await Promise.all([loadRecentFiles(), loadSettings()]);
    await createWindow();
    
    app.on('activate', async () => {
      // 在 macOS 上，当点击 dock 图标并且没有其他窗口打开时，
      // 通常在应用程序中重新创建一个窗口。
      if (BrowserWindow.getAllWindows().length === 0) {
        await createWindow();
      }
    });
  } catch (error) {
    console.error('启动应用时出错:', error);
    app.quit();
  }
});

// 当所有窗口关闭时退出应用
app.on('window-all-closed', function () {
  // 在 macOS 上，用户通常希望点击 Dock 图标时重新打开应用窗口
  if (process.platform !== 'darwin') app.quit();
});

// 应用退出前停止 Python 后端
app.on('will-quit', async (event) => {
  if (!isDev) {
    event.preventDefault(); // 阻止应用退出，直到 Python 后端停止
    await pythonManager.stopPythonBackend();
    app.exit(); // 现在可以安全退出应用
  }
});

// 注册所有的 IPC 处理程序
/**
 * 注册 API 密钥相关的 IPC 处理程序
 */
function registerApiKeyHandlers() {
  // 服务名称
  const SERVICE_NAME = 'llm-editor';

  // 保存 API 密钥
  ipcMain.handle('save-api-key', async (event, keyName, keyValue) => {
    try {
      await keytar.setPassword(SERVICE_NAME, keyName, keyValue);
      return { success: true };
    } catch (error) {
      console.error('Error saving API key:', error);
      return { success: false, error: error.message };
    }
  });

  // 获取 API 密钥
  ipcMain.handle('get-api-key', async (event, keyName) => {
    try {
      const keyValue = await keytar.getPassword(SERVICE_NAME, keyName);
      return { success: true, keyValue };
    } catch (error) {
      console.error('Error getting API key:', error);
      return { success: false, error: error.message };
    }
  });

  // 删除 API 密钥
  ipcMain.handle('delete-api-key', async (event, keyName) => {
    try {
      await keytar.deletePassword(SERVICE_NAME, keyName);
      return { success: true };
    } catch (error) {
      console.error('Error deleting API key:', error);
      return { success: false, error: error.message };
    }
  });

  // 获取 API 后端 URL
  ipcMain.handle('get-api-base-url', () => {
    return apiBaseUrl;
  });

  // 检查 Python 后端状态
  ipcMain.handle('check-backend-status', async () => {
    try {
      const isRunning = await pythonManager.isPythonBackendRunning();
      return { success: true, isRunning };
    } catch (error) {
      console.error('Error checking backend status:', error);
      return { success: false, error: error.message };
    }
  });
}

/**
 * 注册文件操作相关的 IPC 处理程序
 */
function registerIpcHandlers() {
  // 窗口控制相关的 IPC 处理程序
  ipcMain.handle('window-minimize', () => {
    const win = BrowserWindow.getFocusedWindow();
    if (win) win.minimize();
    return true;
  });
  
  ipcMain.handle('window-maximize', () => {
    const win = BrowserWindow.getFocusedWindow();
    if (win) {
      win.maximize();
      return true;
    }
    return false;
  });
  
  ipcMain.handle('window-restore', () => {
    const win = BrowserWindow.getFocusedWindow();
    if (win) {
      win.unmaximize();
      return true;
    }
    return false;
  });
  
  ipcMain.handle('window-close', () => {
    const win = BrowserWindow.getFocusedWindow();
    if (win) win.close();
    return true;
  });
  
  ipcMain.handle('window-is-maximized', () => {
    const win = BrowserWindow.getFocusedWindow();
    return win ? win.isMaximized() : false;
  });
  
  // 菜单操作处理
  ipcMain.handle('menu-action', (event, action) => {
    const win = BrowserWindow.getFocusedWindow();
    if (!win) return false;
    
    // 处理不同的菜单操作
    switch (action) {
      case 'new-file':
        win.webContents.send('menu-new-file');
        return true;
      case 'open-file':
        win.webContents.send('menu-open-file');
        return true;
      case 'save-file':
        win.webContents.send('menu-save-file');
        return true;
      case 'save-file-as':
        win.webContents.send('menu-save-file-as');
        return true;
      case 'export-pdf':
        win.webContents.send('menu-export-pdf');
        return true;
      case 'undo':
        win.webContents.send('menu-undo');
        return true;
      case 'redo':
        win.webContents.send('menu-redo');
        return true;
      case 'cut':
        win.webContents.send('menu-cut');
        return true;
      case 'copy':
        win.webContents.send('menu-copy');
        return true;
      case 'paste':
        win.webContents.send('menu-paste');
        return true;
      case 'select-all':
        win.webContents.send('menu-select-all');
        return true;
      case 'refresh':
        win.webContents.reload();
        return true;
      case 'force-refresh':
        win.webContents.reloadIgnoringCache();
        return true;
      case 'zoom-in':
        win.webContents.send('menu-zoom-in');
        return true;
      case 'zoom-out':
        win.webContents.send('menu-zoom-out');
        return true;
      case 'reset-zoom':
        win.webContents.send('menu-reset-zoom');
        return true;
      case 'toggle-fullscreen':
        const isFullScreen = win.isFullScreen();
        win.setFullScreen(!isFullScreen);
        return true;
      case 'about':
        dialog.showMessageBox(win, {
          title: 'About Text Editor',
          message: 'Text Editor',
          detail: `Version: ${app.getVersion()}\nElectron: ${process.versions.electron}\nChrome: ${process.versions.chrome}\nNode.js: ${process.versions.node}\nV8: ${process.versions.v8}`,
          buttons: ['OK']
        });
        return true;
      case 'documentation':
        shell.openExternal('https://github.com/hongye-zhang/texteditor');
        return true;
      default:
        console.log(`Unhandled menu action: ${action}`);
        return false;
    }
  });
  
  // 导出为 PDF - 使用更简单的方法
  ipcMain.handle('export-pdf', async (event, content, suggestedName) => {
    console.log('Starting PDF export process...', { contentLength: content?.length, suggestedName });
    try {
      // 获取当前焦点窗口（主窗口）
      const mainWindow = BrowserWindow.getFocusedWindow();
      if (!mainWindow) {
        throw new Error('No focused window found');
      }
      
      // 确保默认使用.pdf扩展名
      const defaultName = suggestedName || 'document.pdf';
      const defaultNameWithExt = defaultName.endsWith('.pdf') ? defaultName : defaultName.replace(/\.[^.]+$/, '') + '.pdf';
      console.log('Preparing save dialog:', { defaultName, defaultNameWithExt, defaultSaveDirectory });
      
      const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
        defaultPath: path.join(defaultSaveDirectory, defaultNameWithExt),
        filters: [
          { name: 'PDF Files', extensions: ['pdf'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });
      
      console.log('Save dialog result:', { canceled, filePath });
      if (canceled || !filePath) {
        console.log('User canceled PDF export operation');
        return { success: false, canceled: true };
      }
      
      // 直接使用主窗口生成PDF
      console.log('Starting PDF generation from main window...');
      const pdfData = await mainWindow.webContents.printToPDF({
        pageSize: 'A4',
        margins: {
          top: 2,
          bottom: 2,
          left: 2,
          right: 2
        },
        printBackground: true,
        landscape: false
      });
      console.log(`PDF data generated, size: ${pdfData.length} bytes`);
      
      // 保存PDF文件
      console.log(`Starting to save PDF file to: ${filePath}`);
      
      // Check if directory exists, create if not
      const dir = path.dirname(filePath);
      try {
        await fs.promises.access(dir, fs.constants.F_OK);
        console.log(`Directory exists: ${dir}`);
      } catch (error) {
        console.log(`Directory does not exist, trying to create: ${dir}`);
        await fs.promises.mkdir(dir, { recursive: true });
        console.log(`Directory created successfully: ${dir}`);
      }
      
      await writeFile(filePath, pdfData);
      console.log('PDF file saved successfully');
      
      // Verify file was saved successfully
      try {
        const stats = await fs.promises.stat(filePath);
        console.log(`File save verification successful, file size: ${stats.size} bytes`);
      } catch (error) {
        console.error('File save verification failed:', error);
        throw new Error(`Cannot access file after saving: ${error.message}`);
      }
      
      console.log(`PDF export successful: ${filePath}`);
      return { success: true, filePath };
      
    } catch (error) {
      console.error('PDF export failed:', error);
      return { success: false, error: error.message };
    }
  });
  
  // 保存文件（首次保存，会弹出保存对话框）
  ipcMain.handle('save-file-as', async (event, content, suggestedName) => {
    try {
      // 确保默认使用.json扩展名，因为我们保存的是编辑器的JSON状态
      const defaultName = suggestedName || 'untitled.json';
      const defaultNameWithExt = defaultName.endsWith('.json') ? defaultName : defaultName.replace(/\.md$|\.txt$|\.json$/, '') + '.json';
      
      const { canceled, filePath } = await dialog.showSaveDialog({
        defaultPath: path.join(defaultSaveDirectory, defaultNameWithExt),
        filters: [
          { name: 'Editor JSON', extensions: ['json'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });
      
      if (canceled || !filePath) {
        console.log('用户取消了保存操作');
        return null;
      }
      
      await writeFile(filePath, content);
      
      // 更新最近文件列表
      await addToRecentFiles(filePath);
      
      return filePath;
    } catch (error) {
      console.error('保存文件失败:', error);
      throw error;
    }
  });
  
  // 注意: 这些处理程序已经在下面的 registerIpcHandlers 函数中注册了
  
  // 保存文件（使用已知路径）
  ipcMain.handle('save-file', async (event, filePath, content) => {
    try {
      if (!filePath) {
        throw new Error('未提供文件路径');
      }
      
      // 写入文件
      await writeFile(filePath, content, 'utf8');
      
      // 更新最近文件列表（不改变顺序，只更新时间戳）
      await updateRecentFileTimestamp(filePath);
      
      return filePath;
    } catch (error) {
      console.error('保存文件失败:', error);
      throw error;
    }
  });
  
  // 打开文件
  ipcMain.handle('open-file', async () => {
    try {
      const { canceled, filePaths } = await dialog.showOpenDialog({
        title: '打开文件',
        defaultPath: defaultSaveDirectory,
        filters: [
          { name: 'Editor JSON 文件', extensions: ['json'] },
          { name: 'Markdown 文件', extensions: ['md'] },
          { name: '文本文件', extensions: ['txt'] },
          { name: '所有文件', extensions: ['*'] }
        ],
        properties: ['openFile']
      });
      
      if (canceled || filePaths.length === 0) {
        return null;
      }
      
      const filePath = filePaths[0];
      const content = await readFile(filePath, 'utf8');
      
      // 添加到最近文件列表
      await addToRecentFiles(filePath);
      
      return {
        path: filePath,
        content,
        name: path.basename(filePath)
      };
    } catch (error) {
      console.error('打开文件失败:', error);
      throw error;
    }
  });
  
  // 打开文件夹
  ipcMain.handle('open-folder', async () => {
    try {
      const { canceled, filePaths } = await dialog.showOpenDialog({
        title: '打开文件夹',
        defaultPath: defaultSaveDirectory,
        properties: ['openDirectory']
      });
      
      if (canceled || filePaths.length === 0) {
        return null;
      }
      
      const folderPath = filePaths[0];
      
      // 设置为默认保存目录
      defaultSaveDirectory = folderPath;
      await saveSettings();
      
      return folderPath;
    } catch (error) {
      console.error('打开文件夹失败:', error);
      throw error;
    }
  });
  
  // 读取文件
  ipcMain.handle('read-file', async (event, filePath) => {
    try {
      if (!filePath) {
        throw new Error('未提供文件路径');
      }
      
      const content = await readFile(filePath, 'utf8');
      
      // 更新最近文件列表
      updateRecentFileTimestamp(filePath);
      
      return {
        path: filePath,
        content,
        name: path.basename(filePath)
      };
    } catch (error) {
      console.error('读取文件失败:', error);
      throw error;
    }
  });
  
  // 列出目录中的文件
  ipcMain.handle('list-files', async (event, folderPath) => {
    try {
      if (!folderPath) {
        throw new Error('未提供文件夹路径');
      }
      
      const files = await readdir(folderPath);
      const fileInfos = [];
      
      for (const file of files) {
        const filePath = path.join(folderPath, file);
        try {
          const stats = await stat(filePath);
          
          if (stats.isFile()) {
            // 只返回 .md 和 .txt 文件
            const ext = path.extname(file).toLowerCase();
            if (ext === '.md' || ext === '.txt') {
              fileInfos.push({
                name: file,
                path: filePath,
                isDirectory: false,
                size: stats.size,
                modifiedTime: stats.mtime.getTime()
              });
            }
          } else if (stats.isDirectory()) {
            fileInfos.push({
              name: file,
              path: filePath,
              isDirectory: true,
              modifiedTime: stats.mtime.getTime()
            });
          }
        } catch (error) {
          console.error(`获取文件信息失败: ${filePath}`, error);
        }
      }
      
      return fileInfos;
    } catch (error) {
      console.error('列出文件夹内容失败:', error);
      throw error;
    }
  });
  
  // 获取最近文件列表
  ipcMain.handle('get-recent-files', () => {
    return recentFiles;
  });
  
  // 添加到最近文件列表
  ipcMain.handle('add-to-recent-files', async (event, filePath) => {
    return await addToRecentFiles(filePath);
  });
  
  // 获取默认保存目录
  ipcMain.handle('get-default-save-directory', () => {
    return defaultSaveDirectory;
  });
  
  // 设置默认保存目录
  ipcMain.handle('set-default-save-directory', async (event, directoryPath) => {
    try {
      if (!directoryPath) {
        throw new Error('未提供目录路径');
      }
      
      // 检查目录是否存在
      const stats = await stat(directoryPath);
      if (!stats.isDirectory()) {
        throw new Error('提供的路径不是一个目录');
      }
      
      defaultSaveDirectory = directoryPath;
      await saveSettings();
      
      return defaultSaveDirectory;
    } catch (error) {
      console.error('设置默认保存目录失败:', error);
      throw error;
    }
  });
  
  // 获取模板存储目录
  ipcMain.handle('get-templates-directory', () => {
    return templatesDir;
  });
  
  // 选择模板存储目录
  ipcMain.handle('select-templates-directory', async () => {
    try {
      const { canceled, filePaths } = await dialog.showOpenDialog({
        properties: ['openDirectory'],
        title: 'Select Template Storage Location',
        buttonLabel: 'Select Folder'
      });
      
      if (canceled || filePaths.length === 0) {
        return { canceled: true };
      }
      
      const newTemplatesDir = filePaths[0];
      
      // Update the templates directory
      templatesDir = newTemplatesDir;
      
      // Ensure the directory exists
      if (!fs.existsSync(templatesDir)) {
        fs.mkdirSync(templatesDir, { recursive: true });
      }
      
      // Save the new templates directory in settings
      settings.templatesDirectory = templatesDir;
      await saveSettings();
      
      return { canceled: false, path: newTemplatesDir };
    } catch (error) {
      console.error('选择模板存储目录失败:', error);
      throw error;
    }
  });
  
  // 保存模板文件
  ipcMain.handle('save-template-file', async (event, templateId, templateData) => {
    try {
      if (!templateId) {
        throw new Error('未提供模板ID');
      }
      
      const templateFilePath = path.join(templatesDir, `${templateId}.json`);
      await writeFile(templateFilePath, JSON.stringify(templateData, null, 2), 'utf8');
      
      return { success: true, path: templateFilePath };
    } catch (error) {
      console.error('保存模板文件失败:', error);
      throw error;
    }
  });
  
  // 读取模板文件
  ipcMain.handle('read-template-file', async (event, templateId) => {
    try {
      if (!templateId) {
        throw new Error('未提供模板ID');
      }
      
      const templateFilePath = path.join(templatesDir, `${templateId}.json`);
      if (!fs.existsSync(templateFilePath)) {
        throw new Error('模板文件不存在');
      }
      
      const content = await readFile(templateFilePath, 'utf8');
      return JSON.parse(content);
    } catch (error) {
      console.error('读取模板文件失败:', error);
      throw error;
    }
  });
  
  // 删除模板文件
  ipcMain.handle('delete-template-file', async (event, templateId) => {
    try {
      if (!templateId) {
        throw new Error('未提供模板ID');
      }
      
      const templateFilePath = path.join(templatesDir, `${templateId}.json`);
      if (fs.existsSync(templateFilePath)) {
        await promisify(fs.unlink)(templateFilePath);
      }
      
      return { success: true };
    } catch (error) {
      console.error('删除模板文件失败:', error);
      throw error;
    }
  });
  
  // 列出所有模板文件
  ipcMain.handle('list-template-files', async () => {
    try {
      if (!fs.existsSync(templatesDir)) {
        fs.mkdirSync(templatesDir, { recursive: true });
        return [];
      }
      
      const files = await readdir(templatesDir);
      const templateFiles = [];
      
      for (const file of files) {
        if (path.extname(file).toLowerCase() === '.json') {
          const filePath = path.join(templatesDir, file);
          try {
            const content = await readFile(filePath, 'utf8');
            const templateData = JSON.parse(content);
            templateFiles.push(templateData);
          } catch (error) {
            console.error(`读取模板文件失败: ${filePath}`, error);
          }
        }
      }
      
      return templateFiles;
    } catch (error) {
      console.error('列出模板文件失败:', error);
      throw error;
    }
  });
  
  // 创建目录
  ipcMain.handle('create-directory', async (event, directoryPath) => {
    try {
      if (!directoryPath) {
        throw new Error('未提供目录路径');
      }
      
      // 使用 recursive 选项可以创建嵌套目录
      await promisify(fs.mkdir)(directoryPath, { recursive: true });
      return { success: true, path: directoryPath };
    } catch (error) {
      console.error('创建目录失败:', error);
      throw error;
    }
  });
  
  // 检查路径是否存在
  ipcMain.handle('check-path-exists', async (event, pathToCheck) => {
    try {
      if (!pathToCheck) {
        throw new Error('未提供要检查的路径');
      }
      
      const exists = fs.existsSync(pathToCheck);
      return exists;
    } catch (error) {
      console.error('检查路径存在失败:', error);
      throw error;
    }
  });
  
  // 删除文件
  ipcMain.handle('delete-file', async (event, filePath) => {
    try {
      if (!filePath) {
        throw new Error('未提供要删除的文件路径');
      }
      
      if (fs.existsSync(filePath)) {
        await promisify(fs.unlink)(filePath);
        return { success: true };
      } else {
        return { success: false, reason: '文件不存在' };
      }
    } catch (error) {
      console.error('删除文件失败:', error);
      throw error;
    }
  });
  
  // 最近文件菜单处理已移除，使用自定义标题栏菜单
}

// 添加文件到最近文件列表
function addToRecentFilesList(filePath) {
  if (!filePath) return;
  
  // 移除已存在的相同路径
  recentFiles = recentFiles.filter(file => file.path !== filePath);
  
  // 添加到列表开头
  recentFiles.unshift({
    path: filePath,
    name: path.basename(filePath),
    lastOpened: Date.now()
  });
  
  // 保持列表最多10个文件
  if (recentFiles.length > 10) {
    recentFiles = recentFiles.slice(0, 10);
  }
  
  // 保存到文件
  saveRecentFiles();
}

// 更新最近文件的时间戳
function updateRecentFileTimestamp(filePath) {
  if (!filePath) return;
  
  const fileIndex = recentFiles.findIndex(file => file.path === filePath);
  
  if (fileIndex !== -1) {
    // 更新时间戳
    recentFiles[fileIndex].lastOpened = Date.now();
    saveRecentFiles();
  }
}
