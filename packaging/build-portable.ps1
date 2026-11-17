param(
    [string]$DistPath,
    [string]$WorkPath
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not $DistPath) { $DistPath = Join-Path $projectRoot 'dist' }
if (-not $WorkPath) { $WorkPath = Join-Path $projectRoot 'build\portable' }
$DistPath = [IO.Path]::GetFullPath($DistPath)
$WorkPath = [IO.Path]::GetFullPath($WorkPath)
if (Test-Path -LiteralPath (Join-Path $DistPath 'HybridSign')) {
    throw 'Output already exists. Choose a fresh -DistPath; this script does not delete releases.'
}
Push-Location $projectRoot
try {
    & $pythonPath -B packaging\preflight.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging preflight failed.' }
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Production frontend build failed.' }
    } finally { Pop-Location }
    & $pythonPath -m PyInstaller --distpath $DistPath --workpath $WorkPath packaging\HybridSign.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PORTABLE-README.txt') -Destination (Join-Path $DistPath 'HybridSign\README.txt')
    & $pythonPath -B packaging\notices.py (Join-Path $DistPath 'HybridSign')
    if ($LASTEXITCODE -ne 0) { throw 'Third-party notices could not be collected.' }
    & $pythonPath -B packaging\release_manifest.py (Join-Path $DistPath 'HybridSign')
    if ($LASTEXITCODE -ne 0) { throw 'Release manifest validation failed.' }
} finally { Pop-Location }
exit 0
