param(
    [ValidateSet('Up', 'Connect', 'Disconnect', 'Status', 'Stop')]
    [string]$Action = 'Status'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$composeArgs = @('compose', '-f', (Join-Path $repo 'compose.yaml'), '-f', (Join-Path $repo 'compose.pitwall.yaml'))
$localOverride = Join-Path $repo 'work\compose.local.yaml'
if (Test-Path -LiteralPath $localOverride) { $composeArgs += @('-f', $localOverride) }
if ($Action -eq 'Up') {
    & docker @composeArgs up -d --build --wait backend frontend
    if ($LASTEXITCODE -ne 0) { throw 'Pitwall startup failed. Start the separate Quiz lab first.' }
}
if ($Action -in @('Connect', 'Up')) {
    & docker @composeArgs run --rm --no-deps backend python -m app.connect_quiz connect
    if ($LASTEXITCODE -ne 0) { throw 'Quiz connection failed. Backups remain in the state volume.' }
    Write-Host 'Pitwall: http://localhost:5173'
    Write-Host 'Quiz through Pitwall: http://localhost:8000/quiz-lab-webapp/index.html'
} elseif ($Action -in @('Disconnect', 'Stop')) {
    Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/experiments/restore' -TimeoutSec 5 | Out-Null
    & docker @composeArgs run --rm --no-deps backend python -m app.connect_quiz disconnect
    if ($LASTEXITCODE -ne 0) { throw 'Quiz could not be disconnected; Pitwall was left running.' }
    if ($Action -eq 'Stop') { & docker @composeArgs stop backend frontend }
} else {
    & docker @composeArgs ps
}
if ($LASTEXITCODE -ne 0) { throw "Pitwall action $Action failed." }
