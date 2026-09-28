$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-SupportedPython {
    foreach ($name in @("python3.12", "python3.11", "python3.10", "py", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $exe = $cmd.Source
        if ($name -eq "py") {
            foreach ($arg in @("-3.12", "-3.11", "-3.10")) {
                & $exe $arg -c "pass" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    return (& $exe $arg -c "import sys; print(sys.executable)")
                }
            }
            continue
        }
        $ver = & $exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -match '^3\.(10|11|12)$') { return $exe }
    }
    return $null
}

$pythonExe = Get-SupportedPython
if (-not $pythonExe) {
    Write-Error "This project needs Python 3.10, 3.11, or 3.12. Install 3.12 from https://www.python.org/downloads/ then re-run."
}

Write-Host "Using $pythonExe"
& $pythonExe --version

$needVenv = $true
if (Test-Path ".\venv\Scripts\python.exe") {
    & ".\venv\Scripts\python.exe" -m pip -V 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $needVenv = $false }
}

if ($needVenv) {
    if (Test-Path ".\venv") { Remove-Item -Recurse -Force ".\venv" }
    & $pythonExe -m venv venv --upgrade-deps
}

& ".\venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete."
Write-Host "Activate the environment, then start the app:"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  streamlit run app.py"
