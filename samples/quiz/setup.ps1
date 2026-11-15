param(
    [string]$Path,
    [switch]$SkipImage
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$sourceRepo = 'https://github.com/localstack-samples/sample-serverless-quiz-app.git'
$revision = 'f20e26d45758cfa8d8aa514cdd8472de2a29b0a2'
$image = 'localstack/localstack@sha256:7646cacfd486d46716df04152dcdcfd4060cd234f97c44010403e252b511f932'
$imageTag = 'localstack/localstack:community-4.10.1-cached'
$pitwall = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $Path) { $Path = Join-Path $pitwall '..\aws-serverless-quiz-lab' }
$quiz = [IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)

function Check-Git([string]$message) {
    if ($LASTEXITCODE -ne 0) { throw $message }
}

if (-not (Test-Path -LiteralPath (Join-Path $quiz '.git'))) {
    if ((Test-Path -LiteralPath $quiz) -and @(Get-ChildItem -LiteralPath $quiz -Force).Count) {
        throw "The folder is not empty: $quiz. Choose a new folder with -Path."
    }
    New-Item -ItemType Directory -Path $quiz -Force | Out-Null
    & git init --quiet --initial-branch=main $quiz
    Check-Git 'Could not create the Quiz checkout.'
    & git -C $quiz config core.autocrlf false
    Check-Git 'Could not set line endings for the new checkout.'
    & git -C $quiz remote add origin $sourceRepo
    Check-Git 'Could not set the Quiz source repository.'
}

$root = & git -C $quiz rev-parse --show-toplevel
Check-Git 'This is not a Git checkout.'
if ([IO.Path]::GetFullPath($root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) -ne $quiz) {
    throw 'The selected folder belongs to a different Git checkout.'
}
$origin = & git -C $quiz remote get-url origin
Check-Git 'The Quiz checkout has no origin remote.'
if ($origin.TrimEnd('/') -ne $sourceRepo -and $origin.TrimEnd('/') -ne $sourceRepo.Replace('.git', '')) {
    throw 'This folder does not point to the official Quiz source. No files were changed.'
}
& git -C $quiz rev-parse --verify HEAD *> $null
if ($LASTEXITCODE -ne 0) {
    & git -C $quiz fetch --depth 1 origin $revision
    Check-Git 'Could not download the pinned Quiz version. Check your connection and run this again.'
    & git -C $quiz checkout --quiet --detach FETCH_HEAD
    Check-Git 'Could not check out the pinned Quiz version.'
}
& git -C $quiz merge-base --is-ancestor $revision HEAD
Check-Git 'This checkout is based on a different Quiz version. Choose a new folder with -Path.'
$changed = @(& git -C $quiz diff --name-only $revision --)
Check-Git 'Could not check the existing Quiz files.'
$unexpected = @($changed | Where-Object { $_ -ne 'tests/test_infra.py' -and -not $_.StartsWith('local-lab/') })
if ($unexpected.Count) {
    throw ('The Quiz source has other changes. They were left alone: ' + ($unexpected -join ', '))
}

# Check every existing file before copying anything over it.
$overlay = Join-Path $PSScriptRoot 'local-lab'
$files = @(Get-ChildItem -LiteralPath $overlay -File -Force -Recurse)
foreach ($file in $files) {
    $relative = $file.FullName.Substring($overlay.Length + 1)
    $target = Join-Path (Join-Path $quiz 'local-lab') $relative
    if ((Test-Path -LiteralPath $target) -and
        (Get-FileHash -LiteralPath $target).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) {
        throw "A local setup file has changed: $target. Back up your edits before replacing it."
    }
}
$patch = Join-Path $PSScriptRoot 'wait-for-email.patch'
& git -C $quiz apply --check $patch *> $null
$applyPatch = $LASTEXITCODE -eq 0
if (-not $applyPatch) {
    & git -C $quiz apply --reverse --check $patch *> $null
    Check-Git 'The email test differs from the saved patch. Its edits were left alone.'
}
foreach ($file in $files) {
    $relative = $file.FullName.Substring($overlay.Length + 1)
    $target = Join-Path (Join-Path $quiz 'local-lab') $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $target)) { Copy-Item -LiteralPath $file.FullName -Destination $target }
}
if ($applyPatch) {
    & git -C $quiz apply $patch
    Check-Git 'Could not apply the email test fix.'
}

if (-not $SkipImage) {
    $pinnedId = & docker image inspect $image --format '{{.Id}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        & docker pull $image
        if ($LASTEXITCODE -ne 0) { throw 'Could not download the tested Community image.' }
        $pinnedId = & docker image inspect $image --format '{{.Id}}'
        if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the downloaded image.' }
    }
    $taggedId = & docker image inspect $imageTag --format '{{.Id}}' 2>$null
    if ($LASTEXITCODE -eq 0 -and $taggedId -ne $pinnedId) {
        throw 'The local Community image tag points to another image. It was left unchanged.'
    }
    if ($LASTEXITCODE -ne 0) {
        & docker image tag $image $imageTag
        if ($LASTEXITCODE -ne 0) { throw 'Could not tag the tested Community image.' }
    }
}
Write-Host "Quiz files are ready at $quiz"
Write-Host 'This only prepared files and the image. It did not start, stop, or reset any containers.'
