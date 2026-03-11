# PST to mbox Converter

A Python command-line tool for converting Outlook PST files to mbox format for webmail import. Includes powerful filters, multiple output formats, attachment extraction, and more.

## Features

### Core
- ✅ Reads and parses .PST files exported from Outlook
- ✅ Converts PST email data to standard .mbox format
- ✅ Preserves email metadata (sender, recipient, date, subject)
- ✅ Preserves email body content (both text and HTML)
- ✅ Preserves CC and BCC recipients
- ✅ Handles attachments properly
- ✅ Maintains folder structure information
- ✅ Robust error handling for corrupted or invalid files
- ✅ Efficient memory usage for large PST files
- ✅ Cross-platform compatibility (Windows, macOS, Linux)

### Filters
- 📅 **Date range** — Export only emails between specific dates
- 📁 **Folder filter** — Export only specific folders (e.g. Inbox, Sent)
- 👤 **Sender filter** — Export only emails from a specific person
- 👥 **Recipient filter** — Export only emails sent to a specific person
- 🔍 **Keyword search** — Export only emails containing a word in subject or body
- 🔄 **Duplicate detection** — Skip duplicate emails automatically

### Output Formats
- 📦 **mbox** — Standard single-file format (default)
- 📄 **EML** — Individual `.eml` file per email, organized by folder
- 📂 **Split by folder** — One `.mbox` file per PST folder
- 📊 **Metadata CSV** — Export email metadata to a spreadsheet
- 📋 **Metadata JSON** — Export email metadata as JSON

### Extra Features
- 📎 **Extract attachments** — Save all attachments to a folder on disk
- 🔍 **Dry run** — Preview what would be converted without writing files
- 📈 **Stats only** — View PST statistics (folders, email counts, size) without converting
- 📊 **Progress bar** — Visual progress bar during conversion (via `tqdm`)
- 📝 **Log to file** — Save conversion log to a file

## Requirements

- Python 3.6 or higher
- libratom library (for PST file parsing)
- tqdm (optional, for progress bar)

## Installation

### Option 1: Python Script (Requires Python)

1. Install the required Python libraries:
```bash
pip install -r requirements.txt
```

2. Download the `pst_to_mbox.py` script

### Option 2: Standalone Executable (No Python Required)

1. Download all project files including build scripts
2. Double-click `build_exe.bat` to automatically create a standalone .exe file
3. Use the generated `pst-to-mbox.exe` without needing Python installed

**Manual build:**
```bash
pip install pyinstaller libratom tqdm
pyinstaller pst-to-mbox.spec
```

Find your executable in the `dist` folder.

## Usage

### Basic Conversion
```bash
# Convert entire PST to mbox
python pst_to_mbox.py input.pst output.mbox

# With verbose output
python pst_to_mbox.py -v input.pst output.mbox
```

### Filtering Emails

```bash
# Only emails from 2023 onward
python pst_to_mbox.py input.pst output.mbox --from-date 2023-01-01

# Only emails from January to March 2024
python pst_to_mbox.py input.pst output.mbox --from-date 2024-01-01 --to-date 2024-03-31

# Only emails from the Inbox folder
python pst_to_mbox.py input.pst output.mbox --folder Inbox

# Only emails from a specific sender
python pst_to_mbox.py input.pst output.mbox --sender boss@company.com

# Only emails sent to a specific person
python pst_to_mbox.py input.pst output.mbox --to-filter maria@company.com

# Only emails containing a keyword in subject or body
python pst_to_mbox.py input.pst output.mbox --search "quarterly report"

# Combine multiple filters
python pst_to_mbox.py input.pst output.mbox --folder Inbox --from-date 2024-01-01 --search "project"

# Skip duplicates
python pst_to_mbox.py input.pst output.mbox --skip-duplicates
```

### Alternative Output Formats

