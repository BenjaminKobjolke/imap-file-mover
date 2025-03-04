"""
Account model for IMAP email accounts.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Account:
    """
    Represents an IMAP email account configuration.
    """
    name: str
    server: str
    username: str
    password: str
    port: int
    use_ssl: bool
    target_folder: str
    imap_move_folder: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Account':
        """
        Create an Account instance from a dictionary.
        
        Args:
            data: Dictionary containing account configuration
            
        Returns:
            Account: New Account instance
        """
        return cls(
            name=data.get('name', ''),
            server=data.get('server', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            port=data.get('port', 993),
            use_ssl=data.get('use_ssl', True),
            target_folder=data.get('target_folder', ''),
            imap_move_folder=data.get('imap_move_folder')
        )
