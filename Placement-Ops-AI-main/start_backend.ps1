# Placement Ops – Backend Startup Script
# Run this from the project root: .\start_backend.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n[Placement Ops] Starting FastAPI backend..." -ForegroundColor Cyan

# Set PYTHONPATH so 'backend.*' imports resolve from the project root
$env:PYTHONPATH = $projectRoot

$uvicorn = Join-Path $projectRoot "backend\venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    Write-Error "uvicorn not found at $uvicorn. Run: cd backend && pip install -r requirements.txt"
    exit 1
}

Write-Host "[Placement Ops] Using uvicorn: $uvicorn" -ForegroundColor Green
Write-Host "[Placement Ops] Backend will be available at http://localhost:8000" -ForegroundColor Green
Write-Host "[Placement Ops] Press Ctrl+C to stop.`n" -ForegroundColor Yellow

# --host 0.0.0.0 ensures CORS preflight OPTIONS requests are handled correctly
# (127.0.0.1-only binding has caused CORS failures in the browser)
& $uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
