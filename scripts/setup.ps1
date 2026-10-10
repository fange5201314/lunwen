$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location $taskRoot
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if (!$env:THESIS_ARCHIFY_DIR) { $env:THESIS_ARCHIFY_DIR = Join-Path $taskRoot '.tools/archify' }
if (!(Test-Path (Join-Path $env:THESIS_ARCHIFY_DIR '.git'))) {
  git clone https://github.com/tt-a1i/archify.git $env:THESIS_ARCHIFY_DIR
  if ($LASTEXITCODE -ne 0) { throw 'Archify clone failed' }
}
git -C $env:THESIS_ARCHIFY_DIR checkout 7f483b61e8f68d0d5c3219d2c943c5381c8db0b1
if ($LASTEXITCODE -ne 0) { throw 'Pinned Archify checkout failed' }
node (Join-Path $env:THESIS_ARCHIFY_DIR 'archify/bin/archify.mjs') doctor
if ($LASTEXITCODE -ne 0) { throw 'Archify doctor failed' }
& .\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Control plane tests failed' }
