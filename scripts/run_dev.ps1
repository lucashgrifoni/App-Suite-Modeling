# Sobe API + UI em paralelo. Windows PowerShell.
# Uso: na raiz do repo: .\scripts\run_dev.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
python scripts/run_dev.py @args
