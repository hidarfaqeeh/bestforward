"""
Channel Monitor - Monitors source channels for new messages
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import Message as PyrogramMessage
from loguru import logger


class ChannelMonitor:
    """Monitors channels for new messages and triggers forwarding"""
    
    def __init__(self, task_id: int, task: Dict[str, Any], sources: List[Dict[str, Any]], 
                 settings: Optional[Dict[str, Any]], bot: Bot, userbot: Optional[Client], 
                 forwarding_engine):
        self.task_id = task_id
        self.task = task
        self.sources = sources
        self.settings = settings or {}
        self.bot = bot
        self.userbot = userbot
        self.forwarding_engine = forwarding_engine
        
        # Monitor state
        self.running = False
        self.handlers = []
        self.source_chat_ids = [source["chat_id"] for source in sources if source["is_active"]]
        
        # Statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.start_time = None
        
    async def start(self):
        """Start monitoring channels"""
        if self.running:
            logger.warning(f"Monitor for task {self.task_id} is already running")
            return
        
        try:
            self.running = True
            self.start_time = datetime.now()
            
            if self.task["task_type"] == "userbot" and self.userbot:
                await self._start_userbot_monitoring()
            else:
                await self._start_bot_monitoring()
            
            logger.info(f"Started monitoring for task {self.task_id} ({len(self.source_chat_ids)} sources)")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring for task {self.task_id}: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop monitoring channels"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Remove handlers
            if self.task["task_type"] == "userbot" and self.userbot:
                for handler in self.handlers:
                    self.userbot.remove_handler(handler)
            
            self.handlers.clear()
            
            logger.info(f"Stopped monitoring for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error stopping monitor for task {self.task_id}: {e}")
    
    async def _start_userbot_monitoring(self):
        """Start monitoring using userbot (Telethon)"""
        try:
            if not self.userbot or not self.userbot.is_connected():
                logger.error(f"Userbot not available for task {self.task_id}")
                return
            
            # Import Telethon events
            from telethon import events
            
            # Create event handler for new messages
            @self.userbot.on(events.NewMessage)
            async def handler(event):
                # Check if message is from one of our source chats
                if hasattr(event.message, 'peer_id'):
                    chat_id = abs(event.message.peer_id.channel_id) if hasattr(event.message.peer_id, 'channel_id') else None
                    if chat_id and chat_id in [abs(int(str(cid).replace('-100', ''))) for cid in self.source_chat_ids]:
                        await self._handle_userbot_message(self.task_id, event.message)
            
            logger.info(f"Userbot monitoring started for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error starting userbot monitoring for task {self.task_id}: {e}")
            raise
    
    async def _start_bot_monitoring(self):
        """Start monitoring using bot API (polling-based)"""
        try:
            # For bot API, we'll use a polling approach
            # This is a simplified implementation - in production you might want to use webhooks
            asyncio.create_task(self._poll_channels())
            
            logger.info(f"Bot polling monitoring started for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error starting bot monitoring for task {self.task_id}: {e}")
            raise
    
    async def _handle_userbot_message(self, client: Client, message: PyrogramMessage):
        """Handle incoming message from userbot"""
        try:
            if not self.running:
                return
            
            self.messages_received += 1
            
            # Check if message is from monitored source
            if message.chat.id not in self.source_chat_ids:
                return
            
            # Process message
            await self._process_message(message)
            
        except Exception as e:
            logger.error(f"Error handling userbot message in task {self.task_id}: {e}")
    
    async def _poll_channels(self):
        """Poll channels for new messages (Bot API)"""
        last_message_ids = {}
        
        # Initialize last message IDs
        for chat_id in self.source_chat_ids:
            try:
                # Get last message ID for each channel
                chat = await self.bot.get_chat(chat_id)
                # For bot API, we'll track from current time
                last_message_ids[chat_id] = 0
            except Exception as e:
                logger.error(f"Error initializing polling for chat {chat_id}: {e}")
                continue
        
        # Polling loop
        while self.running:
            try:
                for chat_id in self.source_chat_ids:
                    await self._check_new_messages(chat_id, last_message_ids)
                
                # Wait before next poll
                await asyncio.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in polling loop for task {self.task_id}: {e}")
                await asyncio.sleep(30)  # Longer wait on error
    
    async def _check_new_messages(self, chat_id: int, last_message_ids: Dict[int, int]):
        """Check for new messages in a channel"""
        try:
            # Since Bot API can't read channel history directly,
            # we rely on the channel_post handler in bot_controller
            # This method serves as a heartbeat to ensure monitoring is active
            
            current_time = int(time.time())
            last_check = getattr(self, '_last_heartbeat', 0)
            
            # Log heartbeat every 60 seconds to confirm monitoring is active
            if current_time - last_check > 60:
                logger.debug(f"Channel monitor heartbeat - task {self.task_id}, chat {chat_id}")
                self._last_heartbeat = current_time
            
        except TelegramAPIError as e:
            if "chat not found" not in str(e).lower():
                logger.error(f"Telegram API error checking chat {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking new messages for chat {chat_id}: {e}")
    
    async def _process_message(self, message: Any):
        """Process received message"""
        try:
            if not self.running:
                return
            
            self.messages_processed += 1
            
            # Forward to forwarding engine
            success = await self.forwarding_engine.process_message(
                task_id=self.task_id,
                source_chat_id=message.chat.id,
                message=message
            )
            
            if success:
                logger.debug(f"Message processed successfully for task {self.task_id}")
            else:
                logger.debug(f"Message processing failed for task {self.task_id}")
                
        except Exception as e:
            logger.error(f"Error processing message for task {self.task_id}: {e}")
    
    async def add_source(self, chat_id: int):
        """Add new source to monitor"""
        try:
            if chat_id in self.source_chat_ids:
                return
            
            self.source_chat_ids.append(chat_id)
            
            # Add handler for userbot
            if self.task["task_type"] == "userbot" and self.userbot and self.running:
                handler = self.userbot.add_handler(
                    self.userbot.on_message(
                        filters.chat(chat_id) & ~filters.service
                    )(self._handle_userbot_message)
                )
                self.handlers.append(handler)
            
            logger.info(f"Added source {chat_id} to monitor for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error adding source {chat_id} to task {self.task_id}: {e}")
    
    async def remove_source(self, chat_id: int):
        """Remove source from monitor"""
        try:
            if chat_id not in self.source_chat_ids:
                return
            
            self.source_chat_ids.remove(chat_id)
            
            # For userbot, we'd need to remove specific handlers
            # This is complex with current pyrogram design, so we restart monitoring
            if self.task["task_type"] == "userbot" and self.userbot and self.running:
                await self.stop()
                await self.start()
            
            logger.info(f"Removed source {chat_id} from monitor for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error removing source {chat_id} from task {self.task_id}: {e}")
    
    async def update_sources(self, sources: List[Dict[str, Any]]):
        """Update monitored sources"""
        try:
            new_chat_ids = [source["chat_id"] for source in sources if source["is_active"]]
            
            if set(new_chat_ids) == set(self.source_chat_ids):
                return  # No changes
            
            self.sources = sources
            self.source_chat_ids = new_chat_ids
            
            # Restart monitoring with new sources
            if self.running:
                await self.stop()
                await self.start()
            
            logger.info(f"Updated sources for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error updating sources for task {self.task_id}: {e}")
    
    async def update_settings(self, settings: Dict[str, Any]):
        """Update monitor settings"""
        try:
            self.settings = settings
            logger.info(f"Updated settings for task {self.task_id}")
            
        except Exception as e:
            logger.error(f"Error updating settings for task {self.task_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics"""
        try:
            uptime = 0
            if self.start_time:
                uptime = int((datetime.now() - self.start_time).total_seconds())
            
            return {
                "task_id": self.task_id,
                "running": self.running,
                "sources_count": len(self.source_chat_ids),
                "messages_received": self.messages_received,
                "messages_processed": self.messages_processed,
                "uptime_seconds": uptime,
                "task_type": self.task["task_type"]
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for task {self.task_id}: {e}")
            return {"task_id": self.task_id, "error": str(e)}
    
    async def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to monitored sources"""
        results = {}
        
        for chat_id in self.source_chat_ids:
            try:
                if self.task["task_type"] == "userbot" and self.userbot:
                    # Test with userbot
                    chat = await self.userbot.get_chat(chat_id)
                    results[chat_id] = {
                        "status": "connected",
                        "title": chat.title,
                        "type": str(chat.type),
                        "members_count": getattr(chat, 'members_count', None)
                    }
                else:
                    # Test with bot
                    chat = await self.bot.get_chat(chat_id)
                    results[chat_id] = {
                        "status": "connected",
                        "title": chat.title,
                        "type": chat.type,
                        "members_count": getattr(chat, 'member_count', None)
                    }
                    
            except Exception as e:
                results[chat_id] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    async def get_recent_messages(self, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from a source"""
        try:
            messages = []
            
            if self.task["task_type"] == "userbot" and self.userbot:
                # Get messages with userbot
                async for message in self.userbot.get_chat_history(chat_id, limit=limit):
                    messages.append({
                        "id": message.id,
                        "date": message.date,
                        "text": message.text or message.caption or "[Media]",
                        "from_user": message.from_user.first_name if message.from_user else "Channel",
                        "media": bool(message.media)
                    })
            else:
                # Bot API has limitations for reading messages
                # This would require the bot to be admin or use updates
                pass
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting recent messages for chat {chat_id}: {e}")
            return []
