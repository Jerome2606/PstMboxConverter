#!/usr/bin/env python3
"""
PST to mbox Converter
A command-line tool for converting Outlook PST files to mbox format for webmail import.
Supports filters, multiple output formats, attachment extraction, and more.
"""

import argparse
import csv
import hashlib
import json
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

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

PffArchive = None

def _load_libratom():
    global PffArchive
    if PffArchive is None:
        try:
            from libratom.lib.pff import PffArchive as _PffArchive
            PffArchive = _PffArchive
        except ImportError:
            print("Error: libratom library is required. Install it with: pip install libratom")
            sys.exit(1)


class PSTToMboxConverter:
    """Convert PST files to mbox format with progress tracking and error handling."""

    def __init__(self, pst_file, output_file=None, verbose=False,
                 from_date=None, to_date=None, folder_filter=None,
                 sender_filter=None, recipient_filter=None, search_keyword=None,
                 output_format='mbox', split_by_folder=False,
                 metadata_csv=None, metadata_json=None,
                 extract_attachments_dir=None,
                 dry_run=False, stats_only=False,
                 skip_duplicates=False, log_file=None):
        self.pst_file = Path(pst_file)
        self.output_file = Path(output_file) if output_file else None
        self.verbose = verbose

        # Filters
        self.from_date = from_date
        self.to_date = to_date
        self.folder_filter = folder_filter.lower() if folder_filter else None
        self.sender_filter = sender_filter.lower() if sender_filter else None
        self.recipient_filter = recipient_filter.lower() if recipient_filter else None
        self.search_keyword = search_keyword.lower() if search_keyword else None

        # Output options
        self.output_format = output_format
        self.split_by_folder = split_by_folder
        self.metadata_csv = Path(metadata_csv) if metadata_csv else None
        self.metadata_json = Path(metadata_json) if metadata_json else None
        self.extract_attachments_dir = Path(extract_attachments_dir) if extract_attachments_dir else None

        # Modes
        self.dry_run = dry_run
        self.stats_only = stats_only

        # Duplicate detection
        self.skip_duplicates = skip_duplicates
        self._seen_hashes = set()

        # Log file
        self.log_file = Path(log_file) if log_file else None

        # Stats
        self.processed_emails = 0
        self.skipped_emails = 0
        self.skipped_duplicates = 0
        self.failed_emails = 0
        self.processed_folders = 0
        self.total_size = 0
        self.attachments_found = 0
        self.attachments_extracted = 0
        self.attachment_bytes = 0
        self.folder_counts = {}
        self.metadata_records = []

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        log_level = logging.DEBUG if self.verbose else logging.INFO
        handlers = [logging.StreamHandler(sys.stdout)]

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(str(self.log_file), encoding='utf-8'))

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)

    # ── Validation ──────────────────────────────────────────────

    def validate_files(self):
        if not self.pst_file.exists():
            raise FileNotFoundError(f"PST file not found: {self.pst_file}")
        if not self.pst_file.is_file():
            raise ValueError(f"PST path is not a file: {self.pst_file}")
        if self.pst_file.suffix.lower() != '.pst':
            self.logger.warning(f"File extension is not .pst: {self.pst_file}")

        if self.stats_only or self.dry_run:
            return

        if self.output_file:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            if self.output_format == 'eml' or self.split_by_folder:
                self.output_file.mkdir(parents=True, exist_ok=True)
            elif self.output_file.exists():
                response = input(f"Output file {self.output_file} already exists. Overwrite? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    raise ValueError("Operation cancelled by user")

        if self.extract_attachments_dir:
            self.extract_attachments_dir.mkdir(parents=True, exist_ok=True)
        if self.metadata_csv:
            self.metadata_csv.parent.mkdir(parents=True, exist_ok=True)
        if self.metadata_json:
            self.metadata_json.parent.mkdir(parents=True, exist_ok=True)

    def open_pst_file(self):
        _load_libratom()
        try:
            pst_archive = PffArchive(str(self.pst_file))
            self.logger.info(f"Successfully opened PST file: {self.pst_file}")
            self.logger.info(f"PST file size: {self.pst_file.stat().st_size / (1024*1024):.2f} MB")
            return pst_archive
        except Exception as e:
            raise RuntimeError(f"Failed to open PST file: {e}")

    # ── Helpers ─────────────────────────────────────────────────

    def safe_get_attr(self, obj, attr, default=''):
        try:
            value = getattr(obj, attr, default)
            return value if value is not None else default
        except Exception as e:
            self.logger.debug(f"Failed to read attribute '{attr}': {e}")
            return default

    def format_email_address(self, address, name=None):
        if not address:
            return ""
        if name and name.strip():
            try:
                name.encode('ascii')
                return f"{name} <{address}>"
            except UnicodeEncodeError:
                from email.header import Header
                encoded_name = Header(name, 'utf-8').encode()
                return f"{encoded_name} <{address}>"
        return address

    def _get_delivery_time(self, pst_message, transport_headers=''):
        delivery_time = self.safe_get_attr(pst_message, 'delivery_time', None)
        if not delivery_time and transport_headers:
            date_match = re.search(r'^Date:\s*(.+)', transport_headers, re.MULTILINE | re.IGNORECASE)
            if date_match:
                try:
                    delivery_time = email.utils.parsedate_to_datetime(date_match.group(1).strip())
                except Exception:
                    pass
        return delivery_time

    def _compute_hash(self, subject, sender_email, delivery_time):
        key = f"{subject}|{sender_email}|{delivery_time}"
        return hashlib.sha256(key.encode('utf-8', errors='replace')).hexdigest()

    # ── Filters ─────────────────────────────────────────────────

    def matches_filters(self, pst_message, folder_path, transport_headers=''):
        """Return True if message passes all active filters."""
        # Date filter
        delivery_time = self._get_delivery_time(pst_message, transport_headers)
        if delivery_time:
            if self.from_date and delivery_time < self.from_date:
                return False
            if self.to_date and delivery_time > self.to_date:
                return False
        elif self.from_date or self.to_date:
            # Can't determine date but a date filter is active → skip
            return False

        # Folder filter
        if self.folder_filter:
            if self.folder_filter not in (folder_path or '').lower():
                return False

        # Sender filter
        if self.sender_filter:
            sender = (self.safe_get_attr(pst_message, 'sender_email_address', '') or '').lower()
            sender_name = (self.safe_get_attr(pst_message, 'sender_name', '') or '').lower()
            if self.sender_filter not in sender and self.sender_filter not in sender_name:
                return False

        # Recipient filter
        if self.recipient_filter:
            found = False
            try:
                if hasattr(pst_message, 'recipients') and pst_message.recipients:
                    for r in pst_message.recipients:
                        r_email = (self.safe_get_attr(r, 'email_address', '') or '').lower()
                        r_name = (self.safe_get_attr(r, 'name', '') or '').lower()
                        if self.recipient_filter in r_email or self.recipient_filter in r_name:
                            found = True
                            break
            except Exception:
                pass
            if not found:
                return False

        # Keyword search in subject + body
        if self.search_keyword:
            subject = (self.safe_get_attr(pst_message, 'subject', '') or '').lower()
            body_text = (self.safe_get_attr(pst_message, 'plain_text_body', '') or '').lower()
            body_html = (self.safe_get_attr(pst_message, 'html_body', '') or '').lower()
            if (self.search_keyword not in subject
                    and self.search_keyword not in body_text
                    and self.search_keyword not in body_html):
                return False

        return True

    # ── Attachments ─────────────────────────────────────────────

    def extract_attachments(self, pst_message):
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
                            data = None

                            if data is None and hasattr(attachment, 'read_buffer') and size > 0:
                                try:
                                    data = attachment.read_buffer(size)
                                except Exception as e:
                                    self.logger.debug(f"read_buffer failed for '{filename}': {e}")
                            if data is None and hasattr(attachment, 'get_data'):
                                try:
                                    data = attachment.get_data()
                                except Exception as e:
                                    self.logger.debug(f"get_data failed for '{filename}': {e}")
                            if data is None:
                                data = self.safe_get_attr(attachment, 'data', None)

                            actual_size = len(data) if data else 0
                            att_info = {'filename': filename, 'size': size, 'data': data}
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

    def save_attachments_to_disk(self, attachments, subject, msg_index):
        """Save attachment files to the extract-attachments directory."""
        if not self.extract_attachments_dir or not attachments:
            return
        # Create a subdirectory per email to avoid name collisions
        safe_subject = re.sub(r'[^\w\s-]', '', (subject or 'no_subject')[:50]).strip()
        safe_subject = re.sub(r'\s+', '_', safe_subject)
        email_dir = self.extract_attachments_dir / f"{msg_index:06d}_{safe_subject}"
        email_dir.mkdir(parents=True, exist_ok=True)

        for att in attachments:
            if att['data']:
                safe_name = re.sub(r'[/\\:*?"<>|]', '_', att['filename'] or 'unnamed')
                filepath = email_dir / safe_name
                # Avoid overwriting
                counter = 1
                original = filepath
                while filepath.exists():
                    filepath = original.with_stem(f"{original.stem}_{counter}")
                    counter += 1
                filepath.write_bytes(att['data'] if isinstance(att['data'], bytes) else att['data'].encode('utf-8'))
                self.logger.debug(f"Saved attachment: {filepath}")

    # ── Email conversion ────────────────────────────────────────

    def _extract_recipients_by_type(self, pst_message):
        """Extract To, CC, BCC recipients separately."""
        to_list, cc_list, bcc_list = [], [], []
        try:
            if hasattr(pst_message, 'recipients') and pst_message.recipients:
                for recipient in pst_message.recipients:
                    r_email = self.safe_get_attr(recipient, 'email_address', '')
                    r_name = self.safe_get_attr(recipient, 'name', '')
                    r_type = self.safe_get_attr(recipient, 'type', 0)

                    if not r_email:
                        continue

                    formatted = self.format_email_address(r_email, r_name)
                    # libpff recipient types: 1=To, 2=CC, 3=BCC
                    if r_type == 2:
                        cc_list.append(formatted)
                    elif r_type == 3:
                        bcc_list.append(formatted)
                    else:
                        to_list.append(formatted)
        except (SystemError, ValueError, UnicodeDecodeError, OverflowError) as e:
            self.logger.debug(f"Failed to read recipients: {e}")
        return to_list, cc_list, bcc_list

    def convert_pst_message_to_email(self, pst_message, folder_path=""):
        try:
            body_text = self.safe_get_attr(pst_message, 'plain_text_body', '') or ""
            body_html = self.safe_get_attr(pst_message, 'html_body', '') or ""
            attachments = self.extract_attachments(pst_message)

            # Build MIME structure
            if attachments:
                msg = MIMEMultipart('mixed')
                if body_html and body_text:
                    alt_part = MIMEMultipart('alternative')
                    alt_part.attach(MIMEText(body_text, 'plain', 'utf-8'))
                    alt_part.attach(MIMEText(body_html, 'html', 'utf-8'))
                    msg.attach(alt_part)
                elif body_html:
                    msg.attach(MIMEText(body_html, 'html', 'utf-8'))
                else:
                    msg.attach(MIMEText(body_text or "(No content)", 'plain', 'utf-8'))
                for att in attachments:
                    if att['data']:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(att['data'])
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition',
                                        f'attachment; filename="{att["filename"]}"')
                        msg.attach(part)
            elif body_html and body_text:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif body_html:
                msg = MIMEText(body_html, 'html', 'utf-8')
            else:
                msg = MIMEText(body_text or "(No content)", 'plain', 'utf-8')

            # Subject
            subject = self.safe_get_attr(pst_message, 'subject', '') or "(No Subject)"
            msg['Subject'] = subject

            # Sender
            sender_name = self.safe_get_attr(pst_message, 'sender_name', '')
            sender_email = self.safe_get_attr(pst_message, 'sender_email_address', '')
            transport_headers = self.safe_get_attr(pst_message, 'transport_headers', '')

            if not sender_email and transport_headers:
                m = re.search(r'^From:\s*(.+?)\s*<(.+?)>', transport_headers, re.MULTILINE | re.IGNORECASE)
                if m:
                    sender_name = m.group(1).strip('"')
                    sender_email = m.group(2)

            if sender_email:
                msg['From'] = self.format_email_address(sender_email, sender_name)
                delivery_time = self._get_delivery_time(pst_message, transport_headers)
                if delivery_time:
                    unix_date = delivery_time.strftime('%a %b %d %H:%M:%S %Y')
                else:
                    unix_date = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
                msg.set_unixfrom(f'From {sender_email} {unix_date}')

            # Recipients (To / CC / BCC)
            to_list, cc_list, bcc_list = self._extract_recipients_by_type(pst_message)
            if to_list:
                msg['To'] = ', '.join(to_list)
            if cc_list:
                msg['Cc'] = ', '.join(cc_list)
            if bcc_list:
                msg['Bcc'] = ', '.join(bcc_list)

            # Date
            delivery_time = self._get_delivery_time(pst_message, transport_headers)
            if delivery_time:
                try:
                    msg['Date'] = delivery_time.strftime('%a, %d %b %Y %H:%M:%S %z')
                except Exception:
                    msg['Date'] = delivery_time.isoformat()
            else:
                msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

            # Message-ID
            if transport_headers and 'Message-ID:' in transport_headers:
                try:
                    msg_id = transport_headers.split('Message-ID:')[1].split('\n')[0].strip()
                    msg['Message-ID'] = msg_id
                except Exception:
                    pass

            # Folder header
            if folder_path:
                msg['X-Folder'] = folder_path

            return msg, attachments, subject

        except Exception as e:
            self.logger.error(f"Failed to convert PST message: {e}")
            raise

    # ── Output writers ──────────────────────────────────────────

    def _get_mbox_for_folder(self, folder_path, mbox_files):
        """Get or create an mbox file for a specific folder (split-by-folder mode)."""
        safe_name = re.sub(r'[/\\:*?"<>|]', '_', folder_path or 'Unknown')
        safe_name = safe_name.strip() or 'Unknown'
        if safe_name not in mbox_files:
            mbox_path = self.output_file / f"{safe_name}.mbox"
            mbox_files[safe_name] = mailbox.mbox(str(mbox_path))
            mbox_files[safe_name].lock()
            self.logger.info(f"Created mbox for folder: {safe_name}")
        return mbox_files[safe_name]

    def _write_eml(self, email_msg, index, folder_path):
        """Write a single email as .eml file."""
        safe_folder = re.sub(r'[/\\:*?"<>|]', '_', folder_path or 'Unknown')
        folder_dir = self.output_file / safe_folder
        folder_dir.mkdir(parents=True, exist_ok=True)

        subject = email_msg.get('Subject', 'no_subject') or 'no_subject'
        safe_subject = re.sub(r'[^\w\s-]', '', subject[:60]).strip()
        safe_subject = re.sub(r'\s+', '_', safe_subject)
        filename = f"{index:06d}_{safe_subject}.eml"
        filepath = folder_dir / filename

        filepath.write_text(email_msg.as_string(), encoding='utf-8')
        self.logger.debug(f"Wrote EML: {filepath}")

    # ── Metadata export ─────────────────────────────────────────

    def _collect_metadata(self, email_msg, folder_path, attachments):
        """Collect metadata record for CSV/JSON export."""
        att_names = [a['filename'] for a in attachments if a.get('filename')]
        self.metadata_records.append({
            'subject': email_msg.get('Subject', ''),
            'from': email_msg.get('From', ''),
            'to': email_msg.get('To', ''),
            'cc': email_msg.get('Cc', ''),
            'bcc': email_msg.get('Bcc', ''),
            'date': email_msg.get('Date', ''),
            'folder': folder_path,
            'message_id': email_msg.get('Message-ID', ''),
            'attachments': '; '.join(att_names),
            'attachment_count': len(attachments),
        })

    def _export_metadata(self):
        """Write collected metadata to CSV and/or JSON files."""
        if self.metadata_csv and self.metadata_records:
            fieldnames = list(self.metadata_records[0].keys())
            with open(self.metadata_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.metadata_records)
            self.logger.info(f"Metadata CSV written: {self.metadata_csv} ({len(self.metadata_records)} records)")

        if self.metadata_json and self.metadata_records:
            with open(self.metadata_json, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_records, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Metadata JSON written: {self.metadata_json} ({len(self.metadata_records)} records)")

    # ── Stats ───────────────────────────────────────────────────

    def _gather_stats(self, pst_archive):
        """Gather statistics from the PST file without converting."""
        self.logger.info("Gathering PST statistics...")
        total = 0
        for pst_message in pst_archive.messages():
            total += 1
            folder_path = "Unknown"
            try:
                if hasattr(pst_message, 'folder') and pst_message.folder:
                    folder_path = self.safe_get_attr(pst_message.folder, 'name', 'Unknown')
            except (SystemError, ValueError, UnicodeDecodeError, OverflowError):
                pass
            self.folder_counts[folder_path] = self.folder_counts.get(folder_path, 0) + 1

            att_count = 0
            try:
                if hasattr(pst_message, 'number_of_attachments'):
                    att_count = pst_message.number_of_attachments
            except Exception:
                pass
            self.attachments_found += att_count

        self.logger.info("")
        self.logger.info("=" * 55)
        self.logger.info("  PST FILE STATISTICS")
        self.logger.info("=" * 55)
        self.logger.info(f"  File:             {self.pst_file}")
        self.logger.info(f"  Size:             {self.pst_file.stat().st_size / (1024*1024):.2f} MB")
        self.logger.info(f"  Total emails:     {total}")
        self.logger.info(f"  Total attachments:{self.attachments_found}")
        self.logger.info(f"  Folders:          {len(self.folder_counts)}")
        self.logger.info("-" * 55)
        for folder, count in sorted(self.folder_counts.items(), key=lambda x: -x[1]):
            self.logger.info(f"    {folder:<35} {count:>6} emails")
        self.logger.info("=" * 55)

    # ── Main processing ─────────────────────────────────────────

    def process_messages(self, pst_archive, mbox_file=None):
        """Process all messages in the PST archive applying filters and output modes."""
        self.logger.info("Processing messages from PST archive...")

        # Count messages for progress bar
        messages_list = list(pst_archive.messages())
        total_messages = len(messages_list)
        self.logger.info(f"Found {total_messages} total messages in PST")

        mbox_files = {}  # For split-by-folder mode
        iterator = messages_list

        # Progress bar
        if tqdm and not self.verbose:
            iterator = tqdm(messages_list, desc="Converting", unit="email",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        for msg_index, pst_message in enumerate(iterator, start=1):
            try:
                # Get folder path
                folder_path = "Unknown"
                try:
                    if hasattr(pst_message, 'folder') and pst_message.folder:
                        folder_path = self.safe_get_attr(pst_message.folder, 'name', 'Unknown')
                except (SystemError, ValueError, UnicodeDecodeError, OverflowError):
                    pass

                transport_headers = self.safe_get_attr(pst_message, 'transport_headers', '')

                # Apply filters
                if not self.matches_filters(pst_message, folder_path, transport_headers):
                    self.skipped_emails += 1
                    continue

                # Duplicate detection
                if self.skip_duplicates:
                    subject = self.safe_get_attr(pst_message, 'subject', '') or ''
                    sender = self.safe_get_attr(pst_message, 'sender_email_address', '') or ''
                    dt = self._get_delivery_time(pst_message, transport_headers)
                    msg_hash = self._compute_hash(subject, sender, str(dt))
                    if msg_hash in self._seen_hashes:
                        self.skipped_duplicates += 1
                        self.skipped_emails += 1
                        continue
                    self._seen_hashes.add(msg_hash)

                # Dry run — just count, don't write
                if self.dry_run:
                    self.processed_emails += 1
                    self.folder_counts[folder_path] = self.folder_counts.get(folder_path, 0) + 1
                    subject = self.safe_get_attr(pst_message, 'subject', '') or '(No Subject)'
                    sender = self.safe_get_attr(pst_message, 'sender_email_address', '') or '?'
                    self.logger.debug(f"[dry-run] Would convert: {subject} (from {sender})")
                    continue

                # Convert message
                email_msg, attachments, subject = self.convert_pst_message_to_email(pst_message, folder_path)

                # Save attachments to disk if requested
                self.save_attachments_to_disk(attachments, subject, msg_index)

                # Collect metadata if requested
                if self.metadata_csv or self.metadata_json:
                    self._collect_metadata(email_msg, folder_path, attachments)

                # Write to output
                if self.output_file:
                    if self.output_format == 'eml':
                        self._write_eml(email_msg, msg_index, folder_path)
                    elif self.split_by_folder:
                        folder_mbox = self._get_mbox_for_folder(folder_path, mbox_files)
                        folder_mbox.add(email_msg)
                    elif mbox_file is not None:
                        mbox_file.add(email_msg)

                self.processed_emails += 1
                self.folder_counts[folder_path] = self.folder_counts.get(folder_path, 0) + 1

                if self.verbose and self.processed_emails % 100 == 0:
                    self.logger.info(f"Processed {self.processed_emails} emails...")

            except Exception as e:
                self.failed_emails += 1
                self.logger.error(f"Failed to process message {msg_index}: {e}")

        # Close split-by-folder mboxes
        for name, mb in mbox_files.items():
            mb.flush()
            mb.unlock()
            mb.close()

        self.logger.info(f"Finished processing {total_messages} messages")

    # ── Main entry ──────────────────────────────────────────────

    def convert(self):
        start_time = time.time()

        try:
            self.logger.info("Starting PST to mbox conversion...")

            # Show active filters
            self._log_active_filters()

            self.validate_files()
            pst_archive = self.open_pst_file()

            # Stats-only mode
            if self.stats_only:
                self._gather_stats(pst_archive)
                return True

            # Determine output mode
            mbox_file = None
            if not self.dry_run and self.output_file and self.output_format == 'mbox' and not self.split_by_folder:
                mbox_file = mailbox.mbox(str(self.output_file))
                mbox_file.lock()

            try:
                self.process_messages(pst_archive, mbox_file)

                if mbox_file is not None:
                    mbox_file.flush()
            finally:
                if mbox_file is not None:
                    mbox_file.unlock()
                    mbox_file.close()

            # Export metadata
            self._export_metadata()

            # Print final report
            self._print_report(time.time() - start_time)
            return True

        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            return False

    def _log_active_filters(self):
        filters = []
        if self.from_date:
            filters.append(f"from-date={self.from_date.strftime('%Y-%m-%d')}")
        if self.to_date:
            filters.append(f"to-date={self.to_date.strftime('%Y-%m-%d')}")
        if self.folder_filter:
            filters.append(f"folder={self.folder_filter}")
        if self.sender_filter:
            filters.append(f"sender={self.sender_filter}")
        if self.recipient_filter:
            filters.append(f"recipient={self.recipient_filter}")
        if self.search_keyword:
            filters.append(f"search={self.search_keyword}")
        if self.skip_duplicates:
            filters.append("skip-duplicates")
        if filters:
            self.logger.info(f"Active filters: {', '.join(filters)}")
        if self.dry_run:
            self.logger.info("DRY RUN — no files will be written")

    def _print_report(self, duration):
        self.logger.info("")
        self.logger.info("=" * 55)
        if self.dry_run:
            self.logger.info("  DRY RUN REPORT")
        else:
            self.logger.info("  CONVERSION COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 55)
        self.logger.info(f"  Input file:           {self.pst_file}")
        if self.output_file and not self.dry_run:
            self.logger.info(f"  Output:               {self.output_file}")
        self.logger.info(f"  Format:               {self.output_format}")
        self.logger.info(f"  Processed emails:     {self.processed_emails}")
        self.logger.info(f"  Skipped (filtered):   {self.skipped_emails}")
        if self.skip_duplicates:
            self.logger.info(f"  Skipped (duplicates): {self.skipped_duplicates}")
        self.logger.info(f"  Failed emails:        {self.failed_emails}")
        if not self.dry_run:
            self.logger.info(f"  Attachments found:    {self.attachments_found}")
            self.logger.info(f"  Attachments extracted:{self.attachments_extracted} ({self.attachment_bytes / (1024*1024):.2f} MB)")
            if self.extract_attachments_dir:
                self.logger.info(f"  Attachments saved to: {self.extract_attachments_dir}")
            if self.output_file and self.output_format == 'mbox' and not self.split_by_folder:
                output_size = self.output_file.stat().st_size if self.output_file.exists() else 0
                self.logger.info(f"  Output file size:     {output_size / (1024*1024):.2f} MB")
        self.logger.info(f"  Processing time:      {duration:.2f} seconds")
        if self.processed_emails > 0 and duration > 0:
            self.logger.info(f"  Average speed:        {self.processed_emails / duration:.1f} emails/sec")

        # Folder breakdown
        if self.folder_counts:
            self.logger.info("-" * 55)
            self.logger.info("  Emails per folder:")
            for folder, count in sorted(self.folder_counts.items(), key=lambda x: -x[1]):
                self.logger.info(f"    {folder:<35} {count:>6}")
        self.logger.info("=" * 55)


# ── CLI ─────────────────────────────────────────────────────────

def parse_date(value):
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{value}'. Use YYYY-MM-DD.")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Outlook PST files to mbox format for webmail import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pst output.mbox
  %(prog)s -v input.pst output.mbox
  %(prog)s --stats-only input.pst
  %(prog)s --dry-run input.pst output.mbox --from-date 2023-01-01
  %(prog)s input.pst emails/ --format eml --folder Inbox
  %(prog)s input.pst output/ --split-by-folder
  %(prog)s input.pst out.mbox --sender boss@company.com --search "project"
  %(prog)s input.pst out.mbox --extract-attachments ./attachments
  %(prog)s input.pst out.mbox --metadata-csv report.csv --skip-duplicates
  %(prog)s input.pst out.mbox --log-file conversion.log
        """
    )

    # Positional arguments
    parser.add_argument('pst_file', help='Path to the input PST file')
    parser.add_argument('output_file', nargs='?', default=None,
                        help='Path to the output mbox file or directory (not needed with --stats-only)')

    # General options
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')

    # Filters
    filters = parser.add_argument_group('Filters')
    filters.add_argument('--from-date', type=parse_date, metavar='YYYY-MM-DD',
                         help='Only include emails from this date onward')
    filters.add_argument('--to-date', type=parse_date, metavar='YYYY-MM-DD',
                         help='Only include emails up to this date')
    filters.add_argument('--folder', dest='folder_filter', metavar='NAME',
                         help='Only include emails from folders matching NAME (case-insensitive)')
    filters.add_argument('--sender', dest='sender_filter', metavar='TEXT',
                         help='Only include emails where sender matches TEXT')
    filters.add_argument('--to-filter', dest='recipient_filter', metavar='TEXT',
                         help='Only include emails where any recipient matches TEXT')
    filters.add_argument('--search', dest='search_keyword', metavar='KEYWORD',
                         help='Only include emails containing KEYWORD in subject or body')
    filters.add_argument('--skip-duplicates', action='store_true',
                         help='Skip duplicate emails (based on subject + sender + date)')

    # Output format
    output_group = parser.add_argument_group('Output format')
    output_group.add_argument('--format', dest='output_format', choices=['mbox', 'eml'],
                              default='mbox',
                              help='Output format: mbox (single file) or eml (one file per email)')
    output_group.add_argument('--split-by-folder', action='store_true',
                              help='Create a separate .mbox file per PST folder')
    output_group.add_argument('--metadata-csv', metavar='FILE',
                              help='Export email metadata to a CSV file')
    output_group.add_argument('--metadata-json', metavar='FILE',
                              help='Export email metadata to a JSON file')

    # Extras
    extras = parser.add_argument_group('Extra features')
    extras.add_argument('--extract-attachments', dest='extract_attachments_dir', metavar='DIR',
                        help='Save all attachments to DIR')
    extras.add_argument('--dry-run', action='store_true',
                        help='Show what would be converted without writing files')
    extras.add_argument('--stats-only', action='store_true',
                        help='Show PST statistics (folders, counts) without converting')
    extras.add_argument('--log-file', metavar='FILE',
                        help='Write log output to FILE in addition to console')

    args = parser.parse_args()

    # Validate: output_file is required unless --stats-only
    if not args.stats_only and not args.output_file and not args.dry_run:
        parser.error("output_file is required unless using --stats-only or --dry-run")

    converter = PSTToMboxConverter(
        pst_file=args.pst_file,
        output_file=args.output_file,
        verbose=args.verbose,
        from_date=args.from_date,
        to_date=args.to_date,
        folder_filter=args.folder_filter,
        sender_filter=args.sender_filter,
        recipient_filter=args.recipient_filter,
        search_keyword=args.search_keyword,
        output_format=args.output_format,
        split_by_folder=args.split_by_folder,
        metadata_csv=args.metadata_csv,
        metadata_json=args.metadata_json,
        extract_attachments_dir=args.extract_attachments_dir,
        dry_run=args.dry_run,
        stats_only=args.stats_only,
        skip_duplicates=args.skip_duplicates,
        log_file=args.log_file,
    )

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
