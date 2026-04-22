# Phase 6: Hermes Access Verification (Local)
# Runs from Windows PowerShell, checks WSL and Windows tools

$ErrorActionPreference = "Continue"

$PASS = 0
$FAIL = 0

function Test-Check {
    param([string]$Name, [scriptblock]$Command)
    try {
        & $Command | Out-Null
        if ($?) {
            Write-Host "  [PASS] $Name" -ForegroundColor Green
            $script:PASS++
        } else {
            Write-Host "  [FAIL] $Name" -ForegroundColor Red
            $script:FAIL++
        }
    } catch {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        $script:FAIL++
    }
}

Write-Host "=== Phase 6: Hermes Access Verification (Local) ==="
Write-Host ""

Write-Host "=== WSL Environment ==="
Test-Check "WSL Ubuntu running" { wsl -d Ubuntu -- echo ok }
Test-Check "C: drive mounted" { wsl -d Ubuntu -- test -d /mnt/c }
Test-Check "G: drive mounted" { wsl -d Ubuntu -- test -d /mnt/g }

Write-Host ""
Write-Host "=== WSL Symlinks ==="
Test-Check "work/vps symlink" { wsl -d Ubuntu -- test -L ~/work/vps }
Test-Check "work/github symlink" { wsl -d Ubuntu -- test -L ~/work/github }
Test-Check "work/hermes-kit symlink" { wsl -d Ubuntu -- test -L ~/work/hermes-kit }

Write-Host ""
Write-Host "=== paths.yml Registry ==="
Test-Check "~/.hermes directory exists" { wsl -d Ubuntu -- test -d ~/.hermes }
Test-Check "paths.yml exists" { wsl -d Ubuntu -- test -f ~/.hermes/paths.yml }

Write-Host ""
Write-Host "=== WSL Tools (18) ==="
$wslTools = @('ssh','git','gh','curl','wget','jq','rsync','zip','unzip','tar','rg','fd','python3','pip3','node','npm','docker','pwsh')
foreach ($t in $wslTools) {
    Test-Check $t { wsl -d Ubuntu -- command -v $t }
}

Write-Host ""
Write-Host "=== Windows Tools (12) ==="
$winTools = @('git','gh','pwsh','node','npm','python','pip','docker','rg','fd','jq')
foreach ($t in $winTools) {
    Test-Check $t { Get-Command $t -ErrorAction SilentlyContinue }
}

Write-Host ""
Write-Host "=== Python Packages ==="
$pyPkgs = @('httpx','aiohttp','requests','bs4','paramiko','yaml','dotenv','rich','typer','click')
foreach ($p in $pyPkgs) {
    Test-Check $p { wsl -d Ubuntu -- python3 -c "import $p" }
}

Write-Host ""
Write-Host "=== Docker Connectivity ==="
Test-Check "Docker daemon responding" { docker ps }

Write-Host ""
Write-Host "=== Phase 6 Result ==="
Write-Host "  PASS: $PASS"
Write-Host "  FAIL: $FAIL"
if ($FAIL -eq 0) {
    Write-Host "  [OK] All local checks passed" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  [WARN] $FAIL checks failed" -ForegroundColor Yellow
    exit 1
}
