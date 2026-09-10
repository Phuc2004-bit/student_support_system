[CmdletBinding()]
param(
    [string]$IsccPath
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$InstallerScript = Join-Path $ProjectRoot "installer\StudentSupportSystem.iss"
$PackageDir = Join-Path $ProjectRoot "dist\StudentSupportSystem"
$Executable = Join-Path $PackageDir "StudentSupportSystem.exe"
$Icon = Join-Path $ProjectRoot "assets\app_icon.ico"
$Output = Join-Path $ProjectRoot "installer\output\StudentSupportSystem-1.3.0-Setup.exe"

function Resolve-IsccCompiler {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        if (-not (Test-Path -LiteralPath $RequestedPath -PathType Leaf)) {
            throw "Inno Setup compiler was not found: $RequestedPath"
        }
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }

    $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($null -ne $Command) {
        return $Command.Source
    }

    foreach ($Candidate in @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            return $Candidate
        }
    }

    throw "Inno Setup 6 compiler (ISCC.exe) was not found. Install it separately; this script never downloads prerequisites."
}

foreach ($RequiredFile in @($InstallerScript, $Executable, $Icon)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Required installer input is missing: $RequiredFile"
    }
}
foreach ($RequiredPath in @(
    (Join-Path $PackageDir "_internal"),
    (Join-Path $PackageDir ".env.example"),
    (Join-Path $PackageDir "HUONG_DAN.txt"),
    (Join-Path $PackageDir "RELEASE_NOTES_V1.3.0.md"),
    (Join-Path $PackageDir "RELEASE_CHECKLIST_V1.3.0.md")
)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required ONEDIR content is missing: $RequiredPath"
    }
}

if (Test-Path -LiteralPath (Join-Path $PackageDir ".env")) {
    throw "Refusing to build an installer containing a real .env file."
}
$Forbidden = Get-ChildItem -LiteralPath $PackageDir -Recurse -Force | Where-Object {
    $_.Name -in @("tests", ".git", ".venv", "__pycache__", "logs") -or
    $_.Extension -in @(".log", ".xlsx", ".py")
}
if ($Forbidden) {
    throw "Refusing to package forbidden development, log, or temporary content."
}

$Compiler = Resolve-IsccCompiler $IsccPath
Push-Location (Split-Path -Parent $InstallerScript)
try {
    & $Compiler $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) {
    throw "Expected installer was not created: $Output"
}
$Installer = Get-Item -LiteralPath $Output
Write-Host "Installer: $($Installer.FullName)"
Write-Host "Size: $($Installer.Length) bytes"
