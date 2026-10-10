$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location $taskRoot
if (!$env:THESIS_ARCHIFY_DIR) { $env:THESIS_ARCHIFY_DIR = Join-Path $taskRoot '.tools/archify' }
& .\.venv\Scripts\python.exe -X utf8 -m uvicorn workstation.main:app --host 127.0.0.1 --port 8765 --workers 1
if ($LASTEXITCODE -ne 0) { throw 'Workstation service failed' }
