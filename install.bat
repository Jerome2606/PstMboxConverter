@echo off
echo PST to mbox Converter - Windows Installation
echo ============================================
echo.

echo Installing required Python library...
pip install libratom

echo.
echo Testing installation...
python pst_to_mbox.py --help

echo.
echo Installation complete!
echo.
echo To use the converter:
echo   python pst_to_mbox.py "your-file.pst" "output.mbox"
echo.
echo For detailed help, see WINDOWS_SETUP.md
pause