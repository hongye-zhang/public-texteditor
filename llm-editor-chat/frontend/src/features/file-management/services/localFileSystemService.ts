/**
 * 本地文件系统服务
 * 使用 Electron 的 API 进行本地文件操作
 * 支持文件夹结构的文档存储，每个文档在自己的文件夹中
 */

// 文档资源接口定义
export interface DocumentAsset {
  id: string;       // 资源唯一ID
  name: string;     // 资源名称
  type: string;     // MIME类型
  path: string;     // 资源在文档文件夹中的相对路径
  size: number;     // 文件大小（字节）
  createdAt: number; // 创建时间戳
}

// 检查是否在 Electron 环境中
const isElectronEnvironment = () => {
  // 检查是否在浏览器环境中
  const isBrowser = typeof window !== 'undefined';
  return isBrowser && window.environment?.isElectron === true;
};

// 检查 Electron API 是否可用
const isElectronApiAvailable = () => {
  // 检查是否在浏览器环境中
  const isBrowser = typeof window !== 'undefined';
  return isBrowser && isElectronEnvironment() && window.electronAPI?.fileSystem != null;
};

/**
 * 保存文件（首次保存，会弹出保存对话框）
 * @param content 文件内容
 * @param suggestedName 建议的文件名
 * @returns 保存的文件路径，如果取消则返回 null
 */
export const saveFileAs = async (content: string, suggestedName: string): Promise<string | null> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法保存文件');
  }

  try {
    return await window.electronAPI.fileSystem.saveFileAs(content, suggestedName);
  } catch (error) {
    console.error('保存文件失败:', error);
    throw error;
  }
};

/**
 * 保存文件（使用已知路径）
 * @param filePath 文件路径
 * @param content 文件内容
 * @returns 保存的文件路径
 */
export const saveFile = async (filePath: string, content: string): Promise<string> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法保存文件');
  }

  try {
    return await window.electronAPI.fileSystem.saveFile(filePath, content);
  } catch (error) {
    console.error('保存文件失败:', error);
    throw error;
  }
};

/**
 * 打开文件
 * @returns 文件信息，包括路径、内容和文件名
 */
export const openFile = async (): Promise<{ path: string; content: string; name: string } | null> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法打开文件');
  }

  try {
    return await window.electronAPI.fileSystem.openFile();
  } catch (error) {
    console.error('打开文件失败:', error);
    throw error;
  }
};

/**
 * 打开文件夹
 * @returns 文件夹路径
 */
export const openFolder = async (): Promise<string | null> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法打开文件夹');
  }

  try {
    return await window.electronAPI.fileSystem.openFolder();
  } catch (error) {
    console.error('打开文件夹失败:', error);
    throw error;
  }
};

/**
 * 读取文件
 * @param filePath 文件路径
 * @returns 文件信息，包括路径、内容和文件名
 */
export const readFile = async (filePath: string): Promise<{ path: string; content: string; name: string }> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法读取文件');
  }

  try {
    return await window.electronAPI.fileSystem.readFile(filePath);
  } catch (error) {
    console.error('读取文件失败:', error);
    throw error;
  }
};

/**
 * 列出目录中的文件
 * @param folderPath 文件夹路径
 * @returns 文件列表
 */
export const listFiles = async (folderPath: string): Promise<Array<{
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
  modifiedTime: number;
}>> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法列出文件');
  }

  try {
    return await window.electronAPI.fileSystem.listFiles(folderPath);
  } catch (error) {
    console.error('列出文件失败:', error);
    throw error;
  }
};

/**
 * 获取最近文件列表
 * @returns 最近文件列表
 */
export const getRecentFiles = async (): Promise<Array<{
  path: string;
  name: string;
  lastOpened: number;
}>> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法获取最近文件列表');
  }

  try {
    return await window.electronAPI.fileSystem.getRecentFiles();
  } catch (error) {
    console.error('获取最近文件列表失败:', error);
    throw error;
  }
};

/**
 * 添加到最近文件列表
 * @param filePath 文件路径
 * @returns 更新后的最近文件列表
 */
export const addToRecentFiles = async (filePath: string): Promise<Array<{
  path: string;
  name: string;
  lastOpened: number;
}>> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法添加到最近文件列表');
  }

  try {
    return await window.electronAPI.fileSystem.addToRecentFiles(filePath);
  } catch (error) {
    console.error('添加到最近文件列表失败:', error);
    throw error;
  }
};

/**
 * 获取默认保存目录
 * @returns 默认保存目录
 */
export const getDefaultSaveDirectory = async (): Promise<string> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法获取默认保存目录');
  }

  try {
    return await window.electronAPI.fileSystem.getDefaultSaveDirectory();
  } catch (error) {
    console.error('获取默认保存目录失败:', error);
    throw error;
  }
};

