$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $ProjectRoot ".uv-python"
$env:ROBOT_MODE = if ($env:ROBOT_MODE) { $env:ROBOT_MODE } else { "mock" }
$env:PORT = if ($env:PORT) { $env:PORT } else { "8000" }

Set-Location $ProjectRoot
uv run python -m app.main
