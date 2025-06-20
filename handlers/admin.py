"""
Admin Handlers - Administrative functions and system management
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from database import Database
from security import SecurityManager


class AdminHandlers:
    """Handles administrative functions and system management"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.bot = bot_controller.bot
        self.database = bot_controller.database
        self.security_manager = bot_controller.security_manager
        self.keyboards = bot_controller.keyboards
        self.forwarding_engine = bot_controller.forwarding_engine
        
    async def register_handlers(self):
        """Register admin handlers"""
        try:
            # Admin handlers are called from bot_controller callback router
            logger.info("Admin handlers registered")
        except Exception as e:
            logger.error(f"Failed to register admin handlers: {e}")
            raise
    
    async def handle_callback(self, callback: CallbackQuery, state: FSMContext):
        """Handle admin callback queries"""
        data = callback.data
        user_id = callback.from_user.id
        
        try:
            # Verify admin access
            if not await self.security_manager.is_admin(user_id):
                await callback.answer("🚫 Admin access required.", show_alert=True)
                return
            
            if data == "admin_users":
                await self._handle_users_management(callback, state)
            elif data == "admin_stats":
                await self._handle_admin_statistics(callback, state)
            elif data == "admin_system":
                await self._handle_system_settings(callback, state)
            elif data == "admin_maintenance":
                await self._handle_maintenance(callback, state)
            elif data == "admin_logs":
                await self._handle_logs_viewer(callback, state)
            elif data == "admin_security":
                await self._handle_security_overview(callback, state)
            elif data == "admin_refresh":
                await self._handle_refresh(callback, state)
            elif data == "admin_bot_settings":
                await self._handle_bot_settings(callback, state)
            elif data == "admin_user_settings":
                await self._handle_user_settings(callback, state)
            elif data.startswith("admin_user_"):
                await self._handle_user_action(callback, state)
            elif data.startswith("admin_ban_"):
                await self._handle_ban_user(callback, state)
            elif data.startswith("admin_unban_"):
                await self._handle_unban_user(callback, state)
            elif data.startswith("admin_promote_"):
                await self._handle_promote_user(callback, state)
            elif data.startswith("admin_demote_"):
                await self._handle_demote_user(callback, state)
            elif data.startswith("admin_cleanup_"):
                await self._handle_cleanup_action(callback, state)
            elif data.startswith("admin_user_stats_"):
                await self._handle_user_stats(callback, state)
            elif data.startswith("admin_user_tasks_"):
                await self._handle_user_tasks(callback, state)
            else:
                await callback.answer("❌ Unknown admin action.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in admin callback {data}: {e}")
            await callback.answer("❌ An error occurred.", show_alert=True)
    
    async def _handle_users_management(self, callback: CallbackQuery, state: FSMContext):
        """Handle users management"""
        try:
            # Get user statistics
            users_stats = await self.database.execute_query("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
                    COUNT(CASE WHEN is_admin = true THEN 1 END) as admin_users,
                    COUNT(CASE WHEN last_activity > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_users
                FROM users
            """)
            
            stats = users_stats[0] if users_stats else {}
            
            # Get recent users
            recent_users = await self.database.execute_query("""
                SELECT telegram_id, username, first_name, is_admin, is_active, last_activity
                FROM users 
                ORDER BY last_activity DESC NULLS LAST
                LIMIT 10
            """)
            
            users_text = f"""
👥 **User Management**

**Statistics:**
• Total Users: {stats.get('total_users', 0)}
• Active Users: {stats.get('active_users', 0)}
• Admin Users: {stats.get('admin_users', 0)}
• Recent Activity (24h): {stats.get('recent_users', 0)}

**Recent Users:**
{self._format_user_list(recent_users)}
            """
            
            # Create user management keyboard
            keyboard = []
            
            # Recent users buttons (first 5)
            for user in recent_users[:5]:
                status_emoji = "🟢" if user["is_active"] else "🔴"
                admin_emoji = "👑" if user["is_admin"] else "👤"
                name = user["first_name"] or user["username"] or f"ID:{user['telegram_id']}"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji}{admin_emoji} {name[:20]}{'...' if len(name) > 20 else ''}",
                        callback_data=f"admin_user_{user['telegram_id']}"
                    )
                ])
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text="📊 Full Stats", callback_data="admin_user_stats"),
                    InlineKeyboardButton(text="🔍 Search User", callback_data="admin_user_search")
                ],
                [
                    InlineKeyboardButton(text="📋 Export Data", callback_data="admin_user_export"),
                    InlineKeyboardButton(text="🧹 Cleanup", callback_data="admin_user_cleanup")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_settings")
                ]
            ])
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(users_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in users management: {e}")
            await callback.answer("❌ Error loading users management.")
    
    async def _handle_admin_statistics(self, callback: CallbackQuery, state: FSMContext):
        """Handle admin statistics"""
        try:
            # Get comprehensive statistics
            stats_queries = {
                "system_stats": """
                    SELECT 
                        (SELECT COUNT(*) FROM users) as total_users,
                        (SELECT COUNT(*) FROM tasks) as total_tasks,
                        (SELECT COUNT(*) FROM tasks WHERE is_active = true) as active_tasks,
                        (SELECT COUNT(*) FROM forwarding_logs) as total_messages,
                        (SELECT COUNT(*) FROM forwarding_logs WHERE DATE(processed_at) = CURRENT_DATE) as messages_today
                """,
                "performance_stats": """
                    SELECT 
                        AVG(processing_time) as avg_processing_time,
                        MAX(processing_time) as max_processing_time,
                        COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
                    FROM forwarding_logs 
                    WHERE processed_at >= NOW() - INTERVAL '24 hours'
                """,
                "error_stats": """
                    SELECT status, COUNT(*) as count
                    FROM forwarding_logs 
                    WHERE processed_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY status
                    ORDER BY count DESC
                """
            }
            
            all_stats = {}
            for key, query in stats_queries.items():
                try:
                    result = await self.database.execute_query(query)
                    all_stats[key] = result
                except Exception as e:
                    logger.error(f"Error executing {key}: {e}")
                    all_stats[key] = []
            
            # Get engine statistics
            engine_stats = await self.forwarding_engine.get_stats()
            
            # Get security statistics
            security_stats = await self.security_manager.get_security_stats()
            
            system_data = all_stats["system_stats"][0] if all_stats["system_stats"] else {}
            perf_data = all_stats["performance_stats"][0] if all_stats["performance_stats"] else {}
            
            stats_text = f"""
📊 **Admin Statistics**

**System Overview:**
• Total Users: {system_data.get('total_users', 0)}
• Total Tasks: {system_data.get('total_tasks', 0)}
• Active Tasks: {system_data.get('active_tasks', 0)}
• Messages Today: {system_data.get('messages_today', 0)}
• Total Messages: {system_data.get('total_messages', 0)}

**Performance (24h):**
• Success Rate: {perf_data.get('success_rate', 0):.1f}%
• Avg Processing: {perf_data.get('avg_processing_time', 0):.0f}ms
• Max Processing: {perf_data.get('max_processing_time', 0):.0f}ms

**Forwarding Engine:**
• Status: {'🟢 Running' if engine_stats.get('running') else '🔴 Stopped'}
• Active Monitors: {engine_stats.get('active_monitors', 0)}
• Messages Processed: {engine_stats.get('messages_processed', 0)}
• Memory Usage: {engine_stats.get('memory_usage', 'Unknown')}

**Security:**
• Authorized Users: {security_stats.get('total_authorized_users', 0)}
• Active Sessions: {security_stats.get('active_sessions', 0)}
• Security Events (24h): {security_stats.get('security_events_24h', 0)}

**Status Distribution (24h):**
{self._format_status_distribution(all_stats["error_stats"])}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats"),
                    InlineKeyboardButton(text="📈 Detailed", callback_data="admin_stats_detailed")
                ],
                [
                    InlineKeyboardButton(text="📊 Export", callback_data="admin_stats_export"),
                    InlineKeyboardButton(text="📋 Report", callback_data="admin_stats_report")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_settings")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(stats_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in admin statistics: {e}")
            await callback.answer("❌ Error loading statistics.")
    
    async def _handle_system_settings(self, callback: CallbackQuery, state: FSMContext):
        """Handle system settings"""
        try:
            # Get system information
            from config import Config
            config = Config()
            
            # Get database health
            db_healthy = await self.database.health_check()
            
            # Get bot info
            bot_info = await self.bot.get_me()
            
            system_text = f"""
🔧 **System Settings**

**Bot Information:**
• Name: {bot_info.first_name}
• Username: @{bot_info.username}
• ID: `{bot_info.id}`

**Configuration:**
• Mode: {'Webhook' if config.use_webhook else 'Polling'}
• Userbot: {'✅ Enabled' if config.string_session else '❌ Disabled'}
• Database: {'🟢 Healthy' if db_healthy else '🔴 Unhealthy'}
• Admin Users: {len(config.admin_user_ids)}

**System Status:**
• Forwarding Engine: {'🟢 Running' if self.forwarding_engine.running else '🔴 Stopped'}
• Rate Limiting: ✅ Active
• Security: ✅ Active
• Logging: ✅ Active

**Performance:**
• Max Retries: {config.max_retries}
• Retry Delay: {config.retry_delay}s
• Rate Limit: {config.rate_limit_messages}/{config.rate_limit_period}s
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Toggle Mode", callback_data="admin_toggle_mode"),
                    InlineKeyboardButton(text="⚙️ Config", callback_data="admin_config")
                ],
                [
                    InlineKeyboardButton(text="🔧 Maintenance", callback_data="admin_maintenance"),
                    InlineKeyboardButton(text="🔄 Restart", callback_data="admin_restart_confirm")
                ],
                [
                    InlineKeyboardButton(text="📊 Health Check", callback_data="admin_health_check"),
                    InlineKeyboardButton(text="🧹 Cleanup", callback_data="admin_cleanup")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_settings")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(system_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in system settings: {e}")
            await callback.answer("❌ Error loading system settings.")
    
    async def _handle_maintenance(self, callback: CallbackQuery, state: FSMContext):
        """Handle maintenance operations"""
        try:
            # Get maintenance statistics
            maint_stats = await self.database.execute_query("""
                SELECT 
                    (SELECT COUNT(*) FROM forwarding_logs WHERE processed_at < NOW() - INTERVAL '30 days') as old_logs,
                    (SELECT COUNT(*) FROM user_sessions WHERE expires_at < NOW()) as expired_sessions,
                    (SELECT pg_size_pretty(pg_database_size(current_database()))) as db_size
            """)
            
            stats = maint_stats[0] if maint_stats else {}
            
            maintenance_text = f"""
🔧 **System Maintenance**

**Database Status:**
• Size: {stats.get('db_size', 'Unknown')}
• Old Logs (>30 days): {stats.get('old_logs', 0)}
• Expired Sessions: {stats.get('expired_sessions', 0)}

**Available Operations:**
• Clean old logs (>30 days)
• Remove expired sessions
• Optimize database
• Clear caches
• Reset statistics
• Backup data

**System Health:**
• Database: {'🟢 Healthy' if await self.database.health_check() else '🔴 Unhealthy'}
• Memory Usage: {self.forwarding_engine.get_stats().get('memory_usage', 'Unknown')}
• Uptime: {self.forwarding_engine.get_stats().get('uptime', 'Unknown')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🧹 Clean Logs", callback_data="admin_cleanup_logs"),
                    InlineKeyboardButton(text="🗑️ Clear Sessions", callback_data="admin_cleanup_sessions")
                ],
                [
                    InlineKeyboardButton(text="⚡ Optimize DB", callback_data="admin_optimize_db"),
                    InlineKeyboardButton(text="🔄 Clear Cache", callback_data="admin_clear_cache")
                ],
                [
                    InlineKeyboardButton(text="📊 Reset Stats", callback_data="admin_reset_stats_confirm"),
                    InlineKeyboardButton(text="💾 Backup", callback_data="admin_backup")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="admin_system")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(maintenance_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in maintenance: {e}")
            await callback.answer("❌ Error loading maintenance.")
    
    async def _handle_logs_viewer(self, callback: CallbackQuery, state: FSMContext):
        """Handle logs viewer"""
        try:
            # Get recent logs
            recent_logs = await self.database.execute_query("""
                SELECT 
                    fl.status,
                    fl.error_message,
                    fl.processed_at,
                    t.name as task_name,
                    fl.source_chat_id,
                    fl.target_chat_id
                FROM forwarding_logs fl
                JOIN tasks t ON fl.task_id = t.id
                ORDER BY fl.processed_at DESC
                LIMIT 10
            """)
            
            # Get error summary
            error_summary = await self.database.execute_query("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM forwarding_logs 
                WHERE processed_at >= NOW() - INTERVAL '24 hours'
                GROUP BY status
                ORDER BY count DESC
            """)
            
            logs_text = f"""
📋 **System Logs**

**Error Summary (24h):**
{self._format_status_distribution(error_summary)}

**Recent Activity:**
{self._format_recent_logs(recent_logs)}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_logs"),
                    InlineKeyboardButton(text="⚠️ Errors Only", callback_data="admin_logs_errors")
                ],
                [
                    InlineKeyboardButton(text="📊 Statistics", callback_data="admin_logs_stats"),
                    InlineKeyboardButton(text="📤 Export", callback_data="admin_logs_export")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_settings")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(logs_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in logs viewer: {e}")
            await callback.answer("❌ Error loading logs.")
    
    async def _handle_security_overview(self, callback: CallbackQuery, state: FSMContext):
        """Handle security overview"""
        try:
            # Get security statistics
            security_stats = await self.security_manager.get_security_stats()
            
            # Get recent security events (if available)
            recent_events = getattr(self.security_manager, 'security_events', [])[-10:]
            
            security_text = f"""
🛡️ **Security Overview**

**Access Control:**
• Authorized Users: {security_stats.get('total_authorized_users', 0)}
• Admin Users: {security_stats.get('total_admin_users', 0)}
• Banned Users: {security_stats.get('total_banned_users', 0)}
• Active Sessions: {security_stats.get('active_sessions', 0)}

**Activity (24h):**
• Security Events: {security_stats.get('security_events_24h', 0)}
• Rate Limited Users: {security_stats.get('rate_limited_users', 0)}

**Event Types (24h):**
{self._format_security_events(security_stats.get('event_types_24h', {}))}

**Recent Events:**
{self._format_recent_security_events(recent_events)}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_security"),
                    InlineKeyboardButton(text="⚠️ Alerts", callback_data="admin_security_alerts")
                ],
                [
                    InlineKeyboardButton(text="👥 User Access", callback_data="admin_users"),
                    InlineKeyboardButton(text="🔒 Permissions", callback_data="admin_permissions")
                ],
                [
                    InlineKeyboardButton(text="📊 Audit Log", callback_data="admin_audit_log"),
                    InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_security_settings")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="main_settings")
                ]
            ]
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(security_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in security overview: {e}")
            await callback.answer("❌ Error loading security overview.")
    
    async def _handle_ban_user(self, callback: CallbackQuery, state: FSMContext):
        """Handle user ban"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Update user status in database
            await self.database.execute_command(
                "UPDATE users SET is_active = false WHERE telegram_id = $1", user_id
            )
            
            # Update security manager
            await self.security_manager.ban_user(user_id)
            
            await callback.answer("✅ User banned successfully.", show_alert=True)
            
            # Refresh user list
            await self._handle_users_management(callback, state)
            
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await callback.answer("❌ Error banning user.")
    
    async def _handle_unban_user(self, callback: CallbackQuery, state: FSMContext):
        """Handle user unban"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Update user status in database
            await self.database.execute_command(
                "UPDATE users SET is_active = true WHERE telegram_id = $1", user_id
            )
            
            # Update security manager
            await self.security_manager.unban_user(user_id)
            
            await callback.answer("✅ User unbanned successfully.", show_alert=True)
            
            # Refresh user list
            await self._handle_users_management(callback, state)
            
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            await callback.answer("❌ Error unbanning user.")
    
    async def _handle_promote_user(self, callback: CallbackQuery, state: FSMContext):
        """Handle user promotion to admin"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Update user admin status in database
            await self.database.execute_command(
                "UPDATE users SET is_admin = true WHERE telegram_id = $1", user_id
            )
            
            # Update security manager
            await self.security_manager.promote_user(user_id)
            
            await callback.answer("✅ User promoted to admin successfully.", show_alert=True)
            
            # Refresh user list
            await self._handle_users_management(callback, state)
            
        except Exception as e:
            logger.error(f"Error promoting user: {e}")
            await callback.answer("❌ Error promoting user.")
    
    async def _handle_demote_user(self, callback: CallbackQuery, state: FSMContext):
        """Handle user demotion from admin"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Update user admin status in database
            await self.database.execute_command(
                "UPDATE users SET is_admin = false WHERE telegram_id = $1", user_id
            )
            
            # Update security manager
            await self.security_manager.demote_user(user_id)
            
            await callback.answer("✅ User demoted from admin successfully.", show_alert=True)
            
            # Refresh user list
            await self._handle_users_management(callback, state)
            
        except Exception as e:
            logger.error(f"Error demoting user: {e}")
            await callback.answer("❌ Error demoting user.")
    
    async def _handle_user_action(self, callback: CallbackQuery, state: FSMContext):
        """Handle individual user actions"""
        try:
            user_id = int(callback.data.split("_")[-1])
            
            # Get user information
            user_info = await self.database.get_user_by_id(user_id)
            if not user_info:
                await callback.answer("❌ User not found.")
                return
            
            # Get user statistics
            user_stats = await self.database.execute_query("""
                SELECT 
                    COUNT(t.*) as task_count,
                    COUNT(CASE WHEN t.is_active THEN 1 END) as active_tasks,
                    COUNT(fl.*) as total_messages,
                    MAX(fl.processed_at) as last_activity
                FROM users u
                LEFT JOIN tasks t ON u.id = t.user_id
                LEFT JOIN forwarding_logs fl ON t.id = fl.task_id
                WHERE u.telegram_id = $1
                GROUP BY u.id
            """, user_id)
            
            stats = user_stats[0] if user_stats else {}
            
            user_text = f"""
👤 **User Details**

**Information:**
• ID: `{user_info['telegram_id']}`
• Username: @{user_info['username'] or 'None'}
• Name: {user_info['first_name'] or ''} {user_info['last_name'] or ''}
• Status: {'🟢 Active' if user_info['is_active'] else '🔴 Inactive'}
• Role: {'👑 Admin' if user_info['is_admin'] else '👤 User'}
• Joined: {user_info['created_at'].strftime('%Y-%m-%d')}

**Activity:**
• Tasks: {stats.get('task_count', 0)} ({stats.get('active_tasks', 0)} active)
• Messages: {stats.get('total_messages', 0)}
• Last Activity: {stats.get('last_activity').strftime('%Y-%m-%d %H:%M') if stats.get('last_activity') else 'Never'}
            """
            
            keyboard = []
            
            # Admin actions
            if user_info['is_active']:
                keyboard.append([
                    InlineKeyboardButton(text="🚫 Ban User", callback_data=f"admin_ban_{user_id}"),
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(text="✅ Unban User", callback_data=f"admin_unban_{user_id}"),
                ])
            
            if user_info['is_admin']:
                keyboard.append([
                    InlineKeyboardButton(text="👤 Remove Admin", callback_data=f"admin_demote_{user_id}"),
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(text="👑 Make Admin", callback_data=f"admin_promote_{user_id}"),
                ])
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text="📊 User Stats", callback_data=f"admin_user_stats_{user_id}"),
                    InlineKeyboardButton(text="📋 User Tasks", callback_data=f"admin_user_tasks_{user_id}")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data="admin_users")
                ]
            ])
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(user_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in user action: {e}")
            await callback.answer("❌ Error loading user details.")
    
    async def _handle_cleanup_action(self, callback: CallbackQuery, state: FSMContext):
        """Handle cleanup actions"""
        try:
            action = callback.data.split("_")[-1]
            
            if action == "logs":
                # Clean old logs
                deleted_count = await self.database.cleanup_old_logs(30)
                await callback.answer(f"✅ Cleaned {deleted_count} old log entries.", show_alert=True)
                
            elif action == "sessions":
                # Clean expired sessions
                await self.security_manager.cleanup_expired_sessions()
                await callback.answer("✅ Expired sessions cleaned.", show_alert=True)
                
            elif action == "cache":
                # Clear caches
                await self.database.execute_query("SELECT pg_stat_reset()")
                await callback.answer("✅ Database statistics reset.", show_alert=True)
                
            # Refresh the maintenance view
            await self._handle_maintenance(callback, state)
            
        except Exception as e:
            logger.error(f"Error in cleanup action: {e}")
            await callback.answer("❌ Cleanup failed.", show_alert=True)
    
    async def _handle_user_stats(self, callback: CallbackQuery, state: FSMContext):
        """Handle user statistics view"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Get detailed user statistics
            user_stats = await self.statistics_manager.get_user_statistics(user_id)
            
            if not user_stats:
                await callback.answer("❌ No statistics found for this user.")
                return
            
            stats_text = f"""
📊 **User Statistics**

**Tasks:**
• Total: {user_stats.get('total_tasks', 0)}
• Active: {user_stats.get('active_tasks', 0)}

**Messages:**
• Total Processed: {user_stats.get('total_messages', 0)}
• Successfully Forwarded: {user_stats.get('successful_messages', 0)}
• Success Rate: {user_stats.get('success_rate', 0):.1f}%

**Activity:**
• First Activity: {user_stats.get('first_activity', 'N/A')}
• Last Activity: {user_stats.get('last_activity', 'N/A')}
• Avg Messages/Task: {user_stats.get('avg_messages_per_task', 0):.1f}
            """
            
            keyboard = [[
                InlineKeyboardButton(text="🔙 Back to User", callback_data=f"admin_user_{user_id}")
            ]]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(stats_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in user stats: {e}")
            await callback.answer("❌ Error loading user statistics.")
    
    async def _handle_user_tasks(self, callback: CallbackQuery, state: FSMContext):
        """Handle user tasks view"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            user_id = int(callback.data.split("_")[-1])
            
            # Get user tasks
            tasks = await self.database.execute_query("""
                SELECT t.id, t.name, t.description, t.is_active, t.created_at,
                       (SELECT COUNT(*) FROM forwarding_logs WHERE task_id = t.id) as message_count
                FROM tasks t 
                JOIN users u ON t.user_id = u.id
                WHERE u.telegram_id = $1
                ORDER BY t.created_at DESC
                LIMIT 10
            """, user_id)
            
            if not tasks:
                await callback.answer("❌ No tasks found for this user.")
                return
            
            tasks_text = f"📋 **User Tasks** ({len(tasks)} tasks)\n\n"
            
            for i, task in enumerate(tasks, 1):
                status = "🟢" if task['is_active'] else "🔴"
                tasks_text += f"{i}. {status} **{task['name']}**\n"
                tasks_text += f"   • Messages: {task['message_count']}\n"
                tasks_text += f"   • Created: {task['created_at'].strftime('%Y-%m-%d')}\n\n"
            
            keyboard = [[
                InlineKeyboardButton(text="🔙 Back to User", callback_data=f"admin_user_{user_id}")
            ]]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(tasks_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in user tasks: {e}")
            await callback.answer("❌ Error loading user tasks.")
    
    async def _handle_refresh(self, callback: CallbackQuery, state: FSMContext):
        """Handle refresh button"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Clear any caches
            await self.database.execute_query("SELECT pg_stat_reset()")
            logger.info("Admin panel refreshed by user")
            
            # Refresh admin panel
            keyboard = await self.keyboards.get_admin_keyboard(callback.from_user.id)
            
            await callback.message.edit_text(
                "🔄 **Admin Panel Refreshed**\n\nSelect an option:",
                reply_markup=keyboard
            )
            await callback.answer("✅ Panel refreshed successfully.")
            
        except Exception as e:
            logger.error(f"Error in refresh: {e}")
            await callback.answer("❌ Error refreshing panel.")
    
    async def _handle_bot_settings(self, callback: CallbackQuery, state: FSMContext):
        """Handle bot settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get current bot configuration
            config_summary = self.config.get_config_summary()
            
            settings_text = f"""
⚙️ **Bot Settings**

**Current Configuration:**
• Webhook Mode: {'Enabled' if config_summary.get('webhook_mode') else 'Disabled (Polling)'}
• Admin Users: {len(config_summary.get('admin_ids', []))}
• Bot Token: {'Configured' if config_summary.get('bot_token') else 'Missing'}
• Database: {'Connected' if config_summary.get('database_url') else 'Not Connected'}

**Actions:**
Select a setting to modify.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🔄 Toggle Webhook", callback_data="admin_toggle_webhook"),
                    InlineKeyboardButton(text="👥 Manage Admins", callback_data="admin_manage_admins")
                ],
                [
                    InlineKeyboardButton(text="🔧 Advanced Settings", callback_data="admin_advanced_settings"),
                    InlineKeyboardButton(text="📊 Bot Status", callback_data="admin_bot_status")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Admin", callback_data="main_admin")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(settings_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in bot settings: {e}")
            await callback.answer("❌ Error loading bot settings.")
    
    async def _handle_user_settings(self, callback: CallbackQuery, state: FSMContext):
        """Handle user settings"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get user statistics
            user_stats = await self.database.execute_query("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
                    COUNT(CASE WHEN is_admin = true THEN 1 END) as admin_users,
                    AVG(CASE WHEN last_activity IS NOT NULL THEN 1 ELSE 0 END) * 100 as activity_rate
                FROM users
            """)
            
            stats = user_stats[0] if user_stats else {}
            
            settings_text = f"""
👤 **User Settings**

**User Statistics:**
• Total Users: {stats.get('total_users', 0)}
• Active Users: {stats.get('active_users', 0)}
• Admin Users: {stats.get('admin_users', 0)}
• Activity Rate: {stats.get('activity_rate', 0):.1f}%

**Actions:**
Configure user-related settings and permissions.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(text="👥 View All Users", callback_data="admin_users"),
                    InlineKeyboardButton(text="🚫 Banned Users", callback_data="admin_banned_users")
                ],
                [
                    InlineKeyboardButton(text="👑 Admin Management", callback_data="admin_admin_management"),
                    InlineKeyboardButton(text="📊 User Analytics", callback_data="admin_user_analytics")
                ],
                [
                    InlineKeyboardButton(text="🔙 Back to Admin", callback_data="main_admin")
                ]
            ]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(settings_text, reply_markup=markup)
            
        except Exception as e:
            logger.error(f"Error in user settings: {e}")
            await callback.answer("❌ Error loading user settings.")
    
    def _format_user_list(self, users: List[Dict]) -> str:
        """Format user list for display"""
        if not users:
            return "No users found."
        
        formatted = []
        for user in users[:5]:  # Limit to 5 users
            status = "🟢" if user["is_active"] else "🔴"
            role = "👑" if user["is_admin"] else "👤"
            name = user["first_name"] or user["username"] or f"ID:{user['telegram_id']}"
            activity = "Never"
            
            if user["last_activity"]:
                activity = user["last_activity"].strftime("%m-%d %H:%M")
            
            formatted.append(f"{status}{role} {name[:20]} - {activity}")
        
        return "\n".join(formatted)
    
    def _format_status_distribution(self, status_data: List[Dict]) -> str:
        """Format status distribution"""
        if not status_data:
            return "No data available."
        
        formatted = []
        for item in status_data:
            status = item["status"]
            count = item["count"]
            emoji = {"success": "✅", "failed": "❌", "filtered": "🔽", "duplicate": "🔄"}.get(status, "❓")
            formatted.append(f"{emoji} {status.title()}: {count}")
        
        return "\n".join(formatted)
    
    def _format_recent_logs(self, logs: List[Dict]) -> str:
        """Format recent logs"""
        if not logs:
            return "No recent logs."
        
        formatted = []
        for log in logs[:5]:  # Limit to 5 logs
            status_emoji = {"success": "✅", "failed": "❌", "filtered": "🔽"}.get(log["status"], "❓")
            time_str = log["processed_at"].strftime("%H:%M")
            task_name = log["task_name"][:15] + "..." if len(log["task_name"]) > 15 else log["task_name"]
            
            formatted.append(f"{status_emoji} {time_str} - {task_name}")
            
            if log["error_message"] and log["status"] == "failed":
                error_short = log["error_message"][:40] + "..." if len(log["error_message"]) > 40 else log["error_message"]
                formatted.append(f"   └─ {error_short}")
        
        return "\n".join(formatted)
    
    def _format_security_events(self, events: Dict[str, int]) -> str:
        """Format security events"""
        if not events:
            return "No events."
        
        formatted = []
        for event_type, count in events.items():
            emoji = {
                "unauthorized_access": "🚫",
                "rate_limit_exceeded": "⚠️",
                "user_banned": "🔒",
                "admin_action": "👑",
                "session_created": "🔑"
            }.get(event_type, "📝")
            
            formatted.append(f"{emoji} {event_type.replace('_', ' ').title()}: {count}")
        
        return "\n".join(formatted)
    
    def _format_recent_security_events(self, events: List[Dict]) -> str:
        """Format recent security events"""
        if not events:
            return "No recent events."
        
        formatted = []
        for event in events[-5:]:  # Last 5 events
            time_str = event["timestamp"].strftime("%H:%M")
            event_type = event["event_type"].replace("_", " ").title()
            user_id = event["user_id"]
            
            formatted.append(f"• {time_str} - {event_type} (User: {user_id})")
        
        return "\n".join(formatted)
