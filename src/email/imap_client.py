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
from src.utils.html_to_pdf import HtmlToPdfConverter


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
        
        # Initialize the HTML to PDF converter
        self.html_converter = HtmlToPdfConverter(logger=self.custom_logger, wkhtmltopdf_path=wkhtmltopdf_path)
        
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
    
    def process_url_attachment(self, email_message: EmailMessage, email_filter: EmailFilter) -> int:
        """
        Process URL-based attachment by downloading HTML and converting to PDF.
        
        Args:
            email_message: The email message
            email_filter: The filter with url_to_attachment criteria
            
        Returns:
            int: Number of PDFs created (0 or 1)
        """
        if not email_filter.url_to_attachment or not self.account.target_folder:
            return 0
        
        # Get email body (try plain text first, then HTML)
        body = email_message.get_body("text/plain") or email_message.get_body("text/html") or ""
        
        # Extract matching URLs
        matching_urls = self.extract_urls_from_body(body, email_filter.url_to_attachment)
        
        if not matching_urls:
            self.logger.debug(f"No URLs found matching prefix: {email_filter.url_to_attachment}")
            return 0
        
        # Process the first matching URL
        url = matching_urls[0]
        self.logger.info(f"Processing URL attachment: {url}")
        
        # Generate filename based on email subject and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_subject = re.sub(r'[^\w\s-]', '', email_message.subject)[:50]
        filename = f"{safe_subject}_{timestamp}.pdf"
        
        # Full path for the PDF
        output_path = os.path.join(self.account.target_folder, filename)
        
        # Download and convert to PDF
        if self.html_converter.download_and_convert(url, output_path):
            self.custom_logger.important(f"Created PDF from URL: {output_path}")
            return 1
        else:
            self.logger.error(f"Failed to create PDF from URL: {url}")
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
                self.logger.debug(f"Trying filter #{i+1}: sender='{email_filter.sender}', subject='{email_filter.subject}', ext='{email_filter.attachment_extension}'")
                
                if email_filter.matches_email(email_message.from_address, email_message.subject, self.logger):
                    self.logger.debug(f"Email matched filter #{i+1}")
                    
                    # Check if this filter uses URL-based attachments
                    if email_filter.url_to_attachment:
                        self.logger.debug(f"Filter #{i+1} uses URL-based attachment with prefix: {email_filter.url_to_attachment}")
                        
                        # Process URL attachment
                        url_attachments = self.process_url_attachment(email_message, email_filter)
                        if url_attachments > 0:
                            attachment_count += url_attachments
                            return True  # Successfully processed URL attachment
                        else:
                            self.logger.debug(f"No URL attachments processed for filter #{i+1}")
                    
                    # Process regular attachments
                    else:
                        attachment_matched = False
                        for attachment in email_message.attachments:
                            if email_filter.matches_attachment(attachment.filename, self.logger):
                                self.logger.debug(f"Attachment '{attachment.filename}' matched filter #{i+1}")
                                attachment_matched = True
                                
                                # Save attachment using the account's target folder
                                if self.account.target_folder:
                                    saved_path = self.save_attachment(
                                        attachment,
                                        self.account.target_folder,
                                        sanitize_filename=True
                                    )
                                    if saved_path:
                                        attachment_count += 1
                                        self.custom_logger.important(f"Saved attachment {saved_path}")
                            else:
                                self.logger.debug(f"Attachment '{attachment.filename}' did not match filter #{i+1}")
                        
                        if not attachment_matched and email_message.attachments:
                            self.logger.debug(f"No attachments matched filter #{i+1}")
                        elif not email_message.attachments:
                            self.logger.debug("Email has no attachments")
                        
                        if attachment_matched:
                            return True  # Message matched a filter and had matching attachments
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
