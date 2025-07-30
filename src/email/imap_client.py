"""
IMAP client for connecting to email servers and retrieving messages.
This extends the base library's ImapClient to add file-moving specific functionality.
"""
from typing import List, Optional, Tuple
import os
from pathlib import Path

# Import from the imap_client_python library
# Install with: pip install git+https://github.com/BenjaminKobjolke/imap_client_python.git
from imap_client_lib import ImapClient as BaseImapClient
from imap_client_lib import EmailMessage, Attachment

from src.models.account import Account
from src.models.email_filter import EmailFilter
from src.utils.logger import Logger


class ImapClient(BaseImapClient):
    """
    Extended IMAP client for the file moving application.
    Adds filtering and custom logging functionality.
    """
    
    def __init__(self, account: Account):
        """
        Initialize the IMAP client with an account.
        
        Args:
            account: The email account configuration
        """
        # Initialize the custom logger
        self.custom_logger = Logger()
        
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
                    
                    # Process attachments
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
                    
                    return True  # Message matched a filter
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
