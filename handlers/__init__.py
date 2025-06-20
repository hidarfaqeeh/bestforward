"""
Handlers package for Telegram Forwarding Bot
"""

from .admin import AdminHandlers
from .tasks import TaskHandlers
from .sources import SourceHandlers
from .targets import TargetHandlers

__all__ = [
    "AdminHandlers",
    "TaskHandlers",
    "SourceHandlers", 
    "TargetHandlers"
]
