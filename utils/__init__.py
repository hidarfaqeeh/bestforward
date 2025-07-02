"""
Utilities package for Telegram Forwarding Bot

This package contains performance-critical utilities and helpers
to fix the dashboard performance issues.
"""

# Core utilities for fixing dashboard issues
from .callback_router import CallbackRouter
from .database_cache import DatabaseCache
from .memory_manager import MemoryManager

__all__ = [
    "CallbackRouter",
    "DatabaseCache", 
    "MemoryManager"
]

__version__ = "1.0.0"
__description__ = "Performance and reliability utilities for dashboard"