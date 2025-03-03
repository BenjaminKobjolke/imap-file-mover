"""
Email message model for representing email data.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import email
from email.message import Message
import email.header


@dataclass
class Attachment:
    """
    Represents an email attachment.
    """
    filename: str
    content_type: str
    data: bytes


@dataclass
class EmailMessage:
    """
    Represents an email message with its metadata and attachments.
    """
    message_id: str
    from_address: str
    subject: str
    date: str
    attachments: List[Attachment]
    raw_message: Message

    @classmethod
    def from_bytes(cls, message_id: str, message_data: bytes, logger: Any = None) -> 'EmailMessage':
        """
        Create an EmailMessage instance from raw message bytes.
        
        Args:
            message_id: The unique ID of the message
            message_data: The raw message data
            logger: Optional logger for debug information
            
        Returns:
            EmailMessage: New EmailMessage instance
        """
        if logger:
            logger.debug(f"Parsing email message ID: {message_id}")
            
        # Parse the email message
        msg = email.message_from_bytes(message_data)
        
        # Extract basic headers
        from_address = msg.get('From', '')
        subject = msg.get('Subject', '')
        date = msg.get('Date', '')
        
        # Decode headers if needed
        if from_address:
            try:
                decoded_from = str(email.header.make_header(email.header.decode_header(from_address)))
                if logger and decoded_from != from_address:
                    logger.debug(f"Decoded From header: '{from_address}' -> '{decoded_from}'")
                from_address = decoded_from
            except Exception as e:
                if logger:
                    logger.debug(f"Error decoding From header: {e}")
        
        if subject:
            try:
                decoded_subject = str(email.header.make_header(email.header.decode_header(subject)))
                if logger and decoded_subject != subject:
                    logger.debug(f"Decoded Subject header: '{subject}' -> '{decoded_subject}'")
                subject = decoded_subject
            except Exception as e:
                if logger:
                    logger.debug(f"Error decoding Subject header: {e}")
        
        if logger:
            logger.debug(f"Parsed headers - From: '{from_address}', Subject: '{subject}', Date: '{date}'")
        
        # Extract attachments
        attachments = []
        
        if logger:
            logger.debug("Scanning for attachments...")
            
        for part in msg.walk():
            content_disposition = part.get_content_disposition()
            content_type = part.get_content_type()
            
            if logger:
                logger.debug(f"Message part - Content-Type: '{content_type}', Content-Disposition: '{content_disposition}'")
                
            filename = part.get_filename()
            
            if content_disposition == 'attachment' and filename:
                if logger:
                    logger.debug(f"Found attachment - Filename: '{filename}', Content-Type: '{content_type}'")
                    
                data = part.get_payload(decode=True)
                
                if data:
                    if logger:
                        logger.debug(f"Attachment data size: {len(data)} bytes")
                        
                    attachment = Attachment(
                        filename=filename,
                        content_type=content_type,
                        data=data
                    )
                    attachments.append(attachment)
                else:
                    if logger:
                        logger.debug("Attachment has no data, skipping")
            elif filename and not content_disposition:
                # Some emails don't set content_disposition but still have attachments
                if logger:
                    logger.debug(f"Potential attachment without Content-Disposition - Filename: '{filename}', Content-Type: '{content_type}'")
                
                # Try to extract it anyway
                data = part.get_payload(decode=True)
                
                if data:
                    if logger:
                        logger.debug(f"Extracted attachment without Content-Disposition - Size: {len(data)} bytes")
                        
                    attachment = Attachment(
                        filename=filename,
                        content_type=content_type,
                        data=data
                    )
                    attachments.append(attachment)
        
        return cls(
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            date=date,
            attachments=attachments,
            raw_message=msg
        )
