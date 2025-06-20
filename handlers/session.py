"""
Session Management Handler - Interactive Telethon session creation
"""
import os
import asyncio
import logging
from typing import Optional, Dict, Any
from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError, 
    PhoneCodeInvalidError, 
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    FloodWaitError
)

logger = logging.getLogger(__name__)

class SessionStates(StatesGroup):
    """States for session creation process"""
    WAITING_API_ID = State()
    WAITING_API_HASH = State()
    WAITING_PHONE = State()
    WAITING_CODE = State()
    WAITING_PASSWORD = State()
    SESSION_COMPLETE = State()

class SessionHandler:
    """Handler for interactive session creation"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        
    async def handle_session_command(self, message: Message, state: FSMContext):
        """Start interactive session creation process"""
        try:
            user_id = message.from_user.id
            
            # Check current session status
            current_session = os.getenv('STRING_SESSION', '')
            session_status = "منتهية الصلاحية ❌" if not current_session or len(current_session) < 50 else "نشطة ✅"
            
            welcome_text = f"""🔐 إنشاء جلسة Telethon تفاعلي

📊 الحالة الحالية:
• STRING_SESSION: {session_status}
• وضع التشغيل: {'مختلط (Bot API + Userbot)' if session_status == 'نشطة ✅' else 'Bot API فقط'}

🚀 سيقوم هذا المساعد بإنشاء جلسة جديدة خطوة بخطوة:

1️⃣ API_ID
2️⃣ API_HASH  
3️⃣ رقم الهاتف
4️⃣ كود التحقق
5️⃣ كلمة المرور (إن وجدت)

📖 للحصول على API_ID و API_HASH:
• اذهب إلى: https://my.telegram.org
• سجل دخولك برقم هاتفك
• اذهب إلى API Development Tools
• أنشئ تطبيق جديد

