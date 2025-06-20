"""
Statistics Manager - Handles statistical data and reporting
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from loguru import logger

from database import Database
from utils import format_number, format_duration


class StatisticsManager:
    """Manages statistical data collection and reporting"""
    
    def __init__(self, database: Database):
        self.database = database
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = None
        
    async def initialize(self):
        """Initialize statistics manager"""
        try:
            await self._update_cache()
            logger.success("Statistics manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize statistics manager: {e}")
            raise
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global bot statistics"""
        try:
            # Check cache
            if await self._is_cache_valid("global"):
                return self.cache.get("global", {})
            
            # Database queries for global stats
            queries = {
                "total_users": "SELECT COUNT(*) as count FROM users",
                "active_users": "SELECT COUNT(*) as count FROM users WHERE is_active = true",
                "admin_users": "SELECT COUNT(*) as count FROM users WHERE is_admin = true",
                "total_tasks": "SELECT COUNT(*) as count FROM tasks",
                "active_tasks": "SELECT COUNT(*) as count FROM tasks WHERE is_active = true",
                "total_sources": "SELECT COUNT(*) as count FROM sources",
                "total_targets": "SELECT COUNT(*) as count FROM targets",
                "total_messages": "SELECT COUNT(*) as count FROM forwarding_logs",
                "successful_messages": "SELECT COUNT(*) as count FROM forwarding_logs WHERE status = 'success'",
                "failed_messages": "SELECT COUNT(*) as count FROM forwarding_logs WHERE status = 'failed'",
                "messages_today": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE DATE(processed_at) = CURRENT_DATE
                """,
                "messages_this_week": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE processed_at >= CURRENT_DATE - INTERVAL '7 days'
                """,
                "messages_this_month": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE processed_at >= CURRENT_DATE - INTERVAL '30 days'
                """
            }
            
            stats = {}
            for key, query in queries.items():
                try:
                    result = await self.database.execute_query(query)
                    stats[key] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.error(f"Error executing query for {key}: {e}")
                    stats[key] = 0
            
            # Calculate derived statistics
            stats["success_rate"] = (
                (stats["successful_messages"] / stats["total_messages"] * 100) 
                if stats["total_messages"] > 0 else 0
            )
            
            stats["avg_messages_per_task"] = (
                (stats["total_messages"] / stats["total_tasks"])
                if stats["total_tasks"] > 0 else 0
            )
            
            # Cache the results
            self.cache["global"] = stats
            self.cache["global_timestamp"] = datetime.now()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting global statistics: {e}")
            return {}
    
    async def get_task_statistics(self, task_id: int) -> Dict[str, Any]:
        """Get statistics for a specific task"""
        try:
            cache_key = f"task_{task_id}"
            
            # Check cache
            if await self._is_cache_valid(cache_key):
                return self.cache.get(cache_key, {})
            
            # Get task statistics from database
            task_stats = await self.database.get_task_statistics(task_id)
            if not task_stats:
                return {}
            
            # Get additional statistics
            additional_queries = {
                "messages_today": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE task_id = $1 AND DATE(processed_at) = CURRENT_DATE
                """,
                "messages_this_week": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE task_id = $1 AND processed_at >= CURRENT_DATE - INTERVAL '7 days'
                """,
                "avg_processing_time": """
                    SELECT AVG(processing_time) as avg_time FROM forwarding_logs 
                    WHERE task_id = $1 AND processing_time IS NOT NULL
                """,
                "last_successful_forward": """
                    SELECT processed_at FROM forwarding_logs 
                    WHERE task_id = $1 AND status = 'success' 
                    ORDER BY processed_at DESC LIMIT 1
                """,
                "error_types": """
                    SELECT error_message, COUNT(*) as count 
                    FROM forwarding_logs 
                    WHERE task_id = $1 AND status = 'failed' AND error_message IS NOT NULL
                    GROUP BY error_message 
                    ORDER BY count DESC LIMIT 5
                """
            }
            
            additional_stats = {}
            for key, query in additional_queries.items():
                try:
                    result = await self.database.execute_query(query, task_id)
                    if key == "error_types":
                        additional_stats[key] = result
                    elif result:
                        additional_stats[key] = result[0].get("count") or result[0].get("avg_time") or result[0].get("processed_at")
                    else:
                        additional_stats[key] = None
                except Exception as e:
                    logger.error(f"Error executing query for {key}: {e}")
                    additional_stats[key] = None
            
            # Combine statistics
            combined_stats = {**task_stats, **additional_stats}
            
            # Calculate derived statistics
            total_messages = combined_stats.get("messages_processed", 0)
            successful_messages = combined_stats.get("messages_forwarded", 0)
            
            combined_stats["success_rate"] = (
                (successful_messages / total_messages * 100) 
                if total_messages > 0 else 0
            )
            
            # Cache the results
            self.cache[cache_key] = combined_stats
            self.cache[f"{cache_key}_timestamp"] = datetime.now()
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"Error getting task statistics for {task_id}: {e}")
            return {}
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        try:
            cache_key = f"user_{user_id}"
            
            # Check cache
            if await self._is_cache_valid(cache_key):
                return self.cache.get(cache_key, {})
            
            # Get user statistics
            user_queries = {
                "total_tasks": """
                    SELECT COUNT(*) as count FROM tasks t
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """,
                "active_tasks": """
                    SELECT COUNT(*) as count FROM tasks t
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1 AND t.is_active = true
                """,
                "total_sources": """
                    SELECT COUNT(*) as count FROM sources s
                    JOIN tasks t ON s.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """,
                "total_targets": """
                    SELECT COUNT(*) as count FROM targets tg
                    JOIN tasks t ON tg.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """,
                "total_messages": """
                    SELECT COUNT(*) as count FROM forwarding_logs fl
                    JOIN tasks t ON fl.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """,
                "successful_messages": """
                    SELECT COUNT(*) as count FROM forwarding_logs fl
                    JOIN tasks t ON fl.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1 AND fl.status = 'success'
                """,
                "messages_today": """
                    SELECT COUNT(*) as count FROM forwarding_logs fl
                    JOIN tasks t ON fl.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1 AND DATE(fl.processed_at) = CURRENT_DATE
                """,
                "first_activity": """
                    SELECT MIN(created_at) as first_date FROM tasks t
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """,
                "last_activity": """
                    SELECT MAX(fl.processed_at) as last_date FROM forwarding_logs fl
                    JOIN tasks t ON fl.task_id = t.id
                    JOIN users u ON t.user_id = u.id
                    WHERE u.telegram_id = $1
                """
            }
            
            stats = {}
            for key, query in user_queries.items():
                try:
                    result = await self.database.execute_query(query, user_id)
                    if key in ["first_activity", "last_activity"]:
                        stats[key] = result[0].get("first_date") or result[0].get("last_date") if result else None
                    else:
                        stats[key] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.error(f"Error executing user query for {key}: {e}")
                    stats[key] = 0 if key not in ["first_activity", "last_activity"] else None
            
            # Calculate derived statistics with safe division
            total_msgs = stats.get("total_messages", 0) or 0
            successful_msgs = stats.get("successful_messages", 0) or 0
            total_tasks = stats.get("total_tasks", 0) or 0
            
            stats["success_rate"] = (
                (successful_msgs / total_msgs * 100)
                if total_msgs > 0 else 0
            )
            
            stats["avg_messages_per_task"] = (
                (total_msgs / total_tasks)
                if total_tasks > 0 else 0
            )
            
            # Cache the results
            self.cache[cache_key] = stats
            self.cache[f"{cache_key}_timestamp"] = datetime.now()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics for {user_id}: {e}")
            return {}
    
    async def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        try:
            # Performance queries
            perf_queries = {
                "avg_processing_time": """
                    SELECT AVG(processing_time) as avg_time FROM forwarding_logs 
                    WHERE processing_time IS NOT NULL
                """,
                "max_processing_time": """
                    SELECT MAX(processing_time) as max_time FROM forwarding_logs 
                    WHERE processing_time IS NOT NULL
                """,
                "min_processing_time": """
                    SELECT MIN(processing_time) as min_time FROM forwarding_logs 
                    WHERE processing_time IS NOT NULL AND processing_time > 0
                """,
                "messages_per_hour": """
                    SELECT COUNT(*) / 
                    GREATEST(EXTRACT(EPOCH FROM (MAX(processed_at) - MIN(processed_at))) / 3600, 1) as rate
                    FROM forwarding_logs 
                    WHERE processed_at >= NOW() - INTERVAL '24 hours'
                """,
                "error_rate": """
                    SELECT 
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 / COUNT(*) as error_rate
                    FROM forwarding_logs 
                    WHERE processed_at >= NOW() - INTERVAL '24 hours'
                """,
                "peak_hour": """
                    SELECT EXTRACT(HOUR FROM processed_at) as hour, COUNT(*) as count
                    FROM forwarding_logs 
                    WHERE processed_at >= NOW() - INTERVAL '7 days'
                    GROUP BY EXTRACT(HOUR FROM processed_at)
                    ORDER BY count DESC
                    LIMIT 1
                """
            }
            
            stats = {}
            for key, query in perf_queries.items():
                try:
                    result = await self.database.execute_query(query)
                    if key == "peak_hour":
                        if result:
                            stats["peak_hour"] = int(result[0]["hour"])
                            stats["peak_hour_count"] = result[0]["count"]
                        else:
                            stats["peak_hour"] = None
                            stats["peak_hour_count"] = 0
                    else:
                        value = result[0][list(result[0].keys())[0]] if result else 0
                        stats[key] = float(value) if value is not None else 0
                except Exception as e:
                    logger.error(f"Error executing performance query for {key}: {e}")
                    stats[key] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting performance statistics: {e}")
            return {}
    
    async def get_trending_data(self, days: int = 7) -> Dict[str, Any]:
        """Get trending data for charts"""
        try:
            # Daily message counts
            daily_query = """
                SELECT 
                    DATE(processed_at) as date,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_messages,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_messages
                FROM forwarding_logs 
                WHERE processed_at >= CURRENT_DATE - INTERVAL '{} days'
                GROUP BY DATE(processed_at)
                ORDER BY date
            """.format(days)
            
            daily_data = await self.database.execute_query(daily_query)
            
            # Hourly distribution
            hourly_query = """
                SELECT 
                    EXTRACT(HOUR FROM processed_at) as hour,
                    COUNT(*) as message_count
                FROM forwarding_logs 
                WHERE processed_at >= NOW() - INTERVAL '{} days'
                GROUP BY EXTRACT(HOUR FROM processed_at)
                ORDER BY hour
            """.format(days)
            
            hourly_data = await self.database.execute_query(hourly_query)
            
            # Task performance
            task_perf_query = """
                SELECT 
                    t.name,
                    COUNT(fl.*) as total_messages,
                    COUNT(CASE WHEN fl.status = 'success' THEN 1 END) as successful_messages,
                    AVG(fl.processing_time) as avg_processing_time
                FROM tasks t
                LEFT JOIN forwarding_logs fl ON t.id = fl.task_id
                WHERE fl.processed_at >= NOW() - INTERVAL '{} days' OR fl.processed_at IS NULL
                GROUP BY t.id, t.name
                ORDER BY total_messages DESC
                LIMIT 10
            """.format(days)
            
            task_data = await self.database.execute_query(task_perf_query)
            
            return {
                "daily_data": daily_data,
                "hourly_data": hourly_data,
                "task_performance": task_data
            }
            
        except Exception as e:
            logger.error(f"Error getting trending data: {e}")
            return {"daily_data": [], "hourly_data": [], "task_performance": []}
    
    async def update_engine_stats(self, engine_stats: Dict[str, Any]):
        """Update engine statistics"""
        try:
            self.cache["engine"] = engine_stats
            self.cache["engine_timestamp"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating engine stats: {e}")
    
    async def get_formatted_statistics(self, stat_type: str, identifier: Any = None) -> str:
        """Get formatted statistics text"""
        try:
            if stat_type == "global":
                stats = await self.get_global_statistics()
                return self._format_global_stats(stats)
            elif stat_type == "task" and identifier:
                stats = await self.get_task_statistics(identifier)
                return self._format_task_stats(stats, identifier)
            elif stat_type == "user" and identifier:
                stats = await self.get_user_statistics(identifier)
                return self._format_user_stats(stats, identifier)
            elif stat_type == "performance":
                stats = await self.get_performance_statistics()
                return self._format_performance_stats(stats)
            else:
                return "❌ Invalid statistics type"
                
        except Exception as e:
            logger.error(f"Error getting formatted statistics: {e}")
            return "❌ Error loading statistics"
    
    def _format_global_stats(self, stats: Dict[str, Any]) -> str:
        """Format global statistics"""
        return f"""
📊 **Global Statistics**

**Users:**
• Total Users: {format_number(stats.get('total_users', 0))}
• Active Users: {format_number(stats.get('active_users', 0))}
• Admin Users: {format_number(stats.get('admin_users', 0))}

**Tasks:**
• Total Tasks: {format_number(stats.get('total_tasks', 0))}
• Active Tasks: {format_number(stats.get('active_tasks', 0))}
• Total Sources: {format_number(stats.get('total_sources', 0))}
• Total Targets: {format_number(stats.get('total_targets', 0))}

**Messages:**
• Total Messages: {format_number(stats.get('total_messages', 0))}
• Successful: {format_number(stats.get('successful_messages', 0))}
• Failed: {format_number(stats.get('failed_messages', 0))}
• Success Rate: {stats.get('success_rate', 0):.1f}%

**Activity:**
• Today: {format_number(stats.get('messages_today', 0))}
• This Week: {format_number(stats.get('messages_this_week', 0))}
• This Month: {format_number(stats.get('messages_this_month', 0))}
        """.strip()
    
    def _format_task_stats(self, stats: Dict[str, Any], task_id: int) -> str:
        """Format task statistics"""
        return f"""
📊 **Task Statistics** (ID: {task_id})

**Messages:**
• Total Processed: {format_number(stats.get('messages_processed', 0))}
• Successfully Forwarded: {format_number(stats.get('messages_forwarded', 0))}
• Failed: {format_number(stats.get('messages_failed', 0))}
• Filtered: {format_number(stats.get('messages_filtered', 0))}
• Duplicates: {format_number(stats.get('messages_duplicate', 0))}

**Performance:**
• Success Rate: {stats.get('success_rate', 0):.1f}%
• Avg Processing Time: {stats.get('avg_processing_time', 0):.0f}ms
• Total Processing Time: {format_duration(stats.get('total_processing_time', 0) // 1000)}

**Activity:**
• Today: {format_number(stats.get('messages_today', 0))}
• This Week: {format_number(stats.get('messages_this_week', 0))}
• Last Activity: {stats.get('last_activity').strftime('%Y-%m-%d %H:%M') if stats.get('last_activity') else 'Never'}
• First Message: {stats.get('first_message_at').strftime('%Y-%m-%d %H:%M') if stats.get('first_message_at') else 'Never'}
        """.strip()
    
    def _format_user_stats(self, stats: Dict[str, Any], user_id: int) -> str:
        """Format user statistics"""
        return f"""
📊 **Your Statistics**

**Tasks:**
• Total Tasks: {format_number(stats.get('total_tasks', 0))}
• Active Tasks: {format_number(stats.get('active_tasks', 0))}
• Total Sources: {format_number(stats.get('total_sources', 0))}
• Total Targets: {format_number(stats.get('total_targets', 0))}

**Messages:**
• Total Forwarded: {format_number(stats.get('total_messages', 0))}
• Successful: {format_number(stats.get('successful_messages', 0))}
• Success Rate: {stats.get('success_rate', 0):.1f}%
• Today: {format_number(stats.get('messages_today', 0))}

**Activity:**
• First Activity: {stats.get('first_activity').strftime('%Y-%m-%d') if stats.get('first_activity') else 'Never'}
• Last Activity: {stats.get('last_activity').strftime('%Y-%m-%d %H:%M') if stats.get('last_activity') else 'Never'}
• Avg Messages/Task: {stats.get('avg_messages_per_task', 0):.1f}
        """.strip()
    
    def _format_performance_stats(self, stats: Dict[str, Any]) -> str:
        """Format performance statistics"""
        return f"""
⚡ **Performance Statistics**

**Processing Times:**
• Average: {stats.get('avg_processing_time', 0):.0f}ms
• Maximum: {stats.get('max_processing_time', 0):.0f}ms
• Minimum: {stats.get('min_processing_time', 0):.0f}ms

**Throughput:**
• Messages/Hour: {stats.get('messages_per_hour', 0):.1f}
• Error Rate: {stats.get('error_rate', 0):.2f}%

**Peak Activity:**
• Peak Hour: {stats.get('peak_hour', 'N/A')}:00
• Peak Hour Messages: {format_number(stats.get('peak_hour_count', 0))}
        """.strip()
    
    async def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is valid"""
        if cache_key not in self.cache:
            return False
        
        timestamp_key = f"{cache_key}_timestamp"
        if timestamp_key not in self.cache:
            return False
        
        cache_age = datetime.now() - self.cache[timestamp_key]
        return cache_age.total_seconds() < self.cache_ttl
    
    async def _update_cache(self):
        """Update statistics cache"""
        try:
            # Update global statistics
            await self.get_global_statistics()
            
            self.last_cache_update = datetime.now()
            logger.debug("Statistics cache updated")
            
        except Exception as e:
            logger.error(f"Error updating statistics cache: {e}")
    
    async def clear_cache(self):
        """Clear statistics cache"""
        self.cache.clear()
        logger.info("Statistics cache cleared")
    
    async def generate_report(self, report_type: str = "daily") -> str:
        """Generate statistics report"""
        try:
            if report_type == "daily":
                stats = await self.get_trending_data(1)
                return self._format_daily_report(stats)
            elif report_type == "weekly":
                stats = await self.get_trending_data(7)
                return self._format_weekly_report(stats)
            elif report_type == "monthly":
                stats = await self.get_trending_data(30)
                return self._format_monthly_report(stats)
            else:
                return "❌ Invalid report type"
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "❌ Error generating report"
    
    def _format_daily_report(self, data: Dict[str, Any]) -> str:
        """Format daily report"""
        daily_data = data.get("daily_data", [])
        if not daily_data:
            return "📊 **Daily Report**\n\nNo data available for today."
        
        today_data = daily_data[-1] if daily_data else {}
        
        return f"""
📊 **Daily Report** - {today_data.get('date', 'Today')}

**Messages:**
• Total: {format_number(today_data.get('total_messages', 0))}
• Successful: {format_number(today_data.get('successful_messages', 0))}
• Failed: {format_number(today_data.get('failed_messages', 0))}
• Success Rate: {(today_data.get('successful_messages', 0) / max(today_data.get('total_messages', 1), 1) * 100):.1f}%
        """.strip()
    
    def _format_weekly_report(self, data: Dict[str, Any]) -> str:
        """Format weekly report"""
        daily_data = data.get("daily_data", [])
        
        total_messages = sum(day.get("total_messages", 0) for day in daily_data)
        successful_messages = sum(day.get("successful_messages", 0) for day in daily_data)
        failed_messages = sum(day.get("failed_messages", 0) for day in daily_data)
        
        return f"""
📊 **Weekly Report** - Last 7 Days

**Summary:**
• Total Messages: {format_number(total_messages)}
• Successful: {format_number(successful_messages)}
• Failed: {format_number(failed_messages)}
• Success Rate: {(successful_messages / max(total_messages, 1) * 100):.1f}%
• Daily Average: {format_number(total_messages / 7):.0f}

**Daily Breakdown:**
{chr(10).join([f"• {day.get('date', 'N/A')}: {format_number(day.get('total_messages', 0))} messages" for day in daily_data[-7:]])}
        """.strip()
    
    def _format_monthly_report(self, data: Dict[str, Any]) -> str:
        """Format monthly report"""
        daily_data = data.get("daily_data", [])
        
        total_messages = sum(day.get("total_messages", 0) for day in daily_data)
        successful_messages = sum(day.get("successful_messages", 0) for day in daily_data)
        
        return f"""
📊 **Monthly Report** - Last 30 Days

**Summary:**
• Total Messages: {format_number(total_messages)}
• Successful: {format_number(successful_messages)}
• Daily Average: {format_number(total_messages / 30):.0f}
• Success Rate: {(successful_messages / max(total_messages, 1) * 100):.1f}%

**Trends:**
• Peak Day: {max(daily_data, key=lambda x: x.get('total_messages', 0)).get('date', 'N/A') if daily_data else 'N/A'}
• Active Days: {len([day for day in daily_data if day.get('total_messages', 0) > 0])}
        """.strip()
