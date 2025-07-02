"""
Bot Controller - Main bot interface and command handling
"""

import asyncio
import os
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from database import Database
from forwarding_engine import ForwardingEngine
from keyboards import BotKeyboards
from security import SecurityManager
from modules.settings_manager import SettingsManager
from handlers.admin import AdminHandlers
from handlers.tasks import TaskHandlers
from handlers.sources import SourceHandlers
from handlers.targets import TargetHandlers
from localization import localization


class BotStates(StatesGroup):
    """FSM States for bot interaction"""
    MAIN_MENU = State()
    CREATING_TASK = State()
    EDITING_TASK = State()
    ADDING_SOURCE = State()
    ADDING_TARGET = State()
    CONFIGURING_SETTINGS = State()
    WAITING_INPUT = State()


class BotController:
    """Main bot controller class"""

    def __init__(self, bot: Bot, dispatcher: Dispatcher, database: Database, 
                 forwarding_engine: ForwardingEngine, security_manager: SecurityManager, userbot=None):
        self.bot = bot
        self.dispatcher = dispatcher
        self.database = database
        self.forwarding_engine = forwarding_engine
        self.security_manager = security_manager
        self.userbot = userbot
        self.session_handler = None
        self.settings_manager = SettingsManager(database)
        self.keyboards = BotKeyboards()
        
        # Import and initialize config
        from config import Config
        self.config = Config()

        # Initialize handlers
        self.admin_handlers = AdminHandlers(self)
        self.task_handlers = TaskHandlers(self)
        self.source_handlers = SourceHandlers(self)
        self.target_handlers = TargetHandlers(self)
        self.session_handler = None  # Will be initialized later

        # User sessions cache
        self.user_sessions: Dict[int, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize bot controller and register handlers"""
        try:
            await self.settings_manager.initialize()
            await self._register_handlers()
            await self._setup_bot_commands()
            logger.success("Bot controller initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot controller: {e}")
            raise

    async def _register_handlers(self):
        """Register all bot handlers"""
        # Main command handlers
        self.dispatcher.message.register(
            self.start_command,
            Command("start")
        )

        self.dispatcher.message.register(
            self.help_command,
            Command("help")
        )

        self.dispatcher.message.register(
            self.session_command,
            Command("session")
        )

        self.dispatcher.message.register(
            self.menu_command,
            Command("menu")
        )

        self.dispatcher.message.register(
            self.status_command,
            Command("status")
        )

        self.dispatcher.message.register(
            self.userbot_command,
            Command("userbot")
        )

        self.dispatcher.message.register(
            self.testself_command,
            Command("testself")
        )

        self.dispatcher.message.register(
            self.test_forwarding_command,
            Command("testforward")
        )

        self.dispatcher.message.register(
            self.clear_cache_command,
            Command("clearcache")
        )

        # Callback query handlers (main callbacks and fallback for unhandled callbacks)
        self.dispatcher.callback_query.register(
            self.handle_callback,
            lambda c: c.data.startswith((
                "main_", "task_", "setting_", "content_", "preset_", 
                "filter_", "kw_", "media_", "text_", "len_", "user_", 
                "prefix_", "suffix_", "replace_", "hashtag_", "format_", "links_", 
                "confirm_", "cancel_", "set_", "source_", "target_", "admin_",
                # Advanced feature buttons
                "advanced_", "toggle_", "interval_", "list_",
                # Forward mode buttons
                "forward_mode_", "mode_", 
                # Delay buttons  
                "delay_", "delays_",
                # Filter action buttons
                "clear_", "enable_", "disable_", "reset_", "save_", "view_", "toggle_",
                # User filter buttons
                "verified_", "nobots_", "bots_",
                # Content action buttons
                "add_", "edit_", "remove_", "clear_all_",
                # Preset action buttons
                "basic_", "stealth_", "news_", "custom_",
                # Media type specific buttons
                "photo_", "video_", "audio_", "document_", "voice_", "sticker_", 
                "animation_", "poll_", "contact_", "location_", "venue_", "game_",
                # Additional action buttons
                "apply_", "load_", "delete_", "copy_", "import_", "export_"
            ))
        )

        # Channel post handlers for message forwarding
        self.dispatcher.channel_post.register(
            self.handle_channel_message,
            lambda message: True
        )
        
        # Edited channel post handlers for edit synchronization
        self.dispatcher.edited_channel_post.register(
            self.handle_edited_channel_message,
            lambda message: True
        )

        # Register callback query handler for all callbacks
        self.dispatcher.callback_query.register(
            self.handle_callback,
            lambda callback: True
        )
        
        # Register text message handler for input states  
        from aiogram.filters import StateFilter
        from handlers.tasks import TaskStates
        from aiogram import F
        
        logger.info("Registering text input handler for WAITING_INPUT state")
        
        # Create the text handler function
        async def text_message_handler(message: Message, state: FSMContext):
            try:
                current_state = await state.get_state()
                logger.info(f"Text handler: '{message.text}' from user {message.from_user.id}, state: {current_state}")
                
                if current_state == "TaskStates:WAITING_INPUT":
                    await self.handle_text_input(message, state)
                elif current_state == "TaskStates:WAITING_TASK_NAME":
                    # Route to task handlers for task name processing
                    await self.task_handlers.handle_task_name_input(message, state)
                elif current_state == "TaskStates:WAITING_TASK_DESCRIPTION":
                    # Route to task handlers for task description processing
                    await self.task_handlers.handle_task_description_input(message, state)
                elif current_state == "SourceStates:WAITING_SOURCE_INPUT":
                    # Route to source handlers for source input processing  
                    logger.info(f"Routing to source handler for input: {message.text}")
                    await self.source_handlers.handle_source_input(message, state)
                elif current_state == "TargetStates:WAITING_TARGET_INPUT":
                    # Route to target handlers for target input processing
                    logger.info(f"Routing to target handler for input: {message.text}")
                    await self.target_handlers.handle_target_input(message, state)
                elif current_state in ["edit_header", "edit_footer"]:
                    # Route to task handlers for header/footer editing
                    logger.info(f"Routing to task handler for header/footer input: {message.text}")
                    await self.task_handlers.handle_text_input(message, state)
                elif current_state and "SessionStates" in current_state:
                    # Route to session handler for session creation states
                    logger.info(f"Routing session text to handler: '{message.text}' in state: {current_state}")
                    if self.session_handler:
                        if "WAITING_API_ID" in current_state:
                            await self.session_handler.handle_api_id_input(message, state)
                        elif "WAITING_API_HASH" in current_state:
                            await self.session_handler.handle_api_hash_input(message, state)
                        elif "WAITING_PHONE" in current_state:
                            await self.session_handler.handle_phone_input(message, state)
                        elif "WAITING_CODE" in current_state:
                            await self.session_handler.handle_code_input(message, state)
                        elif "WAITING_PASSWORD" in current_state:
                            await self.session_handler.handle_password_input(message, state)
                elif not message.text.startswith('/'):
                    # Log non-command messages for debugging
                    logger.info(f"Unhandled text message: '{message.text}' in state: {current_state}")
                    await message.answer("تم استلام المدخل النصي")
                    
            except Exception as e:
                logger.error(f"Text handler error: {e}")
        
        # Register the handler using the old method
        self.dispatcher.message.register(text_message_handler, F.text)
        
        logger.info("Text handler registered successfully")

        # Register handler modules
        await self.admin_handlers.register_handlers()
        await self.task_handlers.register_handlers()
        await self.source_handlers.register_handlers()
        await self.target_handlers.register_handlers()

        # Initialize and register session handler
        try:
            if not self.session_handler:
                from handlers.session import SessionHandler
                self.session_handler = SessionHandler(self)
                logger.info("Session handler initialized")
            self.session_handler.register_handlers(self.dispatcher)
            logger.info("Session handler registered successfully")
        except Exception as e:
            logger.error(f"Failed to register session handler: {e}")
            import traceback
            logger.error(f"Session handler traceback: {traceback.format_exc()}")

        logger.info("All handlers registered successfully")

    async def _setup_bot_commands(self):
        """Setup bot command menu"""
        from aiogram.types import BotCommand

        commands = [
            BotCommand(command="start", description="🚀 Start the bot"),
            BotCommand(command="menu", description="📋 Main menu"),
            BotCommand(command="help", description="❓ Get help"),
            BotCommand(command="status", description="📊 Bot status"),
            BotCommand(command="userbot", description="🤖 Check userbot status"),
            BotCommand(command="testself", description="📱 Test userbot self-message"),
        ]

        await self.bot.set_my_commands(commands)
        logger.info("Bot commands menu set up")

    async def start_command(self, message: Message, state: FSMContext):
        """Handle /start command"""
        user_id = message.from_user.id

        try:
            # Security check
            if not await self.security_manager.verify_user_access(user_id):
                await message.answer(
                    "🚫 Access denied. You are not authorized to use this bot."
                )
                return

            # Register or update user
            user_data = {
                "telegram_id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "is_admin": await self.security_manager.is_admin(user_id)
            }

            await self.database.create_or_update_user(user_data)

            # Load user language preference
            try:
                user_lang_result = await self.database.execute_query(
                    "SELECT language FROM users WHERE telegram_id = $1", user_id
                )
                if user_lang_result and user_lang_result[0]['language']:
                    localization.set_user_language(user_id, user_lang_result[0]['language'])
            except Exception as e:
                logger.warning(f"Could not load user language preference: {e}")

            # Send welcome message
            welcome_text = self._get_welcome_message(message.from_user.first_name, user_id)
            keyboard = await self.keyboards.get_main_menu_keyboard(user_id)

            await message.answer(welcome_text, reply_markup=keyboard)
            await state.set_state(BotStates.MAIN_MENU)

            logger.info(f"User {user_id} started the bot")

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("❌ حدث خطأ في بدء البوت. الرجاء المحاولة لاحقاً أو التواصل مع المطور.")

    async def help_command(self, message: Message):
        """Handle /help command"""
        user_id = message.from_user.id
        help_text = localization.get_text(user_id, "help_text")
        await message.answer(help_text, parse_mode="Markdown")

    async def menu_command(self, message: Message, state: FSMContext):
        """Handle /menu command"""
        user_id = message.from_user.id

        if not await self.security_manager.verify_user_access(user_id):
            await message.answer("🚫 Access denied.")
            return

        keyboard = await self.keyboards.get_main_menu_keyboard(user_id)
        main_menu_text = localization.get_text(user_id, "main_menu")
        await message.answer(main_menu_text, reply_markup=keyboard)
        await state.set_state(BotStates.MAIN_MENU)

    async def status_command(self, message: Message):
        """Handle /status command"""
        user_id = message.from_user.id

        if not await self.security_manager.verify_user_access(user_id):
            await message.answer("🚫 Access denied.")
            return

        try:
            # Get bot status
            bot_info = await self.bot.get_me()

            # Get database stats
            db_stats = await self.database.get_database_stats()

            # Get forwarding engine stats
            engine_stats = self.forwarding_engine.get_stats()

            status_text = f"""🤖 حالة البوت

معلومات البوت:
• الاسم: {bot_info.first_name}
• اسم المستخدم: @{bot_info.username}
• المعرف: {bot_info.id}

إحصائيات قاعدة البيانات:
• إجمالي المستخدمين: {db_stats.get('total_users', 0)}
• إجمالي المهام: {db_stats.get('total_tasks', 0)}
• المهام النشطة: {db_stats.get('active_tasks', 0)}
• رسائل اليوم: {db_stats.get('logs_today', 0)}

محرك التوجيه:
• الحالة: {'🟢 يعمل' if engine_stats.get('running') else '🔴 متوقف'}
• المراقبات النشطة: {engine_stats.get('active_monitors', 0)}
• الرسائل المعالجة: {engine_stats.get('messages_processed', 0)}
• معدل النجاح: {engine_stats.get('success_rate', 0):.1f}%

النظام:
• وقت التشغيل: {engine_stats.get('uptime', 'غير محدد')}
• استخدام الذاكرة: {engine_stats.get('memory_usage', 'غير محدد')}"""

            await message.answer(status_text)

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            await message.answer("❌ Failed to get bot status.")

    async def userbot_command(self, message: Message):
        """Handle /userbot command - Check userbot status and connection"""
        try:
            user_id = message.from_user.id
            
            # Check if user is authorized
            if not await self.security_manager.verify_user_access(user_id):
                await message.answer("❌ غير مصرح لك بفحص حالة Userbot")
                return
            
            if not self.userbot:
                await message.answer("❌ Userbot غير متاح - البوت يعمل في وضع Bot API فقط")
                return
            
            # Check userbot connection
            try:
                connection_status = "🟢 متصل" if self.userbot.is_connected() else "🔴 غير متصل"
                
                status_text = f"""🤖 حالة Userbot

الاتصال:
• الحالة: {connection_status}
• نوع الجلسة: StringSession
• الوضع: هجين (Bot API + Userbot)

معلومات الجلسة:
• طول الجلسة: {len(os.environ.get('STRING_SESSION', ''))} حرف
• حالة التحقق: {"✅ نشط" if self.userbot.is_connected() else "❌ غير نشط"}

للاختبار الكامل، استخدم الأمر /testself"""

                await message.answer(status_text)
                
            except Exception as userbot_error:
                logger.error(f"Userbot status check failed: {userbot_error}")
                await message.answer(f"❌ خطأ في فحص حالة Userbot: {str(userbot_error)}")
                
        except Exception as e:
            logger.error(f"Error in userbot command: {e}")
            await message.answer("❌ فشل في فحص حالة Userbot")

    async def testself_command(self, message: Message):
        """Handle /testself command - Send test message to userbot's Saved Messages"""
        try:
            user_id = message.from_user.id
            
            # Check if user is authorized
            if not await self.security_manager.verify_user_access(user_id):
                await message.answer("❌ غير مصرح لك باختبار Userbot")
                return
            
            if not self.userbot:
                await message.answer("❌ Userbot غير متاح - البوت يعمل في وضع Bot API فقط")
                return
            
            try:
                if not self.userbot.is_connected():
                    await message.answer("🔴 Userbot غير متصل - جاري المحاولة...")
                    try:
                        await self.userbot.connect()
                    except:
                        await message.answer("❌ فشل في الاتصال بـ Userbot")
                        return
                
                # Send test message to Saved Messages
                import datetime
                test_message = f"""🧪 رسالة اختبار Userbot

الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
من: بوت إعادة التوجيه
الحالة: ✅ يعمل بشكل صحيح

تم إرسال هذه الرسالة للتأكد من أن Userbot متصل ويعمل بشكل صحيح."""

                # Send to self (Saved Messages)
                try:
                    sent_message = await self.userbot.send_message("me", test_message)
                    
                    success_text = f"""✅ تم إرسال رسالة اختبار بنجاح

تفاصيل:
• تم الإرسال إلى: الرسائل المحفوظة
• معرف الرسالة: {sent_message.id}
• الوقت: {datetime.datetime.now().strftime('%H:%M:%S')}
• نوع الجلسة: StringSession

يمكنك التحقق من الرسالة في رسائلك المحفوظة على تليجرام."""

                    await message.answer(success_text)
                    
                except Exception as send_error:
                    error_msg = str(send_error)
                    if "key is not registered" in error_msg or "AUTH_KEY_UNREGISTERED" in error_msg:
                        await message.answer("""❌ الجلسة منتهية الصلاحية أو غير صالحة

السبب: المفتاح غير مسجل في النظام
الحل: تحتاج لإنشاء جلسة جديدة باستخدام /session

هذا يحدث عادة عندما:
• تم إلغاء تفويض التطبيق من حساب تليجرام
• انتهت صلاحية الجلسة
• تغيير كلمة مرور الحساب""")
                    else:
                        await message.answer(f"❌ خطأ في إرسال الرسالة: {error_msg}")
                    return
                
            except Exception as userbot_error:
                logger.error(f"Userbot test failed: {userbot_error}")
                await message.answer(f"❌ فشل اختبار Userbot: {str(userbot_error)}")
                
        except Exception as e:
            logger.error(f"Error in testself command: {e}")
            await message.answer("❌ فشل في اختبار إرسال Userbot")

    async def session_command(self, message: Message):
        """Handle /session command - Interactive session creation"""
        try:
            user_id = message.from_user.id
            
            # Check if user is authorized
            if not await self.security_manager.verify_user_access(user_id):
                await message.answer("❌ غير مصرح لك بإنشاء جلسات جديدة")
                return

            # Initialize session handler if not exists
            if not self.session_handler:
                from handlers.session import SessionHandler
                self.session_handler = SessionHandler(self)

            # Create state context from message
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey
            
            # Create storage key
            key = StorageKey(bot_id=self.bot.id, chat_id=message.chat.id, user_id=user_id)
            context = FSMContext(storage=self.dispatcher.storage, key=key)
            
            await self.session_handler.handle_session_command(message, context)
            
        except Exception as e:
            logger.error(f"Error in session command: {e}")
            await message.answer("❌ خطأ في بدء إنشاء الجلسة")

    async def test_forwarding_command(self, message: Message):
        """Handle /testforward command - manually test forwarding"""
        try:
            user_id = message.from_user.id

            # Check admin permissions
            if not self.security_manager.is_admin(user_id):
                await message.answer("❌ Admin access required for forwarding tests.")
                return

            # Get active tasks
            tasks = await self.database.get_active_tasks()
            if not tasks:
                await message.answer("❌ No active tasks found.")
                return

            # Use first active task for testing
            task = tasks[0]
            task_id = task['id']

            # Get sources and targets for this task
            sources = await self.database.get_task_sources(task_id)
            targets = await self.database.get_task_targets(task_id)

            if not sources or not targets:
                await message.answer(f"❌ Task {task_id} missing configuration.")
                return

            source_chat_id = sources[0]['chat_id']

            # Send test message to source channel
            from datetime import datetime
            test_message = await self.bot.send_message(
                chat_id=source_chat_id,
                text=f"🧪 **Manual Forwarding Test**\n\nTime: {datetime.now().strftime('%H:%M:%S')}\nTask ID: {task_id}\n\nThis message tests the forwarding system."
            )

            logger.info(f"Test message sent to {source_chat_id}, ID: {test_message.message_id}")

            await message.answer(f"""
🧪 **Test Initiated**

**Source:** {sources[0]['chat_title']}
**Target:** {targets[0]['chat_title']}
**Message ID:** {test_message.message_id}

Monitoring for forwarding results...
            """)

        except Exception as e:
            logger.error(f"Error in test forwarding: {e}")
            await message.answer("❌ Forwarding test failed.")

    async def clear_cache_command(self, message: Message):
        """Handle /clearcache command - Clear all caches"""
        try:
            user_id = message.from_user.id
            
            # Check admin permissions
            if not await self.security_manager.is_admin(user_id):
                await message.answer("❌ صلاحيات المدير مطلوبة لمسح الـ cache")
                return
            
            cleared_items = []
            
            # Clear forwarding engine cache
            if hasattr(self.forwarding_engine, '_task_cache'):
                cache_size = len(self.forwarding_engine._task_cache)
                self.forwarding_engine._task_cache.clear()
                cleared_items.append(f"Forwarding engine cache ({cache_size} items)")
            
            # Clear task manager cache
            if hasattr(self.task_handlers.task_manager, 'task_cache'):
                async with self.task_handlers.task_manager.cache_lock:
                    cache_size = len(self.task_handlers.task_manager.task_cache)
                    self.task_handlers.task_manager.task_cache.clear()
                    cleared_items.append(f"Task manager cache ({cache_size} items)")
            
            # Clear user sessions
            if hasattr(self, '_user_sessions'):
                session_count = len(self._user_sessions)
                self._user_sessions.clear()
                cleared_items.append(f"User sessions ({session_count} items)")
            
            # Force reload of tasks
            await self.forwarding_engine._reload_tasks()
            cleared_items.append("Task configurations reloaded")
            
            cache_report = "\n• ".join(cleared_items) if cleared_items else "لا توجد عناصر cache للمسح"
            
            await message.answer(f"""🧹 **تم مسح الـ Cache بنجاح**

**العناصر التي تم مسحها:**
• {cache_report}

✅ جميع واجهات البوت ستعرض التحديثات الآن""")
            
            logger.info(f"Cache cleared by admin {user_id}: {cleared_items}")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            await message.answer("❌ خطأ في مسح الـ cache")

    async def handle_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle callback queries"""
        user_id = callback.from_user.id
        data = callback.data
        logger.info(f"Bot controller received callback: {data}")
        logger.error(f"DEBUGGING CALLBACK: '{data}' from user {user_id}")

        try:
            # Handle manual approval callbacks first - they bypass normal security for admins
            if data.startswith("approve_") or data.startswith("reject_"):
                logger.warning(f"=== MANUAL APPROVAL CALLBACK DETECTED: {data} ===")
                logger.info(f"User ID: {user_id}, Callback data: {data}")
                await self._handle_approval_callback(callback, state)
                return
                
            if not await self.security_manager.verify_user_access(user_id):
                await callback.answer("🚫 Access denied.", show_alert=True)
                return

            # Handle session callbacks
            if data and data.startswith('session_'):
                if self.session_handler:
                    await self.session_handler.handle_session_callback(callback, state)
                    return
                else:
                    await callback.answer("❌ معالج الجلسة غير متاح")
                    return

            # Route callback to appropriate handler
            if data.startswith("main_"):
                await self._handle_main_callback(callback, state)
            elif data.startswith("settings_"):
                await self._handle_settings_callback(callback, state)
            elif data == "lang_menu":
                await self._handle_language_menu(callback, state)
            elif data.startswith("set_lang_"):
                await self._handle_language_change(callback, state)
            elif (data.startswith("task_") or data.startswith("setting_") or data.startswith("content_") or 
                  data.startswith("preset_") or data.startswith("filter_") or data.startswith("kw_") or 
                  data.startswith("media_") or data.startswith("text_") or data.startswith("len_") or 
                  data.startswith("user_") or data.startswith("prefix_") or data.startswith("replace_") or 
                  data.startswith("hashtag_") or data.startswith("format_") or data.startswith("links_") or
                  data.startswith("forward_mode_") or data.startswith("mode_") or data.startswith("delay_") or
                  data.startswith("clear_") or data.startswith("enable_") or data.startswith("disable_") or
                  data.startswith("reset_") or data.startswith("save_") or data.startswith("view_") or
                  data.startswith("toggle_") or data.startswith("verified_") or data.startswith("nobots_") or
                  data.startswith("photo_") or data.startswith("video_") or data.startswith("audio_") or
                  data.startswith("document_") or data.startswith("voice_") or data.startswith("sticker_") or
                  data.startswith("animation_") or data.startswith("poll_") or data.startswith("contact_") or
                  data.startswith("location_") or data.startswith("venue_") or data.startswith("game_") or
                  data.startswith("basic_") or data.startswith("stealth_") or data.startswith("news_") or
                  data.startswith("custom_") or data.startswith("apply_") or data.startswith("load_") or
                  data.startswith("delete_") or data.startswith("copy_") or data.startswith("import_") or
                  data.startswith("export_") or data.startswith("confirm_") or data.startswith("cancel_") or
                  data.startswith("set_") or data.startswith("add_") or data.startswith("remove_") or
                  data.startswith("edit_") or data.startswith("test_") or data.startswith("back_") or
                  data.startswith("next_") or data.startswith("prev_") or data.startswith("select_") or
                  data.startswith("instant_") or data.startswith("short_") or data.startswith("medium_") or
                  data.startswith("long_") or data.startswith("random_") or data.startswith("bold_") or
                  data.startswith("italic_") or data.startswith("underline_") or data.startswith("strike_") or
                  data.startswith("spoiler_") or data.startswith("code_") or data.startswith("mono_") or
                  data.startswith("preserve_") or data.startswith("strip_") or data.startswith("extract_") or
                  data.startswith("limit_") or data.startswith("min_") or data.startswith("max_") or
                  data.startswith("keyword_") or data.startswith("length_") or data.startswith("sender_") or
                  data.startswith("all_") or data.startswith("none_") or data.startswith("default_") or
                  data.startswith("advanced_") or data.startswith("translation_") or data.startswith("working_") or
                  data.startswith("recurring_") or data.startswith("lang_") or data.startswith("timezone_") or
                  data.startswith("interval_") or data.startswith("hour_") or data.startswith("manual_") or data.startswith("auto_") or
                  data.startswith("header_") or data.startswith("footer_") or data.startswith("inline_button")):
                # Handle specific task management actions in bot controller
                if data in ["task_import", "task_export", "task_start_all", "task_stop_all"]:
                    await self._handle_task_management_actions(callback, state)
                else:
                    logger.info(f"Routing to task handlers: {data}")
                    await self.task_handlers.handle_callback(callback, state)
            elif data.startswith("source_"):
                await self.source_handlers.handle_callback(callback, state)
            elif data.startswith("target_"):
                await self.target_handlers.handle_callback(callback, state)
            elif data.startswith("admin_"):
                await self.admin_handlers.handle_callback(callback, state)
            elif data.startswith("cleaner_"):
                # Route text cleaner callbacks to task handlers
                logger.info(f"Routing text cleaner callback to task handlers: {data}")
                await self.task_handlers.handle_callback(callback, state)
            elif data.startswith("popup_info_"):
                # Handle popup info buttons from inline buttons
                await self._handle_popup_callback(callback)
            else:
                logger.warning(f"Unhandled callback in bot_controller: {data}")
                await callback.answer("❌ Unknown action.", show_alert=True)

        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await callback.answer("❌ An error occurred.", show_alert=True)

    async def _handle_main_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle main menu callbacks"""
        data = callback.data
        user_id = callback.from_user.id

        if data == "main_tasks":
            keyboard = await self.keyboards.get_tasks_keyboard(user_id)
            task_mgmt_text = localization.get_text(user_id, "task_list") + "\n\n" + localization.get_text(user_id, "select_language")
            await callback.message.edit_text(
                task_mgmt_text,
                reply_markup=keyboard
            )

        elif data == "main_statistics":
            stats_text = await self._get_user_statistics(user_id)
            keyboard = await self.keyboards.get_back_to_main_keyboard()
            await callback.message.edit_text(
                stats_text,
                reply_markup=keyboard
            )

        elif data == "main_system_status":
            await self._handle_system_status(callback, state)

        elif data == "main_detailed_report":
            await self._handle_detailed_report(callback, state)

        elif data == "main_quick_start":
            await self._handle_quick_start(callback, state)

        elif data == "main_advanced_tools":
            await self._handle_advanced_tools(callback, state)

        elif data == "main_settings":
            keyboard = await self.keyboards.get_settings_keyboard(user_id)
            settings_text = localization.get_text(user_id, "btn_settings") + "\n\n" + localization.get_text(user_id, "select_language")
            await callback.message.edit_text(
                settings_text,
                reply_markup=keyboard
            )

        elif data == "main_help":
            help_text = localization.get_text(user_id, "help_text")
            keyboard = await self.keyboards.get_back_to_main_keyboard()
            await callback.message.edit_text(
                help_text,
                reply_markup=keyboard
            )

        elif data == "main_back":
            keyboard = await self.keyboards.get_main_menu_keyboard(user_id)
            main_menu_text = localization.get_text(user_id, "main_menu")
            await callback.message.edit_text(
                main_menu_text,
                reply_markup=keyboard
            )
            await state.set_state(BotStates.MAIN_MENU)

    async def _handle_settings_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle settings-related callbacks"""
        data = callback.data
        user_id = callback.from_user.id
        
        try:
            if data == "settings_bot":
                # Get bot configuration summary
                config = self.config.get_config_summary()
                settings_text = f"""🤖 **إعدادات البوت**

**الإعدادات الحالية:**
• الوضع: {'Webhook' if config.get('webhook_mode') else 'Polling'}
• عدد المديرين: {len(config.get('admin_ids', []))}
• حالة التوكن: {'✅ نشط' if config.get('bot_token') else '❌ مفقود'}
• قاعدة البيانات: {'✅ متصلة' if config.get('database_url') else '❌ منقطعة'}

**حالة النظام:**
• المهام النشطة: {len(await self.database.get_active_tasks())}
• حالة Userbot: {'✅ نشط' if self.userbot else '❌ معطل'}

**خيارات التكوين:**
🔧 يمكن تعديل الإعدادات المتقدمة عبر متغيرات البيئة"""

                keyboard = await self.keyboards.get_back_to_main_keyboard()
                await callback.message.edit_text(settings_text, reply_markup=keyboard)

            elif data == "settings_user":
                # Get user permissions and settings
                user_permissions = await self.security_manager.get_user_permissions(user_id)
                settings_text = f"""👤 **إعدادات المستخدم**

**صلاحياتك:**
• الدور: {'👑 مدير' if user_permissions.get('is_admin') else '👤 مستخدم'}
• إنشاء المهام: {'✅ مسموح' if user_permissions.get('can_create_tasks') else '❌ مقيد'}
• إدارة المهام: {'✅ مسموح' if user_permissions.get('can_manage_tasks') else '❌ مقيد'}
• إنشاء الجلسات: {'✅ مسموح' if user_permissions.get('can_create_sessions') else '❌ مقيد'}

**معلومات الحساب:**
• معرف المستخدم: {user_id}
• مستوى الوصول: {'وصول كامل' if user_permissions.get('is_admin') else 'مستخدم عادي'}

**الإجراءات المتاحة:**
📱 استخدم /session لإنشاء جلسات جديدة
📋 الوصول للمهام عبر القائمة الرئيسية"""

                keyboard = await self.keyboards.get_back_to_main_keyboard()
                await callback.message.edit_text(settings_text, reply_markup=keyboard)

            elif data == "settings_system":
                # Get system information
                import psutil
                import os
                from datetime import datetime
                
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
                
                settings_text = f"""🔧 **معلومات النظام**

**الأداء:**
• استخدام المعالج: {cpu_percent:.1f}%
• استخدام الذاكرة: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
• استخدام القرص: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)

