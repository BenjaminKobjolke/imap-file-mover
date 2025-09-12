"""
IMAP client for connecting to email servers and retrieving messages.
This extends the base library's ImapClient to add file-moving specific functionality.
"""
from typing import List, Optional, Tuple
import os
import re
from pathlib import Path
from datetime import datetime

# Import from the imap_client_python library
# Install with: pip install git+https://github.com/BenjaminKobjolke/imap_client_python.git
from imap_client_lib import ImapClient as BaseImapClient
from imap_client_lib import EmailMessage, Attachment

from src.models.account import Account
from src.models.email_filter import EmailFilter
from src.utils.logger import Logger
from src.utils.html_to_pdf import HtmlConverter


class ImapClient(BaseImapClient):
    """
    Extended IMAP client for the file moving application.
    Adds filtering and custom logging functionality.
    """
    
    def __init__(self, account: Account, wkhtmltopdf_path: Optional[str] = None):
        """
        Initialize the IMAP client with an account.
        
        Args:
            account: The email account configuration
            wkhtmltopdf_path: Optional path to wkhtmltopdf executable
        """
        # Initialize the custom logger
        self.custom_logger = Logger()
        
        # Initialize the HTML converter
        self.html_converter = HtmlConverter(logger=self.custom_logger, wkhtmltopdf_path=wkhtmltopdf_path)
        
        # Initialize the base client with the custom logger
        super().__init__(account, logger=self.custom_logger)
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Override to use custom logger's important method.
        """
        result = super().mark_as_read(message_id)
        if result:
            self.custom_logger.important(f"Marked message {message_id} as read")
        return result
    
    def move_to_folder(self, message_id: str, folder: str) -> bool:
        """
        Override to use custom logger's important method.
        """
        result = super().move_to_folder(message_id, folder)
        if result and folder:
            self.custom_logger.important(f"Moved message {message_id} to folder '{folder}'")
        return result
    
    def extract_urls_from_body(self, body: str, url_prefix: str) -> List[str]:
        """
        Extract URLs from email body that start with the specified prefix.
        
        Args:
            body: Email body content (plain text or HTML)
            url_prefix: URL prefix to match
            
        Returns:
            List[str]: List of matching URLs
        """
        # Pattern to find URLs
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        
        # Find all URLs in the body
        all_urls = url_pattern.findall(body)
        
        # Filter URLs that start with the specified prefix
        matching_urls = [url for url in all_urls if url.startswith(url_prefix)]
        
        self.logger.debug(f"Found {len(matching_urls)} URLs matching prefix '{url_prefix}'")
        for url in matching_urls:
            self.logger.debug(f"  - {url}")
        
        return matching_urls
    
    def get_target_folder(self, email_filter: EmailFilter) -> str:
        """
        Get the target folder for a filter, using filter override or account default.
        
        Args:
            email_filter: The email filter
            
        Returns:
            str: Target folder path
        """
        return email_filter.target_folder or self.account.target_folder
    
    def sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """
        Sanitize filename to be safe for filesystem use.
        
        Args:
            filename: Raw filename to sanitize
            max_length: Maximum length for filename (excluding extension)
            
        Returns:
            str: Sanitized filename
        """
        if not filename:
            return "untitled"
        
        # Remove or replace problematic characters
        # Windows forbidden characters: < > : " | ? * \ /
        # Also remove control characters and other problematic ones
        safe_name = re.sub(r'[<>:"|?*\\/\x00-\x1f\x7f]', '', filename)
        
        # Replace multiple spaces with single space
        safe_name = re.sub(r'\s+', ' ', safe_name)
        
        # Remove leading/trailing whitespace and periods (Windows issue)
        safe_name = safe_name.strip(' .')
        
        # Ensure it's not a reserved Windows name
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        if safe_name.upper() in reserved_names:
            safe_name = f"{safe_name}_file"
        
        # Truncate to max length
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length].strip(' .')
        
        # If empty after sanitization, use default
        if not safe_name:
            safe_name = "untitled"
        
        return safe_name

    def generate_filename(self, email_message: EmailMessage, email_filter: EmailFilter, extension: str) -> str:
        """
        Generate filename for attachment based on email and filter.
        
        Args:
            email_message: The email message
            email_filter: The email filter
            extension: File extension (without dot)
            
        Returns:
            str: Generated filename
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        safe_subject = self.sanitize_filename(email_message.subject, 50)
        
        if email_filter.attachment_type == "body":
            return f"{timestamp}_{safe_subject}.{extension}"
        else:
            timestamp_full = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{safe_subject}_{timestamp_full}.{extension}"
    
    def process_body_attachment(self, email_message: EmailMessage, email_filter: EmailFilter) -> int:
        """
        Process email body as attachment by converting to specified format.
        
        Args:
            email_message: The email message
            email_filter: The filter with body attachment criteria
            
        Returns:
            int: Number of files created (0 or 1)
        """
        target_folder = self.get_target_folder(email_filter)
        if not target_folder:
            self.logger.error("No target folder specified for body attachment")
            return 0
        
        # Get email body (prefer HTML, fallback to plain text)
        body = email_message.get_body("text/html") or email_message.get_body("text/plain") or ""
        
        # Trim whitespace from the body content
        body = body.strip()
        
        if not body:
            self.logger.debug("No email body found")
            return 0
        
        # Generate filename
        extension = "md" if email_filter.target_format.lower() == "md" else "pdf"
        filename = self.generate_filename(email_message, email_filter, extension)
        output_path = os.path.join(target_folder, filename)
        
        self.logger.info(f"Processing body attachment: {filename}")
        
        # For markdown, convert HTML directly. For PDF, only if body has HTML structure
        if email_filter.target_format.lower() == "md":
            # If body is plain text, wrap it in minimal HTML for markdown conversion
            if not body.strip().startswith('<'):
                body = f"<html><body><pre>{body}</pre></body></html>"
            success = self.html_converter.convert_content(body, output_path, "md")
        else:
            # For PDF, only convert if it looks like HTML
            if body.strip().startswith('<'):
                success = self.html_converter.convert_content(body, output_path, "pdf")
            else:
                self.logger.debug("Body is plain text, not converting to PDF (use markdown format instead)")
                return 0
        
        if success:
            self.custom_logger.important(f"Created {email_filter.target_format.upper()} from email body: {output_path}")
            return 1
        else:
            self.logger.error(f"Failed to create {email_filter.target_format.upper()} from email body")
            return 0
    
    def process_url_attachment(self, email_message: EmailMessage, email_filter: EmailFilter) -> int:
        """
        Process URL-based attachment by downloading HTML and converting to specified format.
        
        Args:
            email_message: The email message
            email_filter: The filter with URL attachment criteria
            
        Returns:
            int: Number of files created (0 or 1)
        """
        url_prefix = email_filter.url_prefix or email_filter.url_to_attachment
        if not url_prefix:
            return 0
        
        target_folder = self.get_target_folder(email_filter)
        if not target_folder:
            self.logger.error("No target folder specified for URL attachment")
            return 0
        
        # Get email body (try plain text first, then HTML)
        body = email_message.get_body("text/plain") or email_message.get_body("text/html") or ""
        
        # Trim whitespace from the body content
        body = body.strip()
        
        # Extract matching URLs
        matching_urls = self.extract_urls_from_body(body, url_prefix)
        
        if not matching_urls:
            self.logger.debug(f"No URLs found matching prefix: {url_prefix}")
            return 0
        
        # Process the first matching URL
        url = matching_urls[0]
        self.logger.info(f"Processing URL attachment: {url}")
        
        # Generate filename
        extension = "md" if email_filter.target_format.lower() == "md" else "pdf"
        filename = self.generate_filename(email_message, email_filter, extension)
        output_path = os.path.join(target_folder, filename)
        
        # Download and convert to target format
        if self.html_converter.download_and_convert(url, output_path, email_filter.target_format):
            self.custom_logger.important(f"Created {email_filter.target_format.upper()} from URL: {output_path}")
            return 1
        else:
            self.logger.error(f"Failed to create {email_filter.target_format.upper()} from URL: {url}")
            return 0
            
    def process_messages(self, filters: List[EmailFilter]) -> int:
        """
        Process unread messages, download matching attachments, and mark as read.
        
        Args:
            filters: List of email filters to apply
            
        Returns:
            int: Number of attachments processed
        """
        attachment_count = 0
        
        def process_email(email_message: EmailMessage) -> bool:
            """
            Process individual email based on filters.
            """
            nonlocal attachment_count
            
            self.logger.debug(f"Processing message ID: {email_message.message_id}")
            self.logger.debug(f"From: '{email_message.from_address}'")
            self.logger.debug(f"Subject: '{email_message.subject}'")
            self.logger.debug(f"Attachments: {len(email_message.attachments)}")
            
            if email_message.attachments:
                for attachment in email_message.attachments:
                    self.logger.debug(f"Attachment filename: '{attachment.filename}'")
                    self.logger.debug(f"Attachment content type: '{attachment.content_type}'")
            
            # Check if message matches any filter
            for i, email_filter in enumerate(filters):
                self.logger.debug(f"Trying filter #{i+1}: account='{email_filter.account}', sender='{email_filter.sender}', subject='{email_filter.subject}', ext='{email_filter.attachment_extension}'")
                
                # First check if the filter applies to this account
                if not email_filter.matches_account(self.account.name, self.logger):
                    self.logger.debug(f"Filter #{i+1} skipped - not for account '{self.account.name}'")
                    continue
                
                if email_filter.matches_email(email_message.from_address, email_message.subject, self.logger):
                    self.logger.debug(f"Email matched filter #{i+1}")
                    self.logger.debug(f"Filter #{i+1} attachment_type: {email_filter.attachment_type}")
                    
                    processed_count = 0
                    
                    # Process based on attachment type
                    if email_filter.attachment_type == "body":
                        self.logger.debug(f"Filter #{i+1} processes email body")
                        processed_count = self.process_body_attachment(email_message, email_filter)
                    
                    elif email_filter.attachment_type == "url" or email_filter.url_to_attachment:
                        self.logger.debug(f"Filter #{i+1} processes URL attachment")
                        processed_count = self.process_url_attachment(email_message, email_filter)
                    
                    else:  # attachment_type == "attachment" (default)
                        self.logger.debug(f"Filter #{i+1} processes regular attachments")
                        attachment_matched = False
                        target_folder = self.get_target_folder(email_filter)
                        
                        if not target_folder:
                            self.logger.error("No target folder specified for regular attachments")
                        else:
                            for attachment in email_message.attachments:
                                if email_filter.matches_attachment(attachment.filename, self.logger):
                                    self.logger.debug(f"Attachment '{attachment.filename}' matched filter #{i+1}")
                                    attachment_matched = True
                                    
                                    # Save attachment using target folder (filter override or account default)
                                    saved_path = self.save_attachment(
                                        attachment,
                                        target_folder,
                                        sanitize_filename=True
                                    )
                                    if saved_path:
                                        processed_count += 1
                                        self.custom_logger.important(f"Saved attachment {saved_path}")
                                else:
                                    self.logger.debug(f"Attachment '{attachment.filename}' did not match filter #{i+1}")
                            
                            if not attachment_matched and email_message.attachments:
                                self.logger.debug(f"No attachments matched filter #{i+1}")
                            elif not email_message.attachments:
                                self.logger.debug("Email has no attachments")
                    
                    if processed_count > 0:
                        attachment_count += processed_count
                        return True  # Successfully processed attachment(s)
                else:
                    self.logger.debug(f"Email did not match filter #{i+1}")
            
            self.logger.debug("Message did not match any filters")
            return False  # Message didn't match any filter
        
        # Use the base class method with our custom callback
        self.process_messages_with_callback(
            callback=process_email,
            search_criteria=['UNSEEN'],
            mark_as_read=True,
            move_to_folder=self.account.imap_move_folder
        )
        
        return attachment_count
