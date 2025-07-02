"""
Legacy utility functions - compatibility layer for existing code
"""

import re
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def validate_forward_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize forwarding settings"""
    validated = {}

    try:
        # Forward mode
        forward_mode = settings.get("forward_mode", "copy")
        if forward_mode in ["copy", "forward", "quote"]:
            validated["forward_mode"] = forward_mode
        else:
            validated["forward_mode"] = "copy"

        # Boolean settings
        bool_settings = [
            "preserve_sender", "add_caption", "filter_media", "filter_text",
            "filter_forwarded", "filter_links", "remove_links", "remove_mentions",
            "duplicate_check"
        ]

        for setting in bool_settings:
            validated[setting] = bool(settings.get(setting, False))

        # Integer settings
        validated["delay_min"] = max(0, int(settings.get("delay_min", 0)))
        validated["delay_max"] = max(validated["delay_min"], int(settings.get("delay_max", 5)))
        validated["max_message_length"] = max(1, min(4096, int(settings.get("max_message_length", 4096))))

        # Text settings
        custom_caption = settings.get("custom_caption")
        if custom_caption and len(str(custom_caption)) <= 1024:
            validated["custom_caption"] = str(custom_caption)

        # JSON settings
        keyword_filters = settings.get("keyword_filters")
        if isinstance(keyword_filters, list):
            validated["keyword_filters"] = [str(kw)[:100] for kw in keyword_filters[:50]]

        replace_text = settings.get("replace_text")
        if isinstance(replace_text, dict):
            validated["replace_text"] = {str(k)[:100]: str(v)[:100] 
                                       for k, v in list(replace_text.items())[:20]}

        return validated

    except Exception as e:
        logger.error(f"Error validating forward settings: {e}")
        return {
            "forward_mode": "copy",
            "preserve_sender": False,
            "add_caption": False,
            "filter_media": False,
            "filter_text": False,
            "filter_forwarded": False,
            "filter_links": False,
            "delay_min": 0,
            "delay_max": 5,
            "remove_links": False,
            "remove_mentions": False,
            "duplicate_check": True,
            "max_message_length": 4096
        }


def generate_task_name(source_count: int, target_count: int) -> str:
    """Generate default task name"""
    timestamp = datetime.now().strftime("%m%d_%H%M")
    return f"Task_{source_count}to{target_count}_{timestamp}"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON string"""
    try:
        if not json_str:
            return default
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing JSON: {e}")
        return default


def safe_json_dumps(obj: Any) -> str:
    """Safely dump object to JSON string"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.error(f"Error dumping JSON: {e}")
        return "{}"


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Format datetime for display"""
    if not dt:
        return "Never"

    try:
        if format_type == "full":
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "date":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time":
            return dt.strftime("%H:%M:%S")
        elif format_type == "relative":
            now = datetime.now()
            diff = now - dt

            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return "Invalid date"


def extract_chat_id(text: str) -> Optional[int]:
    """Extract chat ID from various formats"""
    try:
        # Direct numeric ID
        if text.lstrip('-').isdigit():
            return int(text)

        # Username format (@username)
        if text.startswith('@'):
            return text[1:]  # Return username without @

        # t.me/username format
        if 't.me/' in text:
            username = text.split('t.me/')[-1].split('?')[0]
            return username

        # joinchat/invite link
        if 'joinchat/' in text or '+' in text:
            return text  # Return as is for invite links

        return None

    except Exception as e:
        logger.error(f"Error extracting chat ID from '{text}': {e}")
        return None


def parse_chat_identifier(identifier: str) -> Dict[str, Any]:
    """Parse chat identifier and return type and value"""
    try:
        result = {"type": "unknown", "value": None, "original": identifier}

        if not identifier:
            return result

        # Numeric ID (channel/group)
        if identifier.lstrip('-').isdigit():
            result["type"] = "id"
            result["value"] = int(identifier)
            return result

        # Username
        if identifier.startswith('@'):
            result["type"] = "username"
            result["value"] = identifier[1:]
            return result

        # t.me link
        if 't.me/' in identifier:
            username = identifier.split('t.me/')[-1].split('?')[0]
            if username.isdigit():
                result["type"] = "id"
                result["value"] = int(username)
            else:
                result["type"] = "username"
                result["value"] = username
            return result

        # Invite link
        if 'joinchat/' in identifier or identifier.startswith('+'):
            result["type"] = "invite"
            result["value"] = identifier
            return result

        # Assume username if no prefix
        result["type"] = "username"
        result["value"] = identifier
        return result

    except Exception as e:
        logger.error(f"Error parsing chat identifier '{identifier}': {e}")
        return {"type": "error", "value": None, "original": identifier}


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    if not text:
        return ""

    special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def validate_telegram_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize Telegram data"""
    validated = {}

    try:
        # Basic user data
        if "id" in data:
            validated["telegram_id"] = int(data["id"])

        if "username" in data and data["username"]:
            validated["username"] = str(data["username"])[:255]

        if "first_name" in data and data["first_name"]:
            validated["first_name"] = str(data["first_name"])[:255]

        if "last_name" in data and data["last_name"]:
            validated["last_name"] = str(data["last_name"])[:255]

        # Chat data
        if "title" in data and data["title"]:
            validated["title"] = str(data["title"])[:255]

        if "type" in data:
            validated["type"] = str(data["type"])

        return validated

    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return {}


def format_number(num: Union[int, float], precision: int = 1) -> str:
    """Format large numbers with K, M, B suffixes"""
    try:
        if num == 0:
            return "0"

        if abs(num) < 1000:
            return str(int(num))
        elif abs(num) < 1000000:
            return f"{num/1000:.{precision}f}K"
        elif abs(num) < 1000000000:
            return f"{num/1000000:.{precision}f}M"
        else:
            return f"{num/1000000000:.{precision}f}B"

    except Exception as e:
        logger.error(f"Error formatting number: {e}")
        return str(num)


def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"