```bash
# Export as individual .eml files (organized in folders)
python pst_to_mbox.py input.pst output_dir/ --format eml

# Create one .mbox per PST folder
python pst_to_mbox.py input.pst output_dir/ --split-by-folder

# Export metadata to CSV (for spreadsheet analysis)
python pst_to_mbox.py input.pst output.mbox --metadata-csv report.csv

# Export metadata to JSON
python pst_to_mbox.py input.pst output.mbox --metadata-json report.json
```

### Attachments

```bash
# Extract all attachments to a directory
python pst_to_mbox.py input.pst output.mbox --extract-attachments ./attachments
```

### Inspection Without Converting

```bash
# View PST statistics (folder names, email counts, size)
python pst_to_mbox.py --stats-only input.pst

# Dry run — see what would be converted without writing any files
python pst_to_mbox.py --dry-run input.pst output.mbox

# Dry run with filters to check what matches
python pst_to_mbox.py --dry-run input.pst output.mbox --sender boss@company.com --from-date 2024-01-01
```

### Logging

```bash
# Save log to a file
python pst_to_mbox.py input.pst output.mbox --log-file conversion.log
```

### Standalone Executable (Windows)
```bash
pst-to-mbox.exe input.pst output.mbox
pst-to-mbox.exe -v input.pst output.mbox --folder Inbox --extract-attachments ./adj
```

## All Options

| Option | Description |
|---|---|
| `pst_file` | Path to the input PST file |
| `output_file` | Path to the output file or directory |
| `-v, --verbose` | Enable verbose output |
| `--from-date YYYY-MM-DD` | Only emails from this date onward |
| `--to-date YYYY-MM-DD` | Only emails up to this date |
| `--folder NAME` | Only emails from folders matching NAME |
| `--sender TEXT` | Only emails where sender matches TEXT |
| `--to-filter TEXT` | Only emails where any recipient matches TEXT |
| `--search KEYWORD` | Only emails containing KEYWORD in subject or body |
| `--skip-duplicates` | Skip duplicate emails |
| `--format {mbox,eml}` | Output format (default: mbox) |
| `--split-by-folder` | Create one .mbox per PST folder |
| `--metadata-csv FILE` | Export metadata to CSV |
| `--metadata-json FILE` | Export metadata to JSON |
| `--extract-attachments DIR` | Save attachments to a directory |
| `--dry-run` | Preview without writing files |
| `--stats-only` | Show PST stats without converting |
| `--log-file FILE` | Write log to a file |

## What it does

1. **Opens your PST file** — The tool reads the PST file you exported from Outlook
2. **Applies your filters** — Only processes emails matching your criteria (date, folder, sender, keywords)
3. **Extracts all matching emails** — Goes through every email in all (or selected) folders
4. **Preserves important data** — Keeps sender, To, CC, BCC, date, subject, and full message content
5. **Handles attachments** — Includes attachments in converted emails and optionally saves them to disk
6. **Creates output** — Generates mbox, EML files, or metadata exports as requested

## Importing to Webmail

Once you have the `.mbox` file, you can import it into various email services:

- **Gmail**: Use Google Takeout or third-party tools
- **Outlook.com**: Use the import feature in account settings
- **Yahoo Mail**: Use the import tool in settings
- **Thunderbird**: File > ImportExportTools > Import mbox file

## Troubleshooting

### Common Issues

1. **"libratom library is required"** — Install with: `pip install libratom`
2. **"PST file not found"** — Check the file path and make sure the file exists
3. **"Permission denied"** — Make sure you have read access to the PST file
4. **Large files taking time** — This is normal; PST files can be several GB. Use `--stats-only` first to check the size

### Getting Help

Run the tool with `--help` to see all available options:
```bash
python pst_to_mbox.py --help
```

## Technical Details

- **Input Format**: Microsoft Outlook PST files
- **Output Format**: mbox (RFC 4155), EML, CSV, JSON
- **Memory Efficient**: Processes large files without loading everything into memory
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Progress Tracking**: Visual progress bar for large conversions

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
