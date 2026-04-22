# Hermes Ecosystem - Windows Setup Script
# Run this script to set up the development environment

param(
    [switch]$SkipPython,
    [switch]$SkipNode,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Hermes Ecosystem Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed. Please install Git first."
    exit 1
}

Write-Host "Git: OK" -ForegroundColor Green

# Setup Python environment
if (-not $SkipPython) {
    Write-Host ""
    Write-Host "Setting up Python environment..." -ForegroundColor Yellow
    
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python is not installed. Please install Python 3.11+ first."
        exit 1
    }
    
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion" -ForegroundColor Green
    
    # Create virtual environment
    if (-not (Test-Path "venv")) {
        Write-Host "Creating virtual environment..."
        python -m venv venv
    }
    
    # Activate and install dependencies
    Write-Host "Installing Python dependencies..."
    & .\venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r requirements.txt
    
    Write-Host "Python setup complete!" -ForegroundColor Green
}

# Setup Node.js environment
if (-not $SkipNode) {
    Write-Host ""
    Write-Host "Setting up Node.js environment..." -ForegroundColor Yellow
    
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Error "Node.js is not installed. Please install Node.js 20+ first."
        exit 1
    }
    
    $nodeVersion = node --version
    Write-Host "Node.js version: $nodeVersion" -ForegroundColor Green
    
    Write-Host "Installing Node dependencies..."
    npm install
    
    Write-Host "Installing Playwright browsers..."
    npx playwright install chromium
    
    Write-Host "Node.js setup complete!" -ForegroundColor Green
}

# Copy environment file
Write-Host ""
Write-Host "Setting up environment..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Green
        Write-Host "Please edit .env with your actual API keys" -ForegroundColor Yellow
    }
} else {
    Write-Host ".env already exists" -ForegroundColor Green
}

# Run tests
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Running tests..." -ForegroundColor Yellow
    
    # Python tests
    & .\venv\Scripts\Activate.ps1
    python -m pytest tests/unit -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Some tests failed. Check the output above."
    }
    
    # Check agents panel
    $agentsTest = python -c "from src.webui.agents_panel import AgentsManager; print('OK')" 2>&1
    if ($agentsTest -eq "OK") {
        Write-Host "Agents Panel: OK" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your API keys" -ForegroundColor White
Write-Host "2. Run: docker-compose up -d" -ForegroundColor White
Write-Host "3. Or start development: python -m src.webui.control_center" -ForegroundColor White
Write-Host ""
Write-Host "Documentation: https://github.com/Ghenghis/hermes.daveai.tech" -ForegroundColor Cyan