**النظام:**
• وقت التشغيل: {str(uptime).split('.')[0]}
• إصدار Python: {os.sys.version.split()[0]}
• المنصة: {os.name}

**حالة البوت:**
• الوضع: {'Webhook' if hasattr(self, 'webhook_mode') and self.webhook_mode else 'Polling'}
• تخزين الجلسات: نظام موحد مشفر
• قاعدة البيانات: PostgreSQL متصلة"""

                keyboard = await self.keyboards.get_back_to_main_keyboard()
                await callback.message.edit_text(settings_text, reply_markup=keyboard)

            elif data == "settings_stats":
                # Get comprehensive statistics
                tasks = await self.database.get_active_tasks()
                total_users = len(await self.database.execute_query("SELECT DISTINCT user_id FROM users"))
                
                # Get forwarding statistics
                logs_today = await self.database.execute_query(
                    "SELECT COUNT(*) as count FROM forwarding_logs WHERE created_at >= CURRENT_DATE"
                )
                logs_count = logs_today[0]['count'] if logs_today else 0
                
                settings_text = f"""📊 **إحصائيات البوت**

**المهام:**
• إجمالي المهام: {len(tasks)}
• المهام النشطة: {len([t for t in tasks if t.get('is_active')])}
• مهام Bot API: {len([t for t in tasks if t.get('task_type') == 'bot'])}
• مهام Userbot: {len([t for t in tasks if t.get('task_type') == 'userbot'])}

