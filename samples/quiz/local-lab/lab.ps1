param(
    [ValidateSet('Build', 'Start', 'Deploy', 'Test', 'Status', 'Stop')]
    [string]$Action = 'Status',
    [ValidateSet('Community', 'Licensed')]
    [string]$Mode = 'Community',
    [switch]$PromptForToken
)
$ErrorActionPreference = 'Stop'
$composeFile = Join-Path $PSScriptRoot 'compose.yaml'
$composeArgs = @('compose', '-f', $composeFile)
if ($Mode -eq 'Community') {
    $composeArgs += @('-f', (Join-Path $PSScriptRoot 'compose.community.yaml'))
}
$previousToken = [Environment]::GetEnvironmentVariable('LOCALSTACK_AUTH_TOKEN', 'Process')
$temporaryToken = $false
try {
    if ($Mode -eq 'Licensed' -and $Action -in @('Start', 'Deploy')) {
        if ([string]::IsNullOrWhiteSpace($previousToken) -and $PromptForToken) {
            $secureToken = Read-Host 'LocalStack auth token (hidden; not saved)' -AsSecureString
            $credential = [System.Net.NetworkCredential]::new('', $secureToken)
            [Environment]::SetEnvironmentVariable('LOCALSTACK_AUTH_TOKEN', $credential.Password, 'Process')
            $temporaryToken = $true
            $credential = $null
            $secureToken.Dispose()
        }
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('LOCALSTACK_AUTH_TOKEN'))) {
            throw 'Activate your LocalStack account, then rerun with -PromptForToken. Keep the token out of chat and source files.'
        }
    }
    if ($Action -eq 'Build') {
        & docker @composeArgs --profile tools build tools
        if ($LASTEXITCODE -ne 0) { throw 'Tool image build failed.' }
        & docker run --rm --entrypoint /opt/lab/tools.sh sunhacks-quiz-lab-tools:local check-tools
    } elseif ($Action -in @('Start', 'Deploy')) {
        & docker @composeArgs up -d --wait --wait-timeout 180 localstack
        if ($LASTEXITCODE -ne 0) { throw 'LocalStack did not start. Inspect docker compose logs.' }
        if ($Action -eq 'Deploy') {
            & docker @composeArgs --profile tools run --rm --no-deps tools deploy
            if ($LASTEXITCODE -ne 0) { throw 'Deployment failed. Existing local state was preserved.' }
            if ($Mode -eq 'Licensed') {
                & docker @composeArgs --profile frontend up -d frontend
            } else {
                Write-Host 'Quiz app: http://localhost:4567/quiz-lab-webapp/index.html'
            }
        }
    } elseif ($Action -eq 'Test') {
        & docker @composeArgs --profile tools run --rm --no-deps tools test
    } elseif ($Action -eq 'Status') {
        & docker @composeArgs ps -a
    } else {
        & docker @composeArgs --profile frontend stop
    }
    if ($LASTEXITCODE -ne 0) { throw "Local lab action $Action failed." }
} finally {
    if ($temporaryToken) {
        [Environment]::SetEnvironmentVariable('LOCALSTACK_AUTH_TOKEN', $previousToken, 'Process')
    }
}
