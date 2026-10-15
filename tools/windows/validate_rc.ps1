param(
    [string]$Exe = 'dist\Kervan-DPI.exe'
)

$ErrorActionPreference = 'Stop'
$exePath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Exe))
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_ComputerSystem
$pythonPath = '.\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $pythonPath -PathType Leaf) {
    $python = & $pythonPath --version 2>&1
} else {
    $python = & py -3.13 --version 2>&1
}
Write-Host "Windows: $($os.Caption) ($($os.Version))"
Write-Host "Architecture: $($cpu.SystemType)"
Write-Host "Python: $python"
if (Test-Path -LiteralPath $exePath -PathType Leaf) {
    $item = Get-Item -LiteralPath $exePath
    Write-Host "EXE: $exePath"
    Write-Host "EXE bytes: $($item.Length)"
    Write-Host "EXE SHA-256: $((Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash)"
} else {
    Write-Host "EXE missing: $exePath"
}
foreach ($resource in @('bin\x86\goodbyedpi.exe', 'bin\x86\WinDivert.dll',
        'bin\x86\WinDivert32.sys', 'bin\x86_64\goodbyedpi.exe',
        'bin\x86_64\WinDivert.dll', 'bin\x86_64\WinDivert64.sys')) {
    Write-Host "Resource $resource : $(Test-Path -LiteralPath $resource -PathType Leaf)"
}
Write-Host 'Relevant processes:'
Get-Process -Name 'Kervan-DPI', 'GoodbyeDPI-Turkey', 'goodbyedpi' -ErrorAction SilentlyContinue |
    Select-Object ProcessName, Id, Path | Format-Table -AutoSize
Write-Host 'WinDivert services/drivers visible to SCM:'
Get-CimInstance Win32_SystemDriver -Filter "Name LIKE 'WinDivert%'" -ErrorAction SilentlyContinue |
    Select-Object Name, State, PathName | Format-Table -AutoSize
Write-Host 'Recent _MEI directories (presence alone is not a leak):'
Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter '_MEI*' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name, LastWriteTime |
    Format-Table -AutoSize
