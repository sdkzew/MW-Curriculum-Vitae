$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Create the virtual environment and install requirements-build.txt first."
}

& .venv\Scripts\python.exe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "MORPH-WRLD-CV-Studio" `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --collect-all webview `
    app.py

Write-Host "Build complete: dist\MORPH-WRLD-CV-Studio.exe"
