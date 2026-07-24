$ErrorActionPreference = 'Stop'

$venvPython = '.venv\Scripts\python.exe'
$venvIsUsable = $false
if (Test-Path $venvPython) {
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    & $venvPython --version *> $null
    $venvIsUsable = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousErrorAction
}

if (-not $venvIsUsable) {
    if (Test-Path '.venv') {
        $projectRoot = (Resolve-Path '.').Path
        $venvRoot = (Resolve-Path '.venv').Path
        if (-not $venvRoot.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar)) {
            throw "Unsafe virtual environment path: $venvRoot"
        }
        Write-Host 'The virtual environment is broken. Recreating .venv...'
        Remove-Item -LiteralPath $venvRoot -Recurse -Force
    }

    $pythonCommand = $null
    $pythonArgs = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in @('3.12', '3.11')) {
            & py "-$version" --version *> $null
            if ($LASTEXITCODE -eq 0) {
                $pythonCommand = 'py'
                $pythonArgs = @("-$version")
                break
            }
        }
    }
    if (-not $pythonCommand -and (Get-Command python -ErrorAction SilentlyContinue)) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -in @('3.11', '3.12')) {
            $pythonCommand = 'python'
        }
    }
    if (-not $pythonCommand) {
        throw 'Install 64-bit Python 3.11 or 3.12 and run setup again.'
    }
    & $pythonCommand @pythonArgs -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython training/build_dataset.py
Write-Host 'Ready. Download the models with: .venv\Scripts\python.exe scripts\download_models.py'
