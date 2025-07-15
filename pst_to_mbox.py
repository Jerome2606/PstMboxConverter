#!/usr/bin/env python3
"""
PST to mbox Converter
A command-line tool for converting Outlook PST files to mbox format for webmail import.
"""

import argparse
import os
import sys
import logging
import mailbox
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import time
from datetime import datetime
import base64

try:
    from libratom.lib.pff import PffArchive
except ImportError:
    print("Error: libratom library is required. Install it with: pip install libratom")
    sys.exit(1)

class PSTToMboxConverter:
    """Convert PST files to mbox format with progress tracking and error handling."""
    
    def __init__(self, pst_file, output_file, verbose=False):
        """
        Initialize the converter.
        
        Args:
            pst_file (str): Path to the input PST file
            output_file (str): Path to the output mbox file
            verbose (bool): Enable verbose logging
        """
        self.pst_file = Path(pst_file)
        self.output_file = Path(output_file)
        self.verbose = verbose
        self.processed_emails = 0
        self.failed_emails = 0
        self.processed_folders = 0
        self.total_size = 0
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def validate_files(self):
        """Validate input and output file paths."""
        if not self.pst_file.exists():
            raise FileNotFoundError(f"PST file not found: {self.pst_file}")
        
        if not self.pst_file.is_file():
            raise ValueError(f"PST path is not a file: {self.pst_file}")
        
        # Check file extension
        if self.pst_file.suffix.lower() not in ['.pst']:
            self.logger.warning(f"File extension is not .pst: {self.pst_file}")
        
        # Check if output directory exists, create if not
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if output file already exists
        if self.output_file.exists():
            response = input(f"Output file {self.output_file} already exists. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                raise ValueError("Operation cancelled by user")
    
    def open_pst_file(self):
        """Open and validate the PST file."""
        try:
            pst_archive = PffArchive(str(self.pst_file))
            
            self.logger.info(f"Successfully opened PST file: {self.pst_file}")
            self.logger.info(f"PST file size: {self.pst_file.stat().st_size / (1024*1024):.2f} MB")
            
            return pst_archive
        except Exception as e:
            raise RuntimeError(f"Failed to open PST file: {e}")
    
    def format_email_address(self, address, name=None):
        """Format email address with proper encoding."""
        if not address:
            return ""
        
        if name and name.strip():
            # Handle non-ASCII characters in name
            try:
                name = name.encode('ascii')
                return f"{name.decode('ascii')} <{address}>"
            except UnicodeEncodeError:
                # Use RFC 2047 encoding for non-ASCII names
                from email.header import Header
                encoded_name = Header(name, 'utf-8').encode()
                return f"{encoded_name} <{address}>"
        
        return address
    
    def extract_attachments(self, pst_message):
        """Extract attachment information from PST message."""
        attachments = []
        
        try:
            if hasattr(pst_message, 'number_of_attachments'):
                attachment_count = pst_message.number_of_attachments
                for i in range(attachment_count):
                    attachment = pst_message.get_attachment(i)
                    if attachment:
                        att_info = {
                            'filename': getattr(attachment, 'name', f"attachment_{i}") or f"attachment_{i}",
                            'size': getattr(attachment, 'size', 0),
                            'data': getattr(attachment, 'data', None)
                        }
                        attachments.append(att_info)
                        self.logger.debug(f"Found attachment: {att_info['filename']} ({att_info['size']} bytes)")
        except Exception as e:
            self.logger.warning(f"Failed to extract attachments: {e}")
        
        return attachments
    
    def convert_pst_message_to_email(self, pst_message, folder_path=""):
        """Convert a PST message to an email.message.Message object."""
        try:
            # Body content
            body_text = getattr(pst_message, 'plain_text_body', '') or ""
            body_html = getattr(pst_message, 'html_body', '') or ""
            
            # Extract attachments
            attachments = self.extract_attachments(pst_message)
            
            # Create appropriate message structure
            if attachments:
                # Message with attachments - use multipart/mixed
                msg = MIMEMultipart('mixed')
                
                # Add text content first
                if body_html and body_text:
                    # Both text and HTML - create alternative part
                    alt_part = MIMEMultipart('alternative')
                    alt_part.attach(MIMEText(body_text, 'plain', 'utf-8'))
                    alt_part.attach(MIMEText(body_html, 'html', 'utf-8'))
                    msg.attach(alt_part)
                elif body_html:
                    msg.attach(MIMEText(body_html, 'html', 'utf-8'))
                else:
                    msg.attach(MIMEText(body_text or "(No content)", 'plain', 'utf-8'))
                
                # Add attachments
                for att in attachments:
                    if att['data']:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(att['data'])
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{att["filename"]}"'
                        )
                        msg.attach(part)
            
            elif body_html and body_text:
                # Both text and HTML - use multipart/alternative
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            
            elif body_html:
                # HTML only
                msg = MIMEText(body_html, 'html', 'utf-8')
            
            else:
                # Plain text only
                msg = MIMEText(body_text or "(No content)", 'plain', 'utf-8')
            
            # Add headers
            subject = getattr(pst_message, 'subject', '') or "(No Subject)"
            msg['Subject'] = subject
            
            # Sender information
            sender_name = getattr(pst_message, 'sender_name', '')
            sender_email = getattr(pst_message, 'sender_email_address', '')
            if sender_email:
                msg['From'] = self.format_email_address(sender_email, sender_name)
            
            # Recipients
            recipients = []
            if hasattr(pst_message, 'recipients') and pst_message.recipients:
                for recipient in pst_message.recipients:
                    recipient_email = getattr(recipient, 'email_address', '')
                    recipient_name = getattr(recipient, 'name', '')
                    if recipient_email:
                        recipients.append(self.format_email_address(recipient_email, recipient_name))
            
            if recipients:
                msg['To'] = ', '.join(recipients)
            
            # Date
            delivery_time = getattr(pst_message, 'delivery_time', None)
            if delivery_time:
                try:
                    msg['Date'] = delivery_time.strftime('%a, %d %b %Y %H:%M:%S %z')
                except:
                    # Fallback to current time if date formatting fails
                    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Message ID
            transport_headers = getattr(pst_message, 'transport_headers', '')
            if transport_headers and 'Message-ID:' in transport_headers:
                try:
                    msg_id = transport_headers.split('Message-ID:')[1].split('\n')[0].strip()
                    msg['Message-ID'] = msg_id
                except:
                    pass
            
            # Add folder information as custom header
            if folder_path:
                msg['X-Folder'] = folder_path
            
            return msg
            
        except Exception as e:
            self.logger.error(f"Failed to convert PST message: {e}")
            raise
    
    def process_messages(self, pst_archive, mbox_file):
        """Process all messages in the PST archive."""
        try:
            self.logger.info("Processing messages from PST archive...")
            
            # Use libratom's messages() generator to iterate through all messages
            message_count = 0
            for pst_message in pst_archive.messages():
                try:
                    # Get folder path if available
                    folder_path = "Unknown"
                    if hasattr(pst_message, 'folder') and pst_message.folder:
                        folder_path = getattr(pst_message.folder, 'name', 'Unknown')
                    
                    email_msg = self.convert_pst_message_to_email(pst_message, folder_path)
                    mbox_file.add(email_msg)
                    self.processed_emails += 1
                    message_count += 1
                    
                    if self.processed_emails % 100 == 0:
                        self.logger.info(f"Processed {self.processed_emails} emails...")
                
                except Exception as e:
                    self.failed_emails += 1
                    self.logger.error(f"Failed to process message {message_count}: {e}")
            
            self.logger.info(f"Finished processing {message_count} messages")
        
        except Exception as e:
            self.logger.error(f"Failed to process messages: {e}")
    
    def convert(self):
        """Main conversion process."""
        start_time = time.time()
        
        try:
            self.logger.info("Starting PST to mbox conversion...")
            
            # Validate files
            self.validate_files()
            
            # Open PST file
            pst_archive = self.open_pst_file()
            
            # Create mbox file
            mbox_file = mailbox.mbox(str(self.output_file))
            mbox_file.lock()
            
            try:
                # Process all messages
                self.process_messages(pst_archive, mbox_file)
                
                # Flush and close mbox file
                mbox_file.flush()
                
            finally:
                mbox_file.unlock()
                mbox_file.close()
            
            # Calculate statistics
            end_time = time.time()
            duration = end_time - start_time
            output_size = self.output_file.stat().st_size if self.output_file.exists() else 0
            
            # Print final statistics
            self.logger.info("\n" + "="*50)
            self.logger.info("CONVERSION COMPLETED SUCCESSFULLY")
            self.logger.info("="*50)
            self.logger.info(f"Input file: {self.pst_file}")
            self.logger.info(f"Output file: {self.output_file}")
            self.logger.info(f"Processed emails: {self.processed_emails}")
            self.logger.info(f"Failed emails: {self.failed_emails}")
            self.logger.info(f"Output file size: {output_size / (1024*1024):.2f} MB")
            self.logger.info(f"Processing time: {duration:.2f} seconds")
            
            if self.processed_emails > 0:
                self.logger.info(f"Average speed: {self.processed_emails / duration:.1f} emails/second")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Outlook PST files to mbox format for webmail import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pst output.mbox
  %(prog)s -v /path/to/outlook.pst /path/to/emails.mbox
  %(prog)s --verbose "C:\\Users\\Name\\Documents\\Outlook.pst" "emails.mbox"
        """
    )
    
    parser.add_argument(
        'pst_file',
        help='Path to the input PST file'
    )
    
    parser.add_argument(
        'output_file',
        help='Path to the output mbox file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Create converter and run conversion
    converter = PSTToMboxConverter(args.pst_file, args.output_file, args.verbose)
    
    try:
        success = converter.convert()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
