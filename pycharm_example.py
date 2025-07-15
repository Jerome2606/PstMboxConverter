#!/usr/bin/env python3
"""
PyCharm Example Script for PST to mbox Converter

This file shows how to use the converter in PyCharm.
Modify the file paths below to match your files.
"""

import os
from pathlib import Path
from pst_to_mbox import PSTToMboxConverter

def main():
    """Example of using the converter in PyCharm."""
    
    # MODIFY THESE PATHS FOR YOUR FILES
    # Use raw strings (r"") to handle Windows backslashes easily
    pst_file_path = r"C:\Users\YourName\Documents\Outlook.pst"
    output_file_path = r"C:\Users\YourName\Documents\converted_emails.mbox"
    
    # Alternative way using forward slashes (also works on Windows)
    # pst_file_path = "C:/Users/YourName/Documents/Outlook.pst"
    # output_file_path = "C:/Users/YourName/Documents/converted_emails.mbox"
    
    print("PST to mbox Converter - PyCharm Example")
    print("=" * 40)
    print(f"Input PST file: {pst_file_path}")
    print(f"Output mbox file: {output_file_path}")
    print()
    
    # Check if PST file exists
    if not os.path.exists(pst_file_path):
        print("❌ ERROR: PST file not found!")
        print(f"   Please check the path: {pst_file_path}")
        print()
        print("📝 To fix this:")
        print("   1. Update the pst_file_path variable above")
        print("   2. Make sure your PST file exists")
        print("   3. Use the full path to your PST file")
        return
    
    # Create the converter
    print("🔄 Starting conversion...")
    converter = PSTToMboxConverter(
        pst_file=pst_file_path,
        output_file=output_file_path,
        verbose=True  # Set to False for less output
    )
    
    try:
        # Run the conversion
        success = converter.convert()
        
        if success:
            print()
            print("✅ Conversion completed successfully!")
            print(f"📁 Your mbox file is ready: {output_file_path}")
            print()
            print("📧 Next steps:")
            print("   1. Use this mbox file to import into your webmail")
            print("   2. Gmail: Use Google Takeout or third-party tools")
            print("   3. Outlook.com: Use import feature in settings")
            print("   4. Yahoo: Use import tool in mail settings")
        else:
            print()
            print("❌ Conversion failed!")
            print("   Check the error messages above for details")
            
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        print()
        print("💡 Common solutions:")
        print("   - Make sure the PST file isn't open in Outlook")
        print("   - Check file permissions")
        print("   - Verify the PST file isn't corrupted")

if __name__ == "__main__":
    main()