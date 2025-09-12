# IMAP File Mover

A Python application that monitors IMAP email accounts, identifies unread emails matching specific criteria, downloads their attachments to designated folders, and marks the emails as read.

## Features

- Connect to multiple IMAP email accounts
- Filter emails based on sender, subject, and attachment criteria
- Multiple attachment processing modes:
  - **Regular attachments**: Download email attachments directly
  - **URL extraction**: Extract URLs from email body and convert to PDF/Markdown
  - **Body processing**: Convert email body content to PDF/Markdown
- Support for PDF and Markdown output formats
- Per-filter target folder override capability
- Download matching attachments to configured target folders
- Mark processed emails as read
- Move processed emails to specified IMAP folders
- Run once or continuously at specified intervals

## Requirements

- Python 3.6+
- IMAPClient
- wkhtmltopdf (for HTML to PDF conversion)
- markdownify (for HTML to Markdown conversion)
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

  - **account**: Restrict filter to specific account name (optional - if not set, applies to all accounts)
  - **sender**: Partial match for email sender (optional - if not set, matches any sender)
  - **subject**: Partial match for email subject (optional - if not set, matches any subject)
  - **attachment_type**: Type of attachment processing ("attachment", "url", "body")
    - **"attachment"**: Process regular email attachments (default)
    - **"url"**: Extract URLs from email body and convert to files
    - **"body"**: Convert email body content to files
  - **target_format**: Output format ("pdf" or "md", default: "pdf")
  - **target_folder**: Override target folder for this filter (optional)
  - **attachment_extension**: File extension to match (for attachment_type="attachment")
  - **url_prefix**: URL prefix to match in email body (for attachment_type="url")
  - **url_to_attachment**: Deprecated - use attachment_type="url" and url_prefix instead

- **check_interval_minutes**: Time between email checks in minutes

  - Set to 0 to check once and exit (single run mode)
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

## Attachment Processing Modes

The application supports three different attachment processing modes:

### 1. Regular Attachments (attachment_type: "attachment")

Process traditional email attachments directly.

```json
{
  "sender": "@microsoft.com",
  "subject": "Invoice",
  "attachment_type": "attachment",
  "attachment_extension": "pdf",
  "target_format": "pdf"
}
```

### 2. URL Extraction (attachment_type: "url")

Extract URLs from email bodies and convert the web pages to files. Useful for services that send invoices as web links.

**Prerequisites:**
- Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html (for PDF output)
- Configure path in settings if needed: `"wkhtmltopdf_path": "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"`

**How it works:**
1. Searches email body for URLs matching the specified prefix
2. Downloads the HTML content from the first matching URL
3. Follows meta refresh redirects (common in invoice systems)
4. Converts to PDF or Markdown format

```json
{
  "sender": "help@paddle.com",
  "subject": "Your invoice",
  "attachment_type": "url",
  "url_prefix": "https://my.paddle.com/receipt/",
  "target_format": "pdf"
}
```

### 3. Body Processing (attachment_type: "body")

Convert email body content directly to files. Useful for emails containing structured content.

**Features:**
- Generates filename with YYYYMMDD_ prefix based on email subject
- Supports both PDF and Markdown output formats
- Can override target folder per filter

```json
{
  "sender": "help@paddle.com",
  "subject": "Your Decodo invoice",
  "attachment_type": "body",
  "target_format": "md",
  "target_folder": "E:\\[--Sync--]\\markdown"
}
```

**Notes:**
- For Markdown output: Converts HTML body to Markdown, plain text is wrapped in `<pre>` tags
- For PDF output: Only processes HTML content (plain text emails are skipped for PDF)
- PDF files have timestamp in filename, Markdown files use date prefix only

## Account-Specific Filters

You can restrict filters to specific accounts using the `account` field. This is useful when you have multiple email accounts and want different processing rules for each:

```json
{
  "account": "Obsidian",
  "sender": "b.kobjolke@xida.de",
  "subject": "privat", 
  "attachment_type": "body",
  "target_format": "md",
  "target_folder": "E:\\[--Sync--]\\Notes_Trading\\Email"
}
```

**Key Features:**
- **Account matching**: Filter only applies to the "Obsidian" account
- **Optional fields**: Both `sender` and `subject` are optional - if not specified, they match any value
- **Global filters**: Filters without the `account` field apply to all accounts

## License

MIT
