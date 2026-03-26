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
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import time
from datetime import datetime
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
    
    def __init__(self, pst_file, output_file, verbose=False, split_by_folder=True):
        """
        Initialize the converter.
        
        Args:
            pst_file (str): Path to the input PST file
            output_file (str): Path to the output mbox file
            verbose (bool): Enable verbose logging
            split_by_folder (bool): Create one mbox per PST folder when True
        """
        self.pst_file = Path(pst_file)
        self.output_file = Path(output_file)
        self.verbose = verbose
        self.split_by_folder = split_by_folder
        self.processed_emails = 0
        self.failed_emails = 0
        self.processed_folders = 0
        self.total_size = 0
        self.output_directory = None
        self.generated_mbox_files = set()

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
        
        if self.split_by_folder:
            self.output_directory = self.get_output_directory()
            self.output_directory.mkdir(parents=True, exist_ok=True)
        else:
            # Check if output directory exists, create if not
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if output file already exists
            if self.output_file.exists():
                response = input(f"Output file {self.output_file} already exists. Overwrite? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    raise ValueError("Operation cancelled by user")

    def get_output_directory(self):
        """Return the directory where split mbox files should be stored."""
        if self.output_file.suffix.lower() == '.mbox':
            return self.output_file.parent / f"{self.output_file.stem}_mboxes"
        return self.output_file

    def sanitize_path_component(self, value):
        """Sanitize folder names for filesystem-safe paths."""
        cleaned = re.sub(r'[\\/:*?"<>|]+', '_', str(value or "Unknown").strip())
        cleaned = cleaned.strip('. ')
        return cleaned or "Unknown"

    def build_folder_path(self, pst_archive, folder):
        """Build a stable folder path from the PST tree."""
        folder_id = self.safe_get_attr(folder, 'identifier', None)
        folder_name = self.safe_get_attr(folder, 'name', 'Unknown') or "Unknown"

        if folder_id is None:
            return folder_name

        tree = pst_archive.tree
        node = tree.get_node(folder_id)
        if node is None:
            return folder_name

        parts = []
        while node is not None:
            tag = str(node.tag or "").strip()
            if tag and tag != "root" and not tag.startswith("Message ID:"):
                parts.append(tag)
            node = tree.parent(node.identifier)

        parts.reverse()
        return "/".join(parts) if parts else folder_name

    def get_mbox_path_for_folder(self, folder_path):
        """Convert a PST folder path into an output mbox file path."""
        parts = [self.sanitize_path_component(p) for p in folder_path.split('/') if p.strip()]
        if not parts:
            parts = ["Unknown"]
        parent = self.output_directory.joinpath(*parts[:-1]) if len(parts) > 1 else self.output_directory
        parent.mkdir(parents=True, exist_ok=True)
        return parent / f"{parts[-1]}.mbox"
    
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
        from_item = from_item if isinstance(from_item, str) else ""
        
        sender_name = "Unknown Sender"
        sender_email = "Unknown Email"
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
            timestamp = str(date_item)

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
            subject = getattr(pst_message, 'subject', '') or "(No Subject)"

            msg['Subject'] = subject

            transport_headers = self.safe_get_attr(pst_message, 'transport_headers', '') or ""
            
            # start of merge-try
            hih = HeaderItemsHelper(transport_headers)
            sender_name, sender_email, header_date = self.extract_from_and_time_values(hih)

            # Normalize delivery time to datetime; some PST headers provide Date as string.
            delivery_time = None
            if header_date:
                try:
                    delivery_time = email.utils.parsedate_to_datetime(str(header_date).strip())
                except Exception:
                    delivery_time = None

            if delivery_time is None:
                pst_delivery_time = self.safe_get_attr(pst_message, 'delivery_time', None)
                if isinstance(pst_delivery_time, datetime):
                    delivery_time = pst_delivery_time
                elif isinstance(pst_delivery_time, str) and pst_delivery_time.strip():
                    try:
                        delivery_time = email.utils.parsedate_to_datetime(pst_delivery_time.strip())
                    except Exception:
                        delivery_time = None

            if delivery_time is None:
                delivery_time = datetime.now()
            
            if (sender_email == "Unknown Email"):
                item_from = hih.get_header_item('From') #get FROM item to check, what went wrong
                #print(f'??????????????? From value: >>>{item_from[1] if item_from[0] else "Unknown From"}<<<')
                #self.result_collector_list.append(f'--------------;>>>{item_from[1] if item_from[0] else "Unknown From"}<<<;;')
                if item_from[0]:
                    self.logger.info(f"Couldn't deal with below \"FROM:\" item data in email transport header:\n{item_from[1]}")
                else:
                    self.logger.info(f"Couldn't find \"FROM:\" item in email transport header!")                    
            else:
                msg['From'] = self.format_email_address(sender_email, sender_name)
                # Set mbox unix from line for correct sender display
                '''
                delivery_time = getattr(pst_message, 'delivery_time', None)
                #delivery_time already set by function self.extract_from_and_time_values
                '''
                if not delivery_time and transport_headers:
                    date_match = re.search(r'^Date:\s*(.+)', transport_headers, re.MULTILINE | re.IGNORECASE)
                    if date_match:
                        try:
                            delivery_time = email.utils.parsedate_to_datetime(date_match.group(1).strip())
                        except Exception:
                            delivery_time = None
                if delivery_time:
                    unix_date = delivery_time.strftime('%a %b %d %H:%M:%S %Y')
                else:
                    unix_date = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
                msg.set_unixfrom(f'From {sender_email} {unix_date}')
            
            # Recipients
            recipients = []
            try:
                if hasattr(pst_message, 'recipients') and pst_message.recipients:
                    for recipient in pst_message.recipients:
                        recipient_email = self.safe_get_attr(recipient, 'email_address', '')
                        recipient_name = self.safe_get_attr(recipient, 'name', '')
                        if recipient_email:
                            recipients.append(self.format_email_address(recipient_email, recipient_name))
            except (SystemError, ValueError, UnicodeDecodeError, OverflowError) as e:
                self.logger.debug(f"Failed to read recipients: {e}")
            
            if recipients:
                msg['To'] = ', '.join(recipients)
            

            msg['Date'] = email.utils.format_datetime(delivery_time)
            ''' date handling seems to be done above already
            # Date
            delivery_time = self.safe_get_attr(pst_message, 'delivery_time', None)
            if not delivery_time and transport_headers:
                date_match = re.search(r'^Date:\s*(.+)', transport_headers, re.MULTILINE | re.IGNORECASE)
                if date_match:
                    try:
                        delivery_time = email.utils.parsedate_to_datetime(date_match.group(1).strip())
                    except Exception:
                        delivery_time = None

            if delivery_time:
                try:
                    msg['Date'] = delivery_time.strftime('%a, %d %b %Y %H:%M:%S %z')
                except Exception:
                    msg['Date'] = delivery_time.isoformat()
            else:
                msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            '''

            # Message ID
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
    
    def process_messages_single_mbox(self, pst_archive, mbox_file):
        """Process all messages in the PST archive into one mbox file."""
        try:
            self.logger.info("Processing messages from PST archive...")
            
            # Use libratom's messages() generator to iterate through all messages
            message_count = 0
            for pst_message in pst_archive.messages():
                '''
                if message_count == 0:
                    print(f'Object attributes: {dir(pst_message)}')
                    header_items = self.header_to_dict(pst_message.transport_headers)
                    for k in header_items.keys():
                        print(f"Key: {k} --- Value: {header_items[k]}")
                    print(f'transport_headers: {pst_message.transport_headers} ')

                '''

                try:
                    # Get folder path if available
                    folder_path = "Unknown"
                    try:
                        if hasattr(pst_message, 'folder') and pst_message.folder:
                            folder_path = self.safe_get_attr(pst_message.folder, 'name', 'Unknown')
                    except (SystemError, ValueError, UnicodeDecodeError, OverflowError):
                        pass
                    
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

    def process_messages_split_by_folder(self, pst_archive):
        """Process PST messages and write one mbox file per PST folder."""
        mbox_files = {}
        seen_message_ids = set()
        message_count = 0

        try:
            self.logger.info("Processing messages by PST folder...")
            self.logger.info(f"Output directory: {self.output_directory}")

            for folder in pst_archive.folders():
                sub_message_count = self.safe_get_attr(folder, 'number_of_sub_messages', 0) or 0
                if sub_message_count <= 0:
                    continue

                folder_path = self.build_folder_path(pst_archive, folder)
                mbox_path = self.get_mbox_path_for_folder(folder_path)
                mbox_key = str(mbox_path)

                if mbox_key not in mbox_files:
                    folder_mbox = mailbox.mbox(mbox_key)
                    folder_mbox.lock()
                    mbox_files[mbox_key] = folder_mbox
                    self.generated_mbox_files.add(mbox_key)
                    self.processed_folders += 1

                for pst_message in folder.sub_messages:
                    try:
                        msg_id = self.safe_get_attr(pst_message, 'identifier', None)
                        if msg_id is not None:
                            seen_message_ids.add(msg_id)

                        email_msg = self.convert_pst_message_to_email(pst_message, folder_path)
                        mbox_files[mbox_key].add(email_msg)
                        self.processed_emails += 1
                        message_count += 1

                        if self.processed_emails % 100 == 0:
                            self.logger.info(f"Processed {self.processed_emails} emails...")

                    except Exception as e:
                        self.failed_emails += 1
                        self.logger.error(f"Failed to process message {message_count}: {e}")

            # Fallback bucket for any messages not reached through folder traversal.
            fallback_folder = "Uncategorized"
            fallback_mbox_path = self.get_mbox_path_for_folder(fallback_folder)
            fallback_key = str(fallback_mbox_path)
            fallback_used = False

            for pst_message in pst_archive.messages():
                try:
                    msg_id = self.safe_get_attr(pst_message, 'identifier', None)
                    if msg_id is not None and msg_id in seen_message_ids:
                        continue

                    if fallback_key not in mbox_files:
                        fallback_mbox = mailbox.mbox(fallback_key)
                        fallback_mbox.lock()
                        mbox_files[fallback_key] = fallback_mbox
                        self.generated_mbox_files.add(fallback_key)
                        self.processed_folders += 1

                    email_msg = self.convert_pst_message_to_email(pst_message, fallback_folder)
                    mbox_files[fallback_key].add(email_msg)
                    self.processed_emails += 1
                    message_count += 1
                    fallback_used = True

                except Exception as e:
                    self.failed_emails += 1
                    self.logger.error(f"Failed to process fallback message {message_count}: {e}")

            if fallback_used:
                self.logger.info("Some messages were exported to fallback folder: Uncategorized")

            self.logger.info(f"Finished processing {message_count} messages")

        finally:
            for folder_mbox in mbox_files.values():
                try:
                    folder_mbox.flush()
                finally:
                    folder_mbox.unlock()
                    folder_mbox.close()
    
    def convert(self):
        """Main conversion process."""
        start_time = time.time()
        
        try:
            self.logger.info("Starting PST to mbox conversion...")
            
            # Validate files
            self.validate_files()
            
            # Open PST file
            pst_archive = self.open_pst_file()

            if self.split_by_folder:
                self.process_messages_split_by_folder(pst_archive)
            else:
                # Create mbox file
                mbox_file = mailbox.mbox(str(self.output_file))
                mbox_file.lock()
                
                try:
                    # Process all messages
                    self.process_messages_single_mbox(pst_archive, mbox_file)
                    
                    # Flush and close mbox file
                    mbox_file.flush()
                    
                finally:
                    mbox_file.unlock()
                    mbox_file.close()
            
            # Calculate statistics
            end_time = time.time()
            duration = end_time - start_time
            if self.split_by_folder:
                output_size = 0
                for mbox_path in self.generated_mbox_files:
                    try:
                        output_size += Path(mbox_path).stat().st_size
                    except FileNotFoundError:
                        pass
            else:
                output_size = self.output_file.stat().st_size if self.output_file.exists() else 0
            
            # Print final statistics
            self.logger.info("\n" + "="*50)
            self.logger.info("CONVERSION COMPLETED SUCCESSFULLY")
            self.logger.info("="*50)
            self.logger.info(f"Input file: {self.pst_file}")
            if self.split_by_folder:
                self.logger.info(f"Output directory: {self.output_directory}")
                self.logger.info(f"Generated mbox files: {len(self.generated_mbox_files)}")
            else:
                self.logger.info(f"Output file: {self.output_file}")
            self.logger.info(f"Processed emails: {self.processed_emails}")
            self.logger.info(f"Failed emails: {self.failed_emails}")
            self.logger.info(f"Processed folders: {self.processed_folders}")
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
        '--single-mbox',
        action='store_true',
        help='Store all messages in one output mbox file (legacy behavior)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Create converter and run conversion
    converter = PSTToMboxConverter(
        args.pst_file,
        args.output_file,
        args.verbose,
        split_by_folder=not args.single_mbox
    )
    
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
