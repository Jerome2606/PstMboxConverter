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

1. Install the required Python library:
```bash
pip install libratom
```

2. Download the `pst_to_mbox.py` script

## Usage

### Basic Usage
```bash
python pst_to_mbox.py input.pst output.mbox
```

### With Verbose Output
```bash
python pst_to_mbox.py -v input.pst output.mbox
```

### Examples
```bash
# Convert a PST file to mbox format
python pst_to_mbox.py "MyEmails.pst" "converted_emails.mbox"

# Convert with detailed progress information
python pst_to_mbox.py --verbose "/path/to/outlook.pst" "/path/to/emails.mbox"

# Windows example with spaces in paths
python pst_to_mbox.py "C:\Users\Name\Documents\Outlook.pst" "emails.mbox"
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

## License

This tool is provided as-is for personal use in converting your own email files.
