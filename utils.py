"""
Utility functions for Telegram Forwarding Bot
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import json
from loguru import logger
from datetime import datetime


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


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


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


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

    return filename or "unnamed_file"


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


def create_progress_bar(current: int, total: int, width: int = 20) -> str:
    """Create a text progress bar"""
    try:
        if total <= 0:
            return "█" * width

        progress = min(current / total, 1.0)
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int(progress * 100)

        return f"{bar} {percentage}%"

    except Exception as e:
        logger.error(f"Error creating progress bar: {e}")
        return "Error"


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


def parse_time_string(time_str: str) -> Optional[int]:
    """Parse time string like '1h30m' into seconds"""
    try:
        if not time_str:
            return None

        # Remove spaces
        time_str = time_str.replace(' ', '').lower()

        # Parse different formats
        total_seconds = 0

        # Hours
        if 'h' in time_str:
            hours_match = re.search(r'(\d+)h', time_str)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600

        # Minutes
        if 'm' in time_str:
            minutes_match = re.search(r'(\d+)m', time_str)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60

        # Seconds
        if 's' in time_str:
            seconds_match = re.search(r'(\d+)s', time_str)
            if seconds_match:
                total_seconds += int(seconds_match.group(1))

        # If no units specified, assume seconds
        if not any(unit in time_str for unit in ['h', 'm', 's']):
            if time_str.isdigit():
                total_seconds = int(time_str)

        return total_seconds if total_seconds > 0 else None

    except Exception as e:
        logger.error(f"Error parsing time string '{time_str}': {e}")
        return None


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


def clean_text(text: str, remove_urls: bool = False, remove_mentions: bool = False) -> str:
    """Clean text by removing URLs, mentions, etc."""
    if not text:
        return ""

    try:
        # Remove URLs
        if remove_urls:
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
            text = re.sub(r't\.me/[^\s]+', '', text)

        # Remove mentions
        if remove_mentions:
            text = re.sub(r'@\w+', '', text)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    except Exception as e:
        logger.error(f"Error cleaning text: {e}")
        return text


def is_valid_telegram_token(token: str) -> bool:
    """Validate Telegram bot token format"""
    if not token:
        return False

    # Telegram bot token format: BOT_ID:BOT_TOKEN
    pattern = r'^\d+:[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, token))


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


async def retry_on_error(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
    """Retry function on error"""
    last_exception = None

    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")

    raise last_exception


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


class AsyncLock:
    """Simple async lock implementation"""

    def __init__(self):
        self._locked = False
        self._waiters = []

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

    async def acquire(self):
        while self._locked:
            future = asyncio.Future()
            self._waiters.append(future)
            try:
                await future
            except:
                self._waiters.remove(future)
                raise

        self._locked = True

    def release(self):
        if not self._locked:
            raise RuntimeError("Lock not acquired")

        self._locked = False

        if self._waiters:
            future = self._waiters.pop(0)
            if not future.cancelled():
                future.set_result(None)


def get_emoji_for_status(status: str) -> str:
    """Get emoji for status"""
    emojis = {
        "active": "🟢",
        "inactive": "🔴",
        "success": "✅",
        "failed": "❌",
        "pending": "🟡",
        "stopped": "⏹️",
        "running": "▶️",
        "paused": "⏸️",
        "warning": "⚠️",
        "error": "🚫",
        "info": "ℹ️"
    }

    return emojis.get(status.lower(), "❓")