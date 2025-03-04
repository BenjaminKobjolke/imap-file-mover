"""
Logger utility for application-wide logging.
"""
import logging
import os
import glob
import re
from datetime import datetime, timedelta
import atexit


class ConditionalFileHandler(logging.Handler):
    """
    A handler that only writes to a file if messages were logged.
    """
    
    def __init__(self, filename, level=logging.NOTSET):
        super().__init__(level)
        self.filename = filename
        self.buffer = []
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
    def emit(self, record):
        self.buffer.append(record)
        
    def flush(self):
        if self.buffer:
            # Only create the file if there are messages
            try:
                with open(self.filename, 'a') as f:
                    for record in self.buffer:
                        msg = self.formatter.format(record)
                        f.write(msg + '\n')
                self.buffer = []
            except Exception:
                self.handleError(None)


class Logger:
    """
    Handles application logging with configurable levels.
    """
    
    _instance = None
    
    def __new__(cls):
        """
        Singleton pattern to ensure only one logger instance exists.
        
        Returns:
            Logger: The singleton logger instance
        """
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, retention_days: int = 3):
        """
        Initialize the logger if it hasn't been initialized yet.
        
        Args:
            retention_days: Number of days to keep log files
        """
        if self._initialized:
            return
            
        self.logger = logging.getLogger('imap_file_mover')
        self.logger.setLevel(logging.WARNING)  # Default to WARNING level
        self._initialized = True
        self.retention_days = retention_days
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Clean up old log files
        self.cleanup_old_logs()
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Default to WARNING level
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add console handler
        self.logger.addHandler(console_handler)
        
        # Set up conditional file handler
        log_filename = f"logs/imap_file_mover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.file_handler = ConditionalFileHandler(log_filename, logging.WARNING)
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)
        
        # Register flush method to be called at exit
        atexit.register(self.flush_logs)
        
    def configure(self, log_level: str, retention_days: int = None):
        """
        Configure the logger with the specified log level and retention days.
        
        Args:
            log_level: The log level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            retention_days: Number of days to keep log files
        """
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        for handler in self.logger.handlers:
            handler.setLevel(level)
            
        if retention_days is not None:
            self.retention_days = retention_days
            self.cleanup_old_logs()
            
    def debug(self, message: str):
        """
        Log a debug message.
        
        Args:
            message: The message to log
        """
        self.logger.debug(message)
        
    def info(self, message: str):
        """
        Log an info message.
        
        Args:
            message: The message to log
        """
        self.logger.info(message)
        
    def warning(self, message: str):
        """
        Log a warning message.
        
        Args:
            message: The message to log
        """
        self.logger.warning(message)
        
    def error(self, message: str):
        """
        Log an error message.
        
        Args:
            message: The message to log
        """
        self.logger.error(message)
        
    def critical(self, message: str):
        """
        Log a critical message.
        
        Args:
            message: The message to log
        """
        self.logger.critical(message)
        
    def important(self, message: str):
        """
        Log an important message that will always be logged regardless of the log level,
        but with INFO level instead of CRITICAL.
        
        Args:
            message: The message to log
        """
        # Save the current log level
        current_level = self.logger.level
        current_handler_levels = {}
        
        try:
            # Temporarily set the log level to INFO for all handlers
            self.logger.setLevel(logging.INFO)
            for handler in self.logger.handlers:
                current_handler_levels[handler] = handler.level
                handler.setLevel(logging.INFO)
                
            # Log the message at INFO level
            self.logger.info(message)
        finally:
            # Restore the original log levels
            self.logger.setLevel(current_level)
            for handler, level in current_handler_levels.items():
                handler.setLevel(level)
        
    def cleanup_old_logs(self):
        """
        Delete log files older than the retention period.
        """
        try:
            # Get all log files
            log_files = glob.glob('logs/imap_file_mover_*.log')
            
            # Get the cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            # Extract date from filename and delete old files
            for log_file in log_files:
                match = re.search(r'imap_file_mover_(\d{8})_', log_file)
                if match:
                    date_str = match.group(1)
                    try:
                        file_date = datetime.strptime(date_str, '%Y%m%d')
                        if file_date < cutoff_date:
                            os.remove(log_file)
                            print(f"Deleted old log file: {log_file}")
                    except ValueError:
                        # Skip files with invalid date format
                        continue
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")
    
    def flush_logs(self):
        """
        Flush any buffered log messages to disk.
        """
        if hasattr(self, 'file_handler'):
            self.file_handler.flush()
