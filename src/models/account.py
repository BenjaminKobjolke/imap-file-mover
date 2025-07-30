"""
Account model for IMAP email accounts - extends the base library Account.
"""
from dataclasses import dataclass
from typing import Optional

# Import from the imap_client_python library
# Install with: pip install git+https://github.com/BenjaminKobjolke/imap_client_python.git
from imap_client_lib import Account as BaseAccount


@dataclass
class Account(BaseAccount):
    """
    Extended Account class for the file moving application.
    Inherits IMAP configuration from base Account and adds app-specific fields.
    """
    target_folder: str = ''
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
            # Base Account fields
            name=data.get('name', ''),
            server=data.get('server', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            port=data.get('port', 993),
            use_ssl=data.get('use_ssl', True),
            # Application-specific fields
            target_folder=data.get('target_folder', ''),
            imap_move_folder=data.get('imap_move_folder')
        )
