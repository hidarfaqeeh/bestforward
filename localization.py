"""
Multi-language localization system for Telegram Forwarding Bot
Supports Arabic and English with dynamic language switching
"""

import json
from typing import Dict, Any, Optional
from loguru import logger

class LocalizationManager:
    """Manages multi-language support for the bot"""
    
    def __init__(self):
        self.languages = {}
        self.user_languages = {}  # Store user language preferences
        self.default_language = "en"
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation strings"""
        
        # English translations
        self.languages["en"] = {
            # Main menu
            "main_menu": "🏠 **Main Menu**",
            "welcome_message": "Welcome {name}! I'm your Telegram Forwarding Bot.",
            "help_text": """
🤖 **Telegram Forwarding Bot Help**

**Available Commands:**
• /start - Start the bot
• /help - Show this help message
• /menu - Main menu
• /status - Bot status
• /userbot - Userbot status

**Features:**
• Create forwarding tasks
• Advanced content filtering
• Text cleaning and modification
• Multi-language support
• Real-time monitoring

Choose your preferred language using the settings menu.
            """,
            
            # Buttons
            "btn_tasks": "📋 Tasks",
            "btn_settings": "⚙️ Settings", 
            "btn_statistics": "📊 Statistics",
            "btn_help": "❓ Help",
            "btn_language": "🌐 Language",
            "btn_back": "🔙 Back",
            "btn_cancel": "❌ Cancel",
            "btn_confirm": "✅ Confirm",
            "btn_save": "💾 Save",
            "btn_reset": "🔄 Reset",
            "btn_delete": "🗑️ Delete",
            "btn_edit": "✏️ Edit",
            "btn_view": "👁️ View",
            "btn_create": "➕ Create",
            "btn_manage": "🔧 Manage",
            
            # Task Management
            "task_list": "📋 **Task List**",
            "task_create": "➕ **Create New Task**",
            "task_settings": "⚙️ **Task Settings**",
            "task_name": "Task Name",
            "task_description": "Description",
            "task_status": "Status",
            "task_active": "Active",
            "task_inactive": "Inactive",
            "no_tasks": "No tasks found. Create your first task!",
            
            # Settings Categories
            "setting_filters": "🔽 Filters",
            "setting_content": "✏️ Content",
            "setting_forward": "📡 Forward",
            "setting_limits": "⏱️ Limits",
            "setting_advanced": "⚡ Advanced",
            "setting_view_all": "📋 View All",
            
            # Forward Settings
            "forward_mode": "🔄 Forward Mode",
            "forward_copy": "📋 Copy",
            "forward_forward": "➡️ Forward", 
            "forward_quote": "💬 Quote",
            "manual_mode": "Manual Mode",
            "link_preview": "Link Preview",
            "pin_messages": "Pin Messages",
            "silent_mode": "Silent Mode",
            "sync_edits": "Sync Edits",
            "sync_deletes": "Sync Deletes",
            "preserve_replies": "Preserve Replies",
            
            # Limits Settings
            "limits_title": "⏱️ **Limits Settings**",
            "message_delays": "⏱️ Message Delays",
            "send_limits": "📊 Send Limits", 
            "length_limit": "📏 Length Limit",
            "time_limits": "⏰ Time Limits",
            "delay_current": "Current delay: **{min}-{max} seconds**",
            "send_limit_current": "Send limit: {limit} messages/hour",
            "length_limit_current": "Length limit: {limit} characters",
            "unlimited": "Unlimited",
            "no_limit": "No limit",
            
            # Content Settings
            "content_settings": "✏️ **Content Settings**",
            "text_cleaner": "🧹 Text Cleaner",
            "text_replace": "🔄 Text Replace",
            "prefix_suffix": "📝 Prefix/Suffix",
            "formatting": "📄 Formatting",
            
            # Text Cleaner
            "cleaner_title": "🧹 **Text Cleaner Settings**",
            "cleaner_remove_emojis": "😀 Remove Emojis",
            "cleaner_remove_links": "🔗 Remove Links",
            "cleaner_remove_mentions": "👤 Remove Mentions",
            "cleaner_remove_emails": "📧 Remove Emails",
            "cleaner_remove_hashtags": "# Remove Hashtags",
            "cleaner_remove_numbers": "🔢 Remove Numbers",
            "cleaner_remove_punctuation": ".,!? Remove Punctuation",
            "cleaner_remove_empty_lines": "📝 Remove Empty Lines",
            "cleaner_remove_extra_lines": "📃 Remove Extra Lines",
            "cleaner_normalize_whitespace": "⬜ Normalize Whitespace",
            "cleaner_remove_duplicates": "🔄 Remove Duplicate Lines",
            "cleaner_target_words": "🎯 Remove Lines with Target Words",
            "cleaner_manage_words": "✏️ Manage Target Words",
            "cleaner_test": "🧪 Test Cleaner",
            
            # Advanced Settings
            "advanced_settings": "⚡ **Advanced Settings**",
            "advanced_translation": "🌐 Translation Settings",
            "advanced_working_hours": "⏰ Working Hours",
            "advanced_recurring": "🔄 Recurring Posts",
            
            # Working Hours Settings
            "working_hours_title": "⏰ **Working Hours Settings**",
            "working_hours_enabled": "✅ Working Hours Enabled",
            "working_hours_disabled": "❌ Working Hours Disabled",
            "start_hour": "🕐 Start Hour",
            "end_hour": "🕕 End Hour",
            "current_timezone": "🌍 Current Timezone",
            "set_timezone": "🌍 Set Timezone",
            "set_start_hour": "🕐 Set Start Hour",
            "set_end_hour": "🕕 Set End Hour",
            "working_days": "📅 Working Days",
            "breaks_settings": "☕ Break Settings",
            "test_current_time": "⏰ Test Current Time",
            "working_hours_report": "📊 Working Hours Report",
            
            # Translation Settings
            "translation_title": "🌐 **Translation Settings**",
            "auto_translate": "🔄 Auto Translation",
            "translation_enabled": "✅ Translation Enabled",
            "translation_disabled": "❌ Translation Disabled",
            "target_language": "🎯 Target Language",
            "source_language": "📝 Source Language",
            "translation_api": "🔧 Translation API",
            "translate_to_arabic": "🇸🇦 Translate to Arabic",
            "translate_to_english": "🇺🇸 Translate to English",
            "translation_test": "🧪 Test Translation",
            
            # User Filter Settings
            "user_filter_title": "👥 **User Filter Settings**",
            "filter_verified_users": "✅ Filter Verified Users",
            # "filter_bots": "🤖 Filter Bots",  # Removed - not implemented
            "user_whitelist": "✅ User Whitelist",
            "user_blacklist": "❌ User Blacklist",
            "manage_users": "👥 Manage Users",
            "add_user": "➕ Add User",
            "remove_user": "➖ Remove User",
            
            # Recurring Posts
            "recurring_title": "🔄 **Recurring Posts Settings**",
            "recurring_enabled": "✅ Recurring Enabled",
            "recurring_disabled": "❌ Recurring Disabled",
            "recurring_content": "📝 Recurring Content",
            "recurring_interval": "⏱️ Recurring Interval",
            "recurring_test": "🧪 Test Recurring Post",
            
            # Language Settings
            "language_settings": "🌐 **Language Settings**",
            "current_language": "Current Language: **{lang}**",
            "select_language": "Select your preferred language:",
            "language_english": "🇺🇸 English",
            "language_arabic": "🇸🇦 العربية",
            "language_changed": "Language changed to {lang}",
            
            # Status Messages
            "status_enabled": "✅ Enabled",
            "status_disabled": "❌ Disabled",
            "status_active": "🟢 Active",
            "status_inactive": "🔴 Inactive",
            "status_success": "✅ Success",
            "status_error": "❌ Error",
            "status_warning": "⚠️ Warning",
            
            # Common Messages
            "access_denied": "❌ Access denied.",
            "error_loading": "❌ Error loading settings.",
            "settings_saved": "✅ Settings saved successfully!",
            "operation_completed": "✅ Operation completed successfully.",
            "please_wait": "⏳ Please wait...",
            "processing": "🔄 Processing...",
            "back_to_main": "🔙 Back to Main Menu",
            "back_to_settings": "🔙 Back to Settings",
            
            # Task Status Messages
            "task_activated": "✅ Task activated successfully!",
            "task_deactivated": "⏹️ Task deactivated successfully!",
            "task_deleted": "🗑️ Task deleted successfully!",
            "task_created": "✅ Task created successfully!",
            "task_updated": "✅ Task updated successfully!",
            "task_not_found": "❌ Task not found.",
            "invalid_task_data": "❌ Invalid task data.",
            "operation_failed": "❌ Operation failed.",
            "confirmation_required": "⚠️ Are you sure?",
            "cancelled": "❌ Operation cancelled.",
            
            # Timezone Names
            "timezone_mecca": "🕌 Mecca",
            "timezone_cairo": "🏛️ Cairo",
            "timezone_utc": "🌍 UTC",
            "timezone_newyork": "🗽 New York",
            "timezone_london": "🏰 London",
            "timezone_paris": "🗼 Paris",
            "timezone_tokyo": "🏙️ Tokyo",
            "timezone_moscow": "🏛️ Moscow",
            
            # Days of Week
            "monday": "Monday",
            "tuesday": "Tuesday",
            "wednesday": "Wednesday", 
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday",
            
            # Time Formats
            "current_time": "Current time: {time}",
            "working_hours_format": "From {start} to {end}",
            "timezone_format": "Timezone: {timezone}",
            
            # Additional UI Elements
            "select_option": "Select an option:",
            "system_status": "🔄 System Status",
            "detailed_report": "📈 Detailed Report", 
            "quick_start": "🚀 Quick Start",
            "advanced_tools": "🔧 Advanced Tools",
            
            # Additional task management
            "import_task": "📥 Import Task",
            "export_tasks": "📤 Export Tasks", 
            "start_all_tasks": "🎯 Start All Tasks",
            "stop_all_tasks": "⏹️ Stop All Tasks",
            
            # Task Management Buttons
            "btn_activate": "▶️ Activate",
            "btn_deactivate": "⏹️ Deactivate", 
            "btn_edit_task": "✏️ Edit",
            "btn_task_stats": "📊 Statistics",
            "btn_task_settings": "⚙️ Settings",
            "btn_sources": "📥 Sources",
            "btn_targets": "📤 Targets",
            "btn_delete_task": "🗑️ Delete",
            "btn_task_info": "📋 Info",
            "btn_back_to_tasks": "🔙 Back to Tasks",
            "btn_add_source": "➕ Add Source",
            "btn_add_target": "➕ Add Target",
            "btn_refresh": "🔄 Refresh",
            "btn_view_all": "📋 View All",
            "btn_previous": "⬅️ Previous",
            "btn_next": "Next ➡️",
            "btn_new_task": "➕ New Task",
            
            # Settings Buttons
            "btn_bot_settings": "🤖 Bot Settings",
            "btn_user_settings": "👤 User Settings", 
            "btn_system": "🔧 System",
            "btn_statistics": "📊 Statistics",
            "btn_back_to_menu": "🔙 Back to Menu",
            "btn_enable": "✅ Enable",
            "btn_disable": "❌ Disable",
            
            # Admin Buttons
            "btn_users": "👥 Users",
            "btn_admin_stats": "📊 Statistics",
            "btn_maintenance": "🔧 Maintenance", 
            "btn_logs": "📋 Logs",
            "btn_security": "🛡️ Security",
            
            # Media Type Buttons
            "btn_media_photos": "Photos",
            "btn_media_videos": "Videos",
            "btn_media_documents": "Documents", 
            "btn_media_audio": "Audio",
            "btn_media_voice": "Voice Messages",
            "btn_media_video_notes": "Video Notes",
            "btn_media_stickers": "Stickers",
            "btn_media_animations": "GIFs",
            "btn_media_contacts": "Contacts",
            "btn_media_locations": "Locations",
            "btn_media_venues": "Venues",
            "btn_media_polls": "Polls",
            "btn_media_dice": "Dice",
        }
        
        # Arabic translations
        self.languages["ar"] = {
            # Main menu
            "main_menu": "🏠 **القائمة الرئيسية**",
            "welcome_message": "مرحباً {name}! أنا بوت توجيه رسائل تليجرام.",
            "help_text": """