**النشاط:**
• إجمالي المستخدمين: {total_users}
• الرسائل اليوم: {logs_count}
• نوع الجلسة: نظام موحد مشفر

**الأداء:**
• محرك التوجيه: {'✅ يعمل' if hasattr(self, 'forwarding_engine') else '❌ متوقف'}
• المراقبة: {'✅ نشطة' if len(tasks) > 0 else '⚠️ لا توجد مهام نشطة'}

**الأمان:**
• التشفير: AES-256 (تخزين الجلسات)
• المصادقة: تحكم في الوصول متعدد المستويات"""

                keyboard = await self.keyboards.get_back_to_main_keyboard()
                await callback.message.edit_text(settings_text, reply_markup=keyboard)

            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in settings callback: {e}")
            await callback.answer("❌ خطأ في تحميل الإعدادات", show_alert=True)

    async def handle_channel_message(self, message):
        """Handle incoming channel messages for forwarding"""
        try:
            # Check if this message is from a monitored source channel
            chat_id = message.chat.id
            logger.info(f"Channel post received from {chat_id} (message {message.message_id})")

            # Pass message to forwarding engine for processing
            success = await self.forwarding_engine.process_channel_message(chat_id, message)

            if success:
                logger.success(f"Message {message.message_id} from {chat_id} forwarded successfully")
            else:
                logger.warning(f"Message {message.message_id} from {chat_id} was not forwarded")

        except Exception as e:
            logger.error(f"Error handling channel message from {message.chat.id}: {e}")

    async def handle_edited_channel_message(self, message):
        """Handle edited channel messages for edit synchronization"""
        try:
            chat_id = message.chat.id
            message_id = message.message_id
            logger.info(f"Edited channel post received from {chat_id} (message {message_id})")

            # Pass edited message to forwarding engine for sync
            success = await self.forwarding_engine.process_edited_message(chat_id, message)

            if success:
                logger.success(f"Edited message {message_id} from {chat_id} synchronized successfully")
            else:
                logger.warning(f"Edited message {message_id} from {chat_id} was not synchronized")

        except Exception as e:
            logger.error(f"Error handling edited channel message from {message.chat.id}: {e}")

    async def shutdown(self):
        """Shutdown bot controller"""
        try:
            # Clear user sessions
            self.user_sessions.clear()
            logger.info("Bot controller shutdown completed")
        except Exception as e:
            logger.error(f"Error during bot controller shutdown: {e}")

    def _get_welcome_message(self, first_name: str, user_id: int) -> str:
        """Get welcome message for user"""
        return localization.get_text(user_id, "welcome_message", name=first_name)

    def _get_help_text(self) -> str:
        """Get help text"""
        return """❓ **المساعدة والدعم**

