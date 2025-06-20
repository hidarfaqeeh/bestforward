"""
Source Handlers - Source channel management
"""

import asyncio
from typing import Any, Dict, List, Optional

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from utils import parse_chat_identifier, validate_telegram_data


class SourceStates(StatesGroup):
    """FSM States for source operations"""
    ADDING_SOURCE = State()
    WAITING_SOURCE_INPUT = State()


class SourceHandlers:
    """Handles source channel management"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.bot = bot_controller.bot
        self.database = bot_controller.database
        self.security_manager = bot_controller.security_manager
        self.keyboards = bot_controller.keyboards
        self.forwarding_engine = bot_controller.forwarding_engine
        
    async def register_handlers(self):
        """Register source handlers"""
        try:
            # Source input handler
            self.bot_controller.dispatcher.message.register(
                self.handle_source_input,
                SourceStates.WAITING_SOURCE_INPUT
            )
            
            logger.info("Source handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register source handlers: {e}")
            raise
    
    async def handle_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle source callback queries"""
        data = callback.data
        user_id = callback.from_user.id
        
        try:
            if data.startswith("source_list_"):
                await self._handle_source_list(callback, state)
            elif data.startswith("source_add_"):
                await self._handle_source_add(callback, state)
            elif data.startswith("source_view_"):
                await self._handle_source_view(callback, state)
            elif data.startswith("source_remove_"):
                await self._handle_source_remove(callback, state)
            elif data.startswith("source_toggle_"):
                await self._handle_source_toggle(callback, state)
            elif data.startswith("source_test_"):
                await self._handle_source_test(callback, state)
            elif data.startswith("confirm_remove_source_"):
                await self._handle_confirm_source_remove(callback, state)
            elif data.startswith("cancel_remove_source_"):
                await self._handle_cancel_source_remove(callback, state)
            else:
                await callback.answer("❌ Unknown source action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in source callback {data}: {e}")
            await callback.answer("❌ An error occurred.", show_alert=True)
    
    async def _handle_source_list(self, callback: CallbackQuery, state: FSMContext):
        """Handle source list display"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get task sources
            sources = await self.database.get_task_sources(task_id)
            
            if not sources:
                no_sources_text = f"""
📥 **Source Channels** (Task {task_id})

No source channels configured yet.

**What are source channels?**
These are the channels/groups that the bot will monitor for new messages to forward.

**Supported formats:**
• Channel username: @channel_username
• Channel ID: -1001234567890
• Channel link: https://t.me/channel_username
• Private channel invite link

Add your first source channel below.
                """
                
                keyboard = [
                    [InlineKeyboardButton(text="➕ Add Source", callback_data=f"source_add_{task_id}")],
                    [InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")]
                ]
                
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await callback.message.edit_text(no_sources_text, reply_markup=markup)
                return
            
            # Format sources list
            sources_text = f"""
📥 **Source Channels** (Task {task_id})

**Total Sources:** {len(sources)}
**Active Sources:** {len([s for s in sources if s['is_active']])}

**Sources:**
{self._format_sources_list(sources)}

