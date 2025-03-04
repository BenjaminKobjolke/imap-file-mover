"""
IMAP client for connecting to email servers and retrieving messages.
"""
from typing import List, Optional, Tuple
import os
from pathlib import Path

from imapclient import IMAPClient

from src.models.account import Account
from src.models.email_message import EmailMessage
from src.models.email_filter import EmailFilter
from src.utils.logger import Logger


class ImapClient:
    """
    Handles IMAP connections and email operations.
    """
    
    def __init__(self, account: Account):
        """
        Initialize the IMAP client with an account.
        
        Args:
            account: The email account configuration
        """
        self.account = account
        self.client = None
        self.logger = Logger()
        
    def connect(self) -> bool:
        """
        Connect to the IMAP server.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to {self.account.server} for account {self.account.name}")
            self.client = IMAPClient(self.account.server, port=self.account.port, use_uid=True, ssl=self.account.use_ssl)
            self.client.login(self.account.username, self.account.password)
            self.logger.info(f"Successfully connected to {self.account.server}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.account.server}: {e}")
            return False
            
    def disconnect(self):
        """
        Disconnect from the IMAP server.
        """
        if self.client:
            try:
                self.client.logout()
                self.logger.info(f"Disconnected from {self.account.server}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {self.account.server}: {e}")
            finally:
                self.client = None
                
    def get_unread_messages(self) -> List[Tuple[str, EmailMessage]]:
        """
        Get all unread messages from the inbox.
        
        Returns:
            List[Tuple[str, EmailMessage]]: List of message IDs and parsed email messages
        """
        if not self.client:
            self.logger.error("Not connected to IMAP server")
            return []
            
        try:
            # Select the inbox
            self.client.select_folder('INBOX')
            
            # Search for unread messages
            self.logger.info("Searching for unread messages")
            message_ids = self.client.search(['UNSEEN'])
            
            if not message_ids:
                self.logger.info("No unread messages found")
                return []
                
            self.logger.info(f"Found {len(message_ids)} unread messages")
            
            # Fetch message data
            messages = []
            for message_id in message_ids:
                try:
                    raw_message = self.client.fetch([message_id], ['BODY.PEEK[]'])
                    message_data = raw_message[message_id][b'BODY[]']
                    email_message = EmailMessage.from_bytes(str(message_id), message_data, self.logger)
                    messages.append((str(message_id), email_message))
                except Exception as e:
                    self.logger.error(f"Error fetching message {message_id}: {e}")
                    
            return messages
        except Exception as e:
            self.logger.error(f"Error getting unread messages: {e}")
            return []
            
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: The ID of the message to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            self.logger.error("Not connected to IMAP server")
            return False
            
        try:
            self.client.add_flags([int(message_id)], [b'\\Seen'])
            self.logger.important(f"Marked message {message_id} as read")
            return True
        except Exception as e:
            self.logger.error(f"Error marking message {message_id} as read: {e}")
            return False
            
    def move_to_folder(self, message_id: str, folder: str) -> bool:
        """
        Move a message to a different folder.
        
        Args:
            message_id: The ID of the message to move
            folder: The destination folder
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            self.logger.error("Not connected to IMAP server")
            return False
            
        if not folder:
            self.logger.debug(f"No move folder specified for message {message_id}, skipping move")
            return True
            
        try:
            # Check if folder exists
            folders = self.client.list_folders()
            folder_names = [f[2] for f in folders]
            
            if folder not in folder_names:
                self.logger.warning(f"Folder '{folder}' does not exist, attempting to create it")
                try:
                    self.client.create_folder(folder)
                    self.logger.info(f"Created folder '{folder}'")
                except Exception as e:
                    self.logger.error(f"Error creating folder '{folder}': {e}")
                    return False
            
            # Move the message
            self.client.move([int(message_id)], folder)
            self.logger.important(f"Moved message {message_id} to folder '{folder}'")
            return True
        except Exception as e:
            self.logger.error(f"Error moving message {message_id} to folder '{folder}': {e}")
            return False
            
    def process_messages(self, filters: List[EmailFilter]) -> int:
        """
        Process unread messages, download matching attachments, and mark as read.
        
        Args:
            filters: List of email filters to apply
            
        Returns:
            int: Number of attachments processed
        """
        if not self.connect():
            return 0
            
        try:
            # Get unread messages
            messages = self.get_unread_messages()
            
            if not messages:
                self.disconnect()
                return 0
                
            # Process each message
            attachment_count = 0
            
            for message_id, email_message in messages:
                self.logger.debug(f"Processing message ID: {message_id}")
                self.logger.debug(f"From: '{email_message.from_address}'")
                self.logger.debug(f"Subject: '{email_message.subject}'")
                self.logger.debug(f"Attachments: {len(email_message.attachments)}")
                
                if email_message.attachments:
                    for attachment in email_message.attachments:
                        self.logger.debug(f"Attachment filename: '{attachment.filename}'")
                        self.logger.debug(f"Attachment content type: '{attachment.content_type}'")
                
                # Check if message matches any filter
                filter_matched = False
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
                                
                                # Save attachment
                                if self._save_attachment(attachment.filename, attachment.data):
                                    attachment_count += 1
                            else:
                                self.logger.debug(f"Attachment '{attachment.filename}' did not match filter #{i+1}")
                        
                        if not attachment_matched and email_message.attachments:
                            self.logger.debug(f"No attachments matched filter #{i+1}")
                        elif not email_message.attachments:
                            self.logger.debug("Email has no attachments")
                        
                        # Mark message as read
                        self.mark_as_read(message_id)
                        
                        # Move message to specified folder if configured
                        if self.account.imap_move_folder:
                            self.move_to_folder(message_id, self.account.imap_move_folder)
                            
                        filter_matched = True
                        break
                    else:
                        self.logger.debug(f"Email did not match filter #{i+1}")
                
                if not filter_matched:
                    self.logger.debug("Message did not match any filters")
                        
            return attachment_count
        finally:
            self.disconnect()
            
    def _save_attachment(self, filename: str, data: bytes) -> bool:
        """
        Save an attachment to the target folder.
        
        Args:
            filename: The name of the file
            data: The file data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create target directory if it doesn't exist
            target_dir = Path(self.account.target_folder)
            os.makedirs(target_dir, exist_ok=True)
            
            # Sanitize filename by replacing path separators with underscores
            sanitized_filename = filename.replace('/', '_').replace('\\', '_')
            self.logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized_filename}'")
            
            # Save file
            file_path = target_dir / sanitized_filename
            
            # Handle duplicate filenames
            counter = 1
            while file_path.exists():
                name, ext = os.path.splitext(sanitized_filename)
                new_filename = f"{name}_{counter}{ext}"
                file_path = target_dir / new_filename
                counter += 1
                
            with open(file_path, 'wb') as f:
                f.write(data)
                
            # Always log saved attachments regardless of log level
            self.logger.important(f"Saved attachment {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving attachment {filename}: {e}")
            return False