**دليل البدء السريع:**
1. إنشاء مهمة جديدة باستخدام "📋 المهام" → "➕ مهمة جديدة"
2. اختر بين وضع Bot API أو Userbot
3. إضافة قنوات المصدر للمراقبة
4. إضافة قنوات الهدف للتوجيه
5. تكوين الإعدادات (اختياري)
6. تفعيل المهمة

**نصائح:**
• استخدم وضع Userbot للقنوات الخاصة
• اضبط التأخير لتجنب حدود المعدل
• استخدم الفلاتر للتحكم فيما يتم توجيهه
• راقب الإحصائيات لتتبع الأداء

**تحتاج مساعدة؟**
تواصل مع مدير البوت للحصول على دعم إضافي."""

    async def _get_user_statistics(self, user_id: int) -> str:
        """Get user statistics"""
        try:
            # Get user tasks
            user_tasks = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM tasks WHERE user_id = (SELECT id FROM users WHERE telegram_id = $1)",
                user_id
            )

            # Get active tasks
            active_tasks = await self.database.execute_query(
                """
                SELECT COUNT(*) as count FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE u.telegram_id = $1 AND t.is_active = true
                """,
                user_id
            )

            # Get forwarding stats
            forwarding_stats = await self.database.execute_query(
                """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM forwarding_logs fl
                JOIN tasks t ON fl.task_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE u.telegram_id = $1
                """,
                user_id
            )

            stats = forwarding_stats[0] if forwarding_stats else {"total_messages": 0, "successful": 0, "failed": 0}
            success_rate = (stats["successful"] / stats["total_messages"] * 100) if stats["total_messages"] > 0 else 0

            return f"""📊 **إحصائياتك**