🤖 **مساعدة بوت توجيه رسائل تليجرام**

**الأوامر المتاحة:**
• /start - بدء تشغيل البوت
• /help - عرض رسالة المساعدة
• /menu - القائمة الرئيسية
• /status - حالة البوت
• /userbot - حالة اليوزربوت

**المميزات:**
• إنشاء مهام التوجيه
• تصفية المحتوى المتقدمة
• تنظيف وتعديل النصوص
• دعم متعدد اللغات
• مراقبة فورية

اختر لغتك المفضلة من قائمة الإعدادات.
            """,
            
            # Buttons
            "btn_tasks": "📋 المهام",
            "btn_settings": "⚙️ الإعدادات",
            "btn_statistics": "📊 الإحصائيات",
            "btn_help": "❓ المساعدة",
            "btn_language": "🌐 اللغة",
            "btn_back": "🔙 رجوع",
            "btn_cancel": "❌ إلغاء",
            "btn_confirm": "✅ تأكيد",
            "btn_save": "💾 حفظ",
            "btn_reset": "🔄 إعادة تعيين",
            "btn_delete": "🗑️ حذف",
            "btn_edit": "✏️ تعديل",
            "btn_view": "👁️ عرض",
            "btn_create": "➕ إنشاء",
            "btn_manage": "🔧 إدارة",
            
            # Task Management
            "task_list": "📋 **قائمة المهام**",
            "task_create": "➕ **إنشاء مهمة جديدة**",
            "task_settings": "⚙️ **إعدادات المهمة**",
            "task_name": "اسم المهمة",
            "task_description": "الوصف",
            "task_status": "الحالة",
            "task_active": "نشط",
            "task_inactive": "غير نشط",
            "no_tasks": "لا توجد مهام. أنشئ مهمتك الأولى!",
            
            # Settings Categories
            "setting_filters": "🔽 المرشحات",
            "setting_content": "✏️ المحتوى",
            "setting_forward": "📡 التوجيه",
            "setting_limits": "⏱️ الحدود",
            "setting_advanced": "⚡ متقدم",
            "setting_view_all": "📋 عرض الكل",
            
            # Forward Settings
            "forward_mode": "🔄 وضع التوجيه",
            "forward_copy": "📋 نسخ",
            "forward_forward": "➡️ توجيه",
            "forward_quote": "💬 اقتباس",
            "manual_mode": "الوضع اليدوي",
            "link_preview": "معاينة الروابط",
            "pin_messages": "تثبيت الرسائل",
            "silent_mode": "الوضع الصامت",
            "sync_edits": "مزامنة التعديل",
            "sync_deletes": "مزامنة الحذف",
            "preserve_replies": "الحفاظ على الردود",
            
            # Limits Settings
            "limits_title": "⏱️ **إعدادات الحدود**",
            "message_delays": "⏱️ تأخير الرسائل",
            "send_limits": "📊 حدود الإرسال",
            "length_limit": "📏 حد الطول",
            "time_limits": "⏰ حدود الوقت",
            "delay_current": "التأخير الحالي: **{min}-{max} ثانية**",
            "send_limit_current": "حد الإرسال: {limit} رسالة/ساعة",
            "length_limit_current": "حد الطول: {limit} حرف",
            "unlimited": "غير محدود",
            "no_limit": "بلا حد",
            
            # Content Settings
            "content_settings": "✏️ **إعدادات المحتوى**",
            "text_cleaner": "🧹 منظف النصوص",
            "text_replace": "🔄 استبدال النص",
            "prefix_suffix": "📝 بادئة/لاحقة",
            "formatting": "📄 التنسيق",
            
            # Text Cleaner
            "cleaner_title": "🧹 **إعدادات منظف النصوص**",
            "cleaner_remove_emojis": "😀 إزالة الرموز التعبيرية",
            "cleaner_remove_links": "🔗 إزالة الروابط", 
            "cleaner_remove_mentions": "👤 إزالة الإشارات",
            "cleaner_remove_emails": "📧 إزالة الإيميلات",
            "cleaner_remove_hashtags": "# إزالة الهاشتاغ",
            "cleaner_remove_numbers": "🔢 إزالة الأرقام",
            "cleaner_remove_punctuation": ".,!? إزالة علامات الترقيم",
            "cleaner_remove_empty_lines": "📝 إزالة الأسطر الفارغة",
            "cleaner_remove_extra_lines": "📃 إزالة الأسطر الزائدة",
            "cleaner_normalize_whitespace": "⬜ تطبيع المسافات",
            "cleaner_remove_duplicates": "🔄 إزالة الأسطر المكررة",
            "cleaner_target_words": "🎯 حذف الأسطر بكلمات معينة",
            "cleaner_manage_words": "✏️ إدارة الكلمات المستهدفة",
            "cleaner_test": "🧪 اختبار التنظيف",
            
            # Advanced Settings
            "advanced_settings": "⚡ **الإعدادات المتقدمة**",
            "advanced_translation": "🌐 إعدادات الترجمة",
            "advanced_working_hours": "⏰ ساعات العمل",
            "advanced_recurring": "🔄 المنشورات المتكررة",
            
            # Working Hours Settings
            "working_hours_title": "⏰ **إعدادات ساعات العمل**",
            "working_hours_enabled": "✅ ساعات العمل مفعلة",
            "working_hours_disabled": "❌ ساعات العمل معطلة",
            "start_hour": "🕐 ساعة البداية",
            "end_hour": "🕕 ساعة النهاية",
            "current_timezone": "🌍 المنطقة الزمنية الحالية",
            "set_timezone": "🌍 تعيين المنطقة الزمنية",
            "set_start_hour": "🕐 تعيين ساعة البداية",
            "set_end_hour": "🕕 تعيين ساعة النهاية",
            "working_days": "📅 أيام العمل",
            "breaks_settings": "☕ إعدادات فترات الراحة",
            "test_current_time": "⏰ اختبار الوقت الحالي",
            "working_hours_report": "📊 تقرير ساعات العمل",
            
            # Translation Settings
            "translation_title": "🌐 **إعدادات الترجمة**",
            "auto_translate": "🔄 الترجمة التلقائية",
            "translation_enabled": "✅ الترجمة مفعلة",
            "translation_disabled": "❌ الترجمة معطلة",
            "target_language": "🎯 اللغة المستهدفة",
            "source_language": "📝 اللغة المصدر",
            "translation_api": "🔧 واجهة برمجة الترجمة",
            "translate_to_arabic": "🇸🇦 ترجمة إلى العربية",
            "translate_to_english": "🇺🇸 ترجمة إلى الإنجليزية",
            "translation_test": "🧪 اختبار الترجمة",
            
            # User Filter Settings
            "user_filter_title": "👥 **إعدادات فلتر المستخدمين**",
            "filter_verified_users": "✅ فلترة المستخدمين المحققين",
            # "filter_bots": "🤖 فلترة البوتات",  # Removed - not implemented
            "user_whitelist": "✅ القائمة البيضاء للمستخدمين",
            "user_blacklist": "❌ القائمة السوداء للمستخدمين",
            "manage_users": "👥 إدارة المستخدمين",
            "add_user": "➕ إضافة مستخدم",
            "remove_user": "➖ حذف مستخدم",
            
            # Recurring Posts
            "recurring_title": "🔄 **إعدادات المنشورات المتكررة**",
            "recurring_enabled": "✅ المنشورات المتكررة مفعلة",
            "recurring_disabled": "❌ المنشورات المتكررة معطلة",
            "recurring_content": "📝 محتوى المنشور المتكرر",
            "recurring_interval": "⏱️ فاصل زمني للتكرار",
            "recurring_test": "🧪 اختبار المنشور المتكرر",
            
            # Language Settings
            "language_settings": "🌐 **إعدادات اللغة**",
            "current_language": "اللغة الحالية: **{lang}**",
            "select_language": "اختر لغتك المفضلة:",
            "language_english": "🇺🇸 English",
            "language_arabic": "🇸🇦 العربية",
            "language_changed": "تم تغيير اللغة إلى {lang}",
            
            # Status Messages
            "status_enabled": "✅ مفعل",
            "status_disabled": "❌ معطل",
            "status_active": "🟢 نشط",
            "status_inactive": "🔴 غير نشط",
            "status_success": "✅ نجح",
            "status_error": "❌ خطأ",
            "status_warning": "⚠️ تحذير",
            
            # Common Messages
            "access_denied": "❌ تم رفض الوصول.",
            "error_loading": "❌ خطأ في تحميل الإعدادات.",
            "settings_saved": "✅ تم حفظ الإعدادات بنجاح!",
            "operation_completed": "✅ تمت العملية بنجاح.",
            "please_wait": "⏳ الرجاء الانتظار...",
            "processing": "🔄 جاري المعالجة...",
            "back_to_main": "🔙 العودة للقائمة الرئيسية",
            "back_to_settings": "🔙 العودة للإعدادات",
            
            # Task Status Messages
            "task_activated": "✅ تم تفعيل المهمة بنجاح!",
            "task_deactivated": "⏹️ تم إيقاف المهمة بنجاح!",
            "task_deleted": "🗑️ تم حذف المهمة بنجاح!",
            "task_created": "✅ تم إنشاء المهمة بنجاح!",
            "task_updated": "✅ تم تحديث المهمة بنجاح!",
            "task_not_found": "❌ لم يتم العثور على المهمة.",
            "invalid_task_data": "❌ بيانات المهمة غير صالحة.",
            "operation_failed": "❌ فشلت العملية.",
            "confirmation_required": "⚠️ هل أنت متأكد؟",
            "cancelled": "❌ تم إلغاء العملية.",
            
            # Timezone Names
            "timezone_mecca": "🕌 مكة المكرمة",
            "timezone_cairo": "🏛️ القاهرة",
            "timezone_utc": "🌍 التوقيت العالمي",
            "timezone_newyork": "🗽 نيويورك",
            "timezone_london": "🏰 لندن",
            "timezone_paris": "🗼 باريس",
            "timezone_tokyo": "🏙️ طوكيو",
            "timezone_moscow": "🏛️ موسكو",
            
            # Days of Week
            "monday": "الاثنين",
            "tuesday": "الثلاثاء", 
            "wednesday": "الأربعاء",
            "thursday": "الخميس",
            "friday": "الجمعة",
            "saturday": "السبت",
            "sunday": "الأحد",
            
            # Time Formats
            "current_time": "الوقت الحالي: {time}",
            "working_hours_format": "من {start} إلى {end}",
            "timezone_format": "المنطقة الزمنية: {timezone}",
            
            # Additional UI Elements  
            "select_option": "اختر خياراً:",
            "system_status": "🔄 حالة النظام",
            "detailed_report": "📈 تقرير مفصل",
            "quick_start": "🚀 بدء سريع", 
            "advanced_tools": "🔧 أدوات متقدمة",
            
            # Additional task management
            "import_task": "📥 استيراد مهمة",
            "export_tasks": "📤 تصدير المهام",
            "start_all_tasks": "🎯 بدء جميع المهام", 
            "stop_all_tasks": "⏹️ إيقاف جميع المهام",
            
            # Task Management Buttons
            "btn_activate": "▶️ تفعيل",
            "btn_deactivate": "⏹️ إيقاف",
            "btn_edit_task": "✏️ تعديل",
            "btn_task_stats": "📊 الإحصائيات",
            "btn_task_settings": "⚙️ الإعدادات",
            "btn_sources": "📥 المصادر",
            "btn_targets": "📤 الأهداف",
            "btn_delete_task": "🗑️ حذف",
            "btn_task_info": "📋 المعلومات",
            "btn_back_to_tasks": "🔙 العودة للمهام",
            "btn_add_source": "➕ إضافة مصدر",
            "btn_add_target": "➕ إضافة هدف",
            "btn_refresh": "🔄 تحديث",
            "btn_view_all": "📋 عرض الكل",
            "btn_previous": "⬅️ السابق",
            "btn_next": "التالي ➡️",
            "btn_new_task": "➕ مهمة جديدة",
            
            # Settings Buttons
            "btn_bot_settings": "🤖 إعدادات البوت",
            "btn_user_settings": "👤 إعدادات المستخدم",
            "btn_system": "🔧 النظام",
            "btn_statistics": "📊 الإحصائيات", 
            "btn_back_to_menu": "🔙 العودة للقائمة",
            "btn_enable": "✅ تفعيل",
            "btn_disable": "❌ تعطيل",
            
            # Admin Buttons
            "btn_users": "👥 المستخدمين",
            "btn_admin_stats": "📊 الإحصائيات",
            "btn_maintenance": "🔧 الصيانة",
            "btn_logs": "📋 السجلات", 
            "btn_security": "🛡️ الأمان",
            
            # Media Type Buttons  
            "btn_media_photos": "الصور",
            "btn_media_videos": "الفيديوهات",
            "btn_media_documents": "المستندات",
            "btn_media_audio": "الصوتيات", 
            "btn_media_voice": "الرسائل الصوتية",
            "btn_media_video_notes": "الفيديوهات الدائرية",
            "btn_media_stickers": "الملصقات",
            "btn_media_animations": "الصور المتحركة",
            "btn_media_contacts": "جهات الاتصال",
            "btn_media_locations": "المواقع",
            "btn_media_venues": "الأماكن",
            "btn_media_polls": "الاستطلاعات",
            "btn_media_dice": "النرد",
        }
        
        logger.info("Localization system initialized with Arabic and English support")
    
    def set_user_language(self, user_id: int, language: str):
        """Set user's preferred language"""
        if language in self.languages:
            self.user_languages[user_id] = language
            logger.info(f"User {user_id} language set to {language}")
            return True
        return False
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        return self.user_languages.get(user_id, self.default_language)
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get localized text for user"""
        language = self.get_user_language(user_id)
        
        if language in self.languages and key in self.languages[language]:
            text = self.languages[language][key]
            try:
                return text.format(**kwargs) if kwargs else text
            except KeyError as e:
                logger.warning(f"Missing format parameter {e} for key {key}")
                return text
        
        # Fallback to default language
        if key in self.languages[self.default_language]:
            text = self.languages[self.default_language][key]
            try:
                return text.format(**kwargs) if kwargs else text
            except KeyError:
                return text
        
        # Last resort fallback
        logger.warning(f"Missing translation key: {key}")
        return key
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages"""
        return {
            "en": "🇺🇸 English",
            "ar": "🇸🇦 العربية"
        }
    
    def get_language_name(self, lang_code: str) -> str:
        """Get language display name"""
        lang_names = {
            "en": "English",
            "ar": "العربية"
        }
        return lang_names.get(lang_code, lang_code)
    
    def t(self, user_id: int, key: str, **kwargs) -> str:
        """Shorthand for get_text - easier to use in code"""
        return self.get_text(user_id, key, **kwargs)
    
    def get_all_keys(self, language: str = None) -> list:
        """Get all available translation keys for debugging"""
        if language and language in self.languages:
            return list(self.languages[language].keys())
        return list(self.languages[self.default_language].keys())

# Global instance
localization = LocalizationManager()

# Convenience function for global access
def _(user_id: int, key: str, **kwargs) -> str:
    """Global shorthand function for translations"""
    return localization.get_text(user_id, key, **kwargs)