@echo off
setlocal enabledelayedexpansion

echo =====================================
echo    LLM Text Editor - Dev Environment   
echo =====================================
echo.

:: Check environment variable file
if not exist "frontend\.env.development" (
    echo [WARNING] Frontend environment file does not exist, creating from example...
    if exist "frontend\.env.example" (
        copy "frontend\.env.example" "frontend\.env.development"
        echo [SUCCESS] Created frontend\.env.development
    ) else (
        echo [ERROR] Example environment file does not exist! Please manually create frontend\.env.development
        goto error
    )
)

:: Startup mode selection
echo Please select startup mode:
echo 1. Full mode (Frontend + Backend + Electron)
echo 2. Frontend + Backend only (Web mode)
echo 3. Electron + Backend only (Desktop mode)
echo 4. Frontend only (requires separate backend start)
echo 5. Backend only
echo.

set /p "mode=Please enter your choice (1-5): "
echo You entered: [%mode%]

:: Set startup flags
set start_frontend=0
set start_backend=0
set start_electron=0

if "%mode%"=="1" (
    set start_frontend=1
    set start_backend=1
    set start_electron=1
) else if "%mode%"=="2" (
    set start_frontend=1
    set start_backend=1
) else if "%mode%"=="3" (
    set start_backend=1
    set start_electron=1
) else if "%mode%"=="4" (
    set start_frontend=1
) else if "%mode%"=="5" (
    set start_backend=1
) else (
    echo [ERROR] Invalid selection!
    goto error
)

echo.
echo --- Flags set ---
echo start_backend: [%start_backend%]
echo start_frontend: [%start_frontend%]
echo start_electron: [%start_electron%]
echo -----------------
echo.

:: Create temporary directory for storing process IDs
if not exist "temp" mkdir temp

:: Start backend
if "%start_backend%"=="1" (
    echo [INFO] Starting Python backend...
    
    :: Check if Python is installed
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH!
        goto error
    )
    
    :: Check backend dependencies
    if not exist "backend\venv" (
        echo [WARNING] Python virtual environment does not exist, creating...
        python -m venv backend\venv
        echo [SUCCESS] Virtual environment created
        
        echo [WARNING] Installing backend dependencies...
        call backend\venv\Scripts\activate.bat
        pip install -r backend\requirements.txt
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to install backend dependencies!
            goto error
        )
        echo [SUCCESS] Backend dependencies installed
    )
    
    :: Start backend service
    start "LLM Editor Backend" cmd /c "call backend\venv\Scripts\activate.bat && python -m backend.app.main --mode=web --port=5000 && pause"
    
    :: Wait for backend to start
    echo [INFO] Waiting for backend to start...
    timeout /t 3 /nobreak > nul
    
    :: Check if backend started successfully
    set max_retries=5
    set retry_count=0
    
    :check_backend
    curl -s http://localhost:5000/health > nul
    if %errorlevel% equ 0 (
        echo [SUCCESS] Backend started successfully
    ) else (
        set /a retry_count+=1
        if !retry_count! lss %max_retries% (
            echo [WARNING] Backend not ready, retrying... (!retry_count!/%max_retries%)
            timeout /t 2 /nobreak > nul
            goto check_backend
        ) else (
            echo [WARNING] Backend may not have started successfully, but will continue...
        )
    )
)

:: Start frontend
if "%start_frontend%"=="1" (
    echo [INFO] Starting frontend development server...
    
    :: Check if Node.js is installed
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Node.js is not installed or not in PATH!
        goto error
    )
    
    :: Check frontend dependencies
    if not exist "frontend\node_modules" (
        echo [WARNING] Frontend dependencies do not exist, installing...
        cd frontend && npm install
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to install frontend dependencies!
            cd ..
            goto error
        )
        cd ..
        echo [SUCCESS] Frontend dependencies installed
    )
    
    :: Start frontend development server
    start "LLM Editor Frontend" cmd /c "cd frontend && npm run dev && pause"
    
    :: Wait for frontend to start
    echo [INFO] Waiting for frontend development server to start...
    timeout /t 5 /nobreak > nul
)

:: Start Electron
if "%start_electron%"=="1" (
    echo [INFO] Starting Electron application...
    
    :: Check Electron dependencies
    if not exist "electron\node_modules" (
        echo [WARNING] Electron dependencies do not exist, installing...
        cd electron && npm install
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to install Electron dependencies!
            cd ..
            goto error
        )
        cd ..
        echo [SUCCESS] Electron dependencies installed
    )
    
    :: Wait for frontend and backend to be ready
    if "%start_frontend%"=="1" (
        echo [INFO] Waiting for frontend to be ready...
        timeout /t 5 /nobreak > nul
    )
    
    :: Start Electron
    start "LLM Editor Electron" cmd /c "cd electron && npm start -- --dev && pause"
)

echo [SUCCESS] All services started
echo =====================================
echo    Press Ctrl+C to stop all services   
echo =====================================

goto end

:error
echo [ERROR] Error occurred during startup
pause
exit /b 1

:end
echo.
echo Press any key to exit...
pause > nul
endlocal
exit /b 0
