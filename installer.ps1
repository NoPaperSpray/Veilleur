$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Installe Python 3.11 avec le lanceur py puis relance.' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation des dependances echouee.' }
if (-not (Test-Path -LiteralPath config.json)) { Copy-Item -LiteralPath config.example.json -Destination config.json }
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
Write-Host 'Installation terminee. Configure .env et config.json puis redemarre le client MCP.'
