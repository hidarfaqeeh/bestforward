"""
Keyboard layouts for Telegram Forwarding Bot
"""

from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from typing import Dict, Any

from database import Database
from security import SecurityManager


class BotKeyboards:
    """Keyboard layouts for the bot interface"""

    def __init__(self):
        pass
    
    def _get_localized_text(self, user_id: int, key: str, fallback: str = None) -> str:
        """Get localized text with fallback"""
        try:
            from localization import localization
            return localization.get_text(user_id, key)
        except:
            return fallback if fallback else key

    async def get_main_menu_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get main menu keyboard"""
        try:
            # Import localization at runtime to avoid circular imports
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_tasks"), callback_data="main_tasks"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_statistics"), callback_data="main_statistics")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "system_status"), callback_data="main_system_status"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "detailed_report"), callback_data="main_detailed_report")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_settings"), callback_data="main_settings"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_help"), callback_data="main_help")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "quick_start"), callback_data="main_quick_start"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "advanced_tools"), callback_data="main_advanced_tools")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_language"), callback_data="lang_menu")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating main menu keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_tasks_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get tasks management keyboard"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=f"➕ {localization.get_text(user_id, 'btn_create')} {localization.get_text(user_id, 'task_name')}", callback_data="task_create"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "task_list"), callback_data="task_list")
                ],
                [
                    InlineKeyboardButton(text=f"🔄 {localization.get_text(user_id, 'btn_refresh')}", callback_data="task_refresh"),
                    InlineKeyboardButton(text=f"📊 {localization.get_text(user_id, 'btn_statistics')}", callback_data="task_stats")
                ],
                [
                    InlineKeyboardButton(text=f"📥 Import Task", callback_data="task_import"),
                    InlineKeyboardButton(text=f"📤 Export Tasks", callback_data="task_export")
                ],
                [
                    InlineKeyboardButton(text=f"🎯 Start All Tasks", callback_data="task_start_all"),
                    InlineKeyboardButton(text=f"⏹️ Stop All Tasks", callback_data="task_stop_all")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "back_to_main"), callback_data="main_back")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating tasks keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_task_list_keyboard(self, tasks: List[dict], user_id: int, page: int = 0) -> InlineKeyboardMarkup:
        """Get task list keyboard with pagination"""
        try:
            keyboard = []

            # Items per page
            per_page = 5
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_tasks = tasks[start_idx:end_idx]

            # Task buttons
            for task in page_tasks:
                status_emoji = "🟢" if task["is_active"] else "🔴"
                type_emoji = "🤖" if task["task_type"] == "bot" else "👤"

                button_text = f"{status_emoji} {task['name'][:25]}{'...' if len(task['name']) > 25 else ''} {type_emoji}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"task_view_{task['id']}"
                    )
                ])

            # Import localization for buttons
            from localization import localization

            # Pagination buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_previous"), callback_data=f"task_list_page_{page-1}")
                )

            if end_idx < len(tasks):
                nav_buttons.append(
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_next"), callback_data=f"task_list_page_{page+1}")
                )

            if nav_buttons:
                keyboard.append(nav_buttons)

            # Action buttons
            keyboard.extend([
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_new_task"), callback_data="task_create"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_refresh"), callback_data="task_list")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_back"), callback_data="main_tasks")
                ]
            ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating task list keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_task_detail_keyboard(self, task_id: int, task_data: dict, user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get task detail keyboard"""
        try:
            from localization import localization
            
            is_active = task_data.get("is_active", False)

            task_type = task_data.get("task_type", "bot")
            mode_emoji = "🤖➡️👤" if task_type == "bot" else "👤➡️🤖"
            mode_text = f"{mode_emoji} Switch to {'Userbot' if task_type == 'bot' else 'Bot'}"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=localization.get_text(user_id, "btn_deactivate") if is_active else localization.get_text(user_id, "btn_activate"),
                        callback_data=f"task_toggle_{task_id}"
                    ),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_edit_task"), callback_data=f"task_edit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=mode_text, callback_data=f"task_mode_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_task_stats"), callback_data=f"task_statistics_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_task_settings"), callback_data=f"task_settings_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_sources"), callback_data=f"source_list_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_targets"), callback_data=f"target_list_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_delete_task"), callback_data=f"task_delete_confirm_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_task_info"), callback_data=f"task_info_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_back_to_tasks"), callback_data="task_list")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating task detail keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_task_creation_keyboard(self, user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get task creation keyboard"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🤖 Bot API", callback_data="task_create_bot"),
                    InlineKeyboardButton(text="👤 Userbot", callback_data="task_create_userbot")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_cancel"), callback_data="main_tasks")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating task creation keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_source_management_keyboard(self, task_id: int, sources: List[dict], user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get source management keyboard"""
        try:
            keyboard = []

            # Source list (up to 5)
            for source in sources[:5]:
                status_emoji = "🟢" if source["is_active"] else "🔴"
                title = source.get("chat_title", f"ID: {source['chat_id']}")

                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} {title[:30]}{'...' if len(title) > 30 else ''}",
                        callback_data=f"source_view_{task_id}_{source['id']}"
                    )
                ])

            # Action buttons
            from localization import localization
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_add_source"), callback_data=f"source_add_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_refresh"), callback_data=f"source_list_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_back"), callback_data=f"task_view_{task_id}")
                ]
            ])

            if len(sources) > 5:
                keyboard.insert(-2, [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_view_all"), callback_data=f"source_list_all_{task_id}")
                ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating source management keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_target_management_keyboard(self, task_id: int, targets: List[dict], user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get target management keyboard"""
        try:
            keyboard = []

            # Target list (up to 5)
            for target in targets[:5]:
                status_emoji = "🟢" if target["is_active"] else "🔴"
                title = target.get("chat_title", f"ID: {target['chat_id']}")

                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} {title[:30]}{'...' if len(title) > 30 else ''}",
                        callback_data=f"target_view_{task_id}_{target['id']}"
                    )
                ])

            # Action buttons
            from localization import localization
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_add_target"), callback_data=f"target_add_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_refresh"), callback_data=f"target_list_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_back"), callback_data=f"task_view_{task_id}")
                ]
            ])

            if len(targets) > 5:
                keyboard.insert(-2, [
                    InlineKeyboardButton(text=localization.get_text(6556918772, "btn_view_all"), callback_data=f"target_list_all_{task_id}")
                ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating target management keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_settings_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get settings keyboard"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_bot_settings"), callback_data="settings_bot"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_user_settings"), callback_data="settings_user")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_system"), callback_data="settings_system"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_statistics"), callback_data="settings_stats")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_back_to_menu"), callback_data="main_back")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_task_settings_keyboard(self, task_id: int, user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get task settings keyboard with localization"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_filters"), callback_data=f"setting_filters_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_content"), callback_data=f"setting_content_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_forward"), callback_data=f"setting_forward_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_limits"), callback_data=f"setting_limits_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_advanced"), callback_data=f"setting_advanced_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_reset"), callback_data=f"setting_reset_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "setting_view_all"), callback_data=f"setting_view_{task_id}"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_save"), callback_data=f"setting_save_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_back"), callback_data=f"task_view_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating task settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_forward_settings_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get advanced forward settings keyboard"""
        try:
            if not settings:
                settings = {}

            # Get current settings with defaults
            manual_mode = settings.get("manual_mode", False)
            link_preview = settings.get("link_preview", True)
            pin_messages = settings.get("pin_messages", False)
            silent_mode = settings.get("silent_mode", False)
            sync_edits = settings.get("sync_edits", False)
            sync_deletes = settings.get("sync_deletes", False)
            preserve_replies = settings.get("preserve_replies", False)
            forward_mode = settings.get("forward_mode", "copy")

            # Create keyboard with status indicators - 2 buttons per row
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Forward Mode", callback_data=f"setting_forward_mode_{task_id}"),
                    InlineKeyboardButton(
                        text=f"وضع التوجيه: {'يدوي👤' if manual_mode else 'تلقائي🤖'}",
                        callback_data=f"toggle_manual_mode_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if link_preview else '❌'} معاينة الروابط",
                        callback_data=f"toggle_link_preview_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"{'✅' if pin_messages else '❌'} تثبيت الرسائل",
                        callback_data=f"toggle_pin_messages_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if silent_mode else '❌'} الوضع الصامت",
                        callback_data=f"toggle_silent_mode_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"{'✅' if sync_deletes else '❌'} مزامنة الحذف",
                        callback_data=f"toggle_sync_deletes_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if preserve_replies else '❌'} المحافظة على الردود",
                        callback_data=f"toggle_preserve_replies_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"{'✅' if sync_edits else '❌'} مزامنة التعديل",
                        callback_data=f"toggle_sync_edits_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📋 وضع التوجيه: {forward_mode}",
                        callback_data=f"forward_mode_{task_id}"
                    ),
                    InlineKeyboardButton(text="⚙️ إعدادات أخرى", callback_data=f"forward_other_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للإعدادات", callback_data=f"task_settings_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating forward settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_manual_approval_keyboard(self, approval_id: int, task_id: int) -> InlineKeyboardMarkup:
        """Get manual approval keyboard for messages"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="✅ الموافقة والتوجيه",
                        callback_data=f"approve_message_{approval_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ رفض",
                        callback_data=f"reject_message_{approval_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📝 تعديل قبل التوجيه",
                        callback_data=f"edit_before_forward_{approval_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 عرض المهمة",
                        callback_data=f"task_view_{task_id}"
                    )
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating manual approval keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_media_types_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get comprehensive media types filter keyboard"""
        try:
            if not settings:
                settings = {}

            # Media types with localization support
            from localization import localization
            
            media_types = [
                ("allow_photos", "📷", "btn_media_photos"),
                ("allow_videos", "🎥", "btn_media_videos"), 
                ("allow_documents", "📄", "btn_media_documents"),
                ("allow_audio", "🎵", "btn_media_audio"),
                ("allow_voice", "🎤", "btn_media_voice"),
                ("allow_video_notes", "🎬", "btn_media_video_notes"),
                ("allow_stickers", "🎭", "btn_media_stickers"),
                ("allow_animations", "🎨", "btn_media_animations"),
                ("allow_contacts", "👤", "btn_media_contacts"),
                ("allow_locations", "📍", "btn_media_locations"),
                ("allow_venues", "🏢", "btn_media_venues"),
                ("allow_polls", "📊", "btn_media_polls"),
                ("allow_dice", "🎲", "btn_media_dice")
            ]

            keyboard = []

            # Add text filter toggle
            allow_text = settings.get('allow_text', True)
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{'✅' if allow_text else '❌'} 📝 Text (Text)",
                    callback_data=f"text_toggle_{task_id}"
                )
            ])

            # Add media types in pairs
            for i in range(0, len(media_types), 2):
                row = []
                for j in range(2):
                    if i + j < len(media_types):
                        key, emoji, text_key = media_types[i + j]
                        is_allowed = settings.get(key, True)
                        status_emoji = "✅" if is_allowed else "❌"
                        
                        # Get localized text - fallback to English if Arabic not available
                        localized_text = localization.get_text(user_id or 6556918772, text_key, fallback=text_key)

                        row.append(InlineKeyboardButton(
                            text=f"{status_emoji} {emoji} {localized_text}",
                            callback_data=f"media_type_{task_id}_{key}"
                        ))

                if row:
                    keyboard.append(row)

            # Control buttons
            keyboard.extend([
                [
                    InlineKeyboardButton(text="✅ تفعيل الكل", callback_data=f"media_enable_all_{task_id}"),
                    InlineKeyboardButton(text="❌ تعطيل الكل", callback_data=f"media_disable_all_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 إعادة تعيين", callback_data=f"media_reset_{task_id}"),
                    InlineKeyboardButton(text="💾 حفظ", callback_data=f"media_save_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating media types keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_confirmation_keyboard(self, action: str, item_id: int, extra: str = "") -> InlineKeyboardMarkup:
        """Get confirmation keyboard"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm_{action}_{item_id}_{extra}"),
                    InlineKeyboardButton(text="❌ No", callback_data=f"cancel_{action}_{item_id}_{extra}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating confirmation keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_back_to_main_keyboard(self, user_id: int = 6556918772) -> InlineKeyboardMarkup:
        """Get back to main menu keyboard"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "back_to_main"), callback_data="main_back")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating back to main keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_admin_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get admin management keyboard"""
        try:
            from localization import localization
            
            keyboard = [
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_users"), callback_data="admin_users"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_admin_stats"), callback_data="admin_stats")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_system"), callback_data="admin_system"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_maintenance"), callback_data="admin_maintenance")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_logs"), callback_data="admin_logs"),
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_security"), callback_data="admin_security")
                ],
                [
                    InlineKeyboardButton(text=localization.get_text(user_id, "btn_back"), callback_data="main_settings")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating admin keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_forward_mode_keyboard(self, task_id: int, current_mode: str = "copy") -> InlineKeyboardMarkup:
        """Get forward mode selection keyboard"""
        try:
            modes = [
                ("copy", "📋 نسخ"),
                ("forward", "➡️ توجيه"),
                ("quote", "💬 اقتباس")
            ]

            keyboard = []
            for mode_value, mode_text in modes:
                check_emoji = "✅" if mode_value == current_mode else "⚪"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{check_emoji} {mode_text}",
                        callback_data=f"set_forward_mode_{task_id}_{mode_value}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(text="🔙 Back", callback_data=f"task_settings_{task_id}")
            ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating forward mode keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_boolean_setting_keyboard(self, task_id: int, setting_name: str, 
                                         current_value: bool = False) -> InlineKeyboardMarkup:
        """Get boolean setting keyboard"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if current_value else '⚪'} تفعيل",
                        callback_data=f"set_bool_{task_id}_{setting_name}_true"
                    ),
                    InlineKeyboardButton(
                        text=f"{'⚪' if current_value else '✅'} تعطيل",
                        callback_data=f"set_bool_{task_id}_{setting_name}_false"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=f"task_settings_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating boolean setting keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_advanced_settings_keyboard(self, task_id: int, settings: Optional[Dict] = None) -> InlineKeyboardMarkup:
        """Get advanced settings keyboard - 2 buttons per row"""
        keyboard = [
            [
                InlineKeyboardButton(text="🌐 إعدادات الترجمة", callback_data=f"advanced_translation_{task_id}"),
                InlineKeyboardButton(text="⏰ ساعات العمل", callback_data=f"advanced_working_hours_{task_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 المنشور المتكرر", callback_data=f"advanced_recurring_{task_id}"),
                InlineKeyboardButton(text="🎛️ إعدادات أخرى", callback_data=f"advanced_other_{task_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 العودة للإعدادات", callback_data=f"task_settings_{task_id}")
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def get_filter_settings_keyboard(self, task_id: int, current_settings: dict) -> InlineKeyboardMarkup:
        """Get filter settings keyboard - Updated to include day filter moved from Advanced"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(text="🔤 الكلمات المفتاحية", callback_data=f"filter_keywords_{task_id}"),
                    InlineKeyboardButton(text="📷 أنواع الوسائط", callback_data=f"filter_media_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 الرسائل المعاد توجيهها", callback_data=f"filter_forwarded_{task_id}"),
                    InlineKeyboardButton(text="🔗 فلتر الروابط", callback_data=f"filter_links_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔘 الأزرار الشفافة", callback_data=f"filter_buttons_{task_id}"),
                    InlineKeyboardButton(text="🔁 فلتر التكرار", callback_data=f"filter_duplicates_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🌍 فلتر اللغة", callback_data=f"filter_language_{task_id}"),
                    InlineKeyboardButton(text="👤 فلتر المستخدمين", callback_data=f"user_filter_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📅 فلتر الأيام", callback_data=f"filter_days_{task_id}"),
                    InlineKeyboardButton(text="📏 طول الرسالة", callback_data=f"filter_length_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"filter_clear_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"task_settings_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating filter settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_language_filter_keyboard(self, task_id: int, current_settings: dict) -> InlineKeyboardMarkup:
        """Get language filter management keyboard"""
        try:
            # Common languages
            languages = [
                ("ar", "🇸🇦 Arabic"),
                ("en", "🇺🇸 English"),
                ("es", "🇪🇸 Spanish"),
                ("fr", "🇫🇷 French"),
                ("de", "🇩🇪 German"),
                ("ru", "🇷🇺 Russian"),
                ("zh", "🇨🇳 Chinese"),
                ("ja", "🇯🇵 Japanese"),
                ("hi", "🇮🇳 Hindi"),
                ("tr", "🇹🇷 Turkish"),
                ("it", "🇮🇹 Italian"),
                ("pt", "🇵🇹 Portuguese"),
                ("ko", "🇰🇷 Korean"),
                ("fa", "🇮🇷 Persian"),
                ("ur", "🇵🇰 Urdu")
            ]

            filter_mode = current_settings.get("language_filter_mode", "blacklist")
            allowed_languages = current_settings.get("allowed_languages", []) or []

            keyboard = []

            # Filter mode toggle
            mode_text = "⚫ Blacklist" if filter_mode == "blacklist" else "⚪ Whitelist"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"Mode: {mode_text}",
                    callback_data=f"toggle_lang_mode_{task_id}"
                )
            ])

            # Language selection (2 per row)
            for i in range(0, len(languages), 2):
                row = []
                for j in range(2):
                    if i + j < len(languages):
                        lang_code, lang_name = languages[i + j]
                        is_selected = lang_code in allowed_languages
                        status = "✅" if is_selected else "❌"

                        row.append(InlineKeyboardButton(
                            text=f"{status} {lang_name}",
                            callback_data=f"toggle_lang_{task_id}_{lang_code}"
                        ))
                keyboard.append(row)

            # Management buttons
            keyboard.extend([
                [
                    InlineKeyboardButton(text="🔄 Clear All", callback_data=f"lang_clear_{task_id}"),
                    InlineKeyboardButton(text="📋 Add Custom", callback_data=f"lang_custom_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="💾 Save", callback_data=f"lang_save_{task_id}"),
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"setting_filters_{task_id}")
                ]
            ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating language filter keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_pagination_keyboard(self, current_page: int, total_pages: int, 
                                    callback_prefix: str, back_callback: str = None) -> InlineKeyboardMarkup:
        """Get pagination keyboard"""
        try:
            keyboard = []

            # Navigation buttons
            nav_buttons = []

            if current_page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_{current_page-1}")
                )

            nav_buttons.append(
                InlineKeyboardButton(text=f"{current_page+1}/{total_pages}", callback_data="noop")
            )

            if current_page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_{current_page+1}")
                )

            if nav_buttons:
                keyboard.append(nav_buttons)

            # Back button
            if back_callback:
                keyboard.append([
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=back_callback)
                ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating pagination keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_advanced_settings_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get advanced features settings keyboard - cleaned up after moving buttons to appropriate sections"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(text="🌐 إعدادات الترجمة", callback_data=f"advanced_translation_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="⏰ إعدادات ساعات العمل", callback_data=f"advanced_working_hours_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 إعدادات المنشور المتكرر", callback_data=f"advanced_recurring_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للإعدادات", callback_data=f"task_settings_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating advanced settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_advanced_translation_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get comprehensive translation settings keyboard"""
        try:
            if not settings:
                settings = {}

            # Language mapping with flags
            languages = [
                ("ar", "🇸🇦", "العربية"), ("en", "🇺🇸", "الإنجليزية"),
                ("fr", "🇫🇷", "الفرنسية"), ("de", "🇩🇪", "الألمانية"),
                ("es", "🇪🇸", "الإسبانية"), ("ru", "🇷🇺", "الروسية"),
                ("tr", "🇹🇷", "التركية"), ("fa", "🇮🇷", "الفارسية"),
                ("ja", "🇯🇵", "اليابانية"), ("ko", "🇰🇷", "الكورية"),
                ("zh", "🇨🇳", "الصينية"), ("it", "🇮🇹", "الإيطالية")
            ]

            keyboard = []

            # Source language selection
            keyboard.append([InlineKeyboardButton(text="📥 اللغة المترجم منها", callback_data="dummy")])
            source_lang = settings.get("source_language", "auto")
            source_rows = []
            auto_status = "✅" if source_lang == "auto" else ""
            source_rows.append([InlineKeyboardButton(text=f"🔍 اكتشاف تلقائي {auto_status}", callback_data=f"set_source_lang_auto_{task_id}")])

            for i in range(0, len(languages), 3):
                row = []
                for j in range(3):
                    if i + j < len(languages):
                        lang_code, flag, name = languages[i + j]
                        status = "✅" if lang_code == source_lang else ""
                        row.append(InlineKeyboardButton(
                            text=f"{flag} {name} {status}",
                            callback_data=f"set_source_lang_{lang_code}_{task_id}"
                        ))
                source_rows.append(row)
            keyboard.extend(source_rows)

            # Target language selection
            keyboard.append([InlineKeyboardButton(text="📤 اللغة المترجم إليها", callback_data="dummy")])
            target_lang = settings.get("target_language", "ar")
            target_rows = []
            for i in range(0, len(languages), 3):
                row = []
                for j in range(3):
                    if i + j < len(languages):
                        lang_code, flag, name = languages[i + j]
                        status = "✅" if lang_code == target_lang else ""
                        row.append(InlineKeyboardButton(
                            text=f"{flag} {name} {status}",
                            callback_data=f"set_target_lang_{lang_code}_{task_id}"
                        ))
                target_rows.append(row)
            keyboard.extend(target_rows)

            # Translation controls
            auto_translate = settings.get("auto_translate", False)
            keyboard.extend([
                [InlineKeyboardButton(text="⚙️ إعدادات الترجمة", callback_data="dummy")],
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if auto_translate else '❌'} تفعيل الترجمة التلقائية",
                        callback_data=f"toggle_auto_translate_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🧪 اختبار الترجمة", callback_data=f"test_translation_{task_id}"),
                    InlineKeyboardButton(text="📊 إحصائيات", callback_data=f"translation_stats_{task_id}")
                ],
                [InlineKeyboardButton(text="🔙 العودة للميزات المتقدمة", callback_data=f"setting_advanced_{task_id}")]
            ])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating advanced translation keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_advanced_working_hours_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get comprehensive working hours settings keyboard"""
        try:
            if not settings:
                settings = {}

            working_hours_enabled = settings.get("working_hours_enabled", False)
            start_hour = settings.get("start_hour", 9)
            end_hour = settings.get("end_hour", 17)
            timezone = settings.get("timezone", "UTC")
            break_start = settings.get("break_start_hour", 12)
            break_end = settings.get("break_end_hour", 13)

            keyboard = []

            # Enable/Disable working hours
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if working_hours_enabled else '❌'} تفعيل ساعات العمل",
                        callback_data=f"toggle_working_hours_{task_id}"
                    )
                ]
            ])

            if working_hours_enabled:
                # Start time selection
                keyboard.append([InlineKeyboardButton(text=f"🕘 وقت البداية: {start_hour:02d}:00", callback_data="dummy")])
                start_rows = []
                for i in range(0, 24, 6):
                    row = []
                    for j in range(6):
                        hour = i + j
                        if hour < 24:
                            status = "✅" if hour == start_hour else ""
                            row.append(InlineKeyboardButton(
                                text=f"{hour:02d}:00 {status}",
                                callback_data=f"set_start_hour_{hour}_{task_id}"
                            ))
                    start_rows.append(row)
                keyboard.extend(start_rows)

                # End time selection
                keyboard.append([InlineKeyboardButton(text=f"🕕 وقت التوقف: {end_hour:02d}:00", callback_data="dummy")])
                end_rows = []
                for i in range(0, 24, 6):
                    row = []
                    for j in range(6):
                        hour = i + j
                        if hour < 24:
                            status = "✅" if hour == end_hour else ""
                            row.append(InlineKeyboardButton(
                                text=f"{hour:02d}:00 {status}",
                                callback_data=f"set_end_hour_{hour}_{task_id}"
                            ))
                    end_rows.append(row)
                keyboard.extend(end_rows)

                # Break time settings
                keyboard.append([InlineKeyboardButton(text=f"☕ وقت الراحة: {break_start:02d}:00 - {break_end:02d}:00", callback_data="dummy")])
                keyboard.extend([
                    [
                        InlineKeyboardButton(text=f"بداية الراحة: {break_start:02d}:00", callback_data=f"set_break_start_{task_id}"),
                        InlineKeyboardButton(text=f"نهاية الراحة: {break_end:02d}:00", callback_data=f"set_break_end_{task_id}")
                    ]
                ])

                # Timezone selection
                keyboard.append([InlineKeyboardButton(text=f"🌍 المنطقة الزمنية: {timezone}", callback_data="dummy")])
                timezones = [
                    ("UTC", "التوقيت العالمي"), ("Asia/Riyadh", "الرياض"), 
                    ("Asia/Dubai", "دبي"), ("Europe/London", "لندن"),
                    ("America/New_York", "نيويورك"), ("Asia/Tokyo", "طوكيو"),
                    ("Europe/Paris", "باريس"), ("Asia/Cairo", "القاهرة")
                ]

                tz_rows = []
                for i in range(0, len(timezones), 2):
                    row = []
                    for j in range(2):
                        if i + j < len(timezones):
                            tz_code, tz_name = timezones[i + j]
                            status = "✅" if tz_code == timezone else ""
                            row.append(InlineKeyboardButton(
                                text=f"{tz_name} {status}",
                                callback_data=f"set_timezone_{tz_code.replace('/', '_')}_{task_id}"
                            ))
                    tz_rows.append(row)
                keyboard.extend(tz_rows)

                # Additional options
                keyboard.extend([
                    [
                        InlineKeyboardButton(text="📊 تقرير ساعات العمل", callback_data=f"working_hours_report_{task_id}"),
                        InlineKeyboardButton(text="⏰ اختبار الوقت", callback_data=f"test_current_time_{task_id}")
                    ]
                ])

            keyboard.append([InlineKeyboardButton(text="🔙 العودة للميزات المتقدمة", callback_data=f"setting_advanced_{task_id}")])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating advanced working hours keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_advanced_recurring_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get comprehensive recurring post settings keyboard"""
        try:
            if not settings:
                settings = {}

            recurring_enabled = settings.get("recurring_post_enabled", False)
            interval_hours = settings.get("recurring_interval_hours", 24)

            keyboard = []

            # Main recurring post controls
            keyboard.extend([
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if recurring_enabled else '❌'} تفعيل المنشور المتكرر",
                        callback_data=f"toggle_recurring_post_{task_id}"
                    )
                ]
            ])

            if recurring_enabled:
                # Time interval selection
                keyboard.append([InlineKeyboardButton(text=f"⏱️ الفترة الزمنية: كل {interval_hours} ساعة", callback_data="dummy")])
                intervals = [
                    (1, "ساعة واحدة"), (3, "3 ساعات"), (6, "6 ساعات"), (12, "12 ساعة"),
                    (24, "يوم واحد"), (48, "يومين"), (72, "3 أيام"), (168, "أسبوع")
                ]

                interval_rows = []
                for i in range(0, len(intervals), 2):
                    row = []
                    for j in range(2):
                        if i + j < len(intervals):
                            hours, name = intervals[i + j]
                            status = "✅" if hours == interval_hours else ""
                            row.append(InlineKeyboardButton(
                                text=f"{name} {status}",
                                callback_data=f"set_interval_{hours}_{task_id}"
                            ))
                    interval_rows.append(row)
                keyboard.extend(interval_rows)

                # Post management
                keyboard.extend([
                    [InlineKeyboardButton(text="📝 إدارة المنشورات المتكررة", callback_data="dummy")],
                    [
                        InlineKeyboardButton(text="➕ إضافة منشور جديد", callback_data=f"add_recurring_post_{task_id}"),
                        InlineKeyboardButton(text="📋 عرض المنشورات", callback_data=f"list_recurring_posts_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="✏️ تعديل منشور", callback_data=f"edit_recurring_post_{task_id}"),
                        InlineKeyboardButton(text="🗑️ حذف منشور", callback_data=f"delete_recurring_post_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="📊 إحصائيات المنشورات", callback_data=f"recurring_stats_{task_id}"),
                        InlineKeyboardButton(text="🔄 تشغيل فوري", callback_data=f"run_recurring_now_{task_id}")
                    ]
                ])

                keyboard.append([InlineKeyboardButton(text="🔙 العودة للميزات المتقدمة", callback_data=f"setting_advanced_{task_id}")])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating advanced recurring keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_translation_settings_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get translation settings keyboard"""
        try:
            if not settings:
                settings = {}

            auto_translate = settings.get("auto_translate", False)
            target_language = settings.get("target_language", "ar")

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if auto_translate else '❌'} تفعيل الترجمة",
                        callback_data=f"toggle_translation_{task_id}"
                    )
                ]
            ]

            if auto_translate:
                keyboard.append([InlineKeyboardButton(text="🌐 اختيار اللغة المستهدفة:", callback_data="dummy")])

                # Language selection with better layout
                languages = [
                    ("🇸🇦 العربية", "ar"), ("🇺🇸 الإنجليزية", "en"), 
                    ("🇫🇷 الفرنسية", "fr"), ("🇩🇪 الألمانية", "de"),
                    ("🇪🇸 الإسبانية", "es"), ("🇷🇺 الروسية", "ru"),
                    ("🇹🇷 التركية", "tr"), ("🇮🇷 الفارسية", "fa")
                ]

                # Add language buttons in rows of 2
                for i in range(0, len(languages), 2):
                    row = []
                    for j in range(i, min(i + 2, len(languages))):
                        lang_name, lang_code = languages[j]
                        status = " ✅" if lang_code == target_language else ""
                        row.append(InlineKeyboardButton(
                            text=f"{lang_name}{status}",
                            callback_data=f"set_target_lang_{lang_code}_{task_id}"
                        ))
                    keyboard.append(row)



            keyboard.append([InlineKeyboardButton(text="🔙 العودة للمتقدم", callback_data=f"setting_advanced_{task_id}")])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating translation settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_working_hours_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get working hours settings keyboard"""
        try:
            if not settings:
                settings = {}

            working_hours_enabled = settings.get("working_hours_enabled", False)
            start_hour = settings.get("start_hour", 0)
            end_hour = settings.get("end_hour", 23)
            timezone = settings.get("timezone", "UTC")

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if working_hours_enabled else '❌'} تفعيل ساعات العمل",
                        callback_data=f"toggle_working_hours_{task_id}"
                    )
                ]
            ]

            if working_hours_enabled:
                # Current time display
                current_time_text = f"⏰ الوقت الحالي: {timezone}"
                keyboard.append([InlineKeyboardButton(text=current_time_text, callback_data="dummy")])

                # Start and end hour selection with better interface
                keyboard.extend([
                    [
                        InlineKeyboardButton(text=f"🕐 تعديل ساعة البداية ({start_hour:02d}:00)", callback_data=f"start_hour_{task_id}"),
                        InlineKeyboardButton(text=f"🕕 تعديل ساعة النهاية ({end_hour:02d}:00)", callback_data=f"end_hour_{task_id}")
                    ]
                ])

                # Timezone and breaks selection
                keyboard.extend([
                    [
                        InlineKeyboardButton(text=f"🌍 المنطقة الزمنية ({timezone})", callback_data=f"timezone_{task_id}"),
                        InlineKeyboardButton(text="☕ فترات الراحة", callback_data=f"breaks_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="📅 أيام العمل", callback_data=f"workdays_{task_id}")
                    ]
                ])

                # Additional options
                keyboard.extend([
                    [
                        InlineKeyboardButton(text="📊 تقرير ساعات العمل", callback_data=f"working_hours_report_{task_id}"),
                        InlineKeyboardButton(text="⏰ اختبار الوقت", callback_data=f"test_current_time_{task_id}")
                    ]
                ])

            keyboard.append([InlineKeyboardButton(text="🔙 العودة للمتقدم", callback_data=f"setting_advanced_{task_id}")])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating working hours keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_recurring_post_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get recurring post settings keyboard"""
        try:
            if not settings:
                settings = {}

            recurring_post_enabled = settings.get("recurring_post_enabled", False)
            recurring_interval_hours = settings.get("recurring_interval_hours", 24)

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if recurring_post_enabled else '❌'} تفعيل المنشور المتكرر",
                        callback_data=f"toggle_recurring_post_{task_id}"
                    )
                ]
            ]

            if recurring_post_enabled:
                # Interval selection
                keyboard.append([InlineKeyboardButton(text=f"⏱️ الفترة الزمنية: كل {recurring_interval_hours} ساعة", callback_data="dummy")])

                # Quick interval buttons
                intervals = [
                    ("1 ساعة", 1), ("3 ساعات", 3), ("6 ساعات", 6), ("12 ساعة", 12),
                    ("24 ساعة", 24), ("48 ساعة", 48), ("72 ساعة", 72), ("أسبوع", 168)
                ]

                interval_rows = []
                for i in range(0, len(intervals), 2):
                    row = []
                    for j in range(i, min(i + 2, len(intervals))):
                        interval_name, interval_hours = intervals[j]
                        status = " ✅" if interval_hours == recurring_interval_hours else ""
                        row.append(InlineKeyboardButton(
                            text=f"{interval_name}{status}",
                            callback_data=f"set_recurring_interval_{interval_hours}_{task_id}"
                        ))
                    interval_rows.append(row)
                keyboard.extend(interval_rows)

                # Custom interval
                keyboard.append([InlineKeyboardButton(text="⚙️ فترة مخصصة", callback_data=f"set_custom_interval_{task_id}")])

                # Content management
                keyboard.extend([
                    [InlineKeyboardButton(text="📝 إنشاء محتوى جديد", callback_data=f"create_recurring_content_{task_id}")],
                    [InlineKeyboardButton(text="✏️ تعديل المحتوى", callback_data=f"edit_recurring_content_{task_id}")],
                    [InlineKeyboardButton(text="📋 عرض المحتوى الحالي", callback_data=f"view_recurring_content_{task_id}")],
                    [InlineKeyboardButton(text="🗂️ قائمة المحتويات", callback_data=f"list_recurring_content_{task_id}")]
                ])

                # Scheduling options
                keyboard.append([InlineKeyboardButton(text="📅 خيارات الجدولة", callback_data="dummy")])
                keyboard.extend([
                    [InlineKeyboardButton(text="🕐 تحديد وقت البداية", callback_data=f"set_recurring_start_time_{task_id}")],
                    [InlineKeyboardButton(text="📊 عرض الجدولة القادمة", callback_data=f"view_recurring_schedule_{task_id}")],
                    [InlineKeyboardButton(text="⏸️ إيقاف مؤقت", callback_data=f"pause_recurring_{task_id}")],
                    [InlineKeyboardButton(text="🔄 إعادة تشغيل الآن", callback_data=f"restart_recurring_{task_id}")]
                ])

                # Advanced options
                keyboard.extend([
                    [InlineKeyboardButton(text="🗑️ حذف المنشورات السابقة", callback_data=f"toggle_delete_previous_{task_id}")],
                    [InlineKeyboardButton(text="📈 إحصائيات المنشورات", callback_data=f"recurring_stats_{task_id}")],
                    [InlineKeyboardButton(text="📄 سجل المنشورات", callback_data=f"recurring_log_{task_id}")]
                ])

            keyboard.append([InlineKeyboardButton(text="🔙 العودة للمتقدم", callback_data=f"setting_advanced_{task_id}")])

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating recurring post keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])

    async def get_limits_settings_keyboard(self, task_id: int, settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Get limits settings keyboard - Updated per user requirements"""
        try:
            if settings is None:
                settings = {}
            
            delay_min = settings.get('delay_min', 0)
            delay_max = settings.get('delay_max', 0)
            length_limit = settings.get('max_message_length', 0)
            send_limit = settings.get('send_limit', 0)
            
            keyboard = [
                [
                    InlineKeyboardButton(text="⏱️ Message Delays", callback_data=f"setting_delays_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📏 حدود الطول", callback_data=f"filter_length_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🚦 حدود الإرسال", callback_data=f"advanced_sending_limit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Settings", callback_data=f"task_settings_{task_id}")
                ]
            ]

            return InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error creating limits settings keyboard: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])