@echo off
setlocal
cd /d "%~dp0"
if defined KERVAN_BUILD_PYTHON (
    set "VENV_PYTHON=%KERVAN_BUILD_PYTHON%"
) else (
    set "VENV_PYTHON=.venv\Scripts\python.exe"
)
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Build Python not found: %VENV_PYTHON%. Use Python 3.13 x64 and a fresh environment.
    exit /b 1
)
"%VENV_PYTHON%" -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
    echo [ERROR] This Windows build requires Python 3.13 x64. Python 3.15 and 32-bit environments are unsupported.
    exit /b 1
)
"%VENV_PYTHON%" -c "import PyInstaller,PySide6,PySide6.QtWidgets,sys; sys.exit(0 if PyInstaller.__version__ == '6.16.0' and PySide6.__version__ == '6.10.3' else 1)"
if errorlevel 1 (
    echo [ERROR] Required PyInstaller 6.16.0 and PySide6 6.10.3 are missing or mismatched. Install requirements.txt.
    exit /b 1
)
if not exist "assets\kervan-camel.png" (
    echo [ERROR] Approved assets\kervan-camel.png is missing.
    exit /b 1
)
if not exist "assets\kervan-camel.ico" (
    echo [ERROR] Generated assets\kervan-camel.ico is missing.
    exit /b 1
)
if exist "dist\Kervan-DPI.exe" (
    echo [ERROR] dist\Kervan-DPI.exe already exists. Use a fresh extracted source directory; no artifact was overwritten.
    exit /b 1
)
"%VENV_PYTHON%" -m PyInstaller --noconfirm --clean packaging\windows\goodbyedpi-turkey.spec
if errorlevel 1 exit /b 1
if not exist "dist\Kervan-DPI.exe" (
    echo [ERROR] PyInstaller finished without dist\Kervan-DPI.exe.
    exit /b 1
)
echo Build complete: dist\Kervan-DPI.exe