/**
 * 设置默认保存目录
 * @param directoryPath 目录路径
 * @returns 设置后的默认保存目录
 */
export const setDefaultSaveDirectory = async (directoryPath: string): Promise<string> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法设置默认保存目录');
  }

  try {
    return await window.electronAPI.fileSystem.setDefaultSaveDirectory(directoryPath);
  } catch (error) {
    console.error('设置默认保存目录失败:', error);
    throw error;
  }
};

/**
 * 创建文档文件夹结构
 * @param parentDir 父目录路径
 * @param documentId 文档ID
 * @returns 创建的文档文件夹路径
 */
export const createDocumentFolderStructure = async (parentDir: string, documentId: string): Promise<string> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法创建文档文件夹');
  }

  try {
    // 创建文档主文件夹
    const documentFolderPath = `${parentDir}/${documentId}`;
    await window.electronAPI.fileSystem.createDirectory(documentFolderPath);
    
    // 创建资源文件夹
    const assetsFolderPath = `${documentFolderPath}/assets`;
    await window.electronAPI.fileSystem.createDirectory(assetsFolderPath);
    
    // 创建版本文件夹（占位符，暂不实现功能）
    const versionsFolderPath = `${documentFolderPath}/versions`;
    await window.electronAPI.fileSystem.createDirectory(versionsFolderPath);
    
    return documentFolderPath;
  } catch (error) {
    console.error('创建文档文件夹结构失败:', error);
    throw error;
  }
};

/**
 * 保存文档到文件夹结构
 * @param parentDir 父目录路径
 * @param documentId 文档ID
 * @param documentData 文档数据
 * @returns 保存的文档文件路径
 */
export const saveDocumentToFolder = async (
  parentDir: string, 
  documentId: string, 
  documentData: any
): Promise<string> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法保存文档');
  }

  try {
    // 确保文档文件夹结构存在
    let documentFolderPath;
    try {
      // 检查文档文件夹是否已存在
      const folderExists = await window.electronAPI.fileSystem.checkPathExists(`${parentDir}/${documentId}`);
      
      if (!folderExists) {
        // 如果不存在，创建文件夹结构
        documentFolderPath = await createDocumentFolderStructure(parentDir, documentId);
      } else {
        documentFolderPath = `${parentDir}/${documentId}`;
      }
    } catch (error) {
      // 如果检查失败，尝试创建文件夹结构
      documentFolderPath = await createDocumentFolderStructure(parentDir, documentId);
    }
    
    // 保存文档JSON文件
    const documentFilePath = `${documentFolderPath}/document.json`;
    const documentContent = JSON.stringify(documentData, null, 2);
    await window.electronAPI.fileSystem.saveFile(documentFilePath, documentContent);
    
    return documentFilePath;
  } catch (error) {
    console.error('保存文档到文件夹失败:', error);
    throw error;
  }
};

/**
 * 加载文档从文件夹结构
 * @param documentFolderPath 文档文件夹路径
 * @returns 文档数据
 */
export const loadDocumentFromFolder = async (documentFolderPath: string): Promise<any> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法加载文档');
  }

  try {
    // 读取文档JSON文件
    const documentFilePath = `${documentFolderPath}/document.json`;
    const { content } = await readFile(documentFilePath);
    
    // 解析文档数据
    return JSON.parse(content);
  } catch (error) {
    console.error('从文件夹加载文档失败:', error);
    throw error;
  }
};

/**
 * 保存资源到文档文件夹
 * @param documentFolderPath 文档文件夹路径
 * @param assetData 资源数据
 * @param assetContent 资源内容
 * @returns 保存的资源信息
 */
export const saveAssetToDocument = async (
  documentFolderPath: string,
  assetData: Omit<DocumentAsset, 'path' | 'size'>,
  assetContent: Blob | File | string
): Promise<DocumentAsset> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法保存资源');
  }

  try {
    // 确保资源文件夹存在
    const assetsFolderPath = `${documentFolderPath}/assets`;
    try {
      const folderExists = await window.electronAPI.fileSystem.checkPathExists(assetsFolderPath);
      if (!folderExists) {
        await window.electronAPI.fileSystem.createDirectory(assetsFolderPath);
      }
    } catch (error) {
      await window.electronAPI.fileSystem.createDirectory(assetsFolderPath);
    }
    
    // 构建资源文件路径
    const assetFilePath = `${assetsFolderPath}/${assetData.id}_${assetData.name}`;
    
    // 将内容转换为字符串或ArrayBuffer
    let content: string | ArrayBuffer;
    let size: number;
    
    if (typeof assetContent === 'string') {
      content = assetContent;
      size = new Blob([assetContent]).size;
    } else if (assetContent instanceof Blob || assetContent instanceof File) {
      content = await assetContent.arrayBuffer();
      size = assetContent.size;
    } else {
      throw new Error('不支持的资源内容类型');
    }
    
    // 保存资源文件
    await window.electronAPI.fileSystem.saveAsset(assetFilePath, content);
    
    // 返回完整的资源信息
    return {
      ...assetData,
      path: `assets/${assetData.id}_${assetData.name}`,
      size
    };
  } catch (error) {
    console.error('保存资源到文档失败:', error);
    throw error;
  }
};

