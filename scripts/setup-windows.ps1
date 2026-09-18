<#!
.SYNOPSIS
Installs the TracePulse backend virtual environment and frontend dependencies on Windows.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$version = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($version -ne "3.12") { throw "TracePulse requires the Python 3.12 launcher; found $version." }
& py -3.12 -m venv (Join-Path $root "backend\.venv")
$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root "backend\requirements.in")
& $venvPython -m pip install -e (Join-Path $root "backend") --no-deps
Push-Location (Join-Path $root "frontend")
try { & npm.cmd ci } finally { Pop-Location }
