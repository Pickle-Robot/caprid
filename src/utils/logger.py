"""
Logging utilities for the Reolink Stream Processor.

Provides centralized logging configuration with file and console output,
rotation, and different log levels for different components.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

def setup_logger(
    name: str = "reolink_processor",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Specific log file name (if None, uses name-based default)
        log_dir: Directory to store log files
        max_file_size: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to also output to console
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = f"{name}_{timestamp}.log"
    
    log_path = os.path.join(log_dir, log_file)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_file_size,
        backupCount=backup_count
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all levels
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_stream_logger() -> logging.Logger:
    """Get a logger specifically for stream operations."""
    return setup_logger(
        name="stream_handler",
        log_level="INFO",
        log_file="stream_operations.log"
    )

def get_motion_logger() -> logging.Logger:
    """Get a logger specifically for motion detection."""
    return setup_logger(
        name="motion_detection",
        log_level="INFO", 
        log_file="motion_detection.log"
    )

def get_recording_logger() -> logging.Logger:
    """Get a logger specifically for recording operations."""
    return setup_logger(
        name="recording",
        log_level="INFO",
        log_file="recording_operations.log"
    )

def setup_application_logging(config: dict) -> None:
    """
    Set up application-wide logging based on configuration.
    
    Args:
        config: Configuration dictionary with logging settings
    """
    log_config = config.get('logging', {})
    
    # Main application logger
    setup_logger(
        name="reolink_processor",
        log_level=log_config.get('level', 'INFO'),
        log_file=log_config.get('file', 'reolink_processor.log'),
        log_dir=log_config.get('dir', 'logs'),
        console_output=log_config.get('console', True)
    )
    
    # Component-specific loggers
    get_stream_logger()
    get_motion_logger() 
    get_recording_logger()

class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    
    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.setup_logger("my_component")
                
            def some_method(self):
                self.logger.info("Something happened")
    """
    
    def setup_logger(self, component_name: str, log_level: str = "INFO"):
        """Set up logger for this component."""
        self.logger = setup_logger(
            name=f"{self.__class__.__module__}.{self.__class__.__name__}",
            log_level=log_level,
            log_file=f"{component_name}.log"
        )

# Context manager for temporary log level changes
class TemporaryLogLevel:
    """
    Context manager to temporarily change log level.
    
    Usage:
        with TemporaryLogLevel(logger, "DEBUG"):
            # Code that needs debug logging
            pass
    """
    
    def __init__(self, logger: logging.Logger, temp_level: str):
        self.logger = logger
        self.temp_level = getattr(logging, temp_level.upper())
        self.original_level = logger.level
    
    def __enter__(self):
        self.logger.setLevel(self.temp_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)

# Performance logging decorator
def log_performance(logger: logging.Logger):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_performance(logger)
        def slow_function():
            time.sleep(1)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{func.__name__} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator

# Example usage and testing
if __name__ == "__main__":
    # Test the logging setup
    logger = setup_logger("test_logger", "DEBUG")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message") 
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test performance logging
    @log_performance(logger)
    def test_function():
        import time
        time.sleep(0.1)
        return "done"
    
    test_function()
    
    # Test temporary log level
    with TemporaryLogLevel(logger, "ERROR"):
        logger.info("This won't show")
        logger.error("This will show")
    
    logger.info("Back to normal level")
