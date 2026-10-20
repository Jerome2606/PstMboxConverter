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
import email.utils
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import time
from datetime import datetime, timezone
import base64

import re
from email.header import decode_header #added rjs

from header_items_helper import HeaderItemsHelper

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
        self.skipped_items = 0
        self.total_size = 0

        #self.result_collector_list = []
        self.attachments_found = 0
        self.attachments_extracted = 0
        self.attachment_bytes = 0
        
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
                if attachment_count > 0:
                    self.logger.debug(f"Message has {attachment_count} attachment(s)")
                    self.attachments_found += attachment_count
                for i in range(attachment_count):
                    try:
                        attachment = pst_message.get_attachment(i)
                        if attachment:
                            filename = self.safe_get_attr(attachment, 'name', f"attachment_{i}") or f"attachment_{i}"
                            size = self.safe_get_attr(attachment, 'size', 0) or 0

                            # Try multiple methods to get attachment data
                            data = None

                            # Method 1: Try read_buffer if available (libpff native method)
                            if data is None and hasattr(attachment, 'read_buffer') and size > 0:
                                try:
                                    data = attachment.read_buffer(size)
                                except Exception as e:
                                    self.logger.debug(f"read_buffer failed for '{filename}': {e}")

                            # Method 2: Try get_data if available
                            if data is None and hasattr(attachment, 'get_data'):
                                try:
                                    data = attachment.get_data()
                                except Exception as e:
                                    self.logger.debug(f"get_data failed for '{filename}': {e}")

                            # Method 3: Try data property
                            if data is None:
                                data = self.safe_get_attr(attachment, 'data', None)

                            actual_size = len(data) if data else 0
                            att_info = {
                                'filename': filename,
                                'size': size,
                                'data': data
                            }
                            attachments.append(att_info)
                            if actual_size == 0 and size > 0:
                                self.logger.warning(f"Attachment '{filename}' reported size {size} but data is empty")
                            else:
                                self.attachments_extracted += 1
                                self.attachment_bytes += actual_size
                                self.logger.debug(f"Found attachment: {filename} ({actual_size} bytes)")
                    except (SystemError, ValueError, UnicodeDecodeError, OverflowError) as e:
                        self.logger.warning(f"Failed to extract attachment {i}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to extract attachments: {e}")

        return attachments
    #-----------------------------------------------------------------------------------------------------------------------------------
    
    def extract_from_and_time_values(self, header_i_h):        
        """trying to xtract sender name, email address and timestamp from transport header."""
        
        from_item_exists, from_item = header_i_h.get_header_item('From')
        date_item_exists, date_item = header_i_h.get_header_item('Date')
        
        sender_name = "Unknown Sender"
        sender_email = "Unknown Email"
        from_item = from_item or ""
        if from_item_exists:
            sender_re = re.search(r"(.+?)\n? <(.+?)>", from_item)
            if sender_re:
                sender_name = sender_re.group(1).strip('"')
                sender_email = sender_re.group(2)
        if sender_email == "Unknown Email":
            sender_re = re.search(r"(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)", from_item)
            if sender_re:
                sender_email = sender_re.group(1)
                if sender_name == "Unknown Sender":
                    sender_name = sender_email

        # Extract the timestamp from the transport header
        timestamp ='Mon, 01 Jan 1900 00:00:00 GMT' # Default timestamp if not found
        if date_item_exists:
            timestamp = date_item

        return sender_name, sender_email, timestamp   
    
    def process_from_info(self, item_from):
        """Process 'From' header item to extract name and email."""
        print(item_from)
        left_pos = item_from.rfind('<')
        at_pos = item_from.rfind('@')
        right_pos = item_from.rfind('>')
        return_value = (None, None )
        if left_pos != -1 and at_pos != -1 and right_pos != -1:
            name = item_from[:left_pos].strip()
            email = item_from[left_pos + 1:right_pos].strip()
            return_value = (name, email)  
        print(f"Processed From info: {return_value}")
        return return_value
    
        
    def safe_get_attr(self, obj, attr, default=''):
        """Safely get an attribute, catching Unicode decode errors from corrupted PST data."""
        try:
            value = getattr(obj, attr, default)
            return value if value is not None else default
        except (SystemError, ValueError, UnicodeDecodeError, OverflowError) as e:
            self.logger.debug(f"Failed to read attribute '{attr}': {e}")
            return default

    PST_PROPERTY_TAGS = (0x001A, 0x0042, 0x0065, 0x0C1A, 0x0C1E, 0x0C1F, 0x0E02, 0x0E03, 0x0E04,
                         0x1035, 0x1039, 0x1042, 0x5D01)

    def read_pst_properties(self, pst_message):
        """Read selected string properties from the message's first record set, keyed by property tag."""
        props = {}
        try:
            for entry in pst_message.record_sets[0].entries:
                if entry.entry_type not in self.PST_PROPERTY_TAGS:
                    continue
                try:
                    data = entry.data
                    if not data:
                        continue
                    if entry.value_type == 0x1F:
                        props[entry.entry_type] = data.decode('utf-16-le', 'replace').rstrip('\0').strip()
                    elif entry.value_type == 0x1E:
                        props[entry.entry_type] = data.decode('latin-1').rstrip('\0').strip()
                except (SystemError, ValueError, UnicodeDecodeError, OverflowError) as e:
                    self.logger.debug(f"Failed to read property {entry.entry_type:#06x}: {e}")
        except (IndexError, SystemError, ValueError, OverflowError, AttributeError) as e:
            self.logger.debug(f"Failed to read PST properties: {e}")
        return props

    @staticmethod
    def first_address(*candidates):
        """Return the first candidate that looks like an SMTP address (Exchange DNs are skipped)."""
        for candidate in candidates:
            if candidate and re.fullmatch(r"[^\s<>@]+@[^\s<>@]+", candidate.strip("'\" ")):
                return candidate.strip("'\" ")
        return None

    def format_display_recipients(self, display_text):
        """Turn a PST display string such as "A; 'b@x.com'; C" into a header value."""
        if not display_text:
            return ""
        recipients = []
        for part in display_text.split(';'):
            part = part.strip()
            if not part:
                continue
            address = self.first_address(part)
            if address:
                recipients.append(address)
            else:
                recipients.append(self.format_email_address("undisclosed@invalid", part.strip("'\"")))
        return ', '.join(recipients)

    def convert_pst_message_to_email(self, pst_message, folder_path=""):
        """Convert a PST message to an email.message.Message object."""
        try:
            # Body content - use safe accessor to handle corrupted strings
            body_text = self.safe_get_attr(pst_message, 'plain_text_body', '') or ""
            body_html = self.safe_get_attr(pst_message, 'html_body', '') or ""
            
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
            msg['Subject'] = self.safe_get_attr(pst_message, 'subject', '') or "(No Subject)"

            transport_headers = self.safe_get_attr(pst_message, 'transport_headers', '') or ""
            hih = HeaderItemsHelper(transport_headers)
            props = self.read_pst_properties(pst_message)

            # From: transport header first, then the sender properties stored in the PST
            sender_name, sender_email, date_header = self.extract_from_and_time_values(hih)
            if sender_email == "Unknown Email":
                sender_name = props.get(0x0C1A) or props.get(0x0042) or ""
                sender_email = self.first_address(props.get(0x5D01), props.get(0x0C1F), props.get(0x0065))
                if not sender_email:
                    sender_email = "unknown@invalid"
                    self.logger.debug("No sender address found in transport header or PST properties")
            msg['From'] = self.format_email_address(sender_email, sender_name)

            # Date: transport header first, then submit/delivery time (PST times are UTC)
            delivery_time = None
            if hih.contains_header_item('Date'):
                try:
                    delivery_time = email.utils.parsedate_to_datetime(date_header)
                except (TypeError, ValueError):
                    delivery_time = None
            if not delivery_time:
                delivery_time = (self.safe_get_attr(pst_message, 'client_submit_time', None)
                                 or self.safe_get_attr(pst_message, 'delivery_time', None))
                if delivery_time and delivery_time.tzinfo is None:
                    delivery_time = delivery_time.replace(tzinfo=timezone.utc)
            if delivery_time:
                msg['Date'] = email.utils.format_datetime(delivery_time)
                unix_date = delivery_time.strftime('%a %b %d %H:%M:%S %Y')
            else:
                unix_date = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
            # Set mbox unix from line for correct sender display
            msg.set_unixfrom(f'From {sender_email} {unix_date}')

            # To / Cc / Bcc: transport header first, then the display strings stored in the PST
            for header, tag in (('To', 0x0E04), ('Cc', 0x0E03), ('Bcc', 0x0E02)):
                found, value = hih.get_header_item(header)
                if found and value:
                    msg[header] = value
                else:
                    recipients = self.format_display_recipients(props.get(tag))
                    if recipients:
                        msg[header] = recipients

            # Threading headers
            for header, tag in (('Message-ID', 0x1035), ('In-Reply-To', 0x1042), ('References', 0x1039),
                                ('Reply-To', None)):
                found, value = hih.get_header_item(header)
                value = value if found and value else (props.get(tag) if tag else None)
                if value:
                    msg[header] = value
            if 'Message-ID' not in msg:
                msg['Message-ID'] = f"<pst-{self.safe_get_attr(pst_message, 'identifier', id(pst_message))}@pst-to-mbox.invalid>"

            # Add folder information as custom header
            if folder_path:
                msg['X-Folder'] = folder_path
            
            return msg
            
        except Exception as e:
            self.logger.error(f"Failed to convert PST message: {e}")
            raise
    
    MAIL_CLASS_PREFIXES = ("IPM.NOTE", "IPM.POST", "IPM.SCHEDULE", "REPORT")

    def iter_messages(self, pst_archive):
        """Yield (folder path, message) for every message, walking the folder tree depth first."""
        stack = [("", next(pst_archive.folders()))]
        while stack:
            path, folder = stack.pop()
            name = self.safe_get_attr(folder, 'name', '') or ''
            folder_path = f"{path}/{name}" if name else path
            try:
                for message in folder.sub_messages:
                    yield folder_path.lstrip('/') or "Unknown", message
                self.processed_folders += 1
                stack.extend((folder_path, sub) for sub in reversed(list(folder.sub_folders)))
            except OSError as e:
                self.logger.debug(f"Failed to read folder '{folder_path}': {e}")

    def process_messages(self, pst_archive, mbox_file):
        """Process all messages in the PST archive."""
        try:
            self.logger.info("Processing messages from PST archive...")
            
            message_count = 0
            for folder_path, pst_message in self.iter_messages(pst_archive):
                try:
                    # Contacts, calendar entries etc. are not mail and can't be represented in mbox
                    message_class = self.read_pst_properties(pst_message).get(0x001A, "IPM.Note")
                    if not message_class.upper().startswith(self.MAIL_CLASS_PREFIXES):
                        self.skipped_items += 1
                        self.logger.debug(f"Skipping non-mail item ({message_class}) in {folder_path}")
                        continue

                    email_msg = self.convert_pst_message_to_email(pst_message, folder_path)
                    mbox_file.add(email_msg)
                    self.processed_emails += 1
                    message_count += 1
                    
                    if self.processed_emails % 100 == 0:
                        self.logger.info(f"Processed {self.processed_emails} emails...")
                
                except Exception as e:
                    self.failed_emails += 1
                    self.logger.error(f"Failed to process message {message_count} in {folder_path}: {e}")
            
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
            self.logger.info(f"Skipped non-mail items: {self.skipped_items}")
            self.logger.info(f"Attachments found: {self.attachments_found}")
            self.logger.info(f"Attachments extracted: {self.attachments_extracted} ({self.attachment_bytes / (1024*1024):.2f} MB)")
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
        ''' required during development only
        # adjust path accordingly
        with open('D:\Python\Python310\gitProjects\PstMboxConverter\\results_file.txt', mode="w", encoding="utf-8") as f:
            for line in converter.result_collector_list:
                #print(line)
                f.write(f"{line}\n")
        '''
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
