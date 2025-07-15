@echo off
echo Building PST to mbox Converter Executable
echo ========================================
echo.

echo Installing required packages...
pip install pyinstaller libratom

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