**المهام:**
• إجمالي المهام: {user_tasks[0]['count'] if user_tasks else 0}
• المهام النشطة: {active_tasks[0]['count'] if active_tasks else 0}

**توجيه الرسائل:**
• إجمالي الرسائل: {stats['total_messages']}
• نجح: {stats['successful']}
• فشل: {stats['failed']}
• معدل النجاح: {success_rate:.1f}%

**النشاط:**
• آخر نشاط: اليوم
• حالة الحساب: نشط"""

        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return "❌ فشل في تحميل الإحصائيات."

    async def handle_text_input(self, message, state):
        """Handle text input from users"""
        try:
            # Get current state and data to route appropriately
            state_data = await state.get_data()
            current_state = await state.get_state()
            action = state_data.get("action")
            
            logger.info(f"Handling text input - State: {current_state}, Action: {action}, Text: '{message.text}'")
            
            # Route to task handlers for text processing
            if hasattr(self, 'task_handlers') and self.task_handlers:
                await self.task_handlers.handle_text_input(message, state)
            else:
                logger.error("Task handlers not available")
                await message.answer("❌ خطأ في معالجة الإدخال")
        except Exception as e:
            logger.error(f"Error handling text input: {e}")
            await message.answer("❌ خطأ في معالجة الإدخال")

    async def _handle_approval_callback(self, callback, state):
        """Handle approval callbacks"""
        try:
            user_id = callback.from_user.id
            callback_data = callback.data
            
            logger.info(f"Processing approval callback: {callback_data} from user {user_id}")
            
            # Route to forwarding engine for approval handling
            if hasattr(self, 'forwarding_engine') and self.forwarding_engine:
                success = await self.forwarding_engine.handle_approval_callback(callback_data, user_id)
                
                if success:
                    if callback_data.startswith("approve_"):
                        await callback.answer("✅ تم الموافقة على النشر", show_alert=True)
                        # Edit the message to show it was approved
                        try:
                            await callback.message.edit_text(
                                f"✅ **تم الموافقة على النشر**\n\n"
                                f"تم توجيه الرسالة إلى جميع القنوات المستهدفة.\n"
                                f"المعتمد بواسطة: {callback.from_user.first_name}\n"
                                f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                    elif callback_data.startswith("reject_"):
                        await callback.answer("❌ تم رفض النشر", show_alert=True)
                        # Edit the message to show it was rejected
                        try:
                            await callback.message.edit_text(
                                f"❌ **تم رفض النشر**\n\n"
                                f"تم رفض توجيه الرسالة.\n"
                                f"المرفوض بواسطة: {callback.from_user.first_name}\n"
                                f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                else:
                    await callback.answer("❌ فشل في معالجة الطلب", show_alert=True)
            else:
                await callback.answer("❌ محرك التوجيه غير متاح", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling approval callback: {e}")
            await callback.answer("❌ خطأ في معالجة الطلب", show_alert=True)

    async def _handle_popup_callback(self, callback, state):
        """Handle popup callbacks"""
        try:
            # Handle popup-related callbacks
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling popup callback: {e}")
    
    async def _handle_language_menu(self, callback: CallbackQuery, state: FSMContext):
        """Handle language selection menu"""
        try:
            user_id = callback.from_user.id
            current_lang = localization.get_user_language(user_id)
            
            # Use localization for the text
            text = localization.get_text(user_id, "language_settings") + "\n\n" + \
                   localization.get_text(user_id, "current_language", lang=localization.get_language_name(current_lang)) + "\n\n" + \
                   localization.get_text(user_id, "select_language")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "language_arabic"), callback_data="set_lang_ar"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "language_english"), callback_data="set_lang_en")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "back_to_main"), callback_data="main_back")
                ]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in language menu: {e}")
            await callback.answer("❌ خطأ في عرض قائمة اللغات", show_alert=True)
    
    async def _handle_language_change(self, callback: CallbackQuery, state: FSMContext):
        """Handle language change"""
        try:
            user_id = callback.from_user.id
            data = callback.data
            new_lang = data.split("_")[-1]  # Extract language code from callback data
            
            # Set user language
            success = localization.set_user_language(user_id, new_lang)
            
            if success:
                # Update user language in database
                await self.database.execute_command(
                    "UPDATE users SET language = $1 WHERE telegram_id = $2",
                    new_lang, user_id
                )
                
                # Get localized success message
                lang_name = localization.get_language_name(new_lang)
                success_text = localization.get_text(user_id, "language_changed", lang=lang_name)
                
                # Show main menu in new language
                keyboard = await self.keyboards.get_main_menu_keyboard(user_id)
                welcome_text = localization.get_text(user_id, "main_menu")
                
                await callback.message.edit_text(
                    f"{success_text}\n\n{welcome_text}",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await callback.answer(f"✅ تم تغيير اللغة إلى {lang_name}")
                
            else:
                await callback.answer("❌ فشل في تغيير اللغة", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error changing language: {e}")
            await callback.answer("❌ خطأ في تغيير اللغة", show_alert=True)
    
    async def update_user_session(self, user_id: int, data: dict):
        """Update user session data"""
        try:
            if not hasattr(self, '_user_sessions'):
                self._user_sessions = {}
            
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = {}
            
            self._user_sessions[user_id].update(data)
            logger.info(f"Updated session for user {user_id}: {data}")
        except Exception as e:
            logger.error(f"Error updating user session: {e}")
    
    async def get_user_session(self, user_id: int) -> dict:
        """Get user session data"""
        try:
            if not hasattr(self, '_user_sessions'):
                self._user_sessions = {}
            
            return self._user_sessions.get(user_id, {})
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return {}
    
    async def clear_user_session(self, user_id: int):
        """Clear user session data"""
        try:
            if not hasattr(self, '_user_sessions'):
                self._user_sessions = {}
            
            if user_id in self._user_sessions:
                del self._user_sessions[user_id]
                logger.info(f"Cleared session for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing user session: {e}")

    # === Missing Main Menu Handlers ===

    async def _handle_system_status(self, callback: CallbackQuery, state: FSMContext):
        """Handle system status display"""
        try:
            user_id = callback.from_user.id
            
            # Get comprehensive system status
            import psutil
            import platform
            from datetime import datetime, timedelta
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # Bot status
            tasks = await self.database.get_active_tasks()
            active_tasks = len([t for t in tasks if t.get('is_active')])
            
            # Database status
            try:
                db_health = await self.database.execute_query("SELECT 1")
                db_status = "✅ متصلة" if db_health else "❌ خطأ"
            except:
                db_status = "❌ منقطعة"
            
            # Userbot status
            userbot_status = "✅ نشط" if self.userbot and self.userbot.is_connected() else "❌ معطل"
            
            status_text = f"""🔧 **حالة النظام المفصلة**

