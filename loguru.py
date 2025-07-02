"""
Temporary loguru compatibility module

This module provides a loguru-compatible interface using standard Python logging.
This is a temporary solution until proper loguru can be installed.
"""

from utils.logging_compat import logger

# Make logger available for direct import
__all__ = ['logger']