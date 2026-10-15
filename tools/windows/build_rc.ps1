param(
    [string]$SourceArchive = '',
    [string]$ExpectedSourceSha256 = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $root
if ($env:OS -ne 'Windows_NT') { throw 'Build this candidate on native Windows x64.' }
if ((Test-Path -LiteralPath '.venv') -or (Test-Path -LiteralPath 'build') -or
    (Test-Path -LiteralPath 'dist')) {
    throw 'This build requires a fresh extracted source directory. Existing .venv, build or dist paths were left untouched.'
}
if (-not (Test-Path -LiteralPath 'SOURCE-INPUTS-SHA256SUMS.txt' -PathType Leaf)) {
    throw 'Extract the Kervan Windows RC source ZIP first; its source-input manifest is missing.'
}
if ($ExpectedSourceSha256 -and -not $SourceArchive) {
    throw 'Provide -SourceArchive when using -ExpectedSourceSha256.'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher py.exe is missing. Install Python 3.13 x64 with the Windows launcher.'
}
& py -3.13 -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8 else 1)"
if ($LASTEXITCODE -ne 0) {
    throw 'Python 3.13 x64 is required. Install it alongside other versions; do not use the default Python 3.15.'
}

$sourceArchiveHash = $null
if ($SourceArchive) {
    $sourceArchivePath = (Resolve-Path -LiteralPath $SourceArchive).Path
    $sourceArchiveHash = (Get-FileHash -LiteralPath $sourceArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ExpectedSourceSha256 -and $sourceArchiveHash -ne $ExpectedSourceSha256.ToLowerInvariant()) {
        throw 'The transferred source archive SHA-256 does not match the expected digest.'
    }
}

$manifest = Get-Content -LiteralPath 'SOURCE-INPUTS-SHA256SUMS.txt' -Encoding ascii
foreach ($line in $manifest) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw "Malformed source manifest line: $line" }
    $expected = $Matches[1]
    $relative = $Matches[2]
    if ($relative.StartsWith('/') -or $relative.Contains('..') -or $relative.Contains('\')) {
        throw "Unsafe source manifest path: $relative"
    }
    $inputPath = Join-Path $root $relative.Replace('/', [IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw "Missing source input: $relative"
    }
    $actual = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "Source input changed: $relative" }
}

New-Item -ItemType Directory -Path 'dist' | Out-Null
$version = & py -3.13 -c "from src.metadata import VERSION; print(VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Cannot read candidate version.' }
$log = Join-Path 'dist' "Kervan-DPI-$version-windows-build.log"
Start-Transcript -LiteralPath $log | Out-Null
try {
    Write-Host "Verified $($manifest.Count) source inputs; Python 3.13 x64 selected."
    & py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated .venv.' }
    $python = '.\.venv\Scripts\python.exe'
    $wheelhouse = Join-Path 'dist' 'wheelhouse'
    New-Item -ItemType Directory -Path $wheelhouse | Out-Null
    & $python -m pip download --only-binary=:all: --dest $wheelhouse -r requirements-windows-rc.txt
    if ($LASTEXITCODE -ne 0) { throw 'Windows wheel download failed; check Python 3.13 compatibility and the package index.' }
    & $python -m pip install --no-index --find-links $wheelhouse -r requirements-windows-rc.txt
    if ($LASTEXITCODE -ne 0) { throw 'Installation from the captured wheelhouse failed.' }
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Installed dependency set is inconsistent.' }
    $resolved = & $python -m pip freeze
    if ($LASTEXITCODE -ne 0) { throw 'Could not record resolved dependencies.' }
    $resolvedPath = Join-Path 'dist' "Kervan-DPI-$version-windows-requirements-resolved.txt"
    $resolved | Set-Content -LiteralPath $resolvedPath -Encoding ascii

    $previousQt = $env:QT_QPA_PLATFORM
    try {
        $env:QT_QPA_PLATFORM = 'offscreen'
        & $python -m unittest discover -s tests -q
        if ($LASTEXITCODE -ne 0) { throw 'Source tests failed on Windows; no EXE was built.' }
    } finally {
        $env:QT_QPA_PLATFORM = $previousQt
    }

    & .\build.bat
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    & $python tools/windows/inspect_rc.py dist/Kervan-DPI.exe
    if ($LASTEXITCODE -ne 0) { throw 'Frozen EXE contents failed inspection.' }
    & .\tools\windows\package_rc.ps1
    if ($LASTEXITCODE -ne 0) { throw 'Portable package creation failed.' }

    $exe = Join-Path 'dist' 'Kervan-DPI.exe'
    $portable = Join-Path 'dist' "Kervan-DPI-$version-windows-portable.zip"
    $checksums = Join-Path 'dist' "Kervan-DPI-$version-WINDOWS-SHA256SUMS.txt"
    $updateManifest = Join-Path 'dist' "Kervan-DPI-$version-update-manifest.json"
    foreach ($path in @($exe, $portable, $checksums, $updateManifest)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing build output: $path" }
    }
    $fileHash = {
        param($path)
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $wheels = @(Get-ChildItem -LiteralPath $wheelhouse -File | Sort-Object Name | ForEach-Object {
        [ordered]@{ name = $_.Name; sha256 = (& $fileHash $_.FullName) }
    })
    $engine = @(Get-ChildItem -LiteralPath 'bin\x86','bin\x86_64' -File | Sort-Object FullName | ForEach-Object {
        [ordered]@{ path = $_.FullName.Substring($root.Length + 1); sha256 = (& $fileHash $_.FullName) }
    })
    $os = Get-CimInstance Win32_OperatingSystem
    $provenance = [ordered]@{
        status = 'native Windows build only; lifecycle and network QA pending'
        candidate_version = $version
        source_archive_sha256 = $sourceArchiveHash
        source_inputs_manifest_sha256 = (& $fileHash 'SOURCE-INPUTS-SHA256SUMS.txt')
        windows_caption = $os.Caption
        windows_version = $os.Version
        python = (& $python --version)
        pyinstaller = (& $python -m PyInstaller --version)
        resolved_requirements_file = (Split-Path $resolvedPath -Leaf)
        resolved_requirements_sha256 = (& $fileHash $resolvedPath)
        wheels = $wheels
        engine_inputs = $engine
        logo_png_sha256 = (& $fileHash 'assets\kervan-camel.png')
        logo_ico_sha256 = (& $fileHash 'assets\kervan-camel.ico')
        exe_sha256 = (& $fileHash $exe)
        portable_sha256 = (& $fileHash $portable)
        windows_checksums_sha256 = (& $fileHash $checksums)
        unsigned_update_manifest_sha256 = (& $fileHash $updateManifest)
    }
    $provenance | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath (Join-Path 'dist' "Kervan-DPI-$version-windows-build-provenance.json") -Encoding utf8
    Write-Host 'Native build and package checks passed. Run the separate real-device QA checklist before any release.'
} finally {
    Stop-Transcript | Out-Null
}
