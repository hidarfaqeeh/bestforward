"""
Target Handlers - Target channel management
"""

import asyncio
from typing import Any, Dict, List, Optional

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from utils import parse_chat_identifier, validate_telegram_data


class TargetStates(StatesGroup):
    """FSM States for target operations"""
    ADDING_TARGET = State()
    WAITING_TARGET_INPUT = State()


class TargetHandlers:
    """Handles target channel management"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.bot = bot_controller.bot
        self.database = bot_controller.database
        self.security_manager = bot_controller.security_manager
        self.keyboards = bot_controller.keyboards
        self.forwarding_engine = bot_controller.forwarding_engine
        
    async def register_handlers(self):
        """Register target handlers"""
        try:
            # Target input handler
            self.bot_controller.dispatcher.message.register(
                self.handle_target_input,
                TargetStates.WAITING_TARGET_INPUT
            )
            
            logger.info("Target handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register target handlers: {e}")
            raise
    
    async def handle_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle target callback queries"""
        data = callback.data
        user_id = callback.from_user.id
        
        try:
            if data.startswith("target_list_"):
                await self._handle_target_list(callback, state)
            elif data.startswith("target_add_"):
                await self._handle_target_add(callback, state)
            elif data.startswith("target_view_"):
                await self._handle_target_view(callback, state)
            elif data.startswith("target_remove_"):
                await self._handle_target_remove(callback, state)
            elif data.startswith("target_toggle_"):
                await self._handle_target_toggle(callback, state)
            elif data.startswith("target_test_"):
                await self._handle_target_test(callback, state)
            elif data.startswith("confirm_remove_target_"):
                await self._handle_confirm_target_remove(callback, state)
            elif data.startswith("cancel_remove_target_"):
                await self._handle_cancel_target_remove(callback, state)
            else:
                await callback.answer("❌ Unknown target action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in target callback {data}: {e}")
            await callback.answer("❌ An error occurred.", show_alert=True)
    
    async def _handle_target_list(self, callback: CallbackQuery, state: FSMContext):
        """Handle target list display"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get task targets
            targets = await self.database.get_task_targets(task_id)
            
            if not targets:
                no_targets_text = f"""
📤 **Target Channels** (Task {task_id})

No target channels configured yet.

**What are target channels?**
These are the channels/groups where forwarded messages will be sent.

**Requirements:**
• For Bot API mode: Bot must be admin with message posting permissions
• For Userbot mode: Your account must have sending permissions

**Supported formats:**
• Channel username: @channel_username
• Channel ID: -1001234567890
• Channel link: https://t.me/channel_username

Add your first target channel below.
                """
                
                keyboard = [
                    [InlineKeyboardButton(text="➕ Add Target", callback_data=f"target_add_{task_id}")],
                    [InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")]
                ]
                
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await callback.message.edit_text(no_targets_text, reply_markup=markup)
                return
            
            # Format targets list
            targets_text = f"""
📤 **Target Channels** (Task {task_id})

**Total Targets:** {len(targets)}
**Active Targets:** {len([t for t in targets if t['is_active']])}

**Targets:**
{self._format_targets_list(targets)}

