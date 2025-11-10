import logging
import os
from logging.handlers import RotatingFileHandler
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# Email configuration


class AlertLogger:
    """A logger wrapper that can send email alerts for significant events"""
    def __init__(self, logger):
        self._logger = logger
        
    def __getattr__(self, name):
        # Forward all standard logging methods to the wrapped logger
        return getattr(self._logger, name)
    
    def alert(self, subject, message, level="info"):
        """Log a message and send an email alert"""
        # Log the message using the specified level
        getattr(self._logger, level)(message)

def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger("books_crawler")
    logger.setLevel(log_level)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    # Create file handler for logging to a file
    # Rotate log file after 1MB, keep 5 backup files
    log_file = os.getenv("LOG_FILE", "books_crawler.log")
    fh = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    fh.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to handlers
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    
    # Wrap logger with AlertLogger
    return AlertLogger(logger)

logger = setup_logging()
