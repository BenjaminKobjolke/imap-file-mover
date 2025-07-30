# Migration to imap_client_python Library

This project has been refactored to use the external `imap_client_python` library for core IMAP functionality.

## Changes Made

1. **Account Model** (`src/models/account.py`)
   - Now extends `BaseAccount` from the library
   - Adds application-specific fields: `target_folder` and `imap_move_folder`

2. **IMAP Client** (`src/email/imap_client.py`)
   - Now extends `BaseImapClient` from the library
   - Only contains application-specific functionality (filtering and custom logging)
   - Reuses base methods like `connect()`, `disconnect()`, `get_unread_messages()`, etc.

3. **Email Message Model**
   - Removed local `src/models/email_message.py`
   - Now uses `EmailMessage` and `Attachment` from the library

4. **Dependencies** (`requirements.txt`)
   - Added the library from GitHub: `git+https://github.com/BenjaminKobjolke/imap_client_python.git`
   - The library includes `IMAPClient` as a dependency

## Installation

To install the project with the new library:

```bash
pip install -r requirements.txt
```

Or install the library directly:

```bash
pip install git+https://github.com/BenjaminKobjolke/imap_client_python.git
```

## Benefits

1. **Reusable Library**: The core IMAP functionality is now in a separate library that can be used in other projects
2. **Cleaner Separation**: Application-specific code (filtering, custom logging) is clearly separated from generic IMAP functionality
3. **Easier Maintenance**: Updates to core IMAP functionality can be made in the library without touching application code
4. **Better Testing**: The library can be tested independently of the application

## Application-Specific Features

The following features remain in this application:

1. **Email Filters** (`EmailFilter` class) - For matching emails based on sender, subject, and attachment extensions
2. **Custom Logger** (`Logger` class) - Application-specific logging with the `important()` method
3. **File Moving Logic** - Processing messages based on filters and saving attachments to configured folders