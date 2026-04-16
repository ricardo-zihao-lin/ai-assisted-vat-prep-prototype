param(
    [string]$PythonExe = "",
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

$defaultPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$resolvedPython = $null

$pythonCandidates = @()
if ($PythonExe) {
    $pythonCandidates += $PythonExe
}
$pythonCandidates += $defaultPython

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonCandidates += $pythonCommand.Source
}

foreach ($candidate in $pythonCandidates) {
    if (-not $candidate) {
        continue
    }

    if ($candidate -eq "python") {
        $resolvedPython = $candidate
        break
    }

    if (Test-Path $candidate) {
        $resolvedPython = $candidate
        break
    }
}

if (-not $resolvedPython) {
    throw "Could not find a Python interpreter. Pass -PythonExe or create the project virtual environment first."
}

& $resolvedPython -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed for '$resolvedPython'. Install it with '$resolvedPython -m pip install pyinstaller'."
}

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}

if (Test-Path "dist\VAT_Spreadsheet_Demo") {
    Remove-Item "dist\VAT_Spreadsheet_Demo" -Recurse -Force
}

$zipPath = Join-Path $projectRoot "dist\VAT_Spreadsheet_Demo_windows_x64.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

& $resolvedPython -m PyInstaller --noconfirm "packaging\vat_spreadsheet_demo.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not $SkipZip) {
    Compress-Archive -Path "dist\VAT_Spreadsheet_Demo" -DestinationPath $zipPath -Force
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Folder: dist\VAT_Spreadsheet_Demo"
if (-not $SkipZip) {
    Write-Host "Zip:    dist\VAT_Spreadsheet_Demo_windows_x64.zip"
}
