"""
Logging compatibility layer - provides loguru-like interface using standard logging
"""

import logging
import sys
from typing import Any, Optional

class LoguruCompatLogger:
    """Compatibility class that provides loguru-like interface"""
    
    def __init__(self, name: str = "telegram_bot"):
        self._logger = logging.getLogger(name)
        
        # Set up basic console handler if no handlers exist
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
    
    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        self._logger.exception(message, *args, **kwargs)
    
    def success(self, message: str, *args, **kwargs):
        """Loguru-specific method - map to info"""
        self._logger.info(f"SUCCESS: {message}", *args, **kwargs)
    
    def trace(self, message: str, *args, **kwargs):
        """Loguru-specific method - map to debug"""
        self._logger.debug(f"TRACE: {message}", *args, **kwargs)


# Create global logger instance
logger = LoguruCompatLogger()

# For modules that need to import specific logger
def get_logger(name: str = "telegram_bot") -> LoguruCompatLogger:
    """Get a logger instance with specific name"""
    return LoguruCompatLogger(name)