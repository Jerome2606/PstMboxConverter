# PST to mbox Converter

A Python command-line tool for converting Outlook PST files to mbox format for webmail import.

## Features

- ✅ Reads and parses .PST files exported from Outlook
- ✅ Converts PST email data to standard .mbox format
- ✅ Preserves email metadata (sender, recipient, date, subject)
- ✅ Preserves email body content (both text and HTML)
- ✅ Handles attachments properly
- ✅ Maintains folder structure information
- ✅ Provides progress feedback during conversion
- ✅ Robust error handling for corrupted or invalid files
- ✅ Efficient memory usage for large PST files
- ✅ Cross-platform compatibility

## Requirements

- Python 3.6 or higher
- libratom library (for PST file parsing)

## Installation

### Option 1: Python Script (Requires Python)

1. Install the required Python library:
```bash
pip install libratom
```

2. Download the `pst_to_mbox.py` script

### Option 2: Standalone Executable (No Python Required)

1. Download all project files including build scripts
2. Double-click `build_exe.bat` to automatically create a standalone .exe file
3. Use the generated `pst-to-mbox.exe` without needing Python installed

**Manual build:**
```bash
pip install pyinstaller libratom
pyinstaller pst-to-mbox.spec
```

Find your executable in the `dist` folder.

## Usage

### Python Script
```bash
# Basic usage
python pst_to_mbox.py input.pst output.mbox

# With verbose output
python pst_to_mbox.py -v input.pst output.mbox
```

### Standalone Executable
```bash
# Basic usage
pst-to-mbox.exe input.pst output.mbox

# With verbose output
pst-to-mbox.exe -v input.pst output.mbox
```

### Examples
```bash
# Python version
python pst_to_mbox.py "MyEmails.pst" "converted_emails.mbox"
python pst_to_mbox.py --verbose "/path/to/outlook.pst" "/path/to/emails.mbox"

# Executable version (Windows)
pst-to-mbox.exe "C:\Users\Name\Documents\Outlook.pst" "emails.mbox"
pst-to-mbox.exe -v "C:\temp\backup.pst" "C:\temp\converted.mbox"
```

## What it does

1. **Opens your PST file** - The tool reads the PST file you exported from Outlook
2. **Extracts all emails** - It goes through every email in all folders
3. **Preserves important data** - Keeps sender, recipient, date, subject, and message content
4. **Handles attachments** - Properly includes file attachments in the conversion
5. **Creates mbox file** - Generates a standard mbox file that most email clients can import

## Importing to Webmail

Once you have the `.mbox` file, you can import it into various email services:

- **Gmail**: Use Google Takeout or third-party tools
- **Outlook.com**: Use the import feature in account settings
- **Yahoo Mail**: Use the import tool in settings
- **Thunderbird**: File > ImportExportTools > Import mbox file

## Troubleshooting

### Common Issues

1. **"libratom library is required"** - Install with: `pip install libratom`
2. **"PST file not found"** - Check the file path and make sure the file exists
3. **"Permission denied"** - Make sure you have read access to the PST file
4. **Large files taking time** - This is normal; PST files can be several GB

### Getting Help

Run the tool with `--help` to see all available options:
```bash
python pst_to_mbox.py --help
```

## Technical Details

- **Input Format**: Microsoft Outlook PST files
- **Output Format**: Standard mbox format (RFC 4155)
- **Memory Efficient**: Processes large files without loading everything into memory
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Progress Tracking**: Shows conversion progress for large files

## Building Executable

To create a standalone Windows executable:

1. **Automatic build**: Double-click `build_exe.bat`
2. **Manual build**:
   ```bash
   pip install pyinstaller libratom
   pyinstaller pst-to-mbox.spec
   ```
3. **Find executable**: `dist\pst-to-mbox.exe`

The executable includes all dependencies and works on any Windows computer without Python installation.

### Distribution
- Executable size: ~50-100MB (includes all libraries)
- No installation required on target computers
- Works on Windows 7, 8, 10, 11
- Antivirus may flag initially (normal for PyInstaller executables)

## License

MIT License

Copyright (c) 2024 PST to mbox Converter

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
