#!/usr/bin/env python3
"""
Demo script showing how to use the PST to mbox converter.
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pst_to_mbox import PSTToMboxConverter

def demo_converter():
    """Demonstrate the PST to mbox converter functionality."""
    print("PST to mbox Converter Demo")
    print("=" * 30)
    
    # Example usage
    print("\n1. Basic Usage:")
    print("   python pst_to_mbox.py input.pst output.mbox")
    
    print("\n2. With verbose output:")
    print("   python pst_to_mbox.py -v input.pst output.mbox")
    
    print("\n3. Example with real paths:")
    print('   python pst_to_mbox.py "C:\\Users\\Name\\Documents\\Outlook.pst" "emails.mbox"')
    
    print("\n4. What happens during conversion:")
    print("   ✓ Opens and validates your PST file")
    print("   ✓ Reads all emails from all folders")
    print("   ✓ Preserves sender, recipient, date, subject")
    print("   ✓ Keeps both text and HTML email content")
    print("   ✓ Handles file attachments")
    print("   ✓ Creates standard mbox file for webmail import")
    
    print("\n5. Supported webmail services:")
    print("   • Gmail (via Google Takeout or third-party tools)")
    print("   • Outlook.com (import feature)")
    print("   • Yahoo Mail (import tool)")
    print("   • Thunderbird (ImportExportTools)")
    
    print("\n6. To use with your PST file:")
    print("   a. Export your emails from Outlook as a .pst file")
    print("   b. Run: python pst_to_mbox.py your-file.pst converted.mbox")
    print("   c. Import the .mbox file into your webmail service")
    
    print("\nConverter is ready to use!")
    print("Run 'python pst_to_mbox.py --help' for detailed options.")

if __name__ == "__main__":
    demo_converter()