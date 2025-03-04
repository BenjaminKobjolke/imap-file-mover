# IMAP File Mover

A Python application that monitors IMAP email accounts, identifies unread emails matching specific criteria, downloads their attachments to designated folders, and marks the emails as read.

## Features

- Connect to multiple IMAP email accounts
- Filter emails based on sender, subject, and attachment extension
- Download matching attachments to configured target folders
- Mark processed emails as read
- Move processed emails to specified IMAP folders
- Run once or continuously at specified intervals

## Requirements

- Python 3.6+
- IMAPClient
- Internet connection

## Installation

1. Clone this repository
2. Run `install.bat` to set up the virtual environment and install dependencies

## Configuration

A sample configuration file `settings_example.json` is provided as a template. The application will automatically create a `settings.json` file from this example if it doesn't exist. Edit the `settings.json` file to configure your email accounts and filter criteria:

```json
{
  "accounts": [
    {
      "name": "Work Email",
      "server": "imap.example.com",
      "username": "user@example.com",
      "password": "password123",
      "port": 993,
      "use_ssl": true,
      "target_folder": "D:/Downloads/Work",
      "imap_move_folder": "Processed"
    }
  ],
  "filters": [
    {
      "sender": "@microsoft.com",
      "subject": "Invoice for",
      "attachment_extension": "pdf"
    }
  ],
  "check_interval_minutes": 0,
  "log_level": "INFO",
  "log_retention_days": 3
}
```

### Configuration Options

- **accounts**: List of IMAP accounts to monitor

  - **name**: Friendly name for the account
  - **server**: IMAP server address
  - **username**: Email account username
  - **password**: Email account password
  - **port**: IMAP server port (usually 993 for SSL)
  - **use_ssl**: Whether to use SSL for connection
  - **target_folder**: Local folder where attachments will be saved
  - **imap_move_folder**: IMAP folder where processed emails will be moved (optional)

- **filters**: List of filter criteria for matching emails

  - **sender**: Partial match for email sender
  - **subject**: Partial match for email subject
  - **attachment_extension**: File extension to match for attachments

- **check_interval_minutes**: Time between email checks in minutes

  - Set to 0 to check once and exit
  - Set to a positive number to run continuously with the specified interval

- **log_level**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

- **log_retention_days**: Number of days to keep log files
  - Default is 3 days if not specified
  - Logs older than this will be automatically deleted

## Usage

1. Configure your settings in `settings.json`
2. Run `run.bat` to start the application

## License

MIT
