# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IMAP File Mover is a Python application that monitors IMAP email accounts, filters emails based on configured criteria, downloads matching attachments to local folders, and marks emails as processed. The application extends the external `imap_client_python` library for core IMAP functionality.

## Key Commands

### Development Setup
```bash
# Install dependencies and create virtual environment
install.bat

# Activate virtual environment manually
venv\Scripts\activate.bat
```

### Running the Application
```bash
# Run the application (uses virtual environment)
run.bat

# Or run directly with Python
python main.py
```

### Testing
No automated test suite is currently configured. Manual testing involves:
1. Configuring `settings.json` with test email accounts
2. Running `main.py` and verifying attachment downloads
3. Checking logs in `logs/` directory for errors

## Architecture

### Core Components

1. **Main Entry Point** (`main.py`): Orchestrates the application lifecycle, processes accounts in cycles, handles configuration loading

2. **IMAP Client** (`src/email/imap_client.py`): Extends `BaseImapClient` from the external library, adds filtering logic and custom logging with the `important()` method

3. **Configuration Management** (`src/config/config_manager.py`): Handles loading and validation of `settings.json`, provides access to accounts and filters

4. **Models**:
   - `Account` (`src/models/account.py`): Extends base library's Account with `target_folder` and `imap_move_folder` fields
   - `EmailFilter` (`src/models/email_filter.py`): Defines filter criteria for matching emails
   - External models used: `EmailMessage` and `Attachment` from `imap_client_lib`

5. **Custom Logger** (`src/utils/logger.py`): Application-specific logger with `important()` method for highlighting key operations

### External Dependency

The project depends on the `imap_client_python` library from GitHub:
```
git+https://github.com/BenjaminKobjolke/imap_client_python.git
```

This library provides:
- Base `Account` and `ImapClient` classes
- `EmailMessage` and `Attachment` models
- Core IMAP operations (connect, disconnect, get messages, mark as read, move to folder)

### Configuration Structure

The application uses `settings.json` (created from `settings_example.json` if not exists):
- `accounts`: List of IMAP accounts with connection details and target folders
- `filters`: Email matching criteria (sender, subject, attachment extension)
- `check_interval_minutes`: 0 for single run, >0 for continuous monitoring
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_retention_days`: Automatic log cleanup period

### Processing Flow

1. Load configuration from `settings.json`
2. For each account:
   - Connect to IMAP server
   - Fetch unread messages
   - Apply filters to identify matching emails
   - Download matching attachments to `target_folder`
   - Mark messages as read
   - Optionally move to `imap_move_folder`
3. Sleep for `check_interval_minutes` or exit if 0

## Windows Environment

This is a Windows-based project using:
- Batch files for setup and execution (`install.bat`, `run.bat`)
- Windows path separators in configuration
- Virtual environment in `venv\` directory