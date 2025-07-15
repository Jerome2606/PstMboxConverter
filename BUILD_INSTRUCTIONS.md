# Building Windows Executable (.exe)

## Method 1: Automatic Build (Recommended)

1. **Download all files** to a folder on your Windows computer
2. **Double-click `build_exe.bat`** - this will:
   - Install PyInstaller and libratom
   - Build the .exe file automatically
   - Show you where the executable is created

## Method 2: Manual Build in PyCharm

1. **Open PyCharm** and load the project folder
2. **Install dependencies** in PyCharm terminal:
   ```cmd
   pip install pyinstaller libratom
   ```

3. **Build the executable** using one of these methods:

   **Option A: Using the spec file (recommended)**
   ```cmd
   pyinstaller pst-to-mbox.spec
   ```

   **Option B: Command line**
   ```cmd
   pyinstaller --onefile --console --name pst-to-mbox pst_to_mbox.py
   ```

4. **Find your executable** in the `dist` folder: `dist\pst-to-mbox.exe`

## Method 3: Command Prompt

1. **Open Command Prompt** in the folder with the files
2. **Install dependencies:**
   ```cmd
   pip install pyinstaller libratom
   ```

3. **Build executable:**
   ```cmd
   pyinstaller pst-to-mbox.spec
   ```

## What You Get

After building, you'll have:
- `dist\pst-to-mbox.exe` - **This is your standalone executable!**
- `build\` folder - Build files (can be deleted)
- `pst-to-mbox.spec` - PyInstaller configuration

## Using the Executable

The `.exe` file is completely standalone - no Python installation needed!

```cmd
# Basic usage
pst-to-mbox.exe "input.pst" "output.mbox"

# With progress details
pst-to-mbox.exe -v "input.pst" "output.mbox"

# Show help
pst-to-mbox.exe --help
```

## Distribution

You can copy just the `pst-to-mbox.exe` file to any Windows computer and it will work without requiring Python or any other installation.

## Troubleshooting

### Build Issues:
- **"PyInstaller not found"** - Run: `pip install pyinstaller`
- **"libratom not found"** - Run: `pip install libratom`
- **Permission errors** - Run Command Prompt as Administrator

### Executable Issues:
- **Antivirus warnings** - This is normal for PyInstaller executables. Add to exceptions if needed.
- **Slow startup** - First run may be slower as libraries initialize
- **Large file size** - Executable includes all dependencies (~50-100MB is normal)

## File Paths in Executable

When using the .exe, remember to:
- Use quotes around paths with spaces: `"C:\My Documents\file.pst"`
- Use full paths for best results
- The executable can run from any location

## Example Usage

```cmd
# Convert PST to mbox
pst-to-mbox.exe "C:\Users\John\Documents\Outlook.pst" "C:\Users\John\Desktop\emails.mbox"

# With detailed progress
pst-to-mbox.exe -v "C:\Email\backup.pst" "C:\Email\converted.mbox"
```

The resulting .mbox file can then be imported into Gmail, Outlook.com, Yahoo Mail, or other email services!