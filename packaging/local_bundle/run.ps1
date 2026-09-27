$ErrorActionPreference = "Stop"
$pythonExe = Join-Path $PSScriptRoot "runtime\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Research2Slides is not installed. Run install.ps1 first."
}
$env:RESEARCH2SLIDES_RENDERER_ROOT = Join-Path $PSScriptRoot "renderer_runtime"
& $pythonExe -m research2slides.cli.app @args
exit $LASTEXITCODE
