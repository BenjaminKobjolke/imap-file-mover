"""
Markdown frontmatter generator with placeholder replacement for Obsidian properties.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import yaml


class FrontmatterGenerator:
    """
    Generates YAML frontmatter for markdown files with placeholder replacement.
    """

    @staticmethod
    def replace_placeholders(value: Any, email_data: Dict[str, Any]) -> Any:
        """
        Replace placeholders in a value with actual email data.

        Args:
            value: The value to process (can be string, list, dict, or other types)
            email_data: Dictionary containing email data for placeholder replacement

        Returns:
            Any: The value with placeholders replaced
        """
        if isinstance(value, str):
            # Replace all supported placeholders
            replacements = {
                '[email_from]': email_data.get('from', ''),
                '[email_to]': email_data.get('to', ''),
                '[email_subject]': email_data.get('subject', ''),
                '[email_datetime]': email_data.get('datetime', ''),
                '[email_date]': email_data.get('date', ''),
                '[email_time]': email_data.get('time', '')
            }

            for placeholder, replacement in replacements.items():
                value = value.replace(placeholder, str(replacement))

            return value

        elif isinstance(value, list):
            # Process each item in the list
            return [FrontmatterGenerator.replace_placeholders(item, email_data) for item in value]

        elif isinstance(value, dict):
            # Process each value in the dictionary
            return {
                key: FrontmatterGenerator.replace_placeholders(val, email_data)
                for key, val in value.items()
            }

        else:
            # Return as-is for other types (numbers, booleans, etc.)
            return value

    @staticmethod
    def generate_frontmatter(properties: Dict[str, Any], email_data: Dict[str, Any]) -> str:
        """
        Generate YAML frontmatter from properties configuration with placeholder replacement.

        Args:
            properties: Dictionary of property names and values (may contain placeholders)
            email_data: Dictionary containing email data for placeholder replacement

        Returns:
            str: YAML frontmatter string with --- delimiters
        """
        if not properties:
            return ""

        # Replace placeholders in all property values
        processed_properties = FrontmatterGenerator.replace_placeholders(properties, email_data)

        # Convert to YAML format
        yaml_content = yaml.dump(
            processed_properties,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Add YAML frontmatter delimiters
        frontmatter = f"---\n{yaml_content}---\n\n"

        return frontmatter

    @staticmethod
    def format_email_datetime(email_message: Any) -> Dict[str, str]:
        """
        Extract and format email datetime information.

        Args:
            email_message: EmailMessage object from imap_client_lib

        Returns:
            Dict[str, str]: Dictionary containing formatted datetime strings
        """
        datetime_data = {}

        try:
            # Get the email date
            if hasattr(email_message, 'date') and email_message.date:
                email_date = email_message.date

                # Handle both datetime objects and strings
                if isinstance(email_date, datetime):
                    dt = email_date
                elif isinstance(email_date, str):
                    # Try to parse common email date formats
                    # Email dates are typically in RFC 2822 format
                    from email.utils import parsedate_to_datetime
                    try:
                        dt = parsedate_to_datetime(email_date)
                    except:
                        # Fallback to current datetime if parsing fails
                        dt = datetime.now()
                else:
                    dt = datetime.now()

                # Format datetime in different ways
                datetime_data['datetime'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                datetime_data['date'] = dt.strftime("%Y-%m-%d")
                datetime_data['time'] = dt.strftime("%H:%M:%S")
            else:
                # Use current datetime as fallback
                now = datetime.now()
                datetime_data['datetime'] = now.strftime("%Y-%m-%d %H:%M:%S")
                datetime_data['date'] = now.strftime("%Y-%m-%d")
                datetime_data['time'] = now.strftime("%H:%M:%S")

        except Exception:
            # If anything goes wrong, use current datetime
            now = datetime.now()
            datetime_data['datetime'] = now.strftime("%Y-%m-%d %H:%M:%S")
            datetime_data['date'] = now.strftime("%Y-%m-%d")
            datetime_data['time'] = now.strftime("%H:%M:%S")

        return datetime_data

    @staticmethod
    def build_email_data(email_message: Any) -> Dict[str, str]:
        """
        Build email data dictionary from an EmailMessage object.

        Args:
            email_message: EmailMessage object from imap_client_lib

        Returns:
            Dict[str, str]: Dictionary containing email data
        """
        email_data = {}

        # Extract basic email fields
        email_data['from'] = getattr(email_message, 'from_address', '')
        email_data['to'] = getattr(email_message, 'to_address', '')
        email_data['subject'] = getattr(email_message, 'subject', '')

        # Extract and format datetime
        datetime_data = FrontmatterGenerator.format_email_datetime(email_message)
        email_data.update(datetime_data)

        return email_data
