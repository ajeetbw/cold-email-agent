"""
Logger setup for the cold email agent.
Logs to both file and console.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, log_file: str = None, level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Formatter
    formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if provided)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger(
    name='cold_email_agent',
    log_file='./logs/agent.log',
    level='INFO'
)
