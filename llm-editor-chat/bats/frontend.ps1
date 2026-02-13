# PowerShell script to start the frontend service
Write-Host "Starting LLM Editor Frontend Service..." -ForegroundColor Green

# Navigate to the project root directory
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

# Navigate to the frontend directory
Set-Location "frontend"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    npm install
}

# Start the frontend development server
Write-Host "Starting Vite development server..." -ForegroundColor Green
npm run dev

# This line will only execute if the server stops
Write-Host "Frontend server has stopped." -ForegroundColor Yellow
