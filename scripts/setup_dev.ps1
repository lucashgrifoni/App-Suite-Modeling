# Executa o setup de desenvolvimento (venv + pip + npm). Windows PowerShell.
# Uso: na raiz do repo: .\scripts\setup_dev.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
python scripts/setup_dev.py @args
