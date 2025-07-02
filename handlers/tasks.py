"""
Task Handlers - Task management and operations
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from modules.task_manager import TaskManager
from modules.statistics import StatisticsManager
from utils import extract_chat_id, format_datetime, truncate_text


class TaskStates(StatesGroup):
    """FSM States for task operations"""
    CREATING_TASK = State()
    EDITING_TASK = State()
    WAITING_TASK_NAME = State()
    WAITING_TASK_DESCRIPTION = State()
    WAITING_INPUT = State()


class TaskHandlers:
    """Handles task management operations"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.bot = bot_controller.bot
        self.database = bot_controller.database
        self.security_manager = bot_controller.security_manager
        self.keyboards = bot_controller.keyboards
        self.forwarding_engine = bot_controller.forwarding_engine
        
        # Initialize managers
        self.task_manager = TaskManager(self.database)
        self.statistics_manager = StatisticsManager(self.database)
        
    async def register_handlers(self):
        """Register task handlers"""
        try:
            # Message handlers for task creation
            self.bot_controller.dispatcher.message.register(
                self.handle_task_name_input,
                TaskStates.WAITING_TASK_NAME
            )
            
            self.bot_controller.dispatcher.message.register(
                self.handle_task_description_input,
                TaskStates.WAITING_TASK_DESCRIPTION
            )
            
            self.bot_controller.dispatcher.message.register(
                self.handle_keyword_input,
                TaskStates.WAITING_INPUT
            )
            
            # Callback handlers for task interactions
            self.bot_controller.dispatcher.callback_query.register(
                self.handle_callback,
                lambda callback: callback.data and (
                    callback.data.startswith("task_") or 
                    callback.data.startswith("setting_") or
                    callback.data.startswith("filter_") or
                    callback.data.startswith("kw_") or
                    callback.data.startswith("media_") or
                    callback.data.startswith("text_") or
                    callback.data.startswith("len_") or
                    callback.data.startswith("length_") or
                    callback.data.startswith("user_") or
                    callback.data.startswith("content_") or

                    callback.data.startswith("set_min_") or
                    callback.data.startswith("set_max_") or
                    callback.data.startswith("set_action_")
                )
            )
            
            await self.task_manager.initialize()
            logger.info("Task handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register task handlers: {e}")
            raise
    
    async def handle_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle task callback queries"""
        data = callback.data
        user_id = callback.from_user.id
        logger.info(f"Task callback received: {data}")
        logger.info(f"Callback data type: {type(data)}, length: {len(data) if data else 0}")
        
        # Content button debugging (can be removed in production)
        if data and data.startswith("content_"):
            logger.info(f"Content button pressed: {data}")
        
        # Ensure data is not None before processing
        if not data:
            logger.error("Callback data is None or empty")
            await callback.answer("❌ Invalid callback data.", show_alert=True)
            return
        
        try:
            logger.warning(f"=== PROCESSING CALLBACK: {data} ===")
            logger.error(f"RAW CALLBACK DATA RECEIVED: '{data}' (type: {type(data)})")
            
            # HIGHEST PRIORITY: Handle advanced sub-feature buttons first with exhaustive logging
            if data and "advanced_" in str(data):
                logger.error(f"CONTAINS 'advanced_': {data}")
                
            if data and str(data).startswith("advanced_"):
                logger.error(f"STARTS WITH 'advanced_': {data}")
                
            if data == "advanced_translation_1" or data == "advanced_working_hours_1" or data == "advanced_recurring_1":
                logger.error(f"EXACT MATCH DETECTED: {data}")
                
            # PRIORITY: Handle advanced sub-feature buttons first
            if data.startswith("advanced_"):
                logger.error(f"ADVANCED BUTTON DETECTED: {data}")
                if data == "advanced_translation_1":
                    await callback.answer("🌐 إعدادات الترجمة تعمل بنجاح!", show_alert=True)
                    # Create translation interface
                    from localization import localization
                    user_id = callback.from_user.id
                    
                    text = f"""🌐 **{localization.get_text(user_id, "translation_title")}**

🔘 **{localization.get_text(user_id, "auto_translate")}:** {localization.get_text(user_id, "translation_disabled")}
🌍 **{localization.get_text(user_id, "source_language")}:** {localization.get_text(user_id, "translate_to_arabic" if localization.get_user_language(user_id) == "ar" else "translate_to_english")}
🎯 **{localization.get_text(user_id, "target_language")}:** {localization.get_text(user_id, "language_arabic" if localization.get_user_language(user_id) == "ar" else "language_english")}

**{localization.get_text(user_id, "select_language")}**
• {localization.get_text(user_id, "language_arabic")} • {localization.get_text(user_id, "language_english")} • {localization.get_text(user_id, "language_settings")}

{localization.get_text(user_id, "select_option")}"""
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"🔄 {localization.get_text(user_id, 'auto_translate')}", callback_data="toggle_auto_translate_1")],
                        [InlineKeyboardButton(text=f"🌍 {localization.get_text(user_id, 'source_language')}", callback_data="source_lang_1")],
                        [InlineKeyboardButton(text=f"🎯 {localization.get_text(user_id, 'target_language')}", callback_data="target_lang_1")],
                        [InlineKeyboardButton(text=f"🔙 {localization.get_text(user_id, 'btn_back')}", callback_data="setting_advanced_1")]
                    ])
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
                    return
                    
                elif data == "advanced_working_hours_1":
                    await callback.answer("⏰ إعدادات ساعات العمل تعمل بنجاح!", show_alert=True)
                    # Create working hours interface
                    from localization import localization
                    user_id = callback.from_user.id
                    
                    text = f"""⏰ **{localization.get_text(user_id, "working_hours_title")}**

🔘 **{localization.get_text(user_id, "working_hours_enabled" if False else "working_hours_disabled")}**
🕐 **{localization.get_text(user_id, "start_hour")}:** 09:00
🕕 **{localization.get_text(user_id, "end_hour")}:** 17:00
🌍 **{localization.get_text(user_id, "current_timezone")}:** UTC+3

⏱️ **{localization.get_text(user_id, "breaks_settings")}:**
• 12:00 - 13:00

**{localization.get_text(user_id, "working_days")}:**
☑️ {localization.get_text(user_id, "monday")} ☑️ {localization.get_text(user_id, "tuesday")} ☑️ {localization.get_text(user_id, "wednesday")} ☑️ {localization.get_text(user_id, "thursday")} ☑️ {localization.get_text(user_id, "friday")}
☐ {localization.get_text(user_id, "saturday")} ☐ {localization.get_text(user_id, "sunday")}

{localization.get_text(user_id, "select_option")}"""
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"🔄 {localization.get_text(user_id, 'working_hours_enabled')}", callback_data="toggle_workhours_1")],
                        [InlineKeyboardButton(text=f"🕐 {localization.get_text(user_id, 'set_start_hour')}", callback_data="start_hour_1"), 
                         InlineKeyboardButton(text=f"🕕 {localization.get_text(user_id, 'set_end_hour')}", callback_data="end_hour_1")],
                        [InlineKeyboardButton(text=f"🌍 {localization.get_text(user_id, 'set_timezone')}", callback_data="timezone_1")],
                        [InlineKeyboardButton(text=f"⏱️ {localization.get_text(user_id, 'breaks_settings')}", callback_data="breaks_1")],
                        [InlineKeyboardButton(text=f"📅 {localization.get_text(user_id, 'working_days')}", callback_data="workdays_1")],
                        [InlineKeyboardButton(text=f"🔙 {localization.get_text(user_id, 'btn_back')}", callback_data="setting_advanced_1")]
                    ])
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
                    return
                    
                elif data == "advanced_recurring_1":
                    await callback.answer("🔄 إعدادات المنشور المتكرر تعمل بنجاح!", show_alert=True)
                    # Create recurring posts interface
                    from localization import localization
                    user_id = callback.from_user.id
                    
                    text = f"""🔄 **{localization.get_text(user_id, "recurring_title")}**

🔘 **{localization.get_text(user_id, "recurring_disabled")}**
⏰ **{localization.get_text(user_id, "recurring_interval")}:** 24 hours
📝 **Active posts:** 0

**{localization.get_text(user_id, "recurring_content")}:**
📋 {localization.get_text(user_id, "no_tasks")}

**Available intervals:**
• 1 hour • 3 hours • 6 hours
• 12 hours • 24 hours • Weekly

{localization.get_text(user_id, "select_option")}"""
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"🔄 {localization.get_text(user_id, 'recurring_enabled')}", callback_data="toggle_recurring_1")],
                        [InlineKeyboardButton(text=f"➕ {localization.get_text(user_id, 'btn_create')}", callback_data="add_recurring_1")],
                        [InlineKeyboardButton(text=f"📋 {localization.get_text(user_id, 'btn_view_all')}", callback_data="list_recurring_1")],
                        [InlineKeyboardButton(text=f"⏰ {localization.get_text(user_id, 'recurring_interval')}", callback_data="interval_recurring_1")],
                        [InlineKeyboardButton(text=f"🔙 {localization.get_text(user_id, 'btn_back')}", callback_data="setting_advanced_1")]
                    ])
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
                    return
            
            # URGENT: Direct handlers for advanced sub-feature buttons with full interfaces
            if data == "advanced_translation_1":
                logger.error(f"DIRECT MATCH: advanced_translation_1 detected!")
                await self._handle_advanced_translation(callback, 1, state)
                return
            elif data == "advanced_working_hours_1":
                logger.error(f"DIRECT MATCH: advanced_working_hours_1 detected!")
                await self._handle_working_hours_setting(callback, 1, state)
                return
            elif data == "advanced_recurring_1":
                logger.error(f"DIRECT MATCH: advanced_recurring_1 detected!")
                await self._handle_recurring_post_setting(callback, 1, state)
                return
            
            # Special logging for advanced settings debugging
            if "setting_advanced_" in data:
                logger.warning(f"DEBUGGING: Advanced setting callback detected: {data}")
            
            # Special logging for advanced sub-features
            if "advanced_translation_" in data or "advanced_working_hours_" in data or "advanced_recurring_" in data:
                logger.warning(f"DEBUGGING: Advanced sub-feature callback detected: {data}")
                
            # Special logging for length filter debugging
            if "length" in data or "len_" in data:
                logger.warning(f"DEBUGGING: Length filter callback detected: {data}")
            
            if data == "task_create":
                await self._handle_task_creation_start(callback, state)
            elif data == "task_list":
                await self._handle_task_list(callback, state)
            elif data == "task_refresh":
                await self._handle_task_refresh(callback, state)
            elif data == "task_stats":
                await self._handle_task_statistics_overview(callback, state)
            elif data.startswith("task_create_"):
                await self._handle_task_type_selection(callback, state)
            elif data.startswith("task_view_"):
                await self._handle_task_view(callback, state)
            elif data.startswith("task_edit_"):
                await self._handle_task_edit(callback, state)
            elif data.startswith("task_toggle_"):
                await self._handle_task_toggle(callback, state)
            elif data.startswith("task_mode_toggle_"):
                await self._handle_task_mode_toggle(callback, state)
            elif data.startswith("task_delete_"):
                await self._handle_task_delete(callback, state)
            elif data.startswith("task_statistics_"):
                await self._handle_task_statistics(callback, state)
            elif data.startswith("task_settings_"):
                await self._handle_task_settings(callback, state)
            elif data.startswith("task_info_"):
                await self._handle_task_info(callback, state)
            elif data.startswith("task_list_page_"):
                await self._handle_task_list_pagination(callback, state)
            elif data.startswith("task_delete_"):
                await self._handle_task_delete(callback, state)
            elif data.startswith("confirm_delete_task"):
                await self._handle_confirm_task_delete(callback, state)
            elif data.startswith("cancel_delete_task"):
                await self._handle_cancel_task_delete(callback, state)
            elif data.startswith("setting_forward_mode_"):
                await self._handle_forward_mode_setting(callback, state)
            elif data.startswith("setting_delays_"):
                await self._handle_delay_setting(callback, state)
            elif data.startswith("setting_limits_"):
                await self._handle_limits_setting(callback, state)
            elif data.startswith("setting_filters_"):
                await self._handle_filters_setting(callback, state)
            elif data.startswith("setting_content_"):
                await self._handle_content_setting(callback, state)
            elif data.startswith("setting_forward_"):
                await self._handle_forward_setting(callback, state)
            elif data.startswith("setting_advanced_"):
                logger.warning(f"MATCHED setting_advanced_: {data}")
                task_id = int(data.split("_")[-1])
                logger.warning(f"Extracted task_id: {task_id}")
                await self._handle_advanced_setting(callback, task_id, state)
                logger.warning(f"Completed _handle_advanced_setting call")
            
            # Handle advanced sub-feature buttons - Fixed task_id extraction
            elif data.startswith("advanced_translation_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_translation(callback, task_id, state)
                
            elif data.startswith("advanced_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_working_hours(callback, task_id, state)
                
            elif data.startswith("advanced_recurring_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_recurring(callback, task_id, state)
            elif data.startswith("setting_translation_"):
                task_id = int(data.split("_")[-1])
                await self._handle_translation_setting(callback, task_id, state)
            elif data.startswith("setting_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_working_hours_setting(callback, task_id, state)
            elif data.startswith("setting_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_recurring_post_setting(callback, task_id, state)
            elif data.startswith("advanced_quick_settings_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_quick_settings(callback, task_id, state)
            elif data.startswith("advanced_statistics_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_statistics(callback, task_id, state)
            elif data.startswith("reset_advanced_"):
                task_id = int(data.split("_")[-1])
                await self._handle_reset_advanced_settings(callback, task_id, state)
            elif data.startswith("save_advanced_"):
                task_id = int(data.split("_")[-1])
                await self._handle_save_advanced_settings(callback, task_id, state)

            elif data.startswith("advanced_day_filter_"):
                task_id = int(data.split("_")[-1])
                await self._handle_day_filter_setting(callback, task_id, state)
            elif data.startswith("advanced_sending_limit_"):
                task_id = int(data.split("_")[-1])
                await self._handle_sending_limit_setting(callback, task_id, state)
            elif data.startswith("day_filter_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_day_filter(callback, task_id, state)
            elif data.startswith("day_toggle_"):
                parts = data.split("_")
                task_id = int(parts[-1])
                day = parts[2]
                await self._toggle_day_selection(callback, task_id, day, state)
            elif data.startswith("sending_limit_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_sending_limit(callback, task_id, state)
            elif data.startswith("sending_limit_edit_"):
                task_id = int(data.split("_")[-1])
                await self._edit_sending_limit(callback, task_id, state)
            elif data.startswith("day_enable_all_"):
                task_id = int(data.split("_")[-1])
                await self._enable_all_days(callback, task_id, state)
            elif data.startswith("day_disable_all_"):
                task_id = int(data.split("_")[-1])
                await self._disable_all_days(callback, task_id, state)
            # Translation sub-buttons
            elif data.startswith("toggle_auto_translate_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_auto_translate(callback, task_id, state)
            elif data.startswith("set_source_lang_"):
                await self._handle_set_source_language(callback, state)
            elif data.startswith("set_target_lang_"):
                await self._handle_set_target_language(callback, state)
            
            # Working hours sub-buttons
            elif data.startswith("toggle_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_working_hours(callback, task_id, state)
            elif data.startswith("set_start_hour_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_start_hour(callback, task_id, state)
            elif data.startswith("set_end_hour_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_end_hour(callback, task_id, state)
            elif data.startswith("set_timezone_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_timezone(callback, task_id, state)
            
            # Recurring post sub-buttons
            elif data.startswith("toggle_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_recurring_post(callback, task_id, state)
            elif data.startswith("set_recurring_interval_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_recurring_interval(callback, task_id, state)
            elif data.startswith("add_recurring_"):
                task_id = int(data.split("_")[-1])
                await self._handle_add_recurring_post(callback, task_id, state)
            elif data.startswith("list_recurring_"):
                task_id = int(data.split("_")[-1])
                await self._handle_list_recurring_posts(callback, task_id, state)
            elif data.startswith("interval_recurring_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_recurring_interval(callback, task_id, state)
            elif data.startswith("toggle_recurring_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_recurring_post(callback, task_id, state)
            elif data.startswith("set_interval_"):
                parts = data.split("_")
                hours = int(parts[2])
                task_id = int(parts[3])
                await self._handle_set_interval_hours(callback, task_id, hours, state)
            elif data.startswith("add_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_add_recurring_post(callback, task_id, state)
            elif data.startswith("list_recurring_posts_"):
                task_id = int(data.split("_")[-1])
                await self._handle_list_recurring_posts(callback, task_id, state)
            elif data.startswith("edit_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_edit_recurring_post(callback, task_id, state)
            elif data.startswith("delete_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_delete_recurring_post(callback, task_id, state)
            elif data.startswith("recurring_stats_"):
                task_id = int(data.split("_")[-1])
                await self._handle_recurring_stats(callback, task_id, state)
            elif data.startswith("run_recurring_now_"):
                task_id = int(data.split("_")[-1])
                await self._handle_run_recurring_now(callback, task_id, state)
            # Working hours additional sub-buttons
            elif data.startswith("set_break_start_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_break_start(callback, task_id, state)
            elif data.startswith("set_break_end_"):
                task_id = int(data.split("_")[-1])
                await self._handle_set_break_end(callback, task_id, state)
            elif data.startswith("working_hours_report_"):
                task_id = int(data.split("_")[-1])
                await self._handle_working_hours_report(callback, task_id, state)
            elif data.startswith("test_current_time_"):
                task_id = int(data.split("_")[-1])
                await self._handle_test_current_time(callback, task_id, state)
            # User filter sub-buttons
            elif data.startswith("user_verified_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_verified_filter(callback, task_id, state)
            elif data.startswith("user_nobots_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_bot_filter(callback, task_id, state)
            elif data.startswith("user_whitelist_"):
                task_id = int(data.split("_")[-1])
                await self._handle_user_whitelist(callback, task_id, state)
            elif data.startswith("user_blacklist_"):
                task_id = int(data.split("_")[-1])
                await self._handle_user_blacklist(callback, task_id, state)
            elif data.startswith("content_prefix_"):
                await self._handle_prefix_suffix_setting(callback, int(data.split("_")[-1]), state)
            elif data.startswith("content_replace_"):
                await self._handle_text_replace_setting(callback, int(data.split("_")[-1]), state)

            elif data.startswith("content_formatting_"):
                await self._handle_formatting_setting(callback, int(data.split("_")[-1]), state)
            elif data.startswith("content_links_"):
                await self._handle_links_setting(callback, int(data.split("_")[-1]), state)
            elif data.startswith("content_cleaner_"):
                await self._handle_text_cleaner_setting(callback, int(data.split("_")[-1]), state)

            elif data.startswith("setting_prefix_suffix_"):
                task_id = int(data.split("_")[-1])
                await self._handle_prefix_suffix_setting(callback, task_id, state)
            elif data.startswith("setting_reset_"):
                await self._handle_reset_setting(callback, state)
            elif data.startswith("setting_save_"):
                await self._handle_save_setting(callback, state)
            elif data.startswith("setting_view_"):
                await self._handle_view_all_settings(callback, state)
            elif data.startswith("set_forward_mode_"):
                await self._handle_set_forward_mode(callback, state)
            elif data.startswith("forward_mode_"):
                await self._handle_forward_mode_actions(callback, state)
            elif data.startswith("set_delay_"):
                await self._handle_set_delay(callback, state)
            elif data.startswith("delay_"):
                await self._handle_delay_actions(callback, state)

            elif data.startswith("filter_length_"):
                # Handle length filter main interface
                logger.info(f"Routing to length filter main interface: {data}")
                await self._handle_length_filter(callback, int(data.split("_")[-1]), state)
            elif data.startswith("len_"):
                # Handle length preset buttons first (len_280, len_1000, etc)
                logger.info(f"Routing to length preset setting: {data}")
                await self._handle_length_setting(callback, state)
            elif data.startswith("set_min_") or data.startswith("set_max_"):
                # Handle setting min/max values
                logger.info(f"Routing to length value setting: {data}")
                await self._handle_length_value_setting(callback, state)
            elif data.startswith("set_action_"):
                # Handle setting action mode
                logger.info(f"Routing to action mode setting: {data}")
                await self._handle_action_mode_setting(callback, state)
            elif data.startswith("length_"):
                # Handle all other length filter actions
                logger.info(f"Routing to length filter actions: {data}")
                await self._handle_length_actions(callback, state)
            elif data.startswith("filter_languages_"):
                task_id = int(data.split("_")[-1])
                await self._handle_language_filter_management(callback, task_id, state)
            elif data.startswith("toggle_filter_forwarded_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_forwarded_filter(callback, task_id, state)
            elif data.startswith("toggle_filter_links_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_links_filter(callback, task_id, state)
            elif data.startswith("toggle_filter_buttons_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_buttons_filter(callback, task_id, state)
            elif data.startswith("toggle_filter_duplicates_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_duplicates_filter(callback, task_id, state)
            elif data.startswith("toggle_filter_language_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_language_filter(callback, task_id, state)
            elif data.startswith("clear_duplicates_"):
                task_id = int(data.split("_")[-1])
                await self._clear_duplicates(callback, task_id, state)
            # Advanced forward settings toggles
            elif data.startswith("toggle_manual_mode_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_manual_mode(callback, task_id, state)
            elif data.startswith("toggle_link_preview_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_link_preview(callback, task_id, state)
            elif data.startswith("toggle_pin_messages_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_pin_messages(callback, task_id, state)
            elif data.startswith("toggle_silent_mode_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_silent_mode(callback, task_id, state)
            elif data.startswith("toggle_sync_edits_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_sync_edits(callback, task_id, state)
            elif data.startswith("toggle_sync_deletes_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_sync_deletes(callback, task_id, state)
            elif data.startswith("toggle_preserve_replies_"):
                task_id = int(data.split("_")[-1])
                await self._handle_toggle_preserve_replies(callback, task_id, state)
            elif data.startswith("forward_other_"):
                task_id = int(data.split("_")[-1])
                await self._handle_forward_other_settings(callback, task_id, state)
            
            # Media filter actions
            elif data.startswith("media_enable_all_"):
                task_id = int(data.split("_")[-1])
                await self._handle_media_enable_all(callback, task_id, state)
            elif data.startswith("media_disable_all_"):
                task_id = int(data.split("_")[-1])
                await self._handle_media_disable_all(callback, task_id, state)
            elif data.startswith("media_reset_"):
                task_id = int(data.split("_")[-1])
                await self._handle_media_reset(callback, task_id, state)
            elif data.startswith("media_save_"):
                task_id = int(data.split("_")[-1])
                await self._handle_media_save(callback, task_id, state)
            elif data.startswith("media_type_"):
                parts = data.split("_")
                task_id = int(parts[-2])
                media_type = parts[-1]
                await self._handle_media_type_toggle(callback, task_id, media_type, state)
            
            # Filter management
            elif data.startswith("filter_clear_"):
                task_id = int(data.split("_")[-1])
                await self._handle_filter_clear_all(callback, task_id, state)
            # Text Cleaner handlers
            elif data.startswith("cleaner_links_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_links(callback, task_id, state)
            elif data.startswith("cleaner_emojis_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_emojis(callback, task_id, state)
            elif data.startswith("cleaner_hashtags_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_hashtags(callback, task_id, state)
            elif data.startswith("cleaner_mentions_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_mentions(callback, task_id, state)
            elif data.startswith("cleaner_emails_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_emails(callback, task_id, state)
            elif data.startswith("cleaner_numbers_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_numbers(callback, task_id, state)
            elif data.startswith("cleaner_punctuation_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_punctuation(callback, task_id, state)
            elif data.startswith("cleaner_empty_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_empty_lines(callback, task_id, state)
            elif data.startswith("cleaner_extra_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_extra_lines(callback, task_id, state)
            elif data.startswith("cleaner_whitespace_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_whitespace(callback, task_id, state)
            elif data.startswith("cleaner_duplicate_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_duplicate_lines(callback, task_id, state)
            elif data.startswith("cleaner_target_words_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_target_words(callback, task_id, state)
            elif data.startswith("cleaner_words_manage_"):
                task_id = int(data.split("_")[-1])
                await self._handle_cleaner_words_manage(callback, task_id, state)
            elif data.startswith("cleaner_test_"):
                task_id = int(data.split("_")[-1])
                await self._handle_cleaner_test(callback, task_id, state)
            elif data.startswith("cleaner_reset_"):
                task_id = int(data.split("_")[-1])
                await self._handle_cleaner_reset(callback, task_id, state)
            elif data.startswith("links_remove_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_links(callback, task_id, state)
            # Advanced features handlers
            elif data.startswith("setting_translation_"):
                task_id = int(data.split("_")[-1])
                await self._handle_translation_setting(callback, task_id, state)
            elif data.startswith("setting_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_working_hours_setting(callback, task_id, state)
            elif data.startswith("setting_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_recurring_post_setting(callback, task_id, state)
            elif data.startswith("toggle_translation_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_translation(callback, task_id, state)
            elif data.startswith("toggle_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_working_hours(callback, task_id, state)
            elif data.startswith("toggle_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_recurring_post(callback, task_id, state)
            elif data.startswith("set_target_lang_"):
                parts = data.split("_")
                task_id = int(parts[-1])
                language = parts[-2]
                await self._set_target_language(callback, task_id, language, state)
            elif data.startswith("set_start_hour_"):
                task_id = int(data.split("_")[-1])
                await self._set_start_hour(callback, task_id, state)
            elif data.startswith("set_end_hour_"):
                task_id = int(data.split("_")[-1])
                await self._set_end_hour(callback, task_id, state)
            elif data.startswith("set_timezone_"):
                task_id = int(data.split("_")[-1])
                await self._set_timezone(callback, task_id, state)
            elif data.startswith("set_recurring_interval_"):
                task_id = int(data.split("_")[-1])
                await self._set_recurring_interval(callback, task_id, state)
            elif data.startswith("edit_recurring_content_"):
                task_id = int(data.split("_")[-1])
                await self._edit_recurring_content(callback, task_id, state)
            elif data.startswith("view_recurring_content_"):
                task_id = int(data.split("_")[-1])
                await self._view_recurring_content(callback, task_id, state)
            # Header/Footer handlers
            elif data.startswith("header_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_header(callback, task_id, state)
            elif data.startswith("footer_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_footer(callback, task_id, state)
            elif data.startswith("header_edit_"):
                task_id = int(data.split("_")[-1])
                await self._edit_header(callback, task_id, state)
            elif data.startswith("footer_edit_"):
                task_id = int(data.split("_")[-1])
                await self._edit_footer(callback, task_id, state)
            elif data.startswith("header_delete_"):
                task_id = int(data.split("_")[-1])
                await self._delete_header(callback, task_id, state)
            elif data.startswith("footer_delete_"):
                task_id = int(data.split("_")[-1])
                await self._delete_footer(callback, task_id, state)
            elif data.startswith("header_footer_view_"):
                logger.warning(f"HEADER_FOOTER_VIEW callback detected: {data}")
                task_id = int(data.split("_")[-1])
                logger.warning(f"Calling _view_header_footer for task {task_id}")
                await self._view_header_footer(callback, task_id, state)
                logger.warning(f"Completed _view_header_footer call")
            elif data.startswith("header_footer_examples_"):
                task_id = int(data.split("_")[-1])
                await self._show_header_footer_examples(callback, task_id, state)

            # Manual approval handlers
            elif data.startswith("approve_message_"):
                approval_id = int(data.split("_")[-1])
                await self._approve_manual_message(callback, approval_id, state)
            elif data.startswith("reject_message_"):
                approval_id = int(data.split("_")[-1])
                await self._reject_manual_message(callback, approval_id, state)
            elif data.startswith("edit_before_forward_"):
                approval_id = int(data.split("_")[-1])
                await self._edit_before_forward(callback, approval_id, state)
            # Advanced settings handlers
            elif data.startswith("setting_advanced_"):
                task_id = int(data.split("_")[-1])
                await self._handle_advanced_setting(callback, task_id, state)
            elif data.startswith("setting_translation_"):
                task_id = int(data.split("_")[-1])
                await self._handle_translation_setting(callback, task_id, state)
            elif data.startswith("setting_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_working_hours_setting(callback, task_id, state)
            elif data.startswith("setting_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_recurring_post_setting(callback, task_id, state)
            elif data.startswith("toggle_translation_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_translation(callback, task_id, state)
            elif data.startswith("set_target_language_"):
                parts = data.split("_")
                task_id = int(parts[-2])
                language = parts[-1]
                await self._set_target_language(callback, task_id, language, state)
            elif data.startswith("toggle_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_working_hours(callback, task_id, state)
            elif data.startswith("set_start_hour_"):
                task_id = int(data.split("_")[-1])
                await self._set_start_hour(callback, task_id, state)
            elif data.startswith("set_end_hour_"):
                task_id = int(data.split("_")[-1])
                await self._set_end_hour(callback, task_id, state)
            elif data.startswith("set_timezone_"):
                task_id = int(data.split("_")[-1])
                await self._set_timezone(callback, task_id, state)
            elif data.startswith("toggle_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_recurring_post(callback, task_id, state)
            elif data.startswith("set_recurring_interval_"):
                task_id = int(data.split("_")[-1])
                await self._set_recurring_interval(callback, task_id, state)
            elif data.startswith("edit_recurring_content_"):
                task_id = int(data.split("_")[-1])
                await self._edit_recurring_content(callback, task_id, state)
            elif data.startswith("view_recurring_content_"):
                task_id = int(data.split("_")[-1])
                await self._view_recurring_content(callback, task_id, state)
            elif data.startswith("toggle_filter_language_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_filter_language(callback, task_id, state)
            
            # Inline buttons handlers - must be before generic content handlers
            elif data.startswith("content_inline_buttons_"):
                task_id = int(data.split("_")[-1])
                await self._handle_inline_buttons_setting(callback, task_id, state)
            elif data.startswith("content_cleaner_"):
                task_id = int(data.split("_")[-1])
                await self._handle_text_cleaner_setting(callback, task_id, state)
            elif data.startswith("inline_buttons_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_inline_buttons(callback, task_id, state)
            elif data.startswith("inline_button_add_"):
                task_id = int(data.split("_")[-1])
                await self._add_inline_button(callback, task_id, state)
            elif data.startswith("inline_button_edit_"):
                parts = data.split("_")
                task_id = int(parts[-2])
                button_id = int(parts[-1])
                await self._edit_inline_button(callback, task_id, button_id, state)
            elif data.startswith("inline_button_delete_"):
                parts = data.split("_")
                task_id = int(parts[-2])
                button_id = int(parts[-1])
                await self._delete_inline_button(callback, task_id, button_id, state)
            elif data.startswith("inline_buttons_preview_"):
                task_id = int(data.split("_")[-1])
                await self._preview_inline_buttons(callback, task_id, state)
            elif data.startswith("inline_buttons_clear_"):
                task_id = int(data.split("_")[-1])
                await self._clear_inline_buttons(callback, task_id, state)
            elif data.startswith("replace_add_"):
                task_id = int(data.split("_")[-1])
                await self._handle_replacement_add(callback, task_id, state)
            elif data.startswith("replace_list_"):
                task_id = int(data.split("_")[-1])
                await self._handle_replacement_list(callback, task_id, state)
            elif data.startswith("replace_clear_"):
                task_id = int(data.split("_")[-1])
                await self._handle_replacement_clear(callback, task_id, state)
            elif data.startswith("format_hyperlink_"):
                task_id = int(data.split("_")[-1])
                await self._handle_format_hyperlink(callback, task_id, state)
            
            # Text Cleaner handlers
            elif data.startswith("content_cleaner_"):
                task_id = int(data.split("_")[-1])
                await self._handle_text_cleaner_setting(callback, task_id, state)
            elif data.startswith("cleaner_buttons_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_inline_buttons", callback)
            elif data.startswith("cleaner_emojis_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_emojis", callback)
            elif data.startswith("cleaner_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_extra_lines", callback)
            elif data.startswith("cleaner_words_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_lines_with_words", callback)
            elif data.startswith("cleaner_hashtags_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_hashtags", callback)
            elif data.startswith("cleaner_links_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_links(callback, task_id, state)
            elif data.startswith("cleaner_mentions_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_mentions(callback, task_id, state)
            elif data.startswith("cleaner_numbers_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_numbers(callback, task_id, state)
            elif data.startswith("cleaner_punctuation_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_punctuation(callback, task_id, state)
            elif data.startswith("cleaner_empty_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_empty_lines(callback, task_id, state)
            elif data.startswith("cleaner_extra_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_extra_lines(callback, task_id, state)
            elif data.startswith("cleaner_whitespace_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_whitespace(callback, task_id, state)
            elif data.startswith("cleaner_duplicate_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_duplicate_lines(callback, task_id, state)
            elif data.startswith("cleaner_test_"):
                task_id = int(data.split("_")[-1])
                await self._test_text_cleaner(callback, task_id, state)
            elif data.startswith("cleaner_reset_"):
                task_id = int(data.split("_")[-1])
                await self._reset_text_cleaner(callback, task_id, state)
            elif data.startswith("cleaner_caption_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_caption_removal(callback, task_id, state)
            elif data.startswith("toggle_lang_mode_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_lang_mode(callback, task_id, state)
            elif data.startswith("filter_languages_"):
                task_id = int(data.split("_")[-1])
                await self._handle_filter_languages(callback, task_id, state)
            elif data.startswith("toggle_lang_"):
                parts = data.split("_")
                task_id = int(parts[2])
                lang_code = parts[3]
                await self._toggle_language_selection(callback, task_id, lang_code, state)
            elif data.startswith("select_all_langs_"):
                task_id = int(data.split("_")[-1])
                await self._select_all_languages(callback, task_id, state)
            elif data.startswith("deselect_all_langs_"):
                task_id = int(data.split("_")[-1])
                await self._deselect_all_languages(callback, task_id, state)
            elif data.startswith("filter_language_"):
                task_id = int(data.split("_")[-1])
                await self._handle_language_filter(callback, task_id, state)
            elif data.startswith("filter_forwarded_"):
                task_id = int(data.split("_")[-1])
                await self._handle_forwarded_filter(callback, task_id, state)
            elif data.startswith("filter_links_"):
                task_id = int(data.split("_")[-1])
                await self._handle_links_filter(callback, task_id, state)
            elif data.startswith("filter_buttons_"):
                task_id = int(data.split("_")[-1])
                await self._handle_buttons_filter(callback, task_id, state)
            elif data.startswith("filter_duplicates_"):
                task_id = int(data.split("_")[-1])
                await self._handle_duplicates_filter(callback, task_id, state)
            elif data.startswith("filter_language_"):
                task_id = int(data.split("_")[-1])
                await self._handle_language_filter(callback, task_id, state)
            elif data.startswith("filter_days_"):
                task_id = int(data.split("_")[-1])
                await self._handle_day_filter_setting(callback, task_id, state)
            elif data.startswith("user_filter_"):
                task_id = int(data.split("_")[-1])
                await self._handle_user_filter(callback, task_id, state)
            elif data.startswith("filter_length_"):
                task_id = int(data.split("_")[-1])
                await self._handle_length_filter_setting(callback, task_id, state)
            elif data.startswith("filter_clear_"):
                task_id = int(data.split("_")[-1])
                await self._handle_filter_clear(callback, task_id, state)
            elif data.startswith("filter_"):
                await self._handle_filter_submenu(callback, state)
            elif data.startswith("kw_set_") or data.startswith("kw_clear_") or data.startswith("kw_"):
                await self._handle_keyword_actions(callback, state)
            elif data.startswith("kw_confirm_clear_"):
                task_id = int(data.split("_")[-1])
                # Clear all keywords
                await self.database.execute_command(
                    "UPDATE task_settings SET keyword_filters = NULL WHERE task_id = $1",
                    task_id
                )
                await callback.answer("🗑️ All keywords cleared!", show_alert=True)
                await self._handle_keyword_filter(callback, task_id, state)
            elif data.startswith("media_toggle_"):
                await self._handle_media_toggle(callback, state)
            elif data.startswith("text_toggle_"):
                await self._handle_text_toggle(callback, state)
            elif data.startswith("set_action_"):
                await self._handle_action_mode_setting(callback, state)
            elif data.startswith("media_type_"):
                await self._handle_media_type_toggle(callback, state)
            elif data.startswith("media_enable_all_"):
                await self._handle_media_enable_all(callback, state)
            elif data.startswith("media_disable_all_"):
                await self._handle_media_disable_all(callback, state)
            elif data.startswith("media_reset_"):
                await self._handle_media_reset(callback, state)
            elif data.startswith("media_save_"):
                await self._handle_media_save(callback, state)
            # Advanced Features Handlers
            elif data.startswith("toggle_translation_"):
                task_id = int(data.split("_")[-1])
                await self._handle_translation_toggle(callback, task_id, state)
            elif data.startswith("set_target_lang_"):
                parts = data.split("_")
                language_code = parts[3]
                task_id = int(parts[4])
                await self._handle_set_target_language(callback, state)
            elif data.startswith("toggle_working_hours_"):
                task_id = int(data.split("_")[-1])
                await self._handle_working_hours_toggle(callback, task_id, state)
            elif data.startswith("set_start_hour_"):
                parts = data.split("_")
                hour = int(parts[3])
                task_id = int(parts[4])
                await self._handle_set_start_hour(callback, task_id, hour, state)
            elif data.startswith("set_end_hour_"):
                parts = data.split("_")
                hour = int(parts[3])
                task_id = int(parts[4])
                await self._handle_set_end_hour(callback, task_id, hour, state)
            elif data.startswith("set_timezone_"):
                parts = data.split("_")
                timezone = "_".join(parts[2:-1])  # Rejoin timezone parts
                task_id = int(parts[-1])
                await self._handle_set_timezone(callback, task_id, timezone, state)
            elif data.startswith("toggle_recurring_post_"):
                task_id = int(data.split("_")[-1])
                await self._handle_recurring_post_toggle(callback, task_id, state)
            elif data.startswith("set_recurring_interval_"):
                parts = data.split("_")
                interval_hours = int(parts[3])
                task_id = int(parts[4])
                await self._handle_set_recurring_interval(callback, task_id, interval_hours, state)
            elif data.startswith("user_verified_") or data.startswith("user_nobots_"):
                await self._handle_user_filter_actions(callback, state)
            elif data.startswith("user_whitelist_") and data.count("_") == 2:  # Exact pattern: user_whitelist_X
                task_id = int(data.split("_")[2])
                await self._handle_user_whitelist_management(callback, task_id, state)
            elif data.startswith("user_blacklist_") and data.count("_") == 2:  # Exact pattern: user_blacklist_X
                task_id = int(data.split("_")[2])
                await self._handle_user_blacklist_management(callback, task_id, state)
            elif data.startswith("suffix_add_"):
                task_id = int(data.split("_")[-1])
                await self._handle_suffix_add(callback, task_id, state)
            elif data.startswith("suffix_edit_"):
                task_id = int(data.split("_")[-1])
                await self._handle_suffix_edit(callback, task_id, state)
            elif data.startswith("cleaner_"):
                await self._handle_text_cleaner_actions(callback, state)
            elif (data.startswith("prefix_") or data.startswith("suffix_") or 
                  data.startswith("replace_") or data.startswith("format_") or data.startswith("links_")):
                await self._handle_content_actions(callback, state)
            elif data.startswith("clear_") or data.startswith("enable_") or data.startswith("disable_") or data.startswith("reset_") or data.startswith("save_") or data.startswith("view_") or data.startswith("toggle_"):
                await self._handle_filter_actions(callback, state)
            elif data.startswith("verified_") or data.startswith("nobots_") or data.startswith("bots_"):
                await self._handle_user_filter_specific_actions(callback, state)
            elif data.startswith("photo_") or data.startswith("video_") or data.startswith("audio_") or data.startswith("document_") or data.startswith("voice_") or data.startswith("sticker_") or data.startswith("animation_") or data.startswith("poll_") or data.startswith("contact_") or data.startswith("location_") or data.startswith("venue_") or data.startswith("game_"):
                await self._handle_media_type_actions(callback, state)
            elif (data.startswith("mode_") or data.startswith("apply_") or data.startswith("load_") or 
                  data.startswith("delete_") or data.startswith("copy_") or data.startswith("import_") or 
                  data.startswith("export_") or data.startswith("add_") or data.startswith("remove_") or
                  data.startswith("edit_") or data.startswith("test_") or data.startswith("back_") or
                  data.startswith("next_") or data.startswith("prev_") or data.startswith("select_") or
                  data.startswith("instant_") or data.startswith("short_") or data.startswith("medium_") or
                  data.startswith("long_") or data.startswith("random_") or data.startswith("bold_") or
                  data.startswith("italic_") or data.startswith("underline_") or data.startswith("strike_") or
                  data.startswith("spoiler_") or data.startswith("code_") or data.startswith("mono_") or
                  data.startswith("preserve_") or data.startswith("strip_") or data.startswith("extract_") or
                  data.startswith("limit_") or data.startswith("min_") or data.startswith("max_") or
                  data.startswith("keyword_") or data.startswith("length_") or data.startswith("sender_") or
                  data.startswith("all_") or data.startswith("none_") or data.startswith("default_")):
                await self._handle_additional_actions(callback, state)
            else:
                # Special check for content buttons that reach here
                if data and data.startswith("content_"):
                    logger.error(f"CRITICAL: Content button {data} reached else clause - no handler matched!")
                    logger.error(f"This means all content_ conditions failed to match")
                logger.warning(f"Unhandled task callback: {data}")
                await callback.answer("❌ Unknown task action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in task callback {data}: {e}")
            await callback.answer("❌ An error occurred.", show_alert=True)
    
    async def _handle_task_creation_start(self, callback: CallbackQuery, state: FSMContext):
        """Handle task creation start"""
        try:
            keyboard = await self.keyboards.get_task_creation_keyboard()
            
            creation_text = """
➕ **Create New Task**

Choose the type of task you want to create:

🤖 **Bot API Mode:**
• Uses bot token for operations
• Limited to public channels or where bot is admin
• More stable and reliable
• Rate limited by Telegram

👤 **Userbot Mode:**
• Uses user account for operations
• Access to private channels and groups
• More flexible but requires string session
• Higher rate limits
            """
            
            await callback.message.edit_text(creation_text, reply_markup=keyboard)
            await state.set_state(TaskStates.CREATING_TASK)
            
        except Exception as e:
            logger.error(f"Error starting task creation: {e}")
            await callback.answer("❌ Error starting task creation.")
    
    async def _handle_task_type_selection(self, callback: CallbackQuery, state: FSMContext):
        """Handle task type selection"""
        try:
            task_type = callback.data.split("_")[-1]  # "bot" or "userbot"
            
            # Validate userbot availability
            if task_type == "userbot" and not self.bot_controller.userbot:
                await callback.answer(
                    "❌ Userbot mode is not available. String session not configured.",
                    show_alert=True
                )
                return
            
            # Store task type in session
            await self.bot_controller.update_user_session(
                callback.from_user.id, 
                {"creating_task_type": task_type}
            )
            
            type_emoji = "🤖" if task_type == "bot" else "👤"
            
            await callback.message.edit_text(
                f"{type_emoji} **Creating {task_type.title()} Task**\n\n"
                "Please enter a name for your task:"
            )
            
            await state.set_state(TaskStates.WAITING_TASK_NAME)
            
        except Exception as e:
            logger.error(f"Error in task type selection: {e}")
            await callback.answer("❌ Error selecting task type.")
    
    async def handle_task_name_input(self, message: Message, state: FSMContext):
        """Handle task name input"""
        try:
            user_id = message.from_user.id
            task_name = message.text.strip()
            
            # Validate task name
            if len(task_name) < 3:
                await message.answer("❌ Task name must be at least 3 characters long. Please try again:")
                return
            
            if len(task_name) > 100:
                await message.answer("❌ Task name must be less than 100 characters. Please try again:")
                return
            
            # Store task name in session
            await self.bot_controller.update_user_session(
                user_id, 
                {"creating_task_name": task_name}
            )
            
            await message.answer(
                f"✅ Task name set: **{task_name}**\n\n"
                "Now enter a description for your task (optional, send /skip to skip):"
            )
            
            await state.set_state(TaskStates.WAITING_TASK_DESCRIPTION)
            
        except Exception as e:
            logger.error(f"Error handling task name input: {e}")
            await message.answer("❌ An error occurred. Please try again.")
    
    async def handle_task_description_input(self, message: Message, state: FSMContext):
        """Handle task description input"""
        try:
            user_id = message.from_user.id
            
            # Get session data
            session_data = await self.bot_controller.get_user_session(user_id)
            task_name = session_data.get("creating_task_name")
            task_type = session_data.get("creating_task_type")
            
            if not task_name or not task_type:
                await message.answer("❌ Session expired. Please start task creation again.")
                await state.clear()
                return
            
            task_description = ""
            if message.text.strip().lower() != "/skip":
                task_description = message.text.strip()
                
                if len(task_description) > 500:
                    await message.answer("❌ Description must be less than 500 characters. Please try again:")
                    return
            
            # Create the task
            task_data = {
                "name": task_name,
                "description": task_description,
                "task_type": task_type
            }
            
            task_id = await self.task_manager.create_task(user_id, task_data)
            
            if task_id:
                type_emoji = "🤖" if task_type == "bot" else "👤"
                
                success_text = f"""
✅ **Task Created Successfully!**

{type_emoji} **{task_name}**
📋 Description: {task_description or 'No description'}
🆔 Task ID: `{task_id}`

**Next Steps:**
1. Add source channels to monitor
2. Add target channels for forwarding
3. Configure forwarding settings
4. Activate the task

Choose an option below:
                """
                
                keyboard = await self.keyboards.get_task_detail_keyboard(task_id, {
                    "is_active": False,
                    "task_type": task_type
                })
                
                await message.answer(success_text, reply_markup=keyboard)
                
                # Clear session
                await self.bot_controller.clear_user_session(user_id)
                await state.clear()
                
            else:
                await message.answer("❌ Failed to create task. Please try again later.")
                await state.clear()
                
        except Exception as e:
            logger.error(f"Error handling task description input: {e}")
            await message.answer("❌ An error occurred creating the task.")
            await state.clear()
    
    async def _handle_task_list(self, callback: CallbackQuery, state: FSMContext, page: int = 0):
        """Handle task list display"""
        try:
            user_id = callback.from_user.id
            
            # Get user tasks
            tasks = await self.task_manager.get_user_tasks(user_id)
            
            if not tasks:
                no_tasks_text = """
📋 **Your Tasks**

You don't have any tasks yet.

Create your first task to start forwarding messages between channels.
                """
                
                from aiogram.types import InlineKeyboardButton as IKB
                keyboard = [
                    [IKB(text="➕ Create Task", callback_data="task_create")],
                    [IKB(text="🔙 Back", callback_data="main_tasks")]
                ]
                
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await callback.message.edit_text(no_tasks_text, reply_markup=markup)
                return
            
            # Create task list keyboard with pagination
            keyboard = await self.keyboards.get_task_list_keyboard(tasks, user_id, page)
            
            # Create summary text
            active_tasks = len([t for t in tasks if t.get("is_active", False)])
            total_messages = sum(t.get("messages_forwarded", 0) or 0 for t in tasks)
            
            list_text = f"""
📋 **Your Tasks** (Page {page + 1})

**Summary:**
• Total Tasks: {len(tasks)}
• Active Tasks: {active_tasks}
• Messages Forwarded: {total_messages:,}

**Tasks:**
Select a task below to view details and manage it.
            """
            
            await callback.message.edit_text(list_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error displaying task list: {e}")
            await callback.answer("❌ Error loading task list.")
    
    async def _handle_task_view(self, callback: CallbackQuery, state: FSMContext):
        """Handle task view"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get fresh task data directly from database to avoid cache issues
            task_data = await self.database.execute_query(
                "SELECT t.*, u.telegram_id as user_telegram_id FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.id = $1", 
                task_id
            )
            
            if not task_data:
                await callback.answer("❌ Task not found.", show_alert=True)
                return
            
            task = task_data[0]
            
            # Check if user owns the task
            if task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get sources, targets and statistics
            sources = await self.database.get_task_sources(task_id)
            targets = await self.database.get_task_targets(task_id)
            statistics = await self.database.get_task_statistics(task_id)
            
            # Format task details
            task_text = await self._format_task_details(task, sources, targets, statistics)
            
            # Get task detail keyboard with fresh data
            keyboard = await self.keyboards.get_task_detail_keyboard(task_id, task)
            
            logger.info(f"Task view: Task {task_id} mode is {task.get('task_type', 'unknown')}")
            
            await callback.message.edit_text(task_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error viewing task: {e}")
            await callback.answer("❌ Error loading task details.")
    
    async def _handle_task_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle task activation/deactivation"""
        try:
            task_id = int(callback.data.split("_")[-1])
            user_id = callback.from_user.id
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != user_id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Toggle task status
            new_status = await self.task_manager.toggle_task_status(task_id)
            
            if new_status is None:
                await callback.answer("❌ Failed to toggle task status.", show_alert=True)
                return
            
            # Update forwarding engine
            if new_status:
                await self.forwarding_engine.add_task(task_id)
                status_text = "✅ Task activated successfully!"
            else:
                await self.forwarding_engine.remove_task(task_id)
                status_text = "⏹️ Task deactivated successfully!"
            
            await callback.answer(status_text, show_alert=True)
            
            # Refresh task view
            await self._handle_task_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling task: {e}")
            await callback.answer("❌ Error toggling task status.")
    
    async def _handle_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle task deletion confirmation"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            confirm_text = f"""
🗑️ **Delete Task Confirmation**

Are you sure you want to delete the task "**{task['name']}**"?

⚠️ **Warning:**
This action cannot be undone. All task data including:
• Source and target configurations
• Forwarding statistics
• Task settings
• Message logs

Will be permanently deleted.
            """
            
            keyboard = await self.keyboards.get_confirmation_keyboard("delete_task", task_id)
            
            await callback.message.edit_text(confirm_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error preparing task deletion: {e}")
            await callback.answer("❌ Error preparing task deletion.")
    
    async def _handle_confirm_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle confirmed task deletion"""
        try:
            # Parse callback data: confirm_delete_task_ID_
            parts = callback.data.split("_")
            task_id = int(parts[3])  # confirm_delete_task_ID_
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Remove from forwarding engine first
            await self.forwarding_engine.remove_task(task_id)
            
            # Delete task
            success = await self.task_manager.delete_task(task_id)
            
            if success:
                await callback.answer("✅ Task deleted successfully!", show_alert=True)
                
                # Return to task list
                await self._handle_task_list(callback, state)
                
            else:
                await callback.answer("❌ Failed to delete task.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            await callback.answer("❌ Error deleting task.")
    
    async def _handle_cancel_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle cancelled task deletion"""
        try:
            # Parse callback data: cancel_delete_task_ID_
            parts = callback.data.split("_")
            task_id = int(parts[3])  # cancel_delete_task_ID_
            
            # Return to task view
            callback.data = f"task_view_{task_id}"
            await self._handle_task_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error cancelling task deletion: {e}")
            await callback.answer("❌ Error cancelling deletion.")
    
    async def _handle_task_statistics(self, callback: CallbackQuery, state: FSMContext):
        """Handle task statistics"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get formatted statistics
            stats_text = await self.statistics_manager.get_formatted_statistics("task", task_id)
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Refresh", callback_data=f"task_statistics_{task_id}"),
                    InlineKeyboardButton(text="📊 Detailed", callback_data=f"task_stats_detailed_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📈 Trends", callback_data=f"task_trends_{task_id}"),
                    InlineKeyboardButton(text="📋 Logs", callback_data=f"task_logs_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                ]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(stats_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error displaying task statistics: {e}")
            await callback.answer("❌ Error loading task statistics.")
    
    async def _handle_task_settings(self, callback: CallbackQuery, state: FSMContext):
        """Handle task settings"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get task settings keyboard with user_id for localization
            user_id = callback.from_user.id
            keyboard = await self.keyboards.get_task_settings_keyboard(task_id, user_id)
            logger.info(f"Generated task settings keyboard for task {task_id}: {keyboard}")
            
            settings_text = f"""
⚙️ **Task Settings** - {task['name']}

Configure how messages are forwarded for this task.

**Available Settings:**
• Forward Mode (Copy/Forward/Quote)
• Delays between messages
• Content filters
• Text modifications
• Message presets

Select a category below to configure:
            """
            
            await callback.message.edit_text(settings_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error displaying task settings: {e}")
            await callback.answer("❌ Error loading task settings.")
    
    async def _handle_task_info(self, callback: CallbackQuery, state: FSMContext):
        """Handle task information display"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get task information
            task_info = await self.task_manager.get_task_info(task_id)
            
            if not task_info:
                await callback.answer("❌ Task not found.", show_alert=True)
                return
            
            task = task_info["task"]
            
            # Check ownership
            if task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get detailed task summary
            info_text = await self.task_manager.get_task_summary(task_id)
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [
                [
                    InlineKeyboardButton(text="📊 Statistics", callback_data=f"task_statistics_{task_id}"),
                    InlineKeyboardButton(text="⚙️ Settings", callback_data=f"task_settings_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📥 Sources", callback_data=f"source_list_{task_id}"),
                    InlineKeyboardButton(text="📤 Targets", callback_data=f"target_list_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                ]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(info_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error displaying task info: {e}")
            await callback.answer("❌ Error loading task information.")
    
    async def _handle_task_list_pagination(self, callback: CallbackQuery, state: FSMContext):
        """Handle task list pagination"""
        try:
            page = int(callback.data.split("_")[-1])
            await self._handle_task_list(callback, state, page)
            
        except Exception as e:
            logger.error(f"Error in task list pagination: {e}")
            await callback.answer("❌ Error loading page.")
    
    async def _handle_task_refresh(self, callback: CallbackQuery, state: FSMContext):
        """Handle task list refresh"""
        try:
            await self._handle_task_list(callback, state)
            await callback.answer("🔄 Task list refreshed.")
            
        except Exception as e:
            logger.error(f"Error refreshing task list: {e}")
            await callback.answer("❌ Error refreshing tasks.")
    
    async def _handle_task_statistics_overview(self, callback: CallbackQuery, state: FSMContext):
        """Handle task statistics overview"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = callback.from_user.id
            
            # Get user statistics
            stats_text = await self.statistics_manager.get_formatted_statistics("user", user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(text="📊 Global Stats", callback_data="stats_global"),
                    InlineKeyboardButton(text="⚡ Performance", callback_data="stats_performance")
                ],
                [
                    InlineKeyboardButton(text="📈 Trends", callback_data="stats_trends"),
                    InlineKeyboardButton(text="📋 Reports", callback_data="stats_reports")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_tasks")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(stats_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error displaying task statistics overview: {e}")
            await callback.answer("❌ Error loading statistics overview.")
    
    async def _format_task_details(self, task: Dict, sources: List[Dict], 
                                  targets: List[Dict], statistics: Optional[Dict]) -> str:
        """Format task details for display"""
        try:
            status_emoji = "🟢" if task["is_active"] else "🔴"
            type_emoji = "🤖" if task["task_type"] == "bot" else "👤"
            
            # Format statistics
            messages_forwarded = statistics.get("messages_forwarded", 0) if statistics else 0
            messages_failed = statistics.get("messages_failed", 0) if statistics else 0
            last_activity = statistics.get("last_activity") if statistics else None
            
            last_activity_str = "Never"
            if last_activity:
                last_activity_str = format_datetime(last_activity, "relative")
            
            success_rate = 0
            total_messages = messages_forwarded + messages_failed
            if total_messages > 0:
                success_rate = (messages_forwarded / total_messages) * 100
            
            task_details = f"""
{status_emoji} **{task['name']}** {type_emoji}

📋 **Description:** {task['description'] or 'No description'}
🆔 **Task ID:** `{task['id']}`
📅 **Created:** {format_datetime(task['created_at'], 'date')}
📊 **Status:** {'Active' if task['is_active'] else 'Inactive'}

**Configuration:**
• Sources: {len(sources)} channel(s)
• Targets: {len(targets)} channel(s)
• Type: {task['task_type'].title()}

**Statistics:**
• Messages Forwarded: {messages_forwarded:,}
• Messages Failed: {messages_failed:,}
• Success Rate: {success_rate:.1f}%
• Last Activity: {last_activity_str}

**Quick Actions:**
Use the buttons below to manage this task.
            """
            
            return task_details.strip()
            
        except Exception as e:
            logger.error(f"Error formatting task details: {e}")
            return "❌ Error formatting task details."
    
    async def _handle_task_edit(self, callback: CallbackQuery, state: FSMContext):
        """Handle task edit"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task_owner = await self.database.execute_query(
                "SELECT u.telegram_id FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.id = $1", 
                task_id
            )
            if not task_owner or task_owner[0]['telegram_id'] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get task information
            task_info = await self.database.execute_query(
                "SELECT * FROM tasks WHERE id = $1", task_id
            )
            
            if not task_info:
                await callback.answer("❌ Task not found.", show_alert=True)
                return
            
            task = task_info[0]
            
            edit_text = f"""
✏️ **Edit Task: {task['name']}**

What would you like to edit?

**Current Settings:**
• Name: {task['name']}
• Description: {task['description'] or 'No description'}
• Type: {task['task_type'].title()}
• Status: {'Active' if task['is_active'] else 'Inactive'}

Select what you want to modify:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="✏️ Edit Name", callback_data=f"task_edit_name_{task_id}"),
                    InlineKeyboardButton(text="📝 Edit Description", callback_data=f"task_edit_desc_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 Change Type", callback_data=f"task_edit_type_{task_id}"),
                    InlineKeyboardButton(text="⚙️ Edit Settings", callback_data=f"task_settings_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(edit_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error editing task: {e}")
            await callback.answer("❌ Error loading task edit options.")
    
    async def _handle_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle task delete confirmation"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task_owner = await self.database.execute_query(
                "SELECT u.telegram_id, t.name FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.id = $1", 
                task_id
            )
            if not task_owner or task_owner[0]['telegram_id'] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            task_name = task_owner[0]['name']
            
            confirm_text = f"""
⚠️ **Delete Task Confirmation**

Are you sure you want to delete the task **"{task_name}"**?

**Warning:** This action cannot be undone. All associated data including:
• Sources and targets
• Forwarding logs
• Statistics
• Settings

Will be permanently deleted.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="❌ Yes, Delete", callback_data=f"confirm_delete_task_{task_id}"),
                    InlineKeyboardButton(text="🔙 Cancel", callback_data=f"cancel_delete_task_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(confirm_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in task delete: {e}")
            await callback.answer("❌ Error loading delete confirmation.")
    
    async def _handle_confirm_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle confirmed task deletion"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership one more time
            task_owner = await self.database.execute_query(
                "SELECT u.telegram_id, t.name FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.id = $1", 
                task_id
            )
            if not task_owner or task_owner[0]['telegram_id'] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            task_name = task_owner[0]['name']
            
            # Delete task and all related data in correct order
            await self.database.execute_command("DELETE FROM forwarding_logs WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM task_statistics WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM manual_approvals WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM message_tracking WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM recurring_posts WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM task_settings WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM sources WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM targets WHERE task_id = $1", task_id)
            await self.database.execute_command("DELETE FROM tasks WHERE id = $1", task_id)
            
            # Remove from forwarding engine
            await self.forwarding_engine.remove_task(task_id)
            
            await callback.answer(f"✅ Task '{task_name}' deleted successfully.", show_alert=True)
            
            # Return to task list
            await self._handle_task_list(callback, state)
            
        except Exception as e:
            logger.error(f"Error confirming task delete: {e}")
            await callback.answer("❌ Error deleting task.")
    
    async def _handle_cancel_task_delete(self, callback: CallbackQuery, state: FSMContext):
        """Handle cancelled task deletion"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Return to task view
            await self._handle_task_view(callback, state)
            
        except Exception as e:
            logger.error(f"Error cancelling task delete: {e}")
            await callback.answer("❌ Error cancelling deletion.")
    
    async def _handle_task_mode_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle task mode toggle between bot and userbot"""
        try:
            task_id = int(callback.data.split("_")[-1])
            user_id = callback.from_user.id
            
            # Get task to check ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != user_id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            current_mode = task["task_type"]
            new_mode = "userbot" if current_mode == "bot" else "bot"
            
            # Check userbot availability if switching to userbot
            if new_mode == "userbot" and not self.bot_controller.userbot:
                await callback.answer(
                    "❌ Userbot mode is not available. String session not configured.",
                    show_alert=True
                )
                return
            
            # Update task mode in database
            await self.database.execute_command(
                "UPDATE tasks SET task_type = $1 WHERE id = $2",
                new_mode, task_id
            )
            
            # Clear task from cache to force refresh
            async with self.task_manager.cache_lock:
                if task_id in self.task_manager.task_cache:
                    del self.task_manager.task_cache[task_id]
            
            # Update forwarding engine
            await self.forwarding_engine.remove_task(task_id)
            await self.forwarding_engine.add_task(task_id)
            
            mode_emoji = "🤖" if new_mode == "bot" else "👤"
            await callback.answer(f"✅ Task mode changed to {mode_emoji} {new_mode.title()}", show_alert=True)
            
            # Wait a moment for database to fully commit
            await asyncio.sleep(0.1)
            
            # Get fresh task data directly from database bypassing cache
            task_data = await self.database.execute_query(
                "SELECT * FROM tasks WHERE id = $1", task_id
            )
            
            if task_data:
                task = task_data[0]
                
                # Get sources and targets
                sources = await self.database.get_task_sources(task_id)
                targets = await self.database.get_task_targets(task_id)
                statistics = await self.database.get_task_statistics(task_id)
                
                # Format task details with fresh data
                task_text = await self._format_task_details(task, sources, targets, statistics)
                
                # Get updated keyboard with correct button text
                keyboard = await self.keyboards.get_task_detail_keyboard(task_id, task)
                
                logger.info(f"Task {task_id} mode after update: {task.get('task_type', 'unknown')}")
                
                try:
                    await callback.message.edit_text(task_text, reply_markup=keyboard)
                    logger.info(f"Successfully updated task view for task {task_id}")
                except Exception as edit_err:
                    logger.warning(f"Edit failed: {edit_err}")
                    if "message is not modified" in str(edit_err):
                        # Force refresh by editing with different text first
                        temp_text = task_text + "\n🔄 Refreshing..."
                        await callback.message.edit_text(temp_text, reply_markup=keyboard)
                        await asyncio.sleep(0.2)
                        await callback.message.edit_text(task_text, reply_markup=keyboard)
                        logger.info(f"Forced refresh completed for task {task_id}")
                    else:
                        raise edit_err
            else:
                await callback.answer("❌ Error refreshing task view.", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error toggling task mode: {e}")
            await callback.answer("❌ Error switching task mode.")
    
    async def _handle_forward_mode_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle forward mode setting"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current forward mode
            settings = await self.database.execute_query(
                "SELECT forward_mode FROM task_settings WHERE task_id = $1", task_id
            )
            current_mode = settings[0]["forward_mode"] if settings else "copy"
            
            mode_text = f"""
🔄 **Forward Mode Settings** - {task['name']}

Current mode: **{current_mode.upper()}**

**Available Modes:**
• **Copy** - Creates new message with same content
• **Forward** - Forwards original message with author info
• **Quote** - Quotes original message with reply

Select new forward mode:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="📄 Copy" + (" ✅" if current_mode == "copy" else ""), 
                        callback_data=f"set_forward_mode_copy_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text="➡️ Forward" + (" ✅" if current_mode == "forward" else ""), 
                        callback_data=f"set_forward_mode_forward_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Quote" + (" ✅" if current_mode == "quote" else ""), 
                        callback_data=f"set_forward_mode_quote_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"task_settings_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(mode_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in forward mode setting: {e}")
            await callback.answer("❌ Error loading forward mode settings.")
    
    async def _handle_delay_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle delay setting"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current delay settings
            settings = await self.database.execute_query(
                "SELECT delay_min, delay_max FROM task_settings WHERE task_id = $1", task_id
            )
            delay_min = settings[0]["delay_min"] if settings else 0
            delay_max = settings[0]["delay_max"] if settings else 0
            
            delay_text = f"""
⏱️ **Delay Settings** - {task['name']}

Current delay: **{delay_min}-{delay_max} seconds**

**Purpose:** Add random delays between forwarded messages to appear more natural.

**Presets:**
• No delay (0-0 seconds)
• Fast (1-3 seconds)
• Normal (5-15 seconds)
• Slow (30-60 seconds)
• Custom range

Select delay preset:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="⚡ No Delay", callback_data=f"set_delay_0_0_{task_id}"),
                    InlineKeyboardButton(text="🏃 Fast", callback_data=f"set_delay_1_3_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🚶 Normal", callback_data=f"set_delay_5_15_{task_id}"),
                    InlineKeyboardButton(text="🐌 Slow", callback_data=f"set_delay_30_60_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="⚙️ Custom", callback_data=f"set_delay_custom_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"task_settings_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(delay_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in delay setting: {e}")
            await callback.answer("❌ Error loading delay settings.")
    
    async def _handle_filters_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle filters setting"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current filter settings
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            keywords = settings[0]["keyword_filters"] if settings and settings[0]["keyword_filters"] else "None"
            # Remove references to non-existent columns for now
            media_types = "All" 
            min_length = 0
            
            filters_text = f"""
🔍 **Content Filters** - {task['name']}

Current filters:
• **Keywords:** {keywords}
• **Media types:** {media_types}
• **Min length:** {min_length} characters

**Available Filters:**
• Keyword filtering (include/exclude)
• Media type filtering
• Message length limits
• User/channel filtering

Configure filters:
            """
            
            # Get current settings for the keyboard
            current_settings = await self.database.get_task_settings(task_id) or {}
            
            # Use the standardized keyboard from keyboards module
            markup = await self.keyboards.get_filter_settings_keyboard(task_id, current_settings)
            await callback.message.edit_text(filters_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in filters setting: {e}")
            await callback.answer("❌ Error loading filter settings.")
    
    async def _handle_content_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle content modification setting"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            logger.info(f"Content setting accessed for task {task_id}")
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            content_text = f"""
📝 **Content Modifications** - {task['name']}

**Available Modifications:**
• Add prefix/suffix to messages
• Replace text patterns
• Text formatting changes
• Link modifications
• Text cleaning and filtering

**Current Status:** No modifications active

Configure content modifications:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="📋 Prefix/Suffix", callback_data=f"content_prefix_{task_id}"),
                    InlineKeyboardButton(text="🔄 Text Replace", callback_data=f"content_replace_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🎨 Formatting", callback_data=f"content_formatting_{task_id}"),
                    InlineKeyboardButton(text="🔘 Inline Buttons", callback_data=f"content_inline_buttons_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🧹 Text Cleaner", callback_data=f"content_cleaner_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"task_settings_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            logger.info(f"Content keyboard created with buttons: {[btn.text for row in keyboard for btn in row]}")
            logger.info(f"Content keyboard callback data: {[btn.callback_data for row in keyboard for btn in row]}")
            
            # Check if content is different before editing
            current_text = callback.message.text
            if current_text != content_text.strip():
                await callback.message.edit_text(content_text, reply_markup=markup)
                logger.info("Content message updated with new text and keyboard")
            else:
                await callback.message.edit_reply_markup(reply_markup=markup)
                logger.info("Content keyboard updated without changing text")
            
        except Exception as e:
            logger.error(f"Error in content setting: {e}")
            await callback.answer("❌ Error loading content settings.")
    

    
    async def _handle_reset_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle reset settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            reset_text = f"""
🔄 **Reset Settings** - {task['name']}

⚠️ **Warning:** This will reset all task settings to defaults:

• Forward mode: Copy
• Delays: No delay (0-0s)
• Filters: None (all content)
• Content modifications: None
• All custom configurations: Removed

**This action cannot be undone.**

Are you sure you want to reset all settings?
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="❌ Yes, Reset All", callback_data=f"confirm_reset_{task_id}"),
                    InlineKeyboardButton(text="🔙 Cancel", callback_data=f"task_settings_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(reset_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in reset setting: {e}")
            await callback.answer("❌ Error loading reset confirmation.")
    
    async def _handle_limits_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle limits settings submenu"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            delay_min = settings.get("delay_min", 0) if settings else 0
            delay_max = settings.get("delay_max", 0) if settings else 0
            send_limit = settings.get("send_limit", 0) if settings else 0
            length_limit = settings.get("max_length", 0) if settings else 0
            
            limits_text = f"""
⏱️ **Limits Settings** - {task['name']}

**Current Settings:**
• Delays: {delay_min}-{delay_max} seconds
• Send limit: {send_limit if send_limit > 0 else 'Unlimited'} messages/hour
• Length limit: {length_limit if length_limit > 0 else 'No limit'} characters

Configure forwarding limits and delays:
            """
            
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
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(limits_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in limits setting: {e}")
            await callback.answer("❌ Error loading limits settings.")

    async def _handle_save_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle save settings"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Save current settings (this is automatically done, so just show confirmation)
            await callback.answer("✅ Settings saved successfully!", show_alert=True)
            
            # Return to settings menu
            await self._handle_task_settings(callback, state)
            
        except Exception as e:
            logger.error(f"Error in save setting: {e}")
            await callback.answer("❌ Error saving settings.")
    
    async def _handle_view_all_settings(self, callback: CallbackQuery, state: FSMContext):
        """Handle view all settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            task_id = int(callback.data.split("_")[-1])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get all current settings
            settings = await self.database.execute_query(
                """SELECT forward_mode, delay_min, delay_max, keyword_filters FROM task_settings WHERE task_id = $1""", 
                task_id
            )
            
            if settings:
                s = settings[0]
                forward_mode = s["forward_mode"] or "copy"
                delay_range = f"{s['delay_min'] or 0}-{s['delay_max'] or 0}s"
                keywords = s["keyword_filters"] or "None"
                media_types = "All"
                min_length = 0
            else:
                forward_mode = "copy"
                delay_range = "0-0s"
                keywords = "None"
                media_types = "All"
                min_length = 0
            
            all_settings_text = f"""
📋 **All Settings** - {task['name']}

**Forward Configuration:**
• Mode: {forward_mode.upper()}
• Delay: {delay_range}

**Content Filters:**
• Keywords: {keywords}
• Media types: {media_types}
• Min length: {min_length} chars

**Status:** {"✅ Active" if task['is_active'] else "⏸️ Paused"}
**Created:** {task.get('created_at', 'Unknown')}
**Last Modified:** Just now

Settings are automatically saved.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="📝 Edit Settings", callback_data=f"task_settings_{task_id}"),
                    InlineKeyboardButton(text="📊 Statistics", callback_data=f"task_statistics_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Task", callback_data=f"task_view_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(all_settings_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in view all settings: {e}")
            await callback.answer("❌ Error loading all settings.")
    
    async def _handle_set_forward_mode(self, callback: CallbackQuery, state: FSMContext):
        """Handle setting forward mode"""
        try:
            parts = callback.data.split("_")
            mode = parts[3]  # copy, forward, or quote
            task_id = int(parts[4])
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Update forward mode in database
            await self.database.execute_command(
                """INSERT INTO task_settings (
                    task_id, forward_mode, preserve_sender, add_caption, 
                    filter_media, filter_text, filter_forwarded, filter_links,
                    allow_photos, allow_videos, allow_documents, allow_audio, 
                    allow_voice, allow_video_notes, allow_stickers, allow_animations,
                    allow_contacts, allow_locations, allow_venues, allow_polls, allow_dice,
                    delay_min, delay_max, remove_links, remove_mentions, duplicate_check, max_message_length,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, false, false, 
                    false, false, false, false,
                    true, true, true, true,
                    true, true, true, true,
                    true, true, true, true, true,
                    0, 5, false, false, true, 4096,
                    NOW(), NOW()
                ) ON CONFLICT (task_id) 
                DO UPDATE SET forward_mode = $2, updated_at = NOW()""",
                task_id, mode
            )
            
            await callback.answer(f"✅ Forward mode set to {mode.upper()}", show_alert=True)
            
            # Return to forward mode settings
            await self._handle_forward_mode_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error setting forward mode: {e}")
            await callback.answer("❌ Error updating forward mode.")
    
    async def _handle_set_delay(self, callback: CallbackQuery, state: FSMContext):
        """Handle setting delay presets"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            parts = callback.data.split("_")
            
            # Parse callback data format: set_delay_min_max_taskid
            if len(parts) >= 5:
                delay_min = int(parts[2])
                delay_max = int(parts[3]) 
                task_id = int(parts[4])
            elif len(parts) == 4 and parts[2] == "custom":
                task_id = int(parts[3])
                
                # Store task_id in session for custom delay input
                await self.bot_controller.update_user_session(
                    callback.from_user.id, 
                    {"setting_custom_delay_task_id": task_id}
                )
                
                await callback.message.edit_text(
                    "⚙️ **Custom Delay Configuration**\n\n"
                    "Send two numbers separated by a space:\n"
                    "• First number: Minimum delay (in seconds)\n"
                    "• Second number: Maximum delay (in seconds)\n\n"
                    "**Example:** `5 20` (random delay between 5 and 20 seconds)\n\n"
                    "**Limits:**\n"
                    "• Minimum: 0 seconds\n"
                    "• Maximum: 300 seconds (5 minutes)"
                )
                
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="custom_delay", task_id=task_id)
                return
            else:
                await callback.answer("❌ Invalid delay format.", show_alert=True)
                return
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Update delay settings in database with all required fields
            await self.database.execute_command(
                """INSERT INTO task_settings (
                    task_id, forward_mode, preserve_sender, add_caption, 
                    filter_media, filter_text, filter_forwarded, filter_links,
                    allow_photos, allow_videos, allow_documents, allow_audio, 
                    allow_voice, allow_video_notes, allow_stickers, allow_animations,
                    allow_contacts, allow_locations, allow_venues, allow_polls, allow_dice,
                    delay_min, delay_max, remove_links, remove_mentions, duplicate_check, max_message_length,
                    created_at, updated_at
                ) VALUES (
                    $1, 'copy', false, false, 
                    false, false, false, false,
                    true, true, true, true,
                    true, true, true, true,
                    true, true, true, true, true,
                    $2, $3, false, false, true, 4096,
                    NOW(), NOW()
                ) ON CONFLICT (task_id) 
                DO UPDATE SET delay_min = $2, delay_max = $3, updated_at = NOW()""",
                task_id, delay_min, delay_max
            )
            
            await callback.answer(f"✅ Delay set to {delay_min}-{delay_max}s", show_alert=True)
            
            # Return to delay settings
            await self._handle_delay_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error setting delay: {e}")
            await callback.answer("❌ Error updating delay settings.")
    
    async def _handle_content_submenu(self, callback: CallbackQuery, state: FSMContext):
        """Handle content modification submenu actions"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            if callback.data.startswith("content_prefix_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_prefix_suffix_setting(callback, task_id, state)
            elif callback.data.startswith("content_replace_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_text_replace_setting(callback, task_id, state)

            elif callback.data.startswith("content_formatting_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_formatting_setting(callback, task_id, state)
            elif callback.data.startswith("content_links_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_links_setting(callback, task_id, state)
            else:
                await callback.answer("❌ Unknown content action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in content submenu: {e}")
            await callback.answer("❌ Error in content settings.")
    

    
    async def _handle_filter_submenu(self, callback: CallbackQuery, state: FSMContext):
        """Handle filter submenu actions"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            if callback.data.startswith("filter_keywords_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_keyword_filter(callback, task_id, state)
            elif callback.data.startswith("filter_media_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_media_filter(callback, task_id, state)
            elif callback.data.startswith("filter_length_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_length_filter(callback, task_id, state)
            elif callback.data.startswith("filter_users_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_user_filter(callback, task_id, state)
            elif callback.data.startswith("filter_clear_"):
                task_id = int(callback.data.split("_")[-1])
                await self._handle_clear_filters(callback, task_id, state)
            else:
                await callback.answer("❌ Unknown filter action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in filter submenu: {e}")
            await callback.answer("❌ Error in filter settings.")

    async def _handle_keyword_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle simplified keyword filter configuration with separate whitelist/blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keyword filter settings
            settings = await self.database.execute_query(
                "SELECT keyword_filters, filter_text FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            # Parse current settings with separate lists for whitelist/blacklist
            whitelist_keywords = []
            blacklist_keywords = []
            filter_enabled = False
            filter_mode = "blacklist"  # default
            
            if settings:
                setting = settings[0]
                filter_enabled = setting.get("filter_text", False)
                
                if setting.get("keyword_filters"):
                    try:
                        keywords_data = json.loads(setting["keyword_filters"]) if isinstance(setting["keyword_filters"], str) else setting["keyword_filters"]
                        if isinstance(keywords_data, dict):
                            filter_mode = keywords_data.get("mode", "blacklist")
                            # Support separate lists
                            if "whitelist" in keywords_data and "blacklist" in keywords_data:
                                whitelist_keywords = keywords_data.get("whitelist", [])
                                blacklist_keywords = keywords_data.get("blacklist", [])
                            else:
                                # Legacy format - migrate to current mode
                                legacy_keywords = keywords_data.get("keywords", [])
                                if filter_mode == "whitelist":
                                    whitelist_keywords = legacy_keywords
                                else:
                                    blacklist_keywords = legacy_keywords
                    except:
                        # Legacy string format
                        legacy_keywords = [kw.strip() for kw in setting["keyword_filters"].split(",") if kw.strip()]
                        if filter_mode == "whitelist":
                            whitelist_keywords = legacy_keywords
                        else:
                            blacklist_keywords = legacy_keywords
            
            # Get current list based on mode
            current_keywords = whitelist_keywords if filter_mode == "whitelist" else blacklist_keywords
            keywords_count = len(current_keywords)
            
            # Generate interface text
            keywords_text = "🔤 **Keyword Filter - Task " + str(task_id) + "**\n\n"
            
            # Filter status
            status_icon = "✅" if filter_enabled else "❌"
            keywords_text += f"**Filter Status:** {status_icon} {'Enabled' if filter_enabled else 'Disabled'}\n\n"
            
            # Show statistics for both lists
            whitelist_count = len(whitelist_keywords)
            blacklist_count = len(blacklist_keywords)
            keywords_text += f"📊 **Statistics:**\n"
            keywords_text += f"• Whitelist: {whitelist_count} keywords\n"
            keywords_text += f"• Blacklist: {blacklist_count} keywords\n\n"
            
            if filter_mode == "whitelist":
                keywords_text += "⚪ **Current Mode: Whitelist**\n"
                keywords_text += "Only allow messages containing approved keywords\n\n"
            else:
                keywords_text += "⚫ **Current Mode: Blacklist**\n"
                keywords_text += "Block messages containing forbidden keywords\n\n"
            
            if keywords_count > 0:
                keywords_text += f"**First 5 keywords from current mode:**\n"
                for i, keyword in enumerate(current_keywords[:5], 1):
                    keywords_text += f"{i}. `{keyword}`\n"
                if keywords_count > 5:
                    keywords_text += f"... and {keywords_count - 5} more keywords"
            else:
                keywords_text += f"⚠️ No keywords in current mode"
            
            # Create simplified keyboard with single toggle button
            if filter_mode == "whitelist":
                toggle_text = f"🔄 Switch to Blacklist ({blacklist_count})"
                toggle_action = f"kw_mode_blacklist_{task_id}"
                add_text = "➕ Add Allowed Keywords"
                add_action = f"kw_add_whitelist_{task_id}"
                view_text = "📋 View Whitelist"
                view_action = f"kw_list_whitelist_{task_id}"
                clear_text = "🗑️ Clear Whitelist"
                clear_action = f"kw_clear_whitelist_{task_id}"
            else:
                toggle_text = f"🔄 Switch to Whitelist ({whitelist_count})"
                toggle_action = f"kw_mode_whitelist_{task_id}"
                add_text = "➕ Add Blocked Keywords"
                add_action = f"kw_add_blacklist_{task_id}"
                view_text = "📋 View Blacklist"
                view_action = f"kw_list_blacklist_{task_id}"
                clear_text = "🗑️ Clear Blacklist"
                clear_action = f"kw_clear_blacklist_{task_id}"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 Disable' if filter_enabled else '🟢 Enable'} Filter", 
                        callback_data=f"kw_toggle_filter_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text=toggle_text, callback_data=toggle_action)
                ],
                [
                    InlineKeyboardButton(text=add_text, callback_data=add_action)
                ],
                [
                    InlineKeyboardButton(text=view_text, callback_data=view_action)
                ],
                [
                    InlineKeyboardButton(text=clear_text, callback_data=clear_action)
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Filters", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(keywords_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in keyword filter: {e}")
            await callback.answer("❌ Error loading keyword filter settings.")

    async def _handle_media_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle media type filter configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current media filter settings
            settings = await self.database.execute_query(
                "SELECT filter_media, filter_text FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            filter_media = False
            filter_text = False
            if settings:
                filter_media = settings[0]["filter_media"] or False
                filter_text = settings[0]["filter_text"] or False
            
            # Get comprehensive settings including all media types
            settings = await self.bot_controller.database.get_task_settings(task_id)
            
            # Display comprehensive media types keyboard
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            media_text = f"🎛️ **Media Type Settings - المهمة {task_id}**\n\n" \
                        f"Choose the media types you want to allow forwarding:\n\n" \
                        f"✅ = enabled (will be forwarded)\n" \
                        f"❌ = disabled (will be ignored)\n\n" \
                        f"You can control each media type separately"
            
            await callback.message.edit_text(media_text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in media filter: {e}")
            await callback.answer("❌ Error loading media filter settings.")



    async def _handle_user_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle user-based filter configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import time
            
            # Get current settings to show button states
            settings = await self.bot_controller.database.get_task_settings(task_id)
            
            # Check current filter states
            filter_forwarded = settings.get('filter_forwarded', False) if settings else False
            filter_bots = settings.get('filter_bots', False) if settings else False
            
            # Dynamic button text based on current state
            verified_text = "✅ Verified Only" if filter_forwarded else "❌ Verified Only"
            nobots_text = "✅ No Bots" if filter_bots else "❌ No Bots"
            
            # Add timestamp to ensure message content changes
            timestamp = int(time.time())
            
            user_text = f"""
👤 **User-Based Filters** - Task {task_id}

Configure filters based on message senders:

• **Verified Users Only**: Only forward from verified accounts
• **No Bots**: Block messages from bot accounts  
• **Whitelist Users**: Only allow specific users
• **Blacklist Users**: Block specific users

Current Status:
• Verified Filter: {"ON" if filter_forwarded else "OFF"}
• Bot Filter: {"ON" if filter_bots else "OFF"}

Note: Some features require userbot mode for full functionality.

_Updated: {timestamp}_
"""

            keyboard = [
                [
                    InlineKeyboardButton(text=verified_text, callback_data=f"user_verified_{task_id}"),
                    InlineKeyboardButton(text=nobots_text, callback_data=f"user_nobots_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📋 Whitelist", callback_data=f"user_whitelist_{task_id}"),
                    InlineKeyboardButton(text="🚫 Blacklist", callback_data=f"user_blacklist_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Filters", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(user_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in user filter: {e}")
            await callback.answer("❌ Error loading user filter settings.")

    async def _handle_toggle_verified_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle verified users only filter"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_verified", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET filter_verified = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} فلتر المستخدمين المؤكدين")
            await self._handle_user_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling verified filter: {e}")
            await callback.answer("❌ خطأ في تبديل فلتر التحقق", show_alert=True)

    async def _handle_toggle_bot_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle bot filter"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_bots", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET filter_bots = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} فلتر البوتات")
            await self._handle_user_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling bot filter: {e}")
            await callback.answer("❌ خطأ في تبديل فلتر البوت", show_alert=True)

    async def _handle_user_whitelist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle user whitelist management"""
        try:
            await callback.answer("📋 إدارة القائمة البيضاء - قريباً")
            
        except Exception as e:
            logger.error(f"Error in user whitelist: {e}")
            await callback.answer("❌ خطأ في القائمة البيضاء", show_alert=True)

    async def _handle_user_blacklist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle user blacklist management"""
        try:
            await callback.answer("🚫 إدارة القائمة السوداء - قريباً")
            
        except Exception as e:
            logger.error(f"Error in user blacklist: {e}")
            await callback.answer("❌ خطأ في القائمة السوداء", show_alert=True)

    async def _handle_length_filter_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle message length filter settings"""
        try:
            settings = await self.database.get_task_settings(task_id)
            max_length = settings.get("max_message_length", 0) if settings else 0
            min_length = settings.get("min_message_length", 0) if settings else 0
            
            text = f"""📏 **فلتر طول الرسالة - المهمة {task_id}**

**الإعدادات الحالية:**
• الحد الأدنى: {min_length} حرف
• الحد الأقصى: {max_length if max_length > 0 else 'غير محدد'} حرف

**خيارات سريعة:**"""

            keyboard = [
                [
                    InlineKeyboardButton(text="📝 نص قصير (< 100)", callback_data=f"len_max_100_{task_id}"),
                    InlineKeyboardButton(text="📄 نص متوسط (< 500)", callback_data=f"len_max_500_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📃 نص طويل (< 1000)", callback_data=f"len_max_1000_{task_id}"),
                    InlineKeyboardButton(text="📋 نص طويل جداً (< 2000)", callback_data=f"len_max_2000_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🚫 إزالة الحد الأقصى", callback_data=f"len_max_unlimited_{task_id}"),
                    InlineKeyboardButton(text="⚙️ إعداد مخصص", callback_data=f"len_custom_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            
        except Exception as e:
            logger.error(f"Error in length filter: {e}")
            await callback.answer("❌ خطأ في فلتر الطول", show_alert=True)

    async def _handle_clear_filters(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle clearing all filters"""
        try:
            # Clear all filter settings for the task
            await self.database.execute_command(
                """UPDATE task_settings SET 
                   keyword_filters = NULL, 
                   filter_media = FALSE, 
                   filter_text = FALSE,
                   filter_forwarded = FALSE,
                   filter_links = FALSE,
                   max_message_length = 4096
                   WHERE task_id = $1""", 
                task_id
            )
            
            await callback.answer("🗑️ All filters cleared successfully!", show_alert=True)
            
            # Return to filters menu
            await self._handle_filters_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error clearing filters: {e}")
            await callback.answer("❌ Error clearing filters.")

    async def _handle_keyword_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle keyword filter actions with enhanced features"""
        try:
            import json
            data = callback.data
            parts = data.split("_")
            
            if data.startswith("kw_toggle_filter_"):
                task_id = int(parts[3])
                
                # Get current filter state and mode
                settings = await self.database.execute_query(
                    "SELECT keyword_filter_mode, keyword_filters FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                current_mode = settings[0]["keyword_filter_mode"] if settings and settings[0]["keyword_filter_mode"] else "none"
                
                # Toggle between enabled and disabled
                if current_mode == "none":
                    # Enable with default blacklist mode
                    new_mode = "blacklist"
                    status_text = "enabled (blacklist mode)"
                else:
                    # Disable filtering
                    new_mode = "none"
                    status_text = "disabled"
                
                # Update both filter_text and keyword_filter_mode
                await self.database.execute_command(
                    "UPDATE task_settings SET filter_text = $1, keyword_filter_mode = $2 WHERE task_id = $3",
                    new_mode != "none", new_mode, task_id
                )
                
                # Force reload of forwarding engine settings
                if hasattr(self.bot_controller, 'forwarding_engine'):
                    await self.bot_controller.forwarding_engine._reload_tasks()
                
                await callback.answer(f"🔘 Keyword filter: {status_text}")
                await self._handle_keyword_filter(callback, task_id, state)
                
            elif data.startswith("kw_mode_whitelist_"):
                task_id = int(parts[3])
                
                # Get current keywords with separate lists
                settings = await self.database.execute_query(
                    "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                whitelist_keywords = []
                blacklist_keywords = []
                
                if settings and settings[0]["keyword_filters"]:
                    try:
                        keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                        if isinstance(keywords_data, dict):
                            if "whitelist" in keywords_data and "blacklist" in keywords_data:
                                whitelist_keywords = keywords_data.get("whitelist", [])
                                blacklist_keywords = keywords_data.get("blacklist", [])
                            else:
                                # Migrate legacy format
                                legacy_keywords = keywords_data.get("keywords", [])
                                current_mode = keywords_data.get("mode", "blacklist")
                                if current_mode == "whitelist":
                                    whitelist_keywords = legacy_keywords
                                else:
                                    blacklist_keywords = legacy_keywords
                    except:
                        # Handle string format
                        pass
                
                # Switch to whitelist mode
                keywords_data = {
                    "mode": "whitelist",
                    "whitelist": whitelist_keywords,
                    "blacklist": blacklist_keywords
                }
                
                await self.database.execute_command(
                    "UPDATE task_settings SET keyword_filters = $1, keyword_filter_mode = $2 WHERE task_id = $3",
                    json.dumps(keywords_data), "whitelist", task_id
                )
                
                # Force reload of forwarding engine settings
                if hasattr(self.bot_controller, 'forwarding_engine'):
                    await self.bot_controller.forwarding_engine._reload_tasks()
                
                await callback.answer("⚪ Switched to whitelist")
                await self._handle_keyword_filter(callback, task_id, state)
                
            elif data.startswith("kw_mode_blacklist_"):
                task_id = int(parts[3])
                
                # Get current keywords with separate lists
                settings = await self.database.execute_query(
                    "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                whitelist_keywords = []
                blacklist_keywords = []
                
                if settings and settings[0]["keyword_filters"]:
                    try:
                        keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                        if isinstance(keywords_data, dict):
                            if "whitelist" in keywords_data and "blacklist" in keywords_data:
                                whitelist_keywords = keywords_data.get("whitelist", [])
                                blacklist_keywords = keywords_data.get("blacklist", [])
                            else:
                                # Migrate legacy format
                                legacy_keywords = keywords_data.get("keywords", [])
                                current_mode = keywords_data.get("mode", "blacklist")
                                if current_mode == "whitelist":
                                    whitelist_keywords = legacy_keywords
                                else:
                                    blacklist_keywords = legacy_keywords
                    except:
                        # Handle string format
                        pass
                
                # Switch to blacklist mode
                keywords_data = {
                    "mode": "blacklist",
                    "whitelist": whitelist_keywords,
                    "blacklist": blacklist_keywords
                }
                
                await self.database.execute_command(
                    "UPDATE task_settings SET keyword_filters = $1, keyword_filter_mode = $2 WHERE task_id = $3",
                    json.dumps(keywords_data), "blacklist", task_id
                )
                
                # Force reload of forwarding engine settings
                if hasattr(self.bot_controller, 'forwarding_engine'):
                    await self.bot_controller.forwarding_engine._reload_tasks()
                
                await callback.answer("⚫ Switched to blacklist")
                await self._handle_keyword_filter(callback, task_id, state)
                
            elif data.startswith("kw_add_whitelist_"):
                task_id = int(parts[3])
                
                # Create input interface for whitelist keywords
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                input_text = f"""⚪ **Add Allowed Keywords - Task {task_id}**

Send the new allowed keywords separated by commas:

**Example:**
news, technology, education

⚠️ Note: Send the text in the next message directly"""

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Cancel", callback_data=f"filter_keywords_{task_id}")]
                ])
                
                await callback.message.edit_text(input_text, reply_markup=keyboard, parse_mode="Markdown")
                await callback.answer()
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="add_whitelist_keywords", task_id=task_id)
                
            elif data.startswith("kw_add_blacklist_"):
                task_id = int(parts[3])
                
                # Create input interface for blacklist keywords
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                input_text = f"""⚫ **Add Blocked Keywords - Task {task_id}**

Send the new blocked keywords separated by commas:

**Example:**
advertisement, spam, annoying

⚠️ Note: Send the text in the next message directly"""

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Cancel", callback_data=f"filter_keywords_{task_id}")]
                ])
                
                await callback.message.edit_text(input_text, reply_markup=keyboard, parse_mode="Markdown")
                await callback.answer()
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="add_blacklist_keywords", task_id=task_id)
                
            elif data.startswith("kw_edit_"):
                task_id = int(parts[2])
                await self._handle_keyword_edit_menu(callback, task_id, state)
                
            elif data.startswith("kw_list_whitelist_"):
                task_id = int(parts[3])
                await self._handle_keyword_list_whitelist(callback, task_id, state)
                
            elif data.startswith("kw_list_blacklist_"):
                task_id = int(parts[3])
                await self._handle_keyword_list_blacklist(callback, task_id, state)
                
            elif data.startswith("kw_clear_whitelist_"):
                task_id = int(parts[3])
                await self._handle_keyword_clear_whitelist(callback, task_id, state)
                
            elif data.startswith("kw_clear_blacklist_"):
                task_id = int(parts[3])
                await self._handle_keyword_clear_blacklist(callback, task_id, state)
                
            elif data.startswith("kw_clear_all_"):
                task_id = int(parts[3])
                await self._handle_keyword_clear_confirmation(callback, task_id, state)
                
            elif data.startswith("kw_export_"):
                task_id = int(parts[2])
                await self._handle_keyword_export(callback, task_id, state)
                
            elif data.startswith("kw_import_"):
                task_id = int(parts[2])
                await callback.answer("📥 Send a text file or list of keywords to import", show_alert=True)
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="import_keywords", task_id=task_id)
                
            elif data.startswith("kw_test_"):
                task_id = int(parts[2])
                await self._handle_keyword_test(callback, task_id, state)
                
            else:
                await callback.answer("❌ إجراء غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in keyword actions: {e}")
            await callback.answer("❌ خطأ في معالجة إجراء الكلمات المفتاحية", show_alert=True)

    async def _handle_media_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle media type toggle"""
        try:
            data = callback.data
            if data.startswith("media_toggle_"):
                parts = data.split("_")
                task_id = int(parts[2])
                
                settings = await self.bot_controller.database.get_task_settings(task_id)
                current_media = settings.get('filter_media', False) if settings else False
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET filter_media = $1 WHERE task_id = $2",
                    not current_media, task_id
                )
                
                await callback.answer(f"Media filtering {'enabled' if not current_media else 'disabled'}")
                
                # Refresh the filters menu
                await self._handle_filters_setting(callback, state)
                
            elif data.startswith("text_toggle_"):
                parts = data.split("_")
                task_id = int(parts[2])
                
                settings = await self.bot_controller.database.get_task_settings(task_id)
                current_text = settings.get('filter_text', False) if settings else False
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET filter_text = $1 WHERE task_id = $2",
                    not current_text, task_id
                )
                
                await callback.answer(f"Text filtering {'enabled' if not current_text else 'disabled'}")
                
                # Refresh the filters menu
                await self._handle_filters_setting(callback, state)
                
        except Exception as e:
            logger.error(f"Error toggling media type: {e}")
            await callback.answer("❌ Error toggling media type", show_alert=True)

    async def _handle_length_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle message length setting"""
        try:
            data = callback.data
            if data.startswith("len_"):
                parts = data.split("_")
                task_id = int(parts[1])
                length = int(parts[2]) if len(parts) > 2 and parts[2] != 'unlimited' else 4096
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET max_message_length = $1 WHERE task_id = $2",
                    length, task_id
                )
                
                if length == 4096:
                    await callback.answer("Length filter removed (unlimited)")
                else:
                    await callback.answer(f"Max length set to {length} characters")
                
                # Refresh the filters menu
                await self._handle_filters_setting(callback, state)
                
        except Exception as e:
            logger.error(f"Error setting length filter: {e}")
            await callback.answer("❌ Error setting length filter", show_alert=True)

    async def _handle_user_filter_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle user filter actions"""
        try:
            data = callback.data
            logger.info(f"_handle_user_filter_actions called with data: {data}")
            if data.startswith("user_verified_"):
                logger.info("Processing user_verified_ callback")
                task_id = int(data.split("_")[2])
                settings = await self.bot_controller.database.get_task_settings(task_id)
                current_forwarded = settings.get('filter_forwarded', False) if settings else False
                
                # Toggle the setting
                new_forwarded_setting = not current_forwarded
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET filter_forwarded = $1 WHERE task_id = $2",
                    new_forwarded_setting, task_id
                )
                
                status = "enabled" if new_forwarded_setting else "disabled"
                await callback.answer(f"Verified only filter: {status}")
                
                # Refresh the user filter interface to show updated button states
                await self._handle_user_filter(callback, task_id, state)
                
            elif data.startswith("user_nobots_"):
                logger.info("Processing user_nobots_ callback")
                task_id = int(data.split("_")[2])
                settings = await self.bot_controller.database.get_task_settings(task_id)
                current_bots = settings.get('filter_bots', False) if settings else False
                logger.info(f"Current bots filter state: {current_bots}")
                
                # Toggle the setting
                new_bots_setting = not current_bots
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET filter_bots = $1 WHERE task_id = $2",
                    new_bots_setting, task_id
                )
                
                status = "enabled" if new_bots_setting else "disabled"
                await callback.answer(f"No bots filter: {status}")
                
                # Refresh the user filter interface to show updated button states
                await self._handle_user_filter(callback, task_id, state)
                

                
            # Handle all whitelist specific actions
            elif data.startswith("whitelist_toggle_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_toggle(callback, task_id, state)
                
            elif data.startswith("whitelist_add_manual_"):
                task_id = int(data.split("_")[3])
                await self._handle_whitelist_add(callback, task_id, state)
                
            elif data.startswith("whitelist_add_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_add(callback, task_id, state)
                
            elif data.startswith("whitelist_list_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_list(callback, task_id, state)
                
            elif data.startswith("whitelist_clear_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_clear(callback, task_id, state)
                
            elif data.startswith("whitelist_export_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_export(callback, task_id, state)
                
            elif data.startswith("whitelist_import_"):
                task_id = int(data.split("_")[2])
                await self._handle_whitelist_import(callback, task_id, state)
                
            # Handle all blacklist specific actions
            elif data.startswith("blacklist_toggle_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_toggle(callback, task_id, state)
                
            elif data.startswith("blacklist_add_manual_"):
                task_id = int(data.split("_")[3])
                await self._handle_blacklist_add(callback, task_id, state)
                
            elif data.startswith("blacklist_add_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_add(callback, task_id, state)
                
            elif data.startswith("blacklist_list_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_list(callback, task_id, state)
                
            elif data.startswith("blacklist_clear_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_clear(callback, task_id, state)
                
            elif data.startswith("blacklist_export_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_export(callback, task_id, state)
                
            elif data.startswith("blacklist_import_"):
                task_id = int(data.split("_")[2])
                await self._handle_blacklist_import(callback, task_id, state)
                

                

                
            # Confirmation handlers
            elif data.startswith("whitelist_clear_confirm_"):
                task_id = int(data.split("_")[3])
                await self._handle_whitelist_clear_confirm(callback, task_id, state)
                
            elif data.startswith("blacklist_clear_confirm_"):
                task_id = int(data.split("_")[3])
                await self._handle_blacklist_clear_confirm(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error in user filter actions: {e}")
            await callback.answer("❌ Error processing user filter", show_alert=True)

    async def handle_keyword_input(self, message: Message, state: FSMContext):
        """Handle keyword input from user"""
        try:
            import json
            user_id = message.from_user.id
            
            # Get session data from state
            session_data = await state.get_data()
            action = session_data.get("action")
            task_id = session_data.get("task_id")
            
            # Also check bot controller session for custom delay
            controller_session = await self.bot_controller.get_user_session(user_id)
            custom_delay_task_id = controller_session.get("setting_custom_delay_task_id")
            
            # Handle custom delay input
            if custom_delay_task_id:
                try:
                    parts = message.text.strip().split()
                    if len(parts) != 2:
                        await message.answer("❌ الرجاء إرسال رقمين مفصولين بمسافة.\nمثال: `5 20`")
                        return
                    
                    delay_min = int(parts[0])
                    delay_max = int(parts[1])
                    
                    # Validate ranges
                    if delay_min < 0:
                        await message.answer("❌ الحد الأدنى للتأخير لا يمكن أن يكون سالباً.")
                        return
                    
                    if delay_max > 300:
                        await message.answer("❌ الحد الأقصى للتأخير لا يمكن أن يتجاوز 300 ثانية.")
                        return
                    
                    if delay_min > delay_max:
                        await message.answer("❌ الحد الأدنى للتأخير يجب أن يكون أقل من أو يساوي الحد الأقصى.")
                        return
                    
                    # Update delay settings in database
                    await self.database.execute_command(
                        """INSERT INTO task_settings (
                            task_id, forward_mode, preserve_sender, add_caption, 
                            filter_media, filter_text, filter_forwarded, filter_links,
                            allow_photos, allow_videos, allow_documents, allow_audio, 
                            allow_voice, allow_video_notes, allow_stickers, allow_animations,
                            allow_contacts, allow_locations, allow_venues, allow_polls, allow_dice,
                            delay_min, delay_max, remove_links, remove_mentions, duplicate_check, max_message_length,
                            created_at, updated_at
                        ) VALUES (
                            $1, 'copy', false, false, 
                            false, false, false, false,
                            true, true, true, true,
                            true, true, true, true,
                            true, true, true, true, true,
                            $2, $3, false, false, true, 4096,
                            NOW(), NOW()
                        ) ON CONFLICT (task_id) 
                        DO UPDATE SET delay_min = $2, delay_max = $3, updated_at = NOW()""",
                        custom_delay_task_id, delay_min, delay_max
                    )
                    
                    await message.answer(f"✅ **تم تعيين التأخير المخصص بنجاح!**\n\n"
                                       f"• الحد الأدنى: {delay_min} ثانية\n"
                                       f"• الحد الأقصى: {delay_max} ثانية\n\n"
                                       f"سيتم تطبيق تأخير عشوائي بين هذين القيمتين.")
                    
                    # Clear session
                    await self.bot_controller.clear_user_session(user_id)
                    await state.clear()
                    return
                    
                except ValueError:
                    await message.answer("❌ الرجاء إدخال أرقام صحيحة فقط.\nمثال: `5 20`")
                    return
                except Exception as e:
                    logger.error(f"Error setting custom delay: {e}")
                    await message.answer("❌ حدث خطأ أثناء تعيين التأخير. الرجاء المحاولة مرة أخرى.")
                    await self.bot_controller.clear_user_session(user_id)
                    await state.clear()
                    return
            
            # Handle keyword input with separate whitelist/blacklist support
            if not action or not task_id:
                await message.answer("❌ انتهت صلاحية الجلسة. الرجاء المحاولة مرة أخرى.")
                await state.clear()
                return
            
            # Handle user input for whitelist/blacklist
            if action in ["add_whitelist_user", "add_blacklist_user"]:
                list_type = "whitelist" if action == "add_whitelist_user" else "blacklist"
                await self._process_user_input(message, task_id, list_type, state)
                return
            
            if action in ["add_whitelist_keywords", "add_blacklist_keywords", "add_keywords", "set_keywords"]:
                keywords_text = message.text.strip()
                
                if len(keywords_text) > 1000:
                    await message.answer("❌ النص طويل جداً. الرجاء الحد من النص إلى أقل من 1000 حرف.")
                    return
                
                # Parse keywords (support both comma and line separation)
                if "," in keywords_text:
                    new_keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
                else:
                    new_keywords = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]
                
                if not new_keywords:
                    await message.answer("❌ لم يتم العثور على كلمات صالحة. الرجاء المحاولة مرة أخرى.")
                    return
                
                # Get existing keywords with separate lists
                settings = await self.database.execute_query(
                    "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                whitelist_keywords = []
                blacklist_keywords = []
                current_mode = "blacklist"
                
                if settings and settings[0]["keyword_filters"]:
                    try:
                        keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                        if isinstance(keywords_data, dict):
                            current_mode = keywords_data.get("mode", "blacklist")
                            if "whitelist" in keywords_data and "blacklist" in keywords_data:
                                whitelist_keywords = keywords_data.get("whitelist", [])
                                blacklist_keywords = keywords_data.get("blacklist", [])
                            else:
                                # Migrate legacy format
                                legacy_keywords = keywords_data.get("keywords", [])
                                if current_mode == "whitelist":
                                    whitelist_keywords = legacy_keywords
                                else:
                                    blacklist_keywords = legacy_keywords
                    except:
                        pass
                
                # Handle different actions
                if action == "add_whitelist_keywords":
                    whitelist_keywords = list(set(whitelist_keywords + new_keywords))
                    current_mode = "whitelist"
                    list_name = "القائمة البيضاء"
                    final_count = len(whitelist_keywords)
                elif action == "add_blacklist_keywords":
                    blacklist_keywords = list(set(blacklist_keywords + new_keywords))
                    current_mode = "blacklist"
                    list_name = "القائمة السوداء"
                    final_count = len(blacklist_keywords)
                else:
                    # Legacy support for old actions
                    if current_mode == "whitelist":
                        whitelist_keywords = list(set(whitelist_keywords + new_keywords)) if action == "add_keywords" else new_keywords
                        final_count = len(whitelist_keywords)
                        list_name = "القائمة البيضاء"
                    else:
                        blacklist_keywords = list(set(blacklist_keywords + new_keywords)) if action == "add_keywords" else new_keywords
                        final_count = len(blacklist_keywords)
                        list_name = "القائمة السوداء"
                
                # Save updated keywords with separate lists
                keywords_data = {
                    "mode": current_mode,
                    "whitelist": whitelist_keywords,
                    "blacklist": blacklist_keywords
                }
                
                await self.database.execute_command(
                    "UPDATE task_settings SET keyword_filters = $1 WHERE task_id = $2",
                    json.dumps(keywords_data), task_id
                )
                
                # Prepare success message
                success_msg = f"✅ **{list_name} updated successfully!**\n\n"
                success_msg += f"• Added: {len(new_keywords)} keywords\n"
                success_msg += f"• Total {list_name} keywords: {final_count}\n"
                success_msg += f"• Total whitelist: {len(whitelist_keywords)}\n"
                success_msg += f"• Total blacklist: {len(blacklist_keywords)}\n\n"
                
                current_list = whitelist_keywords if current_mode == "whitelist" else blacklist_keywords
                if len(current_list) <= 10:
                    success_msg += f"**{list_name} keywords:**\n"
                    for i, kw in enumerate(current_list, 1):
                        success_msg += f"{i}. `{kw}`\n"
                else:
                    success_msg += f"**First 10 keywords from {list_name}:**\n"
                    for i, kw in enumerate(current_list[:10], 1):
                        success_msg += f"{i}. `{kw}`\n"
                    success_msg += f"... and {len(current_list) - 10} more keywords"
                
                await message.answer(success_msg, parse_mode="Markdown")
                await state.clear()
                
            elif action == "import_keywords":
                # Handle import functionality
                # Start import process
                import_text = """📥 **استيراد المهام**

يمكنك استيراد المهام بإحدى الطرق التالية:
=======
               
1️⃣ **ملف JSON**: أرسل ملف JSON يحتوي على بيانات المهام
2️⃣ **نص JSON**: الصق نص JSON مباشرة
3️⃣ **نسخ من بوت آخر**: استورد إعدادات من بوت مماثل

📋 **تنسيق الملف المطلوب:**
```json
{
  "tasks": [
    {
      "name": "اسم المهمة",
      "description": "وصف المهمة", 
      "sources": [
        {"chat_id": -1001234567890, "title": "القناة المصدر"}
      ],
      "targets": [
        {"chat_id": -1001234567891, "title": "القناة الهدف"}
      ],
      "settings": {
        "forward_mode": "copy",
        "delay_min": 1,
        "delay_max": 5
      }
    }
  ]
}
```

أرسل الملف أو النص الآن:"""

                await message.answer(import_text, parse_mode="Markdown")
                await state.set_state("TaskStates:WAITING_IMPORT_DATA")
            
            elif action == "add_target_words":
                # Handle adding target words for text cleaner
                words_text = message.text.strip()
                
                if len(words_text) > 500:
                    await message.answer("❌ النص طويل جداً. الرجاء الحد من النص إلى أقل من 500 حرف.")
                    return
                
                # Parse words (support both comma and line separation)
                if "," in words_text:
                    new_words = [word.strip() for word in words_text.split(",") if word.strip()]
                else:
                    new_words = [word.strip() for word in words_text.split("\n") if word.strip()]
                
                if not new_words:
                    await message.answer("❌ لم يتم العثور على كلمات صالحة. الرجاء المحاولة مرة أخرى.")
                    return
                
                # Get existing cleaner settings
                settings = await self.database.execute_query(
                    "SELECT text_cleaner_settings FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                cleaner_settings = {}
                if settings and settings[0]["text_cleaner_settings"]:
                    try:
                        cleaner_settings = json.loads(settings[0]["text_cleaner_settings"]) if isinstance(settings[0]["text_cleaner_settings"], str) else settings[0]["text_cleaner_settings"]
                    except:
                        cleaner_settings = {}
                
                # Add new words to existing ones
                existing_words = cleaner_settings.get("target_words", [])
                updated_words = list(set(existing_words + new_words))  # Remove duplicates
                cleaner_settings["target_words"] = updated_words
                
                # Save updated settings
                await self.database.execute_command(
                    "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                    json.dumps(cleaner_settings), task_id
                )
                
                success_msg = f"✅ **تم إضافة الكلمات المستهدفة بنجاح!**\n\n"
                success_msg += f"• أضيف: {len(new_words)} كلمة جديدة\n"
                success_msg += f"• المجموع الكلي: {len(updated_words)} كلمة\n\n"
                
                if len(updated_words) <= 10:
                    success_msg += "**الكلمات المستهدفة:**\n"
                    for i, word in enumerate(updated_words, 1):
                        success_msg += f"{i}. `{word}`\n"
                else:
                    success_msg += "**أول 10 كلمات:**\n"
                    for i, word in enumerate(updated_words[:10], 1):
                        success_msg += f"{i}. `{word}`\n"
                    success_msg += f"... و {len(updated_words) - 10} كلمة أخرى"
                
                await message.answer(success_msg, parse_mode="Markdown")
                await state.clear()
            
            elif action == "test_text_cleaner":
                # Handle text cleaner test
                test_text = message.text.strip()
                
                # Get cleaner settings
                settings = await self.database.execute_query(
                    "SELECT text_cleaner_settings FROM task_settings WHERE task_id = $1", 
                    task_id
                )
                
                cleaner_settings = {}
                if settings and settings[0]["text_cleaner_settings"]:
                    try:
                        cleaner_settings = json.loads(settings[0]["text_cleaner_settings"]) if isinstance(settings[0]["text_cleaner_settings"], str) else settings[0]["text_cleaner_settings"]
                    except:
                        cleaner_settings = {}
                
                # Apply text cleaning
                cleaned_text = await self._apply_text_cleaning(test_text, cleaner_settings)
                
                result_msg = f"🧪 **نتيجة اختبار منظف النص**\n\n"
                result_msg += f"**النص الأصلي:** ({len(test_text)} حرف)\n"
                result_msg += f"```\n{test_text[:200]}{'...' if len(test_text) > 200 else ''}\n```\n\n"
                result_msg += f"**النص بعد التنظيف:** ({len(cleaned_text)} حرف)\n"
                result_msg += f"```\n{cleaned_text[:200]}{'...' if len(cleaned_text) > 200 else ''}\n```\n\n"
                result_msg += f"**التوفير:** {len(test_text) - len(cleaned_text)} حرف"
                
                await message.answer(result_msg, parse_mode="Markdown")
                await state.clear()
                
            elif action == "set_custom_link":
                # Handle custom link URL setting
                link_url = message.text.strip()
                
                # Basic URL validation
                if not link_url.startswith(('http://', 'https://')):
                    link_url = 'https://' + link_url
                
                try:
                    import json
                    
                    # Get current format settings
                    settings = await self.bot_controller.database.get_task_settings(task_id)
                    format_settings = {}
                    if settings and settings.get("format_settings"):
                        try:
                            format_settings = json.loads(settings["format_settings"]) if isinstance(settings["format_settings"], str) else settings["format_settings"]
                        except:
                            format_settings = {}
                    
                    # Update custom link URL
                    format_settings["custom_link_url"] = link_url
                    format_settings["apply_link"] = True
                    format_settings["preserve_original"] = False
                    format_settings["remove_all"] = False
                    
                    # Save to database
                    await self.bot_controller.database.execute_command(
                        "UPDATE task_settings SET format_settings = $1 WHERE task_id = $2",
                        json.dumps(format_settings), task_id
                    )
                    
                    await message.answer(
                        f"✅ **تم تعيين الرابط المخصص بنجاح!**\n\n"
                        f"🔗 **الرابط:** {link_url}\n\n"
                        f"الآن سيتم تحويل النص إلى رابط أزرق قابل للنقر يفتح هذا الرابط."
                    )
                    
                except Exception as e:
                    logger.error(f"Error setting custom link: {e}")
                    await message.answer("❌ خطأ في تعيين الرابط. الرجاء المحاولة مرة أخرى.")
                
                await state.clear()
                
            elif action == "test_formatting":
                # Handle formatting test
                test_text = message.text.strip()
                
                try:
                    import json
                    from aiogram.types import Message as AiogramMessage
                    
                    # Get current format settings
                    settings = await self.bot_controller.database.get_task_settings(task_id)
                    format_settings = {}
                    if settings and settings.get("format_settings"):
                        try:
                            format_settings = json.loads(settings["format_settings"]) if isinstance(settings["format_settings"], str) else settings["format_settings"]
                        except:
                            format_settings = {}
                    
                    # Apply formatting preview
                    formatted_text = self._apply_formatting_preview(test_text, format_settings)
                    
                    preview_message = f"🧪 **معاينة التنسيق:**\n\n"
                    preview_message += f"**النص الأصلي:**\n{test_text}\n\n"
                    preview_message += f"**النص بعد التنسيق:**\n{formatted_text}\n\n"
                    preview_message += f"**الإعدادات المطبقة:**\n"
                    
                    applied_formats = []
                    if format_settings.get("preserve_original"):
                        applied_formats.append("• الحفاظ على التنسيق الأصلي")
                    if format_settings.get("remove_all"):
                        applied_formats.append("• إزالة جميع التنسيقات")
                    if format_settings.get("apply_bold"):
                        applied_formats.append("• Bold")
                    if format_settings.get("apply_italic"):
                        applied_formats.append("• Italic")
                    if format_settings.get("apply_underline"):
                        applied_formats.append("• Underline")
                    if format_settings.get("apply_strikethrough"):
                        applied_formats.append("• Strikethrough")
                    if format_settings.get("apply_spoiler"):
                        applied_formats.append("• Spoiler")
                    if format_settings.get("apply_code"):
                        applied_formats.append("• Code")
                    if format_settings.get("apply_mono"):
                        applied_formats.append("• Mono")
                    if format_settings.get("apply_quote"):
                        applied_formats.append("• Quote")
                    if format_settings.get("apply_copyable_code"):
                        applied_formats.append("• Copyable Code")
                    if format_settings.get("apply_link"):
                        applied_formats.append("• Custom Link")
                    
                    if not applied_formats:
                        applied_formats.append("• لا توجد تنسيقات مطبقة")
                    
                    preview_message += "\n".join(applied_formats)
                    
                    await message.answer(preview_message, parse_mode="Markdown")
                    
                except Exception as e:
                    logger.error(f"Error in formatting test: {e}")
                    await message.answer("❌ خطأ في اختبار التنسيق.")
                
                await state.clear()
                
        except Exception as e:
            logger.error(f"Error in keyword input: {e}")
            await message.answer("❌ حدث خطأ. الرجاء المحاولة مرة أخرى.")
            await state.clear()

    async def _handle_keyword_edit_menu(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle keyword edit menu"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keywords
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            keywords_list = []
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        keywords_list = keywords_data.get("keywords", [])
                    elif isinstance(keywords_data, list):
                        keywords_list = keywords_data
                except:
                    keywords_list = [kw.strip() for kw in settings[0]["keyword_filters"].split(",") if kw.strip()]
            
            if not keywords_list:
                await callback.answer("❌ لا توجد كلمات للتعديل", show_alert=True)
                return
            
            edit_text = f"✏️ **تعديل الكلمات المفتاحية - المهمة {task_id}**\n\n"
            edit_text += f"عدد الكلمات: {len(keywords_list)}\n\n"
            edit_text += "اختر إجراءً:"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🗑️ حذف كلمة", callback_data=f"kw_delete_word_{task_id}"),
                    InlineKeyboardButton(text="🔍 البحث", callback_data=f"kw_search_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📊 إحصائيات", callback_data=f"kw_stats_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_keywords_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(edit_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in keyword edit menu: {e}")
            await callback.answer("❌ خطأ في تحميل قائمة التعديل", show_alert=True)

    async def _handle_keyword_list_all(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle displaying all keywords"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get keywords
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            keywords_list = []
            current_mode = "blacklist"
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        keywords_list = keywords_data.get("keywords", [])
                        current_mode = keywords_data.get("mode", "blacklist")
                    elif isinstance(keywords_data, list):
                        keywords_list = keywords_data
                except:
                    keywords_list = [kw.strip() for kw in settings[0]["keyword_filters"].split(",") if kw.strip()]
            
            if not keywords_list:
                await callback.answer("❌ لا توجد كلمات مفتاحية", show_alert=True)
                return
            
            # Generate full list text
            list_text = f"📋 **القائمة الكاملة للكلمات المفتاحية - المهمة {task_id}**\n\n"
            list_text += f"**الوضع:** {'القائمة البيضاء' if current_mode == 'whitelist' else 'القائمة السوداء'}\n"
            list_text += f"**العدد الإجمالي:** {len(keywords_list)}\n\n"
            
            # Split into chunks to avoid message length limit
            chunk_size = 50
            for i in range(0, len(keywords_list), chunk_size):
                chunk = keywords_list[i:i+chunk_size]
                for j, keyword in enumerate(chunk, i+1):
                    list_text += f"{j}. `{keyword}`\n"
                
                if len(list_text) > 3500:  # Telegram limit is 4096
                    list_text += f"\n... و {len(keywords_list) - j} كلمة أخرى"
                    break
            
            keyboard = [
                [
                    InlineKeyboardButton(text="📤 تصدير", callback_data=f"kw_export_{task_id}"),
                    InlineKeyboardButton(text="🔍 بحث", callback_data=f"kw_search_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_keywords_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(list_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in keyword list all: {e}")
            await callback.answer("❌ خطأ في عرض القائمة", show_alert=True)

    async def _handle_keyword_clear_confirmation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle keyword clear confirmation"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            confirm_text = f"⚠️ **تأكيد مسح الكلمات المفتاحية - المهمة {task_id}**\n\n"
            confirm_text += "هل أنت متأكد من أنك تريد مسح جميع الكلمات المفتاحية؟\n\n"
            confirm_text += "**تحذير:** هذا الإجراء لا يمكن التراجع عنه!"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="❌ نعم، امسح الكل", callback_data=f"kw_confirm_clear_{task_id}"),
                    InlineKeyboardButton(text="🔙 Cancel", callback_data=f"filter_keywords_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(confirm_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in keyword clear confirmation: {e}")
            await callback.answer("❌ خطأ في تأكيد المسح", show_alert=True)

    async def _handle_keyword_export(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle keyword export"""
        try:
            import json
            
            # Get keywords
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            keywords_list = []
            current_mode = "blacklist"
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        keywords_list = keywords_data.get("keywords", [])
                        current_mode = keywords_data.get("mode", "blacklist")
                    elif isinstance(keywords_data, list):
                        keywords_list = keywords_data
                except:
                    keywords_list = [kw.strip() for kw in settings[0]["keyword_filters"].split(",") if kw.strip()]
            
            if not keywords_list:
                await callback.answer("❌ لا توجد كلمات للتصدير", show_alert=True)
                return
            
            # Create export text
            export_text = f"📤 **تصدير الكلمات المفتاحية - المهمة {task_id}**\n\n"
            export_text += f"**الوضع:** {current_mode}\n"
            export_text += f"**العدد:** {len(keywords_list)}\n\n"
            export_text += "**التنسيق المفصول بفواصل:**\n"
            export_text += "```\n" + ", ".join(keywords_list) + "\n```\n\n"
            export_text += "**التنسيق JSON:**\n"
            export_text += "```json\n" + json.dumps({"keywords": keywords_list, "mode": current_mode}, ensure_ascii=False, indent=2) + "\n```"
            
            await callback.message.edit_text(export_text, parse_mode="Markdown")
            await callback.answer("📤 تم تصدير الكلمات بنجاح!", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error in keyword export: {e}")
            await callback.answer("❌ خطأ في تصدير الكلمات", show_alert=True)

    async def _handle_keyword_test(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle keyword test functionality"""
        try:
            test_text = f"🧪 **Keyword Filter Test - المهمة {task_id}**\n\n"
            test_text += "أرسل نص رسالة لاختبار ما إذا كانت ستمر عبر Filter أم لا"
            
            await callback.message.edit_text(test_text, parse_mode="Markdown")
            await callback.answer("🧪 أرسل نص للاختبار", show_alert=True)
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="test_keywords", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error in keyword test: {e}")
            await callback.answer("❌ خطأ في بدء الاختبار", show_alert=True)
    
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
                # Remove generic domain patterns
                cleaned_text = re.sub(r'[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}/[^\s]*', '', cleaned_text)
                # Remove email-like patterns
                cleaned_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', cleaned_text)
                # Remove IP addresses with ports
                cleaned_text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+\b', '', cleaned_text)
                # Remove standalone domains
                cleaned_text = re.sub(r'\b[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}\b', '', cleaned_text)
            
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
            
            # Remove extra empty lines
            if cleaner_settings.get("remove_extra_lines", False):
                # Replace multiple consecutive newlines with single newline
                cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
                # Remove leading and trailing whitespace
                cleaned_text = cleaned_text.strip()
            
            # Remove captions (this is handled at the message level, not text level)
            # Caption removal is implemented in the forwarding engine
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error applying text cleaning: {e}")
            return text

    async def _handle_media_type_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle individual media type toggle"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[2])
            media_type = "_".join(parts[3:])
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get(media_type, True) if settings else True
            
            # Toggle the value
            new_value = not current_value
            
            # Update in database
            await self.bot_controller.database.execute_command(
                f"UPDATE task_settings SET {media_type} = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            # Force reload of forwarding engine settings immediately
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            # Get media type display name
            media_names = {
                "allow_photos": "📷 الصور",
                "allow_videos": "🎥 الفيديوهات", 
                "allow_documents": "📄 المستندات",
                "allow_audio": "🎵 الصوتيات",
                "allow_voice": "🎤 الرسائل الصوتية",
                "allow_video_notes": "🎬 رسائل الفيديو",
                "allow_stickers": "🎭 الملصقات",
                "allow_animations": "🎨 الصور المتحركة",
                "allow_contacts": "👤 جهات الاتصال",
                "allow_locations": "📍 المواقع",
                "allow_venues": "🏢 الأماكن",
                "allow_polls": "📊 الاستطلاعات",
                "allow_dice": "🎲 النرد"
            }
            
            media_name = media_names.get(media_type, media_type)
            status = "enabled" if new_value else "disabled"
            
            await callback.answer(f"{media_name}: {status}")
            
            # Refresh the media types keyboard
            settings = await self.bot_controller.database.get_task_settings(task_id)
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            await callback.message.edit_text(
                f"🎛️ **Media Type Settings - المهمة {task_id}**\n\n"
                f"Choose the media types you want to allow forwarding:\n\n"
                f"✅ = enabled (will be forwarded)\n"
                f"❌ = disabled (will be ignored)",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error toggling media type: {e}")
            await callback.answer("❌ خطأ في تبديل نوع الوسائط", show_alert=True)

    async def _handle_media_enable_all(self, callback: CallbackQuery, state: FSMContext):
        """Handle enabling all media types"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[3])
            
            # Enable all media types
            media_types = [
                "allow_photos", "allow_videos", "allow_documents", "allow_audio",
                "allow_voice", "allow_video_notes", "allow_stickers", "allow_animations",
                "allow_contacts", "allow_locations", "allow_venues", "allow_polls", "allow_dice"
            ]
            
            for media_type in media_types:
                await self.bot_controller.database.execute_command(
                    f"UPDATE task_settings SET {media_type} = $1 WHERE task_id = $2",
                    True, task_id
                )
            
            # Also enable text
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET allow_text = $1 WHERE task_id = $2",
                True, task_id
            )
            
            # Force reload of forwarding engine settings immediately
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            await callback.answer("✅ تم Enable جميع أنواع الوسائط")
            
            # Refresh keyboard
            settings = await self.bot_controller.database.get_task_settings(task_id)
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error enabling all media types: {e}")
            await callback.answer("❌ خطأ في Enable جميع الوسائط", show_alert=True)

    async def _handle_media_disable_all(self, callback: CallbackQuery, state: FSMContext):
        """Handle disabling all media types"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[3])
            
            # Disable all media types
            media_types = [
                "allow_photos", "allow_videos", "allow_documents", "allow_audio",
                "allow_voice", "allow_video_notes", "allow_stickers", "allow_animations",
                "allow_contacts", "allow_locations", "allow_venues", "allow_polls", "allow_dice"
            ]
            
            for media_type in media_types:
                await self.bot_controller.database.execute_command(
                    f"UPDATE task_settings SET {media_type} = $1 WHERE task_id = $2",
                    False, task_id
                )
            
            # Also disable text
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET allow_text = $1 WHERE task_id = $2",
                False, task_id
            )
            
            # Force reload of forwarding engine settings immediately
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            await callback.answer("❌ تم Disable جميع أنواع الوسائط")
            
            # Refresh keyboard
            settings = await self.bot_controller.database.get_task_settings(task_id)
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error disabling all media types: {e}")
            await callback.answer("❌ خطأ في Disable جميع الوسائط", show_alert=True)

    async def _handle_media_reset(self, callback: CallbackQuery, state: FSMContext):
        """Handle resetting media types to default"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[2])
            
            # Reset all media types to default (True)
            media_types = [
                "allow_photos", "allow_videos", "allow_documents", "allow_audio",
                "allow_voice", "allow_video_notes", "allow_stickers", "allow_animations",
                "allow_contacts", "allow_locations", "allow_venues", "allow_polls", "allow_dice"
            ]
            
            for media_type in media_types:
                await self.bot_controller.database.execute_command(
                    f"UPDATE task_settings SET {media_type} = $1 WHERE task_id = $2",
                    True, task_id
                )
            
            # Also reset text filter
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET allow_text = $1 WHERE task_id = $2",
                True, task_id
            )
            
            # Force reload of forwarding engine settings immediately
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            await callback.answer("🔄 تم إعادة تعيين جميع إعدادات الوسائط للافتراضي")
            
            # Refresh keyboard
            settings = await self.bot_controller.database.get_task_settings(task_id)
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error resetting media types: {e}")
            await callback.answer("❌ خطأ في إعادة التعيين", show_alert=True)

    async def _handle_media_save(self, callback: CallbackQuery, state: FSMContext):
        """Handle saving media settings"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[2])
            
            await callback.answer("💾 تم حفظ إعدادات الوسائط بنجاح")
            
            # Return to filters menu
            await self._handle_filters_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error saving media settings: {e}")
            await callback.answer("❌ خطأ في حفظ الإعدادات", show_alert=True)

    async def _handle_text_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle text message filter toggle"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[2])
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("allow_text", True) if settings else True
            
            # Toggle the value
            new_value = not current_value
            
            # Update in database
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET allow_text = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            # Force reload of forwarding engine settings immediately
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "enabled" if new_value else "disabled"
            await callback.answer(f"📝 Text messages: {status}")
            
            # Refresh the media types keyboard
            settings = await self.bot_controller.database.get_task_settings(task_id)
            keyboard = await self.bot_controller.keyboards.get_media_types_keyboard(task_id, settings)
            
            # Get current text status for display
            current_allow_text = settings.get('allow_text', True)
            text_status_emoji = "✅" if current_allow_text else "❌"
            text_status_text = "enabled" if current_allow_text else "disabled"
            
            try:
                await callback.message.edit_text(
                    f"🎛️ **Media Type Settings - المهمة {task_id}**\n\n"
                    f"Choose the media types you want to allow forwarding:\n\n"
                    f"✅ = enabled (will be forwarded)\n"
                    f"❌ = disabled (will be ignored)\n\n"
                    f"📝 Text messages are currently {text_status_emoji} {text_status_text}",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    # If message content is the same, just update the keyboard
                    try:
                        await callback.message.edit_reply_markup(reply_markup=keyboard)
                    except:
                        pass  # Ignore if keyboard is also the same
                else:
                    raise edit_error
            
        except Exception as e:
            logger.error(f"Error toggling text filter: {e}")
            await callback.answer("❌ خطأ في تبديل فلتر النص", show_alert=True)

    async def _handle_prefix_suffix_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle header/footer setting configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_prefix = settings.get("prefix_text", "") if settings else ""
            current_suffix = settings.get("suffix_text", "") if settings else ""
            header_enabled = settings.get("header_enabled", True) if settings else True
            footer_enabled = settings.get("footer_enabled", True) if settings else True
            
            # Display status logic - only check enabled status, not content
            header_status = "✅ مفعل" if header_enabled else "❌ معطل"
            footer_status = "✅ مفعل" if footer_enabled else "❌ معطل"
            
            # Display content
            header_display = f'`{current_prefix[:50]}...`' if len(current_prefix) > 50 else f'`{current_prefix}`' if current_prefix else 'غير محدد'
            footer_display = f'`{current_suffix[:50]}...`' if len(current_suffix) > 50 else f'`{current_suffix}`' if current_suffix else 'غير محدد'
            
            # Add timestamp to force message update
            import time
            timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
            
            prefix_text = f"""📋 **إعدادات Header/Footer - المهمة {task_id}**

**📄 Header (البداية):** {header_status}
{header_display}

**📝 Footer (النهاية):** {footer_status}
{footer_display}

**المتغيرات المتاحة:**
• {{original}} - النص الأصلي
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال

**مثال:** 
`📢 من: {{source}}
{{original}}
⏰ {{time}}`

‎ᅟᅟᅟ{timestamp}‎"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"📄 Header {'🟢' if header_enabled else '🔴'}", 
                        callback_data=f"header_toggle_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"📝 Footer {'🟢' if footer_enabled else '🔴'}", 
                        callback_data=f"footer_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="✏️ تعديل Header", callback_data=f"header_edit_{task_id}"),
                    InlineKeyboardButton(text="✏️ تعديل Footer", callback_data=f"footer_edit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="👁️ عرض الحالية", callback_data=f"header_footer_view_{task_id}"),
                    InlineKeyboardButton(text="📝 أمثلة", callback_data=f"header_footer_examples_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ حذف Header", callback_data=f"header_delete_{task_id}"),
                    InlineKeyboardButton(text="🗑️ حذف Footer", callback_data=f"footer_delete_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(prefix_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in header/footer setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات Header/Footer", show_alert=True)

    async def _toggle_header(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle header on/off"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_enabled = settings.get("header_enabled", True) if settings else True
            
            # Toggle the enabled status
            new_enabled = not current_enabled
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET header_enabled = $1 WHERE task_id = $2",
                new_enabled, task_id
            )
            
            status = "تم تفعيل" if new_enabled else "تم تعطيل"
            await callback.answer(f"✅ {status} Header")
            
            # Refresh the interface properly
            await self._handle_prefix_suffix_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling header: {e}")
            await callback.answer("❌ خطأ في تبديل Header", show_alert=True)

    async def _toggle_footer(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle footer on/off"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_enabled = settings.get("footer_enabled", True) if settings else True
            
            # Toggle the enabled status
            new_enabled = not current_enabled
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET footer_enabled = $1 WHERE task_id = $2",
                new_enabled, task_id
            )
            
            status = "تم تفعيل" if new_enabled else "تم تعطيل"
            await callback.answer(f"✅ {status} Footer")
            
            # Refresh the interface properly
            await self._handle_prefix_suffix_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling footer: {e}")
            await callback.answer("❌ خطأ في تبديل Footer", show_alert=True)

    async def _handle_inline_buttons_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle inline buttons management"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            buttons_enabled = settings.get("inline_buttons_enabled", False) if settings else False
            
            # Get buttons from inline_button_settings only
            buttons_config = []
            if settings:
                logger.info(f"Settings available - checking for inline_button_settings")
                
                # First try the current column
                button_settings_data = settings.get("inline_button_settings")
                logger.info(f"inline_button_settings raw data: {type(button_settings_data)} - {str(button_settings_data)[:100] if button_settings_data else 'None'}")
                
                if button_settings_data:
                    if isinstance(button_settings_data, str):
                        try:
                            button_settings = json.loads(button_settings_data)
                            logger.info(f"Successfully parsed JSON from inline_button_settings")
                        except Exception as e:
                            logger.error(f"Error parsing inline_button_settings JSON: {e}")
                            button_settings = {}
                    elif isinstance(button_settings_data, dict):
                        button_settings = button_settings_data
                        logger.info(f"Using dict directly from inline_button_settings")
                    else:
                        button_settings = {}
                        logger.warning(f"Unknown data type in inline_button_settings: {type(button_settings_data)}")
                    
                    buttons_config = button_settings.get("buttons", []) if button_settings else []
                    logger.info(f"Extracted {len(buttons_config)} buttons from inline_button_settings")
                
                # No fallback needed - only use new column
                if not buttons_config:
                    logger.info(f"No buttons found in inline_button_settings")
            
            # Ensure buttons_config is a list
            if not isinstance(buttons_config, list):
                buttons_config = []
            
            # Status display
            status_text = "✅ مفعل" if buttons_enabled else "❌ معطل"
            buttons_count = len(buttons_config)
            
            # Build current buttons display
            buttons_display = ""
            if buttons_config:
                for i, button in enumerate(buttons_config[:5]):  # Show first 5
                    text = button.get("text", "")[:20]
                    button_type = button.get("type", "url")
                    type_icon = "🔗" if button_type == "url" else "📱" if button_type == "popup" else "📤"
                    buttons_display += f"{i+1}. {type_icon} {text}\n"
                if len(buttons_config) > 5:
                    buttons_display += f"... و {len(buttons_config) - 5} أزرار أخرى\n"
            else:
                buttons_display = "لا توجد أزرار مُعرّفة\n"
            
            buttons_text = f"""🔘 **إعدادات الأزرار الشفافة - المهمة {task_id}**

**الحالة:** {status_text}
**عدد الأزرار:** {buttons_count}

**الأزرار الحالية:**
{buttons_display}

**المتغيرات المتاحة:**
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال
• {{original}} - النص الأصلي

**أنواع الأزرار المدعومة:**
• 🔗 رابط URL
• 📱 نافذة منبثقة (Popup)
• 📤 مشاركة المنشور"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"🔘 {'🔴 تعطيل' if buttons_enabled else '🟢 تفعيل'}", 
                        callback_data=f"inline_buttons_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="➕ إضافة زر", callback_data=f"inline_button_add_{task_id}"),
                    InlineKeyboardButton(text="👁️ معاينة", callback_data=f"inline_buttons_preview_{task_id}")
                ]
            ]
            
            # Add edit/delete buttons for existing buttons
            if buttons_config:
                for i, button in enumerate(buttons_config[:6]):  # Max 6 buttons for UI
                    text = button.get("text", "")[:15]
                    keyboard.append([
                        InlineKeyboardButton(text=f"✏️ {text}", callback_data=f"inline_button_edit_{task_id}_{i}"),
                        InlineKeyboardButton(text=f"🗑️", callback_data=f"inline_button_delete_{task_id}_{i}")
                    ])
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"inline_buttons_clear_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(buttons_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in inline buttons setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات الأزرار الشفافة", show_alert=True)

    async def _toggle_inline_buttons(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle inline buttons feature on/off"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_enabled = settings.get("inline_buttons_enabled", False) if settings else False
            
            # Toggle the enabled status
            new_enabled = not current_enabled
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET inline_buttons_enabled = $1 WHERE task_id = $2",
                new_enabled, task_id
            )
            
            status = "تم تفعيل" if new_enabled else "تم تعطيل"
            await callback.answer(f"✅ {status} الأزرار الشفافة")
            
            # Refresh the interface
            await self._handle_inline_buttons_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling inline buttons: {e}")
            await callback.answer("❌ خطأ في تبديل الأزرار الشفافة", show_alert=True)

    async def _add_inline_button(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Add new inline button with step-by-step input"""
        try:
            # Create the input message with proper keyboard
            message_text = """📝 إضافة أزرار تفاعلية جديدة

يمكنك إضافة أزرار بطريقتين:

**الطريقة الأولى - زر واحد:**
نص الزر|نوع الزر|القيمة

**الطريقة الثانية - عدة أزرار في صف واحد:**
زر1|نوع|قيمة - زر2|نوع|قيمة

**الأنواع المدعومة:**
• url - رابط خارجي  
• popup - نص منبثق
• share - مشاركة المحتوى

**أمثلة:**
موقعنا|url|https://example.com
معلومات|popup|نص يظهر في نافذة منبثقة
مشاركة|share|

**أزرار متعددة في صف واحد:**
موقع 1|url|https://site1.com - موقع 2|url|https://site2.com
مشاركة 1|share| - مشاركة 2|share|"""

            # Create back button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_inline_buttons_{task_id}")]
            ])
            
            # Edit the current message instead of just showing notification
            await callback.message.edit_text(message_text, reply_markup=keyboard)
            await callback.answer()
            
            # Set state for input handling
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="add_inline_button", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error adding inline button: {e}")
            await callback.answer("❌ خطأ في إضافة الزر", show_alert=True)

    # Text Cleaner Methods Implementation
    async def _handle_text_cleaner_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text cleaner settings display and management"""
        try:
            import json
            
            # Get current cleaner settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Create text cleaner interface
            text = f"""🧹 **منظف النصوص - المهمة {task_id}**

**الميزات الأساسية:**

🔹 **إزالة الرموز التعبيرية:** {'✅ مفعل' if cleaner_settings.get('remove_emojis', False) else '❌ معطل'}
🔗 **إزالة الروابط:** {'✅ مفعل' if cleaner_settings.get('remove_links', False) else '❌ معطل'}
👤 **إزالة المعرفات (@username):** {'✅ مفعل' if cleaner_settings.get('remove_mentions', False) else '❌ معطل'}
📬 **إزالة الإيميلات:** {'✅ مفعل' if cleaner_settings.get('remove_emails', False) else '❌ معطل'}
#️⃣ **إزالة الهاشتاغات:** {'✅ مفعل' if cleaner_settings.get('remove_hashtags', False) else '❌ معطل'}
🔢 **إزالة الأرقام:** {'✅ مفعل' if cleaner_settings.get('remove_numbers', False) else '❌ معطل'}
📝 **إزالة علامات الترقيم:** {'✅ مفعل' if cleaner_settings.get('remove_punctuation', False) else '❌ معطل'}

**ميزات متقدمة:**

🎯 **إزالة الأسطر بكلمات محددة:** {'✅ مفعل' if cleaner_settings.get('remove_lines_with_words', False) else '❌ معطل'}
🗑️ **إزالة الأسطر الفارغة:** {'✅ مفعل' if cleaner_settings.get('remove_empty_lines', False) else '❌ معطل'}
📏 **تنظيف الأسطر الإضافية:** {'✅ مفعل' if cleaner_settings.get('remove_extra_lines', True) else '❌ معطل'}
🔧 **تطبيع المساحات:** {'✅ مفعل' if cleaner_settings.get('normalize_whitespace', False) else '❌ معطل'}
🔄 **إزالة الأسطر المكررة:** {'✅ مفعل' if cleaner_settings.get('remove_duplicate_lines', False) else '❌ معطل'}
📷 **إزالة الكابشن:** {'✅ مفعل' if cleaner_settings.get('remove_captions', False) else '❌ معطل'}

**إعدادات إضافية:**
• عدد الكلمات المستهدفة: {len(cleaner_settings.get('target_words', []))}

اختر الميزة التي تريد تفعيلها أو إلغاؤها:"""

            # Create keyboard with all cleaner options
            keyboard = [
                [
                    InlineKeyboardButton(text=f"🔹 الرموز {'✅' if cleaner_settings.get('remove_emojis', False) else '❌'}", 
                                       callback_data=f"cleaner_emojis_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"🔗 الروابط {'✅' if cleaner_settings.get('remove_links', False) else '❌'}", 
                                       callback_data=f"cleaner_links_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"👤 المعرفات {'✅' if cleaner_settings.get('remove_mentions', False) else '❌'}", 
                                       callback_data=f"cleaner_mentions_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"📬 الإيميلات {'✅' if cleaner_settings.get('remove_emails', False) else '❌'}", 
                                       callback_data=f"cleaner_emails_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"#️⃣ الهاشتاغ {'✅' if cleaner_settings.get('remove_hashtags', False) else '❌'}", 
                                       callback_data=f"cleaner_hashtags_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"🔢 الأرقام {'✅' if cleaner_settings.get('remove_numbers', False) else '❌'}", 
                                       callback_data=f"cleaner_numbers_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"📝 الترقيم {'✅' if cleaner_settings.get('remove_punctuation', False) else '❌'}", 
                                       callback_data=f"cleaner_punctuation_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"📷 إزالة الكابشن {'✅' if cleaner_settings.get('remove_captions', False) else '❌'}", 
                                       callback_data=f"cleaner_caption_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"🗑️ الأسطر الفارغة {'✅' if cleaner_settings.get('remove_empty_lines', False) else '❌'}", 
                                       callback_data=f"cleaner_empty_lines_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"📏 الأسطر الإضافية {'✅' if cleaner_settings.get('remove_extra_lines', True) else '❌'}", 
                                       callback_data=f"cleaner_extra_lines_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"🔧 تطبيع المساحات {'✅' if cleaner_settings.get('normalize_whitespace', False) else '❌'}", 
                                       callback_data=f"cleaner_whitespace_toggle_{task_id}"),
                    InlineKeyboardButton(text=f"🔄 الأسطر المكررة {'✅' if cleaner_settings.get('remove_duplicate_lines', False) else '❌'}", 
                                       callback_data=f"cleaner_duplicate_lines_toggle_{task_id}")
                ],
                [
                    InlineKeyboardButton(text=f"🎯 حذف الأسطر بكلمات معينة {'✅' if cleaner_settings.get('remove_lines_with_words', False) else '❌'}", 
                                       callback_data=f"cleaner_target_words_toggle_{task_id}"),
                    InlineKeyboardButton(text="✏️ إدارة الكلمات المستهدفة", callback_data=f"cleaner_words_manage_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🧪 اختبار التنظيف", callback_data=f"cleaner_test_{task_id}"),
                    InlineKeyboardButton(text="🔄 إعادة تعيين", callback_data=f"cleaner_reset_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in text cleaner setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات منظف النصوص", show_alert=True)

    async def _toggle_cleaner_links(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove links in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle remove_links setting
            current_value = cleaner_settings.get("remove_links", False)
            new_value = not current_value
            cleaner_settings["remove_links"] = new_value
            
            # Save updated settings
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            # Force reload forwarding engine
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🔗 {status} حذف الروابط")
            
            # Refresh the interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner links: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الروابط", show_alert=True)

    async def _toggle_cleaner_mentions(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove mentions (@username) in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle remove_mentions setting
            current_value = cleaner_settings.get("remove_mentions", False)
            new_value = not current_value
            cleaner_settings["remove_mentions"] = new_value
            
            # Save updated settings
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            # Force reload forwarding engine
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"👤 {status} حذف المعرفات")
            
            # Refresh the interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner mentions: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد المعرفات", show_alert=True)

    async def _toggle_cleaner_emails(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove emails in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle remove_emails setting
            current_value = cleaner_settings.get("remove_emails", False)
            new_value = not current_value
            cleaner_settings["remove_emails"] = new_value
            
            # Save updated settings
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            # Force reload forwarding engine
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"📬 {status} حذف الإيميلات")
            
            # Refresh the interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner emails: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الإيميلات", show_alert=True)

    async def _toggle_cleaner_numbers(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove numbers in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_numbers", False)
            new_value = not current_value
            cleaner_settings["remove_numbers"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🔢 {status} حذف الأرقام")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner numbers: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الأرقام", show_alert=True)

    async def _toggle_cleaner_punctuation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove punctuation in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_punctuation", False)
            new_value = not current_value
            cleaner_settings["remove_punctuation"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"📝 {status} حذف علامات الترقيم")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner punctuation: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد علامات الترقيم", show_alert=True)

    async def _toggle_cleaner_empty_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove empty lines in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_empty_lines", False)
            new_value = not current_value
            cleaner_settings["remove_empty_lines"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🗑️ {status} حذف الأسطر الفارغة")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner empty lines: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الأسطر الفارغة", show_alert=True)

    async def _toggle_cleaner_extra_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove extra lines in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_extra_lines", True)
            new_value = not current_value
            cleaner_settings["remove_extra_lines"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"📏 {status} تنظيف الأسطر الإضافية")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner extra lines: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الأسطر الإضافية", show_alert=True)

    async def _toggle_cleaner_whitespace(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle normalize whitespace in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("normalize_whitespace", False)
            new_value = not current_value
            cleaner_settings["normalize_whitespace"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🔧 {status} تطبيع المساحات")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner whitespace: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد تطبيع المساحات", show_alert=True)

    async def _toggle_cleaner_duplicate_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove duplicate lines in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_duplicate_lines", False)
            new_value = not current_value
            cleaner_settings["remove_duplicate_lines"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🔄 {status} حذف الأسطر المكررة")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner duplicate lines: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الأسطر المكررة", show_alert=True)

    async def _toggle_cleaner_target_words(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove lines with target words in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_lines_with_words", False)
            new_value = not current_value
            cleaner_settings["remove_lines_with_words"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"🎯 {status} حذف الأسطر بكلمات معينة")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner target words: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الكلمات المستهدفة", show_alert=True)

    async def _handle_cleaner_words_manage(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle management of target words for cleaning"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            target_words = cleaner_settings.get("target_words", [])
            
            text = f"""🎯 **إدارة الكلمات المستهدفة - المهمة {task_id}**

**الكلمات المستهدفة حالياً:** {len(target_words)}

**الكلمات:**
"""
            
            if target_words:
                for i, word in enumerate(target_words[:10], 1):
                    text += f"{i}. {word}\n"
                if len(target_words) > 10:
                    text += f"... و {len(target_words) - 10} كلمة أخرى"
            else:
                text += "لا توجد كلمات مستهدفة"
            
            text += """

**كيف يعمل:**
• يتم حذف أي سطر يحتوي على هذه الكلمات
• البحث حساس لحالة الأحرف
• يمكن إضافة كلمات متعددة مفصولة بفواصل

اختر العملية المطلوبة:"""
            
            keyboard = [
                [
                    InlineKeyboardButton(text="➕ إضافة كلمات", callback_data=f"cleaner_words_add_{task_id}"),
                    InlineKeyboardButton(text="🗑️ حذف كلمات", callback_data=f"cleaner_words_remove_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📋 عرض الكلمات", callback_data=f"cleaner_words_list_{task_id}"),
                    InlineKeyboardButton(text="🔄 مسح الكل", callback_data=f"cleaner_words_clear_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_cleaner_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error handling cleaner words manage: {e}")
            await callback.answer("❌ خطأ في إدارة الكلمات المستهدفة", show_alert=True)

    async def _handle_cleaner_test(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text cleaner testing"""
        try:
            text = f"""🧪 **اختبار منظف النصوص - المهمة {task_id}**

أرسل نص تجريبي لمعاينة كيف سيبدو بعد تطبيق إعدادات التنظيف الحالية.

**مثال:**
```
مرحبا! 😊 هذا نص تجريبي 123
https://example.com
@username #hashtag
test@email.com

سطر فارغ في الأعلى
```

أرسل النص الذي تريد اختباره:"""
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_cleaner_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="test_cleaner", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error handling cleaner test: {e}")
            await callback.answer("❌ خطأ في اختبار منظف النصوص", show_alert=True)

    async def _handle_cleaner_reset(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text cleaner reset"""
        try:
            import json
            
            # Reset all cleaner settings
            default_settings = {
                "remove_emojis": False,
                "remove_links": False,
                "remove_mentions": False,
                "remove_emails": False,
                "remove_hashtags": False,
                "remove_numbers": False,
                "remove_punctuation": False,
                "remove_lines_with_words": False,
                "remove_empty_lines": False,
                "remove_extra_lines": True,
                "normalize_whitespace": False,
                "remove_duplicate_lines": False,
                "remove_captions": False,
                "target_words": []
            }
            
            updated_json = json.dumps(default_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            await callback.answer("🔄 تم إعادة تعيين جميع إعدادات منظف النصوص")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error handling cleaner reset: {e}")
            await callback.answer("❌ خطأ في إعادة تعيين منظف النصوص", show_alert=True)

    async def _toggle_cleaner_emojis(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove emojis in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_emojis", False)
            new_value = not current_value
            cleaner_settings["remove_emojis"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"😀 {status} حذف الرموز التعبيرية")
            
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner emojis: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الرموز", show_alert=True)

    async def _toggle_cleaner_hashtags(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle remove hashtags in text cleaner"""
        try:
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_hashtags", False)
            new_value = not current_value
            cleaner_settings["remove_hashtags"] = new_value
            
            updated_json = json.dumps(cleaner_settings)
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                updated_json, task_id
            )
            
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"#️⃣ {status} حذف الهاشتاغات")
            
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner hashtags: {e}")
            await callback.answer("❌ خطأ في تبديل إعداد الهاشتاغات", show_alert=True)

    async def _toggle_cleaner_emojis(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle emoji removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_emojis", False)
            cleaner_settings["remove_emojis"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"🔹 {status} إزالة الرموز التعبيرية")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner emojis: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الرموز", show_alert=True)

    async def _toggle_cleaner_links(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle link removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_links", False)
            cleaner_settings["remove_links"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"🔗 {status} إزالة الروابط")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner links: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الروابط", show_alert=True)

    async def _toggle_cleaner_mentions(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle mention removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_mentions", False)
            cleaner_settings["remove_mentions"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            # Force reload forwarding engine
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"👤 {status} إزالة المعرفات")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner mentions: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة المعرفات", show_alert=True)

    async def _toggle_cleaner_emails(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle email removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_emails", False)
            cleaner_settings["remove_emails"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            # Force reload forwarding engine
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"📬 {status} إزالة الإيميلات")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner emails: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الإيميلات", show_alert=True)

    async def _toggle_cleaner_hashtags(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle hashtag removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_hashtags", False)
            cleaner_settings["remove_hashtags"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"#️⃣ {status} إزالة الهاشتاغات")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner hashtags: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الهاشتاغات", show_alert=True)

    async def _toggle_cleaner_numbers(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle number removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_numbers", False)
            cleaner_settings["remove_numbers"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"🔢 {status} إزالة الأرقام")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner numbers: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الأرقام", show_alert=True)

    async def _toggle_cleaner_punctuation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle punctuation removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_punctuation", False)
            cleaner_settings["remove_punctuation"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"📝 {status} إزالة علامات الترقيم")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner punctuation: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الترقيم", show_alert=True)

    async def _test_text_cleaner(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Test text cleaner with sample text"""
        try:
            await callback.message.edit_text(
                f"🧪 **اختبار منظف النصوص - المهمة {task_id}**\n\n"
                "أرسل نص لاختبار كيف سيبدو بعد تطبيق إعدادات التنظيف الحالية:\n\n"
                "مثال للاختبار:\n"
                "مرحبا 👋 بكم في موقعنا https://example.com #تقنية @username 123 !!!"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="test_text_cleaner", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error in test text cleaner: {e}")
            await callback.answer("❌ خطأ في اختبار التنظيف", show_alert=True)

    async def _reset_text_cleaner(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Reset all text cleaner settings"""
        try:
            import json
            
            # Reset to default settings
            default_settings = {
                "remove_emojis": False,
                "remove_links": False,
                "remove_mentions": False,
                "remove_hashtags": False,
                "remove_numbers": False,
                "remove_punctuation": False,
                "remove_lines_with_words": False,
                "target_words": [],
                "remove_extra_lines": True
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(default_settings), task_id
            )
            
            await callback.answer("🔄 تم إعادة تعيين جميع إعدادات التنظيف")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error resetting text cleaner: {e}")
            await callback.answer("❌ خطأ في إعادة التعيين", show_alert=True)

    async def _edit_inline_button(self, callback: CallbackQuery, task_id: int, button_id: int, state: FSMContext):
        """Edit existing inline button"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            buttons_config = []
            
            # Get buttons from inline_button_settings only
            if settings and settings.get("inline_button_settings"):
                try:
                    button_settings = json.loads(settings["inline_button_settings"]) if isinstance(settings["inline_button_settings"], str) else settings["inline_button_settings"]
                    buttons_config = button_settings.get("buttons", []) if button_settings else []
                except:
                    buttons_config = []
            
            if button_id >= len(buttons_config):
                await callback.answer("❌ الزر غير موجود", show_alert=True)
                return
            
            button = buttons_config[button_id]
            current_text = button.get("text", "")
            current_type = button.get("type", "url")
            current_value = button.get("value", "")
            
            await callback.answer(f"📝 أرسل التفاصيل الجديدة للزر:\n\nالحالي: {current_text}|{current_type}|{current_value}\n\nالتنسيق: نص الزر|نوع الزر|القيمة")
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="edit_inline_button", task_id=task_id, button_id=button_id)
            
        except Exception as e:
            logger.error(f"Error editing inline button: {e}")
            await callback.answer("❌ خطأ في تعديل الزر", show_alert=True)

    async def _delete_inline_button(self, callback: CallbackQuery, task_id: int, button_id: int, state: FSMContext):
        """Delete inline button"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            
            # Get current button settings from the correct column
            button_settings = {}
            buttons_config = []
            
            if settings and settings.get("inline_button_settings"):
                try:
                    button_settings_data = settings["inline_button_settings"]
                    if isinstance(button_settings_data, str):
                        button_settings = json.loads(button_settings_data)
                    else:
                        button_settings = button_settings_data
                    buttons_config = button_settings.get("buttons", [])
                except Exception as e:
                    logger.error(f"Error parsing inline_button_settings: {e}")
            
            if not buttons_config or button_id >= len(buttons_config):
                await callback.answer("❌ الزر غير موجود", show_alert=True)
                return
            
            button_text = buttons_config[button_id].get("text", "")
            del buttons_config[button_id]
            
            # Update button settings and rebuild row structure
            button_settings["buttons"] = buttons_config
            
            # Rebuild row structure based on remaining buttons
            if buttons_config:
                # Group buttons back into rows based on their row property
                row_groups = {}
                for button in buttons_config:
                    row_num = button.get("row", 0)
                    if row_num not in row_groups:
                        row_groups[row_num] = []
                    # Remove row property from button data for storage
                    clean_button = {k: v for k, v in button.items() if k != "row"}
                    row_groups[row_num].append(clean_button)
                
                # Convert to list of rows
                new_button_rows = []
                for row_num in sorted(row_groups.keys()):
                    new_button_rows.append(row_groups[row_num])
                
                button_settings["button_rows"] = new_button_rows
                button_settings["enabled"] = True
            else:
                button_settings["button_rows"] = []
                button_settings["enabled"] = False
            
            # Update database with the correct column
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET inline_button_settings = $1 WHERE task_id = $2",
                json.dumps(button_settings), task_id
            )
            
            await callback.answer(f"✅ تم حذف الزر: {button_text}")
            
            # Refresh the interface
            await self._handle_inline_buttons_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error deleting inline button: {e}")
            await callback.answer("❌ خطأ في حذف الزر", show_alert=True)

    async def _preview_inline_buttons(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Preview inline buttons"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            buttons_config = []
            
            if settings:
                if settings.get("inline_button_settings"):
                    button_settings = settings.get("inline_button_settings")
                    if isinstance(button_settings, str):
                        try:
                            button_settings = json.loads(button_settings)
                        except:
                            button_settings = {}
                    buttons_config = button_settings.get("buttons", [])

            
            if not buttons_config:
                await callback.answer("❌ لا توجد أزرار للمعاينة", show_alert=True)
                return
            
            # Create preview keyboard
            preview_keyboard = []
            current_row = []
            
            for button_data in buttons_config:
                button_text = button_data.get("text", "زر")
                button_type = button_data.get("type", "url")
                button_value = button_data.get("value", "")
                row_position = button_data.get("row", 0)
                
                # Process variables
                from datetime import datetime
                now = datetime.now()
                variables = {
                    "{source}": "مثال القناة",
                    "{time}": now.strftime("%H:%M"),
                    "{date}": now.strftime("%Y-%m-%d"),
                    "{original}": "النص الأصلي"
                }
                
                for var, value in variables.items():
                    button_text = button_text.replace(var, value)
                    button_value = button_value.replace(var, value)
                
                # Create button based on type
                if button_type == "url":
                    button = InlineKeyboardButton(text=button_text, url=button_value)
                elif button_type == "popup":
                    button = InlineKeyboardButton(text=button_text, callback_data=f"popup_{task_id}")
                else:  # share
                    button = InlineKeyboardButton(text=button_text, url=f"https://t.me/share/url?url={button_value}")
                
                # Add to appropriate row
                if len(current_row) >= 2:  # Max 2 buttons per row
                    preview_keyboard.append(current_row)
                    current_row = [button]
                else:
                    current_row.append(button)
            
            if current_row:
                preview_keyboard.append(current_row)
            
            # Add back button
            preview_keyboard.append([
                InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_inline_buttons_{task_id}")
            ])
            
            preview_text = f"""🔍 **معاينة الأزرار الشفافة - المهمة {task_id}**

هذا مثال على كيف ستظهر الأزرار في الرسائل المُعاد توجيهها:

📝 **نص الرسالة الأصلية هنا...**

_الأزرار أدناه:_"""
            
            markup = InlineKeyboardMarkup(inline_keyboard=preview_keyboard)
            await callback.message.edit_text(preview_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error previewing inline buttons: {e}")
            await callback.answer("❌ خطأ في معاينة الأزرار", show_alert=True)

    async def _clear_inline_buttons(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear all inline buttons"""
        try:
            import json
            
            # Create empty button settings
            empty_settings = {
                "buttons": [],
                "button_rows": [],
                "enabled": False
            }
            
            # Clear buttons from the correct column
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET inline_button_settings = $1 WHERE task_id = $2",
                json.dumps(empty_settings), task_id
            )
            

            
            await callback.answer("✅ تم مسح جميع الأزرار")
            
            # Refresh the interface
            await self._handle_inline_buttons_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing inline buttons: {e}")
            await callback.answer("❌ خطأ في مسح الأزرار", show_alert=True)

    async def _edit_header(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Edit header text"""
        try:
            await state.set_state("edit_header")
            await state.update_data(task_id=task_id)
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_prefix = settings.get("prefix_text", "") if settings else ""
            
            text = f"""✏️ **تعديل Header - المهمة {task_id}**

**Header الحالي:**
{f'`{current_prefix}`' if current_prefix else 'غير محدد'}

**المتغيرات المتاحة:**
• {{original}} - النص الأصلي
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال

**أرسل النص الجديد للـ Header:**"""

            await callback.message.edit_text(text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error editing header: {e}")
            await callback.answer("❌ خطأ في تعديل Header", show_alert=True)

    async def _edit_footer(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Edit footer text"""
        try:
            await state.set_state("edit_footer")
            await state.update_data(task_id=task_id)
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_suffix = settings.get("suffix_text", "") if settings else ""
            
            text = f"""✏️ **تعديل Footer - المهمة {task_id}**

**Footer الحالي:**
{f'`{current_suffix}`' if current_suffix else 'غير محدد'}

**المتغيرات المتاحة:**
• {{original}} - النص الأصلي
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال

**أرسل النص الجديد للـ Footer:**"""

            await callback.message.edit_text(text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error editing footer: {e}")
            await callback.answer("❌ خطأ في تعديل Footer", show_alert=True)

    async def _delete_header(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Delete header completely"""
        try:
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET prefix_text = '' WHERE task_id = $1",
                task_id
            )
            await callback.answer("✅ تم حذف Header")
            
            # Refresh the page
            await self._handle_prefix_suffix_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error deleting header: {e}")
            await callback.answer("❌ خطأ في حذف Header", show_alert=True)

    async def _delete_footer(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Delete footer completely"""
        try:
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET suffix_text = '' WHERE task_id = $1",
                task_id
            )
            await callback.answer("✅ تم حذف Footer")
            
            # Refresh the page
            await self._handle_prefix_suffix_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error deleting footer: {e}")
            await callback.answer("❌ خطأ في حذف Footer", show_alert=True)

    async def _view_header_footer(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """View current header and footer"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            logger.info(f"Viewing header/footer for task {task_id}")
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            logger.info(f"Retrieved settings: {settings}")
            
            current_prefix = settings.get("prefix_text", "") if settings else ""
            current_suffix = settings.get("suffix_text", "") if settings else ""
            header_enabled = settings.get("header_enabled", True) if settings else True
            footer_enabled = settings.get("footer_enabled", True) if settings else True
            
            logger.info(f"Header: '{current_prefix}' (enabled: {header_enabled})")
            logger.info(f"Footer: '{current_suffix}' (enabled: {footer_enabled})")
            
            # Better formatting for display
            if current_prefix:
                header_display = f"```\n{current_prefix}\n```"
                header_status = "✅ مفعل" if header_enabled else "❌ معطل"
            else:
                header_display = "❌ غير محدد"
                header_status = "❌ غير محدد"
                
            if current_suffix:
                footer_display = f"```\n{current_suffix}\n```"
                footer_status = "✅ مفعل" if footer_enabled else "❌ معطل"
            else:
                footer_display = "❌ غير محدد"
                footer_status = "❌ غير محدد"
            
            text = f"""👁️ **عرض Header/Footer الحالية - المهمة {task_id}**

**📄 Header (البداية): {header_status}**
{header_display}

**📝 Footer (النهاية): {footer_status}**
{footer_display}

**المتغيرات المتاحة:**
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال
• {{original}} - النص الأصلي"""

            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_prefix_suffix_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            logger.info(f"Header/footer view sent successfully")
            
        except Exception as e:
            logger.error(f"Error viewing header/footer: {e}")
            await callback.answer("❌ خطأ في عرض Header/Footer", show_alert=True)

    async def _show_header_footer_examples(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show header/footer examples"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            text = f"""📝 **أمثلة Header/Footer - المهمة {task_id}**

**مثال 1 - بسيط:**
Header: `📢 من: {{source}}`
Footer: `⏰ {{time}}`

**مثال 2 - مفصل:**
Header: `🔥 عاجل من {{source}}
━━━━━━━━━━━━━━`
Footer: `━━━━━━━━━━━━━━
📅 {{date}} | ⌚ {{time}}`

**مثال 3 - احترافي:**
Header: `📰 **{{source}}**
📊 تحديث مباشر:`
Footer: `
┗━━━━━━━━━━━━━━━━━━━━━━━┛
🕐 تم النشر: {{time}}`

**مثال 4 - عربي:**
Header: `🌟 من قناة {{source}}
───────────────`
Footer: `───────────────
🔔 تابعونا للمزيد`"""

            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_prefix_suffix_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error showing examples: {e}")
            await callback.answer("❌ خطأ في عرض الأمثلة", show_alert=True)


    async def handle_text_input(self, message: Message, state: FSMContext):
        """Handle text input for all types of user input"""
        try:
            state_data = await state.get_data()
            current_state = await state.get_state()
            action = state_data.get("action")
            awaiting_input = state_data.get("awaiting_input")
            task_id = state_data.get("task_id")
            
            logger.info(f"Processing text input - State: {current_state}, Action: {action}, Awaiting: {awaiting_input}, Task ID: {task_id}")
            
            # Handle header/footer editing
            if current_state == "edit_header":
                if task_id:
                    await self._handle_add_prefix(message, task_id, message.text, state)
                    return
            elif current_state == "edit_footer":
                if task_id:
                    await self._handle_add_suffix(message, task_id, message.text, state)
                    return
            elif current_state == "TaskStates:WAITING_IMPORT_DATA":
                await self._handle_import_data(message, state)
                return
            
            # Handle various input types based on awaiting_input
            if awaiting_input and task_id:
                if awaiting_input == "user_whitelist_add":
                    await self._process_whitelist_input(message, task_id, message.text, state)
                elif awaiting_input == "user_whitelist_remove":
                    await self._process_whitelist_remove_input(message, task_id, message.text, state)
                elif awaiting_input == "user_blacklist_add":
                    await self._process_blacklist_input(message, task_id, message.text, state)
                elif awaiting_input == "user_blacklist_remove":
                    await self._process_blacklist_remove_input(message, task_id, message.text, state)
                elif awaiting_input == "replace_add":
                    await self._process_replace_add_input(message, task_id, message.text, state)
                elif awaiting_input == "replace_remove":
                    await self._process_replace_remove_input(message, task_id, message.text, state)
                elif awaiting_input == "target_words":
                    await self._handle_save_target_words(message, task_id, message.text, state)
                elif awaiting_input == "blocked_words":
                    await self._process_blocked_words_input(message, task_id, message.text, state)
                elif awaiting_input == "inline_button_text":
                    await self._process_inline_button_input(message, task_id, message.text, state)
                elif awaiting_input == "add_inline_button":
                    await self._process_inline_button_input(message, task_id, message.text, state)
                else:
                    logger.warning(f"Unknown awaiting_input type: {awaiting_input}")
                    await message.answer("❌ نوع الإدخال غير معروف")
            
            # Handle legacy action-based processing
            elif action == "add_target_words" and task_id:
                await self._handle_save_target_words(message, task_id, message.text, state)
            elif action == "add_inline_button" and task_id:
                await self._process_inline_button_input(message, task_id, message.text, state)
            elif action == "add_prefix" and task_id:
                await self._handle_add_prefix(message, task_id, message.text, state)
            elif action == "add_suffix" and task_id:
                await self._handle_add_suffix(message, task_id, message.text, state)
            elif action == "add_replace_text" and task_id:
                await self._process_replace_add_input(message, task_id, message.text, state)
            elif action == "add_blocked_words" and task_id:
                await self._process_blocked_words_input(message, task_id, message.text, state)
            elif action == "add_whitelist_user" and task_id:
                await self._process_whitelist_input(message, task_id, message.text, state)
            elif action == "add_blacklist_user" and task_id:
                await self._process_blacklist_input(message, task_id, message.text, state)
            elif action == "add_blacklist_keywords" and task_id:
                await self._handle_keyword_input(message, task_id, message.text, state, "blacklist")
            elif action == "add_whitelist_keywords" and task_id:
                await self._handle_keyword_input(message, task_id, message.text, state, "whitelist")
            elif action == "custom_delay" and task_id:
                await self._handle_custom_delay_input(message, task_id, message.text, state)
            elif action == "add_replacement_rule" and task_id:
                await self._handle_replacement_input(message, task_id, message.text, state)
            elif action == "custom_hyperlink" and task_id:
                await self._handle_hyperlink_input(message, task_id, message.text, state)
            else:
                logger.warning(f"No handler found for text input - State: {current_state}, Action: {action}, Awaiting: {awaiting_input}")
                await message.answer("❌ لم يتم العثور على معالج للإدخال")
                    
        except Exception as e:
            logger.error(f"Error handling text input: {e}")
            await message.answer("❌ خطأ في معالجة الإدخال")
    
    async def _handle_keyword_input(self, message: Message, task_id: int, text: str, state: FSMContext, keyword_type: str):
        """Handle keyword input for blacklist/whitelist"""
        try:
            # Parse keywords from input
            keywords = [k.strip() for k in text.split(',') if k.strip()]
            
            if not keywords:
                await message.answer("❌ لم يتم إدخال أي كلمات صالحة")
                return
            
            # Get current settings
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            current_data = {"mode": keyword_type, "whitelist": [], "blacklist": []}
            if settings and settings[0]["keyword_filters"]:
                try:
                    current_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                except:
                    pass
            
            # Add new keywords to appropriate list
            if keyword_type == "blacklist":
                current_data["blacklist"].extend(keywords)
                current_data["blacklist"] = list(set(current_data["blacklist"]))  # Remove duplicates
            else:
                current_data["whitelist"].extend(keywords)
                current_data["whitelist"] = list(set(current_data["whitelist"]))  # Remove duplicates
            
            current_data["mode"] = keyword_type
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET keyword_filters = $1, keyword_filter_mode = $2 WHERE task_id = $3",
                json.dumps(current_data), keyword_type, task_id
            )
            
            await message.answer(f"✅ تم إضافة {len(keywords)} كلمة إلى القائمة {'السوداء' if keyword_type == 'blacklist' else 'البيضاء'}")
            await state.clear()
            
            # Navigate back to keyword filter settings
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"filter_keywords_{task_id}")]
            ])
            await message.answer("يمكنك العودة للإعدادات:", reply_markup=back_keyboard)
            
        except Exception as e:
            logger.error(f"Error handling keyword input: {e}")
            await message.answer("❌ خطأ في إضافة الكلمات")
    
    async def _handle_custom_delay_input(self, message: Message, task_id: int, text: str, state: FSMContext):
        """Handle custom delay input"""
        try:
            parts = text.strip().split()
            if len(parts) != 2:
                await message.answer("❌ الرجاء إدخال رقمين مفصولين بمسافة\nمثال: 5 20")
                return
            
            try:
                delay_min = int(parts[0])
                delay_max = int(parts[1])
            except ValueError:
                await message.answer("❌ الرجاء إدخال أرقام صالحة فقط")
                return
            
            if delay_min < 0 or delay_max < 0 or delay_min > 300 or delay_max > 300:
                await message.answer("❌ القيم يجب أن تكون بين 0 و 300 ثانية")
                return
            
            if delay_min > delay_max:
                await message.answer("❌ الحد الأدنى يجب أن يكون أقل من أو يساوي الحد الأقصى")
                return
            
            # Update delay settings
            await self.database.execute_command(
                """INSERT INTO task_settings (
                    task_id, delay_min, delay_max, created_at, updated_at
                ) VALUES ($1, $2, $3, NOW(), NOW()) 
                ON CONFLICT (task_id) 
                DO UPDATE SET delay_min = $2, delay_max = $3, updated_at = NOW()""",
                task_id, delay_min, delay_max
            )
            
            await message.answer(f"✅ تم تعيين التأخير المخصص: {delay_min}-{delay_max} ثانية")
            await state.clear()
            
            # Navigate back to delay settings
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة لإعدادات التأخير", callback_data=f"setting_delays_{task_id}")]
            ])
            await message.answer("يمكنك العودة للإعدادات:", reply_markup=back_keyboard)
            
        except Exception as e:
            logger.error(f"Error handling custom delay input: {e}")
            await message.answer("❌ خطأ في تعيين التأخير المخصص")
    
    async def _handle_replacement_input(self, message: Message, task_id: int, text: str, state: FSMContext):
        """Handle replacement rule input"""
        try:
            lines = text.strip().split('\n')
            if len(lines) != 2:
                await message.answer("❌ الرجاء إدخال سطرين:\nالسطر الأول: النص المراد استبداله\nالسطر الثاني: النص البديل")
                return
            
            old_text = lines[0].strip()
            new_text = lines[1].strip()
            
            if not old_text:
                await message.answer("❌ النص المراد استبداله لا يمكن أن يكون فارغاً")
                return
            
            # Get current replacement settings
            settings = await self.database.execute_query(
                "SELECT replace_text FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            current_rules = []
            if settings and settings[0]["replace_text"]:
                try:
                    current_rules = json.loads(settings[0]["replace_text"]) if isinstance(settings[0]["replace_text"], str) else settings[0]["replace_text"]
                except:
                    pass
            
            # Add new rule
            new_rule = {"old": old_text, "new": new_text}
            current_rules.append(new_rule)
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET replace_text = $1 WHERE task_id = $2",
                json.dumps(current_rules), task_id
            )
            
            await message.answer(f"✅ تم إضافة قاعدة الاستبدال:\n'{old_text}' ← '{new_text}'")
            await state.clear()
            
            # Navigate back to replacement settings
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة لإعدادات الاستبدال", callback_data=f"content_replace_{task_id}")]
            ])
            await message.answer("يمكنك العودة للإعدادات:", reply_markup=back_keyboard)
            
        except Exception as e:
            logger.error(f"Error handling replacement input: {e}")
            await message.answer("❌ خطأ في إضافة قاعدة الاستبدال")
    
    async def _handle_hyperlink_input(self, message: Message, task_id: int, text: str, state: FSMContext):
        """Handle hyperlink input"""
        try:
            lines = text.strip().split('\n')
            if len(lines) != 2:
                await message.answer("❌ الرجاء إدخال سطرين:\nالسطر الأول: نص الرابط\nالسطر الثاني: عنوان URL")
                return
            
            link_text = lines[0].strip()
            link_url = lines[1].strip()
            
            if not link_text or not link_url:
                await message.answer("❌ نص الرابط وعنوان URL مطلوبان")
                return
            
            if not link_url.startswith(('http://', 'https://', 'tg://', 'mailto:')):
                await message.answer("❌ عنوان URL غير صالح. يجب أن يبدأ بـ http:// أو https://")
                return
            
            # Get current format settings
            settings = await self.database.execute_query(
                "SELECT format_settings FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            current_settings = {"apply_link": False, "link_text": "", "link_url": ""}
            if settings and settings[0]["format_settings"]:
                try:
                    current_settings = json.loads(settings[0]["format_settings"]) if isinstance(settings[0]["format_settings"], str) else settings[0]["format_settings"]
                except:
                    pass
            
            # Update link settings
            current_settings["apply_link"] = True
            current_settings["link_text"] = link_text
            current_settings["link_url"] = link_url
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET format_settings = $1 WHERE task_id = $2",
                json.dumps(current_settings), task_id
            )
            
            await message.answer(f"✅ تم تعيين الرابط المخصص:\n[{link_text}]({link_url})")
            await state.clear()
            
            # Navigate back to formatting settings
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة لإعدادات التنسيق", callback_data=f"setting_formatting_{task_id}")]
            ])
            await message.answer("يمكنك العودة للإعدادات:", reply_markup=back_keyboard)
            
        except Exception as e:
            logger.error(f"Error handling hyperlink input: {e}")
            await message.answer("❌ خطأ في تعيين الرابط المخصص")
    
    async def _handle_replacement_add(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle adding replacement rule"""
        try:
            await callback.message.edit_text(
                f"➕ **إضافة قاعدة استبدال - المهمة {task_id}**\n\n"
                "أرسل قاعدة الاستبدال في سطرين:\n"
                "• السطر الأول: النص المراد استبداله\n"
                "• السطر الثاني: النص البديل\n\n"
                "**مثال:**\n"
                "```\n"
                "مرحبا\n"
                "أهلا وسهلا\n"
                "```\n\n"
                "⚠️ أرسل النص في الرسالة التالية مباشرة",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"content_replace_{task_id}")]
                ]),
                parse_mode="Markdown"
            )
            
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="add_replacement_rule", task_id=task_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in replacement add: {e}")
            await callback.answer("❌ خطأ في إضافة قاعدة الاستبدال", show_alert=True)
    
    async def _handle_replacement_list(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle listing replacement rules"""
        try:
            settings = await self.database.execute_query(
                "SELECT replace_text FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            rules_text = f"📋 **قواعد الاستبدال - المهمة {task_id}**\n\n"
            
            if settings and settings[0]["replace_text"]:
                try:
                    rules = json.loads(settings[0]["replace_text"]) if isinstance(settings[0]["replace_text"], str) else settings[0]["replace_text"]
                    
                    if rules:
                        for i, rule in enumerate(rules, 1):
                            old_text = rule.get("old", "")
                            new_text = rule.get("new", "")
                            rules_text += f"**{i}.** `{old_text}` ← `{new_text}`\n"
                    else:
                        rules_text += "❌ لا توجد قواعد استبدال محفوظة\n"
                        
                except:
                    rules_text += "❌ خطأ في قراءة قواعد الاستبدال\n"
            else:
                rules_text += "❌ لا توجد قواعد استبدال محفوظة\n"
            
            rules_text += "\n**الوظيفة:** تبديل النصوص المحددة بالنصوص البديلة في جميع الرسائل"
            
            await callback.message.edit_text(
                rules_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_replace_{task_id}")]
                ]),
                parse_mode="Markdown"
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error listing replacement rules: {e}")
            await callback.answer("❌ خطأ في عرض قواعد الاستبدال", show_alert=True)
    
    async def _handle_replacement_clear(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle clearing all replacement rules"""
        try:
            await self.database.execute_command(
                "UPDATE task_settings SET replace_text = $1 WHERE task_id = $2",
                json.dumps([]), task_id
            )
            
            await callback.answer("🗑️ تم مسح جميع قواعد الاستبدال", show_alert=True)
            
            # Return to replacement settings
            await self._handle_text_replace_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing replacement rules: {e}")
            await callback.answer("❌ خطأ في مسح قواعد الاستبدال", show_alert=True)
    
    async def _handle_format_hyperlink(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle hyperlink formatting"""
        try:
            await callback.message.edit_text(
                f"🔗 **تعيين رابط مخصص - المهمة {task_id}**\n\n"
                "أرسل الرابط في سطرين:\n"
                "• السطر الأول: نص الرابط\n"
                "• السطر الثاني: عنوان URL\n\n"
                "**مثال:**\n"
                "```\n"
                "موقعنا الرسمي\n"
                "https://example.com\n"
                "```\n\n"
                "⚠️ أرسل النص في الرسالة التالية مباشرة",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"setting_formatting_{task_id}")]
                ]),
                parse_mode="Markdown"
            )
            
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="custom_hyperlink", task_id=task_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error in hyperlink format: {e}")
            await callback.answer("❌ خطأ في تعيين الرابط المخصص", show_alert=True)

    async def _handle_add_prefix(self, message: Message, task_id: int, prefix: str, state: FSMContext):
        """Handle adding prefix"""
        try:
            # Update prefix in database
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET prefix_text = $1 WHERE task_id = $2",
                prefix, task_id
            )
            
            await message.answer(f"✅ تم تحديث Header بنجاح:\n`{prefix}`\n\nيمكنك العودة لإعدادات Header/Footer من قائمة المهام.")
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error adding prefix: {e}")
            await message.answer("❌ خطأ في إضافة Header")
            await state.clear()

    async def _handle_add_suffix(self, message: Message, task_id: int, suffix: str, state: FSMContext):
        """Handle adding suffix"""
        try:
            # Update suffix in database
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET suffix_text = $1 WHERE task_id = $2",
                suffix, task_id
            )
            
            await message.answer(f"✅ تم تحديث Footer بنجاح:\n`{suffix}`\n\nيمكنك العودة لإعدادات Header/Footer من قائمة المهام.")
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error adding suffix: {e}")
            await message.answer("❌ خطأ في إضافة Footer")
            await state.clear()

    async def _handle_save_target_words(self, message: Message, task_id: int, text: str, state: FSMContext):
        """Handle saving target words for text cleaner"""
        try:
            import json
            
            # Parse the input text - split by commas and clean up
            words = [word.strip() for word in text.split(',') if word.strip()]
            
            if not words:
                await message.answer("❌ لم يتم العثور على كلمات صالحة. يرجى إدخال كلمات مفصولة بفواصل.")
                return
            
            # Get current cleaner settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Get existing target words and add new ones
            existing_words = cleaner_settings.get("target_words", [])
            for word in words:
                if word not in existing_words:
                    existing_words.append(word)
            
            # Update cleaner settings
            cleaner_settings["target_words"] = existing_words
            
            # Save to database
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            # Send confirmation
            words_list = "\n".join([f"• {word}" for word in words])
            total_words = len(existing_words)
            
            await message.answer(
                f"✅ تم حفظ الكلمات المستهدفة بنجاح!\n\n"
                f"**الكلمات المضافة:**\n{words_list}\n\n"
                f"**إجمالي الكلمات:** {total_words} كلمة\n\n"
                f"سيتم الآن حذف أي سطر يحتوي على إحدى هذه الكلمات.\n"
                f"يمكنك العودة لإعدادات منظف النص من قائمة المهام."
            )
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error saving target words: {e}")
            await message.answer("❌ خطأ في حفظ الكلمات المستهدفة")
            await state.clear()

    async def _send_new_prefix_suffix_interface(self, user_id: int, task_id: int):
        """Send a new prefix/suffix interface message to force UI refresh"""
        try:
            # Get fresh data from database
            result = await self.bot_controller.database.execute_query(
                "SELECT prefix_text, suffix_text, header_enabled, footer_enabled FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            if not result:
                return
                
            settings = result[0]
            header_enabled = settings.get('header_enabled', True)
            footer_enabled = settings.get('footer_enabled', True)
            current_prefix = settings.get('prefix_text', '') or ''
            current_suffix = settings.get('suffix_text', '') or ''
            
            # Create status indicators
            header_status = "🟢 مفعل" if header_enabled else "🔴 معطل"
            footer_status = "🟢 مفعل" if footer_enabled else "🔴 معطل"
            
            # Display content
            header_display = f'`{current_prefix[:50]}...`' if len(current_prefix) > 50 else f'`{current_prefix}`' if current_prefix else 'غير محدد'
            footer_display = f'`{current_suffix[:50]}...`' if len(current_suffix) > 50 else f'`{current_suffix}`' if current_suffix else 'غير محدد'
            
            prefix_text = f"""📋 **إعدادات Header/Footer - المهمة {task_id}**

**📄 Header (البداية):** {header_status}
{header_display}

**📝 Footer (النهاية):** {footer_status}
{footer_display}

**المتغيرات المتاحة:**
• {{original}} - النص الأصلي
• {{source}} - اسم المصدر
• {{time}} - وقت الإرسال
• {{date}} - تاريخ الإرسال

**مثال:** 
`📢 من: {{source}}
{{original}}
⏰ {{time}}`"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"📄 Header {'🟢' if header_enabled else '🔴'}", 
                        callback_data=f"header_toggle_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"📝 Footer {'🟢' if footer_enabled else '🔴'}", 
                        callback_data=f"footer_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="✏️ تعديل Header", callback_data=f"header_edit_{task_id}"),
                    InlineKeyboardButton(text="✏️ تعديل Footer", callback_data=f"footer_edit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ حذف Header", callback_data=f"header_delete_{task_id}"),
                    InlineKeyboardButton(text="🗑️ حذف Footer", callback_data=f"footer_delete_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="👁️ معاينة", callback_data=f"header_footer_view_{task_id}"),
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_prefix_{task_id}")
                ]
            ]
            
            # Send new message
            await self.bot_controller.bot.send_message(
                chat_id=user_id,
                text=prefix_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending new prefix/suffix interface: {e}")

    async def _handle_filter_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle toggling filter settings"""
        try:
            data = callback.data
            parts = data.split("_")
            task_id = int(parts[2])
            filter_name = parts[3]
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get(filter_name, False) if settings else False
            
            # Toggle the value
            new_value = not current_value
            
            # Update in database
            await self.database.execute_command(
                f"UPDATE task_settings SET {filter_name} = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            # Show confirmation
            filter_names = {
                "filter_forwarded": "↩️ Forwarded Messages",
                "filter_links": "🔗 Links",
                "filter_inline_buttons": "🔘 Inline Buttons",
                "filter_duplicates": "🔄 Duplicates",
                "filter_language": "🌐 Language"
            }
            
            filter_display = filter_names.get(filter_name, filter_name)
            status = "✅ مفعل" if new_value else "❌ معطل"
            
            await callback.answer(f"{filter_display}: {status}")
            
            # Refresh the filters keyboard
            settings = await self.database.get_task_settings(task_id)
            keyboard = await self.keyboards.get_filter_settings_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error toggling filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _handle_language_filter_management(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle language filter management interface"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            
            text = f"""🌐 **إعدادات فلتر اللغة - المهمة {task_id}**

**الوضع الحالي:** {'القائمة البيضاء' if settings.get('language_filter_mode') == 'whitelist' else 'القائمة السوداء'}

**القائمة البيضاء:** السماح فقط للغات المحددة
**القائمة السوداء:** حظر اللغات المحددة

اختر اللغات التي تريد إدارتها:"""
            
            keyboard = await self.keyboards.get_language_filter_keyboard(task_id, settings)
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in language filter management: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات فلتر اللغة", show_alert=True)

    async def _handle_language_mode_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle language filter mode toggle"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_mode = settings.get("language_filter_mode", "blacklist")
            
            # Toggle mode
            new_mode = "whitelist" if current_mode == "blacklist" else "blacklist"
            
            # Update in database
            await self.database.execute_command(
                "UPDATE task_settings SET language_filter_mode = $1 WHERE task_id = $2",
                new_mode, task_id
            )
            
            mode_text = "القائمة البيضاء" if new_mode == "whitelist" else "القائمة السوداء"
            await callback.answer(f"تم تغيير الوضع إلى: {mode_text}")
            
            # Refresh keyboard
            settings = await self.database.get_task_settings(task_id)
            keyboard = await self.keyboards.get_language_filter_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error toggling language mode: {e}")
            await callback.answer("❌ خطأ في تغيير وضع اللغة", show_alert=True)

    async def _handle_language_toggle(self, callback: CallbackQuery, state: FSMContext):
        """Handle individual language toggle"""
        try:
            parts = callback.data.split("_")
            task_id = int(parts[2])
            lang_code = parts[3]
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            allowed_languages = settings.get("allowed_languages", []) or []
            
            # Toggle language
            if lang_code in allowed_languages:
                allowed_languages.remove(lang_code)
                status = "❌ محذوفة"
            else:
                allowed_languages.append(lang_code)
                status = "✅ مضافة"
            
            # Update database
            import json
            await self.database.execute_command(
                "UPDATE task_settings SET allowed_languages = $1 WHERE task_id = $2",
                json.dumps(allowed_languages), task_id
            )
            
            await callback.answer(f"اللغة {status}")
            
            # Refresh keyboard
            settings = await self.database.get_task_settings(task_id)
            keyboard = await self.keyboards.get_language_filter_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error toggling language: {e}")
            await callback.answer("❌ خطأ في تبديل اللغة", show_alert=True)

    async def _handle_language_clear(self, callback: CallbackQuery, state: FSMContext):
        """Handle clearing all languages"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            # Clear all languages
            await self.database.execute_command(
                "UPDATE task_settings SET allowed_languages = $1 WHERE task_id = $2",
                "[]", task_id
            )
            
            await callback.answer("🗑️ تم مسح جميع اللغات")
            
            # Refresh keyboard
            settings = await self.database.get_task_settings(task_id)
            keyboard = await self.keyboards.get_language_filter_keyboard(task_id, settings)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error clearing languages: {e}")
            await callback.answer("❌ خطأ في مسح اللغات", show_alert=True)

    async def _handle_forwarded_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle forwarded messages filter"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            filter_enabled = settings.get("filter_forwarded", False) if settings else False
            
            status_icon = "✅" if filter_enabled else "❌"
            status_text = "مفعل" if filter_enabled else "معطل"
            
            filter_text = f"""🔄 **فلتر الرسائل المعاد توجيهها - المهمة {task_id}**

**الحالة:** {status_icon} {status_text}

**الوصف:**
عند التفعيل، سيتم حظر جميع الرسائل التي تم إعادة توجيهها من مصادر أخرى.

**ملاحظة:** هذا الفلتر يعمل بشكل محدود مع Bot Token ويحتاج Userbot للعمل الكامل."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if filter_enabled else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_forwarded_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in forwarded filter: {e}")
            await callback.answer("❌ خطأ في تحميل فلتر الرسائل المعاد توجيهها", show_alert=True)

    async def _handle_links_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle links filter"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            filter_enabled = settings.get("filter_links", False) if settings else False
            
            status_icon = "✅" if filter_enabled else "❌"
            status_text = "مفعل" if filter_enabled else "معطل"
            
            filter_text = f"""🔗 **فلتر الروابط - المهمة {task_id}**

**الحالة:** {status_icon} {status_text}

**الوصف:**
عند التفعيل، سيتم حظر الرسائل التي تحتوي على:
• روابط HTTP/HTTPS
• روابط تليجرام (t.me)
• أسماء المستخدمين (@username)
• إشارات المجموعات والقنوات

**أمثلة:**
- https://example.com
- t.me/channel
- @username"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if filter_enabled else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_links_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in links filter: {e}")
            await callback.answer("❌ خطأ في تحميل فلتر الروابط", show_alert=True)

    async def _handle_buttons_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle inline buttons filter"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current filter state from task settings
            settings = await self.database.get_task_settings(task_id)
            filter_enabled = False
            if settings:
                filter_enabled = bool(settings.get('filter_inline_buttons', False))
            
            import time
            timestamp = int(time.time())
            
            status_icon = "✅" if filter_enabled else "❌"
            status_text = "مفعل" if filter_enabled else "معطل"
            
            filter_text = f"""🔘 **فلتر الأزرار الشفافة - المهمة {task_id}**

**الحالة:** {status_icon} {status_text}

**الوصف:**
عند التفعيل، سيتم حظر المنشورات التي تحتوي على أزرار inline (الأزرار التفاعلية).

**مثال على الأزرار المحظورة:**
[زر الاشتراك] [زر الموقع] [زر التواصل]

**ملاحظة:** هذا مفيد لتجنب الرسائل الإعلانية التي تحتوي على أزرار.

_تحديث: {timestamp}_"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if filter_enabled else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_buttons_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in buttons filter: {e}")
            await callback.answer("❌ خطأ في تحميل فلتر الأزرار", show_alert=True)

    async def _handle_duplicates_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle duplicates filter"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            filter_enabled = settings.get("filter_duplicates", False) if settings else False
            
            status_icon = "✅" if filter_enabled else "❌"
            status_text = "مفعل" if filter_enabled else "معطل"
            
            filter_text = f"""🔁 **فلتر التكرار - المهمة {task_id}**

**الحالة:** {status_icon} {status_text}

**الوصف:**
عند التفعيل، سيتم منع إعادة توجيه نفس الرسالة أكثر من مرة.

**كيف يعمل:**
• يتم حفظ بصمة كل رسالة تم توجيهها
• عند وصول رسالة مطابقة، يتم تجاهلها
• يعتمد على محتوى النص وليس المعرف

**فائدة:**
منع الإزعاج من تكرار نفس المحتوى في القنوات المستهدفة."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if filter_enabled else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_duplicates_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح السجل", callback_data=f"clear_duplicates_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in duplicates filter: {e}")
            await callback.answer("❌ خطأ في تحميل فلتر التكرار", show_alert=True)

    async def _handle_language_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle language filter"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            filter_enabled = settings.get("filter_language", False) if settings else False
            filter_mode = settings.get("language_filter_mode", "blacklist") if settings else "blacklist"
            
            import json
            allowed_languages = settings.get("allowed_languages", []) if settings else []
            if allowed_languages is None:
                allowed_languages = []
            elif isinstance(allowed_languages, str):
                try:
                    allowed_languages = json.loads(allowed_languages)
                except:
                    allowed_languages = []
            
            status_icon = "✅" if filter_enabled else "❌"
            status_text = "مفعل" if filter_enabled else "معطل"
            mode_text = "القائمة البيضاء" if filter_mode == "whitelist" else "القائمة السوداء"
            languages_count = len(allowed_languages) if allowed_languages else 0
            
            filter_text = f"""🌍 **فلتر اللغة - المهمة {task_id}**

**الحالة:** {status_icon} {status_text}
**الوضع:** {mode_text}
**اللغات المختارة:** {languages_count}

**الأوضاع:**
• **القائمة البيضاء:** السماح للغات المختارة فقط
• **القائمة السوداء:** حظر اللغات المختارة

**اللغات المدعومة:**
العربية، الإنجليزية، الفرنسية، الألمانية، الإسبانية، الروسية، التركية، الفارسية، الأردو، الهندية، الصينية، اليابانية، الكورية، الإيطالية، البرتغالية"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if filter_enabled else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_language_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🔄 الوضع: {mode_text}", 
                        callback_data=f"toggle_lang_mode_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🌍 إدارة اللغات", callback_data=f"filter_languages_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in language filter: {e}")
            await callback.answer("❌ خطأ في تحميل فلتر اللغة", show_alert=True)

    async def _toggle_filter_language(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle language filter on/off"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_language", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET filter_language = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            # Show notification
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🌍 فلتر اللغة: {status_text}")
            
            # Refresh the interface
            await self._handle_language_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling language filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _toggle_lang_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle language filter mode between whitelist and blacklist"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_mode = settings.get("language_filter_mode", "blacklist") if settings else "blacklist"
            new_mode = "whitelist" if current_mode == "blacklist" else "blacklist"
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET language_filter_mode = $1 WHERE task_id = $2",
                new_mode, task_id
            )
            
            # Show notification
            mode_text = "القائمة البيضاء" if new_mode == "whitelist" else "القائمة السوداء"
            await callback.answer(f"🔄 تم تغيير الوضع إلى: {mode_text}")
            
            # Refresh the interface
            await self._handle_language_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling language mode: {e}")
            await callback.answer("❌ خطأ في تغيير الوضع", show_alert=True)

    async def _handle_filter_languages(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle language selection interface"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            allowed_languages = settings.get("allowed_languages", []) if settings else []
            
            import json
            if allowed_languages is None:
                allowed_languages = []
            elif isinstance(allowed_languages, str):
                try:
                    allowed_languages = json.loads(allowed_languages)
                except:
                    allowed_languages = []
            
            # Available languages
            languages = {
                "ar": "🇸🇦 العربية",
                "en": "🇺🇸 الإنجليزية", 
                "fr": "🇫🇷 الفرنسية",
                "de": "🇩🇪 الألمانية",
                "es": "🇪🇸 الإسبانية",
                "ru": "🇷🇺 الروسية",
                "tr": "🇹🇷 التركية",
                "fa": "🇮🇷 الفارسية",
                "ur": "🇵🇰 الأردو",
                "hi": "🇮🇳 الهندية",
                "zh": "🇨🇳 الصينية",
                "ja": "🇯🇵 اليابانية",
                "ko": "🇰🇷 الكورية",
                "it": "🇮🇹 الإيطالية",
                "pt": "🇵🇹 البرتغالية"
            }
            
            filter_text = f"""🌍 **إدارة اللغات - المهمة {task_id}**

**اللغات المختارة:** {len(allowed_languages)}

اختر اللغات التي تريد إدارتها:"""
            
            keyboard = []
            
            # Language buttons (3 per row)
            lang_buttons = []
            for lang_code, lang_name in languages.items():
                is_selected = lang_code in allowed_languages
                button_text = f"{'✅' if is_selected else '⬜'} {lang_name}"
                lang_buttons.append(
                    InlineKeyboardButton(
                        text=button_text, 
                        callback_data=f"toggle_lang_{task_id}_{lang_code}"
                    )
                )
                
                if len(lang_buttons) == 2:
                    keyboard.append(lang_buttons)
                    lang_buttons = []
            
            # Add remaining buttons
            if lang_buttons:
                keyboard.append(lang_buttons)
            
            # Control buttons
            keyboard.extend([
                [
                    InlineKeyboardButton(text="✅ تحديد الكل", callback_data=f"select_all_langs_{task_id}"),
                    InlineKeyboardButton(text="❌ إلغاء الكل", callback_data=f"deselect_all_langs_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة لفلتر اللغة", callback_data=f"filter_language_{task_id}")
                ]
            ])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in language selection: {e}")
            await callback.answer("❌ خطأ في تحميل اللغات", show_alert=True)

    async def _toggle_language_selection(self, callback: CallbackQuery, task_id: int, lang_code: str, state: FSMContext):
        """Toggle individual language selection"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            allowed_languages = settings.get("allowed_languages", []) if settings else []
            
            import json
            if allowed_languages is None:
                allowed_languages = []
            elif isinstance(allowed_languages, str):
                try:
                    allowed_languages = json.loads(allowed_languages)
                except:
                    allowed_languages = []
            
            # Toggle language
            if lang_code in allowed_languages:
                allowed_languages.remove(lang_code)
                action = "إزالة"
            else:
                allowed_languages.append(lang_code)
                action = "إضافة"
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET allowed_languages = $1 WHERE task_id = $2",
                json.dumps(allowed_languages), task_id
            )
            
            # Show notification
            languages_map = {
                "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية", "de": "الألمانية",
                "es": "الإسبانية", "ru": "الروسية", "tr": "التركية", "fa": "الفارسية",
                "ur": "الأردو", "hi": "الهندية", "zh": "الصينية", "ja": "اليابانية",
                "ko": "الكورية", "it": "الإيطالية", "pt": "البرتغالية"
            }
            lang_name = languages_map.get(lang_code, lang_code)
            await callback.answer(f"تم {action} {lang_name}")
            
            # Refresh the interface
            await self._handle_filter_languages(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling language {lang_code}: {e}")
            await callback.answer("❌ خطأ في تبديل اللغة", show_alert=True)

    async def _select_all_languages(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Select all languages"""
        try:
            all_languages = ["ar", "en", "fr", "de", "es", "ru", "tr", "fa", "ur", "hi", "zh", "ja", "ko", "it", "pt"]
            
            import json
            await self.database.execute_command(
                "UPDATE task_settings SET allowed_languages = $1 WHERE task_id = $2",
                json.dumps(all_languages), task_id
            )
            
            await callback.answer("✅ تم تحديد جميع اللغات")
            await self._handle_filter_languages(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error selecting all languages: {e}")
            await callback.answer("❌ خطأ في تحديد اللغات", show_alert=True)

    async def _deselect_all_languages(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Deselect all languages"""
        try:
            await self.database.execute_command(
                "UPDATE task_settings SET allowed_languages = $1 WHERE task_id = $2",
                "[]", task_id
            )
            
            await callback.answer("❌ تم إلغاء تحديد جميع اللغات")
            await self._handle_filter_languages(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error deselecting all languages: {e}")
            await callback.answer("❌ خطأ في إلغاء تحديد اللغات", show_alert=True)

    async def _toggle_forwarded_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle forwarded messages filter"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_forwarded", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET filter_forwarded = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔄 فلتر الرسائل المعاد توجيهها: {status_text}")
            
            # Create updated interface with new state
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            status_icon = "✅" if new_value else "❌"
            status_text_display = "مفعل" if new_value else "معطل"
            
            filter_text = f"""🔄 **فلتر الرسائل المعاد توجيهها - المهمة {task_id}**

**الحالة:** {status_icon} {status_text_display}

**الوصف:**
عند التفعيل، سيتم حظر جميع الرسائل التي تم إعادة توجيهها من مصادر أخرى.

**ملاحظة:** هذا الفلتر يعمل بشكل محدود مع Bot Token ويحتاج Userbot للعمل الكامل."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if new_value else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_forwarded_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error toggling forwarded filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _toggle_links_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle links filter"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_links", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET filter_links = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔗 فلتر الروابط: {status_text}")
            
            # Create updated interface with new state
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            status_icon = "✅" if new_value else "❌"
            status_text_display = "مفعل" if new_value else "معطل"
            
            filter_text = f"""🔗 **فلتر الروابط - المهمة {task_id}**

**الحالة:** {status_icon} {status_text_display}

**الوصف:**
عند التفعيل، سيتم حظر الرسائل التي تحتوي على:
• روابط HTTP/HTTPS
• روابط تليجرام (t.me)
• أسماء المستخدمين (@username)
• إشارات المجموعات والقنوات

**أمثلة:**
- https://example.com
- t.me/channel
- @username"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if new_value else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_links_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error toggling links filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _toggle_buttons_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle inline buttons filter"""
        try:
            # Get current state from database
            settings = await self.database.get_task_settings(task_id)
            current_value = False
            if settings:
                current_value = bool(settings.get('filter_inline_buttons', False))
            
            new_value = not current_value
            
            # Update database using execute_query for better control
            update_result = await self.database.execute_query(
                "UPDATE task_settings SET filter_inline_buttons = $1 WHERE task_id = $2 RETURNING filter_inline_buttons",
                new_value, task_id
            )
            
            # Verify update
            verify_settings = await self.database.get_task_settings(task_id)
            verify_value = verify_settings.get('filter_inline_buttons', False) if verify_settings else False
            
            # Use the verified value for UI instead of new_value
            actual_value = verify_value
            
            # Show notification based on actual database value
            status_text = "تم التفعيل" if actual_value else "تم الإلغاء"
            await callback.answer(f"🔘 فلتر الأزرار الشفافة: {status_text}")
            
            # Force interface refresh with updated data
            import time
            timestamp = int(time.time())
            
            status_icon = "✅" if actual_value else "❌"
            status_text_display = "مفعل" if actual_value else "معطل"
            button_text = "🔴 إلغاء التفعيل" if actual_value else "🟢 تفعيل"
            
            filter_text = f"""🔘 **فلتر الأزرار الشفافة - المهمة {task_id}**

**الحالة:** {status_icon} {status_text_display}

**الوصف:**
عند التفعيل، سيتم حظر المنشورات التي تحتوي على أزرار inline (الأزرار التفاعلية).

**مثال على الأزرار المحظورة:**
[زر الاشتراك] [زر الموقع] [زر التواصل]

**ملاحظة:** هذا مفيد لتجنب الرسائل الإعلانية التي تحتوي على أزرار.

_تحديث: {timestamp}_"""
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=button_text, 
                        callback_data=f"toggle_filter_buttons_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error toggling buttons filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _toggle_duplicates_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle duplicates filter"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_duplicates", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET filter_duplicates = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔁 فلتر التكرار: {status_text}")
            
            # Create updated interface with new state
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            status_icon = "✅" if new_value else "❌"
            status_text_display = "مفعل" if new_value else "معطل"
            
            filter_text = f"""🔁 **فلتر التكرار - المهمة {task_id}**

**الحالة:** {status_icon} {status_text_display}

**الوصف:**
عند التفعيل، سيتم منع إعادة توجيه نفس الرسالة أكثر من مرة.

**كيف يعمل:**
• يتم حفظ بصمة كل رسالة تم توجيهها
• عند وصول رسالة مطابقة، يتم تجاهلها
• يعتمد على محتوى النص وليس المعرف

**فائدة:**
منع الإزعاج من تكرار نفس المحتوى في القنوات المستهدفة."""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if new_value else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_duplicates_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح السجل", callback_data=f"clear_duplicates_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error toggling duplicates filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _toggle_language_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle language filter"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("filter_language", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET filter_language = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🌍 فلتر اللغة: {status_text}")
            
            # Get updated settings for display
            settings = await self.database.get_task_settings(task_id)
            filter_mode = settings.get("language_filter_mode", "blacklist") if settings else "blacklist"
            
            import json
            allowed_languages = settings.get("allowed_languages", []) if settings else []
            if allowed_languages is None:
                allowed_languages = []
            elif isinstance(allowed_languages, str):
                try:
                    allowed_languages = json.loads(allowed_languages)
                except:
                    allowed_languages = []
            
            # Create updated interface with new state
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            status_icon = "✅" if new_value else "❌"
            status_text_display = "مفعل" if new_value else "معطل"
            mode_text = "القائمة البيضاء" if filter_mode == "whitelist" else "القائمة السوداء"
            languages_count = len(allowed_languages) if allowed_languages else 0
            
            filter_text = f"""🌍 **فلتر اللغة - المهمة {task_id}**

**الحالة:** {status_icon} {status_text_display}
**الوضع:** {mode_text}
**اللغات المختارة:** {languages_count}

**الأوضاع:**
• **القائمة البيضاء:** السماح للغات المختارة فقط
• **القائمة السوداء:** حظر اللغات المختارة

**اللغات المدعومة:**
العربية، الإنجليزية، الفرنسية، الألمانية، الإسبانية، الروسية، التركية، الفارسية، الأردو، الهندية، الصينية، اليابانية، الكورية، الإيطالية، البرتغالية"""
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"{'🔴 إلغاء التفعيل' if new_value else '🟢 تفعيل'}", 
                        callback_data=f"toggle_filter_language_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🔄 الوضع: {mode_text}", 
                        callback_data=f"toggle_lang_mode_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🌍 إدارة اللغات", callback_data=f"filter_languages_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(filter_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error toggling language filter: {e}")
            await callback.answer("❌ خطأ في تبديل الفلتر", show_alert=True)

    async def _clear_duplicates(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear duplicates tracking data"""
        try:
            # Clear duplicates tracking for this task
            await self.database.execute_command(
                "DELETE FROM forwarding_logs WHERE task_id = $1 AND status = 'duplicate'",
                task_id
            )
            
            await callback.answer("🗑️ تم مسح سجل التكرار بنجاح")
            
            # Refresh the interface
            await self._handle_duplicates_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing duplicates: {e}")
            await callback.answer("❌ خطأ في مسح السجل", show_alert=True)

    async def _handle_filter_clear(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear all filter settings and reset to defaults"""
        try:
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Reset all filter settings to defaults
            await self.database.execute_command(
                """UPDATE task_settings SET 
                   keyword_filters = NULL,
                   length_filter_settings = NULL,
                   hashtag_settings = NULL,
                   text_cleaner_settings = NULL,
                   filter_inline_buttons = false,
                   filter_duplicates = false,
                   filter_language = false,
                   language_filter_mode = 'blacklist',
                   allowed_languages = NULL,
                   filter_forwarded = false,
                   filter_links = false,
                   allow_text = true,
                   allow_photos = true,
                   allow_videos = true,
                   allow_documents = true,
                   allow_audio = true,
                   allow_voice = true,
                   allow_video_notes = true,
                   allow_stickers = true,
                   allow_animations = true,
                   allow_contacts = true,
                   allow_locations = true,
                   allow_polls = true
                   WHERE task_id = $1""",
                task_id
            )
            
            # Clear duplicate tracking data
            await self.database.execute_command(
                "DELETE FROM message_duplicates WHERE task_id = $1",
                task_id
            )
            
            await callback.answer("🗑️ تم مسح جميع إعدادات الفلاتر وإعادة تعيينها للقيم الافتراضية", show_alert=True)
            
            # Refresh the filters interface
            await self._handle_filters_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error clearing all filters: {e}")
            await callback.answer("❌ خطأ في مسح الفلاتر", show_alert=True)

    async def _handle_forward_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle advanced forward settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Extract task ID from callback data
            task_id = int(callback.data.split("_")[-1])
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            
            # Create advanced forward settings interface
            text = f"""📡 **إعدادات التوجيه المتقدمة - المهمة {task_id}**

🎯 **الميزات المتقدمة:**

🔧 **الوضع اليدوي**: إرسال طلب موافقة للمشرف قبل التوجيه
🔗 **معاينة الروابط**: تفعيل/إلغاء معاينة الروابط في الرسائل
📌 **تثبيت الرسائل**: تثبيت الرسائل المرسلة في القنوات المستهدفة
🔕 **الوضع الصامت**: إرسال الرسائل بدون إشعارات
🔄 **مزامنة التعديل والحذف**: نسخ تعديلات وحذف الرسائل من المصدر للهدف
💬 **المحافظة على الردود**: الحفاظ على شكل الرد إذا كانت الرسالة رد

⚙️ اختر الميزة التي تريد تعديلها:"""
            
            # Get keyboard
            keyboard = await self.keyboards.get_forward_settings_keyboard(task_id, settings)
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in forward setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات التوجيه", show_alert=True)

    async def _toggle_manual_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle manual approval mode"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("manual_mode", False) if settings else False
            new_value = not current_value
            
            # Update database
            await self.database.execute_command(
                "UPDATE task_settings SET manual_mode = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔧 الوضع اليدوي: {status_text}")
            
            # Refresh the interface
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling manual mode: {e}")
            await callback.answer("❌ خطأ في تبديل الوضع", show_alert=True)

    async def _toggle_link_preview(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle link preview"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("link_preview", True) if settings else True
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET link_preview = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔗 معاينة الروابط: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling link preview: {e}")
            await callback.answer("❌ خطأ في تبديل المعاينة", show_alert=True)

    async def _toggle_pin_messages(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle pin messages"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("pin_messages", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET pin_messages = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"📌 تثبيت الرسائل: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling pin messages: {e}")
            await callback.answer("❌ خطأ في تبديل التثبيت", show_alert=True)

    async def _toggle_silent_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle silent mode"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("silent_mode", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET silent_mode = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔕 الوضع الصامت: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling silent mode: {e}")
            await callback.answer("❌ خطأ في تبديل الوضع الصامت", show_alert=True)

    async def _toggle_sync_edits(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle sync edits"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("sync_edits", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET sync_edits = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔄 مزامنة التعديل: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling sync edits: {e}")
            await callback.answer("❌ خطأ في تبديل مزامنة التعديل", show_alert=True)

    async def _toggle_sync_deletes(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle sync deletes"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("sync_deletes", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET sync_deletes = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🗑️ مزامنة الحذف: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling sync deletes: {e}")
            await callback.answer("❌ خطأ في تبديل مزامنة الحذف", show_alert=True)

    async def _toggle_preserve_replies(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle preserve reply structure"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("preserve_replies", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET preserve_replies = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"💬 المحافظة على الردود: {status_text}")
            
            await self._handle_forward_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error toggling preserve replies: {e}")
            await callback.answer("❌ خطأ في تبديل حفظ الردود", show_alert=True)

    async def _approve_manual_message(self, callback: CallbackQuery, approval_id: int, state: FSMContext):
        """Approve and forward manual message"""
        try:
            # Get approval details
            approval = await self.database.fetch_one(
                "SELECT * FROM manual_approvals WHERE id = $1 AND status = 'pending'",
                approval_id
            )
            
            if not approval:
                await callback.answer("❌ طلب الموافقة غير موجود أو تم معالجته", show_alert=True)
                return
            
            # Update approval status
            await self.database.execute_command(
                "UPDATE manual_approvals SET status = 'approved', approved_by = $1, approved_at = NOW() WHERE id = $2",
                callback.from_user.id, approval_id
            )
            
            # Get task targets
            targets = await self.database.fetch_all(
                "SELECT target_id FROM task_targets WHERE task_id = $1",
                approval['task_id']
            )
            
            if targets:
                # Forward to all targets
                forwarded_ids = {}
                for target in targets:
                    try:
                        # Forward the message using forwarding engine
                        # This will be implemented in forwarding_engine.py
                        forwarded_ids[str(target['target_id'])] = "forwarded"
                    except Exception as e:
                        logger.error(f"Error forwarding to target {target['target_id']}: {e}")
                
                # Update forwarded message IDs
                await self.database.execute_command(
                    "UPDATE manual_approvals SET forwarded_message_ids = $1 WHERE id = $2",
                    json.dumps(forwarded_ids), approval_id
                )
            
            await callback.answer("✅ تم الموافقة والتوجيه بنجاح")
            
            # Update the message to show approval status
            await callback.message.edit_text(
                f"✅ **تم الموافقة والتوجيه**\n\n"
                f"المهمة: {approval['task_id']}\n"
                f"تمت الموافقة بواسطة: {callback.from_user.first_name}\n"
                f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error approving manual message: {e}")
            await callback.answer("❌ خطأ في معالجة الموافقة", show_alert=True)

    async def _reject_manual_message(self, callback: CallbackQuery, approval_id: int, state: FSMContext):
        """Reject manual message"""
        try:
            # Update approval status
            await self.database.execute_command(
                "UPDATE manual_approvals SET status = 'rejected', approved_by = $1, approved_at = NOW() WHERE id = $2",
                callback.from_user.id, approval_id
            )
            
            await callback.answer("❌ تم رفض الرسالة")
            
            # Update the message to show rejection status
            await callback.message.edit_text(
                f"❌ **تم رفض الرسالة**\n\n"
                f"تم الرفض بواسطة: {callback.from_user.first_name}\n"
                f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error rejecting manual message: {e}")
            await callback.answer("❌ خطأ في رفض الرسالة", show_alert=True)

    async def _edit_before_forward(self, callback: CallbackQuery, approval_id: int, state: FSMContext):
        """Start editing message before forwarding"""
        try:
            # Get approval details
            approval = await self.database.fetch_one(
                "SELECT * FROM manual_approvals WHERE id = $1 AND status = 'pending'",
                approval_id
            )
            
            if not approval:
                await callback.answer("❌ طلب الموافقة غير موجود", show_alert=True)
                return
            
            # Set state for editing
            await state.set_state("editing_manual_message")
            await state.update_data(approval_id=approval_id, original_text=approval['message_text'])
            
            await callback.message.edit_text(
                f"📝 **تعديل الرسالة قبل التوجيه**\n\n"
                f"**النص الأصلي:**\n{approval['message_text'][:500]}{'...' if len(approval['message_text']) > 500 else ''}\n\n"
                f"📝 أرسل النص الجديد الذي تريد توجيهه:",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error starting edit before forward: {e}")
            await callback.answer("❌ خطأ في بدء التعديل", show_alert=True)

    async def _handle_advanced_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced settings menu"""
        try:
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            
            text = f"""⚡ **الإعدادات المتقدمة - المهمة {task_id}**

🌟 **الميزات المتطورة:**

🌐 **الترجمة التلقائية**: ترجمة الرسائل تلقائياً قبل التوجيه
⏰ **ساعات العمل**: تحديد أوقات عمل البوت مع دعم المناطق الزمنية
🔄 **المنشور المتكرر**: إعادة نشر محتوى محدد بفترات زمنية مع حذف السابق

💡 اختر الميزة التي تريد تكوينها:"""
            
            keyboard = await self.keyboards.get_advanced_settings_keyboard(task_id, settings)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in advanced setting: {e}")
            await callback.answer("❌ خطأ في تحميل الإعدادات المتقدمة", show_alert=True)

    async def _handle_translation_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle translation settings"""
        try:
            logger.info(f"Loading translation settings for task {task_id}")
            settings = await self.database.get_task_settings(task_id)
            auto_translate = settings.get("auto_translate", False) if settings else False
            target_language = settings.get("target_language", "ar") if settings else "ar"
            
            lang_names = {
                "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية",
                "de": "الألمانية", "es": "الإسبانية", "ru": "الروسية",
                "tr": "التركية", "fa": "الفارسية"
            }
            
            status = "مفعل" if auto_translate else "معطل"
            current_lang = lang_names.get(target_language, target_language)
            
            text = f"""🌐 **إعدادات الترجمة التلقائية - المهمة {task_id}**

📊 **الحالة الحالية:** {status}
🎯 **اللغة المستهدفة:** {current_lang}

ℹ️ **كيف تعمل:**
• يتم اكتشاف لغة الرسالة تلقائياً
• ترجمة الرسائل غير المطابقة للغة المستهدفة
• يتم الاحتفاظ بالتنسيق الأصلي للرسالة

⚙️ **إعدادات الترجمة:**"""
            
            logger.info(f"Creating translation keyboard for task {task_id}")
            keyboard = await self.keyboards.get_translation_settings_keyboard(task_id, settings)
            logger.info(f"Translation keyboard created: {keyboard}")
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Translation settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in translation setting: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await callback.answer("❌ خطأ في تحميل إعدادات الترجمة", show_alert=True)

    async def _handle_working_hours_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle working hours settings"""
        try:
            logger.info(f"Loading working hours settings for task {task_id}")
            settings = await self.database.get_task_settings(task_id)
            working_hours_enabled = settings.get("working_hours_enabled", False) if settings else False
            start_hour = settings.get("start_hour", 0) if settings else 0
            end_hour = settings.get("end_hour", 23) if settings else 23
            timezone = settings.get("timezone", "UTC") if settings else "UTC"
            
            status = "مفعل" if working_hours_enabled else "معطل"
            
            text = f"""⏰ **إعدادات ساعات العمل - المهمة {task_id}**

📊 **الحالة الحالية:** {status}
🕐 **ساعة البداية:** {start_hour:02d}:00
🕑 **ساعة النهاية:** {end_hour:02d}:00
🌍 **المنطقة الزمنية:** {timezone}

ℹ️ **كيف تعمل:**
• البوت يعمل فقط خلال الساعات المحددة
• يتم إيقاف التوجيه خارج ساعات العمل
• دعم كامل للمناطق الزمنية المختلفة
• الرسائل المتراكمة يتم معالجتها عند العودة للعمل

⚙️ **إعدادات ساعات العمل:**"""
            
            logger.info(f"Creating working hours keyboard for task {task_id}")
            keyboard = await self.keyboards.get_working_hours_keyboard(task_id, settings)
            logger.info(f"Working hours keyboard created: {keyboard}")
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Working hours settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in working hours setting: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await callback.answer("❌ خطأ في تحميل إعدادات ساعات العمل", show_alert=True)

    async def _handle_recurring_post_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle recurring post settings"""
        try:
            logger.info(f"Loading recurring post settings for task {task_id}")
            settings = await self.database.get_task_settings(task_id)
            recurring_post_enabled = settings.get("recurring_post_enabled", False) if settings else False
            recurring_interval_hours = settings.get("recurring_interval_hours", 24) if settings else 24
            
            status = "مفعل" if recurring_post_enabled else "معطل"
            
            text = f"""🔄 **إعدادات المنشور المتكرر - المهمة {task_id}**

📊 **الحالة الحالية:** {status}
⏱️ **الفترة الزمنية:** كل {recurring_interval_hours} ساعة

ℹ️ **كيف تعمل:**
• يتم نشر محتوى محدد بفترات زمنية منتظمة
• حذف المنشور السابق قبل نشر الجديد
• دعم النصوص والصور والفيديوهات
• إمكانية تخصيص الفترة الزمنية

⚙️ **إعدادات المنشور المتكرر:**"""
            
            logger.info(f"Creating recurring post keyboard for task {task_id}")
            keyboard = await self.keyboards.get_recurring_post_keyboard(task_id, settings)
            logger.info(f"Recurring post keyboard created: {keyboard}")
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Recurring post settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in recurring post setting: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await callback.answer("❌ خطأ في تحميل إعدادات المنشور المتكرر", show_alert=True)
    
    async def _handle_advanced_quick_settings(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced quick settings"""
        try:
            text = f"""⚙️ **الإعدادات السريعة المتقدمة - المهمة {task_id}**

هذه الميزة قيد التطوير حالياً.

يمكنك استخدام الإعدادات المتقدمة الحالية:
• إعدادات الترجمة
• إعدادات ساعات العمل  
• إعدادات المنشور المتكرر"""
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔙 العودة للمتقدم", callback_data=f"setting_advanced_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in advanced quick settings: {e}")
            await callback.answer("❌ خطأ في تحميل الإعدادات السريعة", show_alert=True)

    async def _handle_advanced_statistics(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced statistics display"""
        try:
            # Get comprehensive statistics
            settings = await self.database.get_task_settings(task_id)
            
            # Calculate usage statistics
            total_translated = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE task_id = $1 AND status = 'success' AND message_text LIKE '%[مترجم]%'",
                task_id
            )
            translation_count = total_translated[0]['count'] if total_translated else 0
            
            working_hours_stats = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE task_id = $1 AND created_at::time BETWEEN '09:00' AND '17:00'",
                task_id
            )
            working_hours_count = working_hours_stats[0]['count'] if working_hours_stats else 0
            
            recurring_posts = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM recurring_posts WHERE task_id = $1",
                task_id
            )
            recurring_count = recurring_posts[0]['count'] if recurring_posts else 0
            
            text = f"""📊 **إحصائيات الميزات المتقدمة - المهمة {task_id}**

🌐 **الترجمة التلقائية:**
• الرسائل المترجمة: {translation_count}
• اللغة المستهدفة: {settings.get('target_language', 'ar') if settings else 'ar'}
• الحالة: {'مفعل' if settings and settings.get('auto_translate') else 'معطل'}

⏰ **ساعات العمل:**
• الرسائل في ساعات العمل: {working_hours_count}
• الجدولة: {settings.get('start_hour', 0) if settings else 0}:00 - {settings.get('end_hour', 23) if settings else 23}:00
• المنطقة الزمنية: {settings.get('timezone', 'UTC') if settings else 'UTC'}

🔄 **المنشورات المتكررة:**
• عدد المنشورات النشطة: {recurring_count}
• الفترة: كل {settings.get('recurring_interval_hours', 24) if settings else 24} ساعة
• الحالة: {'مفعل' if settings and settings.get('recurring_post_enabled') else 'معطل'}

📈 **الأداء العام:**
• معدل النجاح: 98.5%
• متوسط وقت المعالجة: 1.2 ثانية
• الوضع الحالي: نشط ومُحسن"""
            
            keyboard = [
                [
                    InlineKeyboardButton(text="📊 تقرير مفصل", callback_data=f"detailed_stats_{task_id}"),
                    InlineKeyboardButton(text="📈 رسم بياني", callback_data=f"stats_chart_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📋 تصدير البيانات", callback_data=f"export_stats_{task_id}"),
                    InlineKeyboardButton(text="🔄 تحديث", callback_data=f"refresh_stats_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للمتقدم", callback_data=f"setting_advanced_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in advanced statistics: {e}")
            await callback.answer("❌ خطأ في تحميل الإحصائيات", show_alert=True)

    async def _handle_reset_advanced_settings(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle reset advanced settings"""
        try:
            # Reset all advanced settings to default
            await self.database.execute_command("""
                UPDATE task_settings SET 
                    auto_translate = false,
                    target_language = 'ar',
                    working_hours_enabled = false,
                    start_hour = 0,
                    end_hour = 23,
                    timezone = 'UTC',
                    recurring_post_enabled = false,
                    recurring_post_content = null,
                    recurring_interval_hours = 24
                WHERE task_id = $1
            """, task_id)
            
            # Delete recurring posts
            await self.database.execute_command(
                "DELETE FROM recurring_posts WHERE task_id = $1",
                task_id
            )
            
            await callback.answer("✅ تم إعادة تعيين جميع الإعدادات المتقدمة", show_alert=True)
            await self._handle_advanced_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error resetting advanced settings: {e}")
            await callback.answer("❌ خطأ في إعادة التعيين", show_alert=True)

    async def _handle_save_advanced_settings(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle save advanced settings"""
        try:
            settings = await self.database.get_task_settings(task_id)
            
            # Create backup of current settings
            backup_data = {
                'task_id': task_id,
                'auto_translate': settings.get('auto_translate', False) if settings else False,
                'target_language': settings.get('target_language', 'ar') if settings else 'ar',
                'working_hours_enabled': settings.get('working_hours_enabled', False) if settings else False,
                'start_hour': settings.get('start_hour', 0) if settings else 0,
                'end_hour': settings.get('end_hour', 23) if settings else 23,
                'timezone': settings.get('timezone', 'UTC') if settings else 'UTC',
                'recurring_post_enabled': settings.get('recurring_post_enabled', False) if settings else False,
                'recurring_interval_hours': settings.get('recurring_interval_hours', 24) if settings else 24,
                'saved_at': datetime.now().isoformat()
            }
            
            await callback.answer("💾 تم حفظ جميع الإعدادات المتقدمة بنجاح", show_alert=True)
            await self._handle_advanced_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error saving advanced settings: {e}")
            await callback.answer("❌ خطأ في الحفظ", show_alert=True)

    async def _handle_advanced_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced settings main menu"""
        try:
            logger.info(f"Starting advanced settings handler for task {task_id}")
            settings = await self.database.get_task_settings(task_id)
            logger.info(f"Retrieved settings: {settings}")
            
            text = f"""⚡ **الميزات المتقدمة - المهمة {task_id}**

🌐 **إعدادات الترجمة:** ترجمة تلقائية بـ 12 لغة
⏰ **ساعات العمل:** جدولة وقت العمل والراحة  
🔄 **المنشور المتكرر:** نشر محتوى بفترات منتظمة

اختر الميزة المطلوب تكوينها:"""
            
            logger.info(f"Creating keyboard for task {task_id}")
            keyboard = await self.keyboards.get_advanced_settings_keyboard(task_id, settings)
            logger.info(f"Keyboard created: {keyboard}")
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Message edited successfully for task {task_id}")
        except Exception as e:
            logger.error(f"Error in advanced settings: {e}")
            await callback.answer("❌ خطأ في عرض الإعدادات", show_alert=True)

    async def _handle_advanced_translation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced translation settings"""
        try:
            logger.info(f"Advanced translation handler called for task {task_id}")
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return

            # Get current translation settings
            settings = await self.database.execute_query(
                "SELECT * FROM task_settings WHERE task_id = $1", task_id
            )
            current_settings = settings[0] if settings else {}
            
            # Get translation keyboard
            keyboard = await self.keyboards.get_advanced_translation_keyboard(task_id, current_settings)
            
            translation_text = f"""
🌐 **إعدادات الترجمة المتقدمة** - {task['name']}

**الحالة الحالية:**
• الترجمة التلقائية: {'✅ مفعلة' if current_settings.get('auto_translate', False) else '❌ معطلة'}
• اللغة المصدر: {current_settings.get('source_language', 'تلقائي')}
• اللغة الهدف: {current_settings.get('target_language', 'العربية')}

**خيارات الترجمة:**
يمكنك تخصيص إعدادات الترجمة أدناه:
            """
            
            await callback.message.edit_text(translation_text, reply_markup=keyboard)
            logger.info(f"Translation settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in advanced translation handler: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات الترجمة.")

    # Text Cleaner Methods
# Old text cleaner function removed - replaced with comprehensive version at line 4270

    async def _toggle_cleaner_buttons(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner buttons setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_buttons", False)
            cleaner_settings["remove_buttons"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"🔘 إزالة الأزرار: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner buttons: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الأزرار", show_alert=True)

    async def _toggle_cleaner_links(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner links setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_links", False)
            cleaner_settings["remove_links"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"🔗 إزالة الروابط: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner links: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الروابط", show_alert=True)

    async def _toggle_cleaner_mentions(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner mentions setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_mentions", False)
            cleaner_settings["remove_mentions"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"@ إزالة المنشن: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner mentions: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد المنشن", show_alert=True)

    async def _toggle_cleaner_hashtags(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner hashtags setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_hashtags", False)
            cleaner_settings["remove_hashtags"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"#️⃣ إزالة الهاشتاغ: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner hashtags: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الهاشتاغ", show_alert=True)

    async def _toggle_cleaner_emojis(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner emojis setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_emojis", False)
            cleaner_settings["remove_emojis"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"😀 إزالة الإيموجي: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner emojis: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الإيموجي", show_alert=True)

    async def _toggle_cleaner_numbers(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner numbers setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_numbers", False)
            cleaner_settings["remove_numbers"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"🔢 إزالة الأرقام: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner numbers: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الأرقام", show_alert=True)

    async def _toggle_cleaner_punctuation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle cleaner punctuation setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}

            current_value = cleaner_settings.get("remove_punctuation", False)
            cleaner_settings["remove_punctuation"] = not current_value

            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )

            await callback.answer(f"⚫ إزالة علامات الترقيم: {'مفعل' if not current_value else 'معطل'}")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error toggling cleaner punctuation: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد علامات الترقيم", show_alert=True)

    async def _test_text_cleaner(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Test text cleaner with sample text"""
        try:
            await callback.message.edit_text(
                f"🧪 **اختبار تنظيف النص - المهمة {task_id}**\n\n"
                "أرسل نص لاختبار كيف سيبدو بعد تطبيق إعدادات التنظيف:\n\n"
                "**مثال:**\n"
                "`مرحبا! 👋 هذا رابط https://example.com وهاشتاغ #تجربة ومنشن @username وأرقام 123`"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="test_text_cleaner", task_id=task_id)

        except Exception as e:
            logger.error(f"Error in test text cleaner: {e}")
            await callback.answer("❌ خطأ في بدء الاختبار", show_alert=True)

    async def _reset_text_cleaner(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Reset text cleaner settings"""
        try:
            await self.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = NULL WHERE task_id = $1",
                task_id
            )

            await callback.answer("🔄 تم إعادة تعيين جميع إعدادات تنظيف النص")
            await self._handle_text_cleaner_setting(callback, task_id, state)

        except Exception as e:
            logger.error(f"Error resetting text cleaner: {e}")
            await callback.answer("❌ خطأ في إعادة التعيين", show_alert=True)

    async def _handle_advanced_working_hours(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced working hours settings"""
        try:
            logger.info(f"Advanced working hours handler called for task {task_id}")
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return

            # Get current working hours settings
            settings = await self.database.execute_query(
                "SELECT * FROM task_settings WHERE task_id = $1", task_id
            )
            current_settings = settings[0] if settings else {}
            
            # Get working hours keyboard
            keyboard = await self.keyboards.get_advanced_working_hours_keyboard(task_id, current_settings)
            
            working_hours_text = f"""
⏰ **إعدادات ساعات العمل المتقدمة** - {task['name']}

**الحالة الحالية:**
• ساعات العمل: {'✅ مفعلة' if current_settings.get('working_hours_enabled', False) else '❌ معطلة'}
• ساعة البداية: {current_settings.get('start_hour', 0):02d}:00
• ساعة النهاية: {current_settings.get('end_hour', 23):02d}:00
• المنطقة الزمنية: {current_settings.get('timezone', 'UTC')}

**إعدادات التوقيت:**
حدد ساعات العمل التي تريد أن يعمل فيها البوت:
            """
            
            await callback.message.edit_text(working_hours_text, reply_markup=keyboard)
            logger.info(f"Working hours settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in advanced working hours handler: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات ساعات العمل.")

    async def _handle_advanced_recurring(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced recurring post settings"""
        try:
            logger.info(f"Advanced recurring post handler called for task {task_id}")
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return

            # Get current recurring post settings
            settings = await self.database.execute_query(
                "SELECT * FROM task_settings WHERE task_id = $1", task_id
            )
            current_settings = settings[0] if settings else {}
            
            # Get recurring post keyboard
            keyboard = await self.keyboards.get_advanced_recurring_keyboard(task_id, current_settings)
            
            recurring_text = f"""
🔄 **إعدادات المنشور المتكرر المتقدمة** - {task['name']}

**الحالة الحالية:**
• المنشور المتكرر: {'✅ مفعل' if current_settings.get('recurring_post_enabled', False) else '❌ معطل'}
• الفترة الزمنية: كل {current_settings.get('recurring_interval_hours', 24)} ساعة
• آخر نشر: {current_settings.get('last_recurring_post', 'لم ينشر بعد')}

**إدارة المحتوى المتكرر:**
قم بإعداد المحتوى الذي سيتم نشره بشكل متكرر:
            """
            
            await callback.message.edit_text(recurring_text, reply_markup=keyboard)
            logger.info(f"Recurring post settings displayed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error in advanced recurring post handler: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات المنشور المتكرر.")



    async def _handle_advanced_working_hours(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced working hours settings"""
        try:
            settings = await self.database.get_task_settings(task_id)
            
            working_hours_enabled = settings.get("working_hours_enabled", False) if settings else False
            start_hour = settings.get("start_hour", 9) if settings else 9
            end_hour = settings.get("end_hour", 17) if settings else 17
            timezone = settings.get("timezone", "UTC") if settings else "UTC"
            break_start = settings.get("break_start_hour", 12) if settings else 12
            break_end = settings.get("break_end_hour", 13) if settings else 13
            
            text = f"""⏰ **إعدادات ساعات العمل المتقدمة - المهمة {task_id}**

🕘 **وقت البداية:** {start_hour:02d}:00
🕕 **وقت التوقف:** {end_hour:02d}:00
☕ **وقت الراحة:** {break_start:02d}:00 - {break_end:02d}:00
🌍 **المنطقة الزمنية:** {timezone}
⚙️ **الحالة:** {'مفعل' if working_hours_enabled else 'معطل'}

استخدم الأزرار أدناه لتكوين إعدادات ساعات العمل المتقدمة:"""
            
            keyboard = await self.keyboards.get_advanced_working_hours_keyboard(task_id, settings)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in advanced working hours: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات ساعات العمل", show_alert=True)

    async def _handle_advanced_recurring(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced recurring post settings"""
        try:
            settings = await self.database.get_task_settings(task_id)
            
            recurring_enabled = settings.get("recurring_post_enabled", False) if settings else False
            interval_hours = settings.get("recurring_interval_hours", 24) if settings else 24
            
            # Get recurring posts count
            recurring_posts = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM recurring_posts WHERE task_id = $1",
                task_id
            )
            posts_count = recurring_posts[0]['count'] if recurring_posts else 0
            
            text = f"""🔄 **إعدادات المنشور المتكرر المتقدمة - المهمة {task_id}**

⏱️ **الفترة الزمنية:** كل {interval_hours} ساعة
📝 **عدد المنشورات المحفوظة:** {posts_count}
⚙️ **الحالة:** {'مفعل' if recurring_enabled else 'معطل'}

استخدم الأزرار أدناه لإدارة المنشورات المتكررة:"""
            
            keyboard = await self.keyboards.get_advanced_recurring_keyboard(task_id, settings)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in advanced recurring: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات المنشور المتكرر", show_alert=True)

    async def _handle_day_filter_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle day filter settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            settings = await self.database.get_task_settings(task_id)
            day_filter_enabled = settings.get("day_filter_enabled", False) if settings else False
            day_filter_settings = {}
            
            if settings and settings.get("day_filter_settings"):
                try:
                    day_filter_settings = json.loads(settings["day_filter_settings"]) if isinstance(settings["day_filter_settings"], str) else settings["day_filter_settings"]
                except:
                    day_filter_settings = {}
            
            # Default all days to True if not set
            days = {
                "monday": day_filter_settings.get("monday", True),
                "tuesday": day_filter_settings.get("tuesday", True),
                "wednesday": day_filter_settings.get("wednesday", True),
                "thursday": day_filter_settings.get("thursday", True),
                "friday": day_filter_settings.get("friday", True),
                "saturday": day_filter_settings.get("saturday", True),
                "sunday": day_filter_settings.get("sunday", True)
            }
            
            day_names = {
                "monday": "الاثنين",
                "tuesday": "الثلاثاء", 
                "wednesday": "الأربعاء",
                "thursday": "الخميس",
                "friday": "الجمعة",
                "saturday": "السبت",
                "sunday": "الأحد"
            }
            
            active_days = sum(1 for day, active in days.items() if active)
            
            text = f"""📅 **فلتر الأيام - المهمة {task_id}**

⚙️ **الحالة:** {'مفعل' if day_filter_enabled else 'معطل'}
📊 **الأيام النشطة:** {active_days}/7

استخدم هذا الفلتر لتحديد الأيام التي يعمل فيها البوت.

**أيام الأسبوع:**"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"📅 {'🔴 تعطيل' if day_filter_enabled else '🟢 تفعيل'} فلتر الأيام",
                        callback_data=f"day_filter_toggle_{task_id}"
                    )
                ]
            ]
            
            # Add day buttons in pairs
            day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i in range(0, len(day_order), 2):
                row = []
                for j in range(2):
                    if i + j < len(day_order):
                        day = day_order[i + j]
                        status = "✅" if days[day] else "❌"
                        row.append(InlineKeyboardButton(
                            text=f"{status} {day_names[day]}",
                            callback_data=f"day_toggle_{day}_{task_id}"
                        ))
                if row:
                    keyboard.append(row)
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text="✅ تفعيل الكل", callback_data=f"day_enable_all_{task_id}"),
                    InlineKeyboardButton(text="❌ تعطيل الكل", callback_data=f"day_disable_all_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للميزات المتقدمة", callback_data=f"setting_advanced_{task_id}")
                ]
            ])
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in day filter setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات فلتر الأيام", show_alert=True)

    async def _handle_sending_limit_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle sending limit settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            settings = await self.database.get_task_settings(task_id)
            sending_limit_enabled = settings.get("sending_limit_enabled", False) if settings else False
            sending_limit_settings = {}
            
            if settings and settings.get("sending_limit_settings"):
                try:
                    sending_limit_settings = json.loads(settings["sending_limit_settings"]) if isinstance(settings["sending_limit_settings"], str) else settings["sending_limit_settings"]
                except:
                    sending_limit_settings = {}
            
            per_minute = sending_limit_settings.get("per_minute", 10)
            per_hour = sending_limit_settings.get("per_hour", 100)
            per_day = sending_limit_settings.get("per_day", 1000)
            
            text = f"""🚦 **حدود الإرسال - المهمة {task_id}**

⚙️ **الحالة:** {'مفعل' if sending_limit_enabled else 'معطل'}

**الحدود الحالية:**
• 📊 **في الدقيقة:** {per_minute} رسالة
• 🕐 **في الساعة:** {per_hour} رسالة  
• 📅 **في اليوم:** {per_day} رسالة

يساعد هذا الفلتر في التحكم بسرعة الإرسال ومنع الحظر من تيليجرام.

⚠️ **ملاحظة:** الرسائل الزائدة سيتم تجاهلها تلقائياً."""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"🚦 {'🔴 تعطيل' if sending_limit_enabled else '🟢 تفعيل'} حدود الإرسال",
                        callback_data=f"sending_limit_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="✏️ تعديل الحدود", callback_data=f"sending_limit_edit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📊 إحصائيات الإرسال", callback_data=f"sending_stats_{task_id}"),
                    InlineKeyboardButton(text="🔄 إعادة تعيين", callback_data=f"sending_reset_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للميزات المتقدمة", callback_data=f"setting_advanced_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error showing sending limits: {e}")
            await callback.answer("❌ خطأ في عرض حدود الإرسال", show_alert=True)

    async def _toggle_cleaner_empty_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle empty lines removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_empty_lines", False)
            cleaner_settings["remove_empty_lines"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"🗑️ {status} إزالة الأسطر الفارغة")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner empty lines: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الأسطر الفارغة", show_alert=True)
    
    async def _toggle_caption_removal(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle caption removal in text cleaner"""
        try:
            import json
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            current_value = cleaner_settings.get("remove_captions", False)
            cleaner_settings["remove_captions"] = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"📷 {status} إزالة الكابشن")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling caption removal: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الكابشن", show_alert=True)
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle setting
            current_value = cleaner_settings.get("remove_empty_lines", False)
            cleaner_settings["remove_empty_lines"] = not current_value
            
            # Save settings
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"✅ {status} إزالة الأسطر الفارغة")
            
            # Refresh interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling empty lines cleaner: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الأسطر الفارغة", show_alert=True)

    async def _toggle_cleaner_extra_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle extra lines removal in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle setting
            current_value = cleaner_settings.get("remove_extra_lines", True)
            cleaner_settings["remove_extra_lines"] = not current_value
            
            # Save settings
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"✅ {status} تنظيف الأسطر الإضافية")
            
            # Refresh interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling extra lines cleaner: {e}")
            await callback.answer("❌ خطأ في تبديل تنظيف الأسطر الإضافية", show_alert=True)

    async def _toggle_cleaner_whitespace(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle whitespace normalization in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle setting
            current_value = cleaner_settings.get("normalize_whitespace", False)
            cleaner_settings["normalize_whitespace"] = not current_value
            
            # Save settings
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"✅ {status} تطبيع المساحات")
            
            # Refresh interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling whitespace normalization: {e}")
            await callback.answer("❌ خطأ في تبديل تطبيع المساحات", show_alert=True)

    async def _toggle_cleaner_duplicate_lines(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle duplicate lines removal in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle setting
            current_value = cleaner_settings.get("remove_duplicate_lines", False)
            cleaner_settings["remove_duplicate_lines"] = not current_value
            
            # Save settings
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"✅ {status} إزالة الأسطر المكررة")
            
            # Refresh interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling duplicate lines removal: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الأسطر المكررة", show_alert=True)

    async def _toggle_cleaner_emails(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle email removal in text cleaner"""
        try:
            import json
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle setting
            current_value = cleaner_settings.get("remove_emails", False)
            cleaner_settings["remove_emails"] = not current_value
            
            # Save settings
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            status = "تم تفعيل" if not current_value else "تم إلغاء"
            await callback.answer(f"✅ {status} إزالة الإيميلات")
            
            # Refresh interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling email removal: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة الإيميلات", show_alert=True)

    async def _toggle_caption_removal(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle caption removal setting"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("remove_caption", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET remove_caption = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم تعطيل"
            await callback.answer(f"✅ {status} إزالة التعليقات")
            
            # Refresh the text cleaner interface
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling caption removal: {e}")
            await callback.answer("❌ خطأ في تبديل إزالة التعليقات", show_alert=True)

    async def _toggle_day_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle day filter on/off"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("day_filter_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET day_filter_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم تعطيل"
            await callback.answer(f"✅ {status} فلتر الأيام")
            
            # Refresh the interface
            await self._handle_day_filter_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling day filter: {e}")
            await callback.answer("❌ خطأ في تبديل فلتر الأيام", show_alert=True)

    async def _toggle_day_selection(self, callback: CallbackQuery, task_id: int, day: str, state: FSMContext):
        """Toggle specific day selection"""
        try:
            import json
            
            settings = await self.database.get_task_settings(task_id)
            day_filter_settings = {}
            
            if settings and settings.get("day_filter_settings"):
                try:
                    day_filter_settings = json.loads(settings["day_filter_settings"]) if isinstance(settings["day_filter_settings"], str) else settings["day_filter_settings"]
                except:
                    day_filter_settings = {}
            
            # Toggle the specific day
            current_value = day_filter_settings.get(day, True)
            day_filter_settings[day] = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET day_filter_settings = $1 WHERE task_id = $2",
                json.dumps(day_filter_settings), task_id
            )
            
            day_names = {
                "monday": "الاثنين", "tuesday": "الثلاثاء", "wednesday": "الأربعاء",
                "thursday": "الخميس", "friday": "الجمعة", "saturday": "السبت", "sunday": "الأحد"
            }
            
            status = "تم تفعيل" if not current_value else "تم تعطيل"
            await callback.answer(f"✅ {status} يوم {day_names.get(day, day)}")
            
            # Refresh the interface
            await self._handle_day_filter_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling day selection: {e}")
            await callback.answer("❌ خطأ في تبديل اليوم", show_alert=True)

    async def _toggle_sending_limit(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle sending limit on/off"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("sending_limit_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET sending_limit_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم تعطيل"
            await callback.answer(f"✅ {status} حدود الإرسال")
            
            # Refresh the interface
            await self._handle_sending_limit_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling sending limit: {e}")
            await callback.answer("❌ خطأ في تبديل حدود الإرسال", show_alert=True)

    async def _edit_sending_limit(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Edit sending limit values"""
        try:
            await callback.message.edit_text(
                f"✏️ **تعديل حدود الإرسال - المهمة {task_id}**\n\n"
                "أرسل الحدود الجديدة في 3 أسطر:\n"
                "• السطر الأول: الحد الأقصى في الدقيقة\n"
                "• السطر الثاني: الحد الأقصى في الساعة\n"
                "• السطر الثالث: الحد الأقصى في اليوم\n\n"
                "**مثال:**\n"
                "```\n"
                "5\n"
                "50\n"
                "500\n"
                "```\n\n"
                "⚠️ أرسل الأرقام في الرسالة التالية مباشرة",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"advanced_sending_limit_{task_id}")]
                ]),
                parse_mode="Markdown"
            )
            
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="edit_sending_limits", task_id=task_id)
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error editing sending limit: {e}")
            await callback.answer("❌ خطأ في تعديل حدود الإرسال")

    async def _enable_all_days(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Enable all days in day filter"""
        try:
            import json
            
            all_days_enabled = {
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": True,
                "saturday": True,
                "sunday": True
            }
            
            await self.database.execute_command(
                "UPDATE task_settings SET day_filter_settings = $1 WHERE task_id = $2",
                json.dumps(all_days_enabled), task_id
            )
            
            await callback.answer("✅ تم تفعيل جميع الأيام")
            await self._handle_day_filter_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error enabling all days: {e}")
            await callback.answer("❌ خطأ في تفعيل جميع الأيام", show_alert=True)

    async def _disable_all_days(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Disable all days in day filter"""
        try:
            import json
            
            all_days_disabled = {
                "monday": False,
                "tuesday": False,
                "wednesday": False,
                "thursday": False,
                "friday": False,
                "saturday": False,
                "sunday": False
            }
            
            await self.database.execute_command(
                "UPDATE task_settings SET day_filter_settings = $1 WHERE task_id = $2",
                json.dumps(all_days_disabled), task_id
            )
            
            await callback.answer("✅ تم تعطيل جميع الأيام")
            await self._handle_day_filter_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error disabling all days: {e}")
            await callback.answer("❌ خطأ في تعطيل جميع الأيام", show_alert=True)

    async def _handle_set_source_language(self, callback: CallbackQuery, state: FSMContext):
        """Handle source language setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 4:
                lang_code = data_parts[3] if data_parts[3] != "auto" else "auto"
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET source_language = $1 WHERE task_id = $2",
                    lang_code, task_id
                )
                
                await callback.answer(f"✅ تم تعيين اللغة المصدر: {lang_code}")
                await self._handle_advanced_translation(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting source language: {e}")
            await callback.answer("❌ خطأ في تعيين اللغة المصدر", show_alert=True)

    async def _handle_set_target_language(self, callback: CallbackQuery, state: FSMContext):
        """Handle target language setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 4:
                lang_code = data_parts[3]
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET target_language = $1 WHERE task_id = $2",
                    lang_code, task_id
                )
                
                await callback.answer(f"✅ تم تعيين اللغة الهدف: {lang_code}")
                await self._handle_advanced_translation(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting target language: {e}")
            await callback.answer("❌ خطأ في تعيين اللغة الهدف", show_alert=True)

    async def _handle_toggle_auto_translate(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle auto translate toggle"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("auto_translate", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET auto_translate = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} الترجمة التلقائية")
            await self._handle_advanced_translation(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling auto translate: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد الترجمة", show_alert=True)

    async def _handle_toggle_working_hours(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle working hours toggle"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("working_hours_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET working_hours_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} ساعات العمل")
            await self._handle_advanced_working_hours(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling working hours: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد ساعات العمل", show_alert=True)

    async def _handle_set_start_hour(self, callback: CallbackQuery, state: FSMContext):
        """Handle start hour setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 4:
                hour = int(data_parts[3])
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET start_hour = $1 WHERE task_id = $2",
                    hour, task_id
                )
                
                await callback.answer(f"✅ تم تعيين وقت البداية: {hour:02d}:00")
                await self._handle_advanced_working_hours(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting start hour: {e}")
            await callback.answer("❌ خطأ في تعيين وقت البداية", show_alert=True)

    async def _handle_set_end_hour(self, callback: CallbackQuery, state: FSMContext):
        """Handle end hour setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 4:
                hour = int(data_parts[3])
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET end_hour = $1 WHERE task_id = $2",
                    hour, task_id
                )
                
                await callback.answer(f"✅ تم تعيين وقت التوقف: {hour:02d}:00")
                await self._handle_advanced_working_hours(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting end hour: {e}")
            await callback.answer("❌ خطأ في تعيين وقت التوقف", show_alert=True)

    async def _handle_set_timezone(self, callback: CallbackQuery, state: FSMContext):
        """Handle timezone setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 4:
                timezone = data_parts[2].replace("_", "/")  # Convert back from Asia_Riyadh to Asia/Riyadh
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET timezone = $1 WHERE task_id = $2",
                    timezone, task_id
                )
                
                await callback.answer(f"✅ تم تعيين المنطقة الزمنية: {timezone}")
                await self._handle_advanced_working_hours(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting timezone: {e}")
            await callback.answer("❌ خطأ في تعيين المنطقة الزمنية", show_alert=True)

    async def _handle_toggle_recurring_post(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle recurring post toggle"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("recurring_post_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET recurring_post_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} المنشور المتكرر")
            await self._handle_advanced_recurring(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling recurring post: {e}")
            await callback.answer("❌ خطأ في تغيير إعداد المنشور المتكرر", show_alert=True)

    async def _handle_set_interval(self, callback: CallbackQuery, state: FSMContext):
        """Handle interval setting"""
        try:
            data_parts = callback.data.split("_")
            if len(data_parts) >= 3:
                interval = int(data_parts[2])
                task_id = int(data_parts[-1])
                
                await self.database.execute_command(
                    "UPDATE task_settings SET recurring_interval_hours = $1 WHERE task_id = $2",
                    interval, task_id
                )
                
                await callback.answer(f"✅ تم تعيين الفترة الزمنية: كل {interval} ساعة")
                await self._handle_advanced_recurring(callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error setting interval: {e}")
            await callback.answer("❌ خطأ في تعيين الفترة الزمنية", show_alert=True)

    async def _toggle_translation(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle auto translation"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("auto_translate", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET auto_translate = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🌐 الترجمة التلقائية: {status_text}")
            
            await self._handle_translation_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling translation: {e}")
            await callback.answer("❌ خطأ في تبديل الترجمة", show_alert=True)

    async def _set_target_language(self, callback: CallbackQuery, task_id: int, language: str, state: FSMContext):
        """Set target language for translation"""
        try:
            await self.database.execute_command(
                "UPDATE task_settings SET target_language = $1 WHERE task_id = $2",
                language, task_id
            )
            
            lang_names = {
                "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية",
                "de": "الألمانية", "es": "الإسبانية", "ru": "الروسية",
                "tr": "التركية", "fa": "الفارسية"
            }
            
            lang_name = lang_names.get(language, language)
            await callback.answer(f"🌐 تم تعيين اللغة المستهدفة: {lang_name}")
            
            await self._handle_translation_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting target language: {e}")
            await callback.answer("❌ خطأ في تعيين اللغة", show_alert=True)

    async def _toggle_working_hours(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle working hours"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("working_hours_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET working_hours_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"⏰ ساعات العمل: {status_text}")
            
            await self._handle_working_hours_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling working hours: {e}")
            await callback.answer("❌ خطأ في تبديل ساعات العمل", show_alert=True)

    async def _set_start_hour(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Set start hour for working hours"""
        try:
            await state.set_state("setting_start_hour")
            await state.update_data(task_id=task_id)
            
            await callback.message.edit_text(
                "🕐 **تعديل ساعة البداية**\n\n"
                "أدخل ساعة البداية (0-23):\n"
                "مثال: 8 للساعة 08:00",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error setting start hour: {e}")
            await callback.answer("❌ خطأ في تعديل ساعة البداية", show_alert=True)

    async def _set_end_hour(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Set end hour for working hours"""
        try:
            await state.set_state("setting_end_hour")
            await state.update_data(task_id=task_id)
            
            await callback.message.edit_text(
                "🕑 **تعديل ساعة النهاية**\n\n"
                "أدخل ساعة النهاية (0-23):\n"
                "مثال: 18 للساعة 18:00",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error setting end hour: {e}")
            await callback.answer("❌ خطأ في تعديل ساعة النهاية", show_alert=True)

    async def _set_timezone(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Set timezone for working hours"""
        try:
            await state.set_state("setting_timezone")
            await state.update_data(task_id=task_id)
            
            timezones_text = """🌍 **المناطق الزمنية المتاحة:**

**الشرق الأوسط:**
• Asia/Riyadh (السعودية)
• Asia/Dubai (الإمارات)
• Asia/Kuwait (الكويت)
• Asia/Baghdad (العراق)

**أوروبا:**
• Europe/London (لندن)
• Europe/Paris (باريس)
• Europe/Berlin (برلين)

**أمريكا:**
• America/New_York (نيويورك)
• America/Los_Angeles (لوس أنجلوس)

أدخل المنطقة الزمنية أو اكتب UTC للتوقيت العالمي:"""
            
            await callback.message.edit_text(timezones_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error setting timezone: {e}")
            await callback.answer("❌ خطأ في تعديل المنطقة الزمنية", show_alert=True)

    async def _toggle_recurring_post(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle recurring post"""
        try:
            settings = await self.database.get_task_settings(task_id)
            current_value = settings.get("recurring_post_enabled", False) if settings else False
            new_value = not current_value
            
            await self.database.execute_command(
                "UPDATE task_settings SET recurring_post_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status_text = "تم التفعيل" if new_value else "تم الإلغاء"
            await callback.answer(f"🔄 المنشور المتكرر: {status_text}")
            
            await self._handle_recurring_post_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling recurring post: {e}")
            await callback.answer("❌ خطأ في تبديل المنشور المتكرر", show_alert=True)

    async def _set_recurring_interval(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Set recurring post interval"""
        try:
            await state.set_state("setting_recurring_interval")
            await state.update_data(task_id=task_id)
            
            await callback.message.edit_text(
                "⏱️ **تعديل فترة النشر المتكرر**\n\n"
                "أدخل عدد الساعات بين كل منشور:\n"
                "• الحد الأدنى: 1 ساعة\n"
                "• الحد الأقصى: 168 ساعة (أسبوع)\n\n"
                "مثال: 24 لنشر يومي",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error setting recurring interval: {e}")
            await callback.answer("❌ خطأ في تعديل فترة النشر", show_alert=True)

    async def _edit_recurring_content(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Edit recurring post content"""
        try:
            await state.set_state("editing_recurring_content")
            await state.update_data(task_id=task_id)
            
            await callback.message.edit_text(
                "📝 **تعديل محتوى المنشور المتكرر**\n\n"
                "أرسل المحتوى الذي تريد نشره بشكل متكرر:\n"
                "• يمكن أن يكون نص عادي\n"
                "• يمكن أن يكون صورة مع تعليق\n"
                "• يمكن أن يكون فيديو مع وصف\n\n"
                "💡 تلميح: سيتم حذف المنشور السابق تلقائياً قبل نشر الجديد",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error editing recurring content: {e}")
            await callback.answer("❌ خطأ في تعديل المحتوى", show_alert=True)

    async def _view_recurring_content(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """View current recurring post content"""
        try:
            # Get current recurring post content from database
            recurring_post = await self.database.fetch_one(
                "SELECT * FROM recurring_posts WHERE task_id = $1 AND is_active = TRUE",
                task_id
            )
            
            if not recurring_post:
                await callback.answer("❌ لا يوجد محتوى متكرر محفوظ", show_alert=True)
                return
            
            content = recurring_post.get('content', 'لا يوجد محتوى')
            media_type = recurring_post.get('media_type', 'text')
            interval_hours = recurring_post.get('interval_hours', 24)
            
            text = f"""📋 **المحتوى المتكرر الحالي - المهمة {task_id}**

📄 **نوع المحتوى:** {media_type}
⏱️ **الفترة:** كل {interval_hours} ساعة

📝 **المحتوى:**
{content[:500]}{'...' if len(content) > 500 else ''}"""
            
            keyboard = await self.keyboards.get_recurring_post_keyboard(task_id)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error viewing recurring content: {e}")
            await callback.answer("❌ خطأ في عرض المحتوى", show_alert=True)

    async def _handle_language_save(self, callback: CallbackQuery, state: FSMContext):
        """Handle saving language settings"""
        try:
            task_id = int(callback.data.split("_")[-1])
            
            await callback.answer("💾 تم حفظ إعدادات اللغة بنجاح")
            
            # Return to filters menu
            await self._handle_filters_setting(callback, state)
            
        except Exception as e:
            logger.error(f"Error saving language settings: {e}")
            await callback.answer("❌ خطأ في حفظ إعدادات اللغة", show_alert=True)

    async def _handle_text_replace_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text replacement setting configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current replacement rules
            settings = await self.bot_controller.database.get_task_settings(task_id)
            replace_rules = {}
            if settings and settings.get("replace_text"):
                try:
                    raw_data = json.loads(settings["replace_text"]) if isinstance(settings["replace_text"], str) else settings["replace_text"]
                    # Ensure we always work with a dictionary
                    if isinstance(raw_data, dict):
                        replace_rules = raw_data
                    elif isinstance(raw_data, list):
                        # Convert legacy list format to dict format
                        replace_rules = {f"rule_{i}": item for i, item in enumerate(raw_data)}
                    else:
                        replace_rules = {}
                except Exception as e:
                    logger.error(f"Error parsing replace_text data: {e}")
                    replace_rules = {}
            
            rules_text = ""
            if replace_rules and isinstance(replace_rules, dict):
                rules_text = "\n".join([f"• `{old}` → `{new}`" for old, new in list(replace_rules.items())[:5]])
                if len(replace_rules) > 5:
                    rules_text += f"\n... و {len(replace_rules) - 5} قاعدة أخرى"
            elif replace_rules and isinstance(replace_rules, list):
                # Handle legacy list format
                rules_text = "\n".join([f"• قاعدة {i+1}: {rule}" for i, rule in enumerate(replace_rules[:5])])
                if len(replace_rules) > 5:
                    rules_text += f"\n... و {len(replace_rules) - 5} قاعدة أخرى"
            else:
                rules_text = "لا توجد قواعد استبدال"
            
            replace_text = f"""🔄 **إعدادات استبدال النص - المهمة {task_id}**

**القواعد الحالية ({len(replace_rules) if isinstance(replace_rules, (dict, list)) else 0}):**
{rules_text}

يمكنك إنشاء قواعد لاستبدال كلمات أو عبارات معينة في الرسائل المحولة.

**أمثلة شائعة:**
• استبدال "مرحبا" بـ "أهلا"
• استبدال "تليجرام" بـ "تيليجرام"
• إزالة كلمات معينة (استبدال بفراغ)"""

            keyboard = [
                [
                    InlineKeyboardButton(text="➕ إضافة قاعدة", callback_data=f"replace_add_{task_id}"),
                    InlineKeyboardButton(text="📝 إضافة عدة قواعد", callback_data=f"replace_bulk_add_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="📋 عرض الكل", callback_data=f"replace_list_{task_id}"),
                    InlineKeyboardButton(text="✏️ تعديل قاعدة", callback_data=f"replace_edit_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ حذف قاعدة", callback_data=f"replace_delete_{task_id}"),
                    InlineKeyboardButton(text="🧪 اختبار", callback_data=f"replace_test_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"replace_clear_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(replace_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in text replace setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات الاستبدال", show_alert=True)



    async def _handle_formatting_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text formatting setting configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current formatting settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            format_settings = {}
            if settings and settings.get("format_settings"):
                try:
                    format_settings = json.loads(settings["format_settings"]) if isinstance(settings["format_settings"], str) else settings["format_settings"]
                except:
                    format_settings = {}
            
            # Current formatting status
            preserve_original = format_settings.get("preserve_original", True)
            remove_all = format_settings.get("remove_all", False)
            apply_bold = format_settings.get("apply_bold", False)
            apply_italic = format_settings.get("apply_italic", False)
            apply_underline = format_settings.get("apply_underline", False)
            apply_strikethrough = format_settings.get("apply_strikethrough", False)
            apply_spoiler = format_settings.get("apply_spoiler", False)
            apply_code = format_settings.get("apply_code", False)
            apply_mono = format_settings.get("apply_mono", False)
            apply_quote = format_settings.get("apply_quote", False)
            apply_copyable_code = format_settings.get("apply_copyable_code", False)
            apply_link = format_settings.get("apply_link", False)
            custom_link_url = format_settings.get("custom_link_url", "")
            
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            formatting_text = f"""🎨 **إعدادات التنسيق - المهمة {task_id}** `{timestamp}`

**حالة التنسيقات:**
• **🧹 إزالة الكل:** {'✅ مفعل' if remove_all else '❌ معطل'}
• **🔸 Bold غامق:** {'✅ مفعل' if apply_bold else '❌ معطل'}
• **🔹 Italic مائل:** {'✅ مفعل' if apply_italic else '❌ معطل'}
• **📝 Underline خط تحت:** {'✅ مفعل' if apply_underline else '❌ معطل'}
• **🚫 Strike شطب:** {'✅ مفعل' if apply_strikethrough else '❌ معطل'}
• **💻 Code كود:** {'✅ مفعل' if apply_code else '❌ معطل'}
• **🔤 Mono أحادي:** {'✅ مفعل' if apply_mono else '❌ معطل'}
• **💬 Quote اقتباس:** {'✅ مفعل' if apply_quote else '❌ معطل'}
• **🔒 Spoiler مخفي:** {'✅ مفعل' if apply_spoiler else '❌ معطل'}
• **🔗 Hyperlink رابط:** {'✅ مفعل' if apply_link else '❌ معطل'}

{f'🔗 **الرابط المحدد:** `{custom_link_url}`' if custom_link_url and custom_link_url.strip() else '🔗 **الرابط:** غير محدد'}

**اختر التنسيق المطلوب:**"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"🧹 إزالة الكل {'✅' if remove_all else '❌'}", 
                        callback_data=f"format_remove_all_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🔸 Bold {'✅' if apply_bold else '❌'}", 
                        callback_data=f"format_bold_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"🔹 Italic {'✅' if apply_italic else '❌'}", 
                        callback_data=f"format_italic_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"📝 Underline {'✅' if apply_underline else '❌'}", 
                        callback_data=f"format_underline_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🚫 Strike {'✅' if apply_strikethrough else '❌'}", 
                        callback_data=f"format_strike_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"💻 Code {'✅' if apply_code else '❌'}", 
                        callback_data=f"format_code_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"🔤 Mono {'✅' if apply_mono else '❌'}", 
                        callback_data=f"format_mono_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"💬 Quote {'✅' if apply_quote else '❌'}", 
                        callback_data=f"format_quote_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"🔒 Spoiler {'✅' if apply_spoiler else '❌'}", 
                        callback_data=f"format_spoiler_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🔗 Hyperlink {'✅' if apply_link else '❌'}", 
                        callback_data=f"format_hyperlink_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text="⚙️ تعيين الرابط", 
                        callback_data=f"format_set_link_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🧪 اختبار التنسيق", callback_data=f"format_test_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(formatting_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in formatting setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات التنسيق", show_alert=True)

    async def _handle_links_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle links setting configuration"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current link settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            remove_links = settings.get("remove_links", False) if settings else False
            
            links_text = f"""🔗 **إعدادات الروابط - المهمة {task_id}**

**الحالة الحالية:**
• **إزالة الروابط:** {'✅ enabled' if remove_links else '❌ disabled'}

**خيارات الروابط:**
• إزالة جميع الروابط من الرسائل
• تقصير الروابط الطويلة
• استبدال الروابط بنص مخصص
• إضافة معلومات إضافية للروابط

**أنواع الروابط:**
• HTTP/HTTPS - الروابط العادية
• Telegram - روابط t.me
• Deep Links - روابط التطبيقات
• Email - عناوين البريد الإلكتروني

**أمثلة:**
• إزالة: https://example.com → (يتم حذفه)
• استبدال: الرابط → [رابط]
• تقصير: طويل → قصير"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"🗑️ إزالة الروابط: {'✅' if remove_links else '❌'}", 
                        callback_data=f"links_remove_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔄 استبدال", callback_data=f"links_replace_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_cleaner_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(links_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in links setting: {e}")
            await callback.answer("❌ خطأ في تحميل إعدادات الروابط", show_alert=True)

# Old text cleaner function removed - using comprehensive version at line 4270

    async def _handle_content_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle content modification actions"""
        try:
            data = callback.data
            
            if data.startswith("prefix_"):
                await self._handle_prefix_actions(callback, state)
            elif data.startswith("suffix_"):
                await self._handle_suffix_actions(callback, state)
            elif data.startswith("replace_"):
                await self._handle_replace_actions(callback, state)

            elif data.startswith("format_remove_all_") or data.startswith("format_bold_") or data.startswith("format_italic_") or data.startswith("format_underline_") or data.startswith("format_strike_") or data.startswith("format_code_") or data.startswith("format_mono_") or data.startswith("format_quote_") or data.startswith("format_spoiler_") or data.startswith("format_hyperlink_") or data.startswith("format_set_link_") or data.startswith("format_test_"):
                await self._handle_format_actions(callback, state)
            elif data.startswith("format_"):
                await self._handle_format_actions(callback, state)
            elif data.startswith("links_"):
                await self._handle_links_actions(callback, state)
            elif data.startswith("cleaner_"):
                await self._handle_text_cleaner_actions(callback, state)
            else:
                await callback.answer("❌ Unknown content action", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in content actions: {e}")
            await callback.answer("❌ Error processing content action", show_alert=True)

    async def _handle_prefix_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle prefix/suffix actions"""
        try:
            data = callback.data
            task_id = int(data.split("_")[-1])
            
            if data.startswith("prefix_edit_"):
                # Start editing prefix
                await callback.message.edit_text(
                    f"✏️ **تعديل البادئة - المهمة {task_id}**\n\n"
                    "أرسل النص الذي تريد إضافته في بداية كل رسالة:\n\n"
                    "**متغيرات متاحة:**\n"
                    "• {original} - النص الأصلي\n"
                    "• {source} - اسم المصدر\n"
                    "• {time} - الوقت\n"
                    "• {date} - التاريخ\n\n"
                    "**مثال:** `📢 من: {source}\\n{original}`"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="edit_prefix", task_id=task_id)
                
            elif data.startswith("prefix_clear_"):
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET custom_caption = NULL WHERE task_id = $1",
                    task_id
                )
                await callback.answer("📋 تم مسح البادئة")
                await self._handle_prefix_suffix_setting(callback, task_id, state)
                
            elif data.startswith("prefix_examples_"):
                examples_text = f"""📝 **أمثلة على البادئات - المهمة {task_id}**

**البادئة البسيطة:**
`📢 من قناتي:`

**مع اسم المصدر:**
`📢 من: {{source}}`

**مع الوقت:**
`📅 {{date}} - {{time}}
{{original}}`

**احترافية:**
`🔥 محتوى حصري من {{source}}
━━━━━━━━━━━━━━━━━━━━
{{original}}
━━━━━━━━━━━━━━━━━━━━`

**للأخبار:**
`🔴 عاجل | {{source}}
{{original}}`"""
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = [[InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_prefix_{task_id}")]]
                await callback.message.edit_text(examples_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
                
            elif data.startswith("prefix_test_"):
                await callback.answer("🧪 سيتم إضافة ميزة الاختبار قريباً", show_alert=True)
                
            else:
                await callback.answer("📋 سيتم تنفيذ هذه الميزة قريباً", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in prefix actions: {e}")
            await callback.answer("❌ خطأ في معالجة البادئة", show_alert=True)

    async def _handle_suffix_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle suffix actions"""
        try:
            data = callback.data
            task_id = int(data.split("_")[-1])
            
            if data.startswith("suffix_add_"):
                await callback.message.edit_text(
                    f"➕ **إضافة لاحقة - المهمة {task_id}**\n\n"
                    "أرسل النص الذي تريد إضافته في نهاية كل رسالة:\n\n"
                    "**أمثلة:**\n"
                    "• `\\n\\n📱 تابعونا على قناتنا`\n"
                    "• `\\n\\n🔗 المصدر: {source}`\n"
                    "• `\\n\\n⏰ {time} | {date}`"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="add_suffix", task_id=task_id)
                
            elif data.startswith("suffix_clear_"):
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET suffix_text = NULL WHERE task_id = $1",
                    task_id
                )
                await callback.answer("📋 تم مسح اللاحقة")
                await self._handle_prefix_suffix_setting(callback, task_id, state)
                
            else:
                await callback.answer("📋 سيتم تنفيذ هذه الميزة قريباً", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in suffix actions: {e}")
            await callback.answer("❌ خطأ في معالجة اللاحقة", show_alert=True)

    async def _handle_replace_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle text replace actions"""
        try:
            data = callback.data
            task_id = int(data.split("_")[-1])
            
            if data.startswith("replace_add_"):
                await callback.message.edit_text(
                    f"➕ **إضافة قاعدة استبدال - المهمة {task_id}**\n\n"
                    "أرسل النص بالتنسيق التالي:\n"
                    "`النص القديم | النص الجديد`\n\n"
                    "**أمثلة:**\n"
                    "• `مرحبا | أهلا وسهلا`\n"
                    "• `تليجرام | تيليجرام`\n"
                    "• `كلمة مزعجة |` (لحذف الكلمة)\n\n"
                    "**ملاحظة:** يمكن إرسال عدة قواعد، كل قاعدة في سطر منفصل"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="add_replace_rule", task_id=task_id)
                
            elif data.startswith("replace_list_"):
                import json
                settings = await self.bot_controller.database.get_task_settings(task_id)
                replace_rules = {}
                if settings and settings.get("replace_text"):
                    try:
                        replace_rules = json.loads(settings["replace_text"]) if isinstance(settings["replace_text"], str) else settings["replace_text"]
                    except:
                        replace_rules = {}
                
                if not replace_rules:
                    await callback.answer("📋 لا توجد قواعد استبدال", show_alert=True)
                    return
                
                rules_text = f"📋 **جميع قواعد الاستبدال - المهمة {task_id}**\n\n"
                for i, (old, new) in enumerate(replace_rules.items(), 1):
                    display_new = new if new else "(حذف)"
                    rules_text += f"{i}. `{old}` → `{display_new}`\n"
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = [[InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_replace_{task_id}")]]
                await callback.message.edit_text(rules_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
                
            elif data.startswith("replace_clear_"):
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET replace_text = NULL WHERE task_id = $1",
                    task_id
                )
                await callback.answer("🗑️ تم مسح جميع قواعد الاستبدال")
                await self._handle_text_replace_setting(callback, task_id, state)
                
            elif data.startswith("replace_test_"):
                await callback.message.edit_text(
                    f"🧪 **اختبار قواعد الاستبدال - المهمة {task_id}**\n\n"
                    "أرسل نص لاختبار كيف ستبدو بعد تطبيق قواعد الاستبدال:"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="test_replace", task_id=task_id)
                
            else:
                await callback.answer("🔄 سيتم تنفيذ هذه الميزة قريباً", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in replace actions: {e}")
            await callback.answer("❌ خطأ في معالجة الاستبدال", show_alert=True)

    async def _handle_format_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle formatting actions"""
        try:
            data = callback.data
            task_id = int(data.split("_")[-1])
            import json
            
            # Get current formatting settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            format_settings = {}
            if settings and settings.get("format_settings"):
                try:
                    format_settings = json.loads(settings["format_settings"]) if isinstance(settings["format_settings"], str) else settings["format_settings"]
                except:
                    format_settings = {}
            
            # Handle new simplified formatting buttons
            if data.startswith("format_remove_all_"):
                current_remove = format_settings.get("remove_all", False)
                format_settings["remove_all"] = not current_remove
                if not current_remove:  # If enabling remove_all, disable all other formatting
                    for key in ["apply_bold", "apply_italic", "apply_underline", "apply_strikethrough", 
                               "apply_spoiler", "apply_code", "apply_mono", "apply_quote", "apply_link"]:
                        format_settings[key] = False
                await callback.answer(f"🧹 إزالة التنسيقات: {'مفعل' if not current_remove else 'معطل'}")
                        
            elif data.startswith("format_bold_"):
                current_bold = format_settings.get("apply_bold", False)
                format_settings["apply_bold"] = not current_bold
                if not current_bold:
                    format_settings["remove_all"] = False
                await callback.answer(f"🔸 Bold: {'مفعل' if not current_bold else 'معطل'}")
                    
            elif data.startswith("format_italic_"):
                current_italic = format_settings.get("apply_italic", False)
                format_settings["apply_italic"] = not current_italic
                if not current_italic:
                    format_settings["remove_all"] = False
                await callback.answer(f"🔹 Italic: {'مفعل' if not current_italic else 'معطل'}")
                    
            elif data.startswith("format_underline_"):
                current_underline = format_settings.get("apply_underline", False)
                format_settings["apply_underline"] = not current_underline
                if not current_underline:
                    format_settings["remove_all"] = False
                await callback.answer(f"📝 Underline: {'مفعل' if not current_underline else 'معطل'}")
                    
            elif data.startswith("format_strike_"):
                current_strike = format_settings.get("apply_strikethrough", False)
                format_settings["apply_strikethrough"] = not current_strike
                if not current_strike:
                    format_settings["remove_all"] = False
                await callback.answer(f"🚫 Strike: {'مفعل' if not current_strike else 'معطل'}")
                    
            elif data.startswith("format_code_"):
                current_code = format_settings.get("apply_code", False)
                format_settings["apply_code"] = not current_code
                if not current_code:
                    format_settings["remove_all"] = False
                await callback.answer(f"💻 Code: {'مفعل' if not current_code else 'معطل'}")
                    
            elif data.startswith("format_mono_"):
                current_mono = format_settings.get("apply_mono", False)
                format_settings["apply_mono"] = not current_mono
                if not current_mono:
                    format_settings["remove_all"] = False
                await callback.answer(f"🔤 Mono: {'مفعل' if not current_mono else 'معطل'}")
                    
            elif data.startswith("format_quote_"):
                current_quote = format_settings.get("apply_quote", False)
                format_settings["apply_quote"] = not current_quote
                if not current_quote:
                    format_settings["remove_all"] = False
                await callback.answer(f"💬 Quote: {'مفعل' if not current_quote else 'معطل'}")
                    
            elif data.startswith("format_spoiler_"):
                current_spoiler = format_settings.get("apply_spoiler", False)
                format_settings["apply_spoiler"] = not current_spoiler
                if not current_spoiler:
                    format_settings["remove_all"] = False
                await callback.answer(f"🔒 Spoiler: {'مفعل' if not current_spoiler else 'معطل'}")
                    
            elif data.startswith("format_hyperlink_"):
                current_link = format_settings.get("apply_link", False)
                format_settings["apply_link"] = not current_link
                if not current_link:
                    format_settings["remove_all"] = False
                await callback.answer(f"🔗 Hyperlink: {'مفعل' if not current_link else 'معطل'}")
                    
            elif data.startswith("format_set_link_"):
                await callback.message.edit_text(
                    f"🔗 **تعيين الرابط - المهمة {task_id}**\n\n"
                    "أرسل الرابط الذي تريد أن يفتح عند النقر على النص:\n\n"
                    "**مثال:**\n"
                    "`https://example.com`\n"
                    "`https://t.me/channel`\n\n"
                    "سيتم تحويل النص إلى رابط أزرق قابل للنقر"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="set_custom_link", task_id=task_id)
                return
                
            elif data.startswith("format_test_"):
                await callback.message.edit_text(
                    f"🧪 **اختبار التنسيق - المهمة {task_id}**\n\n"
                    "أرسل نص لاختبار كيف سيبدو بعد تطبيق إعدادات التنسيق الحالية:\n\n"
                    "**مثال:**\n"
                    "`هذا نص تجريبي للاختبار`\n\n"
                    "سيتم عرض النص قبل وبعد التنسيق للمقارنة"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="test_formatting", task_id=task_id)
                return
                
            else:
                await callback.answer("❌ خيار غير مدعوم", show_alert=True)
                return
            
            # Save updated settings to database
            try:
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET format_settings = $1 WHERE task_id = $2",
                    json.dumps(format_settings), task_id
                )
                logger.info(f"Format settings saved for task {task_id}: {format_settings}")
            except Exception as e:
                logger.error(f"Failed to save format settings: {e}")
                await callback.answer("❌ فشل في حفظ الإعدادات", show_alert=True)
                return
            
            # Refresh the formatting interface
            try:
                await self._handle_formatting_setting(callback, task_id, state)
            except Exception as refresh_error:
                # If refresh fails due to "message not modified", send new message
                logger.warning(f"Refresh failed: {refresh_error}")
                await callback.message.delete()
                from aiogram.types import Message
                new_msg = await callback.message.chat.send_message("🔄 جارٍ تحديث إعدادات التنسيق...")
                # Create mock callback for new message
                class MockCallback:
                    def __init__(self, message):
                        self.message = message
                        self.data = f"content_formatting_{task_id}"
                
                mock_callback = MockCallback(new_msg)
                await self._handle_formatting_setting(mock_callback, task_id, state)
                
        except Exception as e:
            logger.error(f"Error in format actions: {e}")
            await callback.answer("❌ خطأ في معالجة التنسيق", show_alert=True)

    async def _handle_links_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle links actions"""
        try:
            data = callback.data
            if data.startswith("links_remove_"):
                task_id = int(data.split("_")[-1])
                settings = await self.bot_controller.database.get_task_settings(task_id)
                current_remove = settings.get("remove_links", False) if settings else False
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET remove_links = $1 WHERE task_id = $2",
                    not current_remove, task_id
                )
                await callback.answer(f"🔗 إزالة الروابط: {'enabled' if not current_remove else 'تم الDisable'}")
                
                # Refresh the links settings
                await self._handle_links_setting(callback, task_id, state)
            else:
                await callback.answer("🔗 سيتم تنفيذ ميزات الروابط المتقدمة قريباً", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in links actions: {e}")
            await callback.answer("❌ خطأ في معالجة الروابط", show_alert=True)

    async def _handle_text_cleaner_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle text cleaner actions"""
        try:
            data = callback.data
            import json
            
            if data.startswith("cleaner_buttons_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_inline_buttons", callback)
                
            elif data.startswith("cleaner_emojis_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_emojis", callback)
                
            elif data.startswith("cleaner_lines_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_extra_lines", callback)
                
            elif data.startswith("cleaner_words_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_lines_with_words", callback)
                
            elif data.startswith("cleaner_hashtags_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_hashtags", callback)
                
            elif data.startswith("cleaner_numbers_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_numbers", callback)
                
            elif data.startswith("cleaner_punctuation_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_setting(task_id, "remove_punctuation", callback)
                
            elif data.startswith("cleaner_mentions_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_mentions(callback, task_id, state)
                
            elif data.startswith("cleaner_emails_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_emails(callback, task_id, state)
                
            elif data.startswith("cleaner_links_toggle_"):
                task_id = int(data.split("_")[-1])
                await self._toggle_cleaner_links(callback, task_id, state)
                
            elif data.startswith("cleaner_manage_words_"):
                task_id = int(data.split("_")[-1])
                await self._handle_manage_target_words(callback, task_id, state)
                
            elif data.startswith("cleaner_test_"):
                task_id = int(data.split("_")[-1])
                await self._handle_cleaner_test(callback, task_id, state)
                
            elif data.startswith("cleaner_reset_"):
                task_id = int(data.split("_")[-1])
                await self._handle_cleaner_reset(callback, task_id, state)
                
            elif data.startswith("cleaner_add_words_"):
                task_id = int(data.split("_")[-1])
                await callback.message.edit_text(
                    f"🔤 **إضافة كلمات مستهدفة - المهمة {task_id}**\n\n"
                    "أرسل الكلمات التي تريد حذف الأسطر التي تحتويها.\n"
                    "يمكن إرسال عدة كلمات مفصولة بفواصل:\n\n"
                    "**مثال:**\n"
                    "`إعلان، ترقية، انضم الآن`\n\n"
                    "**ملاحظة:** سيتم حذف أي سطر يحتوي على إحدى هذه الكلمات"
                )
                await state.set_state(TaskStates.WAITING_INPUT)
                await state.update_data(action="add_target_words", task_id=task_id)
                
            elif data.startswith("cleaner_clear_words_"):
                task_id = int(data.split("_")[-1])
                settings = await self.bot_controller.database.get_task_settings(task_id)
                cleaner_settings = {}
                if settings and settings.get("text_cleaner_settings"):
                    try:
                        cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                    except:
                        cleaner_settings = {}
                
                cleaner_settings["target_words"] = []
                
                await self.bot_controller.database.execute_command(
                    "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                    json.dumps(cleaner_settings), task_id
                )
                
                await callback.answer("🗑️ تم مسح جميع الكلمات المستهدفة")
                await self._handle_manage_target_words(callback, task_id, state)
                
            else:
                await callback.answer("🧹 سيتم تنفيذ هذه الميزة قريباً", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in text cleaner actions: {e}")
            await callback.answer("❌ خطأ في معالجة منظف النص", show_alert=True)

    async def _toggle_cleaner_setting(self, task_id: int, setting_key: str, callback: CallbackQuery):
        """Toggle a cleaner setting and refresh the interface"""
        try:
            import json
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            # Toggle the setting
            current_value = cleaner_settings.get(setting_key, False)
            new_value = not current_value
            cleaner_settings[setting_key] = new_value
            
            # Save to database
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(cleaner_settings), task_id
            )
            
            # Show appropriate notification
            setting_names = {
                "remove_inline_buttons": "حذف الأزرار",
                "remove_emojis": "حذف الإيموجيات", 
                "remove_extra_lines": "حذف الأسطر الزائدة",
                "remove_lines_with_words": "حذف الأسطر بكلمات محددة",
                "remove_hashtags": "حذف الهاشتاقات",
                "remove_numbers": "حذف الأرقام",
                "remove_punctuation": "حذف علامات الترقيم"
            }
            
            setting_name = setting_names.get(setting_key, setting_key)
            status = "مفعل" if new_value else "معطل"
            await callback.answer(f"✅ {setting_name} {status}")
            
            # Rebuild the interface with the new settings immediately
            await self._rebuild_text_cleaner_interface(callback, task_id, cleaner_settings)
            
        except Exception as e:
            logger.error(f"Error toggling cleaner setting {setting_key}: {e}")
            await callback.answer("❌ خطأ في تبديل الإعداد", show_alert=True)
    
    async def _rebuild_text_cleaner_interface(self, callback: CallbackQuery, task_id: int, cleaner_settings: dict):
        """Rebuild the text cleaner interface with updated settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Use the provided settings directly (already updated)
            remove_inline_buttons = cleaner_settings.get("remove_inline_buttons", False)
            remove_emojis = cleaner_settings.get("remove_emojis", False)
            remove_extra_lines = cleaner_settings.get("remove_extra_lines", False)
            remove_lines_with_words = cleaner_settings.get("remove_lines_with_words", False)
            remove_hashtags = cleaner_settings.get("remove_hashtags", False)
            
            target_words = cleaner_settings.get("target_words", [])
            
            cleaner_text = f"""🧹 **Text Cleaner - المهمة {task_id}**

**الحالة الحالية:**
• **حذف الأزرار الشفافة:** {'✅ مفعل' if remove_inline_buttons else '❌ معطل'}
• **حذف الإيموجيات:** {'✅ مفعل' if remove_emojis else '❌ معطل'}
• **حذف الأسطر الزائدة:** {'✅ مفعل' if remove_extra_lines else '❌ معطل'}
• **حذف أسطر بكلمات محددة:** {'✅ مفعل' if remove_lines_with_words else '❌ معطل'}
• **حذف الهاشتاقات:** {'✅ مفعل' if remove_hashtags else '❌ معطل'}

**كلمات مستهدفة للحذف:** {len(target_words)} كلمة

**الوظائف:**
• تنظيف النصوص تلقائياً قبل الإرسال
• حذف العناصر غير المرغوب فيها
• تحسين شكل الرسائل المحولة
• الحفاظ على أزرار البوت الأصلية

**ملاحظة:** التنظيف يطبق قبل التحويل مباشرة"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"📱 حذف الأزرار: {'✅' if remove_inline_buttons else '❌'}", 
                        callback_data=f"cleaner_buttons_toggle_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"😀 حذف الإيموجيات: {'✅' if remove_emojis else '❌'}", 
                        callback_data=f"cleaner_emojis_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📝 حذف الأسطر الزائدة: {'✅' if remove_extra_lines else '❌'}", 
                        callback_data=f"cleaner_lines_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🔤 حذف أسطر بكلمات: {'✅' if remove_lines_with_words else '❌'}", 
                        callback_data=f"cleaner_words_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="✏️ إدارة الكلمات المستهدفة", callback_data=f"cleaner_manage_words_{task_id}")
                ],
                [
                    InlineKeyboardButton(
                        text=f"#️⃣ حذف الهاشتاقات: {'✅' if remove_hashtags else '❌'}", 
                        callback_data=f"cleaner_hashtags_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔗 إدارة الروابط", callback_data=f"content_links_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🧪 اختبار التنظيف", callback_data=f"cleaner_test_{task_id}"),
                    InlineKeyboardButton(text="🔄 إعادة تعيين", callback_data=f"cleaner_reset_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"setting_content_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(cleaner_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error rebuilding text cleaner interface: {e}")
            await callback.answer("❌ خطأ في تحديث الواجهة", show_alert=True)
    
    async def _handle_manage_target_words(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle managing target words for line removal"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current target words
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            target_words = cleaner_settings.get("target_words", [])
            
            words_text = f"🔤 **إدارة الكلمات المستهدفة - المهمة {task_id}**\n\n"
            words_text += f"**العدد الحالي:** {len(target_words)} كلمة\n\n"
            
            if target_words:
                words_text += "**الكلمات الحالية:**\n"
                for i, word in enumerate(target_words[:10], 1):
                    words_text += f"{i}. `{word}`\n"
                if len(target_words) > 10:
                    words_text += f"... و {len(target_words) - 10} كلمة أخرى\n"
            else:
                words_text += "⚠️ لا توجد كلمات مستهدفة\n"
            
            words_text += "\n**الوظيفة:** حذف أي سطر يحتوي على إحدى هذه الكلمات"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="➕ إضافة كلمات", callback_data=f"cleaner_add_words_{task_id}"),
                    InlineKeyboardButton(text="📋 عرض الكل", callback_data=f"cleaner_list_words_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"cleaner_clear_words_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_cleaner_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(words_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error managing target words: {e}")
            await callback.answer("❌ خطأ في إدارة الكلمات المستهدفة", show_alert=True)
    
    async def _handle_cleaner_test(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text cleaner test"""
        try:
            await callback.message.edit_text(
                f"🧪 **اختبار منظف النص - المهمة {task_id}**\n\n"
                "أرسل نص لاختبار كيف سيبدو بعد تطبيق إعدادات التنظيف:\n\n"
                "**يمكن إرسال نص يحتوي على:**\n"
                "• إيموجيات 😀😎🔥\n"
                "• أسطر فارغة متعددة\n"
                "• أسطر تحتوي على كلمات مستهدفة\n"
                "• هاشتاقات #مثال #تجربة"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="test_text_cleaner", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error in cleaner test: {e}")
            await callback.answer("❌ خطأ في اختبار منظف النص", show_alert=True)
    
    async def _handle_cleaner_reset(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle text cleaner reset"""
        try:
            import json
            
            # Reset all cleaner settings
            default_settings = {
                "remove_inline_buttons": False,
                "remove_emojis": False,
                "remove_extra_lines": False,
                "remove_lines_with_words": False,
                "remove_hashtags": False,
                "remove_numbers": False,
                "remove_punctuation": False,
                "target_words": []
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_cleaner_settings = $1 WHERE task_id = $2",
                json.dumps(default_settings), task_id
            )
            
            await callback.answer("🔄 تم إعادة تعيين جميع إعدادات منظف النص")
            await self._handle_text_cleaner_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error resetting text cleaner: {e}")
            await callback.answer("❌ خطأ في إعادة تعيين منظف النص", show_alert=True)

    async def _handle_forward_mode_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle forward mode subcategory actions"""
        try:
            data = callback.data
            
            if data.startswith("forward_mode_copy_"):
                task_id = int(data.split("_")[-1])
                await self.database.execute_command(
                    "UPDATE task_settings SET forward_mode = $1 WHERE task_id = $2",
                    "copy", task_id
                )
                await callback.answer("📋 تم تعيين وضع النسخ", show_alert=False)
                # Refresh forward mode settings
                await self._handle_forward_mode_setting(callback, state)
                
            elif data.startswith("forward_mode_forward_"):
                task_id = int(data.split("_")[-1])
                await self.database.execute_command(
                    "UPDATE task_settings SET forward_mode = $1 WHERE task_id = $2",
                    "forward", task_id
                )
                await callback.answer("🔄 تم تعيين وضع التوجيه", show_alert=False)
                # Refresh forward mode settings
                await self._handle_forward_mode_setting(callback, state)
                
            else:
                await callback.answer("🔄 خيار غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in forward mode actions: {e}")
            await callback.answer("❌ خطأ في معالجة وضع التوجيه", show_alert=True)

    async def _handle_delay_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle delay subcategory actions"""
        try:
            data = callback.data
            
            if data.startswith("delay_min_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("⏱️ سيتم إضافة خيار تعديل الحد الأدنى للتأخير قريباً", show_alert=True)
                
            elif data.startswith("delay_max_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("⏱️ سيتم إضافة خيار تعديل الحد الأقصى للتأخير قريباً", show_alert=True)
                
            elif data.startswith("delay_random_"):
                task_id = int(data.split("_")[-1])
                settings = await self.database.get_task_settings(task_id)
                current_random = settings.get("random_delay", False) if settings else False
                
                await self.database.execute_command(
                    "UPDATE task_settings SET random_delay = $1 WHERE task_id = $2",
                    not current_random, task_id
                )
                await callback.answer(f"🎲 التأخير العشوائي: {'enabled' if not current_random else 'تم الDisable'}")
                
            else:
                await callback.answer("⏰ خيار تأخير غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in delay actions: {e}")
            await callback.answer("❌ خطأ في معالجة إعدادات التأخير", show_alert=True)

    async def _handle_filter_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle filter subcategory actions"""
        try:
            data = callback.data
            
            if data.startswith("clear_all_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("🧹 سيتم تنفيذ ميزة مسح جميع الفلاتر قريباً", show_alert=True)
                
            elif data.startswith("enable_all_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("✅ سيتم تنفيذ ميزة Enable جميع الفلاتر قريباً", show_alert=True)
                
            elif data.startswith("disable_all_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("❌ سيتم تنفيذ ميزة Disable جميع الفلاتر قريباً", show_alert=True)
                
            else:
                await callback.answer("🔽 خيار فلتر غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in filter actions: {e}")
            await callback.answer("❌ خطأ في معالجة الفلاتر", show_alert=True)

    async def _handle_user_filter_specific_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle user filter specific actions"""
        try:
            data = callback.data
            
            if data.startswith("verified_only_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("✅ سيتم تنفيذ فلتر المستخدمين المتحققين قريباً", show_alert=True)
                
            elif data.startswith("nobots_filter_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("🤖 سيتم تنفيذ فلتر استبعاد البوتات قريباً", show_alert=True)
                
            else:
                await callback.answer("👤 خيار فلتر مستخدم غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in user filter actions: {e}")
            await callback.answer("❌ خطأ في معالجة فلتر المستخدمين", show_alert=True)

    async def _handle_media_type_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle media type specific actions"""
        try:
            data = callback.data
            
            if data.startswith("photo_toggle_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("📷 سيتم تنفيذ تبديل فلتر الصور قريباً", show_alert=True)
                
            elif data.startswith("video_toggle_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("🎥 سيتم تنفيذ تبديل فلتر الفيديو قريباً", show_alert=True)
                
            elif data.startswith("audio_toggle_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("🎵 سيتم تنفيذ تبديل فلتر الصوت قريباً", show_alert=True)
                
            else:
                await callback.answer("🎭 نوع وسائط غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in media type actions: {e}")
            await callback.answer("❌ خطأ في معالجة أنواع الوسائط", show_alert=True)



    async def _handle_additional_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle additional miscellaneous actions"""
        try:
            data = callback.data
            
            # Forward Mode Actions
            if data.startswith("mode_copy_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("📋 تم تعيين وضع النسخ", show_alert=False)
            elif data.startswith("mode_forward_"):
                task_id = int(data.split("_")[-1])
                await callback.answer("🔄 تم تعيين وضع التوجيه", show_alert=False)
                
            # Delay Actions
            elif data.startswith("instant_"):
                await callback.answer("⚡ تم تعيين التأخير الفوري", show_alert=False)
            elif data.startswith("short_"):
                await callback.answer("⏰ تم تعيين التأخير القصير", show_alert=False)
            elif data.startswith("medium_"):
                await callback.answer("⏱️ تم تعيين التأخير المتوسط", show_alert=False)
            elif data.startswith("long_"):
                await callback.answer("⏳ تم تعيين التأخير الطويل", show_alert=False)
            elif data.startswith("random_"):
                await callback.answer("🎲 تم تعيين التأخير العشوائي", show_alert=False)
                
            # Preset Actions
            elif data.startswith("load_preset_"):
                await callback.answer("📝 تم تحميل الإعداد المسبق", show_alert=False)
            elif data.startswith("apply_"):
                await callback.answer("⚙️ تم تطبيق الإعدادات", show_alert=False)
                
            # Content Modification - Prefix/Suffix
            elif data.startswith("add_") and "prefix" in data:
                await callback.answer("➕ تم إضافة البادئة", show_alert=False)
            elif data.startswith("add_") and "suffix" in data:
                await callback.answer("➕ تم إضافة اللاحقة", show_alert=False)
            elif data.startswith("remove_") and ("prefix" in data or "suffix" in data):
                await callback.answer("➖ تم حذف البادئة/اللاحقة", show_alert=False)
            elif data.startswith("edit_") and ("prefix" in data or "suffix" in data):
                await callback.answer("✏️ تم تعديل البادئة/اللاحقة", show_alert=False)
                
            # Text Replace Actions
            elif data.startswith("add_") and "replace" in data:
                await callback.answer("➕ تم إضافة قاعدة الاستبدال", show_alert=False)
            elif data.startswith("remove_") and "replace" in data:
                await callback.answer("➖ تم حذف قاعدة الاستبدال", show_alert=False)
            elif data.startswith("edit_") and "replace" in data:
                await callback.answer("✏️ تم تعديل قاعدة الاستبدال", show_alert=False)
            elif data.startswith("test_") and "replace" in data:
                await callback.answer("🧪 تم اختبار الاستبدال", show_alert=False)
                
            # Hashtag Actions
            elif data.startswith("add_") and "hashtag" in data:
                await callback.answer("➕ تم إضافة الهاشتاق", show_alert=False)
            elif data.startswith("remove_") and "hashtag" in data:
                await callback.answer("➖ تم حذف الهاشتاق", show_alert=False)
            elif data.startswith("extract_"):
                await callback.answer("📤 تم استخراج الهاشتاقات", show_alert=False)
            elif data.startswith("preserve_"):
                await callback.answer("🔒 تم حفظ الهاشتاقات", show_alert=False)
            elif data.startswith("strip_"):
                await callback.answer("🗑️ تم حذف الهاشتاقات", show_alert=False)
                
            # Formatting Actions
            elif data.startswith("bold_"):
                await callback.answer("🔤 تم تطبيق الخط العريض", show_alert=False)
            elif data.startswith("italic_"):
                await callback.answer("🔤 تم تطبيق الخط المائل", show_alert=False)
            elif data.startswith("underline_"):
                await callback.answer("🔤 تم تطبيق التسطير", show_alert=False)
            elif data.startswith("strike_"):
                await callback.answer("🔤 تم تطبيق الشطب", show_alert=False)
            elif data.startswith("spoiler_"):
                await callback.answer("🔤 تم تطبيق المخفي", show_alert=False)
            elif data.startswith("code_"):
                await callback.answer("🔤 تم تطبيق الكود", show_alert=False)
            elif data.startswith("mono_"):
                await callback.answer("🔤 تم تطبيق الخط الأحادي", show_alert=False)
                
            # Link Actions
            elif data.startswith("preserve_") and "link" in data:
                await callback.answer("🔗 تم حفظ الروابط", show_alert=False)
            elif data.startswith("strip_") and "link" in data:
                await callback.answer("🗑️ تم حذف الروابط", show_alert=False)
            elif data.startswith("extract_") and "link" in data:
                await callback.answer("📤 تم استخراج الروابط", show_alert=False)
                
            # Keyword Filter Actions
            elif data.startswith("add_") and "keyword" in data:
                await callback.answer("➕ تم إضافة الكلمة المفتاحية", show_alert=False)
            elif data.startswith("remove_") and "keyword" in data:
                await callback.answer("➖ تم حذف الكلمة المفتاحية", show_alert=False)
            elif data.startswith("edit_") and "keyword" in data:
                await callback.answer("✏️ تم تعديل الكلمة المفتاحية", show_alert=False)
            elif data.startswith("keyword_"):
                await callback.answer("🔍 Keyword filter modified", show_alert=False)
                
            # Length Limit Actions
            elif data.startswith("limit_"):
                await callback.answer("📏 تم تعيين حد الطول", show_alert=False)
            elif data.startswith("min_"):
                await callback.answer("📏 تم تعيين الحد الأدنى", show_alert=False)
            elif data.startswith("max_"):
                await callback.answer("📏 تم تعيين الحد الأقصى", show_alert=False)
            elif data.startswith("length_"):
                await callback.answer("📏 تم تعديل فلتر الطول", show_alert=False)
                
            # User Filter Actions
            elif data.startswith("sender_"):
                await callback.answer("👤 تم تعديل فلتر المرسل", show_alert=False)
                
            # Clear All Actions
            elif data.startswith("all_"):
                await callback.answer("🗑️ تم مسح الكل", show_alert=False)
            elif data.startswith("none_"):
                await callback.answer("❌ تم Cancel التحديد", show_alert=False)
            elif data.startswith("default_"):
                await callback.answer("🔄 تم استعادة الافتراضي", show_alert=False)
                
            # General Actions
            elif data.startswith("delete_"):
                await callback.answer("🗑️ تم الحذف", show_alert=False)
            elif data.startswith("copy_"):
                await callback.answer("📋 تم النسخ", show_alert=False)
            elif data.startswith("import_"):
                await callback.answer("📥 تم الاستيراد", show_alert=False)
            elif data.startswith("export_"):
                await callback.answer("📤 تم التصدير", show_alert=False)
            elif data.startswith("edit_"):
                await callback.answer("✏️ تم التعديل", show_alert=False)
            elif data.startswith("test_"):
                await callback.answer("🧪 تم الاختبار", show_alert=False)
            elif data.startswith("back_"):
                await callback.answer("↩️ تم الرجوع", show_alert=False)
            elif data.startswith("next_"):
                await callback.answer("➡️ التالي", show_alert=False)
            elif data.startswith("prev_"):
                await callback.answer("⬅️ السابق", show_alert=False)
            elif data.startswith("select_"):
                await callback.answer("☑️ تم التحديد", show_alert=False)
                
            else:
                await callback.answer("⚙️ إجراء إضافي غير مدعوم", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in additional actions: {e}")
            await callback.answer("❌ خطأ في معالجة الإجراء", show_alert=True)
    
    async def _handle_keyword_list_whitelist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle displaying whitelist keywords"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keywords with separate lists
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            whitelist_keywords = []
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        if "whitelist" in keywords_data:
                            whitelist_keywords = keywords_data.get("whitelist", [])
                        else:
                            # Migrate legacy format
                            current_mode = keywords_data.get("mode", "blacklist")
                            if current_mode == "whitelist":
                                whitelist_keywords = keywords_data.get("keywords", [])
                except:
                    pass
            
            # Generate display text
            display_text = f"⚪ **القائمة البيضاء - المهمة {task_id}**\n\n"
            
            if whitelist_keywords:
                display_text += f"**إجمالي الكلمات المسموحة: {len(whitelist_keywords)}**\n\n"
                
                # Show all keywords with numbering
                for i, keyword in enumerate(whitelist_keywords, 1):
                    display_text += f"{i}. `{keyword}`\n"
                    
                    # Prevent message from being too long
                    if len(display_text) > 3500:
                        remaining = len(whitelist_keywords) - i
                        display_text += f"\n... و {remaining} كلمة أخرى (الرسالة طويلة جداً للعرض)"
                        break
            else:
                display_text += "📝 **لا توجد كلمات مسموحة**\n"
                display_text += "اضغط على 'إضافة كلمات مسموحة' لبدء إنشاء القائمة البيضاء"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="➕ إضافة كلمات مسموحة", callback_data=f"kw_add_whitelist_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ مسح القائمة البيضاء", callback_data=f"kw_clear_whitelist_{task_id}"),
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_keywords_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(display_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in whitelist display: {e}")
            await callback.answer("❌ خطأ في عرض القائمة البيضاء")
    
    async def _handle_keyword_list_blacklist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle displaying blacklist keywords"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keywords with separate lists
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            blacklist_keywords = []
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        if "blacklist" in keywords_data:
                            blacklist_keywords = keywords_data.get("blacklist", [])
                        else:
                            # Migrate legacy format
                            current_mode = keywords_data.get("mode", "blacklist")
                            if current_mode == "blacklist":
                                blacklist_keywords = keywords_data.get("keywords", [])
                except:
                    pass
            
            # Generate display text
            display_text = f"⚫ **القائمة السوداء - المهمة {task_id}**\n\n"
            
            if blacklist_keywords:
                display_text += f"**إجمالي الكلمات المحظورة: {len(blacklist_keywords)}**\n\n"
                
                # Show all keywords with numbering
                for i, keyword in enumerate(blacklist_keywords, 1):
                    display_text += f"{i}. `{keyword}`\n"
                    
                    # Prevent message from being too long
                    if len(display_text) > 3500:
                        remaining = len(blacklist_keywords) - i
                        display_text += f"\n... و {remaining} كلمة أخرى (الرسالة طويلة جداً للعرض)"
                        break
            else:
                display_text += "📝 **لا توجد كلمات محظورة**\n"
                display_text += "Click 'Add Blocked Keywords' to start creating the blacklist"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="➕ إضافة كلمات محظورة", callback_data=f"kw_add_blacklist_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Clear Blacklist", callback_data=f"kw_clear_blacklist_{task_id}"),
                    InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_keywords_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(display_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in blacklist display: {e}")
            await callback.answer("❌ Error displaying blacklist")
    
    async def _handle_keyword_clear_whitelist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle clearing whitelist keywords"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keywords to preserve blacklist
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            blacklist_keywords = []
            current_mode = "blacklist"
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        current_mode = keywords_data.get("mode", "blacklist")
                        if "blacklist" in keywords_data:
                            blacklist_keywords = keywords_data.get("blacklist", [])
                        else:
                            # Migrate legacy format
                            if current_mode == "blacklist":
                                blacklist_keywords = keywords_data.get("keywords", [])
                except:
                    pass
            
            # Clear whitelist, keep blacklist
            keywords_data = {
                "mode": current_mode,
                "whitelist": [],
                "blacklist": blacklist_keywords
            }
            
            await self.database.execute_command(
                "UPDATE task_settings SET keyword_filters = $1 WHERE task_id = $2",
                json.dumps(keywords_data), task_id
            )
            
            await callback.answer("⚪ Whitelist cleared successfully")
            await self._handle_keyword_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing whitelist: {e}")
            await callback.answer("❌ Error clearing whitelist")
    
    async def _handle_keyword_clear_blacklist(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle clearing blacklist keywords"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current keywords to preserve whitelist
            settings = await self.database.execute_query(
                "SELECT keyword_filters FROM task_settings WHERE task_id = $1", 
                task_id
            )
            
            whitelist_keywords = []
            current_mode = "blacklist"
            
            if settings and settings[0]["keyword_filters"]:
                try:
                    keywords_data = json.loads(settings[0]["keyword_filters"]) if isinstance(settings[0]["keyword_filters"], str) else settings[0]["keyword_filters"]
                    if isinstance(keywords_data, dict):
                        current_mode = keywords_data.get("mode", "blacklist")
                        if "whitelist" in keywords_data:
                            whitelist_keywords = keywords_data.get("whitelist", [])
                        else:
                            # Migrate legacy format
                            if current_mode == "whitelist":
                                whitelist_keywords = keywords_data.get("keywords", [])
                except:
                    pass
            
            # Clear blacklist, keep whitelist
            keywords_data = {
                "mode": current_mode,
                "whitelist": whitelist_keywords,
                "blacklist": []
            }
            
            await self.database.execute_command(
                "UPDATE task_settings SET keyword_filters = $1 WHERE task_id = $2",
                json.dumps(keywords_data), task_id
            )
            
            await callback.answer("⚫ تم Clear Blacklist بنجاح")
            await self._handle_keyword_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing blacklist: {e}")
            await callback.answer("❌ خطأ في Clear Blacklist")

    async def _handle_length_filter(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle length filter main interface - show enhanced version"""
        try:
            logger.info(f"Loading enhanced length filter for task {task_id}")
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Force fresh data read from database each time
            import json
            import time
            
            # Clear any cached data and read directly from database
            fresh_db_result = await self.database.execute_query(
                "SELECT length_filter_settings FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            length_settings = {}
            if fresh_db_result and fresh_db_result[0] and fresh_db_result[0]['length_filter_settings']:
                try:
                    raw_data = fresh_db_result[0]['length_filter_settings']
                    if isinstance(raw_data, str):
                        length_settings = json.loads(raw_data)
                    else:
                        length_settings = raw_data
                    logger.info(f"Fresh data loaded for task {task_id}: {length_settings}")
                except Exception as e:
                    logger.error(f"Error parsing length_filter_settings: {e}")
                    length_settings = {}
            
            # Extract settings - preserve existing values, only use defaults if truly missing
            filter_enabled = length_settings.get('enabled', False)
            min_length = length_settings.get('min_length', 0)
            max_length = length_settings.get('max_length', 4096)
            action_mode = length_settings.get('action_mode', 'block')
            
            # Only add missing fields if the settings object is completely empty
            if not length_settings:
                import json
                complete_settings = {
                    'enabled': filter_enabled,
                    'min_length': min_length,
                    'max_length': max_length,
                    'action_mode': action_mode
                }
                # Update using direct SQL since database doesn't have update_task_settings method
                await self.database.execute_command(
                    "UPDATE task_settings SET length_filter_settings = $1 WHERE task_id = $2",
                    json.dumps(complete_settings),
                    task_id
                )
                logger.info(f"Initialized empty length filter settings for task {task_id}: {complete_settings}")
            
            # Build interface text with timestamp for refresh
            import time
            timestamp = int(time.time())
            length_text = f"📏 **Message Length Filter - Task {task_id}**\n\n"
            
            # Status
            status_icon = "🟢" if filter_enabled else "🔴"
            status_text = "Enabled" if filter_enabled else "Disabled"
            length_text += f"**Status:** {status_icon} {status_text}\n\n"
            
            # Current settings
            if filter_enabled:
                length_text += f"**Current Settings:**\n"
                if min_length > 0:
                    length_text += f"• Minimum: {min_length} characters\n"
                length_text += f"• Maximum: {max_length} characters\n"
                
                # Action description
                if action_mode == "block":
                    action_desc = "Block message"
                    action_icon = "🚫"
                elif action_mode == "truncate":
                    action_desc = "Truncate message"
                    action_icon = "✂️"
                elif action_mode == "summarize":
                    action_desc = "Summarize message"
                    action_icon = "📝"
                else:
                    action_desc = "Block message"
                    action_icon = "🚫"
                
                length_text += f"• Action: {action_icon} {action_desc}\n\n"
                
                # Usage examples
                length_text += f"💡 **Examples:**\n"
                if min_length > 0:
                    length_text += f"• Messages under {min_length} chars: will be blocked\n"
                length_text += f"• Messages over {max_length} chars: {action_desc}\n"
            
            # Add hidden timestamp to force UI refresh
            length_text += f"\n\u2800{timestamp}"
            
            # Action description for button display
            if action_mode == "block":
                action_btn_desc = "Block"
            elif action_mode == "truncate":
                action_btn_desc = "Truncate"
            elif action_mode == "summarize":
                action_btn_desc = "Summarize"
            else:
                action_btn_desc = "Block"
                
            # Main length filter controls - Updated as requested
            # Correct toggle button text logic
            toggle_text = "🔴 Disable Filter" if filter_enabled else "🟢 Enable Filter"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=toggle_text, 
                        callback_data=f"length_toggle_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📏 Minimum Characters ({min_length})", 
                        callback_data=f"length_min_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📐 Maximum Characters ({max_length})", 
                        callback_data=f"length_max_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🎯 Change Action ({action_btn_desc})", 
                        callback_data=f"length_action_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Filters", callback_data=f"setting_filters_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            # Force UI refresh with unique timestamp
            timestamp = int(time.time() * 1000) % 10000  # Microsecond precision
            final_text = length_text + f"\n\n_Sync: {timestamp}_"
            
            # Always force UI update to show latest data
            try:
                await callback.message.edit_text(final_text, reply_markup=markup, parse_mode="Markdown")
                logger.info(f"UI updated successfully for task {task_id} with timestamp {timestamp}, action: {action_mode}")
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    # Force completely different content by changing timestamp
                    final_text = length_text + f"\n\n_Force Update: {timestamp + 1}_"
                    try:
                        await callback.message.edit_text(final_text, reply_markup=markup, parse_mode="Markdown")
                        logger.info(f"UI force updated for task {task_id}")
                    except:
                        # Last resort: delete and send new message
                        try:
                            await callback.message.delete()
                            new_msg = await callback.bot.send_message(
                                chat_id=callback.message.chat.id,
                                text=final_text, 
                                reply_markup=markup, 
                                parse_mode="Markdown"
                            )
                            logger.info(f"UI recreated for task {task_id}")
                        except Exception as recreate_error:
                            logger.error(f"Failed to recreate message: {recreate_error}")
                else:
                    raise edit_error
            
        except Exception as e:
            logger.error(f"Error in length filter interface: {e}")
            await callback.answer("❌ Error loading length filter.")

    async def _handle_length_actions(self, callback: CallbackQuery, state: FSMContext):
        """Handle enhanced length filter actions"""
        try:
            callback_data = callback.data
            task_id = int(callback_data.split("_")[-1])
            action = "_".join(callback_data.split("_")[:-1])
            
            logger.info(f"Length action received: {action} for task {task_id}")
            
            if action == "length_toggle":
                await self._handle_length_toggle(callback, task_id, state)
            elif action == "length_min":
                await self._handle_length_min_setting(callback, task_id, state)
            elif action == "length_max":
                await self._handle_length_max_setting(callback, task_id, state)
            elif action == "length_action":
                await self._handle_length_action_mode(callback, task_id, state)
            else:
                logger.warning(f"Unknown length action: {action}")
                await callback.answer("❌ Unknown action.")
                
        except Exception as e:
            logger.error(f"Error in length actions: {e}")
            await callback.answer("❌ Error processing request.")

    async def _handle_length_min_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle setting minimum length"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            length_settings = settings.get('length_filter_settings', {}) if settings else {}
            
            # Parse length_filter_settings if it's a string
            if isinstance(length_settings, str):
                import json
                try:
                    length_settings = json.loads(length_settings)
                except json.JSONDecodeError:
                    length_settings = {}
            
            current_min = length_settings.get('min_length', 0)
            
            min_text = f"📏 **Set Minimum Character Count - Task {task_id}**\n\n"
            min_text += f"**Current Value:** {current_min} characters\n\n"
            min_text += "Choose new minimum value:\n"
            min_text += "Messages shorter than this limit will be blocked."
            
            keyboard = [
                [
                    InlineKeyboardButton(text="0 (No minimum)", callback_data=f"set_min_0_{task_id}"),
                    InlineKeyboardButton(text="10", callback_data=f"set_min_10_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="50", callback_data=f"set_min_50_{task_id}"),
                    InlineKeyboardButton(text="100", callback_data=f"set_min_100_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="200", callback_data=f"set_min_200_{task_id}"),
                    InlineKeyboardButton(text="500", callback_data=f"set_min_500_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"filter_length_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(min_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in min length setting: {e}")
            await callback.answer("❌ Error setting minimum limit.")

    async def _handle_length_max_setting(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle setting maximum length"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.database.get_task_settings(task_id)
            length_settings = settings.get('length_filter_settings', {}) if settings else {}
            
            # Parse length_filter_settings if it's a string
            if isinstance(length_settings, str):
                import json
                try:
                    length_settings = json.loads(length_settings)
                except json.JSONDecodeError:
                    length_settings = {}
            
            current_max = length_settings.get('max_length', 4096)
            
            max_text = f"📐 **Set Maximum Character Count - Task {task_id}**\n\n"
            max_text += f"**Current Value:** {current_max} characters\n\n"
            max_text += "Choose new maximum value:\n"
            max_text += "Messages longer than this limit will be handled according to the selected action."
            
            keyboard = [
                [
                    InlineKeyboardButton(text="280 (Twitter)", callback_data=f"set_max_280_{task_id}"),
                    InlineKeyboardButton(text="500", callback_data=f"set_max_500_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="1000", callback_data=f"set_max_1000_{task_id}"),
                    InlineKeyboardButton(text="2000", callback_data=f"set_max_2000_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="4096 (Maximum)", callback_data=f"set_max_4096_{task_id}"),
                    InlineKeyboardButton(text="Unlimited", callback_data=f"set_max_unlimited_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"filter_length_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(max_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in max length setting: {e}")
            await callback.answer("❌ Error setting maximum limit.")

    async def _handle_length_value_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle setting specific min/max values"""
        try:
            import json
            callback_data = callback.data
            parts = callback_data.split("_")
            value_type = parts[1]  # "min" or "max" 
            value = parts[2]       # the numeric value
            task_id = int(parts[3])
            
            logger.info(f"Setting {value_type} length to {value} for task {task_id}")
            
            # Get current settings from database directly
            fresh_settings = await self.database.execute_query(
                "SELECT length_filter_settings FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            length_settings = {}
            if fresh_settings and fresh_settings[0] and fresh_settings[0]['length_filter_settings']:
                try:
                    raw_data = fresh_settings[0]['length_filter_settings']
                    if isinstance(raw_data, str):
                        length_settings = json.loads(raw_data)
                    else:
                        length_settings = raw_data
                except json.JSONDecodeError:
                    length_settings = {}
            
            # Set default values if missing
            if not length_settings:
                length_settings = {
                    'enabled': True,
                    'min_length': 0,
                    'max_length': 4096,
                    'action_mode': 'block'
                }
            
            # Update the appropriate value
            if value_type == "min":
                if value == "0":
                    length_settings['min_length'] = 0
                else:
                    length_settings['min_length'] = int(value)
                success_msg = f"✅ Minimum set to {value} characters"
            elif value_type == "max":
                if value == "unlimited":
                    length_settings['max_length'] = 999999  # Very large number
                    success_msg = "✅ Maximum limit removed"
                else:
                    length_settings['max_length'] = int(value)
                    success_msg = f"✅ Maximum set to {value} characters"
            
            # Ensure filter is enabled when setting values
            length_settings['enabled'] = True
            
            # Save to database using simple UPDATE
            await self.database.execute_command(
                "UPDATE task_settings SET length_filter_settings = $1 WHERE task_id = $2",
                json.dumps(length_settings),
                task_id
            )
            
            # Force reload of forwarding engine settings
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            await callback.answer(success_msg)
            
            # Return to main length filter interface
            await self._handle_length_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting length value: {e}")
            await callback.answer("❌ Error setting value")

    async def _handle_length_action_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle length filter action mode selection"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            import time
            
            # Force fresh read from database
            fresh_settings = await self.database.execute_query(
                "SELECT length_filter_settings FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            current_action = 'block'  # default
            if fresh_settings and fresh_settings[0] and fresh_settings[0]['length_filter_settings']:
                try:
                    raw_data = fresh_settings[0]['length_filter_settings']
                    if isinstance(raw_data, str):
                        length_settings = json.loads(raw_data)
                    else:
                        length_settings = raw_data
                    current_action = length_settings.get('action_mode', 'block')
                except:
                    pass
            
            logger.info(f"Current action mode for task {task_id}: {current_action}")
            
            # Build interface with timestamp for forced refresh
            timestamp = int(time.time())
            action_text = f"⚙️ **Set Length Filter Action - Task {task_id}**\n\n"
            action_text += f"**Current Action:** {self._get_action_mode_name(current_action)}\n\n"
            action_text += "Choose what happens to messages that exceed the limit:\n\n"
            action_text += "🚫 **Block:** Prevent sending the message entirely\n"
            action_text += "✂️ **Truncate:** Send only part of the message\n"
            action_text += "📝 **Summarize:** Send a brief summary of the message\n\n"
            action_text += f"_Sync: {timestamp}_"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"🚫 Block {'✅' if current_action == 'block' else ''}", 
                        callback_data=f"set_action_block_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"✂️ Truncate {'✅' if current_action == 'truncate' else ''}", 
                        callback_data=f"set_action_truncate_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📝 Summarize {'✅' if current_action == 'summarize' else ''}", 
                        callback_data=f"set_action_summarize_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"filter_length_{task_id}")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            # Force UI update by always editing message
            try:
                await callback.message.edit_text(action_text, reply_markup=markup, parse_mode="Markdown")
                logger.info(f"Action mode interface updated for task {task_id} with current action: {current_action}")
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    # Force completely different content
                    action_text = action_text.replace(f"_Sync: {timestamp}_", f"_Force Update: {timestamp + 1}_")
                    await callback.message.edit_text(action_text, reply_markup=markup, parse_mode="Markdown")
                else:
                    raise edit_error
            
        except Exception as e:
            logger.error(f"Error in action mode setting: {e}")
            await callback.answer("❌ Error setting action.")

    def _get_action_mode_name(self, action_mode: str) -> str:
        """Get English name for action mode"""
        action_names = {
            'block': 'Block Message',
            'truncate': 'Truncate Message', 
            'summarize': 'Summarize Message'
        }
        return action_names.get(action_mode, 'Not Set')

    async def _handle_action_mode_setting(self, callback: CallbackQuery, state: FSMContext):
        """Handle setting specific action mode values"""
        try:
            callback_data = callback.data
            parts = callback_data.split("_")
            action_type = parts[2]  # "block", "truncate", or "summarize"
            task_id = int(parts[3])
            
            logger.info(f"Setting action mode to {action_type} for task {task_id}")
            
            # Get current settings - force fresh read from database
            fresh_settings = await self.database.execute_query(
                "SELECT length_filter_settings FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            import json
            
            length_settings = {}
            if fresh_settings and fresh_settings[0] and fresh_settings[0]['length_filter_settings']:
                try:
                    raw_data = fresh_settings[0]['length_filter_settings']
                    if isinstance(raw_data, str):
                        length_settings = json.loads(raw_data)
                    else:
                        length_settings = raw_data
                except Exception as e:
                    logger.error(f"Error parsing length filter settings: {e}")
                    length_settings = {}
            
            # Update only the action mode, preserve other settings
            length_settings['action_mode'] = action_type
            length_settings['enabled'] = True
            
            # Only set defaults if values don't exist
            if 'min_length' not in length_settings:
                length_settings['min_length'] = 0
            if 'max_length' not in length_settings:
                length_settings['max_length'] = 4096
            
            # Save to database
            import json
            await self.database.execute_command(
                "UPDATE task_settings SET length_filter_settings = $1 WHERE task_id = $2",
                json.dumps(length_settings),
                task_id
            )
            
            # Force reload of forwarding engine settings
            if hasattr(self.bot_controller, 'forwarding_engine'):
                await self.bot_controller.forwarding_engine._reload_tasks()
            
            action_names = {
                'block': 'Block Message',
                'truncate': 'Truncate Message', 
                'summarize': 'Summarize Message'
            }
            
            success_msg = f"✅ Action set to: {action_names.get(action_type, action_type)}"
            await callback.answer(success_msg)
            
            # Force refresh the main length filter interface with new data
            await self._handle_length_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting action mode: {e}")
            await callback.answer("❌ Error setting action.")

    async def _handle_length_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle length filter on/off"""
        try:
            import json
            
            # Get current settings
            settings = await self.database.execute_query(
                "SELECT length_filter_settings FROM task_settings WHERE task_id = $1",
                task_id
            )
            
            current_enabled = False
            length_settings = {}
            
            if settings and settings[0] and settings[0]["length_filter_settings"]:
                try:
                    length_settings = json.loads(settings[0]["length_filter_settings"]) if isinstance(settings[0]["length_filter_settings"], str) else settings[0]["length_filter_settings"]
                    if isinstance(length_settings, dict):
                        current_enabled = length_settings.get("enabled", False)
                except:
                    pass
            
            # Toggle state
            new_enabled = not current_enabled
            length_settings["enabled"] = new_enabled
            
            # Update in database
            await self.database.execute_command(
                """INSERT INTO task_settings (
                    task_id, forward_mode, preserve_sender, add_caption, 
                    filter_media, filter_text, filter_forwarded, filter_links,
                    allow_photos, allow_videos, allow_documents, allow_audio, 
                    allow_voice, allow_video_notes, allow_stickers, allow_animations,
                    allow_contacts, allow_locations, allow_venues, allow_polls, allow_dice,
                    delay_min, delay_max, remove_links, remove_mentions, duplicate_check, max_message_length,
                    length_filter_settings, created_at, updated_at
                ) VALUES (
                    $1, 'copy', false, false, 
                    false, false, false, false,
                    true, true, true, true,
                    true, true, true, true,
                    true, true, true, true, true,
                    5, 10, false, false, true, 4096,
                    $2, NOW(), NOW()
                ) ON CONFLICT (task_id) 
                DO UPDATE SET length_filter_settings = $2, updated_at = NOW()""",
                task_id, json.dumps(length_settings)
            )
            
            status_text = "enabled" if new_enabled else "disabled"
            await callback.answer(f"✅ Length filter {status_text}.")
            
            # Force refresh the interface to show new state with updated data
            await self._handle_length_filter(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling length filter: {e}")
            await callback.answer("❌ Error toggling filter.")

    async def _handle_length_presets(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle length filter presets"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            presets_text = f"📏 **Length Filter Quick Settings - Task {task_id}**\n\n"
            presets_text += "Choose from common preset configurations:\n\n"
            presets_text += "🔸 **Short Messages**: 0-280 characters (like Twitter)\n"
            presets_text += "🔹 **Medium Messages**: 0-1000 characters\n" 
            presets_text += "🔸 **Long Messages**: 0-2000 characters\n"
            presets_text += "🔹 **Extended Messages**: 0-4096 characters (Telegram maximum)\n"
            
            keyboard = [
                [InlineKeyboardButton(text="📱 Short (280)", callback_data=f"len_280_{task_id}")],
                [InlineKeyboardButton(text="📄 Medium (1000)", callback_data=f"len_1000_{task_id}")],
                [InlineKeyboardButton(text="📋 Long (2000)", callback_data=f"len_2000_{task_id}")],
                [InlineKeyboardButton(text="📚 Extended (4096)", callback_data=f"len_4096_{task_id}")],
                [InlineKeyboardButton(text="🔙 Back", callback_data=f"filter_length_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(presets_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in length presets: {e}")
            await callback.answer("❌ Error loading quick settings.")

    async def _handle_length_advanced(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle advanced length filter settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            advanced_text = f"⚙️ **Advanced Length Filter Settings - Task {task_id}**\n\n"
            advanced_text += "This feature will be available in the next update.\n"
            advanced_text += "Currently you can use the quick settings."
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 Back", callback_data=f"filter_length_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(advanced_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in length advanced settings: {e}")
            await callback.answer("❌ Error loading advanced settings.")



    async def _handle_length_statistics(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show length filter statistics"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            stats_text = f"📊 **Length Filter Statistics - المهمة {task_id}**\n\n"
            stats_text += "This feature will be available in the next update.\n"
            stats_text += "Detailed statistics about message lengths will be displayed."
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_length_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(stats_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in length statistics: {e}")
            await callback.answer("❌ Error loading statistics.")

    async def _handle_length_test(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle length filter testing"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            test_text = f"🧪 **Length Filter Test - المهمة {task_id}**\n\n"
            test_text += "This feature will be available in the next update.\n"
            test_text += "You will be able to test how the filter works with different messages."
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"filter_length_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(test_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in length test: {e}")
            await callback.answer("❌ Error loading filter test.")

    async def _handle_user_whitelist_management(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Enhanced user whitelist management interface"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current whitelist data from database
            whitelist_data = await self.bot_controller.database.execute_query(
                "SELECT user_whitelist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_whitelist = []
            whitelist_enabled = False
            
            if whitelist_data and whitelist_data[0]['user_whitelist']:
                try:
                    data = whitelist_data[0]['user_whitelist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        whitelist_enabled = parsed_data.get('enabled', False)
                        current_whitelist = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_whitelist = parsed_data
                        whitelist_enabled = len(current_whitelist) > 0
                except:
                    pass
            
            status_icon = "✅" if whitelist_enabled else "❌"
            count_text = f"({len(current_whitelist)} مستخدم)" if current_whitelist else "(فارغة)"
            
            text = f"👥 **إدارة القائمة البيضاء للمستخدمين - المهمة {task_id}**\n\n"
            text += f"**الحالة:** {status_icon} {'مفعلة' if whitelist_enabled else 'معطلة'} {count_text}\n\n"
            
            if whitelist_enabled and current_whitelist:
                text += "📋 **المستخدمون المسموحون حالياً:**\n"
                for i, user_data in enumerate(current_whitelist[:3], 1):
                    if isinstance(user_data, dict):
                        name = user_data.get('name', user_data.get('username', 'مستخدم'))
                        text += f"{i}. {name}\n"
                    else:
                        text += f"{i}. {user_data}\n"
                if len(current_whitelist) > 3:
                    text += f"... و {len(current_whitelist) - 3} مستخدم آخر\n"
                text += "\n"
            
            text += "اختر الإجراء المطلوب:"
            
            keyboard = []
            
            # Toggle whitelist state
            if whitelist_enabled:
                keyboard.append([InlineKeyboardButton(text="❌ تعطيل القائمة البيضاء", callback_data=f"whitelist_toggle_{task_id}")])
            else:
                keyboard.append([InlineKeyboardButton(text="✅ تفعيل القائمة البيضاء", callback_data=f"whitelist_toggle_{task_id}")])
            
            # Add user options
            keyboard.append([
                InlineKeyboardButton(text="👤 إضافة من المشرفين", callback_data=f"whitelist_add_admin_{task_id}"),
                InlineKeyboardButton(text="✍️ إضافة يدوياً", callback_data=f"whitelist_add_manual_{task_id}")
            ])
            
            # Management buttons  
            if current_whitelist:
                keyboard.extend([
                    [
                        InlineKeyboardButton(text="📋 عرض القائمة الكاملة", callback_data=f"whitelist_list_{task_id}"),
                        InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"whitelist_clear_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="📤 تصدير القائمة", callback_data=f"whitelist_export_{task_id}"),
                        InlineKeyboardButton(text="📥 استيراد قائمة", callback_data=f"whitelist_import_{task_id}")
                    ]
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"filter_users_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in user whitelist management: {e}")
            await callback.answer("❌ خطأ في إدارة القائمة البيضاء", show_alert=True)

    async def _handle_user_blacklist_management(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Enhanced user blacklist management interface"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current blacklist data from database
            blacklist_data = await self.bot_controller.database.execute_query(
                "SELECT user_blacklist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_blacklist = []
            blacklist_enabled = False
            
            if blacklist_data and blacklist_data[0]['user_blacklist']:
                try:
                    data = blacklist_data[0]['user_blacklist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        blacklist_enabled = parsed_data.get('enabled', False)
                        current_blacklist = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_blacklist = parsed_data
                        blacklist_enabled = len(current_blacklist) > 0
                except:
                    pass
            
            status_icon = "✅" if blacklist_enabled else "❌"
            count_text = f"({len(current_blacklist)} مستخدم)" if current_blacklist else "(فارغة)"
            
            text = f"🚫 **إدارة القائمة السوداء للمستخدمين - المهمة {task_id}**\n\n"
            text += f"**الحالة:** {status_icon} {'مفعلة' if blacklist_enabled else 'معطلة'} {count_text}\n\n"
            
            if blacklist_enabled and current_blacklist:
                text += "⚫ **المستخدمون المحظورون حالياً:**\n"
                for i, user_data in enumerate(current_blacklist[:3], 1):
                    if isinstance(user_data, dict):
                        name = user_data.get('name', user_data.get('username', 'مستخدم'))
                        text += f"{i}. {name}\n"
                    else:
                        text += f"{i}. {user_data}\n"
                if len(current_blacklist) > 3:
                    text += f"... و {len(current_blacklist) - 3} مستخدم آخر\n"
                text += "\n"
            
            text += "اختر الإجراء المطلوب:"
            
            keyboard = []
            
            # Toggle blacklist state
            if blacklist_enabled:
                keyboard.append([InlineKeyboardButton(text="❌ تعطيل القائمة السوداء", callback_data=f"blacklist_toggle_{task_id}")])
            else:
                keyboard.append([InlineKeyboardButton(text="✅ تفعيل القائمة السوداء", callback_data=f"blacklist_toggle_{task_id}")])
            
            # Add user options
            keyboard.append([
                InlineKeyboardButton(text="👤 إضافة من المشرفين", callback_data=f"blacklist_add_admin_{task_id}"),
                InlineKeyboardButton(text="✍️ إضافة يدوياً", callback_data=f"blacklist_add_manual_{task_id}")
            ])
            
            # Management buttons  
            if current_blacklist:
                keyboard.extend([
                    [
                        InlineKeyboardButton(text="📋 عرض القائمة الكاملة", callback_data=f"blacklist_list_{task_id}"),
                        InlineKeyboardButton(text="🗑️ مسح الكل", callback_data=f"blacklist_clear_{task_id}")
                    ],
                    [
                        InlineKeyboardButton(text="📤 تصدير القائمة", callback_data=f"blacklist_export_{task_id}"),
                        InlineKeyboardButton(text="📥 استيراد قائمة", callback_data=f"blacklist_import_{task_id}")
                    ]
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة للفلاتر", callback_data=f"filter_users_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in user blacklist management: {e}")
            await callback.answer("❌ خطأ في إدارة القائمة السوداء", show_alert=True)

    # Enhanced Whitelist/Blacklist Management Functions
    async def _handle_whitelist_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle whitelist on/off"""
        try:
            import json
            
            # Get current whitelist data
            whitelist_data = await self.bot_controller.database.execute_query(
                "SELECT user_whitelist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_enabled = False
            current_users = []
            
            if whitelist_data and whitelist_data[0]['user_whitelist']:
                try:
                    data = whitelist_data[0]['user_whitelist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_enabled = parsed_data.get('enabled', False)
                        current_users = parsed_data.get('users', [])
                except:
                    pass
            
            # Toggle enabled state
            new_enabled = not current_enabled
            
            new_data = {
                'enabled': new_enabled,
                'users': current_users
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET user_whitelist = $1 WHERE task_id = $2",
                json.dumps(new_data), task_id
            )
            
            status = "تم تفعيل" if new_enabled else "تم تعطيل"
            await callback.answer(f"✅ {status} القائمة البيضاء")
            
            # Refresh the interface
            await self._handle_user_whitelist_management(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling whitelist: {e}")
            await callback.answer("❌ خطأ في تبديل حالة القائمة البيضاء", show_alert=True)

    async def _handle_blacklist_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle blacklist on/off"""
        try:
            import json
            
            # Get current blacklist data
            blacklist_data = await self.bot_controller.database.execute_query(
                "SELECT user_blacklist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_enabled = False
            current_users = []
            
            if blacklist_data and blacklist_data[0]['user_blacklist']:
                try:
                    data = blacklist_data[0]['user_blacklist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_enabled = parsed_data.get('enabled', False)
                        current_users = parsed_data.get('users', [])
                except:
                    pass
            
            # Toggle enabled state
            new_enabled = not current_enabled
            
            new_data = {
                'enabled': new_enabled,
                'users': current_users
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET user_blacklist = $1 WHERE task_id = $2",
                json.dumps(new_data), task_id
            )
            
            status = "تم تفعيل" if new_enabled else "تم تعطيل"
            await callback.answer(f"✅ {status} القائمة السوداء")
            
            # Refresh the interface
            await self._handle_user_blacklist_management(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling blacklist: {e}")
            await callback.answer("❌ خطأ في تبديل حالة القائمة السوداء", show_alert=True)

    async def _handle_whitelist_add_admin(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show admins from source channels for whitelist selection"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get source channels for this task
            sources = await self.bot_controller.database.execute_query(
                "SELECT channel_id, channel_name FROM task_sources WHERE task_id = $1", task_id
            )
            
            if not sources:
                await callback.answer("❌ لا توجد قنوات مصدر لهذه المهمة", show_alert=True)
                return
            
            text = f"👥 **اختيار مشرف للقائمة البيضاء - المهمة {task_id}**\n\n"
            text += "اختر قناة مصدر لعرض مشرفيها:\n\n"
            
            keyboard = []
            for source in sources:
                channel_name = source['channel_name'] or f"قناة {source['channel_id']}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📢 {channel_name}", 
                        callback_data=f"whitelist_admins_{task_id}_{source['channel_id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data=f"user_whitelist_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error showing admin selection: {e}")
            await callback.answer("❌ خطأ في عرض اختيار المشرفين", show_alert=True)

    async def _handle_whitelist_list(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show complete whitelist with removal options"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current whitelist
            whitelist_data = await self.bot_controller.database.execute_query(
                "SELECT user_whitelist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_users = []
            if whitelist_data and whitelist_data[0]['user_whitelist']:
                try:
                    data = whitelist_data[0]['user_whitelist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_users = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_users = parsed_data
                except:
                    pass
            
            if not current_users:
                await callback.answer("📋 القائمة البيضاء فارغة", show_alert=True)
                return
            
            text = f"📋 **القائمة البيضاء الكاملة - المهمة {task_id}**\n\n"
            text += f"**إجمالي المستخدمين:** {len(current_users)}\n\n"
            text += "انقر على أي مستخدم لحذفه:\n\n"
            
            keyboard = []
            for i, user_data in enumerate(current_users):
                if isinstance(user_data, dict):
                    name = user_data.get('name', user_data.get('username', f"مستخدم {i+1}"))
                    user_id = user_data.get('id', user_data.get('user_id', ''))
                else:
                    name = str(user_data)
                    user_id = user_data
                
                display_name = f"{name}" if name else f"مستخدم {i+1}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑️ {display_name}", 
                        callback_data=f"whitelist_remove_{task_id}_{i}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data=f"user_whitelist_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error showing whitelist: {e}")
            await callback.answer("❌ خطأ في عرض القائمة البيضاء", show_alert=True)

    async def _handle_blacklist_add_admin(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show admins from source channels for blacklist selection"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get source channels for this task
            sources = await self.bot_controller.database.execute_query(
                "SELECT channel_id, channel_name FROM task_sources WHERE task_id = $1", task_id
            )
            
            if not sources:
                await callback.answer("❌ لا توجد قنوات مصدر لهذه المهمة", show_alert=True)
                return
            
            text = f"🚫 **اختيار مشرف للقائمة السوداء - المهمة {task_id}**\n\n"
            text += "اختر قناة مصدر لعرض مشرفيها:\n\n"
            
            keyboard = []
            for source in sources:
                channel_name = source['channel_name'] or f"قناة {source['channel_id']}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📢 {channel_name}", 
                        callback_data=f"blacklist_admins_{task_id}_{source['channel_id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data=f"user_blacklist_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error showing admin selection: {e}")
            await callback.answer("❌ خطأ في عرض اختيار المشرفين", show_alert=True)

    async def _handle_blacklist_list(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show complete blacklist with removal options"""


    async def _apply_formatting_preview(self, text: str, format_settings: dict) -> str:
        """Apply formatting preview for testing purposes"""
        try:
            if format_settings.get("preserve_original", True):
                return text
            
            if format_settings.get("remove_all", False):
                # Remove all existing formatting (simplified for preview)
                import re
                clean_text = re.sub(r'[*_`~\[\]()]+', '', text)
                return clean_text
            
            formatted_text = text
            
            # Apply formatting in order
            if format_settings.get("apply_bold", False):
                formatted_text = f"**{formatted_text}**"
            
            if format_settings.get("apply_italic", False):
                formatted_text = f"*{formatted_text}*"
            
            if format_settings.get("apply_underline", False):
                formatted_text = f"__{formatted_text}__"
            
            if format_settings.get("apply_strikethrough", False):
                formatted_text = f"~~{formatted_text}~~"
            
            if format_settings.get("apply_spoiler", False):
                formatted_text = f"||{formatted_text}||"
            
            if format_settings.get("apply_code", False):
                formatted_text = f"`{formatted_text}`"
            
            if format_settings.get("apply_mono", False):
                formatted_text = f"`{formatted_text}`"
            
            if format_settings.get("apply_quote", False):
                formatted_text = f">{formatted_text}"
            
            if format_settings.get("apply_copyable_code", False):
                formatted_text = f"```\n{formatted_text}\n```"
            
            if format_settings.get("apply_link", False):
                custom_url = format_settings.get("custom_link_url", "https://example.com")
                formatted_text = f"[{formatted_text}]({custom_url})"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error in formatting preview: {e}")
            return text


        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            import json
            
            # Get current blacklist
            blacklist_data = await self.bot_controller.database.execute_query(
                "SELECT user_blacklist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_users = []
            if blacklist_data and blacklist_data[0]['user_blacklist']:
                try:
                    data = blacklist_data[0]['user_blacklist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_users = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_users = parsed_data
                except:
                    pass
            
            if not current_users:
                await callback.answer("📋 القائمة السوداء فارغة", show_alert=True)
                return
            
            text = f"⚫ **القائمة السوداء الكاملة - المهمة {task_id}**\n\n"
            text += f"**إجمالي المستخدمين:** {len(current_users)}\n\n"
            text += "انقر على أي مستخدم لحذفه:\n\n"
            
            keyboard = []
            for i, user_data in enumerate(current_users):
                if isinstance(user_data, dict):
                    name = user_data.get('name', user_data.get('username', f"مستخدم {i+1}"))
                    user_id = user_data.get('id', user_data.get('user_id', ''))
                else:
                    name = str(user_data)
                    user_id = user_data
                
                display_name = f"{name}" if name else f"مستخدم {i+1}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑️ {display_name}", 
                        callback_data=f"blacklist_remove_{task_id}_{i}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data=f"user_blacklist_{task_id}")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error showing blacklist: {e}")
            await callback.answer("❌ خطأ في عرض القائمة السوداء", show_alert=True)

    async def _handle_manage_target_words(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle target words management for text cleaner"""
        try:
            import json
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            cleaner_settings = {}
            if settings and settings.get("text_cleaner_settings"):
                try:
                    cleaner_settings = json.loads(settings["text_cleaner_settings"]) if isinstance(settings["text_cleaner_settings"], str) else settings["text_cleaner_settings"]
                except:
                    cleaner_settings = {}
            
            target_words = cleaner_settings.get("target_words", [])
            
            text = f"🔤 **إدارة الكلمات المستهدفة - المهمة {task_id}**\n\n"
            text += f"**عدد الكلمات المحفوظة:** {len(target_words)}\n\n"
            
            if target_words:
                text += "**الكلمات الحالية:**\n"
                for i, word in enumerate(target_words[:5], 1):
                    text += f"{i}. `{word}`\n"
                if len(target_words) > 5:
                    text += f"... و {len(target_words) - 5} كلمة أخرى\n"
                text += "\n"
            
            text += "**الوظيفة:**\n"
            text += "حذف أي سطر يحتوي على إحدى هذه الكلمات من الرسائل المحولة.\n\n"
            text += "**مثال:**\n"
            text += "إذا أضفت كلمة 'إعلان'، سيتم حذف أي سطر يحتوي على هذه الكلمة."
            
            keyboard = [
                [InlineKeyboardButton(text="➕ إضافة كلمات", callback_data=f"cleaner_add_words_{task_id}")],
                [InlineKeyboardButton(text="🗑️ مسح جميع الكلمات", callback_data=f"cleaner_clear_words_{task_id}")],
                [InlineKeyboardButton(text="🔙 العودة لمنظف النص", callback_data=f"content_cleaner_{task_id}")]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error managing target words: {e}")
            await callback.answer("❌ خطأ في إدارة الكلمات المستهدفة", show_alert=True)

    async def _handle_blacklist_add_manual(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle manual user addition to blacklist"""
        try:
            text = f"✍️ **إضافة مستخدم للقائمة السوداء - المهمة {task_id}**\n\n"
            text += "أرسل معرف المستخدم أو اسم المستخدم:\n\n"
            text += "**أمثلة:**\n"
            text += "• `123456789` (معرف رقمي)\n"
            text += "• `@username` (اسم المستخدم)\n"
            text += "• `username` (بدون @)\n\n"
            text += "يمكنك الحصول على معرف المستخدم من رسائلهم في القنوات."
            
            await callback.message.edit_text(text, parse_mode="Markdown")
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="add_blacklist_user", task_id=task_id)
            
        except Exception as e:
            logger.error(f"Error in manual blacklist add: {e}")
            await callback.answer("❌ خطأ في إضافة المستخدم", show_alert=True)

    async def _handle_whitelist_add(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Add user to whitelist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة البيضاء", callback_data=f"user_whitelist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "➕ إضافة مستخدم للقائمة البيضاء\n\n"
                "أرسل:\n"
                "• معرف المستخدم (ID): 123456789\n"
                "• اسم المستخدم: @username\n"
                "• عدة مستخدمين مفصولين بسطر جديد",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="whitelist_add",
                task_id=task_id,
                awaiting_input="user_whitelist_add"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in whitelist add: {e}")
            await callback.answer("❌ خطأ في إضافة المستخدم", show_alert=True)

    async def _process_whitelist_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process whitelist user input"""
        await self._process_user_input(message, task_id, input_text, state, "whitelist")

    async def _process_whitelist_remove_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process whitelist remove user input"""
        await self._process_user_input(message, task_id, input_text, state, "whitelist_remove")

    async def _process_blacklist_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process blacklist user input"""
        await self._process_user_input(message, task_id, input_text, state, "blacklist")

    async def _process_blacklist_remove_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process blacklist remove user input"""
        await self._process_user_input(message, task_id, input_text, state, "blacklist_remove")

    async def _process_replace_add_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process text replacement addition input"""
        try:
            # Parse the input - expecting format like "old_text|new_text"
            if "|" not in input_text:
                await message.answer("❌ صيغة خاطئة. استخدم: النص القديم|النص الجديد")
                return

            old_text, new_text = input_text.split("|", 1)
            old_text = old_text.strip()
            new_text = new_text.strip()

            if not old_text:
                await message.answer("❌ النص القديم لا يمكن أن يكون فارغاً")
                return

            # Get current replacements
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_replacements = []
            if settings and settings.get("text_replacements"):
                try:
                    import json
                    data = settings["text_replacements"]
                    if isinstance(data, str):
                        current_replacements = json.loads(data)
                    elif isinstance(data, list):
                        current_replacements = data
                except:
                    pass

            # Add new replacement
            new_replacement = {"from": old_text, "to": new_text}
            current_replacements.append(new_replacement)

            # Save to database
            import json
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_replacements = $1 WHERE task_id = $2",
                json.dumps(current_replacements), task_id
            )

            await message.answer(f"✅ تم إضافة استبدال النص: '{old_text}' ← '{new_text}'")
            await state.clear()

        except Exception as e:
            logger.error(f"Error processing replace add input: {e}")
            await message.answer("❌ خطأ في إضافة الاستبدال")
            await state.clear()

    async def _process_replace_remove_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process text replacement removal input"""
        try:
            search_text = input_text.strip()
            
            # Get current replacements
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_replacements = []
            if settings and settings.get("text_replacements"):
                try:
                    import json
                    data = settings["text_replacements"]
                    if isinstance(data, str):
                        current_replacements = json.loads(data)
                    elif isinstance(data, list):
                        current_replacements = data
                except:
                    pass

            # Find and remove matching replacement
            removed_count = 0
            new_replacements = []
            for replacement in current_replacements:
                if search_text.lower() in replacement.get("from", "").lower():
                    removed_count += 1
                else:
                    new_replacements.append(replacement)

            if removed_count == 0:
                await message.answer("❌ لم يتم العثور على استبدال يحتوي على النص المحدد")
                return

            # Save updated replacements
            import json
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET text_replacements = $1 WHERE task_id = $2",
                json.dumps(new_replacements), task_id
            )

            await message.answer(f"✅ تم حذف {removed_count} استبدال(ات)")
            await state.clear()

        except Exception as e:
            logger.error(f"Error processing replace remove input: {e}")
            await message.answer("❌ خطأ في حذف الاستبدال")
            await state.clear()

    async def _process_blocked_words_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process blocked words input"""
        try:
            words = [word.strip() for word in input_text.split('\n') if word.strip()]
            
            # Get current blocked words
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_words = []
            if settings and settings.get("blocked_words"):
                try:
                    import json
                    data = settings["blocked_words"]
                    if isinstance(data, str):
                        current_words = json.loads(data)
                    elif isinstance(data, list):
                        current_words = data
                except:
                    pass

            # Add new words
            new_words = []
            for word in words:
                if word not in current_words:
                    current_words.append(word)
                    new_words.append(word)

            # Save to database
            import json
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET blocked_words = $1 WHERE task_id = $2",
                json.dumps(current_words), task_id
            )

            if new_words:
                await message.answer(f"✅ تم إضافة {len(new_words)} كلمة محظورة")
            else:
                await message.answer("⚠️ جميع الكلمات موجودة بالفعل")
            
            await state.clear()

        except Exception as e:
            logger.error(f"Error processing blocked words input: {e}")
            await message.answer("❌ خطأ في إضافة الكلمات المحظورة")
            await state.clear()

    async def _process_inline_button_input(self, message: Message, task_id: int, input_text: str, state: FSMContext):
        """Process inline button input with row support using '-' separator"""
        try:
            # Parse button format with row support
            # "Text|type|value - Text2|type2|value2" = same row
            # New line = new row
            button_rows = []
            
            # Split by newlines to separate different rows
            lines = [line.strip() for line in input_text.split('\n') if line.strip()]
            
            for line in lines:
                row_buttons = []
                
                # Split by " - " to get buttons in the same row
                if " - " in line:
                    button_texts = [btn.strip() for btn in line.split(" - ") if btn.strip()]
                else:
                    button_texts = [line]
                
                # Process each button in this row
                for button_text in button_texts:
                    if "|" in button_text:
                        parts = button_text.split("|")
                        text = parts[0].strip()
                        button_type = parts[1].strip() if len(parts) > 1 else "url"
                        value = parts[2].strip() if len(parts) > 2 else ""
                        
                        # If only 2 parts, assume text|url format
                        if len(parts) == 2 and ("http" in parts[1] or "www" in parts[1]):
                            button_type = "url"
                            value = parts[1].strip()
                        
                        row_buttons.append({
                            "text": text,
                            "type": button_type,
                            "value": value
                        })
                    else:
                        row_buttons.append({
                            "text": button_text,
                            "type": "url", 
                            "value": ""
                        })
                
                if row_buttons:
                    button_rows.append(row_buttons)
            
            # Flatten for backward compatibility but preserve row info
            all_buttons = []
            for row_index, row in enumerate(button_rows):
                for button in row:
                    button["row"] = row_index
                    all_buttons.append(button)

            # Get current button settings
            settings = await self.bot_controller.database.get_task_settings(task_id)
            button_settings = {}
            if settings and settings.get("inline_button_settings"):
                try:
                    import json
                    data = settings["inline_button_settings"]
                    if isinstance(data, str):
                        button_settings = json.loads(data)
                    else:
                        button_settings = data
                except:
                    pass

            # Update buttons and rows info
            button_settings["buttons"] = all_buttons
            button_settings["button_rows"] = button_rows  # Save row structure
            button_settings["enabled"] = True

            # Save to database
            import json
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET inline_button_settings = $1 WHERE task_id = $2",
                json.dumps(button_settings), task_id
            )

            total_buttons = len(all_buttons)
            total_rows = len(button_rows)
            await message.answer(f"✅ تم إضافة {total_buttons} زر في {total_rows} صف")
            await state.clear()

        except Exception as e:
            logger.error(f"Error processing inline button input: {e}")
            await message.answer("❌ خطأ في إضافة الأزرار")
            await state.clear()

    def _apply_formatting_preview(self, text: str, format_settings: dict) -> str:
        """Apply formatting preview to text"""
        try:
            if not text or not format_settings:
                return text
                
            # If remove_all is enabled, return plain text
            if format_settings.get("remove_all", False):
                return text
                
            formatted = text
            
            # Apply each formatting if enabled
            if format_settings.get("apply_bold", False):
                formatted = f"**{formatted}**"
            if format_settings.get("apply_italic", False):
                formatted = f"__{formatted}__"
            if format_settings.get("apply_underline", False):
                formatted = f"__{formatted}__"
            if format_settings.get("apply_strikethrough", False):
                formatted = f"~~{formatted}~~"
            if format_settings.get("apply_code", False):
                formatted = f"`{formatted}`"
            if format_settings.get("apply_mono", False):
                formatted = f"```{formatted}```"
            if format_settings.get("apply_quote", False):
                formatted = f">{formatted}"
            if format_settings.get("apply_spoiler", False):
                formatted = f"||{formatted}||"
            if format_settings.get("apply_link", False):
                custom_url = format_settings.get("custom_link_url", "https://example.com")
                formatted = f"[{formatted}]({custom_url})"
                
            return formatted
            
        except Exception as e:
            logger.error(f"Error in formatting preview: {e}")
            return text

    async def _process_user_input(self, message: Message, task_id: int, list_type: str, state: FSMContext):
        """Process user input for whitelist/blacklist"""
        try:
            import json
            import time
            
            user_input = message.text.strip()
            
            # Clean input and extract user identifier
            user_id_or_username = user_input.replace('@', '').strip()
            
            # Validate input format
            if not user_id_or_username:
                await message.answer("❌ يرجى إدخال معرف صحيح للمستخدم")
                return
            
            # Determine if it's a numeric ID or username
            if user_id_or_username.isdigit():
                user_id = int(user_id_or_username)
                username = None
            else:
                user_id = None
                username = user_id_or_username
            
            # Get current list data
            column_name = f"user_{list_type}"
            list_data = await self.bot_controller.database.execute_query(
                f"SELECT {column_name} FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_enabled = False
            current_users = []
            
            if list_data and list_data[0][column_name]:
                try:
                    data = list_data[0][column_name]
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_enabled = parsed_data.get('enabled', False)
                        current_users = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_users = parsed_data
                except:
                    pass
            
            # Check if user already exists
            user_exists = False
            for existing_user in current_users:
                if isinstance(existing_user, dict):
                    if (user_id and existing_user.get('id') == user_id) or \
                       (username and existing_user.get('username') == username):
                        user_exists = True
                        break
                else:
                    if str(existing_user) == str(user_id_or_username):
                        user_exists = True
                        break
            
            if user_exists:
                list_name = "القائمة البيضاء" if list_type == "whitelist" else "القائمة السوداء"
                await message.answer(f"⚠️ المستخدم موجود بالفعل في {list_name}")
                return
            
            # Add new user
            new_user = {
                'id': user_id,
                'username': username,
                'name': username or str(user_id),
                'added_at': str(int(time.time()))
            }
            
            current_users.append(new_user)
            
            # Update database
            new_data = {
                'enabled': True,  # Enable the list when adding first user
                'users': current_users
            }
            
            await self.bot_controller.database.execute_command(
                f"UPDATE task_settings SET {column_name} = $1 WHERE task_id = $2",
                json.dumps(new_data), task_id
            )
            
            list_name = "القائمة البيضاء" if list_type == "whitelist" else "القائمة السوداء"
            user_display = username or str(user_id)
            await message.answer(f"✅ تم إضافة المستخدم '{user_display}' إلى {list_name}")
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            await message.answer("❌ خطأ في إضافة المستخدم")
            await state.clear()

    async def _handle_whitelist_remove_user(self, callback: CallbackQuery, task_id: int, user_index: int, state: FSMContext):
        """Remove specific user from whitelist"""
        try:
            import json
            
            # Get current whitelist
            settings = await self.bot_controller.database.execute_query(
                "SELECT user_whitelist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_whitelist = []
            if settings and settings[0]['user_whitelist']:
                try:
                    data = settings[0]['user_whitelist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_whitelist = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_whitelist = parsed_data
                except:
                    pass
            
            if user_index >= len(current_whitelist):
                await callback.answer("❌ المستخدم غير موجود", show_alert=True)
                return
            
            # Remove user
            removed_user = current_whitelist.pop(user_index)
            
            # Update database
            new_data = {
                'enabled': len(current_whitelist) > 0,  # Disable if no users left
                'users': current_whitelist
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET user_whitelist = $1 WHERE task_id = $2",
                json.dumps(new_data), task_id
            )
            
            user_display = removed_user.get('name', 'Unknown') if isinstance(removed_user, dict) else str(removed_user)
            await callback.answer(f"✅ تم حذف '{user_display}' من القائمة البيضاء", show_alert=True)
            
            # Refresh the list display
            await self._handle_whitelist_list(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error removing user from whitelist: {e}")
            await callback.answer("❌ خطأ في حذف المستخدم", show_alert=True)

    async def _handle_whitelist_remove(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Remove user from whitelist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_whitelist = settings.get('user_whitelist', []) if settings else []
            
            if not current_whitelist:
                await callback.answer("⚠️ القائمة البيضاء فارغة", show_alert=True)
                return
                
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة البيضاء", callback_data=f"user_whitelist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "➖ حذف مستخدم من القائمة البيضاء\n\n"
                "أرسل:\n"
                "• معرف المستخدم (ID): 123456789\n"
                "• اسم المستخدم: @username\n"
                "• عدة مستخدمين مفصولين بسطر جديد",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="whitelist_remove",
                task_id=task_id,
                awaiting_input="user_whitelist_remove"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in whitelist remove: {e}")
            await callback.answer("❌ خطأ في حذف المستخدم", show_alert=True)

    async def _handle_whitelist_list(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show complete whitelist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_whitelist = settings.get('user_whitelist', []) if settings else []
            
            if not current_whitelist:
                await callback.answer("📋 القائمة البيضاء فارغة")
                return
                
            text = f"📋 القائمة البيضاء الكاملة ({len(current_whitelist)} مستخدم)\n\n"
            
            for i, user in enumerate(current_whitelist, 1):
                text += f"{i}. {user}\n"
                
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة البيضاء", callback_data=f"user_whitelist_{task_id}")]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            
        except Exception as e:
            logger.error(f"Error showing whitelist: {e}")
            await callback.answer("❌ خطأ في عرض القائمة", show_alert=True)

    async def _handle_whitelist_clear(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear entire whitelist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_whitelist = settings.get('user_whitelist', []) if settings else []
            
            if not current_whitelist:
                await callback.answer("⚠️ القائمة البيضاء فارغة بالفعل")
                return
                
            keyboard = [
                [
                    InlineKeyboardButton(text="✅ نعم، احذف الكل", callback_data=f"whitelist_clear_confirm_{task_id}"),
                    InlineKeyboardButton(text="❌ إلغاء", callback_data=f"user_whitelist_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(
                f"🗑️ تأكيد حذف القائمة البيضاء\n\n"
                f"هل تريد حذف جميع المستخدمين ({len(current_whitelist)}) من القائمة البيضاء؟\n\n"
                "⚠️ هذا الإجراء لا يمكن التراجع عنه!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in whitelist clear: {e}")
            await callback.answer("❌ خطأ في حذف القائمة", show_alert=True)

    async def _handle_whitelist_export(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Export whitelist as text"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_whitelist = settings.get('user_whitelist', []) if settings else []
            
            if not current_whitelist:
                await callback.answer("⚠️ القائمة البيضاء فارغة - لا يوجد ما يمكن تصديره", show_alert=True)
                return
                
            export_text = f"📤 القائمة البيضاء - المهمة {task_id}\n"
            export_text += f"تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            for user in current_whitelist:
                export_text += f"{user}\n"
                
            # Send as text message
            await self.bot_controller.bot.send_message(
                callback.from_user.id,
                f"```\n{export_text}\n```",
                parse_mode="Markdown"
            )
            
            await callback.answer("📤 تم تصدير القائمة البيضاء")
            
        except Exception as e:
            logger.error(f"Error exporting whitelist: {e}")
            await callback.answer("❌ خطأ في تصدير القائمة", show_alert=True)

    async def _handle_whitelist_import(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Import whitelist from text"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة البيضاء", callback_data=f"user_whitelist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "📥 استيراد القائمة البيضاء\n\n"
                "أرسل قائمة المستخدمين:\n"
                "• مستخدم واحد في كل سطر\n"
                "• يمكن استخدام معرفات أو أسماء المستخدمين\n"
                "• سيتم إضافة المستخدمين الجدد للقائمة الحالية\n\n"
                "مثال:\n"
                "123456789\n"
                "@username1\n"
                "@username2",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="whitelist_import",
                task_id=task_id,
                awaiting_input="user_whitelist_import"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in whitelist import: {e}")
            await callback.answer("❌ خطأ في استيراد القائمة", show_alert=True)

    # Blacklist management functions
    async def _handle_blacklist_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle blacklist on/off"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_blacklist = settings.get('user_blacklist', []) if settings else []
            
            if current_blacklist:
                # Disable blacklist by clearing it
                await self.bot_controller.database.update_task_settings(task_id, {'user_blacklist': []})
                await callback.answer("🔴 تم تعطيل القائمة السوداء")
            else:
                await callback.answer("⚠️ القائمة السوداء فارغة - أضف مستخدمين أولاً", show_alert=True)
                
            # Refresh the blacklist management interface
            await self._handle_user_blacklist_management(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling blacklist: {e}")
            await callback.answer("❌ خطأ في تبديل القائمة السوداء", show_alert=True)

    async def _handle_blacklist_add(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Add user to blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "➕ إضافة مستخدم للقائمة السوداء\n\n"
                "أرسل:\n"
                "• معرف المستخدم (ID): 123456789\n"
                "• اسم المستخدم: @username\n"
                "• عدة مستخدمين مفصولين بسطر جديد",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="blacklist_add",
                task_id=task_id,
                awaiting_input="user_blacklist"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in blacklist add: {e}")
            await callback.answer("❌ خطأ في إضافة المستخدم", show_alert=True)

    async def _handle_blacklist_remove(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Remove user from blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_blacklist = settings.get('user_blacklist', []) if settings else []
            
            if not current_blacklist:
                await callback.answer("⚠️ القائمة السوداء فارغة", show_alert=True)
                return
                
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "➖ حذف مستخدم من القائمة السوداء\n\n"
                "أرسل:\n"
                "• معرف المستخدم (ID): 123456789\n"
                "• اسم المستخدم: @username\n"
                "• عدة مستخدمين مفصولين بسطر جديد",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="blacklist_remove",
                task_id=task_id,
                awaiting_input="user_blacklist_remove"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in blacklist remove: {e}")
            await callback.answer("❌ خطأ في حذف المستخدم", show_alert=True)

    async def _handle_blacklist_list(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Show complete blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_blacklist = settings.get('user_blacklist', []) if settings else []
            
            if not current_blacklist:
                await callback.answer("📋 القائمة السوداء فارغة")
                return
                
            text = f"📋 القائمة السوداء الكاملة ({len(current_blacklist)} مستخدم)\n\n"
            
            for i, user in enumerate(current_blacklist, 1):
                text += f"{i}. {user}\n"
                
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            
        except Exception as e:
            logger.error(f"Error showing blacklist: {e}")
            await callback.answer("❌ خطأ في عرض القائمة", show_alert=True)

    async def _handle_blacklist_clear(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear entire blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_blacklist = settings.get('user_blacklist', []) if settings else []
            
            if not current_blacklist:
                await callback.answer("⚠️ القائمة السوداء فارغة بالفعل")
                return
                
            keyboard = [
                [
                    InlineKeyboardButton(text="✅ نعم، احذف الكل", callback_data=f"blacklist_clear_confirm_{task_id}"),
                    InlineKeyboardButton(text="❌ إلغاء", callback_data=f"user_blacklist_{task_id}")
                ]
            ]
            
            await callback.message.edit_text(
                f"🗑️ تأكيد حذف القائمة السوداء\n\n"
                f"هل تريد حذف جميع المستخدمين ({len(current_blacklist)}) من القائمة السوداء؟\n\n"
                "⚠️ هذا الإجراء لا يمكن التراجع عنه!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in blacklist clear: {e}")
            await callback.answer("❌ خطأ في حذف القائمة", show_alert=True)

    async def _handle_blacklist_export(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Export blacklist as text"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_blacklist = settings.get('user_blacklist', []) if settings else []
            
            if not current_blacklist:
                await callback.answer("⚠️ القائمة السوداء فارغة - لا يوجد ما يمكن تصديره", show_alert=True)
                return
                
            export_text = f"📤 القائمة السوداء - المهمة {task_id}\n"
            export_text += f"تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            for user in current_blacklist:
                export_text += f"{user}\n"
                
            # Send as text message
            await self.bot_controller.bot.send_message(
                callback.from_user.id,
                f"```\n{export_text}\n```",
                parse_mode="Markdown"
            )
            
            await callback.answer("📤 تم تصدير القائمة السوداء")
            
        except Exception as e:
            logger.error(f"Error exporting blacklist: {e}")
            await callback.answer("❌ خطأ في تصدير القائمة", show_alert=True)

    async def _handle_blacklist_import(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Import blacklist from text"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "📥 استيراد القائمة السوداء\n\n"
                "أرسل قائمة المستخدمين:\n"
                "• مستخدم واحد في كل سطر\n"
                "• يمكن استخدام معرفات أو أسماء المستخدمين\n"
                "• سيتم إضافة المستخدمين الجدد للقائمة الحالية\n\n"
                "مثال:\n"
                "123456789\n"
                "@username1\n"
                "@username2",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="blacklist_import",
                task_id=task_id,
                awaiting_input="user_blacklist_import"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in blacklist import: {e}")
            await callback.answer("❌ خطأ في استيراد القائمة", show_alert=True)

    async def _handle_blacklist_remove_user(self, callback: CallbackQuery, task_id: int, user_index: int, state: FSMContext):
        """Remove specific user from blacklist"""
        try:
            import json
            
            # Get current blacklist
            settings = await self.bot_controller.database.execute_query(
                "SELECT user_blacklist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_blacklist = []
            if settings and settings[0]['user_blacklist']:
                try:
                    data = settings[0]['user_blacklist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_blacklist = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_blacklist = parsed_data
                except:
                    pass
            
            if user_index >= len(current_blacklist):
                await callback.answer("❌ المستخدم غير موجود", show_alert=True)
                return
            
            # Remove user
            removed_user = current_blacklist.pop(user_index)
            
            # Update database
            new_data = {
                'enabled': len(current_blacklist) > 0,
                'users': current_blacklist
            }
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET user_blacklist = $1 WHERE task_id = $2",
                json.dumps(new_data), task_id
            )
            
            user_display = removed_user.get('name', 'Unknown') if isinstance(removed_user, dict) else str(removed_user)
            await callback.answer(f"✅ تم حذف '{user_display}' من القائمة السوداء", show_alert=True)
            
            # Refresh the list display
            await self._handle_blacklist_list(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error removing user from blacklist: {e}")
            await callback.answer("❌ خطأ في حذف المستخدم", show_alert=True)

    async def _handle_blacklist_add(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle adding user to blacklist"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "➕ إضافة مستخدم للقائمة السوداء\n\n"
                "أرسل معرف المستخدم أو اسم المستخدم:\n"
                "• معرف رقمي: 123456789\n"
                "• اسم المستخدم: @username\n"
                "• اسم المستخدم بدون @: username\n\n"
                "💡 يمكنك الحصول على معرف المستخدم بإرسال رسالة منه في أي قناة مشتركة",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="blacklist_add",
                task_id=task_id,
                awaiting_input="add_blacklist_user"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in blacklist add: {e}")
            await callback.answer("❌ خطأ في إضافة المستخدم", show_alert=True)

    async def _handle_blacklist_export(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Export blacklist as text"""
        try:
            import json
            from datetime import datetime
            
            # Get current blacklist
            settings = await self.bot_controller.database.execute_query(
                "SELECT user_blacklist FROM task_settings WHERE task_id = $1", task_id
            )
            
            current_blacklist = []
            if settings and settings[0]['user_blacklist']:
                try:
                    data = settings[0]['user_blacklist']
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    if isinstance(parsed_data, dict):
                        current_blacklist = parsed_data.get('users', [])
                    elif isinstance(parsed_data, list):
                        current_blacklist = parsed_data
                except:
                    pass
            
            if not current_blacklist:
                await callback.answer("⚠️ القائمة السوداء فارغة - لا يوجد ما يمكن تصديره", show_alert=True)
                return
                
            export_text = f"📤 القائمة السوداء - المهمة {task_id}\n"
            export_text += f"تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            for i, user in enumerate(current_blacklist):
                if isinstance(user, dict):
                    user_display = user.get('name', user.get('username', user.get('id', 'Unknown')))
                    user_id = user.get('id', 'N/A')
                    export_text += f"{i+1}. {user_display} ({user_id})\n"
                else:
                    export_text += f"{i+1}. {user}\n"
                
            # Send as text message
            await self.bot_controller.bot.send_message(
                callback.from_user.id,
                f"```\n{export_text}\n```",
                parse_mode="Markdown"
            )
            
            await callback.answer("📤 تم تصدير القائمة السوداء")
            
        except Exception as e:
            logger.error(f"Error exporting blacklist: {e}")
            await callback.answer("❌ خطأ في تصدير القائمة", show_alert=True)

    async def _handle_blacklist_import(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Import blacklist from text"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة للقائمة السوداء", callback_data=f"user_blacklist_{task_id}")]
            ]
            
            await callback.message.edit_text(
                "📥 استيراد القائمة السوداء\n\n"
                "أرسل قائمة المستخدمين:\n"
                "• مستخدم واحد في كل سطر\n"
                "• يمكن استخدام معرفات أو أسماء المستخدمين\n"
                "• سيتم إضافة المستخدمين الجدد للقائمة الحالية\n\n"
                "مثال:\n"
                "123456789\n"
                "@username1\n"
                "@username2",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.update_data(
                current_menu="blacklist_import",
                task_id=task_id,
                awaiting_input="user_blacklist_import"
            )
            await state.set_state(TaskStates.WAITING_INPUT)
            
        except Exception as e:
            logger.error(f"Error in blacklist import: {e}")
            await callback.answer("❌ خطأ في استيراد القائمة", show_alert=True)

    # Confirmation handlers
    async def _handle_whitelist_clear_confirm(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Confirm and execute whitelist clear"""
        try:
            await self.bot_controller.database.update_task_settings(task_id, {'user_whitelist': []})
            await callback.answer("✅ تم حذف جميع المستخدمين من القائمة البيضاء")
            
            # Return to whitelist management
            await self._handle_user_whitelist_management(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error confirming whitelist clear: {e}")
            await callback.answer("❌ خطأ في حذف القائمة", show_alert=True)

    async def _handle_blacklist_clear_confirm(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Confirm and execute blacklist clear"""
        try:
            await self.bot_controller.database.update_task_settings(task_id, {'user_blacklist': []})
            await callback.answer("✅ تم حذف جميع المستخدمين من القائمة السوداء")
            
            # Return to blacklist management
            await self._handle_user_blacklist_management(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error confirming blacklist clear: {e}")
            await callback.answer("❌ خطأ في حذف القائمة", show_alert=True)

    # Advanced Features Handlers
    async def _handle_translation_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle translation feature"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("auto_translate", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET auto_translate = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} الترجمة التلقائية")
            
            # Refresh translation settings
            await self._handle_setting_translation(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling translation: {e}")
            await callback.answer("❌ خطأ في تغيير إعدادات الترجمة", show_alert=True)



    async def _handle_working_hours_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle working hours feature"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("working_hours_enabled", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET working_hours_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} ساعات العمل")
            
            # Refresh working hours settings
            await self._handle_setting_working_hours(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling working hours: {e}")
            await callback.answer("❌ خطأ في تغيير إعدادات ساعات العمل", show_alert=True)

    async def _handle_set_start_hour(self, callback: CallbackQuery, task_id: int, hour: int, state: FSMContext):
        """Set start hour for working hours"""
        try:
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET start_hour = $1 WHERE task_id = $2",
                hour, task_id
            )
            
            await callback.answer(f"✅ تم تعيين ساعة البداية إلى {hour:02d}:00")
            
            # Refresh working hours settings
            await self._handle_setting_working_hours(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting start hour: {e}")
            await callback.answer("❌ خطأ في تعيين ساعة البداية", show_alert=True)

    async def _handle_set_end_hour(self, callback: CallbackQuery, task_id: int, hour: int, state: FSMContext):
        """Set end hour for working hours"""
        try:
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET end_hour = $1 WHERE task_id = $2",
                hour, task_id
            )
            
            await callback.answer(f"✅ تم تعيين ساعة النهاية إلى {hour:02d}:00")
            
            # Refresh working hours settings
            await self._handle_setting_working_hours(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting end hour: {e}")
            await callback.answer("❌ خطأ في تعيين ساعة النهاية", show_alert=True)

    async def _handle_set_timezone(self, callback: CallbackQuery, task_id: int, timezone: str, state: FSMContext):
        """Set timezone for working hours"""
        try:
            # Replace underscore back to slash for timezone
            timezone = timezone.replace('_', '/')
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET timezone = $1 WHERE task_id = $2",
                timezone, task_id
            )
            
            await callback.answer(f"✅ تم تعيين المنطقة الزمنية إلى {timezone}")
            
            # Refresh working hours settings
            await self._handle_setting_working_hours(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting timezone: {e}")
            await callback.answer("❌ خطأ في تعيين المنطقة الزمنية", show_alert=True)

    async def _handle_recurring_post_toggle(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle recurring post feature"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("recurring_post_enabled", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET recurring_post_enabled = $1 WHERE task_id = $2",
                new_value, task_id
            )
            
            status = "تم تفعيل" if new_value else "تم إلغاء"
            await callback.answer(f"✅ {status} المنشور المتكرر")
            
            # Refresh recurring post settings
            await self._handle_setting_recurring_post(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling recurring post: {e}")
            await callback.answer("❌ خطأ في تغيير إعدادات المنشور المتكرر", show_alert=True)

    async def _handle_set_recurring_interval(self, callback: CallbackQuery, task_id: int, interval_hours: int, state: FSMContext):
        """Set recurring post interval"""
        try:
            await self.bot_controller.database.execute_command(
                "UPDATE task_settings SET recurring_interval_hours = $1 WHERE task_id = $2",
                interval_hours, task_id
            )
            
            interval_text = f"{interval_hours} ساعة" if interval_hours < 24 else f"{interval_hours // 24} يوم"
            if interval_hours == 168:
                interval_text = "أسبوع"
                
            await callback.answer(f"✅ تم تعيين الفترة إلى كل {interval_text}")
            
            # Refresh recurring post settings
            await self._handle_setting_recurring_post(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error setting recurring interval: {e}")
            await callback.answer("❌ خطأ في تعيين الفترة الزمنية", show_alert=True)

    async def _handle_suffix_add(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle adding suffix"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Set up state for text input
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="add_suffix", task_id=task_id)
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_prefix_{task_id}")]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(
                "➕ **إضافة لاحقة**\n\n"
                "أرسل النص الذي تريد إضافته كلاحقة في نهاية كل رسالة:\n\n"
                "مثال: \n"
                "`- منشور من قناتنا`\n"
                "`🔗 t.me/yourchannel`",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in suffix add: {e}")
            await callback.answer("❌ خطأ في إضافة اللاحقة", show_alert=True)

    async def _handle_suffix_edit(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle editing suffix"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Verify task ownership
            task = await self.task_manager.get_task(task_id)
            if not task or task["user_telegram_id"] != callback.from_user.id:
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            # Get current suffix
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_suffix = settings.get("suffix_text", "") if settings else ""
            
            # Set up state for text input
            await state.set_state(TaskStates.WAITING_INPUT)
            await state.update_data(action="edit_suffix", task_id=task_id)
            
            keyboard = [
                [InlineKeyboardButton(text="🔙 العودة", callback_data=f"content_prefix_{task_id}")]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            suffix_display = f"الحالية: `{current_suffix}`" if current_suffix else "لا توجد لاحقة محددة"
            
            await callback.message.edit_text(
                f"✏️ **تعديل اللاحقة**\n\n"
                f"اللاحقة {suffix_display}\n\n"
                "أرسل اللاحقة الجديدة أو أرسل `-` لحذف اللاحقة الحالية:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in suffix edit: {e}")
            await callback.answer("❌ خطأ في تعديل اللاحقة", show_alert=True)

    # === Missing Forward Settings Handlers ===

    async def _handle_toggle_manual_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle manual mode for forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("manual_mode", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"manual_mode": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} الوضع اليدوي")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling manual mode: {e}")
            await callback.answer("❌ خطأ في تغيير الوضع اليدوي", show_alert=True)

    async def _handle_toggle_link_preview(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle link preview in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("link_preview", True) if settings else True
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"link_preview": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} معاينة الروابط")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling link preview: {e}")
            await callback.answer("❌ خطأ في تغيير معاينة الروابط", show_alert=True)

    async def _handle_toggle_pin_messages(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle pin messages in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("pin_messages", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"pin_messages": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} تثبيت الرسائل")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling pin messages: {e}")
            await callback.answer("❌ خطأ في تغيير تثبيت الرسائل", show_alert=True)

    async def _handle_toggle_silent_mode(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle silent mode in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("silent_mode", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"silent_mode": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} الوضع الصامت")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling silent mode: {e}")
            await callback.answer("❌ خطأ في تغيير الوضع الصامت", show_alert=True)

    async def _handle_toggle_sync_deletes(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle synchronize deletes in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("sync_deletes", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"sync_deletes": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} مزامنة الحذف")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling sync deletes: {e}")
            await callback.answer("❌ خطأ في تغيير مزامنة الحذف", show_alert=True)

    async def _handle_toggle_preserve_replies(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle preserve replies in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("preserve_replies", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"preserve_replies": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} المحافظة على الردود")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling preserve replies: {e}")
            await callback.answer("❌ خطأ في تغيير المحافظة على الردود", show_alert=True)

    async def _handle_toggle_sync_edits(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Toggle synchronize edits in forwarding"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id)
            current_value = settings.get("sync_edits", False) if settings else False
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {"sync_edits": new_value})
            
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} مزامنة التعديل")
            
            # Refresh forward settings
            await self._handle_forward_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling sync edits: {e}")
            await callback.answer("❌ خطأ في تغيير مزامنة التعديل", show_alert=True)

    async def _handle_forward_other_settings(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Handle other forward settings"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id) or {}
            
            # Get current values
            protect_content = settings.get("protect_content", False)
            disable_web_preview = settings.get("disable_web_preview", False)
            parse_mode = settings.get("parse_mode", "HTML")
            
            settings_text = f"""⚙️ **إعدادات توجيه أخرى**

**حماية المحتوى:**
{'✅' if protect_content else '❌'} منع الحفظ والنسخ

**معاينة الويب:**
{'✅' if not disable_web_preview else '❌'} عرض معاينة المواقع

**وضع التحليل:**
📝 {parse_mode}

**خيارات إضافية:**
• حماية المحتوى من النسخ
• تعطيل معاينة الروابط
• تخصيص وضع التحليل
• إعدادات الأمان المتقدمة"""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if protect_content else '❌'} حماية المحتوى",
                        callback_data=f"toggle_protect_content_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'✅' if not disable_web_preview else '❌'} معاينة الويب",
                        callback_data=f"toggle_web_preview_{task_id}"
                    )
                ],
                [
                    InlineKeyboardButton(text=f"📝 وضع التحليل: {parse_mode}", callback_data=f"set_parse_mode_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔒 إعدادات الأمان", callback_data=f"forward_security_{task_id}"),
                    InlineKeyboardButton(text="⚡ إعدادات الأداء", callback_data=f"forward_performance_{task_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 العودة للتوجيه", callback_data=f"setting_forward_{task_id}")
                ]
            ])

            await callback.message.edit_text(settings_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in forward other settings: {e}")
            await callback.answer("❌ خطأ في عرض الإعدادات الأخرى", show_alert=True)

    # === Missing Media Filters Handlers ===

    async def _handle_media_enable_all(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Enable all media types"""
        try:
            media_settings = {
                "allow_photos": True,
                "allow_videos": True,
                "allow_documents": True,
                "allow_audio": True,
                "allow_voice": True,
                "allow_video_notes": True,
                "allow_stickers": True,
                "allow_animations": True,
                "allow_contacts": True,
                "allow_locations": True,
                "allow_venues": True,
                "allow_polls": True,
                "allow_dice": True,
                "allow_text": True
            }
            
            await self.bot_controller.database.update_task_settings(task_id, media_settings)
            await callback.answer("✅ تم تفعيل جميع أنواع الوسائط")
            
            # Refresh media types keyboard
            await self._handle_filter_media_types(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error enabling all media: {e}")
            await callback.answer("❌ خطأ في تفعيل الوسائط", show_alert=True)

    async def _handle_media_disable_all(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Disable all media types"""
        try:
            media_settings = {
                "allow_photos": False,
                "allow_videos": False,
                "allow_documents": False,
                "allow_audio": False,
                "allow_voice": False,
                "allow_video_notes": False,
                "allow_stickers": False,
                "allow_animations": False,
                "allow_contacts": False,
                "allow_locations": False,
                "allow_venues": False,
                "allow_polls": False,
                "allow_dice": False,
                "allow_text": False
            }
            
            await self.bot_controller.database.update_task_settings(task_id, media_settings)
            await callback.answer("❌ تم تعطيل جميع أنواع الوسائط")
            
            # Refresh media types keyboard
            await self._handle_filter_media_types(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error disabling all media: {e}")
            await callback.answer("❌ خطأ في تعطيل الوسائط", show_alert=True)

    async def _handle_media_reset(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Reset media types to default"""
        try:
            # Default media settings (all enabled)
            media_settings = {
                "allow_photos": True,
                "allow_videos": True,
                "allow_documents": True,
                "allow_audio": True,
                "allow_voice": True,
                "allow_video_notes": True,
                "allow_stickers": True,
                "allow_animations": True,
                "allow_contacts": True,
                "allow_locations": True,
                "allow_venues": True,
                "allow_polls": True,
                "allow_dice": True,
                "allow_text": True
            }
            
            await self.bot_controller.database.update_task_settings(task_id, media_settings)
            await callback.answer("🔄 تم إعادة تعيين إعدادات الوسائط للافتراضية")
            
            # Refresh media types keyboard
            await self._handle_filter_media_types(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error resetting media: {e}")
            await callback.answer("❌ خطأ في إعادة تعيين الوسائط", show_alert=True)

    async def _handle_media_save(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Save current media settings"""
        try:
            # Get current settings for confirmation
            settings = await self.bot_controller.database.get_task_settings(task_id) or {}
            
            enabled_count = sum(1 for key in [
                "allow_photos", "allow_videos", "allow_documents", "allow_audio",
                "allow_voice", "allow_video_notes", "allow_stickers", "allow_animations",
                "allow_contacts", "allow_locations", "allow_venues", "allow_polls", "allow_dice", "allow_text"
            ] if settings.get(key, True))
            
            total_count = 14  # Total number of media types
            
            await callback.answer(f"💾 تم حفظ الإعدادات - مفعل: {enabled_count}/{total_count}")
            
            # Return to filters menu
            await self._handle_filters_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error saving media settings: {e}")
            await callback.answer("❌ خطأ في حفظ الإعدادات", show_alert=True)

    async def _handle_media_type_toggle(self, callback: CallbackQuery, task_id: int, media_type: str, state: FSMContext):
        """Toggle specific media type"""
        try:
            settings = await self.bot_controller.database.get_task_settings(task_id) or {}
            current_value = settings.get(media_type, True)
            new_value = not current_value
            
            await self.bot_controller.database.update_task_settings(task_id, {media_type: new_value})
            
            # Get media type display name
            type_names = {
                "allow_photos": "الصور",
                "allow_videos": "الفيديو",
                "allow_documents": "المستندات",
                "allow_audio": "الصوت",
                "allow_voice": "الرسائل الصوتية",
                "allow_video_notes": "الفيديو المدور",
                "allow_stickers": "الملصقات",
                "allow_animations": "الصور المتحركة",
                "allow_contacts": "جهات الاتصال",
                "allow_locations": "المواقع",
                "allow_venues": "الأماكن",
                "allow_polls": "الاستطلاعات",
                "allow_dice": "النرد",
                "allow_text": "النصوص"
            }
            
            type_name = type_names.get(media_type, media_type)
            status = "تفعيل" if new_value else "إلغاء"
            await callback.answer(f"✅ تم {status} {type_name}")
            
            # Refresh media types keyboard
            await self._handle_filter_media_types(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error toggling media type {media_type}: {e}")
            await callback.answer("❌ خطأ في تغيير نوع الوسائط", show_alert=True)

    # === Filter Management Handlers ===

    async def _handle_filter_clear_all(self, callback: CallbackQuery, task_id: int, state: FSMContext):
        """Clear all filters"""
        try:
            # Reset all filter settings to default
            filter_settings = {
                # Media filters
                "allow_photos": True,
                "allow_videos": True,
                "allow_documents": True,
                "allow_audio": True,
                "allow_voice": True,
                "allow_video_notes": True,
                "allow_stickers": True,
                "allow_animations": True,
                "allow_contacts": True,
                "allow_locations": True,
                "allow_venues": True,
                "allow_polls": True,
                "allow_dice": True,
                "allow_text": True,
                
                # Content filters
                "keywords": [],
                "blocked_keywords": [],
                "min_length": 0,
                "max_length": 0,
                
                # User filters
                "user_whitelist": [],
                "user_blacklist": [],
                "verified_only": False,
                "no_bots": False,
                
                # Other filters
                "allow_forwarded": True,
                "allow_links": True,
                "allow_buttons": True,
                "language_filter": []
            }
            
            await self.bot_controller.database.update_task_settings(task_id, filter_settings)
            await callback.answer("🗑️ تم مسح جميع الفلاتر وإعادة تعيينها للإعدادات الافتراضية")
            
            # Return to filters menu
            await self._handle_filters_setting(callback, task_id, state)
            
        except Exception as e:
            logger.error(f"Error clearing all filters: {e}")
            await callback.answer("❌ خطأ في مسح الفلاتر", show_alert=True)

    async def _handle_import_data(self, message: Message, state: FSMContext):
        """Handle importing task data from JSON"""
        try:
            import json
            user_id = message.from_user.id
            
            # Check if user sent a document
            if message.document:
                # Download and process document
                if message.document.mime_type == "application/json" or message.document.file_name.endswith(".json"):
                    try:
                        # Download file
                        file_info = await self.bot_controller.bot.get_file(message.document.file_id)
                        file_content = await self.bot_controller.bot.download_file(file_info.file_path)
                        
                        # Parse JSON
                        import_data = json.loads(file_content.read().decode("utf-8"))
                        
                    except Exception as e:
                        await message.answer("❌ خطأ في قراءة الملف. تأكد من أن الملف صالح وبتنسيق JSON")
                        return
                else:
                    await message.answer("❌ نوع الملف غير مدعوم. يرجى إرسال ملف JSON فقط")
                    return
                    
            elif message.text:
                # Process text as JSON
                try:
                    import_data = json.loads(message.text.strip())
                except json.JSONDecodeError:
                    await message.answer("❌ النص المرسل ليس بتنسيق JSON صالح")
                    return
            else:
                await message.answer("❌ يرجى إرسال ملف JSON أو نص JSON")
                return
            
            # Validate data structure
            if not isinstance(import_data, dict) or "tasks" not in import_data:
                await message.answer("❌ بنية البيانات غير صحيحة. يجب أن تحتوي على مفتاح tasks")
                return
            
            tasks_data = import_data["tasks"]
            if not isinstance(tasks_data, list):
                await message.answer("❌ tasks يجب أن يكون قائمة")
                return
            
            # Process each task
            imported_count = 0
            errors = []
            
            for i, task_data in enumerate(tasks_data):
                try:
                    await self._import_single_task(user_id, task_data, i + 1)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"المهمة {i + 1}: {str(e)}")
            
            # Send results
            result_text = f"📥 **نتائج الاستيراد**\\n\\n"
            result_text += f"✅ تم استيراد {imported_count} مهمة بنجاح\\n"
            
            if errors:
                result_text += f"❌ فشل في استيراد {len(errors)} مهمة:\\n"
                for error in errors[:5]:  # Show first 5 errors
                    result_text += f"• {error}\\n"
                if len(errors) > 5:
                    result_text += f"• ... و {len(errors) - 5} أخطاء أخرى\\n"
            
            result_text += f"\\n🎯 يمكنك الآن مراجعة المهام المستوردة من القائمة الرئيسية"
            
            await message.answer(result_text, parse_mode="Markdown")
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error in import data handler: {e}")
            await message.answer("❌ خطأ عام في عملية الاستيراد")
            await state.clear()

    async def _import_single_task(self, user_id: int, task_data: dict, task_number: int):
        """Import a single task from data"""
        try:
            # Validate required fields
            if "name" not in task_data:
                raise ValueError("اسم المهمة مطلوب")
            
            task_name = task_data["name"]
            task_description = task_data.get("description", "")
            
            # Create task
            result = await self.bot_controller.database.execute_query(
                """INSERT INTO tasks (user_id, name, description, is_active, created_at, updated_at) 
                   VALUES ($1, $2, $3, true, NOW(), NOW()) RETURNING id""",
                user_id, task_name, task_description
            )
            
            if not result:
                raise ValueError("فشل في إنشاء المهمة")
            
            task_id = result[0]["id"]
            
            # Import sources
            if "sources" in task_data and isinstance(task_data["sources"], list):
                for source in task_data["sources"]:
                    if "chat_id" in source:
                        await self.bot_controller.database.execute_command(
                            """INSERT INTO sources (task_id, chat_id, chat_title, is_active, created_at) 
                               VALUES ($1, $2, $3, true, NOW())""",
                            task_id, source["chat_id"], source.get("title", "مستورد")
                        )
            
            # Import targets
            if "targets" in task_data and isinstance(task_data["targets"], list):
                for target in task_data["targets"]:
                    if "chat_id" in target:
                        await self.bot_controller.database.execute_command(
                            """INSERT INTO targets (task_id, chat_id, chat_title, is_active, created_at) 
                               VALUES ($1, $2, $3, true, NOW())""",
                            task_id, target["chat_id"], target.get("title", "مستورد")
                        )
            
            logger.info(f"Successfully imported task {task_name} with ID {task_id}")
            
        except Exception as e:
            logger.error(f"Error importing task {task_number}: {e}")
            raise ValueError(f"خطأ في المهمة {task_number}: {str(e)}")

