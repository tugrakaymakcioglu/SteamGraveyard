[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repositoryRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

try {
    Set-Location -LiteralPath $repositoryRoot
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host 'Preparing SteamGraveyard for first use...' -ForegroundColor Cyan
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            & py.exe -3 -c "import sys; raise SystemExit(sys.version_info < (3, 12))"
            if ($LASTEXITCODE -ne 0) {
                throw 'Python 3.12 or newer is required. Install it from https://python.org/downloads/'
            }
            & py.exe -3 -m venv $venvPath
        }
        elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
            & python.exe -c "import sys; raise SystemExit(sys.version_info < (3, 12))"
            if ($LASTEXITCODE -ne 0) {
                throw 'Python 3.12 or newer is required. Install it from https://python.org/downloads/'
            }
            & python.exe -m venv $venvPath
        }
        else {
            throw 'Python was not found. Install Python 3.12+ from https://python.org/downloads/'
        }
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
            throw 'The private Python environment could not be created.'
        }
    }

    & $venvPython -m pip install --disable-pip-version-check --quiet --editable $repositoryRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'SteamGraveyard dependencies could not be installed.'
    }
    & $venvPython -m steam_graveyard
    if ($LASTEXITCODE -ne 0) {
        throw 'SteamGraveyard closed with an error.'
    }
}
catch {
    Write-Host ''
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Nothing was deleted. Fix the message above and run START_STEAM_GRAVEYARD.bat again.'
    exit 1
}
