# PST to mbox Converter - Windows Setup Guide

## Prerequisites
- ✅ Python 3.9.18 (you already have this)
- ✅ PyCharm (you already have this)

## Step-by-Step Installation

### 1. Download the Files
Download these files to a folder on your computer (e.g., `C:\PST-Converter\`):
- `pst_to_mbox.py` (main converter script)
- `README.md` (documentation)
- `requirements.txt` (Python dependencies)
- `demo.py` (demo script)
- This setup guide

### 2. Install Required Library
Open Command Prompt (cmd) or PowerShell as Administrator and run:
```cmd
pip install libratom
```

**Alternative if you get permission errors:**
```cmd
pip install --user libratom
```

### 3. Setting up in PyCharm

#### Option A: Create New PyCharm Project
1. Open PyCharm
2. Click "New Project"
3. Choose "Pure Python"
4. Set location to your folder (e.g., `C:\PST-Converter\`)
5. Select your Python 3.9.18 interpreter
6. Click "Create"

#### Option B: Open Existing Folder
1. Open PyCharm
2. Click "Open"
3. Select your PST-Converter folder
4. PyCharm will detect it as a Python project

### 4. Configure PyCharm Environment
1. Go to File → Settings (or Ctrl+Alt+S)
2. Navigate to Project → Python Interpreter
3. Make sure it shows Python 3.9.18
4. Check if `libratom` appears in the package list
5. If not, click the "+" button and install `libratom`

### 5. Test the Installation
In PyCharm terminal (at the bottom), run:
```cmd
python pst_to_mbox.py --help
```

You should see the help message with usage instructions.

## Using the Converter

### Method 1: Command Line in PyCharm
1. Open the terminal in PyCharm (View → Tool Windows → Terminal)
2. Run the converter:
```cmd
python pst_to_mbox.py "C:\path\to\your\file.pst" "C:\path\to\output\emails.mbox"
```

### Method 2: Run Configuration in PyCharm
1. Right-click on `pst_to_mbox.py` in PyCharm
2. Select "Create 'pst_to_mbox'..."
3. In the configuration dialog:
   - **Script path**: (should be filled automatically)
   - **Parameters**: Add your file paths like: `"C:\Users\YourName\Documents\Outlook.pst" "C:\Users\YourName\Documents\emails.mbox"`
4. Click "OK"
5. Click the green "Run" button

### Method 3: Interactive Mode
1. Create a new Python file in PyCharm
2. Add this code:
```python
from pst_to_mbox import PSTToMboxConverter

# Configure your file paths
pst_file = r"C:\path\to\your\outlook.pst"
output_file = r"C:\path\to\output\emails.mbox"

# Create and run converter
converter = PSTToMboxConverter(pst_file, output_file, verbose=True)
success = converter.convert()

if success:
    print("Conversion completed successfully!")
else:
    print("Conversion failed. Check the error messages above.")
```

## File Paths on Windows

### Important Notes:
- Use double backslashes `\\` or raw strings `r"path"` for Windows paths
- Or use forward slashes `/` which also work on Windows
- Put quotes around paths with spaces

### Examples:
```python
# Option 1: Double backslashes
pst_file = "C:\\Users\\John\\Documents\\Outlook.pst"

# Option 2: Raw string (recommended)
pst_file = r"C:\Users\John\Documents\Outlook.pst"

# Option 3: Forward slashes
pst_file = "C:/Users/John/Documents/Outlook.pst"
```

## Troubleshooting

### Common Issues:

1. **"libratom library is required"**
   - Solution: Run `pip install libratom` in Command Prompt

2. **"Permission denied" errors**
   - Solution: Run Command Prompt as Administrator
   - Or use: `pip install --user libratom`

3. **"PST file not found"**
   - Check the file path is correct
   - Make sure the PST file exists
   - Use raw strings: `r"C:\path\to\file.pst"`

4. **PyCharm can't find libratom**
   - Go to File → Settings → Project → Python Interpreter
   - Click "+" and install libratom directly in PyCharm

5. **Large PST files are slow**
   - This is normal for files over 1GB
   - Use verbose mode (`-v`) to see progress
   - The tool will show progress every 100 emails

### Getting Your PST File from Outlook:
1. Open Outlook
2. Go to File → Open & Export → Import/Export
3. Choose "Export to a file"
4. Select "Outlook Data File (.pst)"
5. Choose the folders to export
6. Save the PST file to a location you can remember

## Next Steps
Once conversion is complete:
1. You'll have a `.mbox` file
2. Import this into your webmail service:
   - **Gmail**: Use Google Takeout or third-party tools
   - **Outlook.com**: Account settings → Import
   - **Thunderbird**: ImportExportTools extension

## Need Help?
If you encounter issues:
1. Check the error messages carefully
2. Try running with verbose mode: `python pst_to_mbox.py -v input.pst output.mbox`
3. Make sure your PST file isn't corrupted or password-protected