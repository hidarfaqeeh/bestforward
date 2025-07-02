"""
Database models for Telegram Forwarding Bot
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, 
    Integer, String, Text, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    """User model for storing Telegram users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Task(Base):
    """Task model for storing forwarding tasks"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False, default="bot")  # 'bot' or 'userbot'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    sources = relationship("Source", back_populates="task", cascade="all, delete-orphan")
    targets = relationship("Target", back_populates="task", cascade="all, delete-orphan")
    settings = relationship("TaskSettings", back_populates="task", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ForwardingLog", back_populates="task")
    statistics = relationship("TaskStatistics", back_populates="task", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_task_user_active", "user_id", "is_active"),
        Index("idx_task_type_active", "task_type", "is_active"),
    )
    
    def __repr__(self):
        return f"<Task(id={self.id}, name={self.name}, type={self.task_type}, active={self.is_active})>"


class Source(Base):
    """Source model for storing source channels/chats"""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_title = Column(String(255), nullable=True)
    chat_username = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=True)  # 'channel', 'group', 'supergroup'
    is_active = Column(Boolean, default=True, nullable=False)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="sources")
    
    # Indexes
    __table_args__ = (
        Index("idx_source_task_active", "task_id", "is_active"),
        Index("idx_source_chat_id", "chat_id"),
    )
    
    def __repr__(self):
        return f"<Source(id={self.id}, task_id={self.task_id}, chat_id={self.chat_id}, title={self.chat_title})>"


class Target(Base):
    """Target model for storing target channels/chats"""
    __tablename__ = "targets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_title = Column(String(255), nullable=True)
    chat_username = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=True)  # 'channel', 'group', 'supergroup'
    is_active = Column(Boolean, default=True, nullable=False)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="targets")
    
    # Indexes
    __table_args__ = (
        Index("idx_target_task_active", "task_id", "is_active"),
        Index("idx_target_chat_id", "chat_id"),
    )
    
    def __repr__(self):
        return f"<Target(id={self.id}, task_id={self.task_id}, chat_id={self.chat_id}, title={self.chat_title})>"


class MessageDuplicate(Base):
    """Model for tracking message duplicates"""
    __tablename__ = "message_duplicates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    message_hash = Column(String(255), nullable=False)  # Hash of message content
    first_seen = Column(DateTime, default=func.now(), nullable=False)
    last_seen = Column(DateTime, default=func.now(), onupdate=func.now())
    count = Column(Integer, default=1, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_duplicate_task_hash", "task_id", "message_hash", unique=True),
        Index("idx_duplicate_task_id", "task_id"),
    )


class TaskSettings(Base):
    """Task settings model for storing task-specific configurations"""
    __tablename__ = "task_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, unique=True)
    
    # Forwarding settings
    forward_mode = Column(String(50), default="copy", nullable=False)  # 'copy', 'forward', 'quote'
    preserve_sender = Column(Boolean, default=False, nullable=False)
    add_caption = Column(Boolean, default=False, nullable=False)
    custom_caption = Column(Text, nullable=True)
    
    # Filter settings
    filter_media = Column(Boolean, default=False, nullable=False)
    filter_text = Column(Boolean, default=False, nullable=False)
    filter_forwarded = Column(Boolean, default=False, nullable=False)
    filter_links = Column(Boolean, default=False, nullable=False)
    filter_inline_buttons = Column(Boolean, default=False, nullable=False)  # Block transparent buttons
    filter_duplicates = Column(Boolean, default=False, nullable=False)  # Block duplicate messages
    filter_language = Column(Boolean, default=False, nullable=False)  # Language filtering
    # filter_bots column removed - not implemented
    language_filter_mode = Column(String(50), default="blacklist", nullable=False)  # 'whitelist' or 'blacklist'
    allowed_languages = Column(JSON, nullable=True)  # List of allowed/blocked languages
    keyword_filters = Column(JSON, nullable=True)  # List of keywords to filter
    keyword_filter_mode = Column(String(50), default="blacklist", nullable=False)  # 'whitelist' or 'blacklist'
    
    # Granular media type filters
    allow_photos = Column(Boolean, default=True, nullable=False)
    allow_videos = Column(Boolean, default=True, nullable=False)
    allow_documents = Column(Boolean, default=True, nullable=False)
    allow_audio = Column(Boolean, default=True, nullable=False)
    allow_voice = Column(Boolean, default=True, nullable=False)
    allow_video_notes = Column(Boolean, default=True, nullable=False)
    allow_stickers = Column(Boolean, default=True, nullable=False)
    allow_animations = Column(Boolean, default=True, nullable=False)
    allow_contacts = Column(Boolean, default=True, nullable=False)
    allow_locations = Column(Boolean, default=True, nullable=False)
    allow_venues = Column(Boolean, default=True, nullable=False)
    allow_polls = Column(Boolean, default=True, nullable=False)
    allow_dice = Column(Boolean, default=True, nullable=False)
    
    # Timing settings
    delay_min = Column(Integer, default=0, nullable=False)  # Minimum delay in seconds
    delay_max = Column(Integer, default=5, nullable=False)  # Maximum delay in seconds
    
    # Content modification
    remove_links = Column(Boolean, default=False, nullable=False)
    remove_mentions = Column(Boolean, default=False, nullable=False)
    replace_text = Column(JSON, nullable=True)  # Dictionary of text replacements
    
    # Advanced settings
    duplicate_check = Column(Boolean, default=True, nullable=False)
    max_message_length = Column(Integer, default=4096, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="settings")
    
    def __repr__(self):
        return f"<TaskSettings(id={self.id}, task_id={self.task_id}, mode={self.forward_mode})>"


class ForwardingLog(Base):
    """Forwarding log model for tracking forwarded messages"""
    __tablename__ = "forwarding_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    source_chat_id = Column(BigInteger, nullable=False)
    target_chat_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    forwarded_message_id = Column(BigInteger, nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False)  # 'success', 'failed', 'filtered', 'duplicate'
    error_message = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)  # Processing time in milliseconds
    
    # Message metadata
    message_type = Column(String(50), nullable=True)  # 'text', 'photo', 'video', etc.
    message_size = Column(Integer, nullable=True)  # Message size in bytes
    
    processed_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_log_task_status", "task_id", "status"),
        Index("idx_log_processed_at", "processed_at"),
        Index("idx_log_source_message", "source_chat_id", "message_id"),
    )
    
    def __repr__(self):
        return f"<ForwardingLog(id={self.id}, task_id={self.task_id}, status={self.status})>"


class TaskStatistics(Base):
    """Task statistics model for storing task performance metrics"""
    __tablename__ = "task_statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, unique=True)
    
    # Message counters
    messages_processed = Column(Integer, default=0, nullable=False)
    messages_forwarded = Column(Integer, default=0, nullable=False)
    messages_failed = Column(Integer, default=0, nullable=False)
    messages_filtered = Column(Integer, default=0, nullable=False)
    messages_duplicate = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_processing_time = Column(Integer, default=0, nullable=False)  # Average time in milliseconds
    total_processing_time = Column(BigInteger, default=0, nullable=False)  # Total time in milliseconds
    
    # Activity tracking
    first_message_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    total_uptime = Column(BigInteger, default=0, nullable=False)  # Total uptime in seconds
    
    # Error tracking
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    consecutive_errors = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="statistics")
    
    def __repr__(self):
        return f"<TaskStatistics(id={self.id}, task_id={self.task_id}, forwarded={self.messages_forwarded})>"


class SystemSettings(Base):
    """System settings model for storing global bot configurations"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), nullable=False, default="string")  # 'string', 'integer', 'boolean', 'json'
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value_type={self.value_type})>"


class UserSession(Base):
    """User session model for storing user interaction states"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_data = Column(JSON, nullable=True)
    current_state = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("idx_session_user_state", "user_id", "current_state"),
        Index("idx_session_expires", "expires_at"),
    )
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, state={self.current_state})>"