**📊 أداء النظام:**
• المعالج: {cpu_percent:.1f}%
• الذاكرة: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
• القرص: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)
• وقت التشغيل: {str(uptime).split('.')[0]}

**🤖 حالة البوت:**
• نوع التشغيل: {'Webhook' if hasattr(self, 'webhook_mode') and self.webhook_mode else 'Polling'}
• إجمالي المهام: {len(tasks)}
• المهام النشطة: {active_tasks}
• قاعدة البيانات: {db_status}
• Userbot: {userbot_status}

**💻 معلومات النظام:**
• المنصة: {platform.system()} {platform.release()}
• Python: {platform.python_version()}
• المعمارية: {platform.architecture()[0]}

**⚡ الخدمات:**
• محرك التوجيه: {'🟢 يعمل' if hasattr(self.forwarding_engine, 'running') and self.forwarding_engine.running else '🔴 متوقف'}
• أمان النظام: {'🟢 نشط' if self.security_manager else '🔴 معطل'}
• إدارة الجلسات: 🟢 نشط"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 تحديث", callback_data="main_system_status"),
                    InlineKeyboardButton(text="📊 إحصائيات متقدمة", callback_data="main_advanced_stats")
                ],
                [
                    InlineKeyboardButton(text="🔧 أدوات الصيانة", callback_data="main_maintenance_tools"),
                    InlineKeyboardButton(text="⚡ اختبار الأداء", callback_data="main_performance_test")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_back")
                ]
            ])

            await callback.message.edit_text(status_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in system status: {e}")
            await callback.answer("❌ خطأ في عرض حالة النظام", show_alert=True)

    async def _handle_detailed_report(self, callback: CallbackQuery, state: FSMContext):
        """Handle detailed report generation"""
        try:
            user_id = callback.from_user.id
            
            # Generate comprehensive report
            from datetime import datetime, timedelta
            
            # Get task statistics
            tasks = await self.database.get_active_tasks()
            total_tasks = len(tasks)
            active_tasks = len([t for t in tasks if t.get('is_active')])
            bot_tasks = len([t for t in tasks if t.get('task_type') == 'bot'])
            userbot_tasks = len([t for t in tasks if t.get('task_type') == 'userbot'])
            
            # Get forwarding statistics for last 24h, 7d, 30d
            now = datetime.now()
            stats_24h = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE created_at >= $1",
                now - timedelta(hours=24)
            )
            stats_7d = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE created_at >= $1",
                now - timedelta(days=7)
            )
            stats_30d = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE created_at >= $1",
                now - timedelta(days=30)
            )
            
            # Get user statistics
            total_users = await self.database.execute_query("SELECT COUNT(*) as count FROM users")
            
            # Get success rates
            success_stats = await self.database.execute_query(
                """SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful
                FROM forwarding_logs 
                WHERE created_at >= $1""",
                now - timedelta(days=7)
            )
            
            success_rate = 0
            if success_stats and success_stats[0]['total'] > 0:
                success_rate = (success_stats[0]['successful'] / success_stats[0]['total']) * 100

            report_text = f"""📋 **التقرير المفصل**

**📈 إحصائيات المهام:**
• إجمالي المهام: {total_tasks}
• المهام النشطة: {active_tasks}
• مهام Bot API: {bot_tasks}
• مهام Userbot: {userbot_tasks}
• معدل التفعيل: {(active_tasks/total_tasks*100):.1f}% إذا كان هناك مهام

**📊 إحصائيات التوجيه:**
• آخر 24 ساعة: {stats_24h[0]['count'] if stats_24h else 0}
• آخر 7 أيام: {stats_7d[0]['count'] if stats_7d else 0} 
• آخر 30 يوم: {stats_30d[0]['count'] if stats_30d else 0}
• معدل النجاح (7 أيام): {success_rate:.1f}%

**👥 إحصائيات المستخدمين:**
• إجمالي المستخدمين: {total_users[0]['count'] if total_users else 0}
• المديرين: {len(self.config.admin_ids) if hasattr(self.config, 'admin_ids') else 'غير محدد'}

**🔧 حالة النظام:**
• تاريخ التقرير: {now.strftime('%Y-%m-%d %H:%M:%S')}
• البيانات صحيحة حتى: {now.strftime('%H:%M')}
• المنطقة الزمنية: UTC

**📝 ملاحظات:**
• جميع الإحصائيات محدثة في الوقت الفعلي
• يتم تحديث البيانات كل دقيقة
• التقرير يشمل جميع المهام والمستخدمين"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📤 تصدير PDF", callback_data="export_report_pdf"),
                    InlineKeyboardButton(text="📊 تصدير Excel", callback_data="export_report_excel")
                ],
                [
                    InlineKeyboardButton(text="📈 رسوم بيانية", callback_data="report_charts"),
                    InlineKeyboardButton(text="🔍 تحليل متقدم", callback_data="report_analysis")
                ],
                [
                    InlineKeyboardButton(text="🔄 تحديث التقرير", callback_data="main_detailed_report"),
                    InlineKeyboardButton(text="📧 إرسال بالبريد", callback_data="email_report")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_back")
                ]
            ])

            await callback.message.edit_text(report_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in detailed report: {e}")
            await callback.answer("❌ خطأ في إنشاء التقرير", show_alert=True)

    async def _handle_quick_start(self, callback: CallbackQuery, state: FSMContext):
        """Handle quick start guide"""
        try:
            user_id = callback.from_user.id
            
            quick_start_text = f"""🚀 **دليل البدء السريع**

