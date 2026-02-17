# Run the full TRIX+WMA robustness pipeline
# Usage: .\scripts\run_all.ps1

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

Write-Host "Installing package..." -ForegroundColor Cyan
pip install -e ".[dev]"

Write-Host "`nRunning full pipeline..." -ForegroundColor Cyan
python -m trixwma run-all --config config/default.yaml

Write-Host "`nRunning tests..." -ForegroundColor Cyan
pytest tests/ -v

Write-Host "`nDone!" -ForegroundColor Green