Select a source to view details or manage it.
            """
            
            # Create sources keyboard
            keyboard = await self.keyboards.get_source_management_keyboard(task_id, sources)
            
            # Always try to update the content
            try:
                await callback.message.edit_text(sources_text, reply_markup=keyboard)
            except Exception as edit_error:
                if "message is not modified" in str(edit_error).lower():
                    await callback.answer("✅ Sources list refreshed")
                else:
                    logger.error(f"Error editing message: {edit_error}")
                    await callback.answer("❌ Error refreshing list")
            
        except Exception as e:
            logger.error(f"Error displaying source list: {e}")
            await callback.answer("❌ Error loading source list.")
    
    async def _handle_source_add(self, callback: CallbackQuery, state: FSMContext):
        """Handle source addition"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Store task ID in session
            await self.bot_controller.update_user_session(
                callback.from_user.id,
                {"adding_source_task_id": task_id}
            )
            
            add_text = f"""
➕ **Add Source Channel** (Task {task_id})

Please send the channel information in one of these formats:

**Username:** @channel_username
**Channel ID:** -1001234567890
**Channel Link:** https://t.me/channel_username
**Invite Link:** https://t.me/joinchat/xxxxx

**Note:**
• For Bot API mode: Bot must be admin in the channel or channel must be public
• For Userbot mode: Your account must have access to the channel

Send the channel information now:
            """
            
            await callback.message.edit_text(add_text)
            await state.set_state(SourceStates.WAITING_SOURCE_INPUT)
            
        except Exception as e:
            logger.error(f"Error starting source addition: {e}")
            await callback.answer("❌ Error starting source addition.")
    
    async def handle_source_input(self, message: Message, state: FSMContext):
        """Handle source channel input"""
        try:
            user_id = message.from_user.id
            
            # Get session data
            session_data = await self.bot_controller.get_user_session(user_id)
            task_id = session_data.get("adding_source_task_id")
            
            if not task_id:
                await message.answer("❌ Session expired. Please start source addition again.")
                await state.clear()
                return
            
            # Parse channel identifier
            channel_input = message.text.strip()
            parsed_id = parse_chat_identifier(channel_input)
            
            if parsed_id["type"] == "error":
                await message.answer(
                    "❌ Invalid channel format. Please use:\n"
                    "• @username\n"
                    "• Channel ID\n"
                    "• t.me/username\n"
                    "• Invite link"
                )
                return
            
            # Get task to determine mode
            task = await self.database.execute_query(
                "SELECT task_type FROM tasks WHERE id = $1", task_id
            )
            
            if not task:
                await message.answer("❌ Task not found.")
                await state.clear()
                return
            
            task_type = task[0]["task_type"]
            
            # Try to get channel information
            chat_info = await self._get_channel_info(parsed_id, task_type)
            
            if not chat_info:
                await message.answer(
                    "❌ Could not access the channel. Please check:\n"
                    "• Channel exists and is accessible\n"
                    "• Bot has necessary permissions\n"
                    "• Channel format is correct"
                )
                return
            
            # Check if source already exists
            existing_sources = await self.database.get_task_sources(task_id)
            if any(s["chat_id"] == chat_info["chat_id"] for s in existing_sources):
                await message.answer("❌ This channel is already added as a source.")
                return
            
            # Add source to database
            success = await self._add_source_to_task(task_id, chat_info)
            
            if success:
                # Update forwarding engine if task is active
                task_info = await self.database.execute_query(
                    "SELECT is_active FROM tasks WHERE id = $1", task_id
                )
                
                if task_info and task_info[0]["is_active"]:
                    # Notify forwarding engine to update monitors
                    if task_id in self.forwarding_engine.monitors:
                        monitor = self.forwarding_engine.monitors[task_id]
                        await monitor.add_source(chat_info["chat_id"])
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                success_text = f"""
✅ **Source Added Successfully!**

📥 **{chat_info['chat_title']}**
🆔 ID: `{chat_info['chat_id']}`
📱 Type: {chat_info['chat_type'].title()}

The channel is now being monitored for new messages.
                """
                
                keyboard = [
                    [
                        InlineKeyboardButton(text="➕ Add Another", callback_data=f"source_add_{task_id}"),
                        InlineKeyboardButton(text="📋 View Sources", callback_data=f"source_list_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                    ]
                ]
                
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await message.answer(success_text, reply_markup=markup)
                
            else:
                await message.answer("❌ Failed to add source. Please try again.")
            
            # Clear session and state
            await self.bot_controller.clear_user_session(user_id)
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error handling source input: {e}")
            await message.answer("❌ An error occurred while adding the source.")
            await state.clear()
    
    async def _handle_source_view(self, callback: CallbackQuery, state: FSMContext):
        """Handle source view"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            source_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get source information
            source_info = await self.database.execute_query(
                "SELECT * FROM sources WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            if not source_info:
                await callback.answer("❌ Source not found.", show_alert=True)
                return
            
            source = source_info[0]
            
            # Get recent activity
            recent_messages = await self.database.execute_query("""
                SELECT COUNT(*) as count
                FROM forwarding_logs 
                WHERE task_id = $1 AND source_chat_id = $2 
                AND processed_at >= NOW() - INTERVAL '24 hours'
            """, task_id, source["chat_id"])
            
            recent_count = recent_messages[0]["count"] if recent_messages else 0
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            source_text = f"""
📥 **Source Details**

**Channel Information:**
• Name: {source['chat_title'] or 'Unknown'}
• ID: `{source['chat_id']}`
• Username: @{source['chat_username'] or 'None'}
• Type: {source['chat_type'] or 'Unknown'}
• Status: {'🟢 Active' if source['is_active'] else '🔴 Inactive'}

**Activity:**
• Added: {source['created_at'].strftime('%Y-%m-%d %H:%M')}
• Messages Today: {recent_count}

**Actions:**
Use the buttons below to manage this source.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="⏹️ Disable" if source['is_active'] else "▶️ Enable",
                        callback_data=f"source_toggle_{task_id}_{source_id}"
                    ),
                    InlineKeyboardButton(text="🔍 Test", callback_data=f"source_test_{task_id}_{source_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Remove", callback_data=f"source_remove_{task_id}_{source_id}"),
                    InlineKeyboardButton(text="📊 Statistics", callback_data=f"source_stats_{task_id}_{source_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Sources", callback_data=f"source_list_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(source_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error viewing source: {e}")
            await callback.answer("❌ Error loading source details.")
    
    async def _handle_source_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle source removal confirmation"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            source_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get source information
            source_info = await self.database.execute_query(
                "SELECT * FROM sources WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            if not source_info:
                await callback.answer("❌ Source not found.", show_alert=True)
                return
            
            source = source_info[0]
            
            confirm_text = f"""
🗑️ **Remove Source Confirmation**

Are you sure you want to remove this source?

📥 **{source['chat_title'] or 'Unknown'}**
🆔 ID: `{source['chat_id']}`

⚠️ **Warning:**
• The channel will no longer be monitored
• Historical data will be preserved
• This action can be undone by re-adding the source
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="✅ Yes, Remove", callback_data=f"confirm_remove_source_{task_id}_{source_id}"),
                    InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_remove_source_{task_id}_{source_id}")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(confirm_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error preparing source removal: {e}")
            await callback.answer("❌ Error preparing source removal.")
    
    async def _handle_confirm_source_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle confirmed source removal"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[3])
            source_id = int(parts[4])
            
            # Get source info for chat_id
            source_info = await self.database.execute_query(
                "SELECT chat_id FROM sources WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            if not source_info:
                await callback.answer("❌ Source not found.", show_alert=True)
                return
            
            chat_id = source_info[0]["chat_id"]
            
            # Remove from database
            await self.database.execute_command(
                "DELETE FROM sources WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            # Update forwarding engine if task is active
            task_info = await self.database.execute_query(
                "SELECT is_active FROM tasks WHERE id = $1", task_id
            )
            
            if task_info and task_info[0]["is_active"]:
                if task_id in self.forwarding_engine.monitors:
                    monitor = self.forwarding_engine.monitors[task_id]
                    await monitor.remove_source(chat_id)
            
            await callback.answer("✅ Source removed successfully!", show_alert=True)
            
            # Return to source list
            await self._handle_source_list(callback, state)
            
        except Exception as e:
            logger.error(f"Error removing source: {e}")
            await callback.answer("❌ Error removing source.")
    
    async def _handle_cancel_source_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle cancelled source removal"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[3])
            source_id = int(parts[4])
            
            # Return to source view
            callback.data = f"source_view_{task_id}_{source_id}"
            await self._handle_source_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error cancelling source removal: {e}")
            await callback.answer("❌ Error cancelling removal.")
    
    async def _handle_source_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle source enable/disable"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            source_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Toggle source status
            await self.database.execute_command(
                "UPDATE sources SET is_active = NOT is_active WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            # Get new status
            source_info = await self.database.execute_query(
                "SELECT is_active, chat_id FROM sources WHERE id = $1 AND task_id = $2",
                source_id, task_id
            )
            
            if source_info:
                new_status = source_info[0]["is_active"]
                chat_id = source_info[0]["chat_id"]
                
                # Update forwarding engine
                if task_id in self.forwarding_engine.monitors:
                    sources = await self.database.get_task_sources(task_id)
                    monitor = self.forwarding_engine.monitors[task_id]
                    await monitor.update_sources(sources)
                
                status_text = "✅ Source enabled!" if new_status else "⏹️ Source disabled!"
                await callback.answer(status_text, show_alert=True)
                
                # Refresh source view
                await self._handle_source_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling source: {e}")
            await callback.answer("❌ Error toggling source status.")
    
    async def _handle_source_test(self, callback: CallbackQuery, state: FSMContext):
        """Handle source connectivity test"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            source_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get source and task info
            source_info = await self.database.execute_query(
                "SELECT s.*, t.task_type FROM sources s JOIN tasks t ON s.task_id = t.id WHERE s.id = $1",
                source_id
            )
            
            if not source_info:
                await callback.answer("❌ Source not found.", show_alert=True)
                return
            
            source = source_info[0]
            chat_id = source["chat_id"]
            task_type = source["task_type"]
            
            await callback.answer("🔍 Testing connectivity...", show_alert=False)
            
            # Test connectivity
            try:
                if task_type == "userbot" and self.bot_controller.userbot:
                    chat = await self.bot_controller.userbot.get_chat(chat_id)
                    test_result = f"""
✅ **Connection Test Successful**

📥 **{chat.title}**
🆔 ID: `{chat_id}`
👥 Members: {getattr(chat, 'members_count', 'Unknown')}
📱 Type: {str(chat.type)}
🤖 Mode: Userbot

Connection is working properly!
                    """
                else:
                    chat = await self.bot.get_chat(chat_id)
                    test_result = f"""
✅ **Connection Test Successful**

📥 **{chat.title}**
🆔 ID: `{chat_id}`
👥 Members: {getattr(chat, 'member_count', 'Unknown')}
📱 Type: {chat.type}
🤖 Mode: Bot API

Connection is working properly!
                    """
                    
            except Exception as e:
                test_result = f"""
❌ **Connection Test Failed**

📥 **{source['chat_title']}**
🆔 ID: `{chat_id}`

**Error:** {str(e)}

**Possible causes:**
• Channel is private and bot lacks access
• Channel was deleted or moved
• Bot was removed from channel
• Network connectivity issues
                """
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 Back", callback_data=f"source_view_{task_id}_{source_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(test_result, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error testing source: {e}")
            await callback.answer("❌ Error testing source connectivity.")
    
    async def _verify_task_ownership(self, task_id: int, user_id: int) -> bool:
        """Verify that user owns the task"""
        try:
            task_info = await self.database.execute_query("""
                SELECT t.id FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = $1 AND u.telegram_id = $2
            """, task_id, user_id)
            
            return len(task_info) > 0
        except Exception as e:
            logger.error(f"Error verifying task ownership: {e}")
            return False
    
    async def _get_channel_info(self, parsed_id: dict, task_type: str) -> Optional[dict]:
        """Get channel information using bot or userbot"""
        try:
            chat_info = None
            
            # Try with Bot API first
            try:
                if parsed_id["type"] == "id":
                    chat = await self.bot.get_chat(parsed_id["value"])
                elif parsed_id["type"] == "username":
                    chat = await self.bot.get_chat(f"@{parsed_id['value']}")
                elif parsed_id["type"] == "invite":
                    # Can't get info from invite links with bot API
                    chat = None
                else:
                    chat = None
                
                if chat:
                    chat_info = {
                        "chat_id": chat.id,
                        "chat_title": chat.title or chat.first_name or f"Chat {chat.id}",
                        "chat_type": chat.type.value,
                        "username": getattr(chat, 'username', None)
                    }
            except Exception as bot_error:
                logger.warning(f"Bot API failed to get chat info: {bot_error}")
                chat_info = None
            
            # Try with userbot if bot API failed and userbot is available
            if not chat_info and hasattr(self.bot_controller, 'userbot') and self.bot_controller.userbot:
                try:
                    userbot = self.bot_controller.userbot
                    
                    if parsed_id["type"] == "id":
                        entity = await userbot.get_entity(parsed_id["value"])
                    elif parsed_id["type"] == "username":
                        entity = await userbot.get_entity(parsed_id["value"])
                    elif parsed_id["type"] == "invite":
                        # Try to join from invite link to get info
                        entity = await userbot.get_entity(parsed_id["value"])
                    else:
                        entity = None
                    
                    if entity:
                        chat_info = {
                            "chat_id": entity.id,
                            "chat_title": getattr(entity, 'title', None) or getattr(entity, 'first_name', None) or f"Chat {entity.id}",
                            "chat_type": "channel" if hasattr(entity, 'broadcast') else "group",
                            "username": getattr(entity, 'username', None)
                        }
                except Exception as userbot_error:
                    logger.warning(f"Userbot failed to get chat info: {userbot_error}")
                    chat_info = None
            
            return chat_info
            
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return None
    
    async def _add_source_to_task(self, task_id: int, chat_info: dict) -> bool:
        """Add source to task in database"""
        try:
            await self.database.execute_command("""
                INSERT INTO sources (task_id, chat_id, chat_title, chat_type, username, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, task_id, chat_info["chat_id"], chat_info["chat_title"], 
                chat_info["chat_type"], chat_info.get("username"), True)
            
            return True
        except Exception as e:
            logger.error(f"Error adding source to database: {e}")
            return False
    
    def _format_sources_list(self, sources: List[dict]) -> str:
        """Format sources list for display"""
        sources_list = ""
        for i, source in enumerate(sources[:10], 1):  # Show max 10 sources
            status_emoji = "🟢" if source["is_active"] else "🔴"
            title = source.get("chat_title", f"ID: {source['chat_id']}")
            sources_list += f"{i}. {status_emoji} **{title[:25]}{'...' if len(title) > 25 else ''}**\n"
            sources_list += f"   🆔 `{source['chat_id']}`\n"
            if source.get("username"):
                sources_list += f"   📧 @{source['username']}\n"
            sources_list += "\n"
        
        if len(sources) > 10:
            sources_list += f"... and {len(sources) - 10} more sources\n"
        
        return sources_list
    
    async def _get_channel_info(self, parsed_id: Dict[str, Any], task_type: str) -> Optional[Dict[str, Any]]:
        """Get channel information using both Bot API and Telethon userbot"""
        try:
            chat_id = parsed_id["value"]
            logger.info(f"Getting channel info for {chat_id} using {task_type} mode")
            
            # Try userbot first if available and task_type is userbot
            if task_type == "userbot" and self.bot_controller.userbot:
                try:
                    from telethon.tl.types import Channel, Chat, User
                    
                    entity = await self.bot_controller.userbot.get_entity(chat_id)
                    
                    if isinstance(entity, Channel):
                        chat_type = "channel" if entity.broadcast else "supergroup"
                        title = entity.title
                        username = entity.username
                    elif isinstance(entity, Chat):
                        chat_type = "group"
                        title = entity.title
                        username = None
                    elif isinstance(entity, User):
                        chat_type = "private"
                        title = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
                        username = entity.username
                    else:
                        title = "Unknown"
                        username = None
                        chat_type = "unknown"
                    
                    return {
                        "chat_id": entity.id if hasattr(entity, 'id') else chat_id,
                        "chat_title": title,
                        "chat_username": username,
                        "chat_type": chat_type
                    }
                    
                except Exception as userbot_error:
                    logger.warning(f"Userbot failed for {chat_id}: {userbot_error}")
                    # Fall back to Bot API
            
            # Try Bot API as fallback or primary method
            try:
                chat = await self.bot.get_chat(chat_id)
                
                return {
                    "chat_id": chat.id,
                    "chat_title": chat.title or chat.first_name or "Unknown",
                    "chat_username": getattr(chat, 'username', None),
                    "chat_type": chat.type
                }
                
            except Exception as bot_error:
                logger.warning(f"Bot API failed for {chat_id}: {bot_error}")
                
                # If both methods fail, try a basic approach
                if isinstance(chat_id, str) and chat_id.startswith('@'):
                    # For username channels, try a simple approach
                    return {
                        "chat_id": chat_id,
                        "chat_title": chat_id,
                        "chat_username": chat_id.replace('@', ''),
                        "chat_type": "channel"
                    }
                elif isinstance(chat_id, (int, str)) and str(chat_id).lstrip('-').isdigit():
                    # For numeric IDs, create basic info
                    return {
                        "chat_id": int(chat_id),
                        "chat_title": f"Channel {chat_id}",
                        "chat_username": None,
                        "chat_type": "channel"
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting channel info for {chat_id}: {e}")
            return None
    
    async def _add_source_to_task(self, task_id: int, chat_info: Dict[str, Any]) -> bool:
        """Add source to task"""
        try:
            query = """
                INSERT INTO sources (task_id, chat_id, chat_title, chat_username, chat_type, is_active, added_at, created_at)
                VALUES ($1, $2, $3, $4, $5, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            await self.database.execute_command(
                query,
                task_id,
                chat_info["chat_id"],
                chat_info["chat_title"],
                chat_info.get("chat_username"),
                chat_info["chat_type"]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding source to task: {e}")
            return False
    
    def _format_sources_list(self, sources: List[Dict]) -> str:
        """Format sources list for display"""
        if not sources:
            return "No sources configured."
        
        formatted = []
        for i, source in enumerate(sources[:10], 1):  # Limit to 10 sources
            status_emoji = "🟢" if source["is_active"] else "🔴"
            title = source["chat_title"] or f"ID: {source['chat_id']}"
            
            formatted.append(f"{i}. {status_emoji} {title[:30]}{'...' if len(title) > 30 else ''}")
        
        if len(sources) > 10:
            formatted.append(f"... and {len(sources) - 10} more")
        
        return "\n".join(formatted)
