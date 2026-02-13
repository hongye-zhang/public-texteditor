import argparse
import os
import sys
import uvicorn
from fastapi import FastAPI, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    examples, 
    text_selection, 
    command_parsing
)
from app.features.llm import router as llm_router
from app.features.document_structure.router import router as document_structure_router
from app.features.document_editing.router import router as document_editing_router
from app.features.chat.router import router as chat_router
from app.features.intent_analysis.router import router as intent_analysis_router
from app.features.document_tree.router import router as document_tree_router
from app.features.templates.router import router as template_router
from app.logging_config import configure_logging
from app.features.auth.config import auth_settings
from app.features.auth.middleware.csrf_middleware import csrf_protection

# 配置日志系统
configure_logging()

# 应用运行模式
APP_MODE = os.environ.get("APP_MODE", "web")  # 默认为 web 模式

def create_app(mode="web"):
    """
    创建 FastAPI 应用实例
    
    Args:
        mode: 运行模式，可选值为 "web" 或 "electron"
    """
    global APP_MODE
    APP_MODE = mode
    
    app = FastAPI(title="LLM Editor API")
    
    # 配置 CORS
    # 允许来自 localhost 的请求，无论是 web 还是 electron 模式
    origins = auth_settings.ALLOWED_ORIGINS + ["https://accounts.google.com"]
    
    # 在开发模式下，允许所有 localhost 来源
    dev_mode = os.environ.get("DEV_MODE", "true").lower() == "true"
    
    if dev_mode:
        # 开发模式下允许所有来源
        origins = ["*"]
    else:
        # 生产模式下只允许特定端口
        origins.extend([
            "http://localhost:3000",
            "http://localhost:5000", 
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:8000"
        ])
    
    if mode == "electron":
        origins.extend(["file://", "app://"])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-CSRF-Token"],
    )
    
    # 包含现有路由器
    app.include_router(examples.router)
    app.include_router(llm_router)  # 使用基于特性的 LLM 路由器
    app.include_router(chat_router)
    
    # 包含高级编辑功能的新路由器
    app.include_router(text_selection.router)
    app.include_router(document_editing_router)
    app.include_router(document_structure_router)
    app.include_router(intent_analysis_router)
    app.include_router(command_parsing.router)
    app.include_router(document_tree_router)  # 文档树路由器
    app.include_router(template_router)  # 模板系统路由器
    
    @app.get("/")
    async def root():
        return {"message": "Welcome to LLM Editor API", "mode": APP_MODE}
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "mode": APP_MODE}
    
    return app

# 创建默认应用实例
app = create_app()

# 直接运行此脚本时执行
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="LLM Editor Backend Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the server on")
    parser.add_argument("--mode", type=str, default="web", choices=["web", "electron"], 
                        help="Running mode: 'web' for traditional web server, 'electron' for embedded in Electron")
    
    args = parser.parse_args()
    
    # 创建应用实例
    app = create_app(mode=args.mode)
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=False,  # 在 Electron 模式下禁用热重载
        log_level="info"
    )
