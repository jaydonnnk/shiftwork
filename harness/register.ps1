# register.ps1 — build the exe, pack the sparse package, sign it, register it.
# Run from a NORMAL (non-admin) PowerShell, after make-cert.ps1.
#
# This IS checklist probe 0. If it fails, stop and report the exact error.

$ErrorActionPreference = 'Stop'

$Root       = $PSScriptRoot
$SrcDir     = Join-Path $Root 'src'
$PfxPath    = Join-Path $Root 'celeste-harness.pfx'
$MsixPath   = Join-Path $Root 'sparse.msix'
$StageDir   = Join-Path $Root 'stage'
$Password   = 'harness'

function Find-SdkTool([string]$name) {
    $hit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter $name -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -match '\\x64\\' } |
           Sort-Object FullName -Descending |
           Select-Object -First 1
    if (-not $hit) { throw "$name not found. Install the Windows SDK (ships with Visual Studio, or standalone from Microsoft)." }
    return $hit.FullName
}

# ---------------------------------------------------------------- 1. build

Write-Host '[1/5] Building CaptureHarness...' -ForegroundColor Cyan
Push-Location $SrcDir
try {
    dotnet publish -c Release -r win-x64 --self-contained false | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'dotnet publish failed.' }
} finally { Pop-Location }

# Find the exe rather than assuming a layout - the bin path shape depends on
# whether MSBuild materialises a platform subfolder, which varies by SDK.
$candidates = Get-ChildItem (Join-Path $SrcDir 'bin') -Recurse -Filter 'CaptureHarness.exe' -ErrorAction SilentlyContinue
if (-not $candidates) { throw "CaptureHarness.exe not found anywhere under $SrcDir\bin" }

$exe = $candidates |
    Sort-Object `
        @{ Expression = { if ($_.FullName -match '\\publish\\') { 0 } else { 1 } } },
        @{ Expression = 'LastWriteTime'; Descending = $true } |
    Select-Object -First 1

$PublishDir = $exe.DirectoryName
Write-Host ("      exe at: {0}" -f $PublishDir)

# ------------------------------------------------- 2. placeholder logo assets

Write-Host '[2/5] Staging manifest + placeholder logos...' -ForegroundColor Cyan

$ImagesDir = Join-Path $PublishDir 'Images'
New-Item -ItemType Directory -Force -Path $ImagesDir | Out-Null

# 1x1 transparent PNG. Dimensions are not validated for a sparse package.
$pngB64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
$pngBytes = [Convert]::FromBase64String($pngB64)
foreach ($n in @('StoreLogo.png','Square150x150Logo.png','Square44x44Logo.png')) {
    [IO.File]::WriteAllBytes((Join-Path $ImagesDir $n), $pngBytes)
}

# The .msix itself carries ONLY the manifest + logos. Binaries stay external.
if (Test-Path $StageDir) { Remove-Item $StageDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir 'Images') | Out-Null
Copy-Item (Join-Path $Root 'AppxManifest.xml') $StageDir
foreach ($n in @('StoreLogo.png','Square150x150Logo.png','Square44x44Logo.png')) {
    [IO.File]::WriteAllBytes((Join-Path $StageDir "Images\$n"), $pngBytes)
}

# ----------------------------------------------------------------- 3. pack

Write-Host '[3/5] Packing sparse .msix...' -ForegroundColor Cyan
$makeappx = Find-SdkTool 'makeappx.exe'
if (Test-Path $MsixPath) { Remove-Item $MsixPath -Force }
& $makeappx pack /d $StageDir /p $MsixPath /nv | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'makeappx pack failed.' }

# ----------------------------------------------------------------- 4. sign

Write-Host '[4/5] Signing...' -ForegroundColor Cyan
if (-not (Test-Path $PfxPath)) { throw "celeste-harness.pfx missing. Run make-cert.ps1 as Administrator first." }
$signtool = Find-SdkTool 'signtool.exe'
& $signtool sign /fd SHA256 /a /f $PfxPath /p $Password $MsixPath | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'signtool sign failed.' }

# ------------------------------------------------------------- 5. register

Write-Host '[5/5] Registering sparse package with external location...' -ForegroundColor Cyan

Get-AppxPackage *CelesteCaptureHarness* -ErrorAction SilentlyContinue | Remove-AppxPackage -ErrorAction SilentlyContinue

Add-AppxPackage -Path $MsixPath -ExternalLocation $PublishDir

$pkg = Get-AppxPackage *CelesteCaptureHarness*
if (-not $pkg) { throw 'Registration reported success but the package is not listed.' }

Write-Host ''
Write-Host 'PROBE 0 PASSED — sparse package registered.' -ForegroundColor Green
Write-Host ("  PackageFullName: {0}" -f $pkg.PackageFullName)
Write-Host ''
Write-Host 'Next, open Notepad, type a sentence, then run:'
Write-Host ("  {0}\CaptureHarness.exe ""Notepad""" -f $PublishDir) -ForegroundColor Yellow