/**
 * 加载文档中的资源
 * @param documentFolderPath 文档文件夹路径
 * @param assetPath 资源相对路径
 * @returns 资源内容
 */
export const loadAssetFromDocument = async (
  documentFolderPath: string,
  assetPath: string
): Promise<ArrayBuffer> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法加载资源');
  }

  try {
    // 构建完整的资源路径
    const fullAssetPath = `${documentFolderPath}/${assetPath}`;
    
    // 读取资源文件
    return await window.electronAPI.fileSystem.readAsset(fullAssetPath);
  } catch (error) {
    console.error('从文档加载资源失败:', error);
    throw error;
  }
};

/**
 * 列出文档中的所有资源
 * @param documentFolderPath 文档文件夹路径
 * @returns 资源列表
 */
export const listDocumentAssets = async (documentFolderPath: string): Promise<DocumentAsset[]> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法列出资源');
  }

  try {
    // 构建资源文件夹路径
    const assetsFolderPath = `${documentFolderPath}/assets`;
    
    // 检查资源文件夹是否存在
    try {
      const folderExists = await window.electronAPI.fileSystem.checkPathExists(assetsFolderPath);
      if (!folderExists) {
        return [];
      }
    } catch (error) {
      return [];
    }
    
    // 列出资源文件夹中的文件
    const files = await listFiles(assetsFolderPath);
    
    // 转换为资源列表
    return files
      .filter(file => !file.isDirectory)
      .map(file => {
        // 从文件名解析资源ID和名称
        const fileNameMatch = file.name.match(/^(.+?)_(.+)$/);
        const id = fileNameMatch ? fileNameMatch[1] : file.name;
        const name = fileNameMatch ? fileNameMatch[2] : file.name;
        
        // 从文件路径获取相对路径
        const relativePath = `assets/${file.name}`;
        
        return {
          id,
          name,
          type: getMimeTypeFromFileName(name),
          path: relativePath,
          size: file.size || 0,
          createdAt: file.modifiedTime
        };
      });
  } catch (error) {
    console.error('列出文档资源失败:', error);
    throw error;
  }
};

/**
 * 删除文档中的资源
 * @param documentFolderPath 文档文件夹路径
 * @param assetPath 资源相对路径
 */
export const deleteDocumentAsset = async (
  documentFolderPath: string,
  assetPath: string
): Promise<void> => {
  if (!isElectronApiAvailable()) {
    throw new Error('Electron API 不可用，无法删除资源');
  }

  try {
    // 构建完整的资源路径
    const fullAssetPath = `${documentFolderPath}/${assetPath}`;
    
    // 删除资源文件
    await window.electronAPI.fileSystem.deleteFile(fullAssetPath);
  } catch (error) {
    console.error('删除文档资源失败:', error);
    throw error;
  }
};

/**
 * 从文件名获取MIME类型
 * @param fileName 文件名
 * @returns MIME类型
 */
const getMimeTypeFromFileName = (fileName: string): string => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'gif':
      return 'image/gif';
    case 'svg':
      return 'image/svg+xml';
    case 'pdf':
      return 'application/pdf';
    case 'doc':
      return 'application/msword';
    case 'docx':
      return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    case 'xls':
      return 'application/vnd.ms-excel';
    case 'xlsx':
      return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    case 'ppt':
      return 'application/vnd.ms-powerpoint';
    case 'pptx':
      return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
    case 'txt':
      return 'text/plain';
    case 'html':
    case 'htm':
      return 'text/html';
    case 'css':
      return 'text/css';
    case 'js':
      return 'application/javascript';
    case 'json':
      return 'application/json';
    case 'xml':
      return 'application/xml';
    case 'zip':
      return 'application/zip';
    case 'mp3':
      return 'audio/mpeg';
    case 'mp4':
      return 'video/mp4';
    case 'wav':
      return 'audio/wav';
    case 'avi':
      return 'video/x-msvideo';
    case 'mov':
      return 'video/quicktime';
    default:
      return 'application/octet-stream';
  }
};
