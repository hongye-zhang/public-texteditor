/**
 * 双模式架构开发指南
 * 
 * 本文件包含了关于如何在双模式架构下开发和运行应用的详细说明。
 * 这些注释不会影响应用的运行，但为开发者提供了重要的参考信息。
 */

/**
 * # LLM 文本编辑器 - 双模式架构开发指南
 * 
 * ## 架构概述
 * 
 * 该应用支持两种运行模式：
 * 
 * 1. **Electron 模式**：作为桌面应用运行，内嵌 Python 后端
 * 2. **Web 模式**：在浏览器中运行，连接到远程 Python 后端
 * 
 * 两种模式共享相同的前端代码，但在 API 密钥管理和后端通信方面有所不同。
 * 
 * ## 环境配置
 * 
 * 1. 复制 `frontend/.env.example` 到 `frontend/.env.development`（开发环境）或 `frontend/.env.production`（生产环境）
 * 2. 根据需要修改环境变量，特别是 API 基础 URL：
 *    - `VITE_API_BASE_URL_DEVELOPMENT_WEB`：开发环境下 Web 模式的 API 基础 URL
 *    - `VITE_API_BASE_URL_DEVELOPMENT_ELECTRON`：开发环境下 Electron 模式的 API 基础 URL
 *    - `VITE_API_BASE_URL_PRODUCTION_WEB`：生产环境下 Web 模式的 API 基础 URL
 *    - `VITE_API_BASE_URL_PRODUCTION_ELECTRON`：生产环境下 Electron 模式的 API 基础 URL
 * 
 * ## 开发环境启动
 * 
 * 我们提供了两个启动脚本来简化开发流程：
 * 
 * - **Windows**：使用 `dev-start.bat`
 * - **macOS/Linux**：使用 `dev-start.sh`（记得先运行 `chmod +x dev-start.sh` 添加执行权限）
 * 
 * 这些脚本提供了以下启动模式：
 * 
 * 1. 完整模式（前端 + 后端 + Electron）
 * 2. 仅前端 + 后端（Web 模式）
 * 3. 仅 Electron + 后端（桌面模式）
 * 4. 仅前端（需要单独启动后端）
 * 5. 仅后端
 * 
 * 脚本会自动检查依赖并在需要时安装，还会等待服务启动并提供状态反馈。
 * 
 * ## API 密钥管理
 * 
 * API 密钥管理在两种模式下有所不同：
 * 
 * - **Electron 模式**：API 密钥存储在系统密钥链中（更安全）
 * - **Web 模式**：API 密钥存储在浏览器的 localStorage 中（较不安全）
 * 
 * 用户可以通过设置页面管理 API 密钥。在 Electron 模式下，可以通过应用菜单中的"设置"访问；
 * 在 Web 模式下，可以通过访问 `/settings` 路径访问。
 * 
 * ## 后端通信
 * 
 * 后端通信通过统一的 API 客户端处理，该客户端会根据当前运行模式自动选择正确的 API 基础 URL：
 * 
 * - **Electron 模式**：使用本地嵌入的 Python 后端（通常是 http://localhost:5000）
 * - **Web 模式**：使用远程后端服务器（由环境变量配置）
 * 
 * ## 构建和打包
 * 
 * ### 前端构建
 * 
 * ```bash
 * cd frontend
 * npm run build
 * ```
 * 
 * ### Electron 应用打包
 * 
 * ```bash
 * cd electron
 * npm run package
 * ```
 * 
 * 这将打包 Electron 应用，并自动包含已构建的前端和 Python 后端。
 * 
 * ## 故障排除
 * 
 * 1. **后端连接问题**：检查环境变量中的 API 基础 URL 是否正确
 * 2. **API 密钥问题**：在设置页面中重新设置 API 密钥
 * 3. **Electron 启动问题**：检查 Python 后端是否正确打包
 * 4. **前端构建问题**：检查 Node.js 版本是否兼容
 */

// 导出一个空对象，使该文件可以作为模块导入
export const DEVELOPMENT_GUIDE = {
  version: '1.0.0',
  lastUpdated: '2025-06-29',
};

export default DEVELOPMENT_GUIDE;
