"""
Configuration management for Telegram Forwarding Bot
"""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the bot"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables"""
        # Bot configuration
        self.bot_token = os.getenv("BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Telegram API credentials for userbot
        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        self.string_session = os.getenv("STRING_SESSION")
        
        # Database configuration
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            # Construct from individual components if DATABASE_URL not provided
            pg_host = os.getenv("PGHOST", "localhost")
            pg_port = os.getenv("PGPORT", "5432")
            pg_user = os.getenv("PGUSER", "postgres")
            pg_password = os.getenv("PGPASSWORD", "")
            pg_database = os.getenv("PGDATABASE", "telegram_bot")
            
            self.database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        
        # Webhook configuration
        self.webhook_host = os.getenv("WEBHOOK_HOST", "")
        self.webhook_port = int(os.getenv("WEBHOOK_PORT", "5000"))
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "webhook_secret_token_2024")
        self.use_webhook = bool(self.webhook_host and not self.webhook_host.startswith("localhost"))
        
        # Security configuration
        self.admin_user_ids = self._parse_admin_ids(os.getenv("ADMIN_USER_IDS", ""))
        self.encryption_key = os.getenv("ENCRYPTION_KEY", "your-32-char-encryption-key-here")
        
        # Bot settings
        self.max_forwarding_delay = int(os.getenv("MAX_FORWARDING_DELAY", "1"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "1"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "1"))
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "logs/bot.log")
        
        # Rate limiting
        self.rate_limit_messages = int(os.getenv("RATE_LIMIT_MESSAGES", "30"))
        self.rate_limit_period = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
        
        logger.info("Configuration loaded successfully")
        logger.debug(f"Webhook mode: {self.use_webhook}")
        logger.debug(f"Admin users: {len(self.admin_user_ids)}")
        logger.debug(f"Userbot enabled: {bool(self.string_session)}")
    
    def _parse_admin_ids(self, admin_ids_str: str) -> list[int]:
        """Parse admin user IDs from string"""
        if not admin_ids_str:
            return []
        
        try:
            return [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
        except ValueError as e:
            logger.error(f"Invalid admin user IDs format: {e}")
            return []
    
    def toggle_webhook_mode(self) -> bool:
        """Toggle between webhook and polling mode"""
        self.use_webhook = not self.use_webhook
        logger.info(f"Switched to {'webhook' if self.use_webhook else 'polling'} mode")
        return self.use_webhook
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admin_user_ids
    
    def add_admin(self, user_id: int) -> bool:
        """Add admin user"""
        if user_id not in self.admin_user_ids:
            self.admin_user_ids.append(user_id)
            logger.info(f"Added admin user: {user_id}")
            return True
        return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove admin user"""
        if user_id in self.admin_user_ids:
            self.admin_user_ids.remove(user_id)
            logger.info(f"Removed admin user: {user_id}")
            return True
        return False
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration and return errors if any"""
        errors = []
        
        if not self.bot_token:
            errors.append("BOT_TOKEN is required")
        
        if self.use_webhook:
            if not self.webhook_url:
                errors.append("WEBHOOK_URL is required for webhook mode")
            if not self.webhook_secret:
                errors.append("WEBHOOK_SECRET is recommended for webhook mode")
        
        if self.string_session and (not self.api_id or not self.api_hash):
            errors.append("API_ID and API_HASH are required when using STRING_SESSION")
        
        if not self.database_url:
            errors.append("Database configuration is incomplete")
        
        if len(self.encryption_key) < 32:
            errors.append("ENCRYPTION_KEY should be at least 32 characters long")
        
        return len(errors) == 0, errors
    
    def get_config_summary(self) -> dict:
        """Get configuration summary for display"""
        return {
            "mode": "webhook" if self.use_webhook else "polling",
            "userbot_enabled": bool(self.string_session),
            "admin_count": len(self.admin_user_ids),
            "webhook_port": self.webhook_port if self.use_webhook else None,
            "database_configured": bool(self.database_url),
            "log_level": self.log_level
        }
