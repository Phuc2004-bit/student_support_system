[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DistDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "dist"))
$PackageDir = [System.IO.Path]::GetFullPath((Join-Path $DistDir "StudentSupportSystem"))
$ReleaseDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "release"))
$ZipName = "StudentSupportSystem-1.0.0-win64.zip"
$ZipPath = Join-Path $ReleaseDir $ZipName
$ChecksumPath = "$ZipPath.sha256"
$Executable = Join-Path $PackageDir "StudentSupportSystem.exe"
$ReleaseNotes = Join-Path $ProjectRoot "RELEASE_NOTES_V1.0.0.md"
$ReleaseChecklist = Join-Path $ProjectRoot "RELEASE_CHECKLIST_V1.0.0.md"

function Assert-ProjectChildPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $ResolvedProject = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\")
    $ResolvedTarget = [System.IO.Path]::GetFullPath($Path)
    if (-not $ResolvedTarget.StartsWith(
        $ResolvedProject + "\",
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to modify a path outside the project: $ResolvedTarget"
    }
    return $ResolvedTarget
}

$PackageDir = Assert-ProjectChildPath $PackageDir
$ReleaseDir = Assert-ProjectChildPath $ReleaseDir
$ZipPath = Assert-ProjectChildPath $ZipPath
$ChecksumPath = Assert-ProjectChildPath $ChecksumPath

foreach ($RequiredFile in @($Executable, $ReleaseNotes, $ReleaseChecklist)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Required release input is missing: $RequiredFile"
    }
}
if (Test-Path -LiteralPath (Join-Path $PackageDir ".env")) {
    throw "Refusing to release a package containing a real .env file."
}
if (Get-ChildItem -LiteralPath $PackageDir -Recurse -Filter "*.xlsx" -File) {
    throw "Refusing to release a package containing Excel test artifacts."
}

Copy-Item -LiteralPath $ReleaseNotes -Destination $PackageDir -Force
Copy-Item -LiteralPath $ReleaseChecklist -Destination $PackageDir -Force

if (-not (Test-Path -LiteralPath $ReleaseDir)) {
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
}
foreach ($Output in @($ZipPath, $ChecksumPath)) {
    if (Test-Path -LiteralPath $Output) {
        Remove-Item -LiteralPath $Output -Force
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $DistDir,
    $ZipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

$Hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText(
    $ChecksumPath,
    "$Hash  $ZipName`n",
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Release archive: $ZipPath"
Write-Host "SHA-256: $Hash"