هل تريد البدء؟"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 بدء إنشاء الجلسة", callback_data="session_start")],
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="session_cancel")]
            ])
            
            await message.answer(welcome_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in session command: {e}")
            await message.answer("❌ خطأ في بدء عملية إنشاء الجلسة")

    async def handle_session_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle session creation callbacks"""
        try:
            data = callback.data
            user_id = callback.from_user.id
            
            if data == "session_start":
                await self._start_api_id_input(callback, state)
            elif data == "session_cancel":
                await self._cancel_session(callback, state)
            elif data == "session_retry":
                await self._start_api_id_input(callback, state)
                
        except Exception as e:
            logger.error(f"Error in session callback: {e}")
            await callback.answer("❌ خطأ في معالجة الطلب")

    async def _start_api_id_input(self, callback: CallbackQuery, state: FSMContext):
        """Start API_ID input process"""
        try:
            text = """1️⃣ أدخل API_ID

📝 أرسل API_ID الخاص بك كرقم فقط
مثال: 12345678

⚠️ تأكد من أن الرقم صحيح وكامل"""

            await callback.message.edit_text(text)
            await state.set_state(SessionStates.WAITING_API_ID)
            await callback.answer("✅ أرسل API_ID الآن")
            
        except Exception as e:
            logger.error(f"Error starting API ID input: {e}")
            await callback.answer("❌ خطأ في بدء إدخال API_ID")

    async def handle_api_id_input(self, message: Message, state: FSMContext):
        """Handle API_ID input"""
        try:
            user_id = message.from_user.id
            api_id_text = message.text.strip() if message.text else ""
            
            # Validate API_ID
            try:
                api_id = int(api_id_text)
                if api_id <= 0:
                    raise ValueError("Invalid API_ID")
            except ValueError:
                await message.answer("❌ API_ID غير صحيح\nيجب أن يكون رقماً صحيحاً\nمثال: 12345678")
                return

            # Store API_ID
            await state.update_data(api_id=api_id)
            
            text = """2️⃣ أدخل API_HASH

📝 أرسل API_HASH الخاص بك
مثال: 1234567890abcdef1234567890abcdef

⚠️ يجب أن يكون نص من 32 حرف"""

            await message.answer(text)
            await state.set_state(SessionStates.WAITING_API_HASH)
            
        except Exception as e:
            logger.error(f"Error handling API_ID input: {e}")
            await message.answer("❌ خطأ في معالجة API_ID")

    async def handle_api_hash_input(self, message: Message, state: FSMContext):
        """Handle API_HASH input"""
        try:
            user_id = message.from_user.id
            api_hash = message.text.strip() if message.text else ""
            
            # Validate API_HASH
            if not api_hash or len(api_hash) != 32:
                await message.answer("❌ API_HASH غير صحيح\nيجب أن يكون 32 حرف بالضبط\nمثال: 1234567890abcdef1234567890abcdef")
                return

            # Store API_HASH
            await state.update_data(api_hash=api_hash)
            
            text = """3️⃣ أدخل رقم الهاتف

📝 أرسل رقم هاتفك مع رمز الدولة
مثال: +967771234567

⚠️ تأكد من أن الرقم صحيح ومرتبط بحساب تليجرام"""

            await message.answer(text)
            await state.set_state(SessionStates.WAITING_PHONE)
            
        except Exception as e:
            logger.error(f"Error handling API_HASH input: {e}")
            await message.answer("❌ خطأ في معالجة API_HASH")

    async def handle_phone_input(self, message: Message, state: FSMContext):
        """Handle phone number input and send verification code"""
        try:
            user_id = message.from_user.id
            phone = message.text.strip() if message.text else ""
            
            # Validate phone number
            if not phone.startswith('+') or len(phone) < 10:
                await message.answer("❌ رقم الهاتف غير صحيح\nيجب أن يبدأ بـ + ويتضمن رمز الدولة\nمثال: +967771234567")
                return

            # Get stored data
            data = await state.get_data()
            api_id = data.get('api_id')
            api_hash = data.get('api_hash')
            
            # Create Telethon client and send code
            try:
                client = TelegramClient(StringSession(), api_id, api_hash)
                await client.connect()
                
                # Send verification code
                result = await client.send_code_request(phone)
                phone_code_hash = result.phone_code_hash
                
                # Store session data
                self.active_sessions[user_id] = {
                    'client': client,
                    'phone': phone,
                    'phone_code_hash': phone_code_hash,
                    'api_id': api_id,
                    'api_hash': api_hash
                }
                
                await state.update_data(phone=phone, phone_code_hash=phone_code_hash)
                
                text = f"""4️⃣ أدخل كود التحقق

📱 تم إرسال كود التحقق إلى: {phone}

📝 أرسل الكود بإحدى الطرق التالية:
• الكود مباشرة: 12345
• مع حروف إضافية: 12345tt (لتجاوز انتهاء الصلاحية)

💡 نصيحة مهمة: استخدم تنسيق مثل 12345tt لتجنب انتهاء صلاحية الكود عند إرساله في تليجرام

⚠️ الكود مكون من 5 أرقام فقط"""

                await message.answer(text)
                await state.set_state(SessionStates.WAITING_CODE)
                
            except PhoneNumberInvalidError:
                await message.answer("❌ رقم الهاتف غير صحيح\nتأكد من رقم الهاتف ورمز الدولة")
            except FloodWaitError as e:
                await message.answer(f"❌ يجب الانتظار {e.seconds} ثانية قبل المحاولة مرة أخرى")
            except Exception as e:
                logger.error(f"Error sending verification code: {e}")
                await message.answer("❌ خطأ في إرسال كود التحقق\nتأكد من صحة API_ID و API_HASH")
                
        except Exception as e:
            logger.error(f"Error handling phone input: {e}")
            await message.answer("❌ خطأ في معالجة رقم الهاتف")

    async def handle_code_input(self, message: Message, state: FSMContext):
        """Handle verification code input with special format support"""
        try:
            user_id = message.from_user.id
            raw_code = message.text.strip() if message.text else ""
            
            # Parse special code format (e.g., 72737tt -> 72737)
            code = self._parse_verification_code(raw_code)
            
            # Validate parsed code
            if not code or not code.isdigit() or len(code) != 5:
                await message.answer("""❌ كود التحقق غير صحيح

📝 أرسل الكود بإحدى الطرق:
• مباشرة: 12345
• مع حروف لتجاوز انتهاء الصلاحية: 12345xx أو 12345tt

⚠️ الكود يجب أن يكون 5 أرقام""")
                return

            # Get session data
            session_data = self.active_sessions.get(user_id)
            if not session_data:
                await message.answer("❌ انتهت صلاحية الجلسة\nابدأ من جديد بأمر /session")
                await state.clear()
                return

            client = session_data['client']
            phone = session_data['phone']
            phone_code_hash = session_data['phone_code_hash']
            
            try:
                # Sign in with code
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                
                # Generate string session
                string_session = client.session.save()
                
                await self._save_and_complete_session(message, state, string_session, user_id)
                
            except SessionPasswordNeededError:
                text = """🔐 مطلوب كلمة مرور التحقق بخطوتين

📝 أرسل كلمة مرور التحقق بخطوتين الخاصة بك

⚠️ هذه كلمة المرور التي أنشأتها في إعدادات الأمان بتليجرام"""

                await message.answer(text)
                await state.set_state(SessionStates.WAITING_PASSWORD)
                
            except PhoneCodeInvalidError:
                retry_text = f"""❌ كود التحقق {code} غير صحيح

💡 نصائح:
• تأكد من الكود الصحيح
• جرب تنسيق مختلف: {code}xx أو {code}tt
• اطلب كود جديد إذا انتهت الصلاحية

🔄 أرسل الكود مرة أخرى أو ابدأ من جديد بـ /session"""
                
                await message.answer(retry_text)
                
            except PhoneCodeExpiredError:
                await message.answer("""❌ انتهت صلاحية كود التحقق

🔄 لإنشاء جلسة جديدة:
• استخدم /session للبدء من جديد
• ستحصل على كود تحقق جديد

💡 نصيحة: استخدم تنسيق مثل 12345xx لتجاوز انتهاء الصلاحية""")
                await self._cleanup_session(user_id)
                await state.clear()
                
            except Exception as e:
                logger.error(f"Error signing in with code: {e}")
                await message.answer(f"❌ خطأ في تسجيل الدخول\nالكود المستخدم: {code}\nتأكد من صحة الكود وحاول مرة أخرى")
                
        except Exception as e:
            logger.error(f"Error handling code input: {e}")
            await message.answer("❌ خطأ في معالجة كود التحقق")

    def _parse_verification_code(self, raw_code: str) -> str:
        """Parse verification code from various formats"""
        if not raw_code:
            return ""
            
        # Remove all non-digit characters except at the end
        # Support formats like: 12345xx, 12345tt, 12345abc, etc.
        import re
        
        # Extract digits from the beginning
        match = re.match(r'^(\d+)', raw_code)
        if match:
            return match.group(1)
            
        return ""

    async def handle_password_input(self, message: Message, state: FSMContext):
        """Handle 2FA password input"""
        try:
            user_id = message.from_user.id
            password = message.text.strip() if message.text else ""
            
            # Get session data
            session_data = self.active_sessions.get(user_id)
            if not session_data:
                await message.answer("❌ انتهت صلاحية الجلسة\nابدأ من جديد بأمر /session")
                await state.clear()
                return

            client = session_data['client']
            
            try:
                # Sign in with password
                await client.sign_in(password=password)
                
                # Generate string session
                string_session = client.session.save()
                
                await self._save_and_complete_session(message, state, string_session, user_id)
                
            except Exception as e:
                logger.error(f"Error signing in with password: {e}")
                await message.answer("❌ كلمة المرور غير صحيحة\nحاول مرة أخرى")
                
        except Exception as e:
            logger.error(f"Error handling password input: {e}")
            await message.answer("❌ خطأ في معالجة كلمة المرور")

    async def _save_and_complete_session(self, message: Message, state: FSMContext, string_session: str, user_id: int):
        """Save session and complete the process"""
        saved_messages_status = "⚠️ لم يتم إرسال نسخة للرسائل المحفوظة"
        
        # Send session to user's Saved Messages first
        try:
            session_data = self.active_sessions.get(user_id)
            if session_data and 'client' in session_data:
                client = session_data['client']
                if client and client.is_connected():
                    from datetime import datetime
                    session_message = f"""🔑 جلسة Telethon الجديدة

🆔 معرف المستخدم: {user_id}
📅 تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 STRING_SESSION:
```
{string_session}
```

⚠️ احتفظ بهذه الجلسة في مكان آمن ولا تشاركها مع أحد!

🤖 تم إنشاؤها بواسطة: Telegram Forwarding Bot"""
                    
                    await client.send_message('me', session_message)
                    logger.info(f"Session sent to Saved Messages for user {user_id}")
                    saved_messages_status = "✅ تم إرسال نسخة إلى رسائلك المحفوظة"
                    
        except Exception as e:
            logger.warning(f"Could not send session to Saved Messages: {e}")
        
        # Send success message
        try:
            success_text = f"""✅ تم إنشاء الجلسة بنجاح!

🔑 تم حفظ الجلسة في النظام
{saved_messages_status}

📱 يمكنك الآن استخدام البوت بكامل إمكانياته

🔄 سيتم إعادة تشغيل البوت لتطبيق الجلسة الجديدة

⚠️ تحذير: 
• لا تشارك هذه الجلسة مع أي شخص
• احتفظ بها في مكان آمن
• هذه الجلسة تعطي وصول كامل لحسابك"""

            await message.answer(success_text)
            
        except Exception as e:
            logger.error(f"Error sending success message: {e}")
        
        # Send session separately
        try:
            session_text = f"📋 STRING_SESSION (للنسخ الاحتياطي):\n\n{string_session}"
            await message.answer(session_text)
            
        except Exception as e:
            logger.error(f"Error sending session text: {e}")
        
        # Save session securely using session manager
        try:
            from session_manager import get_session_manager
            import os
            
            session_manager = get_session_manager()
            
            # Save to encrypted file with metadata
            metadata = {
                'created_via': 'interactive_session_command',
                'user_id': user_id,
                'timestamp': message.date.isoformat() if message.date else None
            }
            
            if session_manager.save_session(string_session, user_id, metadata):
                logger.success(f"Session saved securely to encrypted file for user {user_id}")
                
                # Also update environment variable for current process
                os.environ['STRING_SESSION'] = string_session
                logger.info("Environment variable updated with new session")
            else:
                logger.error("Failed to save session to encrypted file")
                # Fallback: still update environment variable
                os.environ['STRING_SESSION'] = string_session
                logger.warning("Session saved only to environment variable (fallback)")
            
        except Exception as e:
            logger.error(f"Could not save session securely: {e}")
            # Fallback: update environment variable only
            try:
                import os
                os.environ['STRING_SESSION'] = string_session
                logger.warning("Session saved only to environment variable (fallback)")
            except Exception as env_error:
                logger.error(f"Could not update environment variable: {env_error}")
        
        # Cleanup
        try:
            await self._cleanup_session(user_id)
            await state.clear()
            logger.info(f"Session cleanup completed for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Error during session cleanup: {e}")
        
        logger.info(f"Session creation process completed for user {user_id}")

    async def _cancel_session(self, callback: CallbackQuery, state: FSMContext):
        """Cancel session creation process"""
        try:
            user_id = callback.from_user.id
            await self._cleanup_session(user_id)
            await state.clear()
            
            await callback.message.edit_text("❌ تم إلغاء عملية إنشاء الجلسة")
            await callback.answer("تم الإلغاء")
            
        except Exception as e:
            logger.error(f"Error canceling session: {e}")
            await callback.answer("❌ خطأ في الإلغاء")

    async def _cleanup_session(self, user_id: int):
        """Cleanup active session data"""
        try:
            if user_id in self.active_sessions:
                session_data = self.active_sessions[user_id]
                client = session_data.get('client')
                if client:
                    await client.disconnect()
                del self.active_sessions[user_id]
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")

    def register_handlers(self, dispatcher):
        """Register session handlers"""
        try:
            # Register state handlers
            dispatcher.message.register(
                self.handle_api_id_input,
                SessionStates.WAITING_API_ID
            )
            
            dispatcher.message.register(
                self.handle_api_hash_input,
                SessionStates.WAITING_API_HASH
            )
            
            dispatcher.message.register(
                self.handle_phone_input,
                SessionStates.WAITING_PHONE
            )
            
            dispatcher.message.register(
                self.handle_code_input,
                SessionStates.WAITING_CODE
            )
            
            dispatcher.message.register(
                self.handle_password_input,
                SessionStates.WAITING_PASSWORD
            )
            
            # Register callback handler
            dispatcher.callback_query.register(
                self.handle_session_callback,
                lambda c: c.data and c.data.startswith('session_')
            )
            
            logger.info("Session handlers registered")
            
        except Exception as e:
            logger.error(f"Error registering session handlers: {e}")