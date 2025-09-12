"""
Email filter model for matching emails based on criteria.
"""
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class EmailFilter:
    """
    Represents filter criteria for matching emails.
    """
    sender: Optional[str] = None
    subject: Optional[str] = None
    attachment_extension: Optional[str] = None
    url_to_attachment: Optional[str] = None  # Deprecated - use attachment_type and url_prefix
    attachment_type: str = "attachment"  # "attachment", "url", "body"
    target_format: str = "pdf"  # "pdf", "md"
    target_folder: Optional[str] = None  # Optional override for account target_folder
    url_prefix: Optional[str] = None  # For attachment_type="url"
    account: Optional[str] = None  # Optional account name filter

    @classmethod
    def from_dict(cls, data: dict) -> 'EmailFilter':
        """
        Create an EmailFilter instance from a dictionary.
        
        Args:
            data: Dictionary containing filter criteria
            
        Returns:
            EmailFilter: New EmailFilter instance
        """
        # Handle backward compatibility for url_to_attachment
        url_to_attachment = data.get('url_to_attachment')
        attachment_type = data.get('attachment_type', 'attachment')
        url_prefix = data.get('url_prefix')
        
        # If url_to_attachment is specified but attachment_type isn't, migrate
        if url_to_attachment and attachment_type == 'attachment':
            attachment_type = 'url'
            url_prefix = url_to_attachment
        
        return cls(
            sender=data.get('sender'),
            subject=data.get('subject'),
            attachment_extension=data.get('attachment_extension'),
            url_to_attachment=url_to_attachment,
            attachment_type=attachment_type,
            target_format=data.get('target_format', 'pdf'),
            target_folder=data.get('target_folder'),
            url_prefix=url_prefix or url_to_attachment,
            account=data.get('account')
        )
    
    def matches_account(self, account_name: str, logger: Any = None) -> bool:
        """
        Check if this filter applies to the given account.
        
        Args:
            account_name: The name of the account
            logger: Optional logger for debug information
            
        Returns:
            bool: True if the filter applies to this account, False otherwise
        """
        if not self.account:
            # If no account filter is set, apply to all accounts
            if logger:
                logger.debug("Filter has no account restriction, applies to all accounts")
            return True
        
        if self.account == account_name:
            if logger:
                logger.debug(f"Filter account '{self.account}' matches account '{account_name}'")
            return True
        else:
            if logger:
                logger.debug(f"Filter account '{self.account}' does not match account '{account_name}'")
            return False
    
    def matches_email(self, email_from: str, email_subject: str, logger: Any = None) -> bool:
        """
        Check if an email matches this filter's criteria.
        
        Args:
            email_from: The sender of the email
            email_subject: The subject of the email
            logger: Optional logger for debug information
            
        Returns:
            bool: True if the email matches the filter criteria, False otherwise
        """
        if logger:
            logger.debug(f"Checking email match - From: '{email_from}', Subject: '{email_subject}'")
            logger.debug(f"Filter criteria - Sender: '{self.sender}', Subject: '{self.subject}'")
        
        # Check sender match if filter has a sender criteria
        if self.sender and self.sender not in email_from:
            if logger:
                logger.debug(f"Sender mismatch - Filter: '{self.sender}' not in '{email_from}'")
            return False
            
        # Check subject match if filter has a subject criteria (ignore if not set)
        if self.subject and self.subject not in email_subject:
            if logger:
                logger.debug(f"Subject mismatch - Filter: '{self.subject}' not in '{email_subject}'")
            return False
            
        # If we get here, all specified criteria match
        if logger:
            logger.debug("Email matches filter criteria")
        return True
    
    def matches_attachment(self, filename: str, logger: Any = None) -> bool:
        """
        Check if a filename matches this filter's attachment extension criteria.
        
        Args:
            filename: The filename to check
            logger: Optional logger for debug information
            
        Returns:
            bool: True if the filename matches the extension criteria, False otherwise
        """
        if logger:
            logger.debug(f"Checking attachment match - Filename: '{filename}'")
            logger.debug(f"Filter criteria - Extension: '{self.attachment_extension}'")
        
        if not self.attachment_extension:
            if logger:
                logger.debug("No attachment extension filter specified, matching all attachments")
            return True
        
        match_result = filename.lower().endswith(f'.{self.attachment_extension.lower()}')
        
        if logger:
            if match_result:
                logger.debug(f"Attachment matches extension filter: '{self.attachment_extension}'")
            else:
                logger.debug(f"Attachment extension mismatch - Expected: '{self.attachment_extension}'")
                
        return match_result
