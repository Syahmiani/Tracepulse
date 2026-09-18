param([string]$HostAddress = "127.0.0.1")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) { throw "Backend environment is missing. Run .\scripts\setup-windows.ps1 first." }
$env:TRACEPULSE_BIND_HOST = "0.0.0.0"
$env:TRACEPULSE_SERVICE_URL = "http://${HostAddress}:8443/"
$env:TRACEPULSE_FRONTEND_ORIGIN = "http://${HostAddress}:5173"
$env:TRACEPULSE_LOCAL_ADMIN_ONLY = "false"
$env:TRACEPULSE_LOCAL_STATUS_ONLY = "false"
$env:TRACEPULSE_ALLOW_INSECURE_LOCAL = "true"
$env:TRACEPULSE_LOCK_OPERATIONS_ENABLED = "false"
$dataRoot = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "TracePulse" } else { Join-Path $HOME "AppData\Local\TracePulse" }
$env:TRACEPULSE_DATABASE_PATH = Join-Path $dataRoot "tracepulse.sqlite3"
Push-Location (Join-Path $root "backend")
try { & $venvPython -m tracepulse.app } finally { Pop-Location }
