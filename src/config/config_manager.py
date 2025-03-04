"""
Configuration manager for loading and parsing application settings.
"""
import json
import os
from typing import List, Dict, Any, Optional

from src.models.account import Account
from src.models.email_filter import EmailFilter


class ConfigManager:
    """
    Manages application configuration settings.
    """
    
    def __init__(self, config_path: str = 'settings.json'):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config_data = {}
        self.accounts = []
        self.filters = []
        self.check_interval_minutes = 0
        self.log_level = "INFO"
        self.log_retention_days = 3  # Default to 3 days
        
    def load(self) -> bool:
        """
        Load and parse the configuration file.
        If settings.json doesn't exist but settings_example.json does,
        create settings.json from the example.
        
        Returns:
            bool: True if configuration was loaded successfully, False otherwise
        """
        try:
            # If settings.json doesn't exist, try to create it from settings_example.json
            if not os.path.exists(self.config_path):
                example_path = 'settings_example.json'
                if os.path.exists(example_path):
                    print(f"Creating {self.config_path} from {example_path}")
                    with open(example_path, 'r') as f:
                        example_data = f.read()
                    with open(self.config_path, 'w') as f:
                        f.write(example_data)
                    print(f"Created {self.config_path}. Please edit it with your settings.")
                else:
                    print(f"Configuration file {self.config_path} not found and no example file available.")
                    return False
            
            # Load the configuration file
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
                
            # Parse accounts
            self.accounts = [
                Account.from_dict(account_data)
                for account_data in self.config_data.get('accounts', [])
            ]
            
            # Parse filters
            self.filters = [
                EmailFilter.from_dict(filter_data)
                for filter_data in self.config_data.get('filters', [])
            ]
            
            # Parse other settings
            self.check_interval_minutes = self.config_data.get('check_interval_minutes', 0)
            self.log_level = self.config_data.get('log_level', 'INFO')
            self.log_retention_days = self.config_data.get('log_retention_days', 3)
            
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
            
    def get_accounts(self) -> List[Account]:
        """
        Get the list of configured accounts.
        
        Returns:
            List[Account]: List of account configurations
        """
        return self.accounts
        
    def get_filters(self) -> List[EmailFilter]:
        """
        Get the list of configured email filters.
        
        Returns:
            List[EmailFilter]: List of email filters
        """
        return self.filters
        
    def get_check_interval(self) -> int:
        """
        Get the check interval in minutes.
        
        Returns:
            int: Check interval in minutes
        """
        return self.check_interval_minutes
        
    def get_log_level(self) -> str:
        """
        Get the configured log level.
        
        Returns:
            str: Log level
        """
        return self.log_level
        
    def get_log_retention_days(self) -> int:
        """
        Get the configured log retention days.
        
        Returns:
            int: Log retention days
        """
        return self.log_retention_days
