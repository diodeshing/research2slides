$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run.ps1"
$sample = Join-Path $PSScriptRoot "sample"
$workspace = Join-Path $PSScriptRoot "smoke_workspace"

& $runner doctor --require-renderer
if ($LASTEXITCODE -ne 0) { throw "Doctor check failed." }
& $runner build `
    (Join-Path $sample "paper.pdf") `
    --latex (Join-Path $sample "source.zip") `
    --workspace $workspace `
    --analysis-draft (Join-Path $sample "analysis_draft.json") `
    --storyline-draft (Join-Path $sample "storyline_draft.json") `
    --slide-spec-draft (Join-Path $sample "slide_spec_draft.json") `
    --semantic-qa-draft (Join-Path $sample "semantic_qa_draft.json") `
    --time-minutes 5.75 `
    --no-render-qa
if ($LASTEXITCODE -ne 0) { throw "Offline end-to-end smoke test failed." }
Write-Output "Local bundle verification passed: $workspace"