Select a target to view details or manage it.
            """
            
            # Create targets keyboard
            keyboard = await self.keyboards.get_target_management_keyboard(task_id, targets)
            
            # Always try to update the content
            try:
                await callback.message.edit_text(targets_text, reply_markup=keyboard)
            except Exception as edit_error:
                if "message is not modified" in str(edit_error).lower():
                    await callback.answer("✅ Targets list refreshed")
                else:
                    logger.error(f"Error editing message: {edit_error}")
                    await callback.answer("❌ Error refreshing list")
            
        except Exception as e:
            logger.error(f"Error displaying target list: {e}")
            await callback.answer("❌ Error loading target list.")
    
    async def _handle_target_add(self, callback: CallbackQuery, state: FSMContext):
        """Handle target addition"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Store task ID in session
            await self.bot_controller.update_user_session(
                callback.from_user.id,
                {"adding_target_task_id": task_id}
            )
            
            add_text = f"""
➕ **Add Target Channel** (Task {task_id})

Please send the channel information in one of these formats:

**Username:** @channel_username
**Channel ID:** -1001234567890
**Channel Link:** https://t.me/channel_username

**Important Requirements:**
• For Bot API mode: Bot must be admin with message posting permissions
• For Userbot mode: Your account must have message sending permissions
• Channel must be accessible to the bot/userbot

Send the channel information now:
            """
            
            await callback.message.edit_text(add_text)
            await state.set_state(TargetStates.WAITING_TARGET_INPUT)
            
        except Exception as e:
            logger.error(f"Error starting target addition: {e}")
            await callback.answer("❌ Error starting target addition.")
    
    async def handle_target_input(self, message: Message, state: FSMContext):
        """Handle target channel input"""
        try:
            user_id = message.from_user.id
            
            # Get session data
            session_data = await self.bot_controller.get_user_session(user_id)
            task_id = session_data.get("adding_target_task_id")
            
            if not task_id:
                await message.answer("❌ Session expired. Please start target addition again.")
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
                    "• t.me/username"
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
            
            # Try to get channel information and test permissions
            chat_info = await self._get_channel_info_and_test(parsed_id, task_type)
            
            if not chat_info:
                await message.answer(
                    "❌ Could not access the channel or insufficient permissions. Please check:\n"
                    "• Channel exists and is accessible\n"
                    "• Bot has admin rights with message posting permissions\n"
                    "• Channel format is correct"
                )
                return
            
            # Check if target already exists
            existing_targets = await self.database.get_task_targets(task_id)
            if any(t["chat_id"] == chat_info["chat_id"] for t in existing_targets):
                await message.answer("❌ This channel is already added as a target.")
                return
            
            # Add target to database
            success = await self._add_target_to_task(task_id, chat_info)
            
            if success:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                success_text = f"""
✅ **Target Added Successfully!**

📤 **{chat_info['chat_title']}**
🆔 ID: `{chat_info['chat_id']}`
📱 Type: {chat_info['chat_type'].title()}

Messages will now be forwarded to this channel.
                """
                
                keyboard = [
                    [
                        InlineKeyboardButton(text="➕ Add Another", callback_data=f"target_add_{task_id}"),
                        InlineKeyboardButton(text="📋 View Targets", callback_data=f"target_list_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                    ]
                ]
                
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await message.answer(success_text, reply_markup=markup)
                
            else:
                await message.answer("❌ Failed to add target. Please try again.")
            
            # Clear session and state
            await self.bot_controller.clear_user_session(user_id)
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error handling target input: {e}")
            await message.answer("❌ An error occurred while adding the target.")
            await state.clear()
    
    async def _handle_target_view(self, callback: CallbackQuery, state: FSMContext):
        """Handle target view"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            target_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get target information
            target_info = await self.database.execute_query(
                "SELECT * FROM targets WHERE id = $1 AND task_id = $2",
                target_id, task_id
            )
            
            if not target_info:
                await callback.answer("❌ Target not found.", show_alert=True)
                return
            
            target = target_info[0]
            
            # Get forwarding statistics
            forwarding_stats = await self.database.execute_query("""
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    MAX(processed_at) as last_message
                FROM forwarding_logs 
                WHERE task_id = $1 AND target_chat_id = $2
            """, task_id, target["chat_id"])
            
            stats = forwarding_stats[0] if forwarding_stats else {}
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            target_text = f"""
📤 **Target Details**

**Channel Information:**
• Name: {target['chat_title'] or 'Unknown'}
• ID: `{target['chat_id']}`
• Username: @{target['chat_username'] or 'None'}
• Type: {target['chat_type'] or 'Unknown'}
• Status: {'🟢 Active' if target['is_active'] else '🔴 Inactive'}

**Statistics:**
• Total Messages: {stats.get('total_messages', 0)}
• Successful: {stats.get('successful', 0)}
• Failed: {stats.get('failed', 0)}
• Last Message: {stats.get('last_message').strftime('%Y-%m-%d %H:%M') if stats.get('last_message') else 'Never'}

**Activity:**
• Added: {target['created_at'].strftime('%Y-%m-%d %H:%M')}

**Actions:**
Use the buttons below to manage this target.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="⏹️ Disable" if target['is_active'] else "▶️ Enable",
                        callback_data=f"target_toggle_{task_id}_{target_id}"
                    ),
                    InlineKeyboardButton(text="🔍 Test", callback_data=f"target_test_{task_id}_{target_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Remove", callback_data=f"target_remove_{task_id}_{target_id}"),
                    InlineKeyboardButton(text="📊 Statistics", callback_data=f"target_stats_{task_id}_{target_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Targets", callback_data=f"target_list_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(target_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error viewing target: {e}")
            await callback.answer("❌ Error loading target details.")
    
    async def _handle_target_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle target removal confirmation"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            target_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get target information
            target_info = await self.database.execute_query(
                "SELECT * FROM targets WHERE id = $1 AND task_id = $2",
                target_id, task_id
            )
            
            if not target_info:
                await callback.answer("❌ Target not found.", show_alert=True)
                return
            
            target = target_info[0]
            
            confirm_text = f"""
🗑️ **Remove Target Confirmation**

Are you sure you want to remove this target?

📤 **{target['chat_title'] or 'Unknown'}**
🆔 ID: `{target['chat_id']}`

⚠️ **Warning:**
• Messages will no longer be forwarded to this channel
• Historical forwarding data will be preserved
• This action can be undone by re-adding the target
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="✅ Yes, Remove", callback_data=f"confirm_remove_target_{task_id}_{target_id}"),
                    InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_remove_target_{task_id}_{target_id}")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(confirm_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error preparing target removal: {e}")
            await callback.answer("❌ Error preparing target removal.")
    
    async def _handle_confirm_target_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle confirmed target removal"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[3])
            target_id = int(parts[4])
            
            # Remove from database
            await self.database.execute_command(
                "DELETE FROM targets WHERE id = $1 AND task_id = $2",
                target_id, task_id
            )
            
            await callback.answer("✅ Target removed successfully!", show_alert=True)
            
            # Return to target list
            await self._handle_target_list(callback, state)
            
        except Exception as e:
            logger.error(f"Error removing target: {e}")
            await callback.answer("❌ Error removing target.")
    
    async def _handle_cancel_target_remove(self, callback: CallbackQuery, state: FSMContext):
        """Handle cancelled target removal"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[3])
            target_id = int(parts[4])
            
            # Return to target view
            callback.data = f"target_view_{task_id}_{target_id}"
            await self._handle_target_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error cancelling target removal: {e}")
            await callback.answer("❌ Error cancelling removal.")
    
    async def _handle_target_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle target enable/disable"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            target_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Toggle target status
            await self.database.execute_command(
                "UPDATE targets SET is_active = NOT is_active WHERE id = $1 AND task_id = $2",
                target_id, task_id
            )
            
            # Get new status
            target_info = await self.database.execute_query(
                "SELECT is_active FROM targets WHERE id = $1 AND task_id = $2",
                target_id, task_id
            )
            
            if target_info:
                new_status = target_info[0]["is_active"]
                status_text = "✅ Target enabled!" if new_status else "⏹️ Target disabled!"
                await callback.answer(status_text, show_alert=True)
                
                # Refresh target view
                await self._handle_target_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling target: {e}")
            await callback.answer("❌ Error toggling target status.")
    
    async def _handle_target_test(self, callback: CallbackQuery, state: FSMContext):
        """Handle target connectivity and permissions test"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            target_id = int(parts[3])
            
            # Verify task ownership
            if not await self._verify_task_ownership(task_id, callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get target and task info
            target_info = await self.database.execute_query(
                "SELECT t.*, tasks.task_type FROM targets t JOIN tasks ON t.task_id = tasks.id WHERE t.id = $1",
                target_id
            )
            
            if not target_info:
                await callback.answer("❌ Target not found.", show_alert=True)
                return
            
            target = target_info[0]
            chat_id = target["chat_id"]
            task_type = target["task_type"]
            
            await callback.answer("🔍 Testing connectivity and permissions...", show_alert=False)
            
            # Test connectivity and permissions
            try:
                if task_type == "userbot" and self.bot_controller.userbot:
                    # Test with userbot
                    chat = await self.bot_controller.userbot.get_chat(chat_id)
                    
                    # Try to send a test message (if possible)
                    try:
                        # Get bot info to mention in test
                        bot_info = await self.bot.get_me()
                        test_message = await self.bot_controller.userbot.send_message(
                            chat_id, 
                            f"🔍 Test message from {bot_info.first_name} forwarding bot - Connection OK!"
                        )
                        
                        # Delete the test message
                        await self.bot_controller.userbot.delete_messages(chat_id, test_message.id)
                        
                        permissions_status = "✅ Send permissions confirmed"
                    except:
                        permissions_status = "⚠️ Cannot verify send permissions"
                    
                    test_result = f"""
✅ **Connection Test Successful**

📤 **{chat.title}**
🆔 ID: `{chat_id}`
👥 Members: {getattr(chat, 'members_count', 'Unknown')}
📱 Type: {str(chat.type)}
🤖 Mode: Userbot
🔒 Permissions: {permissions_status}

Target is ready for message forwarding!
                    """
                else:
                    # Test with bot API
                    chat = await self.bot.get_chat(chat_id)
                    
                    # Try to get bot member status
                    try:
                        bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
                        if bot_member.status in ['administrator']:
                            permissions_status = "✅ Admin permissions confirmed"
                        elif bot_member.status == 'member':
                            permissions_status = "⚠️ Member only (needs admin rights)"
                        else:
                            permissions_status = f"❌ Status: {bot_member.status}"
                    except:
                        permissions_status = "❌ Cannot verify bot permissions"
                    
                    test_result = f"""
✅ **Connection Test Successful**

📤 **{chat.title}**
🆔 ID: `{chat_id}`
👥 Members: {getattr(chat, 'member_count', 'Unknown')}
📱 Type: {chat.type}
🤖 Mode: Bot API
🔒 Permissions: {permissions_status}

{'Target is ready for message forwarding!' if 'confirmed' in permissions_status else 'Please ensure bot has proper permissions!'}
                    """
                    
            except Exception as e:
                test_result = f"""
❌ **Connection Test Failed**

📤 **{target['chat_title']}**
🆔 ID: `{chat_id}`

**Error:** {str(e)}

**Possible causes:**
• Channel is private and bot lacks access
• Bot was removed from channel
• Insufficient permissions (needs admin rights)
• Channel was deleted or moved
• Network connectivity issues

**Required permissions:**
• Bot must be admin with message posting rights
• For userbot: account needs send message permissions
                """
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 Back", callback_data=f"target_view_{task_id}_{target_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(test_result, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error testing target: {e}")
            await callback.answer("❌ Error testing target connectivity.")
    
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
    
    async def _get_channel_info_and_test(self, parsed_id: dict, task_type: str) -> Optional[dict]:
        """Get channel information and test permissions"""
        try:
            chat_info = None
            
            # Try with Bot API first
            try:
                if parsed_id["type"] == "id":
                    chat = await self.bot.get_chat(parsed_id["value"])
                elif parsed_id["type"] == "username":
                    chat = await self.bot.get_chat(f"@{parsed_id['value']}")
                else:
                    chat = None
                
                if chat:
                    # Test bot permissions
                    try:
                        bot_member = await self.bot.get_chat_member(chat.id, self.bot.id)
                        can_post = getattr(bot_member, 'can_post_messages', False) or getattr(bot_member, 'status', '') == 'administrator'
                        
                        if can_post:
                            chat_info = {
                                "chat_id": chat.id,
                                "chat_title": chat.title or chat.first_name or f"Chat {chat.id}",
                                "chat_type": chat.type.value,
                                "username": getattr(chat, 'username', None)
                            }
                    except Exception as perm_error:
                        logger.warning(f"Bot permission check failed: {perm_error}")
                        
            except Exception as bot_error:
                logger.warning(f"Bot API failed to get chat info: {bot_error}")
            
            # Try with userbot if bot API failed and userbot is available
            if not chat_info and hasattr(self.bot_controller, 'userbot') and self.bot_controller.userbot:
                try:
                    userbot = self.bot_controller.userbot
                    
                    if parsed_id["type"] == "id":
                        entity = await userbot.get_entity(parsed_id["value"])
                    elif parsed_id["type"] == "username":
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
            
            return chat_info
            
        except Exception as e:
            logger.error(f"Error getting channel info and testing permissions: {e}")
            return None
    
    async def _add_target_to_task(self, task_id: int, chat_info: dict) -> bool:
        """Add target to task in database"""
        try:
            await self.database.execute_command("""
                INSERT INTO targets (task_id, chat_id, chat_title, chat_type, username, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, task_id, chat_info["chat_id"], chat_info["chat_title"], 
                chat_info["chat_type"], chat_info.get("username"), True)
            
            return True
        except Exception as e:
            logger.error(f"Error adding target to database: {e}")
            return False
    
    def _format_targets_list(self, targets: List[dict]) -> str:
        """Format targets list for display"""
        targets_list = ""
        for i, target in enumerate(targets[:10], 1):  # Show max 10 targets
            status_emoji = "🟢" if target["is_active"] else "🔴"
            title = target.get("chat_title", f"ID: {target['chat_id']}")
            targets_list += f"{i}. {status_emoji} **{title[:25]}{'...' if len(title) > 25 else ''}**\n"
            targets_list += f"   🆔 `{target['chat_id']}`\n"
            if target.get("username"):
                targets_list += f"   📧 @{target['username']}\n"
            targets_list += "\n"
        
        if len(targets) > 10:
            targets_list += f"... and {len(targets) - 10} more targets\n"
        
        return targets_list
    
    async def _get_channel_info_and_test(self, parsed_id: Dict[str, Any], task_type: str) -> Optional[Dict[str, Any]]:
        """Get channel information and test permissions using both Bot API and Telethon userbot"""
        try:
            chat_id = parsed_id["value"]
            logger.info(f"Getting target channel info for {chat_id} using {task_type} mode")
            
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
                    logger.warning(f"Userbot failed for target {chat_id}: {userbot_error}")
                    # Fall back to Bot API
            
            # Try Bot API as fallback or primary method
            try:
                chat = await self.bot.get_chat(chat_id)
                
                # For bot API, also try to verify bot is member/admin for targets
                try:
                    bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
                    if bot_member.status not in ['administrator', 'member']:
                        logger.warning(f"Bot is not a member of target chat {chat_id}")
                        # Don't return None immediately, continue with basic info
                except Exception as e:
                    logger.warning(f"Cannot verify bot membership in target {chat_id}: {e}")
                    # Continue anyway, might be a public channel
                
                return {
                    "chat_id": chat.id,
                    "chat_title": chat.title or chat.first_name or "Unknown",
                    "chat_username": getattr(chat, 'username', None),
                    "chat_type": chat.type
                }
                
            except Exception as bot_error:
                logger.warning(f"Bot API failed for target {chat_id}: {bot_error}")
                
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
            logger.error(f"Error getting target channel info for {chat_id}: {e}")
            return None
    
    async def _add_target_to_task(self, task_id: int, chat_info: Dict[str, Any]) -> bool:
        """Add target to task"""
        try:
            query = """
                INSERT INTO targets (task_id, chat_id, chat_title, chat_username, chat_type, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, true, CURRENT_TIMESTAMP)
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
            logger.error(f"Error adding target to task: {e}")
            return False
    
    def _format_targets_list(self, targets: List[Dict]) -> str:
        """Format targets list for display"""
        if not targets:
            return "No targets configured."
        
        formatted = []
        for i, target in enumerate(targets[:10], 1):  # Limit to 10 targets
            status_emoji = "🟢" if target["is_active"] else "🔴"
            title = target["chat_title"] or f"ID: {target['chat_id']}"
            
            formatted.append(f"{i}. {status_emoji} {title[:30]}{'...' if len(title) > 30 else ''}")
        
        if len(targets) > 10:
            formatted.append(f"... and {len(targets) - 10} more")
        
        return "\n".join(formatted)
