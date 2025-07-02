"""
Task Manager - Handles task lifecycle and operations
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from loguru import logger

from database import Database
from utils import validate_forward_settings, generate_task_name


class TaskManager:
    """Manages forwarding tasks lifecycle and operations"""
    
    def __init__(self, database: Database):
        self.database = database
        self.task_cache: Dict[int, Dict[str, Any]] = {}
        self.cache_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize task manager"""
        try:
            await self._load_tasks_cache()
            logger.success("Task manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize task manager: {e}")
            raise
    
    async def create_task(self, user_id: int, task_data: Dict[str, Any]) -> Optional[int]:
        """Create a new forwarding task"""
        try:
            async with self.database.get_session() as session:
                # Validate task data
                task_name = task_data.get("name") or generate_task_name(0, 0)
                task_type = task_data.get("task_type", "bot")
                description = task_data.get("description", "")
                
                # Ensure user exists in database first
                user = await self.database.get_user_by_id(user_id)
                if not user:
                    # Create user if doesn't exist
                    user_data = {
                        "telegram_id": user_id,
                        "username": None,  # Will be set when available
                        "first_name": None,
                        "last_name": None,
                        "is_admin": False,
                        "is_active": True
                    }
                    user = await self.database.create_or_update_user(user_data)
                    if not user:
                        logger.error(f"Failed to create user {user_id}")
                        return None
                    logger.info(f"Created user {user_id} for task creation")
                
                # Create task using the user's database ID
                task_query = """
                    INSERT INTO tasks (user_id, name, description, task_type, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, false, NOW(), NOW())
                    RETURNING id
                """
                
                result = await self.database.execute_query(
                    task_query, user["id"], task_name, description, task_type
                )
                
                if not result:
                    logger.error("Failed to create task - no result returned")
                    return None
                
                task_id = result[0]["id"]
                
                # Create default settings
                await self._create_default_settings(task_id)
                
                # Create default statistics
                await self._create_default_statistics(task_id)
                
                # Update cache
                await self._refresh_task_cache(task_id)
                
                logger.info(f"Created task {task_id} for user {user_id}")
                return task_id
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
    
    async def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        try:
            async with self.cache_lock:
                if task_id in self.task_cache:
                    return self.task_cache[task_id].copy()
            
            # Load from database
            query = """
                SELECT t.*, u.telegram_id as user_telegram_id
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = $1
            """
            
            result = await self.database.execute_query(query, task_id)
            if result:
                task = result[0]
                async with self.cache_lock:
                    self.task_cache[task_id] = task
                return task
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def get_user_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all tasks for a user"""
        try:
            query = """
                SELECT t.*, 
                       COUNT(s.id) as source_count,
                       COUNT(target.id) as target_count,
                       ts.messages_forwarded,
                       ts.messages_failed,
                       ts.last_activity
                FROM tasks t
                LEFT JOIN sources s ON t.id = s.task_id
                LEFT JOIN targets target ON t.id = target.task_id
                LEFT JOIN task_statistics ts ON t.id = ts.task_id
                WHERE t.user_id = (SELECT id FROM users WHERE telegram_id = $1)
                GROUP BY t.id, ts.messages_forwarded, ts.messages_failed, ts.last_activity
                ORDER BY t.created_at DESC
            """
            
            return await self.database.execute_query(query, user_id)
            
        except Exception as e:
            logger.error(f"Error getting user tasks for {user_id}: {e}")
            return []
    
    async def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """Update task"""
        try:
            # Build update query
            update_fields = []
            values = []
            param_count = 1
            
            allowed_fields = ["name", "description", "task_type", "is_active"]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not update_fields:
                return False
            
            update_fields.append(f"updated_at = NOW()")
            values.append(task_id)
            
            query = f"""
                UPDATE tasks 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
            """
            
            await self.database.execute_command(query, *values)
            
            # Update cache
            await self._refresh_task_cache(task_id)
            
            logger.info(f"Updated task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    async def delete_task(self, task_id: int) -> bool:
        """Delete task and all related data"""
        try:
            # Delete in correct order due to foreign key constraints
            delete_queries = [
                "DELETE FROM forwarding_logs WHERE task_id = $1",
                "DELETE FROM task_statistics WHERE task_id = $1",
                "DELETE FROM task_settings WHERE task_id = $1",
                "DELETE FROM sources WHERE task_id = $1",
                "DELETE FROM targets WHERE task_id = $1",
                "DELETE FROM tasks WHERE id = $1"
            ]
            
            for query in delete_queries:
                await self.database.execute_command(query, task_id)
            
            # Remove from cache
            async with self.cache_lock:
                self.task_cache.pop(task_id, None)
            
            logger.info(f"Deleted task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
    
    async def toggle_task_status(self, task_id: int) -> Optional[bool]:
        """Toggle task active status"""
        try:
            # Get current status
            task = await self.get_task(task_id)
            if not task:
                return None
            
            new_status = not task["is_active"]
            
            # Update status
            success = await self.update_task(task_id, {"is_active": new_status})
            
            if success:
                logger.info(f"Task {task_id} {'activated' if new_status else 'deactivated'}")
                return new_status
            
            return None
            
        except Exception as e:
            logger.error(f"Error toggling task {task_id}: {e}")
            return None
    
    async def add_source(self, task_id: int, chat_data: Dict[str, Any]) -> bool:
        """Add source to task"""
        try:
            query = """
                INSERT INTO sources (task_id, chat_id, chat_title, chat_username, chat_type, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, true, NOW())
                ON CONFLICT (task_id, chat_id) DO UPDATE SET
                    chat_title = EXCLUDED.chat_title,
                    chat_username = EXCLUDED.chat_username,
                    chat_type = EXCLUDED.chat_type,
                    is_active = true
            """
            
            await self.database.execute_command(
                query,
                task_id,
                chat_data["chat_id"],
                chat_data.get("chat_title"),
                chat_data.get("chat_username"),
                chat_data.get("chat_type", "unknown")
            )
            
            logger.info(f"Added source {chat_data['chat_id']} to task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding source to task {task_id}: {e}")
            return False
    
    async def remove_source(self, task_id: int, chat_id: int) -> bool:
        """Remove source from task"""
        try:
            query = "DELETE FROM sources WHERE task_id = $1 AND chat_id = $2"
            await self.database.execute_command(query, task_id, chat_id)
            
            logger.info(f"Removed source {chat_id} from task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing source from task {task_id}: {e}")
            return False
    
    async def add_target(self, task_id: int, chat_data: Dict[str, Any]) -> bool:
        """Add target to task"""
        try:
            query = """
                INSERT INTO targets (task_id, chat_id, chat_title, chat_username, chat_type, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, true, NOW())
                ON CONFLICT (task_id, chat_id) DO UPDATE SET
                    chat_title = EXCLUDED.chat_title,
                    chat_username = EXCLUDED.chat_username,
                    chat_type = EXCLUDED.chat_type,
                    is_active = true
            """
            
            await self.database.execute_command(
                query,
                task_id,
                chat_data["chat_id"],
                chat_data.get("chat_title"),
                chat_data.get("chat_username"),
                chat_data.get("chat_type", "unknown")
            )
            
            logger.info(f"Added target {chat_data['chat_id']} to task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding target to task {task_id}: {e}")
            return False
    
    async def remove_target(self, task_id: int, chat_id: int) -> bool:
        """Remove target from task"""
        try:
            query = "DELETE FROM targets WHERE task_id = $1 AND chat_id = $2"
            await self.database.execute_command(query, task_id, chat_id)
            
            logger.info(f"Removed target {chat_id} from task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing target from task {task_id}: {e}")
            return False
    
    async def update_task_settings(self, task_id: int, settings: Dict[str, Any]) -> bool:
        """Update task settings"""
        try:
            # Validate settings
            validated_settings = validate_forward_settings(settings)
            
            # Convert to JSON where needed
            keyword_filters = validated_settings.get("keyword_filters")
            replace_text = validated_settings.get("replace_text")
            
            query = """
                UPDATE task_settings SET
                    forward_mode = $2,
                    preserve_sender = $3,
                    add_caption = $4,
                    custom_caption = $5,
                    filter_media = $6,
                    filter_text = $7,
                    filter_forwarded = $8,
                    filter_links = $9,
                    keyword_filters = $10,
                    delay_min = $11,
                    delay_max = $12,
                    remove_links = $13,
                    remove_mentions = $14,
                    replace_text = $15,
                    duplicate_check = $16,
                    max_message_length = $17,
                    updated_at = NOW()
                WHERE task_id = $1
            """
            
            await self.database.execute_command(
                query,
                task_id,
                validated_settings.get("forward_mode", "copy"),
                validated_settings.get("preserve_sender", False),
                validated_settings.get("add_caption", False),
                validated_settings.get("custom_caption"),
                validated_settings.get("filter_media", False),
                validated_settings.get("filter_text", False),
                validated_settings.get("filter_forwarded", False),
                validated_settings.get("filter_links", False),
                keyword_filters,
                validated_settings.get("delay_min", 0),
                validated_settings.get("delay_max", 5),
                validated_settings.get("remove_links", False),
                validated_settings.get("remove_mentions", False),
                replace_text,
                validated_settings.get("duplicate_check", True),
                validated_settings.get("max_message_length", 4096)
            )
            
            logger.info(f"Updated settings for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task settings {task_id}: {e}")
            return False
    
    async def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get complete task information"""
        try:
            # Get task
            task = await self.get_task(task_id)
            if not task:
                return None
            
            # Get sources
            sources = await self.database.get_task_sources(task_id)
            
            # Get targets
            targets = await self.database.get_task_targets(task_id)
            
            # Get settings
            settings = await self.database.get_task_settings(task_id)
            
            # Get statistics
            statistics = await self.database.get_task_statistics(task_id)
            
            return {
                "task": task,
                "sources": sources,
                "targets": targets,
                "settings": settings,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"Error getting task info {task_id}: {e}")
            return None
    
    async def _create_default_settings(self, task_id: int):
        """Create default settings for task"""
        try:
            query = """
                INSERT INTO task_settings (task_id, created_at, updated_at)
                VALUES ($1, NOW(), NOW())
            """
            await self.database.execute_command(query, task_id)
            
        except Exception as e:
            logger.error(f"Error creating default settings for task {task_id}: {e}")
    
    async def _create_default_statistics(self, task_id: int):
        """Create default statistics for task"""
        try:
            query = """
                INSERT INTO task_statistics (task_id, created_at, updated_at)
                VALUES ($1, NOW(), NOW())
            """
            await self.database.execute_command(query, task_id)
            
        except Exception as e:
            logger.error(f"Error creating default statistics for task {task_id}: {e}")
    
    async def _load_tasks_cache(self):
        """Load tasks into cache"""
        try:
            query = """
                SELECT t.*, u.telegram_id as user_telegram_id
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.is_active = true
            """
            
            tasks = await self.database.execute_query(query)
            
            async with self.cache_lock:
                self.task_cache = {task["id"]: task for task in tasks}
            
            logger.info(f"Loaded {len(tasks)} tasks into cache")
            
        except Exception as e:
            logger.error(f"Error loading tasks cache: {e}")
    
    async def _refresh_task_cache(self, task_id: int):
        """Refresh specific task in cache"""
        try:
            query = """
                SELECT t.*, u.telegram_id as user_telegram_id
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = $1
            """
            
            result = await self.database.execute_query(query, task_id)
            
            async with self.cache_lock:
                if result:
                    self.task_cache[task_id] = result[0]
                else:
                    self.task_cache.pop(task_id, None)
                    
        except Exception as e:
            logger.error(f"Error refreshing task cache for {task_id}: {e}")
    
    async def get_task_summary(self, task_id: int) -> str:
        """Get formatted task summary"""
        try:
            info = await self.get_task_info(task_id)
            if not info:
                return "❌ Task not found"
            
            task = info["task"]
            sources = info["sources"]
            targets = info["targets"]
            stats = info["statistics"]
            
            status_emoji = "🟢" if task["is_active"] else "🔴"
            type_emoji = "🤖" if task["task_type"] == "bot" else "👤"
            
            summary = f"""
{status_emoji} **{task['name']}** {type_emoji}

📋 **Description:** {task['description'] or 'No description'}
🆔 **Task ID:** `{task_id}`
📅 **Created:** {task['created_at'].strftime('%Y-%m-%d %H:%M')}

📊 **Statistics:**
• Sources: {len(sources)}
• Targets: {len(targets)}
• Messages Forwarded: {stats['messages_forwarded'] if stats else 0}
• Messages Failed: {stats['messages_failed'] if stats else 0}
• Last Activity: {stats['last_activity'].strftime('%Y-%m-%d %H:%M') if stats and stats['last_activity'] else 'Never'}

⚙️ **Status:** {'Active' if task['is_active'] else 'Inactive'}
            """
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error getting task summary {task_id}: {e}")
            return "❌ Error loading task summary"
