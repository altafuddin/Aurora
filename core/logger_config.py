# In: core/logger_config.py
import logging
import sys

def setup_logger():
    """
    Set up the root logger with a timestamped format and 
    DEBUG level, replacing any existing handlers.
    """
    # Get the root logger
    logger = logging.getLogger()
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create a new handler that prints to standard output
    handler = logging.StreamHandler(sys.stdout)
    
    # Define the format: Timestamp - Log Level - Message
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Set the formatter for the handler
    handler.setFormatter(formatter)
    
    # Add the new handler to the root logger
    logger.addHandler(handler)
    
    # Set the logging level
    logger.setLevel(logging.DEBUG) # Change to logging.DEBUG for more verbose output

    logging.info("Logger configured successfully with timestamps.")