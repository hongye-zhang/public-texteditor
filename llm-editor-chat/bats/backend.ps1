# PowerShell script to start the backend service
Write-Host "Starting LLM Editor Backend Service..." -ForegroundColor Green

# Navigate to the project root directory
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

# Check if .venv exists and activate it
if (Test-Path ".venv") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Please create it first." -ForegroundColor Red
    exit 1
}

# Start the backend service using uvicorn
Write-Host "Starting FastAPI backend server..." -ForegroundColor Green
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

# This line will only execute if the server stops
Write-Host "Backend server has stopped." -ForegroundColor Yellow
