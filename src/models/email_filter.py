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
    url_to_attachment: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'EmailFilter':
        """
        Create an EmailFilter instance from a dictionary.
        
        Args:
            data: Dictionary containing filter criteria
            
        Returns:
            EmailFilter: New EmailFilter instance
        """
        return cls(
            sender=data.get('sender'),
            subject=data.get('subject'),
            attachment_extension=data.get('attachment_extension'),
            url_to_attachment=data.get('url_to_attachment')
        )
    
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
            
        # Check subject match if filter has a subject criteria
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