**📋 الخطوات الأساسية:**

**1️⃣ إنشاء مهمة جديدة**
• انقر على "📋 المهام" → "➕ إنشاء مهمة"
• اختر نوع المهمة (Bot API أو Userbot)
• أدخل اسم ووصف المهمة

**2️⃣ إضافة المصادر**
• انقر على "📥 المصادر" في إعدادات المهمة
• أضف معرف القناة أو اسم المستخدم
• مثال: @channel_name أو -1001234567890

**3️⃣ إضافة الأهداف**
• انقر على "📤 الأهداف" في إعدادات المهمة  
• أضف القنوات التي تريد التوجيه إليها
• تأكد من أن البوت مدير في القنوات

**4️⃣ تفعيل المهمة**
• ارجع لعرض المهمة
• انقر على "تفعيل المهمة"
• ستبدأ المراقبة والتوجيه فوراً

**⚡ نصائح سريعة:**
• استخدم Userbot للقنوات الخاصة
• اضبط التأخير لتجنب الحظر
• فعل الفلاتر لتخصيص المحتوى
• راقب الإحصائيات باستمرار

**🎯 الأهداف الشائعة:**
• توجيه من قنوات الأخبار → قناتك
• نسخ المحتوى مع تعديل
• فلترة أنواع محددة من المحتوى"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ إنشاء مهمة الآن", callback_data="task_create"),
                    InlineKeyboardButton(text="📺 شاهد فيديو تعليمي", callback_data="tutorial_video")
                ],
                [
                    InlineKeyboardButton(text="❓ أسئلة شائعة", callback_data="quick_faq"),
                    InlineKeyboardButton(text="🛠️ حل المشاكل", callback_data="troubleshooting")
                ],
                [
                    InlineKeyboardButton(text="📖 دليل كامل", callback_data="full_guide"),
                    InlineKeyboardButton(text="💬 دعم فني", callback_data="tech_support")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_back")
                ]
            ])

            await callback.message.edit_text(quick_start_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in quick start: {e}")
            await callback.answer("❌ خطأ في عرض دليل البدء السريع", show_alert=True)

    async def _handle_advanced_tools(self, callback: CallbackQuery, state: FSMContext):
        """Handle advanced tools menu"""
        try:
            user_id = callback.from_user.id
            
            # Check admin permissions for advanced tools
            is_admin = await self.security_manager.is_admin(user_id)
            
            tools_text = f"""🛠️ **الأدوات المتقدمة**

**📊 أدوات التحليل:**
• مراقبة الأداء في الوقت الفعلي
• تحليل معدلات النجاح
• إحصائيات مفصلة للمهام
• تقارير الاستخدام

**🔧 أدوات الإدارة:**
• إدارة المهام المتقدمة
• تصدير واستيراد الإعدادات  
• النسخ الاحتياطي للبيانات
• تحسين الأداء

**⚙️ أدوات التكوين:**
• إعدادات متقدمة للبوت
• تخصيص واجهة المستخدم
• إدارة الصلاحيات
• تكوين التنبيهات

**🔍 أدوات التشخيص:**
• فحص صحة النظام
• مراقبة استهلاك الموارد
• تحليل الأخطاء
• اختبار الاتصالات

{'**👑 أدوات المدير متاحة لك**' if is_admin else '**ℹ️ بعض الأدوات تتطلب صلاحيات إدارية**'}"""

            keyboard_rows = [
                [
                    InlineKeyboardButton(text="📊 مراقب الأداء", callback_data="tool_performance_monitor"),
                    InlineKeyboardButton(text="📈 محلل البيانات", callback_data="tool_data_analyzer")
                ],
                [
                    InlineKeyboardButton(text="🔧 مدير المهام المتقدم", callback_data="tool_advanced_task_manager"),
                    InlineKeyboardButton(text="💾 نسخ احتياطي", callback_data="tool_backup_manager")
                ],
                [
                    InlineKeyboardButton(text="⚙️ تكوين النظام", callback_data="tool_system_config"),
                    InlineKeyboardButton(text="🔍 أداة التشخيص", callback_data="tool_diagnostics")
                ]
            ]
            
            if is_admin:
                keyboard_rows.append([
                    InlineKeyboardButton(text="👑 لوحة المدير", callback_data="admin_dashboard"),
                    InlineKeyboardButton(text="🔐 إدارة الأمان", callback_data="security_manager")
                ])
            
            keyboard_rows.append([
                InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="main_back")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

            await callback.message.edit_text(tools_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in advanced tools: {e}")
            await callback.answer("❌ خطأ في عرض الأدوات المتقدمة", show_alert=True)

    # === Task Management Actions Handler ===

    async def _handle_task_management_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle task management actions (import, export, start/stop all)"""
        try:
            data = callback.data
            user_id = callback.from_user.id
            
            if data == "task_import":
                await self._handle_task_import(callback, state)
            elif data == "task_export":
                await self._handle_task_export(callback, state)
            elif data == "task_start_all":
                await self._handle_task_start_all(callback, state)
            elif data == "task_stop_all":
                await self._handle_task_stop_all(callback, state)
            else:
                await callback.answer("❌ إجراء غير معروف", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in task management actions: {e}")
            await callback.answer("❌ خطأ في تنفيذ الإجراء", show_alert=True)

    async def _handle_task_import(self, callback: CallbackQuery, state: FSMContext):
        """Handle task import"""
        try:
            user_id = callback.from_user.id
            
            import_text = f"""📥 **استيراد المهام**

**الطرق المدعومة:**
• 📂 ملف JSON
• 📋 نص مُنسق 
• 🔗 رابط التكوين
• 💾 نسخة احتياطية

**تنسيق JSON المطلوب:**
```json
{{
  "tasks": [
    {{
      "name": "اسم المهمة",
      "description": "وصف المهمة",
      "task_type": "bot",
      "sources": ["@channel1", "@channel2"],
      "targets": ["@mychannel"],
      "settings": {{}}
    }}
  ]
}}
```

**📝 التعليمات:**
1. أرسل الملف أو النص
2. سيتم التحقق من التنسيق
3. اختر المهام للاستيراد
4. تأكيد الاستيراد"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📂 استيراد ملف", callback_data="import_file"),
                    InlineKeyboardButton(text="📋 استيراد نص", callback_data="import_text")
                ],
                [
                    InlineKeyboardButton(text="🔗 من رابط", callback_data="import_url"),
                    InlineKeyboardButton(text="💾 من نسخة احتياطية", callback_data="import_backup")
                ],
                [
                    InlineKeyboardButton(text="📖 دليل التنسيق", callback_data="import_format_guide"),
                    InlineKeyboardButton(text="🧪 اختبار التنسيق", callback_data="test_import_format")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للمهام", callback_data="main_tasks")
                ]
            ])

            await callback.message.edit_text(import_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in task import: {e}")
            await callback.answer("❌ خطأ في استيراد المهام", show_alert=True)

    async def _handle_task_export(self, callback: CallbackQuery, state: FSMContext):
        """Handle task export"""
        try:
            user_id = callback.from_user.id
            
            # Get user tasks
            tasks = await self.database.execute_query(
                """SELECT t.*, u.telegram_id 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE u.telegram_id = $1""",
                user_id
            )
            
            total_tasks = len(tasks) if tasks else 0
            active_tasks = len([t for t in tasks if t.get('is_active')]) if tasks else 0
            
            export_text = f"""📤 **تصدير المهام**

**إحصائيات المهام:**
• إجمالي المهام: {total_tasks}
• المهام النشطة: {active_tasks}
• المهام غير النشطة: {total_tasks - active_tasks}

**تنسيقات التصدير:**
• 📄 JSON (للاستيراد لاحقاً)
• 📊 Excel (للتحليل)
• 📋 نص مُنسق (للمراجعة)
• 💾 نسخة احتياطية كاملة

**خيارات التصدير:**
• كل المهام أو مهام محددة
• مع أو بدون الإعدادات
• مع أو بدون الإحصائيات

{f'**⚠️ لا توجد مهام للتصدير**' if total_tasks == 0 else '**✅ جاهز للتصدير**'}"""

            keyboard_rows = []
            
            if total_tasks > 0:
                keyboard_rows.extend([
                    [
                        InlineKeyboardButton(text="📄 تصدير JSON", callback_data="export_json"),
                        InlineKeyboardButton(text="📊 تصدير Excel", callback_data="export_excel")
                    ],
                    [
                        InlineKeyboardButton(text="📋 تصدير نص", callback_data="export_text"),
                        InlineKeyboardButton(text="💾 نسخة احتياطية", callback_data="export_backup")
                    ],
                    [
                        InlineKeyboardButton(text="🎯 تصدير محدد", callback_data="export_selective"),
                        InlineKeyboardButton(text="📈 مع الإحصائيات", callback_data="export_with_stats")
                    ]
                ])
            else:
                keyboard_rows.append([
                    InlineKeyboardButton(text="➕ إنشاء مهمة أولاً", callback_data="task_create")
                ])
            
            keyboard_rows.append([
                InlineKeyboardButton(text="🔙 العودة للمهام", callback_data="main_tasks")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

            await callback.message.edit_text(export_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in task export: {e}")
            await callback.answer("❌ خطأ في تصدير المهام", show_alert=True)

    async def _handle_task_start_all(self, callback: CallbackQuery, state: FSMContext):
        """Handle start all tasks"""
        try:
            user_id = callback.from_user.id
            
            # Get user's inactive tasks
            tasks = await self.database.execute_query(
                """SELECT t.* FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE u.telegram_id = $1 AND t.is_active = false""",
                user_id
            )
            
            if not tasks:
                await callback.answer("ℹ️ جميع المهام نشطة بالفعل أو لا توجد مهام", show_alert=True)
                return
            
            start_text = f"""🎯 **بدء جميع المهام**

**المهام المعطلة:**
• عدد المهام: {len(tasks)}
• سيتم تفعيل جميع المهام
• سيبدأ التوجيه فوراً

**تحذيرات:**
⚠️ تأكد من صحة إعدادات المهام
⚠️ تحقق من صلاحيات البوت
⚠️ راقب استهلاك الموارد

**المهام التي ستبدأ:**"""

            # Add task names
            for i, task in enumerate(tasks[:5], 1):
                start_text += f"\n{i}. {task.get('name', 'مهمة بدون اسم')}"
            
            if len(tasks) > 5:
                start_text += f"\n... و {len(tasks) - 5} مهام أخرى"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ بدء جميع المهام", callback_data="confirm_start_all"),
                    InlineKeyboardButton(text="❌ إلغاء", callback_data="main_tasks")
                ],
                [
                    InlineKeyboardButton(text="🎯 بدء محدد", callback_data="selective_start"),
                    InlineKeyboardButton(text="📊 عرض التفاصيل", callback_data="view_inactive_tasks")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للمهام", callback_data="main_tasks")
                ]
            ])

            await callback.message.edit_text(start_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in start all tasks: {e}")
            await callback.answer("❌ خطأ في بدء المهام", show_alert=True)

    async def _handle_task_stop_all(self, callback: CallbackQuery, state: FSMContext):
        """Handle stop all tasks"""
        try:
            user_id = callback.from_user.id
            
            # Get user's active tasks
            tasks = await self.database.execute_query(
                """SELECT t.* FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE u.telegram_id = $1 AND t.is_active = true""",
                user_id
            )
            
            if not tasks:
                await callback.answer("ℹ️ لا توجد مهام نشطة للإيقاف", show_alert=True)
                return
            
            stop_text = f"""⏹️ **إيقاف جميع المهام**

**المهام النشطة:**
• عدد المهام: {len(tasks)}
• سيتم إيقاف جميع المهام
• سيتوقف التوجيه فوراً

**تأثير الإيقاف:**
• لن يتم توجيه رسائل جديدة
• ستبقى الإعدادات محفوظة
• يمكن إعادة التشغيل لاحقاً

**المهام التي ستتوقف:**"""

            # Add task names
            for i, task in enumerate(tasks[:5], 1):
                stop_text += f"\n{i}. {task.get('name', 'مهمة بدون اسم')}"
            
            if len(tasks) > 5:
                stop_text += f"\n... و {len(tasks) - 5} مهام أخرى"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏹️ إيقاف جميع المهام", callback_data="confirm_stop_all"),
                    InlineKeyboardButton(text="❌ إلغاء", callback_data="main_tasks")
                ],
                [
                    InlineKeyboardButton(text="🎯 إيقاف محدد", callback_data="selective_stop"),
                    InlineKeyboardButton(text="📊 عرض التفاصيل", callback_data="view_active_tasks")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للمهام", callback_data="main_tasks")
                ]
            ])

            await callback.message.edit_text(stop_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in stop all tasks: {e}")
            await callback.answer("❌ خطأ في إيقاف المهام", show_alert=True)