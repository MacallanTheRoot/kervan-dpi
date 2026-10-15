param([string]$Exe = 'dist\Kervan-DPI.exe')

$ErrorActionPreference = 'Stop'
$version = & .\.venv\Scripts\python.exe -c "from src.metadata import VERSION; print(VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Cannot read source version' }
$exePath = (Resolve-Path -LiteralPath $Exe).Path
$properties = (Get-Item -LiteralPath $exePath).VersionInfo
$expectedCopyright = 'Copyright (c) 2026 MacallanTheRoot'
if ($properties.ProductName -ne 'Kervan DPI' -or
    $properties.FileDescription -ne 'Kervan DPI' -or
    $properties.InternalName -ne 'Kervan DPI' -or
    $properties.OriginalFilename -ne 'Kervan-DPI.exe' -or
    $properties.CompanyName -ne 'MacallanTheRoot' -or
    $properties.LegalCopyright -ne $expectedCopyright -or
    $properties.ProductVersion -ne $version) {
    throw "EXE version resources do not match Kervan DPI $version"
}

$stage = Join-Path 'dist' "Kervan-DPI-$version-windows-portable"
$archive = "$stage.zip"
$manifest = Join-Path 'dist' "Kervan-DPI-$version-WINDOWS-SHA256SUMS.txt"
$updateManifest = Join-Path 'dist' "Kervan-DPI-$version-update-manifest.json"
if (Test-Path -LiteralPath $stage) { throw "Staging path already exists: $stage" }
if (Test-Path -LiteralPath $archive) { throw "Archive already exists: $archive" }
if (Test-Path -LiteralPath $manifest) { throw "Checksum manifest already exists: $manifest" }
if (Test-Path -LiteralPath $updateManifest) { throw "Update manifest already exists: $updateManifest" }
& .\.venv\Scripts\python.exe tools/windows/inspect_rc.py $exePath
if ($LASTEXITCODE -ne 0) { throw 'Frozen EXE content inspection failed' }
New-Item -ItemType Directory -Path $stage | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage 'assets') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage 'bin') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage 'packaging') | Out-Null
Copy-Item -LiteralPath $exePath -Destination (Join-Path $stage 'Kervan-DPI.exe')
Copy-Item -LiteralPath 'README.md','LICENSE','THIRD_PARTY_NOTICES.md' -Destination $stage
Copy-Item -LiteralPath 'assets\kervan-camel.png' -Destination (Join-Path $stage 'assets')
Copy-Item -LiteralPath 'docs' -Destination $stage -Recurse
Copy-Item -LiteralPath 'bin\licenses' -Destination (Join-Path $stage 'bin') -Recurse
Copy-Item -LiteralPath 'packaging\licenses' -Destination (Join-Path $stage 'packaging') -Recurse
Compress-Archive -LiteralPath $stage -DestinationPath $archive -CompressionLevel Optimal
& .\.venv\Scripts\python.exe tools/windows/inspect_portable.py $archive $exePath
if ($LASTEXITCODE -ne 0) { throw 'Portable ZIP content inspection failed' }
& .\.venv\Scripts\python.exe tools/release/update_manifest.py prepare --exe $exePath --version $version --output $updateManifest
if ($LASTEXITCODE -ne 0) { throw 'Unsigned update manifest preparation failed' }

@($exePath, (Resolve-Path -LiteralPath $archive).Path) |
    ForEach-Object { $item = Get-Item -LiteralPath $_; "$((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $($item.Name)" } |
    Set-Content -LiteralPath $manifest -Encoding ascii
Write-Host "Portable candidate: $archive"
Write-Host "Checksums: $manifest"
Write-Host "Unsigned update manifest: $updateManifest (publisher signature and QA still required)"
Write-Host 'Native visual, lifecycle, migration and network QA is still required before publication.'
