#!/bin/bash

# 设置颜色代码
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印彩色文本的函数
print_colored() {
  echo -e "${1}${2}${NC}"
}

# 打印标题
print_colored "$CYAN" "====================================="
print_colored "$CYAN" "   LLM 文本编辑器 - 开发环境启动   "
print_colored "$CYAN" "====================================="
echo

# 检查环境变量文件
if [ ! -f "frontend/.env.development" ]; then
  print_colored "$YELLOW" "[警告] 前端环境变量文件不存在，将从示例文件创建..."
  if [ -f "frontend/.env.example" ]; then
    cp "frontend/.env.example" "frontend/.env.development"
    print_colored "$GREEN" "[成功] 已创建 frontend/.env.development"
  else
    print_colored "$RED" "[错误] 示例环境变量文件不存在！请手动创建 frontend/.env.development"
    exit 1
  fi
fi

# 创建临时目录用于存储进程ID
mkdir -p temp

# 启动模式选择
echo "请选择启动模式:"
echo "1. 完整模式 (前端 + 后端 + Electron)"
echo "2. 仅前端 + 后端 (Web 模式)"
echo "3. 仅 Electron + 后端 (桌面模式)"
echo "4. 仅前端 (需要单独启动后端)"
echo "5. 仅后端"
echo

read -p "请输入选择 (1-5): " mode

# 设置启动标志
start_frontend=0
start_backend=0
start_electron=0

case $mode in
  1)
    start_frontend=1
    start_backend=1
    start_electron=1
    ;;
  2)
    start_frontend=1
    start_backend=1
    ;;
  3)
    start_backend=1
    start_electron=1
    ;;
  4)
    start_frontend=1
    ;;
  5)
    start_backend=1
    ;;
  *)
    print_colored "$RED" "[错误] 无效的选择！"
    exit 1
    ;;
esac

# 启动后端
if [ $start_backend -eq 1 ]; then
  print_colored "$CYAN" "[信息] 正在启动 Python 后端..."
  
  # 检查 Python 是否安装
  if ! command -v python3 &> /dev/null; then
    print_colored "$RED" "[错误] Python 未安装或不在 PATH 中！"
    exit 1
  fi
  
  # 检查后端依赖
  if [ ! -d "backend/venv" ]; then
    print_colored "$YELLOW" "[警告] Python 虚拟环境不存在，正在创建..."
    python3 -m venv backend/venv
    print_colored "$GREEN" "[成功] 已创建虚拟环境"
    
    print_colored "$YELLOW" "[警告] 正在安装后端依赖..."
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt
    if [ $? -ne 0 ]; then
      print_colored "$RED" "[错误] 安装后端依赖失败！"
      exit 1
    fi
    print_colored "$GREEN" "[成功] 已安装后端依赖"
    deactivate
  fi
  
  # 启动后端服务
  print_colored "$CYAN" "[信息] 启动后端服务..."
  source backend/venv/bin/activate
  python -m backend.app.main --mode=web --port=5000 &
  backend_pid=$!
  echo $backend_pid > temp/backend.pid
  deactivate
  
  # 等待后端启动
  print_colored "$YELLOW" "[信息] 等待后端启动..."
  sleep 3
  
  # 检查后端是否成功启动
  max_retries=5
  retry_count=0
  
  while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:5000/health &> /dev/null; then
      print_colored "$GREEN" "[成功] 后端已成功启动"
      break
    else
      retry_count=$((retry_count+1))
      if [ $retry_count -lt $max_retries ]; then
        print_colored "$YELLOW" "[警告] 后端尚未就绪，重试中... ($retry_count/$max_retries)"
        sleep 2
      else
        print_colored "$RED" "[警告] 后端可能未成功启动，但将继续执行..."
      fi
    fi
  done
fi

# 启动前端
if [ $start_frontend -eq 1 ]; then
  print_colored "$CYAN" "[信息] 正在启动前端开发服务器..."
  
  # 检查 Node.js 是否安装
  if ! command -v node &> /dev/null; then
    print_colored "$RED" "[错误] Node.js 未安装或不在 PATH 中！"
    exit 1
  fi
  
  # 检查前端依赖
  if [ ! -d "frontend/node_modules" ]; then
    print_colored "$YELLOW" "[警告] 前端依赖不存在，正在安装..."
    (cd frontend && npm install)
    if [ $? -ne 0 ]; then
      print_colored "$RED" "[错误] 安装前端依赖失败！"
      exit 1
    fi
    print_colored "$GREEN" "[成功] 已安装前端依赖"
  fi
  
  # 启动前端开发服务器
  print_colored "$CYAN" "[信息] 启动前端开发服务器..."
  (cd frontend && npm run dev) &
  frontend_pid=$!
  echo $frontend_pid > temp/frontend.pid
  
  # 等待前端启动
  print_colored "$YELLOW" "[信息] 等待前端开发服务器启动..."
  sleep 5
fi

# 启动 Electron
if [ $start_electron -eq 1 ]; then
  print_colored "$CYAN" "[信息] 正在启动 Electron 应用..."
  
  # 检查 Electron 依赖
  if [ ! -d "electron/node_modules" ]; then
    print_colored "$YELLOW" "[警告] Electron 依赖不存在，正在安装..."
    (cd electron && npm install)
    if [ $? -ne 0 ]; then
      print_colored "$RED" "[错误] 安装 Electron 依赖失败！"
      exit 1
    fi
    print_colored "$GREEN" "[成功] 已安装 Electron 依赖"
  fi
  
  # 等待前端和后端都准备好
  if [ $start_frontend -eq 1 ]; then
    print_colored "$YELLOW" "[信息] 等待前端准备就绪..."
    sleep 5
  fi
  
  # 启动 Electron
  print_colored "$CYAN" "[信息] 启动 Electron 应用..."
  (cd electron && npm start -- --dev) &
  electron_pid=$!
  echo $electron_pid > temp/electron.pid
fi

print_colored "$GREEN" "[成功] 所有服务已启动"
print_colored "$CYAN" "====================================="
print_colored "$CYAN" "   按 Ctrl+C 停止所有服务   "
print_colored "$CYAN" "====================================="

# 注册清理函数
cleanup() {
  print_colored "$YELLOW" "正在停止所有服务..."
  
  if [ -f "temp/backend.pid" ]; then
    backend_pid=$(cat temp/backend.pid)
    kill $backend_pid 2>/dev/null
    rm temp/backend.pid
    print_colored "$GREEN" "已停止后端服务"
  fi
  
  if [ -f "temp/frontend.pid" ]; then
    frontend_pid=$(cat temp/frontend.pid)
    kill $frontend_pid 2>/dev/null
    rm temp/frontend.pid
    print_colored "$GREEN" "已停止前端服务"
  fi
  
  if [ -f "temp/electron.pid" ]; then
    electron_pid=$(cat temp/electron.pid)
    kill $electron_pid 2>/dev/null
    rm temp/electron.pid
    print_colored "$GREEN" "已停止 Electron 应用"
  fi
  
  print_colored "$GREEN" "清理完成"
  exit 0
}

# 捕获中断信号
trap cleanup SIGINT SIGTERM

# 等待用户中断
wait
