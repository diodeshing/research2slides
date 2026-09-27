param(
    [string]$InstallDir = (Join-Path $PSScriptRoot "runtime"),
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$venvDir = Join-Path $InstallDir ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$wheelDir = Join-Path $PSScriptRoot "python_wheels"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
& $PythonCommand -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required." }
& $PythonCommand -m venv $venvDir
if ($LASTEXITCODE -ne 0) { throw "Unable to create virtual environment." }
& $pythonExe -m pip install --no-index --find-links $wheelDir research2slides==0.2.0
if ($LASTEXITCODE -ne 0) { throw "Offline Python package installation failed." }

Write-Output "Installed Research2Slides 0.2.0 into $InstallDir"
Write-Output "Run: powershell -ExecutionPolicy Bypass -File .\run.ps1 doctor --require-renderer"
