# IMAP File Mover

A Python application that monitors IMAP email accounts, identifies unread emails matching specific criteria, downloads their attachments to designated folders, and marks the emails as read.

## Features

- Connect to multiple IMAP email accounts
- Filter emails based on sender, subject, and attachment extension
- Extract URLs from email body and convert HTML to PDF
- Download matching attachments to configured target folders
- Mark processed emails as read
- Move processed emails to specified IMAP folders
- Run once or continuously at specified intervals

## Requirements

- Python 3.6+
- IMAPClient
- wkhtmltopdf (for HTML to PDF conversion)
- Internet connection

## Installation

1. Clone this repository
2. Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html (required for URL to PDF conversion)
3. Run `install.bat` to set up the virtual environment and install dependencies

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
  - **attachment_extension**: File extension to match for attachments (for regular attachments)
  - **url_to_attachment**: URL prefix to match in email body (for URL-based attachments that will be converted to PDF)

- **check_interval_minutes**: Time between email checks in minutes

  - Set to 0 to check once and exit
  - Set to a positive number to run continuously with the specified interval

- **log_level**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

- **log_retention_days**: Number of days to keep log files
  - Default is 3 days if not specified
  - Logs older than this will be automatically deleted

- **wkhtmltopdf_path**: Path to wkhtmltopdf executable (optional)
  - Set to null or omit to use automatic detection
  - Example: `"C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"`
  - Required for URL to PDF conversion feature

## Usage

1. Configure your settings in `settings.json`
2. Run `run.bat` to start the application

## URL-based Attachment Feature

The application supports extracting URLs from email bodies and converting them to PDF. This is useful for services that send invoices as web pages instead of PDF attachments.

### Prerequisites:

- Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html
- Either add it to your PATH or configure the path in `settings.json`:
  ```json
  "wkhtmltopdf_path": "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
  ```

### How it works:

1. When a filter includes `url_to_attachment`, the application searches the email body for URLs starting with that prefix
2. If a matching URL is found, it downloads the HTML content
3. The application follows meta refresh redirects (common in invoice systems)
4. The final HTML page is converted to PDF and saved to the target folder

### Example configuration:

```json
{
  "sender": "help@paddle.com",
  "subject": "Your invoice",
  "url_to_attachment": "https://my.paddle.com/receipt/"
}
```

This filter will:
- Match emails from help@paddle.com with "Your invoice" in the subject
- Find URLs in the email starting with "https://my.paddle.com/receipt/"
- Download the HTML from that URL and convert it to PDF

## License

MIT
