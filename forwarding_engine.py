"""
Forwarding Engine - Core message forwarding logic
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import re
import random

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
try:
    from pyrogram import Client
    from pyrogram.errors import RPCError
except ImportError:
    Client = None
    RPCError = None

try:
    from telethon import TelegramClient
    from telethon.errors import RPCError as TelethonRPCError
except ImportError:
    TelegramClient = None
    TelethonRPCError = None
from loguru import logger
import psutil
import pytz
from googletrans import Translator

from database import Database
from security import SecurityManager
from modules.channel_monitor import ChannelMonitor
from modules.statistics import StatisticsManager
import json


class ForwardingEngine:
    """Core forwarding engine for message processing"""
    
    def __init__(self, database: Database, bot: Bot, userbot: Optional[Any], 
                 security_manager: SecurityManager):
        self.database = database
        self.bot = bot
        self.userbot = userbot
        self.security_manager = security_manager
        
        # Engine state
        self.running = False
        self.start_time = None
        self.monitors: Dict[int, ChannelMonitor] = {}
        self.statistics = StatisticsManager(database)
        
        # Performance tracking
        self.messages_processed = 0
        self.successful_forwards = 0
        self.failed_forwards = 0
        self.processing_times: List[float] = []
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}
        self.rate_limit_window = 60  # 1 minute window
        self.max_requests_per_minute = 30  # Max 30 requests per minute per chat
        
        # Translation service
        self.translator = Translator()
        
        # Advanced features cache with TTL
        self._settings_cache: Dict[int, Dict[str, Any]] = {}
        self._cache_timestamp: Dict[int, float] = {}
        self.duplicate_tracker: Set[str] = set()
        self._cache_size_limit = 1000  # Limit cache size
        self._duplicate_cleanup_interval = 3600  # Clean duplicates every hour
        
        # Task cache
        self.active_tasks_cache: Dict[int, Dict[str, Any]] = {}
        self.cache_last_update = None
        self.cache_ttl = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize the forwarding engine"""
        try:
            await self.statistics.initialize()
            await self._load_active_tasks()
            logger.success("Forwarding engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize forwarding engine: {e}")
            raise
    
    async def start(self):
        """Start the forwarding engine"""
        if self.running:
            logger.warning("Forwarding engine is already running")
            return
        
        try:
            self.running = True
            self.start_time = datetime.now()
            
            # Start monitoring active tasks
            await self._start_monitoring()
            
            # Start background tasks
            asyncio.create_task(self._background_tasks())
            
            logger.success("Forwarding engine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start forwarding engine: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the forwarding engine"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Stop all monitors
            for monitor in self.monitors.values():
                await monitor.stop()
            
            self.monitors.clear()
            logger.success("Forwarding engine stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping forwarding engine: {e}")
    
    async def _load_active_tasks(self):
        """Load active tasks from database"""
        try:
            tasks = await self.database.get_active_tasks()
            self.active_tasks_cache = {task["id"]: task for task in tasks}
            self.cache_last_update = datetime.now()
            
            logger.info(f"Loaded {len(tasks)} active tasks")
            
        except Exception as e:
            logger.error(f"Failed to load active tasks: {e}")
            raise
    
    async def _start_monitoring(self):
        """Start monitoring for all active tasks"""
        for task_id, task in self.active_tasks_cache.items():
            try:
                await self._start_task_monitoring(task_id, task)
            except Exception as e:
                logger.error(f"Failed to start monitoring for task {task_id}: {e}")
    
    async def _start_task_monitoring(self, task_id: int, task: Dict[str, Any]):
        """Start monitoring for a specific task with automatic fallback to Bot API"""
        try:
            # Get task sources
            sources = await self.database.get_task_sources(task_id)
            if not sources:
                logger.warning(f"No sources found for task {task_id}")
                return
            
            # Get task settings
            settings = await self.database.get_task_settings(task_id)
            
            # Check if userbot is needed and available
            use_userbot = (task["task_type"] == "userbot" and 
                          self.userbot and 
                          hasattr(self.userbot, 'is_connected'))
            
            # If userbot task but userbot is not available, switch to bot mode
            if task["task_type"] == "userbot" and not use_userbot:
                logger.warning(f"Task {task_id} configured for userbot but userbot unavailable, switching to Bot API mode")
                # Update task type in database to bot mode
                try:
                    await self.database.execute_command(
                        "UPDATE tasks SET task_type = 'bot' WHERE id = $1", task_id
                    )
                    task["task_type"] = "bot"  # Update local cache
                    logger.info(f"Task {task_id} automatically switched to Bot API mode")
                except Exception as update_error:
                    logger.error(f"Failed to update task {task_id} to bot mode: {update_error}")
            
            # Create and start monitor
            monitor = ChannelMonitor(
                task_id=task_id,
                task=task,
                sources=sources,
                settings=settings,
                bot=self.bot,
                userbot=self.userbot if use_userbot else None,
                forwarding_engine=self
            )
            
            await monitor.start()
            self.monitors[task_id] = monitor
            
            logger.info(f"Started monitoring for task {task_id} ({len(sources)} sources) using {'userbot' if use_userbot else 'Bot API'}")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring for task {task_id}: {e}")
            # Try to start with Bot API as final fallback
            if task.get("task_type") == "userbot":
                try:
                    logger.warning(f"Attempting Bot API fallback for task {task_id}")
                    task["task_type"] = "bot"
                    await self.database.execute_command(
                        "UPDATE tasks SET task_type = 'bot' WHERE id = $1", task_id
                    )
                    
                    monitor = ChannelMonitor(
                        task_id=task_id,
                        task=task,
                        sources=sources,
                        settings=settings,
                        bot=self.bot,
                        userbot=None,
                        forwarding_engine=self
                    )
                    
                    await monitor.start()
                    self.monitors[task_id] = monitor
                    logger.info(f"Task {task_id} successfully started with Bot API fallback")
                    
                except Exception as fallback_error:
                    logger.error(f"Bot API fallback also failed for task {task_id}: {fallback_error}")
    
    async def _stop_task_monitoring(self, task_id: int):
        """Stop monitoring for a specific task"""
        if task_id in self.monitors:
            try:
                await self.monitors[task_id].stop()
                del self.monitors[task_id]
                logger.info(f"Stopped monitoring for task {task_id}")
            except Exception as e:
                logger.error(f"Error stopping monitor for task {task_id}: {e}")
    
    async def process_channel_message(self, chat_id: int, message: Any) -> bool:
        """Process incoming channel message and check if it needs forwarding"""
        try:
            # Find all tasks that monitor this source channel
            for task_id, task in self.active_tasks_cache.items():
                if not task.get("is_active"):
                    continue
                
                # Check if this chat_id is a source for this task
                sources = await self.database.get_task_sources(task_id)
                source_chat_ids = [s["chat_id"] for s in sources if s["is_active"]]
                
                if chat_id in source_chat_ids:
                    logger.info(f"Processing channel message from {chat_id} for task {task_id}")
                    success = await self.process_message(task_id, chat_id, message)
                    return success
            
            return False  # No matching task found
            
        except Exception as e:
            logger.error(f"Error processing channel message from {chat_id}: {e}")
            return False

    async def process_edited_message(self, chat_id: int, message: Any) -> bool:
        """Process edited message for synchronization with target channels"""
        try:
            logger.info(f"DEBUG: Checking edited message from {chat_id}, active tasks: {list(self.active_tasks_cache.keys())}")
            
            # Find which task this channel belongs to
            for task_id, task in self.active_tasks_cache.items():
                source_chat_ids = [source['chat_id'] for source in task.get('sources', [])]
                logger.info(f"DEBUG: Task {task_id} sources: {source_chat_ids}")
                
                if chat_id in source_chat_ids:
                    logger.info(f"Processing edited message from {chat_id} for task {task_id}")
                    return await self._sync_edited_message(task_id, chat_id, message)
            
            logger.warning(f"No active task found for edited message from {chat_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error processing edited message from {chat_id}: {e}")
            return False
    
    async def _handle_manual_approval(self, task_id: int, message: Any, settings: Dict[str, Any]):
        """Handle manual approval by sending message to admins for review"""
        try:
            # Get admin users from security manager
            admin_users = await self._get_admin_users()
            if not admin_users:
                logger.warning("No admin users found for manual approval")
                return
            
            # Store message for approval
            approval_id = await self._store_pending_approval(task_id, message)
            if not approval_id:
                logger.error("Failed to store pending approval")
                return
            
            # Create approval keyboard
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Use shorter callback data to ensure it works
            approve_data = f"approve_{approval_id}"
            reject_data = f"reject_{approval_id}"
            
            # Ensure callback data is not too long
            if len(approve_data) > 64:
                approve_data = f"approve_{approval_id}"[:64]
            if len(reject_data) > 64:
                reject_data = f"reject_{approval_id}"[:64]
                
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ موافق - نشر",
                        callback_data=approve_data
                    ),
                    InlineKeyboardButton(
                        text="❌ رفض - إلغاء", 
                        callback_data=reject_data
                    )
                ]
            ])
            
            # Send message to each admin
            for admin_id in admin_users:
                try:
                    # Always forward the original message first
                    await self.bot.forward_message(
                        chat_id=admin_id,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                    
                    # Then send approval request with buttons
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 *طلب موافقة على النشر*\n\n"
                             f"🔢 رقم المهمة: {task_id}\n"
                             f"📤 من القناة: {message.chat.title if hasattr(message.chat, 'title') else 'غير معروف'}\n\n"
                             f"هل تريد نشر هذه الرسالة إلى جميع القنوات الهدف؟",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                        
                    logger.info(f"Manual approval request sent to admin {admin_id} for task {task_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send approval request to admin {admin_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error in manual approval handling: {e}")
    
    async def _get_admin_users(self) -> list:
        """Get list of admin user IDs"""
        try:
            # Get admin users from security manager
            query = "SELECT user_id FROM user_permissions WHERE is_admin = true AND is_active = true"
            result = await self.database.execute_query(query)
            return [row['user_id'] for row in result]
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return []
    
    async def _store_pending_approval(self, task_id: int, message: Any) -> Optional[int]:
        """Store pending approval in database"""
        try:
            import json
            from datetime import datetime
            
            # Prepare message data with complete media information
            message_data = {
                'message_id': message.message_id,
                'chat_id': message.chat.id,
                'text': getattr(message, 'text', None),
                'caption': getattr(message, 'caption', None),
                'media_type': self._get_message_media_type(message),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add media-specific file_id based on media type
            media_type = message_data['media_type']
            if media_type == 'photo' and hasattr(message, 'photo') and message.photo:
                message_data['file_id'] = message.photo[-1].file_id  # Get highest resolution
            elif media_type == 'video' and hasattr(message, 'video') and message.video:
                message_data['file_id'] = message.video.file_id
            elif media_type == 'document' and hasattr(message, 'document') and message.document:
                message_data['file_id'] = message.document.file_id
            elif media_type == 'audio' and hasattr(message, 'audio') and message.audio:
                message_data['file_id'] = message.audio.file_id
            elif media_type == 'voice' and hasattr(message, 'voice') and message.voice:
                message_data['file_id'] = message.voice.file_id
            elif media_type == 'video_note' and hasattr(message, 'video_note') and message.video_note:
                message_data['file_id'] = message.video_note.file_id
            elif media_type == 'sticker' and hasattr(message, 'sticker') and message.sticker:
                message_data['file_id'] = message.sticker.file_id
            elif media_type == 'animation' and hasattr(message, 'animation') and message.animation:
                message_data['file_id'] = message.animation.file_id
            
            # Store inline keyboard if present
            if hasattr(message, 'reply_markup') and message.reply_markup:
                try:
                    # Convert InlineKeyboardMarkup to dict for JSON storage
                    keyboard_data = []
                    if hasattr(message.reply_markup, 'inline_keyboard'):
                        for row in message.reply_markup.inline_keyboard:
                            button_row = []
                            for button in row:
                                button_data = {
                                    'text': button.text,
                                    'url': getattr(button, 'url', None),
                                    'callback_data': getattr(button, 'callback_data', None)
                                }
                                button_row.append(button_data)
                            keyboard_data.append(button_row)
                    message_data['inline_keyboard'] = keyboard_data
                except Exception as e:
                    logger.error(f"Error storing inline keyboard: {e}")
                    message_data['inline_keyboard'] = None
            
            # Insert into manual_approvals table
            query = """
                INSERT INTO manual_approvals (task_id, source_message_id, source_chat_id, message_data, status, created_at)
                VALUES ($1, $2, $3, $4, 'pending', CURRENT_TIMESTAMP)
                RETURNING id
            """
            result = await self.database.execute_query(
                query, task_id, message.message_id, message.chat.id, json.dumps(message_data)
            )
            
            if result:
                approval_id = result[0]['id']
                logger.info(f"Stored pending approval with ID {approval_id}")
                return approval_id
                
        except Exception as e:
            logger.error(f"Error storing pending approval: {e}")
        
        return None
    
    async def handle_approval_callback(self, callback_data: str, user_id: int) -> bool:
        """Handle approval/rejection callback from admin"""
        try:
            # Parse callback data: approve_123 or reject_123
            action, approval_id = callback_data.split('_', 1)
            approval_id = int(approval_id)
            
            # Check if user is admin
            admin_users = await self._get_admin_users()
            if user_id not in admin_users:
                return False
            
            # Get approval record
            query = "SELECT * FROM manual_approvals WHERE id = $1 AND status = 'pending'"
            result = await self.database.execute_query(query, approval_id)
            
            if not result:
                logger.warning(f"Approval {approval_id} not found or already processed")
                return False
            
            approval = result[0]
            task_id = approval['task_id']
            
            if action == "approve":
                # Process the approval - forward the message
                await self._process_approved_message(approval)
                
                # Update status
                update_query = """
                    UPDATE manual_approvals 
                    SET status = 'approved', approved_by = $1, approved_at = CURRENT_TIMESTAMP 
                    WHERE id = $2
                """
                await self.database.execute_command(update_query, user_id, approval_id)
                
                logger.info(f"Message {approval_id} approved by admin {user_id}")
                return True
                
            elif action == "reject":
                # Update status to rejected
                update_query = """
                    UPDATE manual_approvals 
                    SET status = 'rejected', approved_by = $1, approved_at = CURRENT_TIMESTAMP 
                    WHERE id = $2
                """
                await self.database.execute_command(update_query, user_id, approval_id)
                
                logger.info(f"Message {approval_id} rejected by admin {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling approval callback: {e}")
        
        return False
    
    async def _process_approved_message(self, approval: dict):
        """Process an approved message for forwarding"""
        try:
            import json
            
            task_id = approval['task_id']
            message_data = json.loads(approval['message_data'])
            
            # Get task settings
            settings = await self.database.get_task_settings(task_id)
            if not settings:
                settings = self._get_default_settings()
            
            # Temporarily disable manual mode to allow forwarding
            settings['manual_mode'] = False
            
            # Get targets
            targets = await self.database.get_task_targets(task_id)
            active_targets = [t for t in targets if t.get("is_active")]
            
            if not active_targets:
                logger.warning(f"No active targets found for approved message in task {task_id}")
                return
            
            # Create a mock message object for forwarding
            class MockMessage:
                def __init__(self, data):
                    self.message_id = data['message_id']
                    self.chat = type('Chat', (), {'id': data['chat_id']})()
                    self.text = data.get('text')
                    self.caption = data.get('caption')
                    self.media_type = data.get('media_type', 'text')
            
            mock_message = MockMessage(message_data)
            
            # Forward to all targets
            success_count = 0
            for target in active_targets:
                try:
                    # Apply delay
                    await self._apply_delay(settings)
                    
                    # Forward message with full processing and settings
                    if message_data.get('text'):
                        # Apply text processing and transformations
                        processed_text = message_data['text']
                        
                        # Apply text cleaning
                        if settings.get('text_cleaner_settings'):
                            processed_text = await self._apply_text_cleaning(processed_text, settings.get('text_cleaner_settings', {}))
                        
                        # Apply translation if enabled
                        if settings.get('auto_translate', False):
                            processed_text = await self._apply_auto_translation(processed_text, settings)
                        
                        # Apply delay before sending
                        await self._apply_delay(settings)
                        
                        # Rebuild inline keyboard for text messages too
                        reply_markup = None
                        message_data = json.loads(approval['message_data'])
                        if message_data.get('inline_keyboard'):
                            try:
                                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                keyboard_rows = []
                                for row in message_data['inline_keyboard']:
                                    button_row = []
                                    for button_data in row:
                                        if button_data.get('url'):
                                            button = InlineKeyboardButton(
                                                text=button_data['text'],
                                                url=button_data['url']
                                            )
                                        elif button_data.get('callback_data'):
                                            button = InlineKeyboardButton(
                                                text=button_data['text'],
                                                callback_data=button_data['callback_data']
                                            )
                                        else:
                                            continue
                                        button_row.append(button)
                                    if button_row:
                                        keyboard_rows.append(button_row)
                                if keyboard_rows:
                                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
                            except Exception as e:
                                logger.error(f"Error rebuilding inline keyboard for text: {e}")
                                reply_markup = None
                        
                        result = await self.bot.send_message(
                            chat_id=target['chat_id'],
                            text=processed_text,
                            reply_markup=reply_markup,
                            disable_web_page_preview=not settings.get('link_preview', False),
                            disable_notification=settings.get('silent_mode', False)
                        )
                        forwarded_id = result.message_id if result else None
                    else:
                        # Handle media messages
                        try:
                            message_data = json.loads(approval['message_data'])
                            media_type = message_data.get('media_type', 'unknown')
                            file_id = message_data.get('file_id')
                            
                            if not file_id:
                                logger.error(f"No file_id found for media message. Media type: {media_type}, Data: {message_data}")
                                continue
                                
                            # Process caption with settings
                            caption = message_data.get('caption', '')
                            if caption and settings.get('text_cleaner_settings'):
                                caption = await self._apply_text_cleaning(caption, settings.get('text_cleaner_settings', {}))
                            if caption and settings.get('auto_translate', False):
                                caption = await self._apply_auto_translation(caption, settings)
                            
                            # Apply delay before sending
                            await self._apply_delay(settings)
                            
                            # Rebuild inline keyboard if present
                            reply_markup = None
                            if message_data.get('inline_keyboard'):
                                try:
                                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                    keyboard_rows = []
                                    for row in message_data['inline_keyboard']:
                                        button_row = []
                                        for button_data in row:
                                            if button_data.get('url'):
                                                button = InlineKeyboardButton(
                                                    text=button_data['text'],
                                                    url=button_data['url']
                                                )
                                            elif button_data.get('callback_data'):
                                                button = InlineKeyboardButton(
                                                    text=button_data['text'],
                                                    callback_data=button_data['callback_data']
                                                )
                                            else:
                                                continue
                                            button_row.append(button)
                                        if button_row:
                                            keyboard_rows.append(button_row)
                                    if keyboard_rows:
                                        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
                                except Exception as e:
                                    logger.error(f"Error rebuilding inline keyboard: {e}")
                                    reply_markup = None
                            
                            if media_type == 'photo':
                                result = await self.bot.send_photo(
                                    chat_id=target["chat_id"],
                                    photo=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'video':
                                result = await self.bot.send_video(
                                    chat_id=target["chat_id"],
                                    video=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'document':
                                result = await self.bot.send_document(
                                    chat_id=target["chat_id"],
                                    document=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'audio':
                                result = await self.bot.send_audio(
                                    chat_id=target["chat_id"],
                                    audio=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'voice':
                                result = await self.bot.send_voice(
                                    chat_id=target["chat_id"],
                                    voice=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'video_note':
                                result = await self.bot.send_video_note(
                                    chat_id=target["chat_id"],
                                    video_note=file_id,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'sticker':
                                result = await self.bot.send_sticker(
                                    chat_id=target["chat_id"],
                                    sticker=file_id,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            elif media_type == 'animation':
                                result = await self.bot.send_animation(
                                    chat_id=target["chat_id"],
                                    animation=file_id,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    disable_notification=settings.get('silent_mode', False)
                                )
                            else:
                                logger.warning(f"Unsupported media type: {media_type}")
                                continue
                                
                            forwarded_id = result.message_id if result else None
                            logger.info(f"Media message ({media_type}) forwarded successfully to {target['chat_id']}")
                            
                        except Exception as media_error:
                            logger.error(f"Error forwarding media message: {media_error}")
                            continue
                    
                    if forwarded_id:
                        await self._log_forwarding(
                            task_id, approval['source_chat_id'], target["chat_id"], 
                            approval['source_message_id'], forwarded_id, "success", "Manual approval"
                        )
                        success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error forwarding approved message to target {target['chat_id']}: {e}")
            
            logger.info(f"Approved message forwarded to {success_count} targets")
            
        except Exception as e:
            logger.error(f"Error processing approved message: {e}")
    
    def _get_message_media_type(self, message) -> str:
        """Get message media type"""
        if hasattr(message, 'photo') and message.photo:
            return 'photo'
        elif hasattr(message, 'video') and message.video:
            return 'video'
        elif hasattr(message, 'document') and message.document:
            return 'document'
        elif hasattr(message, 'audio') and message.audio:
            return 'audio'
        elif hasattr(message, 'voice') and message.voice:
            return 'voice'
        elif hasattr(message, 'video_note') and message.video_note:
            return 'video_note'
        else:
            return 'text'

    async def _sync_edited_message(self, task_id: int, source_chat_id: int, message: Any) -> bool:
        """Synchronize edited message with all target channels"""
        try:
            message_id = message.message_id
            
            # Check if sync_edits is enabled for this task
            settings = await self.database.get_task_settings(task_id)
            if not settings or not settings.get('sync_edits', False):
                logger.info(f"Edit synchronization disabled for task {task_id}")
                return False
            
            # Find all forwarded messages for this original message
            query = """
            SELECT target_message_ids FROM message_tracking 
            WHERE task_id = $1 AND source_message_id = $2
            ORDER BY created_at DESC LIMIT 1
            """
            result = await self.database.execute_query(query, task_id, message_id)
            
            if not result:
                logger.info(f"No forwarded messages found for edited message {message_id}")
                return False
            
            target_message_ids = result[0].get('target_message_ids')
            if not target_message_ids:
                return False
            
            import json
            try:
                target_mappings = json.loads(target_message_ids) if isinstance(target_message_ids, str) else target_message_ids
            except json.JSONDecodeError:
                logger.error(f"Failed to parse target message mappings for message {message_id}")
                return False
            
            # Get task targets
            task = self.active_tasks_cache.get(task_id)
            if not task:
                return False
            
            sync_count = 0
            
            # Sync edits to all target channels
            for target in task.get('targets', []):
                target_chat_id = target['chat_id']
                
                # Find the forwarded message ID for this target
                forwarded_message_id = None
                if isinstance(target_mappings, list):
                    for mapping in target_mappings:
                        if isinstance(mapping, dict):
                            chat_key = str(target_chat_id)
                            if chat_key in mapping:
                                forwarded_message_id = mapping[chat_key]
                                break
                        elif isinstance(mapping, int):
                            forwarded_message_id = mapping
                            break
                
                if not forwarded_message_id:
                    logger.warning(f"No forwarded message found for target {target_chat_id}")
                    continue
                
                # Sync the edit
                success = await self._sync_edit_to_target(message, target_chat_id, forwarded_message_id, settings)
                if success:
                    sync_count += 1
                    logger.info(f"Synchronized edit to target {target_chat_id}, message {forwarded_message_id}")
            
            logger.info(f"Synchronized edits to {sync_count} target channels for message {message_id}")
            return sync_count > 0
            
        except Exception as e:
            logger.error(f"Error synchronizing edited message: {e}")
            return False

    async def _sync_edit_to_target(self, original_message: Any, target_chat_id: int, 
                                  forwarded_message_id: int, settings: dict) -> bool:
        """Synchronize edit to a specific target channel"""
        try:
            # Prepare edited content
            new_text = None
            new_caption = None
            new_reply_markup = None
            
            # Handle text messages
            if hasattr(original_message, 'text') and original_message.text:
                new_text = original_message.text
                
                # Apply text modifications if needed
                if settings:
                    modified_text = await self._get_modified_text(original_message, settings)
                    if modified_text:
                        new_text = modified_text
            
            # Handle media with captions
            elif hasattr(original_message, 'caption') and original_message.caption:
                new_caption = original_message.caption
                
                # Apply caption modifications if needed
                if settings:
                    # Create a temporary message object with caption as text for processing
                    class CaptionMessage:
                        def __init__(self, caption):
                            self.text = caption
                    
                    temp_message = CaptionMessage(original_message.caption)
                    modified_caption = await self._get_modified_text(temp_message, settings)
                    if modified_caption:
                        new_caption = modified_caption
            
            # Handle inline keyboard updates
            if hasattr(original_message, 'reply_markup') and original_message.reply_markup:
                # Check if buttons should be removed based on settings
                text_cleaner = settings.get('text_cleaner_settings', {}) if settings else {}
                if isinstance(text_cleaner, str):
                    import json
                    try:
                        text_cleaner = json.loads(text_cleaner)
                    except json.JSONDecodeError:
                        text_cleaner = {}
                
                should_remove_buttons = text_cleaner.get('remove_buttons', False) if isinstance(text_cleaner, dict) else False
                
                if not should_remove_buttons:
                    new_reply_markup = original_message.reply_markup
            
            # Perform the edit
            if new_text is not None:
                # Edit text message
                await self.bot.edit_message_text(
                    chat_id=target_chat_id,
                    message_id=forwarded_message_id,
                    text=new_text,
                    reply_markup=new_reply_markup,
                    disable_web_page_preview=not settings.get('link_preview', False) if settings else True
                )
                
            elif new_caption is not None:
                # Edit media caption
                await self.bot.edit_message_caption(
                    chat_id=target_chat_id,
                    message_id=forwarded_message_id,
                    caption=new_caption,
                    reply_markup=new_reply_markup
                )
                
            elif new_reply_markup is not None:
                # Edit only reply markup
                await self.bot.edit_message_reply_markup(
                    chat_id=target_chat_id,
                    message_id=forwarded_message_id,
                    reply_markup=new_reply_markup
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing edit to target {target_chat_id}: {e}")
            return False

    async def _check_day_filter(self, settings: Dict[str, Any]) -> bool:
        """Check if current day is allowed by day filter"""
        try:
            if not settings.get("day_filter_enabled", False):
                return True
            
            day_filter_settings = settings.get("day_filter_settings", {})
            if isinstance(day_filter_settings, str):
                day_filter_settings = json.loads(day_filter_settings)
            
            # Get current day of week
            current_day = datetime.now().strftime('%A').lower()
            
            # Check if current day is allowed
            return day_filter_settings.get(current_day, True)
            
        except Exception as e:
            logger.error(f"Error checking day filter: {e}")
            return True
    
    async def _check_sending_limits(self, task_id: int, settings: Dict[str, Any]) -> bool:
        """Check if sending limits allow this message"""
        try:
            if not settings.get("sending_limit_enabled", False):
                return True
            
            sending_limit_settings = settings.get("sending_limit_settings", {})
            if isinstance(sending_limit_settings, str):
                sending_limit_settings = json.loads(sending_limit_settings)
            
            per_minute = sending_limit_settings.get("per_minute", 10)
            per_hour = sending_limit_settings.get("per_hour", 100)
            per_day = sending_limit_settings.get("per_day", 1000)
            
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            current_day = now.date()
            
            # Check minute limit
            minute_count = await self.database.execute_query(
                "SELECT COALESCE(message_count, 0) as count FROM sending_stats WHERE task_id = $1 AND day = $2 AND hour = $3 AND minute = $4",
                task_id, current_day, current_hour.hour, current_minute.minute
            )
            
            if minute_count and minute_count[0]['count'] >= per_minute:
                return False
            
            # Check hour limit
            hour_count = await self.database.execute_query(
                "SELECT COALESCE(SUM(message_count), 0) as count FROM sending_stats WHERE task_id = $1 AND day = $2 AND hour = $3",
                task_id, current_day, current_hour.hour
            )
            
            if hour_count and hour_count[0]['count'] >= per_hour:
                return False
            
            # Check day limit
            day_count = await self.database.execute_query(
                "SELECT COALESCE(SUM(message_count), 0) as count FROM sending_stats WHERE task_id = $1 AND day = $2",
                task_id, current_day
            )
            
            if day_count and day_count[0]['count'] >= per_day:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking sending limits: {e}")
            return True
    
    async def _update_sending_stats(self, task_id: int):
        """Update sending statistics"""
        try:
            now = datetime.now()
            current_day = now.date()
            current_hour = now.hour
            current_minute = now.minute
            
            await self.database.execute_command(
                """INSERT INTO sending_stats (task_id, day, hour, minute, message_count)
                   VALUES ($1, $2, $3, $4, 1)
                   ON CONFLICT (task_id, day, hour, minute)
                   DO UPDATE SET message_count = sending_stats.message_count + 1""",
                task_id, current_day, current_hour, current_minute
            )
            
        except Exception as e:
            logger.error(f"Error updating sending stats: {e}")

    async def process_message(self, task_id: int, source_chat_id: int, message: Any) -> bool:
        """Process a message for forwarding"""
        start_time = time.time()
        
        try:
            # Get task and settings - always fetch fresh settings from database
            task = self.active_tasks_cache.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found in cache")
                return False
            
            # Always fetch fresh settings to avoid cache issues
            settings = await self.database.get_task_settings(task_id)
            if settings:
                logger.debug(f"Fresh settings loaded - keyword_filter_mode: {settings.get('keyword_filter_mode', 'none')}")
            if not settings:
                settings = self._get_default_settings()
            
            # Check working hours first
            if not await self._check_working_hours(task_id, settings):
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "working_hours", "Outside working hours")
                return False
            
            # Check day filter
            if not await self._check_day_filter(settings):
                logger.info(f"Message blocked by day filter for task {task_id}")
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "day_filter", "Day filter blocked message")
                return False
            
            # Check sending limits
            if not await self._check_sending_limits(task_id, settings):
                logger.info(f"Message blocked by sending limits for task {task_id}")
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "sending_limit", "Sending limit reached")
                return False
            
            # Check if message should be processed
            if not await self._should_process_message(message, settings, task_id):
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "filtered", "Message filtered by settings")
                return False
            
            # Check for duplicates
            if await self._is_duplicate(task_id, message):
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "duplicate", "Duplicate message")
                return False
            
            # Check if manual approval is enabled
            if settings.get("manual_mode", False):
                await self._handle_manual_approval(task_id, message, settings)
                await self._log_forwarding(task_id, source_chat_id, 0, message.message_id, 
                                         None, "pending_approval", "Message sent for manual approval")
                return True  # Message handled, pending approval
            
            # Get targets
            targets = await self.database.get_task_targets(task_id)
            active_targets = [t for t in targets if t.get("is_active")]
            if not active_targets:
                logger.warning(f"No targets found for task {task_id}")
                return False
            
            # Forward to all targets
            success_count = 0
            for target in targets:
                if not target["is_active"]:
                    continue
                
                try:
                    # Apply delay
                    await self._apply_delay(settings)
                    
                    # Forward message
                    forwarded_id = await self._forward_message(
                        task, settings, message, target["chat_id"], task_id
                    )
                    
                    if forwarded_id:
                        await self._log_forwarding(
                            task_id, source_chat_id, target["chat_id"], 
                            message.message_id, forwarded_id, "success"
                        )
                        
                        # Update sending stats
                        await self._update_sending_stats(task_id)
                        
                        # Store message mapping for edit synchronization if enabled
                        if settings.get("sync_edits", False) or settings.get("preserve_replies", False):
                            await self._store_message_mapping(
                                task_id, message.message_id, forwarded_id, target["chat_id"]
                            )
                        
                        success_count += 1
                    else:
                        await self._log_forwarding(
                            task_id, source_chat_id, target["chat_id"], 
                            message.message_id, None, "failed", "Failed to forward"
                        )
                        
                except Exception as e:
                    logger.error(f"Error forwarding to target {target['chat_id']}: {e}")
                    await self._log_forwarding(
                        task_id, source_chat_id, target["chat_id"], 
                        message.message_id, None, "failed", str(e)
                    )
            
            # Update statistics
            processing_time = int((time.time() - start_time) * 1000)
            self.processing_times.append(processing_time)
            self.messages_processed += 1
            
            if success_count > 0:
                self.successful_forwards += success_count
                await self.database.update_task_statistics(task_id, "success")
            else:
                self.failed_forwards += 1
                await self.database.update_task_statistics(task_id, "failed")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            processing_time = int((time.time() - start_time) * 1000)
            self.processing_times.append(processing_time)
            self.failed_forwards += 1
            return False
    
    async def _should_process_message(self, message: Any, settings: Dict[str, Any], task_id: int = None) -> bool:
        """Check if message should be processed based on comprehensive media filtering"""
        try:
            # First check: Text message filter (must be first to override other checks)
            # Check if this is a pure text message (no media attachments)
            is_pure_text = (hasattr(message, 'text') and message.text and 
                           not (hasattr(message, 'photo') and message.photo) and
                           not (hasattr(message, 'video') and message.video) and
                           not (hasattr(message, 'document') and message.document) and
                           not (hasattr(message, 'audio') and message.audio) and
                           not (hasattr(message, 'voice') and message.voice) and
                           not (hasattr(message, 'video_note') and message.video_note) and
                           not (hasattr(message, 'sticker') and message.sticker) and
                           not (hasattr(message, 'animation') and message.animation))
            
            if is_pure_text:
                logger.info(f"Pure text message detected: '{message.text[:50]}...'")
                logger.info(f"Text filter setting: allow_text = {settings.get('allow_text', True)}")
                if not settings.get("allow_text", True):
                    logger.info("Text messages are disabled - blocking message")
                    return False
            
            # Check comprehensive media type filtering
            if hasattr(message, 'photo') and message.photo:
                if not settings.get("allow_photos", True):
                    return False
            
            elif hasattr(message, 'video') and message.video:
                if not settings.get("allow_videos", True):
                    return False
            
            elif hasattr(message, 'document') and message.document:
                if not settings.get("allow_documents", True):
                    return False
            
            elif hasattr(message, 'audio') and message.audio:
                if not settings.get("allow_audio", True):
                    return False
            
            elif hasattr(message, 'voice') and message.voice:
                if not settings.get("allow_voice", True):
                    return False
            
            elif hasattr(message, 'video_note') and message.video_note:
                if not settings.get("allow_video_notes", True):
                    return False
            
            elif hasattr(message, 'sticker') and message.sticker:
                if not settings.get("allow_stickers", True):
                    return False
            
            elif hasattr(message, 'animation') and message.animation:
                if not settings.get("allow_animations", True):
                    return False
            
            elif hasattr(message, 'contact') and message.contact:
                if not settings.get("allow_contacts", True):
                    return False
            
            elif hasattr(message, 'location') and message.location:
                if not settings.get("allow_locations", True):
                    return False
            
            elif hasattr(message, 'venue') and message.venue:
                if not settings.get("allow_venues", True):
                    return False
            
            elif hasattr(message, 'poll') and message.poll:
                if not settings.get("allow_polls", True):
                    return False
            
            elif hasattr(message, 'dice') and message.dice:
                if not settings.get("allow_dice", True):
                    return False
            

            
            # Additional checks that apply to all message types
            # Check forwarded filter - block any forwarded message
            if settings.get("filter_forwarded", False):
                # Check if message is forwarded (has any forward indicators)
                is_forwarded = False
                
                # Check for forward_from (forwarded from user)
                if hasattr(message, 'forward_from') and message.forward_from:
                    is_forwarded = True
                    logger.info(f"Message is forwarded from user: {message.forward_from.first_name}")
                
                # Check for forward_from_chat (forwarded from channel/group)
                elif hasattr(message, 'forward_from_chat') and message.forward_from_chat:
                    is_forwarded = True
                    logger.info(f"Message is forwarded from chat: {message.forward_from_chat.title}")
                
                # Check for forward_sender_name (forwarded from hidden user)
                elif hasattr(message, 'forward_sender_name') and message.forward_sender_name:
                    is_forwarded = True
                    logger.info(f"Message is forwarded from hidden sender: {message.forward_sender_name}")
                
                # Check for forward_date (any forwarded message should have this)
                elif hasattr(message, 'forward_date') and message.forward_date:
                    is_forwarded = True
                    logger.info("Message has forward_date - indicating it's forwarded")
                
                # For Pyrogram messages, check additional forward fields
                elif hasattr(message, 'forward_origin') and message.forward_origin:
                    is_forwarded = True
                    logger.info("Message has forward_origin - indicating it's forwarded (Pyrogram)")
                
                if is_forwarded:
                    logger.info("BLOCKING: Message is forwarded and forwarded filter is enabled")
                    return False
                else:
                    logger.info("Message is not forwarded - allowing to proceed")
            
            # Check links filter for text messages (including usernames and mentions)
            if settings.get("filter_links", False):
                text_to_check = ""
                if hasattr(message, 'text') and message.text:
                    text_to_check = message.text
                elif hasattr(message, 'caption') and message.caption:
                    text_to_check = message.caption
                
                if text_to_check:
                    # Check for URLs, usernames, and channel mentions
                    if (re.search(r'http[s]?://|t\.me/|@\w+|#\w+', text_to_check) or
                        re.search(r'www\.|\.com|\.org|\.net|\.edu|\.gov', text_to_check)):
                        logger.info("Message blocked: contains links or mentions")
                        return False
            
            # Check inline buttons filter - block message if filter is enabled
            if settings.get("filter_inline_buttons", False):
                if hasattr(message, 'reply_markup') and message.reply_markup:
                    if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                        logger.info("BLOCKING: Message contains inline buttons and button filter is enabled")
                        return False
            else:
                # If filter is disabled, check if we should remove buttons during forwarding
                if hasattr(message, 'reply_markup') and message.reply_markup:
                    if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                        # Check if text cleaner is set to remove buttons
                        cleaner_settings = settings.get("text_cleaner_settings")
                        should_remove_buttons = False
                        if cleaner_settings:
                            import json
                            try:
                                if isinstance(cleaner_settings, str):
                                    cleaner_settings = json.loads(cleaner_settings)
                                should_remove_buttons = cleaner_settings.get("remove_inline_buttons", False)
                            except:
                                should_remove_buttons = False
                        
                        if should_remove_buttons:
                            logger.info("Message contains inline buttons - will be removed during forwarding (text cleaner)")
                        else:
                            logger.info("Message contains inline buttons - will be preserved")
            
            # Check duplicate filter
            if settings.get("filter_duplicates", False) and task_id:
                if await self._is_duplicate_message(message, task_id):
                    logger.info("Message blocked: duplicate detected")
                    return False
            
            # Check language filter
            if settings.get("filter_language", False):
                if not await self._check_language_filter(message, settings):
                    logger.info("Message blocked: language filter")
                    return False
            
            # Check length filter for text messages - ONLY BLOCKING CHECK
            if hasattr(message, 'text') and message.text:
                length_filter_settings = settings.get("length_filter_settings")
                if length_filter_settings:
                    import json
                    try:
                        # Parse length filter settings if it's a string
                        if isinstance(length_filter_settings, str):
                            length_filter_settings = json.loads(length_filter_settings)
                        
                        if length_filter_settings.get("enabled", False):
                            text_length = len(message.text)
                            min_length = length_filter_settings.get("min_length", 0)
                            max_length = length_filter_settings.get("max_length", 4096)
                            action_mode = length_filter_settings.get("action_mode", "block")
                            
                            logger.info(f"Length filter check: text_length={text_length}, min={min_length}, max={max_length}, action={action_mode}")
                            
                            # Check minimum length
                            if min_length > 0 and text_length < min_length:
                                logger.info(f"Message blocked: length {text_length} < min {min_length}")
                                return False
                            
                            # Check maximum length - ONLY block here, truncate/summarize handled in forwarding
                            if text_length > max_length and action_mode == "block":
                                logger.info(f"Message blocked: length {text_length} > max {max_length}")
                                return False
                                    
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.error(f"Error parsing length filter settings: {e}")
            
            # Early check: if text cleaning will remove all content, skip processing
            if hasattr(message, 'text') and message.text:
                # Check if text cleaning would make message empty
                if settings.get("text_cleaner_settings"):
                    try:
                        import json
                        cleaner_settings = settings.get("text_cleaner_settings", "{}")
                        if isinstance(cleaner_settings, str):
                            cleaner_settings = json.loads(cleaner_settings)
                        
                        # If remove_links is enabled, simulate cleaning to check if text becomes empty
                        if cleaner_settings.get("remove_links", False):
                            import re
                            test_text = message.text
                            
                            # Apply same cleaning logic as in _apply_text_cleaning
                            test_text = re.sub(r'https?://[^\s]+', '', test_text)
                            test_text = re.sub(r'ftp://[^\s]+', '', test_text)
                            test_text = re.sub(r'www\.[^\s]+', '', test_text)
                            test_text = re.sub(r't\.me/[^\s]+', '', test_text)
                            test_text = re.sub(r'telegram\.me/[^\s]+', '', test_text)
                            test_text = re.sub(r'telegram\.dog/[^\s]+', '', test_text)
                            test_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', test_text)
                            test_text = re.sub(r'\b[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}\b', '', test_text)
                            
                            # If text becomes empty or only whitespace after cleaning
                            if not test_text.strip():
                                logger.info("Message would become empty after link removal - skipping processing")
                                return False
                    except Exception as e:
                        logger.error(f"Error in early text cleaning check: {e}")
            
            # Check keyword filters for text messages (this should run AFTER basic text filter check)
            if hasattr(message, 'text') and message.text:
                keyword_filters = settings.get("keyword_filters")
                keyword_filter_mode = settings.get("keyword_filter_mode", "none")
                
                logger.info(f"DEBUG: Text message content: '{message.text}'")
                logger.info(f"DEBUG: keyword_filters raw: {keyword_filters}")
                logger.info(f"DEBUG: keyword_filter_mode: {keyword_filter_mode}")
                
                if keyword_filters and keyword_filter_mode != "none":
                    import json
                    try:
                        # Parse keyword filters if it's a string
                        if isinstance(keyword_filters, str):
                            keyword_filters = json.loads(keyword_filters)
                            logger.info(f"DEBUG: Parsed keyword_filters: {keyword_filters}")
                        
                        # Use mode from keyword_filters JSON, not from database column
                        actual_mode = keyword_filters.get("mode", "blacklist") if isinstance(keyword_filters, dict) else "blacklist"
                        logger.info(f"DEBUG: Using filter mode: {actual_mode} (from JSON data)")
                        
                        text_lower = message.text.lower()
                        logger.info(f"DEBUG: Text lowercase: '{text_lower}'")
                        
                        if actual_mode == "whitelist":
                            # For whitelist mode: message must contain at least one whitelisted keyword
                            whitelist = keyword_filters.get("whitelist", [])
                            logger.info(f"DEBUG: Whitelist keywords: {whitelist}")
                            
                            if whitelist:  # Only apply filter if whitelist is not empty
                                found_keyword = False
                                for keyword in whitelist:
                                    keyword_lower = keyword.lower()
                                    logger.info(f"DEBUG: Checking keyword '{keyword_lower}' in text '{text_lower}'")
                                    if keyword_lower in text_lower:
                                        found_keyword = True
                                        logger.info(f"SUCCESS: Found whitelist keyword '{keyword}' in text - ALLOWING message")
                                        break
                                    else:
                                        logger.info(f"DEBUG: Keyword '{keyword_lower}' NOT found in text")
                                
                                if not found_keyword:
                                    logger.info(f"BLOCKING: No whitelist keywords found in text - FILTERING message")
                                    return False
                                else:
                                    logger.info(f"ALLOWING: Whitelist keyword found - message will be forwarded")
                            else:
                                logger.info(f"DEBUG: Whitelist is empty - allowing all messages")
                        
                        elif actual_mode == "blacklist":
                            # For blacklist mode: message must not contain any blacklisted keyword
                            blacklist = keyword_filters.get("blacklist", [])
                            logger.info(f"DEBUG: Blacklist keywords: {blacklist}")
                            for keyword in blacklist:
                                if keyword.lower() in text_lower:
                                    logger.info(f"BLOCKING: Found blacklist keyword '{keyword}' in text - FILTERING message")
                                    return False
                                    
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.error(f"ERROR: Error parsing keyword filters: {e}")
                        # Continue processing if filters are malformed
                else:
                    logger.info(f"DEBUG: No keyword filtering - filters={keyword_filters}, mode={keyword_filter_mode}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking message filters: {e}")
            return False
    
    async def _is_duplicate(self, task_id: int, message: Any) -> bool:
        """Check if message is a duplicate"""
        try:
            # Create message signature
            signature = f"{task_id}_{message.chat.id}_{message.message_id}"
            
            if signature in self.duplicate_tracker:
                return True
            
            # Add to tracker (with size limit)
            self.duplicate_tracker.add(signature)
            if len(self.duplicate_tracker) > 10000:
                # Remove old entries (simple FIFO)
                self.duplicate_tracker = set(list(self.duplicate_tracker)[-5000:])
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False

    async def _check_working_hours(self, task_id: int, settings: Dict[str, Any]) -> bool:
        """Check if current time is within working hours for the task"""
        try:
            if not settings.get("working_hours_enabled", False):
                return True
            
            timezone_str = settings.get("timezone", "UTC")
            start_hour = settings.get("start_hour", 0)
            end_hour = settings.get("end_hour", 23)
            
            # Get current time in task timezone
            tz = pytz.timezone(timezone_str)
            current_time = datetime.now(tz)
            current_hour = current_time.hour
            
            # Check if current hour is within working hours
            if start_hour <= end_hour:
                # Normal case: 9 AM to 5 PM
                is_working_hours = start_hour <= current_hour <= end_hour
            else:
                # Overnight case: 10 PM to 6 AM
                is_working_hours = current_hour >= start_hour or current_hour <= end_hour
            
            if not is_working_hours:
                logger.info(f"Task {task_id}: Outside working hours ({current_hour}:00 not between {start_hour}:00-{end_hour}:00 {timezone_str})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking working hours for task {task_id}: {e}")
            return True  # Default to allowing if there's an error

    async def _translate_message(self, message_text: str, target_language: str) -> str:
        """Translate message text to target language"""
        try:
            if not message_text or not target_language:
                return message_text
            
            # Detect source language
            detected = self.translator.detect(message_text)
            source_lang = detected.lang if detected else 'auto'
            
            # Skip translation if already in target language
            if source_lang == target_language:
                return message_text
            
            # Perform translation
            translated = self.translator.translate(message_text, dest=target_language, src=source_lang)
            return translated.text if translated else message_text
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return message_text  # Return original text if translation fails

    async def _apply_auto_translation(self, message_text: str, settings: Dict[str, Any]) -> str:
        """Apply automatic translation if enabled"""
        try:
            if not settings.get("auto_translate", False):
                return message_text
            
            target_language = settings.get("target_language", "ar")
            return await self._translate_message(message_text, target_language)
            
        except Exception as e:
            logger.error(f"Error in auto translation: {e}")
            return message_text

    async def _create_inline_buttons(self, settings: Dict[str, Any], variables: Dict[str, str]) -> Optional[Any]:
        """Create custom inline buttons based on task settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Check if inline buttons are enabled
            if not settings.get("inline_buttons_enabled", False):
                logger.info("Inline buttons are disabled in settings")
                return None
            
            logger.info("Inline buttons are enabled, proceeding to create buttons")
            
            # Get buttons configuration from the correct database field
            buttons_config = []
            if settings.get("inline_button_settings"):
                button_settings = settings.get("inline_button_settings")
                if isinstance(button_settings, str):
                    try:
                        button_settings = json.loads(button_settings)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in inline_button_settings")
                        return None
                buttons_config = button_settings.get("buttons", [])
            elif settings.get("inline_buttons_config"):
                # Legacy support
                buttons_config = settings.get("inline_buttons_config", [])
                if isinstance(buttons_config, str):
                    try:
                        buttons_config = json.loads(buttons_config)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in inline_buttons_config")
                        return None
            
            if not buttons_config or not isinstance(buttons_config, list):
                logger.info(f"No valid buttons configuration found. Config: {buttons_config}")
                return None
            
            logger.info(f"Found {len(buttons_config)} buttons to create")
            
            # Check if we have new row structure or old flat structure
            button_rows_data = None
            if isinstance(button_settings, dict) and "button_rows" in button_settings:
                button_rows_data = button_settings.get("button_rows", [])
                logger.info(f"Using new row structure with {len(button_rows_data)} rows")
            
            keyboard = []
            
            if button_rows_data:
                # Use the new row structure
                for row_data in button_rows_data:
                    if not isinstance(row_data, list):
                        continue
                    
                    keyboard_row = []
                    for button_data in row_data:
                        if not isinstance(button_data, dict):
                            continue
                        
                        button_text = button_data.get("text", "")
                        button_type = button_data.get("type", "url")
                        button_value = button_data.get("value", "")
                        
                        if not button_text:
                            continue
                        
                        # Apply variable substitution
                        for var, value in variables.items():
                            button_text = button_text.replace(var, value)
                            if button_value:
                                button_value = button_value.replace(var, value)
                        
                        # Create button based on type
                        try:
                            if button_type == "url":
                                if button_value and (button_value.startswith("http://") or button_value.startswith("https://")):
                                    button = InlineKeyboardButton(text=button_text, url=button_value)
                                else:
                                    logger.warning(f"Invalid URL for button: {button_value}")
                                    continue
                            elif button_type == "popup":
                                button = InlineKeyboardButton(text=button_text, callback_data=f"popup_info_{hash(button_value) % 10000}")
                            elif button_type == "share":
                                import urllib.parse
                                message_text = variables.get('message_text', 'رسالة من القناة')
                                target_channel = variables.get('target_channel', '@channel')
                                share_content = f"{message_text}\n\nمن: {target_channel}"
                                encoded_text = urllib.parse.quote(share_content)
                                share_url = f"https://t.me/share/url?url=&text={encoded_text}"
                                button = InlineKeyboardButton(text=button_text, url=share_url)
                            else:
                                logger.warning(f"Unknown button type: {button_type}")
                                continue
                            
                            keyboard_row.append(button)
                            
                        except Exception as e:
                            logger.error(f"Error creating button: {e}")
                            continue
                    
                    if keyboard_row:
                        keyboard.append(keyboard_row)
            else:
                # Fallback to old flat structure (each button in separate row)
                logger.info("Using fallback flat structure")
                for button_data in buttons_config:
                    if not isinstance(button_data, dict):
                        continue
                    
                    button_text = button_data.get("text", "")
                    button_type = button_data.get("type", "url")
                    button_value = button_data.get("value", "")
                    
                    if not button_text:
                        continue
                    
                    # Apply variable substitution
                    for var, value in variables.items():
                        button_text = button_text.replace(var, value)
                        if button_value:
                            button_value = button_value.replace(var, value)
                    
                    # Create button based on type
                    try:
                        if button_type == "url":
                            if button_value and (button_value.startswith("http://") or button_value.startswith("https://")):
                                button = InlineKeyboardButton(text=button_text, url=button_value)
                            else:
                                logger.warning(f"Invalid URL for button: {button_value}")
                                continue
                        elif button_type == "popup":
                            button = InlineKeyboardButton(text=button_text, callback_data=f"popup_info_{hash(button_value) % 10000}")
                        elif button_type == "share":
                            import urllib.parse
                            message_text = variables.get('message_text', 'رسالة من القناة')
                            target_channel = variables.get('target_channel', '@channel')
                            share_content = f"{message_text}\n\nمن: {target_channel}"
                            encoded_text = urllib.parse.quote(share_content)
                            share_url = f"https://t.me/share/url?url=&text={encoded_text}"
                            button = InlineKeyboardButton(text=button_text, url=share_url)
                        else:
                            logger.warning(f"Unknown button type: {button_type}")
                            continue
                        
                        keyboard.append([button])  # Each button in its own row
                        
                    except Exception as e:
                        logger.error(f"Error creating button: {e}")
                        continue
            
            if keyboard:
                logger.info(f"Created custom inline keyboard with {len(keyboard)} rows")
                return InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating inline buttons: {e}")
            return None
    
    async def _forward_message(self, task: Dict[str, Any], settings: Dict[str, Any], 
                              message: Any, target_chat_id: int, task_id: int = None) -> Optional[int]:
        """Forward message to target with automatic fallback to Bot API if userbot fails"""
        try:
            # Get task_id if not provided
            if task_id is None:
                task_id = task.get("id")
            
            if task["task_type"] == "userbot" and self.userbot:
                # Try userbot first
                logger.info(f"Attempting userbot forwarding for task {task_id}")
                userbot_result = await self._forward_with_userbot(
                    message, target_chat_id, settings
                )
                
                if userbot_result:
                    logger.info(f"Userbot forwarding successful for task {task_id}")
                    return userbot_result
                else:
                    # Userbot failed, fallback to Bot API
                    logger.warning(f"Userbot forwarding failed for task {task_id}, falling back to Bot API")
                    return await self._forward_with_bot(
                        message, target_chat_id, settings, task_id
                    )
            else:
                # Use Bot API directly
                return await self._forward_with_bot(
                    message, target_chat_id, settings, task_id
                )
                
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            # Try Bot API as last resort
            try:
                logger.warning(f"Attempting Bot API as final fallback for task {task_id}")
                return await self._forward_with_bot(
                    message, target_chat_id, settings, task_id
                )
            except Exception as fallback_error:
                logger.error(f"All forwarding methods failed: {fallback_error}")
                return None
    
    async def _forward_with_bot(self, message: Any, target_chat_id: int, 
                               settings: Dict[str, Any], task_id: int = None) -> Optional[int]:
        """Forward message using Bot API"""
        try:
            forward_mode = settings.get("forward_mode", "copy")
            
            # Check if we need to remove inline buttons (only from text cleaner settings)
            should_remove_buttons = False
            cleaner_settings = settings.get("text_cleaner_settings")
            if cleaner_settings:
                import json
                try:
                    if isinstance(cleaner_settings, str):
                        cleaner_settings = json.loads(cleaner_settings)
                    should_remove_buttons = cleaner_settings.get("remove_inline_buttons", False)
                except:
                    should_remove_buttons = False
            
            # Note: filter_inline_buttons blocks messages entirely, so we don't remove buttons here
            # Only text_cleaner_settings controls button removal during forwarding
            
            # Initialize variables for inline buttons (always available)
            from datetime import datetime
            now = datetime.now()
            source_name = "Unknown Source"
            original_text = message.text or message.caption or ""
            
            # Try to get source name from message
            if hasattr(message, 'chat') and message.chat:
                if hasattr(message.chat, 'title') and message.chat.title:
                    source_name = message.chat.title
                elif hasattr(message.chat, 'username') and message.chat.username:
                    source_name = f"@{message.chat.username}"
                elif hasattr(message.chat, 'first_name') and message.chat.first_name:
                    source_name = message.chat.first_name
            
            # Fallback to database source name if needed
            if source_name == "Unknown Source" and task_id:
                try:
                    sources = await self.database.get_task_sources(task_id)
                    if sources:
                        chat_id = message.chat.id if hasattr(message, 'chat') else None
                        for source in sources:
                            if str(source.get("chat_id")) == str(chat_id):
                                source_name = source.get("name", "Unknown Source")
                                break
                        if source_name == "Unknown Source" and sources:
                            source_name = sources[0].get("name", "Unknown Source")
                except Exception as e:
                    logger.warning(f"Could not retrieve source name: {e}")
            
            # Initialize variables that will be used throughout
            variables = {
                "{original}": original_text,
                "{source}": source_name,
                "{time}": now.strftime("%H:%M"),
                "{date}": now.strftime("%Y-%m-%d")
            }
            
            # Check if we need to modify text content or apply formatting
            modified_text = None
            modified_message = message
            if settings:
                
                # Apply text replacements first
                modified_text = original_text
                
                # Check both possible field names for text replacements
                replace_rules = settings.get("replace_text") or settings.get("text_replacements")
                
                if replace_rules and original_text:
                    try:
                        import json
                        
                        # Parse JSON if it's a string
                        if isinstance(replace_rules, str):
                            replace_rules = json.loads(replace_rules)
                        
                        logger.info(f"Applying text replacement rules: {replace_rules}")
                        
                        # Handle different formats of replacement rules
                        if isinstance(replace_rules, dict):
                            # Format: {"old": "new", "old2": "new2"}
                            for old_text, new_text in replace_rules.items():
                                if old_text in modified_text:
                                    modified_text = modified_text.replace(old_text, new_text)
                                    logger.info(f"Replaced '{old_text}' with '{new_text}'")
                        elif isinstance(replace_rules, list):
                            # Format: [{"old": "text1", "new": "text2"}, {"from": "text3", "to": "text4"}]
                            for rule in replace_rules:
                                if isinstance(rule, dict):
                                    # Support both "old/new" and "from/to" formats
                                    old_text = rule.get('old') or rule.get('from')
                                    new_text = rule.get('new') or rule.get('to')
                                    
                                    if old_text and new_text is not None:
                                        if old_text in modified_text:
                                            modified_text = modified_text.replace(old_text, new_text)
                                            logger.info(f"Replaced '{old_text}' with '{new_text}'")
                        
                        if original_text != modified_text:
                            logger.info(f"Text replacement completed successfully")
                        else:
                            logger.info("No text replacements were applied")
                        
                    except Exception as e:
                        logger.error(f"Error applying text replacements: {e}")
                        logger.error(f"Replace rules data: {replace_rules}")
                        modified_text = original_text
                
                # Apply auto translation after replacements but before text cleaning
                if modified_text and settings.get("auto_translate", False):
                    try:
                        target_language = settings.get("target_language", "ar")
                        translated_text = await self._apply_auto_translation(modified_text, settings)
                        if translated_text != modified_text:
                            modified_text = translated_text
                            logger.info(f"Auto translation applied: '{original_text[:50]}...' -> '{translated_text[:50]}...'")
                        else:
                            logger.info("Auto translation: no translation needed or failed")
                    except Exception as e:
                        logger.error(f"Error applying auto translation: {e}")
                
                # Apply text cleaning after translation but before header/footer
                if modified_text and settings.get("text_cleaner_settings"):
                    try:
                        import json
                        cleaner_settings = settings["text_cleaner_settings"]
                        if isinstance(cleaner_settings, str):
                            cleaner_settings = json.loads(cleaner_settings)
                        
                        if cleaner_settings:
                            original_length = len(modified_text)
                            cleaned_text = await self._apply_text_cleaning(modified_text, cleaner_settings)
                            if cleaned_text != modified_text:
                                modified_text = cleaned_text
                                logger.info(f"Text cleaning applied: {original_length} -> {len(modified_text)} chars")
                            else:
                                logger.info("Text cleaning: no changes needed")
                    except Exception as e:
                        logger.error(f"Error applying text cleaning: {e}")
                
                # Check if message became empty after text cleaning
                if modified_text and modified_text.strip() == "":
                    logger.info("Message became empty after text cleaning - skipping forward")
                    return None
                
                # Apply header/footer (prefix/suffix) before formatting
                if modified_text:
                    from datetime import datetime
                    
                    # Get header and footer from settings with enabled flags
                    header = settings.get("prefix_text", "")
                    footer = settings.get("suffix_text", "")
                    header_enabled = settings.get("header_enabled", True)
                    footer_enabled = settings.get("footer_enabled", True)
                    
                    if (header and header_enabled) or (footer and footer_enabled):
                        # Prepare variables for replacement
                        now = datetime.now()
                        source_name = "Unknown Source"  # Will be replaced with actual source name
                        
                        # Try to get source name from message and task
                        if hasattr(message, 'chat') and message.chat:
                            # Try to get chat title first
                            if hasattr(message.chat, 'title') and message.chat.title:
                                source_name = message.chat.title
                            elif hasattr(message.chat, 'username') and message.chat.username:
                                source_name = f"@{message.chat.username}"
                            elif hasattr(message.chat, 'first_name') and message.chat.first_name:
                                source_name = message.chat.first_name
                        
                        # Fallback to database source name if chat info not available
                        if source_name == "Unknown Source" and task_id:
                            try:
                                sources = await self.database.get_task_sources(task_id)
                                if sources:
                                    # Find the matching source by chat_id
                                    chat_id = message.chat.id if hasattr(message, 'chat') else None
                                    for source in sources:
                                        if str(source.get("chat_id")) == str(chat_id):
                                            source_name = source.get("name", "Unknown Source")
                                            break
                                    if source_name == "Unknown Source" and sources:
                                        source_name = sources[0].get("name", "Unknown Source")
                            except Exception as e:
                                logger.warning(f"Could not retrieve source name: {e}")
                        
                        # Update variables with modified text for header/footer
                        variables["{original}"] = modified_text
                        variables["{source}"] = source_name
                        variables["message_text"] = modified_text
                        variables["target_channel"] = f"@{target_chat_id}" if str(target_chat_id).startswith("-100") else f"Chat {target_chat_id}"
                        
                        # Apply header only if enabled
                        if header and header.strip() and header_enabled:
                            processed_header = header
                            for var, value in variables.items():
                                processed_header = processed_header.replace(var, value)
                            modified_text = processed_header + "\n" + modified_text
                            logger.info(f"Applied header: '{header}'")
                        
                        # Apply footer only if enabled
                        if footer and footer.strip() and footer_enabled:
                            processed_footer = footer
                            for var, value in variables.items():
                                processed_footer = processed_footer.replace(var, value)
                            modified_text = modified_text + "\n" + processed_footer
                            logger.info(f"Applied footer: '{footer}'")

                # Apply formatting to the modified text
                if settings.get("format_settings") and modified_text:
                    # Create a temporary message object for formatting
                    class TempMessage:
                        def __init__(self, text):
                            self.text = text
                            self.caption = None
                    
                    temp_msg = TempMessage(modified_text)
                    formatted_text = await self._apply_formatting(temp_msg, settings)
                    if formatted_text and formatted_text != modified_text:
                        logger.info(f"Formatting applied to text with headers/footers: '{formatted_text[:100]}...'")
                        modified_text = formatted_text
                    else:
                        logger.info(f"Using text with headers/footers (no formatting changes): '{modified_text[:100]}...'")
                elif modified_text:
                    logger.info(f"Using text with headers/footers (no format settings): '{modified_text[:100]}...'")
                else:
                    logger.info("No modified text available after header/footer processing")
                
                # Then check if length filtering modification is needed (only if no formatting was applied)
                if not modified_text:
                    modified_text = await self._get_modified_text(modified_message, settings)
                    if modified_text:
                        logger.info(f"Text modification applied: {len(message.text)} -> {len(modified_text)} chars")
            
            # Determine if this is a media message
            is_media_message = (
                hasattr(message, 'photo') and message.photo or
                hasattr(message, 'video') and message.video or
                hasattr(message, 'animation') and message.animation or
                hasattr(message, 'document') and message.document or
                hasattr(message, 'audio') and message.audio or
                hasattr(message, 'voice') and message.voice or
                hasattr(message, 'video_note') and message.video_note or
                hasattr(message, 'sticker') and message.sticker
            )
            
            if forward_mode == "forward" and not modified_text and not should_remove_buttons:
                # Forward original message preserving all original properties including buttons
                result = await self.bot.forward_message(
                    chat_id=target_chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
            elif is_media_message:
                # Handle media messages with copy_message
                copy_kwargs = {
                    "chat_id": target_chat_id,
                    "from_chat_id": message.chat.id,
                    "message_id": message.message_id,
                    "disable_notification": settings.get("silent_mode", False)
                }
                
                # Handle reply preservation if enabled
                if settings.get("preserve_replies", False) and hasattr(message, 'reply_to_message') and message.reply_to_message:
                    try:
                        reply_to_message_id = await self._find_forwarded_message_id(
                            task_id, message.reply_to_message.message_id, target_chat_id
                        )
                        if reply_to_message_id:
                            copy_kwargs["reply_to_message_id"] = reply_to_message_id
                            logger.info(f"Preserving reply structure in media copy: replying to message {reply_to_message_id}")
                    except Exception as e:
                        logger.warning(f"Failed to preserve reply structure in media copy: {e}")
                
                # Handle caption - check for caption removal first
                if settings.get("remove_caption", False):
                    # Remove caption entirely
                    copy_kwargs["caption"] = None
                    logger.info("Caption removed as requested by remove_caption setting")
                elif modified_text:
                    copy_kwargs["caption"] = modified_text
                    copy_kwargs["parse_mode"] = "HTML"
                    logger.info(f"Using modified caption for media: '{modified_text[:100]}...'")
                elif hasattr(message, 'caption') and message.caption:
                    copy_kwargs["caption"] = message.caption
                    logger.info("Preserving original caption for media")
                
                # Handle inline buttons: custom buttons take priority, then preserve original
                if should_remove_buttons:
                    copy_kwargs["reply_markup"] = None
                    logger.info("Removing inline buttons from media as requested")
                else:
                    reply_markup = await self._create_inline_buttons(settings, variables)
                    if not reply_markup and hasattr(message, 'reply_markup') and message.reply_markup:
                        if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                            reply_markup = message.reply_markup
                            logger.info("Preserving original inline buttons in media message")
                    
                    if reply_markup:
                        copy_kwargs["reply_markup"] = reply_markup
                        logger.info("Applied inline buttons to media message")
                
                result = await self.bot.copy_message(**copy_kwargs)
                
                # Pin message if enabled
                if settings.get("pin_messages", False) and result:
                    try:
                        await self.bot.pin_chat_message(
                            chat_id=target_chat_id,
                            message_id=result.message_id,
                            disable_notification=True
                        )
                        logger.info(f"Pinned media message {result.message_id} in chat {target_chat_id}")
                    except Exception as e:
                        logger.warning(f"Failed to pin media message: {e}")
                        
            else:
                # Handle text messages
                if modified_text or (hasattr(modified_message, 'text') and modified_message.text):
                    # Send modified text - preserve buttons if they exist
                    text_to_send = modified_text if modified_text else modified_message.text
                    send_kwargs = {
                        "chat_id": target_chat_id,
                        "text": text_to_send,
                        "parse_mode": "HTML",  # Always use HTML parse_mode for formatting
                        "disable_web_page_preview": not settings.get("link_preview", False),
                        "disable_notification": settings.get("silent_mode", False)
                    }
                    
                    # Handle reply preservation if enabled
                    if settings.get("preserve_replies", False) and hasattr(message, 'reply_to_message') and message.reply_to_message:
                        try:
                            reply_to_message_id = await self._find_forwarded_message_id(
                                task_id, message.reply_to_message.message_id, target_chat_id
                            )
                            if reply_to_message_id:
                                send_kwargs["reply_to_message_id"] = reply_to_message_id
                                logger.info(f"Preserving reply structure in modified text: replying to message {reply_to_message_id}")
                        except Exception as e:
                            logger.warning(f"Failed to preserve reply structure in modified text: {e}")
                    
                    # Handle inline buttons: custom buttons take priority, then preserve original
                    logger.info(f"Creating inline buttons for modified text message. Settings enabled: {settings.get('inline_buttons_enabled', False)}")
                    reply_markup = await self._create_inline_buttons(settings, variables)
                    if reply_markup:
                        logger.info(f"Custom inline buttons created successfully for modified text")
                    elif not reply_markup and hasattr(message, 'reply_markup') and message.reply_markup and not should_remove_buttons:
                        if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                            reply_markup = message.reply_markup
                            logger.info("Preserving original inline buttons in modified message")
                    
                    if reply_markup:
                        send_kwargs["reply_markup"] = reply_markup
                        logger.info("Inline buttons added to send_kwargs for modified text message")
                    else:
                        logger.info("No inline buttons to apply to modified text message")
                    
                    result = await self.bot.send_message(**send_kwargs)
                    
                    # Pin message if enabled
                    if settings.get("pin_messages", False) and result:
                        try:
                            await self.bot.pin_chat_message(
                                chat_id=target_chat_id,
                                message_id=result.message_id,
                                disable_notification=True  # Pin silently
                            )
                            logger.info(f"Pinned message {result.message_id} in chat {target_chat_id}")
                        except Exception as e:
                            logger.warning(f"Failed to pin message: {e}")
                elif hasattr(modified_message, 'text') and modified_message.text:
                    # For formatted text messages, use send_message to support disable_web_page_preview
                    send_kwargs = {
                        "chat_id": target_chat_id,
                        "text": modified_message.text,
                        "disable_web_page_preview": not settings.get("link_preview", False),
                        "disable_notification": settings.get("silent_mode", False)
                    }
                    
                    # Handle reply preservation if enabled  
                    if settings.get("preserve_replies", False) and hasattr(message, 'reply_to_message') and message.reply_to_message:
                        try:
                            reply_to_message_id = await self._find_forwarded_message_id(
                                task_id, message.reply_to_message.message_id, target_chat_id
                            )
                            if reply_to_message_id:
                                send_kwargs["reply_to_message_id"] = reply_to_message_id
                                logger.info(f"Preserving reply structure: replying to message {reply_to_message_id}")
                        except Exception as e:
                            logger.warning(f"Failed to preserve reply structure: {e}")
                    
                    # Handle inline buttons: custom buttons take priority, then preserve original
                    logger.info(f"Creating inline buttons for text message. Settings enabled: {settings.get('inline_buttons_enabled', False)}")
                    reply_markup = await self._create_inline_buttons(settings, variables)
                    if reply_markup:
                        logger.info(f"Custom inline buttons created successfully for text message")
                    elif not reply_markup and hasattr(message, 'reply_markup') and message.reply_markup and not should_remove_buttons:
                        if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                            reply_markup = message.reply_markup
                            logger.info("Preserving original inline buttons in text message")
                    
                    if reply_markup:
                        send_kwargs["reply_markup"] = reply_markup
                        logger.info("Inline buttons added to send_kwargs for text message")
                    else:
                        logger.info("No inline buttons to apply to text message")
                    
                    result = await self.bot.send_message(**send_kwargs)
                    
                    # Pin message if enabled
                    if settings.get("pin_messages", False) and result:
                        try:
                            await self.bot.pin_chat_message(
                                chat_id=target_chat_id,
                                message_id=result.message_id,
                                disable_notification=True  # Pin silently
                            )
                            logger.info(f"Pinned message {result.message_id} in chat {target_chat_id}")
                        except Exception as e:
                            logger.warning(f"Failed to pin message: {e}")
                else:
                    # Fallback for pure text messages without modifications
                    copy_kwargs = {
                        "chat_id": target_chat_id,
                        "from_chat_id": message.chat.id,
                        "message_id": message.message_id,
                        "disable_notification": settings.get("silent_mode", False)
                    }
                    
                    # Handle reply preservation if enabled
                    if settings.get("preserve_replies", False) and hasattr(message, 'reply_to_message') and message.reply_to_message:
                        try:
                            reply_to_message_id = await self._find_forwarded_message_id(
                                task_id, message.reply_to_message.message_id, target_chat_id
                            )
                            if reply_to_message_id:
                                copy_kwargs["reply_to_message_id"] = reply_to_message_id
                                logger.info(f"Preserving reply structure in fallback: replying to message {reply_to_message_id}")
                        except Exception as e:
                            logger.warning(f"Failed to preserve reply structure in fallback: {e}")
                    
                    # Handle inline buttons for fallback text messages
                    if should_remove_buttons:
                        copy_kwargs["reply_markup"] = None
                        logger.info("Removing inline buttons from fallback text as requested")
                    else:
                        reply_markup = await self._create_inline_buttons(settings, variables)
                        if not reply_markup and hasattr(message, 'reply_markup') and message.reply_markup:
                            if hasattr(message.reply_markup, 'inline_keyboard') and message.reply_markup.inline_keyboard:
                                reply_markup = message.reply_markup
                                logger.info("Preserving original inline buttons in fallback text")
                        
                        if reply_markup:
                            copy_kwargs["reply_markup"] = reply_markup
                    
                    result = await self.bot.copy_message(**copy_kwargs)
                    
                    # Pin message if enabled
                    if settings.get("pin_messages", False) and result:
                        try:
                            await self.bot.pin_chat_message(
                                chat_id=target_chat_id,
                                message_id=result.message_id,
                                disable_notification=True
                            )
                            logger.info(f"Pinned fallback message {result.message_id} in chat {target_chat_id}")
                        except Exception as e:
                            logger.warning(f"Failed to pin fallback message: {e}")
            
            # Store message mapping for reply preservation or edit synchronization if enabled
            if result and hasattr(result, 'message_id') and result.message_id and (
                settings.get("preserve_replies", False) or settings.get("sync_edits", False)
            ):
                await self._store_message_mapping(
                    task_id, message.message_id, result.message_id, target_chat_id
                )
            
            return result.message_id
            
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}")
            return None
    
    async def _forward_with_userbot(self, message: Any, target_chat_id: int, 
                                   settings: Dict[str, Any]) -> Optional[int]:
        """Forward message using Telethon Userbot"""
        try:
            forward_mode = settings.get("forward_mode", "copy")
            
            # Check if userbot is Telethon client
            if hasattr(self.userbot, 'forward_messages'):
                # Telethon userbot
                if forward_mode == "forward":
                    # Forward original message using Telethon
                    result = await self.userbot.forward_messages(
                        entity=target_chat_id,
                        messages=message.message_id,
                        from_peer=message.chat.id
                    )
                else:
                    # Copy mode - reproduce message content without showing original source
                    if hasattr(message, 'text') and message.text and not hasattr(message, 'media'):
                        # Pure text message - apply all content processing
                        processed_text = await self._process_userbot_text(message.text, settings)
                        result = await self.userbot.send_message(
                            entity=target_chat_id,
                            message=processed_text,
                            parse_mode='html'  # Support HTML formatting
                        )
                    elif hasattr(message, 'media') and message.media:
                        # Media message - send media with processed caption
                        try:
                            # Download and re-upload media to avoid showing original source
                            media_path = await self.userbot.download_media(message)
                            if media_path:
                                caption = message.message if hasattr(message, 'message') else ""
                                # Check caption removal setting first
                                if settings.get("remove_caption", False):
                                    processed_caption = ""
                                    logger.info("Caption removed by userbot due to remove_caption setting")
                                elif caption:
                                    processed_caption = await self._process_userbot_text(caption, settings)
                                else:
                                    processed_caption = ""
                                
                                result = await self.userbot.send_file(
                                    entity=target_chat_id,
                                    file=media_path,
                                    caption=processed_caption,
                                    parse_mode='html'  # Support HTML formatting
                                )
                                # Clean up downloaded file
                                import os
                                try:
                                    os.remove(media_path)
                                except:
                                    pass
                            else:
                                # Fallback: forward if download fails
                                result = await self.userbot.forward_messages(
                                    entity=target_chat_id,
                                    messages=message.message_id,
                                    from_peer=message.chat.id
                                )
                        except Exception as media_error:
                            logger.warning(f"Failed to copy media, falling back to forward: {media_error}")
                            result = await self.userbot.forward_messages(
                                entity=target_chat_id,
                                messages=message.message_id,
                                from_peer=message.chat.id
                            )
                    else:
                        # Text with no media - send as new message with processing
                        text_content = message.message if hasattr(message, 'message') else (message.text if hasattr(message, 'text') else "")
                        processed_text = await self._process_userbot_text(text_content, settings)
                        result = await self.userbot.send_message(
                            entity=target_chat_id,
                            message=processed_text,
                            parse_mode='html'  # Support HTML formatting
                        )
                
                return result.id if hasattr(result, 'id') else (result[0].id if isinstance(result, list) else None)
            
            elif hasattr(self.userbot, 'forward_messages') and Client:
                # Pyrogram userbot (fallback)
                if forward_mode == "forward":
                    result = await self.userbot.forward_messages(
                        chat_id=target_chat_id,
                        from_chat_id=message.chat.id,
                        message_ids=message.message_id
                    )
                else:
                    result = await self.userbot.copy_message(
                        chat_id=target_chat_id,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                
                return result.id if hasattr(result, 'id') else result[0].id
            
            return None
            
        except Exception as e:
            error_msg = str(e).lower()
            if "key is not registered" in error_msg or "session" in error_msg or "unauthorized" in error_msg:
                logger.error(f"Telethon userbot session error: {e} - This indicates STRING_SESSION is invalid or expired")
            else:
                logger.error(f"Telethon userbot error: {e}")
            return None

    async def _process_userbot_text(self, text: str, settings: Dict[str, Any]) -> str:
        """Process text with all content settings for userbot"""
        try:
            if not text or not settings:
                return text
            
            processed_text = text
            
            # Apply text replacements first
            if settings.get("replace_text"):
                try:
                    import json
                    replace_rules = settings["replace_text"]
                    if isinstance(replace_rules, str):
                        replace_rules = json.loads(replace_rules)
                    
                    logger.info(f"Applying text replacement rules: {replace_rules}")
                    
                    for old_text, new_text in replace_rules.items():
                        if old_text in processed_text:
                            processed_text = processed_text.replace(old_text, new_text)
                            logger.info(f"Replaced '{old_text}' with '{new_text}'")
                    
                except Exception as e:
                    logger.error(f"Error applying text replacements: {e}")
            
            # Apply prefix and suffix
            prefix = settings.get("prefix", "")
            suffix = settings.get("suffix", "")
            
            if prefix:
                processed_text = prefix + processed_text
                logger.info(f"Added prefix: '{prefix}'")
            
            if suffix:
                processed_text = processed_text + suffix
                logger.info(f"Added suffix: '{suffix}'")
            
            # Apply formatting if enabled
            if settings.get("format_settings"):
                # Create a temporary message object for formatting
                class TempMessage:
                    def __init__(self, text):
                        self.text = text
                        self.caption = None
                
                temp_msg = TempMessage(processed_text)
                formatted_text = await self._apply_formatting(temp_msg, settings)
                if formatted_text and formatted_text != processed_text:
                    logger.info(f"Formatting applied: '{formatted_text}'")
                    processed_text = formatted_text
            
            # Apply text cleaning if enabled
            if settings.get("text_cleaner_settings"):
                try:
                    import json
                    cleaner_settings = settings["text_cleaner_settings"]
                    if isinstance(cleaner_settings, str):
                        cleaner_settings = json.loads(cleaner_settings)
                    
                    processed_text = await self._apply_text_cleaning(processed_text, cleaner_settings)
                    logger.info(f"Text cleaning applied")
                    
                except Exception as e:
                    logger.error(f"Error applying text cleaning: {e}")
            
            # Apply auto translation if enabled
            if settings.get("auto_translate", False):
                try:
                    processed_text = await self._apply_auto_translation(processed_text, settings)
                    logger.info(f"Auto translation applied")
                except Exception as e:
                    logger.error(f"Error applying auto translation: {e}")
            
            return processed_text
            
        except Exception as e:
            logger.error(f"Error processing userbot text: {e}")
            return text
    
    async def _get_modified_text(self, message: Any, settings: Dict[str, Any]) -> Optional[str]:
        """Get modified text content if length filtering is needed"""
        try:
            if not hasattr(message, 'text') or not message.text:
                return None
            
            # Handle None settings gracefully
            if settings is None:
                settings = {}
            
            text = message.text
            length_settings = settings.get('length_filter_settings', {}) if settings else {}
            
            # Parse JSON if it's a string
            if isinstance(length_settings, str):
                import json
                try:
                    length_settings = json.loads(length_settings)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse length_filter_settings: {length_settings}")
                    return None
            
            if not length_settings.get('enabled', False):
                return None
            
            min_length = length_settings.get('min_length', 0)
            max_length = length_settings.get('max_length', 4096)
            action_mode = length_settings.get('action_mode', 'block')
            
            text_length = len(text)
            
            # Check if modification is needed
            logger.info(f"Length filter check: text_length={text_length}, max_length={max_length}, action_mode={action_mode}")
            if text_length > max_length and action_mode in ['truncate', 'summarize']:
                logger.info(f"Applying {action_mode} to message of length {text_length}")
                if action_mode == 'truncate':
                    modified_text = text[:max_length] + "..."
                elif action_mode == 'summarize':
                    # Take first 200 characters and add Arabic summary note
                    summary_length = min(200, max_length - 50)  # Leave space for note
                    modified_text = text[:summary_length] + "\n\n[تم اختصار الرسالة - النص كامل في المصدر]"
                
                # Apply other content modifications
                if settings and settings.get("remove_links", False):
                    modified_text = re.sub(r'http[s]?://[^\s]+|t\.me/[^\s]+', '', modified_text)
                if settings and settings.get("remove_mentions", False):
                    modified_text = re.sub(r'@\w+', '', modified_text)
                
                logger.info(f"Text modification completed: {len(modified_text)} chars")
                return modified_text
            else:
                logger.info("No text modification needed - within length limits or different action mode")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting modified text: {e}")
            return message.text if hasattr(message, 'text') and message.text else None

    async def _process_message_content(self, message: Any, settings: Dict[str, Any]) -> Any:
        """Process message content based on settings - NO LENGTH FILTERING HERE"""
        try:
            # Handle None settings gracefully
            if settings is None:
                settings = {}
                
            # Apply text cleaning first
            if hasattr(message, 'text') and message.text and settings.get("text_cleaner_settings"):
                import json
                try:
                    cleaner_settings = settings["text_cleaner_settings"]
                    if isinstance(cleaner_settings, str):
                        cleaner_settings = json.loads(cleaner_settings)
                    
                    message.text = await self._apply_text_cleaning(message.text, cleaner_settings)
                except Exception as e:
                    logger.error(f"Error applying text cleaning: {e}")
            
            # Apply text replacements BEFORE formatting
            if hasattr(message, 'text') and message.text and settings.get("replace_text"):
                try:
                    import json
                    replace_rules = settings["replace_text"]
                    if isinstance(replace_rules, str):
                        replace_rules = json.loads(replace_rules)
                    
                    logger.info(f"Applying text replacement rules: {replace_rules}")
                    original_text = message.text
                    modified_text = original_text
                    
                    for old_text, new_text in replace_rules.items():
                        if old_text in modified_text:
                            modified_text = modified_text.replace(old_text, new_text)
                            logger.info(f"Replaced '{old_text}' with '{new_text}'")
                    
                    if original_text != modified_text:
                        logger.info(f"Text replacement completed: '{original_text}' -> '{modified_text}'")
                        # Create a mock message object with the modified text
                        class ModifiedMessage:
                            def __init__(self, original_message, new_text):
                                # Copy all attributes from original
                                for attr in dir(original_message):
                                    if not attr.startswith('_') and attr != 'text':
                                        try:
                                            setattr(self, attr, getattr(original_message, attr))
                                        except:
                                            pass
                                self.text = new_text
                                self.caption = getattr(original_message, 'caption', None)
                        
                        message = ModifiedMessage(message, modified_text)
                    
                except Exception as e:
                    logger.error(f"Error applying text replacements: {e}")
            
            # Apply formatting settings AFTER replacements
            if (hasattr(message, 'text') and message.text) or (hasattr(message, 'caption') and message.caption):
                message = await self._apply_formatting(message, settings)
            
            # Remove links
            if settings.get("remove_links", False) and hasattr(message, 'text') and message.text:
                message.text = re.sub(r'http[s]?://[^\s]+|t\.me/[^\s]+', '', message.text)
            
            # Remove mentions
            if settings.get("remove_mentions", False) and hasattr(message, 'text') and message.text:
                message.text = re.sub(r'@\w+', '', message.text)
            
            # Add custom caption
            if settings.get("add_caption", False) and settings.get("custom_caption"):
                if hasattr(message, 'caption'):
                    message.caption = (message.caption or "") + "\n\n" + settings["custom_caption"]
                elif hasattr(message, 'text'):
                    message.text = (message.text or "") + "\n\n" + settings["custom_caption"]
            
            return message
            
        except Exception as e:
            logger.error(f"Error processing message content: {e}")
            return message
    
    async def _apply_formatting(self, message: Any, settings: Dict[str, Any]) -> str:
        """Apply formatting settings to message text and return formatted text"""
        try:
            import json
            
            # Handle None settings gracefully
            if settings is None:
                settings = {}
            
            # Get format settings - if empty, fetch directly from database
            format_settings = settings.get("format_settings", {})
            if isinstance(format_settings, str):
                try:
                    format_settings = json.loads(format_settings)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse format_settings: {format_settings}")
                    format_settings = {}
            
            # If no format settings found, try to get task_id and fetch from database
            if not format_settings:
                # Try to extract task_id from context or find it
                task_id = None
                if hasattr(message, 'task_id'):
                    task_id = message.task_id
                elif 'task_id' in settings:
                    task_id = settings['task_id']
                else:
                    # Try to find task by checking active tasks
                    for tid, task_data in self.active_tasks_cache.items():
                        if hasattr(message, 'chat') and message.chat:
                            chat_id = message.chat.id
                            sources = task_data.get('sources', [])
                            if any(str(source.get('chat_id')) == str(chat_id) for source in sources):
                                task_id = tid
                                break
                
                if task_id:
                    try:
                        fresh_settings = await self.database.get_task_settings(task_id)
                        if fresh_settings and fresh_settings.get('format_settings'):
                            format_settings = fresh_settings['format_settings']
                            if isinstance(format_settings, str):
                                format_settings = json.loads(format_settings)
                            logger.info(f"Loaded fresh format settings from database for task {task_id}: {format_settings}")
                    except Exception as e:
                        logger.error(f"Error loading fresh format settings: {e}")
            
            # Log the format settings for debugging
            logger.info(f"Applying formatting with settings: {format_settings}")
            
            # Get text content
            text_content = ""
            
            if hasattr(message, 'text') and message.text:
                text_content = message.text
            elif hasattr(message, 'caption') and message.caption:
                text_content = message.caption
            
            if not text_content:
                logger.info("No text content to format")
                return text_content
                
            if not format_settings:
                logger.info("No format settings found")
                return text_content
            
            # Remove all formatting if enabled
            if format_settings.get("remove_all", False):
                # Strip HTML/Markdown formatting comprehensively
                import re
                text_content = re.sub(r'<[^>]+>', '', text_content)  # Remove HTML tags
                text_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', text_content)  # Bold
                text_content = re.sub(r'\*([^*]+)\*', r'\1', text_content)  # Italic
                text_content = re.sub(r'__([^_]+)__', r'\1', text_content)  # Underline
                text_content = re.sub(r'~~([^~]+)~~', r'\1', text_content)  # Strikethrough
                text_content = re.sub(r'\|\|([^|]+)\|\|', r'\1', text_content)  # Spoiler
                text_content = re.sub(r'`([^`]+)`', r'\1', text_content)  # Inline code
                text_content = re.sub(r'```([^`]*)```', r'\1', text_content, flags=re.DOTALL)  # Code blocks
                text_content = re.sub(r'> ([^\n]*)', r'\1', text_content)  # Quotes
                text_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text_content)  # Links
            
            # Initialize formatted_text with original content
            formatted_text = text_content
            
            # Apply formatting if any formatting option is enabled
            if (format_settings.get("apply_bold", False) or 
                format_settings.get("apply_italic", False) or 
                format_settings.get("apply_underline", False) or 
                format_settings.get("apply_strikethrough", False) or
                format_settings.get("apply_spoiler", False) or
                format_settings.get("apply_code", False) or
                format_settings.get("apply_mono", False) or
                format_settings.get("apply_copyable_code", False) or
                format_settings.get("apply_quote", False) or
                format_settings.get("apply_link", False) or
                format_settings.get("remove_all", False)):
                
                # Apply block formatting first (mutually exclusive)
                if format_settings.get("apply_mono", False):
                    formatted_text = f"<pre>{formatted_text}</pre>" 
                elif format_settings.get("apply_code", False):
                    formatted_text = f"<code>{formatted_text}</code>"
                elif format_settings.get("apply_quote", False):
                    lines = formatted_text.split('\n')
                    formatted_text = '\n'.join(f"<blockquote>{line}</blockquote>" for line in lines)
                else:
                    # Apply inline formatting (can be combined) using HTML tags
                    if format_settings.get("apply_bold", False):
                        formatted_text = f"<b>{formatted_text}</b>"
                    
                    if format_settings.get("apply_italic", False):
                        formatted_text = f"<i>{formatted_text}</i>"
                    
                    if format_settings.get("apply_underline", False):
                        formatted_text = f"<u>{formatted_text}</u>"
                    
                    if format_settings.get("apply_strikethrough", False):
                        formatted_text = f"<s>{formatted_text}</s>"
                    
                    if format_settings.get("apply_spoiler", False):
                        formatted_text = f"<tg-spoiler>{formatted_text}</tg-spoiler>"
                
                # Apply custom link last (outermost) using HTML
                if format_settings.get("apply_link", False) and format_settings.get("custom_link_url", ""):
                    url = format_settings["custom_link_url"]
                    if url.strip():
                        formatted_text = f'<a href="{url}">{formatted_text}</a>'
                
                text_content = formatted_text
            
            # Successfully applied formatting - return the formatted text
            logger.info(f"Successfully applied formatting: '{repr(formatted_text)}' (Bold: {format_settings.get('apply_bold', False)})")
            logger.info(f"DEBUG: Final formatted text being returned: '{repr(formatted_text)}'")
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error applying formatting: {e}")
            # Return original text on error
            if hasattr(message, 'text') and message.text:
                return message.text
            elif hasattr(message, 'caption') and message.caption:
                return message.caption
            return ""

    async def _apply_text_cleaning(self, text: str, cleaner_settings: dict) -> str:
        """Apply text cleaning based on settings"""
        try:
            import re
            
            cleaned_text = text
            
            # Remove emojis
            if cleaner_settings.get("remove_emojis", False):
                # Unicode ranges for emojis
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "\U00002500-\U00002BEF"  # chinese char
                    "\U00002702-\U000027B0"
                    "\U00002702-\U000027B0"
                    "\U000024C2-\U0001F251"
                    "\U0001f926-\U0001f937"
                    "\U00010000-\U0010ffff"
                    "\u2640-\u2642" 
                    "\u2600-\u2B55"
                    "\u200d"
                    "\u23cf"
                    "\u23e9"
                    "\u231a"
                    "\ufe0f"  # dingbats
                    "\u3030"
                    "]+", 
                    flags=re.UNICODE
                )
                cleaned_text = emoji_pattern.sub('', cleaned_text)
            
            # Remove links
            if cleaner_settings.get("remove_links", False):
                # Remove HTTP/HTTPS URLs
                cleaned_text = re.sub(r'https?://[^\s]+', '', cleaned_text)
                # Remove FTP URLs
                cleaned_text = re.sub(r'ftp://[^\s]+', '', cleaned_text)
                # Remove www URLs (without protocol)
                cleaned_text = re.sub(r'www\.[^\s]+', '', cleaned_text)
                # Remove telegram links
                cleaned_text = re.sub(r't\.me/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'telegram\.me/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'telegram\.dog/[^\s]+', '', cleaned_text)
                # Remove social media links
                cleaned_text = re.sub(r'instagram\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'facebook\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'twitter\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'x\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'youtube\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'youtu\.be/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'tiktok\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'linkedin\.com/[^\s]+', '', cleaned_text)
                # Remove video platforms
                cleaned_text = re.sub(r'aparat\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'vimeo\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'dailymotion\.com/[^\s]+', '', cleaned_text)
                # Remove messaging apps
                cleaned_text = re.sub(r'whatsapp\.com/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'wa\.me/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'discord\.gg/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'discord\.com/[^\s]+', '', cleaned_text)
                # Remove generic domain patterns with paths (includes subdomains)
                cleaned_text = re.sub(r'\b[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}/[^\s]*', '', cleaned_text)
                # Remove email-like patterns
                cleaned_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', cleaned_text)
                # Remove IP addresses with ports
                cleaned_text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+\b', '', cleaned_text)
                # Remove standalone domains (includes subdomains like meyon.com.ye)
                cleaned_text = re.sub(r'\b[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}\b', '', cleaned_text)
            
            # Remove Telegram usernames (mentions) - supports all valid username characters
            if cleaner_settings.get("remove_mentions", False):
                cleaned_text = re.sub(r'@[a-zA-Z0-9_]{1,32}', '', cleaned_text)
            
            # Remove email addresses
            if cleaner_settings.get("remove_emails", False):
                cleaned_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', cleaned_text)
            
            # Remove hashtags
            if cleaner_settings.get("remove_hashtags", False):
                cleaned_text = re.sub(r'#\w+', '', cleaned_text)
            
            # Remove lines containing target words
            if cleaner_settings.get("remove_lines_with_words", False):
                target_words = cleaner_settings.get("target_words", [])
                if target_words:
                    lines = cleaned_text.split('\n')
                    filtered_lines = []
                    for line in lines:
                        line_lower = line.lower()
                        should_remove = False
                        for word in target_words:
                            if word.lower() in line_lower:
                                should_remove = True
                                break
                        if not should_remove:
                            filtered_lines.append(line)
                    cleaned_text = '\n'.join(filtered_lines)
            
            # Remove empty lines
            if cleaner_settings.get("remove_empty_lines", False):
                lines = cleaned_text.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                cleaned_text = '\n'.join(non_empty_lines)
            
            # Remove extra empty lines (multiple consecutive empty lines)
            if cleaner_settings.get("remove_extra_lines", False):
                # Replace multiple consecutive newlines with single newline
                cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
                # Remove leading and trailing whitespace
                cleaned_text = cleaned_text.strip()
            
            # Normalize whitespace
            if cleaner_settings.get("normalize_whitespace", False):
                # Replace multiple spaces with single space
                cleaned_text = re.sub(r' +', ' ', cleaned_text)
                # Replace tabs with spaces
                cleaned_text = cleaned_text.replace('\t', ' ')
                # Remove trailing spaces from each line
                lines = cleaned_text.split('\n')
                cleaned_text = '\n'.join(line.rstrip() for line in lines)
            
            # Remove duplicate lines
            if cleaner_settings.get("remove_duplicate_lines", False):
                lines = cleaned_text.split('\n')
                seen = set()
                unique_lines = []
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                cleaned_text = '\n'.join(unique_lines)
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error applying text cleaning: {e}")
            return text
    
    async def _apply_delay(self, settings: Dict[str, Any]):
        """Apply random delay based on settings"""
        try:
            delay_min = settings.get("delay_min", 0)
            delay_max = settings.get("delay_max", 5)
            
            if delay_max > delay_min:
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error applying delay: {e}")

    async def _check_rate_limit(self, chat_id: int) -> bool:
        """Check if rate limit is exceeded for a chat"""
        try:
            current_time = time.time()
            chat_key = str(chat_id)
            
            # Initialize if not exists
            if chat_key not in self.rate_limits:
                self.rate_limits[chat_key] = []
            
            # Clean old entries outside the window
            self.rate_limits[chat_key] = [
                timestamp for timestamp in self.rate_limits[chat_key]
                if current_time - timestamp < self.rate_limit_window
            ]
            
            # Check if limit exceeded
            if len(self.rate_limits[chat_key]) >= self.max_requests_per_minute:
                logger.warning(f"Rate limit exceeded for chat {chat_id}")
                return False  # Rate limit exceeded
            
            # Add current request
            self.rate_limits[chat_key].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    async def _log_forwarding(self, task_id: int, source_chat_id: int, target_chat_id: int, 
                             message_id: int, forwarded_message_id: Optional[int], 
                             status: str, error_message: Optional[str] = None):
        """Log forwarding operation"""
        log_data = {
            "task_id": task_id,
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "message_id": message_id,
            "forwarded_message_id": forwarded_message_id,
            "status": status,
            "error_message": error_message
        }
        
        await self.database.log_forwarding(log_data)
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default task settings"""
        return {
            "forward_mode": "copy",
            "preserve_sender": False,
            "add_caption": False,
            "custom_caption": None,
            "filter_media": False,
            "filter_text": False,
            "filter_forwarded": False,
            "filter_links": False,
            "keyword_filters": None,
            "delay_min": 0,
            "delay_max": 5,
            "remove_links": False,
            "remove_mentions": False,
            "replace_text": None,
            "duplicate_check": True,
            "max_message_length": 4096
        }
    
    async def _background_tasks(self):
        """Background maintenance tasks"""
        while self.running:
            try:
                # Update task cache every 5 minutes
                if (not self.cache_last_update or 
                    datetime.now() - self.cache_last_update > timedelta(seconds=self.cache_ttl)):
                    await self._reload_tasks()
                
                # Clean up caches every 10 minutes
                if time.time() % 600 < 60:  # Every 10 minutes
                    await self._cleanup_caches()
                
                # Clean up old logs every hour
                if time.time() % 3600 < 60:  # Once per hour
                    await self.database.cleanup_old_logs()
                
                # Update statistics
                await self.statistics.update_engine_stats(self.get_stats())
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in background tasks: {e}")
                await asyncio.sleep(60)

    async def _cleanup_caches(self):
        """Clean up caches to prevent memory leaks"""
        try:
            current_time = time.time()
            
            # Clean settings cache - remove entries older than 1 hour
            cache_ttl = 3600  # 1 hour
            expired_keys = [
                key for key, timestamp in self._cache_timestamp.items()
                if current_time - timestamp > cache_ttl
            ]
            
            for key in expired_keys:
                self._settings_cache.pop(key, None)
                self._cache_timestamp.pop(key, None)
            
            # Limit cache size
            if len(self._settings_cache) > self._cache_size_limit:
                # Remove oldest entries
                sorted_keys = sorted(self._cache_timestamp.items(), key=lambda x: x[1])
                keys_to_remove = [key for key, _ in sorted_keys[:len(sorted_keys) - self._cache_size_limit]]
                for key in keys_to_remove:
                    self._settings_cache.pop(key, None)
                    self._cache_timestamp.pop(key, None)
            
            # Clean duplicate tracker - keep only recent entries
            if len(self.duplicate_tracker) > 10000:
                self.duplicate_tracker = set(list(self.duplicate_tracker)[-5000:])
            
            # Clean processing times - keep only last 1000 entries
            if len(self.processing_times) > 1000:
                self.processing_times = self.processing_times[-500:]
            
            logger.debug(f"Cache cleanup completed. Cache size: {len(self._settings_cache)}, Duplicates: {len(self.duplicate_tracker)}")
            
        except Exception as e:
            logger.error(f"Error cleaning caches: {e}")
    
    async def _reload_tasks(self):
        """Reload active tasks and update monitors"""
        try:
            old_tasks = set(self.active_tasks_cache.keys())
            await self._load_active_tasks()
            new_tasks = set(self.active_tasks_cache.keys())
            
            # Stop monitors for removed tasks
            for task_id in old_tasks - new_tasks:
                await self._stop_task_monitoring(task_id)
            
            # Start monitors for new tasks
            for task_id in new_tasks - old_tasks:
                task = self.active_tasks_cache[task_id]
                await self._start_task_monitoring(task_id, task)
            
            logger.info(f"Reloaded tasks: {len(new_tasks)} active")
            
        except Exception as e:
            logger.error(f"Error reloading tasks: {e}")
    
    async def _is_duplicate_message(self, message, task_id: int) -> bool:
        """Check if message is a duplicate"""
        try:
            import hashlib
            
            # Create message hash based on content + message_id + timestamp for uniqueness
            content = ""
            if hasattr(message, 'text') and message.text:
                content = message.text
            elif hasattr(message, 'caption') and message.caption:
                content = message.caption
            elif hasattr(message, 'photo') and message.photo:
                # For media without text, use file_id as content
                content = message.photo[-1].file_id if message.photo else ""
            elif hasattr(message, 'video') and message.video:
                content = message.video.file_id
            elif hasattr(message, 'document') and message.document:
                content = message.document.file_id
            
            if not content:
                return False  # Can't check duplicates without content
            
            # Add message_id and date to content for better uniqueness
            # This prevents single characters from being considered duplicates
            unique_content = f"{content}_{message.message_id}_{message.date}"
            
            # Create hash
            message_hash = hashlib.md5(unique_content.encode('utf-8')).hexdigest()
            
            # Check if hash exists in database
            existing = await self.database.execute_query(
                "SELECT id FROM message_duplicates WHERE task_id = $1 AND message_hash = $2",
                task_id, message_hash
            )
            
            if existing:
                # Update count and last_seen
                await self.database.execute_command(
                    "UPDATE message_duplicates SET count = count + 1, last_seen = NOW() WHERE task_id = $1 AND message_hash = $2",
                    task_id, message_hash
                )
                return True
            else:
                # Add new duplicate record
                await self.database.execute_command(
                    "INSERT INTO message_duplicates (task_id, message_hash, first_seen, last_seen, count) VALUES ($1, $2, NOW(), NOW(), 1)",
                    task_id, message_hash
                )
                return False
                
        except Exception as e:
            logger.error(f"Error checking duplicate message: {e}")
            return False
    
    async def _check_language_filter(self, message, settings: dict) -> bool:
        """Check if message passes language filter"""
        try:
            # Get text to analyze
            text_to_check = ""
            if hasattr(message, 'text') and message.text:
                text_to_check = message.text
            elif hasattr(message, 'caption') and message.caption:
                text_to_check = message.caption
            
            if not text_to_check:
                return True  # Allow non-text messages
            
            # Simple language detection based on character sets
            detected_language = self._detect_language(text_to_check)
            
            language_filter_mode = settings.get("language_filter_mode", "blacklist")
            allowed_languages = settings.get("allowed_languages", []) or []
            
            if language_filter_mode == "whitelist":
                # Whitelist mode: allow only if language is in allowed list
                return detected_language in allowed_languages
            else:
                # Blacklist mode: block if language is in blocked list
                return detected_language not in allowed_languages
                
        except Exception as e:
            logger.error(f"Error checking language filter: {e}")
            return True  # Allow on error
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character sets"""
        try:
            # Remove spaces and punctuation for analysis
            clean_text = ''.join(c for c in text if c.isalpha())
            
            if not clean_text:
                return "unknown"
            
            # Count character types
            arabic_chars = sum(1 for c in clean_text if '\u0600' <= c <= '\u06FF')
            latin_chars = sum(1 for c in clean_text if c.isascii() and c.isalpha())
            cyrillic_chars = sum(1 for c in clean_text if '\u0400' <= c <= '\u04FF')
            chinese_chars = sum(1 for c in clean_text if '\u4e00' <= c <= '\u9fff')
            japanese_chars = sum(1 for c in clean_text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
            korean_chars = sum(1 for c in clean_text if '\uac00' <= c <= '\ud7af')
            
            total_chars = len(clean_text)
            
            # Determine dominant language (threshold: 30%)
            threshold = total_chars * 0.3
            
            if arabic_chars > threshold:
                return "ar"
            elif cyrillic_chars > threshold:
                return "ru"
            elif chinese_chars > threshold:
                return "zh"
            elif japanese_chars > threshold:
                return "ja"
            elif korean_chars > threshold:
                return "ko"
            elif latin_chars > threshold:
                # Could be English, Spanish, French, etc.
                # Simple heuristic based on common words
                text_lower = text.lower()
                if any(word in text_lower for word in ["the", "and", "is", "in", "to", "of", "a", "that"]):
                    return "en"
                elif any(word in text_lower for word in ["el", "la", "de", "que", "y", "en", "un", "es"]):
                    return "es"
                elif any(word in text_lower for word in ["le", "de", "et", "à", "un", "il", "être", "et"]):
                    return "fr"
                elif any(word in text_lower for word in ["der", "die", "und", "in", "den", "von", "zu", "das"]):
                    return "de"
                elif any(word in text_lower for word in ["il", "di", "che", "e", "la", "un", "a", "per"]):
                    return "it"
                elif any(word in text_lower for word in ["o", "de", "que", "e", "do", "da", "em", "um"]):
                    return "pt"
                else:
                    return "en"  # Default to English for Latin script
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "unknown"

    async def add_task(self, task_id: int):
        """Add a new task to monitoring"""
        try:
            # Reload tasks to get the new one
            await self._load_active_tasks()
            
            if task_id in self.active_tasks_cache:
                task = self.active_tasks_cache[task_id]
                await self._start_task_monitoring(task_id, task)
                logger.info(f"Added task {task_id} to monitoring")
            
        except Exception as e:
            logger.error(f"Error adding task {task_id}: {e}")
    
    async def remove_task(self, task_id: int):
        """Remove a task from monitoring"""
        try:
            await self._stop_task_monitoring(task_id)
            if task_id in self.active_tasks_cache:
                del self.active_tasks_cache[task_id]
            logger.info(f"Removed task {task_id} from monitoring")
            
        except Exception as e:
            logger.error(f"Error removing task {task_id}: {e}")
    
    async def toggle_task(self, task_id: int, active: bool):
        """Toggle task active status"""
        try:
            if active:
                await self.add_task(task_id)
            else:
                await self.remove_task(task_id)
                
        except Exception as e:
            logger.error(f"Error toggling task {task_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        try:
            # Calculate uptime
            uptime = "Unknown"
            if self.start_time:
                uptime_delta = datetime.now() - self.start_time
                hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                uptime = f"{hours}h {minutes}m"
            
            # Calculate success rate
            total_messages = self.successful_forwards + self.failed_forwards
            success_rate = (self.successful_forwards / total_messages * 100) if total_messages > 0 else 0
            
            # Calculate average processing time
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            
            # Get memory usage
            memory_usage = f"{psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB"
            
            return {
                "running": self.running,
                "uptime": uptime,
                "active_monitors": len(self.monitors),
                "messages_processed": self.messages_processed,
                "successful_forwards": self.successful_forwards,
                "failed_forwards": self.failed_forwards,
                "success_rate": success_rate,
                "avg_processing_time": avg_processing_time,
                "memory_usage": memory_usage,
                "duplicate_tracker_size": len(self.duplicate_tracker)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"running": self.running, "error": str(e)}

    async def _find_forwarded_message_id(self, task_id: int, original_message_id: int, target_chat_id: int) -> Optional[int]:
        """Find the forwarded message ID for reply preservation in specific target chat"""
        try:
            import json
            
            # First try: Look for exact match with this target chat
            query = """
            SELECT target_message_ids FROM message_tracking 
            WHERE task_id = $1 AND source_message_id = $2
            ORDER BY created_at DESC LIMIT 5
            """
            result = await self.database.execute_query(query, task_id, original_message_id)
            
            if result:
                for row in result:
                    target_message_ids = row.get('target_message_ids')
                    if target_message_ids:
                        try:
                            target_mappings = json.loads(target_message_ids) if isinstance(target_message_ids, str) else target_message_ids
                            
                            # Look for mapping that matches our target chat ID
                            if isinstance(target_mappings, list):
                                for mapping in target_mappings:
                                    if isinstance(mapping, dict):
                                        # Check if this mapping contains our target chat ID
                                        chat_key = str(target_chat_id)
                                        if chat_key in mapping:
                                            forwarded_id = mapping[chat_key]
                                            logger.info(f"Found exact chat match for reply: original={original_message_id} -> forwarded={forwarded_id} in chat {target_chat_id}")
                                            return forwarded_id
                                
                                # Fallback: if no exact chat match, try first available mapping
                                for mapping in target_mappings:
                                    if isinstance(mapping, dict) and mapping:
                                        forwarded_id = next(iter(mapping.values()))
                                        logger.info(f"Found fallback mapping for reply: original={original_message_id} -> forwarded={forwarded_id}")
                                        return forwarded_id
                                    elif isinstance(mapping, int):
                                        # Old format: direct message ID
                                        logger.info(f"Found direct mapping for reply: original={original_message_id} -> forwarded={mapping}")
                                        return mapping
                                
                        except (json.JSONDecodeError, TypeError, IndexError):
                            continue
            
            # Second try: Search by similar timing (messages sent close to each other)
            query = """
            SELECT target_message_ids FROM message_tracking 
            WHERE task_id = $1 
            AND source_message_id BETWEEN $2 - 10 AND $2 + 10
            AND target_message_ids IS NOT NULL
            ORDER BY ABS(source_message_id - $2) ASC
            LIMIT 10
            """
            result = await self.database.execute_query(query, task_id, original_message_id)
            
            if result:
                for row in result:
                    target_message_ids = row.get('target_message_ids')
                    if target_message_ids:
                        try:
                            target_mappings = json.loads(target_message_ids) if isinstance(target_message_ids, str) else target_message_ids
                            if isinstance(target_mappings, list) and target_mappings:
                                forwarded_id = target_mappings[0]
                                logger.info(f"Found nearby forwarded message for reply: original={original_message_id} -> forwarded={forwarded_id}")
                                return forwarded_id
                        except (json.JSONDecodeError, TypeError, IndexError):
                            continue
                        
            logger.info(f"No forwarded message found for original={original_message_id} in chat {target_chat_id}")
            return None
        except Exception as e:
            logger.error(f"Error finding forwarded message ID: {e}")
            return None

    async def _store_message_mapping(self, task_id: int, original_message_id: int, 
                                   forwarded_message_id: int, target_chat_id: int):
        """Store message mapping for reply preservation with specific target chat ID"""
        try:
            import json
            
            # Get source chat ID for this task
            source_chat_id = await self._get_source_chat_id(task_id)
            
            # Check if record exists for this combination
            check_query = """
            SELECT target_message_ids FROM message_tracking 
            WHERE task_id = $1 AND source_message_id = $2 AND source_chat_id = $3
            """
            existing = await self.database.execute_query(check_query, task_id, original_message_id, source_chat_id)
            
            if existing:
                # Update existing record by adding the new target mapping
                current_targets = existing[0].get('target_message_ids')
                try:
                    target_list = json.loads(current_targets) if isinstance(current_targets, str) else current_targets
                    if not isinstance(target_list, list):
                        target_list = []
                    
                    # Add new mapping as {chat_id: message_id}
                    new_mapping = {str(target_chat_id): forwarded_message_id}
                    target_list.append(new_mapping)
                    
                    update_query = """
                    UPDATE message_tracking 
                    SET target_message_ids = $1::jsonb 
                    WHERE task_id = $2 AND source_message_id = $3 AND source_chat_id = $4
                    """
                    await self.database.execute_command(update_query, json.dumps(target_list), task_id, original_message_id, source_chat_id)
                    logger.info(f"Updated message mapping: task={task_id}, source={original_message_id} -> target={forwarded_message_id} in chat {target_chat_id}")
                    
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, create new record
                    target_ids_json = json.dumps([{str(target_chat_id): forwarded_message_id}])
                    update_query = """
                    UPDATE message_tracking 
                    SET target_message_ids = $1::jsonb 
                    WHERE task_id = $2 AND source_message_id = $3 AND source_chat_id = $4
                    """
                    await self.database.execute_command(update_query, target_ids_json, task_id, original_message_id, source_chat_id)
            else:
                # Create new record
                target_ids_json = json.dumps([{str(target_chat_id): forwarded_message_id}])
                
                insert_query = """
                INSERT INTO message_tracking (task_id, source_message_id, source_chat_id, target_message_ids, created_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW())
                """
                await self.database.execute_command(insert_query, task_id, original_message_id, source_chat_id, target_ids_json)
                logger.info(f"Created message mapping: task={task_id}, source={original_message_id} -> target={forwarded_message_id} in chat {target_chat_id}")
                
        except Exception as e:
            logger.error(f"Error storing message mapping: {e}")
    
    async def _get_source_chat_id(self, task_id: int) -> int:
        """Get the source chat ID for a task"""
        try:
            query = "SELECT source_chat_id FROM sources WHERE task_id = $1 LIMIT 1"
            result = await self.database.execute_query(query, task_id)
            if result:
                return result[0]['source_chat_id']
            return -1002289754739  # fallback to known source chat
        except:
            return -1002289754739
