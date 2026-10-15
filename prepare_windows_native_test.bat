@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\windows\build_rc.ps1"
if errorlevel 1 goto failed

echo.
echo Build complete: dist\Kervan-DPI.exe
echo Leave this window open to review the build output.
pause
exit /b 0

:failed
echo.
echo [ERROR] Windows build did not complete. Keep this window open and record the error.
pause
exit /b 1
