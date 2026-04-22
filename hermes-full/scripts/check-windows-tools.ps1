$tools = @('git','gh','pwsh','node','npm','python','pip','ssh','docker','rg','fd','jq')
Write-Host "=== Windows tool check ==="
foreach ($t in $tools) {
    $v = Get-Command $t -ErrorAction SilentlyContinue
    if ($v) {
        Write-Host "[OK] $t at $($v.Source)"
    } else {
        Write-Host "[MISSING] $t"
    }
}
