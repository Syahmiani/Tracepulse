param([string]$HostAddress = "127.0.0.1")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "frontend\node_modules\.bin\vite"))) { throw "Frontend dependencies are missing. Run .\scripts\setup-windows.ps1 first." }
$env:VITE_SERVICE_URL = "http://${HostAddress}:8443"
$env:VITE_PUBLIC_FRONTEND_ORIGIN = "http://${HostAddress}:5173"
$env:VITE_ALLOW_INSECURE_LOCAL = "true"
Push-Location (Join-Path $root "frontend")
try { & npm.cmd run dev -- --host 0.0.0.0 } finally { Pop-Location }
