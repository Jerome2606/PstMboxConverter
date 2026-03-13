@echo off
setlocal enableextensions enabledelayedexpansion

echo Building PST to mbox Converter Executable
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python was not found in PATH.
    echo.
    echo Installation help:
    echo   - Windows: https://www.python.org/downloads/windows/ (download installer, enable "Add python.exe to PATH")
    echo   - macOS: Install via Homebrew (https://brew.sh) with "brew install python" or download from python.org
    echo   - Linux: Use your package manager, e.g. "sudo apt install python3 python3-pip" or visit https://wiki.python.org/moin/BeginnersGuide/Download
    echo.
    echo After installing Python, reopen this terminal and rerun build_exe.bat.
    pause
    exit /b 1
)

for /f "tokens=1-3 delims=." %%A in ('python -c "import sys; print('{0}.{1}.{2}'.format(*sys.version_info[:3]))"') do (
    set PY_MAJOR=%%A
    set PY_MINOR=%%B
    set PY_PATCH=%%C
)

set /a PY_COMBINED=!PY_MAJOR!*100 + !PY_MINOR!
echo Detected Python version: !PY_MAJOR!.!PY_MINOR!.!PY_PATCH!
echo.

if !PY_MAJOR! LSS 3 (
    echo ❌ Python 3 is required to build this project.
    pause
    exit /b 1
)

if !PY_COMBINED! GEQ 312 (
    echo Detected Python 3.12 or newer. Upgrading pip, setuptools, and wheel for compatibility...
    python -m pip install --upgrade pip setuptools wheel
) else (
    echo Detected Python version earlier than 3.12. Ensuring pip is up to date...
    python -m pip install --upgrade pip
    echo You can optionally update setuptools and wheel with:
    echo   python -m pip install --upgrade setuptools wheel
)

echo.
echo Installing required packages...
python -m pip install --upgrade pyinstaller libratom

echo.
echo Installed package versions:
python -m pip show pip
python -m pip show setuptools >nul 2>nul
if not errorlevel 1 python -m pip show setuptools
python -m pip show wheel >nul 2>nul
if not errorlevel 1 python -m pip show wheel
python -m pip show pyinstaller
python -m pip show libratom

echo.
echo Building executable...
pyinstaller --onefile --console --name pst-to-mbox --hidden-import libratom.lib.pff --hidden-import email.mime.multipart --hidden-import email.mime.text --hidden-import email.mime.base --clean pst_to_mbox.py

echo.
if exist "dist\pst-to-mbox.exe" (
    echo ✓ Build complete!
    echo ✓ Executable created: dist\pst-to-mbox.exe
    echo.
    echo Usage:
    echo   pst-to-mbox.exe "input.pst" "output.mbox"
    echo   pst-to-mbox.exe --help
) else (
    echo ❌ Build failed. Check error messages above.
)
echo.
pause
