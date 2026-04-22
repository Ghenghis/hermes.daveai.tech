# Phase 3: Windows native tool bundle via winget
# Must run in ELEVATED PowerShell (Run as Administrator)
# Real checks only - no mocks, no skips

$ErrorActionPreference = "Stop"

function Test-Command {
    param([string]$Name)
    $null = Get-Command $Name -ErrorAction SilentlyContinue
    return $?
}

function Test-WingetPackage {
    param([string]$Id)
    try {
        $wingetPath = "C:\Program Files\WindowsApps\Microsoft.DesktopAppInstaller_1.28.240.0_x64__8wekyb3d8bbwe\winget.exe"
        $info = & $wingetPath list --id $Id --exact 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Install-WingetPackage {
    param([string]$Id, [string]$Name)
    if (Test-WingetPackage -Id $Id) {
        Write-Host "  [OK]      $Name (already installed)" -ForegroundColor Green
        return $true
    }
    Write-Host "  [INSTALL] $Name ($Id)..." -ForegroundColor Yellow
    $wingetPath = "C:\Program Files\WindowsApps\Microsoft.DesktopAppInstaller_1.28.240.0_x64__8wekyb3d8bbwe\winget.exe"
    $result = & $wingetPath install --id $Id --exact --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]      $Name" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [FAIL]    $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "=== Phase 3: Windows native tool bundle ===" -ForegroundColor Cyan
Write-Host "Checking winget availability..."
$wingetPath = "C:\Program Files\WindowsApps\Microsoft.DesktopAppInstaller_1.28.240.0_x64__8wekyb3d8bbwe\winget.exe"
if (-not (Test-Path $wingetPath)) {
    Write-Host "[!] winget not found - install from Microsoft Store or run:" -ForegroundColor Red
    Write-Host "    Invoke-WebRequest -Uri https://aka.ms/getwinget -OutFile winget.msixbundle; Add-AppxPackage winget.msixbundle"
    exit 1
}
Write-Host "  [OK] winget available at $wingetPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== Installing packages ===" -ForegroundColor Cyan

$packages = @(
    @{ Id = "Git.Git"; Name = "Git" },
    @{ Id = "GitHub.cli"; Name = "GitHub CLI (gh)" },
    @{ Id = "Microsoft.PowerShell"; Name = "PowerShell 7" },
    @{ Id = "OpenJS.NodeJS.LTS"; Name = "Node.js LTS" },
    @{ Id = "Python.Python.3.12"; Name = "Python 3.12" },
    @{ Id = "Microsoft.OpenSSH.Beta"; Name = "OpenSSH Client" },
    @{ Id = "Docker.DockerDesktop"; Name = "Docker Desktop" },
    @{ Id = "Microsoft.WindowsTerminal"; Name = "Windows Terminal" },
    @{ Id = "7zip.7zip"; Name = "7-Zip" },
    @{ Id = "BurntSushi.ripgrep.MSVC"; Name = "ripgrep (rg)" },
    @{ Id = "sharkdp.fd"; Name = "fd" },
    @{ Id = "jqlang.jq"; Name = "jq" }
)

$failed = @()
foreach ($pkg in $packages) {
    if (-not (Install-WingetPackage -Id $pkg.Id -Name $pkg.Name)) {
        $failed += $pkg.Name
    }
}

Write-Host ""
Write-Host "=== Post-install verification ===" -ForegroundColor Cyan

$tools = @(
    @{ Name = "git"; Cmd = "git --version" },
    @{ Name = "gh";  Cmd = "gh --version" },
    @{ Name = "pwsh"; Cmd = "pwsh --version" },
    @{ Name = "node"; Cmd = "node --version" },
    @{ Name = "npm";  Cmd = "npm --version" },
    @{ Name = "python"; Cmd = "python --version" },
    @{ Name = "pip";  Cmd = "pip --version" },
    @{ Name = "ssh";  Cmd = "ssh -V 2>&1" },
    @{ Name = "docker"; Cmd = "docker --version" },
    @{ Name = "rg";   Cmd = "rg --version" },
    @{ Name = "fd";   Cmd = "fd --version" },
    @{ Name = "jq";   Cmd = "jq --version" }
)

$missing = @()
foreach ($tool in $tools) {
    $output = Invoke-Expression $tool.Cmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = $output[0] -replace '.*', ''
        Write-Host "  [OK]      $($tool.Name)  $version" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $($tool.Name)" -ForegroundColor Red
        $missing += $tool.Name
    }
}

Write-Host ""
Write-Host "=== WSL check ===" -ForegroundColor Cyan
if (Test-Command wsl) {
    Write-Host "  [OK] wsl available" -ForegroundColor Green
    $ubuntu = wsl --list --verbose | Select-String "Ubuntu" | Select-Object -First 1
    if ($ubuntu) {
        Write-Host "  [OK] Ubuntu installed: $($ubuntu)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] Ubuntu (run: wsl --install -d Ubuntu-24.04)" -ForegroundColor Yellow
        $missing += "Ubuntu-WSL"
    }
} else {
    Write-Host "  [MISSING] wsl (enable via Turn Windows features on or off)" -ForegroundColor Yellow
    $missing += "wsl"
}

Write-Host ""
Write-Host "=== Phase 3 Result ===" -ForegroundColor Cyan
if ($failed.Count -gt 0) {
    Write-Host "[!] Failed to install: $($failed -join ', ')" -ForegroundColor Red
}
if ($missing.Count -gt 0) {
    Write-Host "[!] Missing tools after install: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] All Windows tools installed successfully" -ForegroundColor Green
Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1. If Docker Desktop was installed, start it and enable WSL integration for Ubuntu"
Write-Host "2. Restart PowerShell to pick up new PATH entries"
Write-Host "3. Proceed to Phase 4 (gh auth login + ssh-copy-id)"
