#!/usr/bin/env python3
"""
IMAP File Mover - Main entry point

This script monitors IMAP email accounts, identifies unread emails matching specific criteria,
downloads their attachments to designated folders, and marks the emails as read.
"""
import time
import sys
import os
from typing import List

from src.config.config_manager import ConfigManager
from src.email.imap_client import ImapClient
from src.models.account import Account
from src.models.email_filter import EmailFilter
from src.utils.logger import Logger


def process_account(account: Account, filters: List[EmailFilter], logger: Logger) -> int:
    """
    Process a single email account.
    
    Args:
        account: The account to process
        filters: The filters to apply
        logger: The logger instance
        
    Returns:
        int: Number of attachments processed
    """
    logger.info(f"Processing account: {account.name}")
    
    client = ImapClient(account)
    attachment_count = client.process_messages(filters)
    
    logger.info(f"Processed {attachment_count} attachments for account {account.name}")
    return attachment_count


def main():
    """
    Main entry point for the application.
    """
    # Initialize logger
    logger = Logger()
    
    # Load configuration
    config_manager = ConfigManager()
    if not config_manager.load():
        logger.critical("Failed to load configuration. Exiting.")
        sys.exit(1)
        
    # Configure logger with settings
    logger.configure(
        config_manager.get_log_level(),
        config_manager.get_log_retention_days()
    )
    
    # Now that the logger is configured, log the start message
    logger.info("Starting IMAP File Mover")
    
    # Get accounts and filters
    accounts = config_manager.get_accounts()
    filters = config_manager.get_filters()
    
    if not accounts:
        logger.critical("No accounts configured. Exiting.")
        sys.exit(1)
        
    if not filters:
        logger.critical("No filters configured. Exiting.")
        sys.exit(1)
        
    # Get check interval
    check_interval = config_manager.get_check_interval()
    
    # Process accounts
    total_attachments = 0
    
    try:
        while True:
            logger.info("Starting email check cycle")
            
            cycle_attachments = 0
            for account in accounts:
                attachments = process_account(account, filters, logger)
                cycle_attachments += attachments
                
            total_attachments += cycle_attachments
            logger.info(f"Completed check cycle. Processed {cycle_attachments} attachments.")
            
            # If check_interval is 0 or not set, exit after one run
            if check_interval <= 0:
                logger.info(f"Single check completed. Total attachments processed: {total_attachments}")
                break
                
            # Otherwise sleep until next check
            logger.info(f"Sleeping for {check_interval} minutes until next check")
            time.sleep(check_interval * 60)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Exiting.")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        sys.exit(1)
        
    logger.info("IMAP File Mover completed successfully")


if __name__ == "__main__":
    main()
