[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$BuildDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "build"))
$DistDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "dist"))
$ReleaseDir = Join-Path $DistDir "StudentSupportSystem"
$Executable = Join-Path $ReleaseDir "StudentSupportSystem.exe"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $ProjectRoot "StudentSupportSystem.spec"

function Assert-ProjectChildPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $ResolvedProject = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\")
    $ResolvedTarget = [System.IO.Path]::GetFullPath($Path)
    $RequiredPrefix = $ResolvedProject + "\"
    if (-not $ResolvedTarget.StartsWith(
        $RequiredPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to modify a path outside the project: $ResolvedTarget"
    }
    return $ResolvedTarget
}

$BuildDir = Assert-ProjectChildPath $BuildDir
$DistDir = Assert-ProjectChildPath $DistDir

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python virtual environment was not found: $Python"
}
if (-not (Test-Path -LiteralPath $Spec -PathType Leaf)) {
    throw "PyInstaller spec was not found: $Spec"
}

Push-Location $ProjectRoot
try {
    & $Python -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed in .venv."
    }

    foreach ($Target in @($BuildDir, $DistDir)) {
        if (Test-Path -LiteralPath $Target) {
            Remove-Item -LiteralPath $Target -Recurse -Force
        }
    }

    & $Python -m PyInstaller --noconfirm --clean $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Expected executable was not created: $Executable"
    }

    Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.example") -Destination $ReleaseDir
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "HUONG_DAN.txt") -Destination $ReleaseDir
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "RELEASE_NOTES_V1.2.0.md") -Destination $ReleaseDir
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "RELEASE_CHECKLIST_V1.2.0.md") -Destination $ReleaseDir

    $QtPlatformPlugin = Get-ChildItem -LiteralPath $ReleaseDir -Recurse -Filter "qwindows.dll" |
        Select-Object -First 1
    if ($null -eq $QtPlatformPlugin) {
        throw "Qt platform plugin qwindows.dll was not collected."
    }

    $PyodbcExtension = Get-ChildItem -LiteralPath $ReleaseDir -Recurse -Filter "pyodbc*.pyd" |
        Select-Object -First 1
    if ($null -eq $PyodbcExtension) {
        throw "The pyodbc native extension was not collected."
    }

    $BcryptExtension = Get-ChildItem -LiteralPath $ReleaseDir -Recurse -Filter "_bcrypt.pyd" |
        Select-Object -First 1
    if ($null -eq $BcryptExtension) {
        throw "The bcrypt native extension was not collected."
    }

    $MatplotlibConfig = Get-ChildItem -LiteralPath $ReleaseDir -Recurse -Filter "matplotlibrc" |
        Select-Object -First 1
    if ($null -eq $MatplotlibConfig) {
        throw "Matplotlib runtime data was not collected."
    }

    Write-Host "Build completed: $Executable"
    Write-Host "Qt platform plugin: $($QtPlatformPlugin.FullName)"
    Write-Host "pyodbc extension: $($PyodbcExtension.FullName)"
    Write-Host "bcrypt extension: $($BcryptExtension.FullName)"
    Write-Host "matplotlib data: $($MatplotlibConfig.FullName)"
}
finally {
    Pop-Location
}
