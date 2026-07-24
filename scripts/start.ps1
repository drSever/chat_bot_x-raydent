$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Сначала запустите scripts\setup.ps1' }
$env:XRAYDENT_OFFLINE = 'true'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
& '.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
