#!/usr/bin/env python3
"""
Build script to create a Windows executable using PyInstaller.
"""

import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    """Build the PST to mbox converter as a Windows executable."""
    
    print("Building PST to mbox Converter Executable")
    print("=" * 45)
    print()
    
    # Check if PyInstaller is available
    try:
        import PyInstaller
        print(f"✓ PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")
    
    # Check if libratom is available
    try:
        import libratom
        print(f"✓ libratom found: {libratom.__version__}")
    except ImportError:
        print("❌ libratom not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "libratom"])
        print("✓ libratom installed")
    
    print()
    print("🔨 Building executable...")
    
    # Determine the correct separator for --add-data based on platform
    import platform
    if platform.system() == "Windows":
        data_separator = ";"
    else:
        data_separator = ":"
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable file
        "--console",                    # Keep console window
        "--name", "pst-to-mbox",       # Output filename
        f"--add-data=README.md{data_separator}.",   # Include README
        "--hidden-import", "libratom.lib.pff",  # Include hidden imports
        "--hidden-import", "email.mime.multipart",
        "--hidden-import", "email.mime.text",
        "--hidden-import", "email.mime.base",
        "--clean",                     # Clean build
        "pst_to_mbox.py"              # Main script
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build completed successfully!")
        
        # Check if executable was created
        exe_path = Path("dist/pst-to-mbox.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✓ Executable created: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
        else:
            print("❌ Executable not found in expected location")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print("Error output:", e.stderr)
        return False
    
    print()
    print("📁 Files created:")
    print("  dist/pst-to-mbox.exe  <- Main executable")
    print("  build/                <- Build files (can be deleted)")
    print("  pst-to-mbox.spec      <- PyInstaller spec file")
    
    return True

if __name__ == "__main__":
    success = build_executable()
    if success:
        print()
        print("🎉 Success! You can now distribute the .exe file.")
        print()
        print("Usage:")
        print('  pst-to-mbox.exe "input.pst" "output.mbox"')
        print('  pst-to-mbox.exe --help')
    else:
        print()
        print("❌ Build failed. Check the error messages above.")