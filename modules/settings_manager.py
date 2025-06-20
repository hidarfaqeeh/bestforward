"""
Settings Manager - Handles bot and task settings
"""

import json
from typing import Dict, List, Any, Optional

from loguru import logger

from database import Database
from utils import validate_forward_settings, safe_json_loads, safe_json_dumps


class SettingsManager:
    """Manages bot and task settings"""
    
    def __init__(self, database: Database):
        self.database = database
        self.system_settings_cache: Dict[str, Any] = {}
        self.task_settings_cache: Dict[int, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize settings manager"""
        try:
            await self._load_system_settings()
            logger.success("Settings manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize settings manager: {e}")
            raise
    
    async def get_system_setting(self, key: str, default: Any = None) -> Any:
        """Get system setting value"""
        try:
            # Check cache first
            if key in self.system_settings_cache:
                return self.system_settings_cache[key]
            
            # Query database
            query = "SELECT value, value_type FROM system_settings WHERE key = $1"
            result = await self.database.execute_query(query, key)
            
            if not result:
                return default
            
            setting = result[0]
            value = setting["value"]
            value_type = setting["value_type"]
            
            # Convert value based on type
            if value_type == "integer":
                value = int(value) if value else 0
            elif value_type == "boolean":
                value = value.lower() == "true" if value else False
            elif value_type == "json":
                value = safe_json_loads(value, {})
            # string type needs no conversion
            
            # Cache the value
            self.system_settings_cache[key] = value
            
            return value
            
        except Exception as e:
            logger.error(f"Error getting system setting {key}: {e}")
            return default
    
    async def set_system_setting(self, key: str, value: Any, value_type: str = "string", 
                                description: str = "", is_public: bool = False) -> bool:
        """Set system setting value"""
        try:
            # Convert value to string for storage
            if value_type == "json":
                value_str = safe_json_dumps(value)
            elif value_type == "boolean":
                value_str = "true" if value else "false"
            else:
                value_str = str(value)
            
            # Upsert setting
            query = """
                INSERT INTO system_settings (key, value, value_type, description, is_public, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    value_type = EXCLUDED.value_type,
                    description = EXCLUDED.description,
                    is_public = EXCLUDED.is_public,
                    updated_at = NOW()
            """
            
            await self.database.execute_command(
                query, key, value_str, value_type, description, is_public
            )
            
            # Update cache
            self.system_settings_cache[key] = value
            
            logger.info(f"Updated system setting: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting system setting {key}: {e}")
            return False
    
    async def get_all_system_settings(self, public_only: bool = False) -> Dict[str, Any]:
        """Get all system settings"""
        try:
            query = "SELECT key, value, value_type, description, is_public FROM system_settings"
            if public_only:
                query += " WHERE is_public = true"
            query += " ORDER BY key"
            
            results = await self.database.execute_query(query)
            
            settings = {}
            for row in results:
                key = row["key"]
                value = row["value"]
                value_type = row["value_type"]
                
                # Convert value based on type
                if value_type == "integer":
                    value = int(value) if value else 0
                elif value_type == "boolean":
                    value = value.lower() == "true" if value else False
                elif value_type == "json":
                    value = safe_json_loads(value, {})
                
                settings[key] = {
                    "value": value,
                    "type": value_type,
                    "description": row["description"],
                    "public": row["is_public"]
                }
            
            return settings
            
        except Exception as e:
            logger.error(f"Error getting all system settings: {e}")
            return {}
    
    async def delete_system_setting(self, key: str) -> bool:
        """Delete system setting"""
        try:
            query = "DELETE FROM system_settings WHERE key = $1"
            await self.database.execute_command(query, key)
            
            # Remove from cache
            self.system_settings_cache.pop(key, None)
            
            logger.info(f"Deleted system setting: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting system setting {key}: {e}")
            return False
    
    async def get_task_settings(self, task_id: int) -> Dict[str, Any]:
        """Get task settings"""
        try:
            # Check cache
            if task_id in self.task_settings_cache:
                return self.task_settings_cache[task_id].copy()
            
            # Query database
            settings = await self.database.get_task_settings(task_id)
            
            if not settings:
                # Return default settings
                default_settings = self._get_default_task_settings()
                self.task_settings_cache[task_id] = default_settings
                return default_settings
            
            # Convert JSON fields
            if settings.get("keyword_filters"):
                settings["keyword_filters"] = safe_json_loads(settings["keyword_filters"], [])
            
            if settings.get("replace_text"):
                settings["replace_text"] = safe_json_loads(settings["replace_text"], {})
            
            # Cache settings
            self.task_settings_cache[task_id] = settings
            
            return settings
            
        except Exception as e:
            logger.error(f"Error getting task settings for {task_id}: {e}")
            return self._get_default_task_settings()
    
    async def update_task_settings(self, task_id: int, settings: Dict[str, Any]) -> bool:
        """Update task settings"""
        try:
            # Validate settings
            validated_settings = validate_forward_settings(settings)
            
            # Convert JSON fields
            keyword_filters = safe_json_dumps(validated_settings.get("keyword_filters", []))
            replace_text = safe_json_dumps(validated_settings.get("replace_text", {}))
            
            # Check if settings exist
            existing = await self.database.get_task_settings(task_id)
            
            if existing:
                # Update existing settings
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
            else:
                # Insert new settings
                query = """
                    INSERT INTO task_settings (
                        task_id, forward_mode, preserve_sender, add_caption, custom_caption,
                        filter_media, filter_text, filter_forwarded, filter_links, keyword_filters,
                        delay_min, delay_max, remove_links, remove_mentions, replace_text,
                        duplicate_check, max_message_length, created_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, NOW(), NOW()
                    )
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
            
            # Update cache
            validated_settings["keyword_filters"] = validated_settings.get("keyword_filters", [])
            validated_settings["replace_text"] = validated_settings.get("replace_text", {})
            self.task_settings_cache[task_id] = validated_settings
            
            logger.info(f"Updated task settings for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task settings for {task_id}: {e}")
            return False
    
    async def reset_task_settings(self, task_id: int) -> bool:
        """Reset task settings to defaults"""
        try:
            default_settings = self._get_default_task_settings()
            success = await self.update_task_settings(task_id, default_settings)
            
            if success:
                logger.info(f"Reset task settings for task {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error resetting task settings for {task_id}: {e}")
            return False
    
    async def copy_task_settings(self, source_task_id: int, target_task_id: int) -> bool:
        """Copy settings from one task to another"""
        try:
            source_settings = await self.get_task_settings(source_task_id)
            
            # Remove system fields
            source_settings.pop("id", None)
            source_settings.pop("task_id", None)
            source_settings.pop("created_at", None)
            source_settings.pop("updated_at", None)
            
            success = await self.update_task_settings(target_task_id, source_settings)
            
            if success:
                logger.info(f"Copied settings from task {source_task_id} to {target_task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error copying task settings: {e}")
            return False
    
    async def get_settings_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get settings preset"""
        try:
            presets = await self.get_system_setting("settings_presets", {})
            return presets.get(preset_name)
            
        except Exception as e:
            logger.error(f"Error getting settings preset {preset_name}: {e}")
            return None
    
    async def save_settings_preset(self, preset_name: str, settings: Dict[str, Any], 
                                  description: str = "") -> bool:
        """Save settings preset"""
        try:
            presets = await self.get_system_setting("settings_presets", {})
            
            presets[preset_name] = {
                "settings": validate_forward_settings(settings),
                "description": description,
                "created_at": datetime.now().isoformat()
            }
            
            success = await self.set_system_setting(
                "settings_presets", presets, "json", "Task settings presets"
            )
            
            if success:
                logger.info(f"Saved settings preset: {preset_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving settings preset {preset_name}: {e}")
            return False
    
    async def delete_settings_preset(self, preset_name: str) -> bool:
        """Delete settings preset"""
        try:
            presets = await self.get_system_setting("settings_presets", {})
            
            if preset_name in presets:
                del presets[preset_name]
                
                success = await self.set_system_setting(
                    "settings_presets", presets, "json", "Task settings presets"
                )
                
                if success:
                    logger.info(f"Deleted settings preset: {preset_name}")
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting settings preset {preset_name}: {e}")
            return False
    
    async def apply_settings_preset(self, task_id: int, preset_name: str) -> bool:
        """Apply settings preset to task"""
        try:
            preset = await self.get_settings_preset(preset_name)
            
            if not preset:
                logger.error(f"Settings preset {preset_name} not found")
                return False
            
            success = await self.update_task_settings(task_id, preset["settings"])
            
            if success:
                logger.info(f"Applied preset {preset_name} to task {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying settings preset: {e}")
            return False
    
    def _get_default_task_settings(self) -> Dict[str, Any]:
        """Get default task settings"""
        return {
            "forward_mode": "copy",
            "preserve_sender": False,
            "add_caption": False,
            "custom_caption": None,
            "filter_media": False,
            "filter_text": False,
            "filter_forwarded": False,
            "filter_links": False,
            "keyword_filters": [],
            "delay_min": 0,
            "delay_max": 5,
            "remove_links": False,
            "remove_mentions": False,
            "replace_text": {},
            "duplicate_check": True,
            "max_message_length": 4096
        }
    
    async def _load_system_settings(self):
        """Load system settings into cache"""
        try:
            settings = await self.get_all_system_settings()
            
            for key, setting_data in settings.items():
                self.system_settings_cache[key] = setting_data["value"]
            
            logger.info(f"Loaded {len(settings)} system settings into cache")
            
        except Exception as e:
            logger.error(f"Error loading system settings: {e}")
    
    async def get_formatted_task_settings(self, task_id: int) -> str:
        """Get formatted task settings text"""
        try:
            settings = await self.get_task_settings(task_id)
            
            if not settings:
                return "❌ No settings found"
            
            return f"""
⚙️ **Task Settings** (ID: {task_id})

**Forwarding Mode:**
• Mode: {settings.get('forward_mode', 'copy').title()}
• Preserve Sender: {'✅' if settings.get('preserve_sender') else '❌'}
• Add Caption: {'✅' if settings.get('add_caption') else '❌'}
• Custom Caption: {settings.get('custom_caption') or 'None'}

**Filters:**
• Filter Media: {'✅' if settings.get('filter_media') else '❌'}
• Filter Text: {'✅' if settings.get('filter_text') else '❌'}
• Filter Forwarded: {'✅' if settings.get('filter_forwarded') else '❌'}
• Filter Links: {'✅' if settings.get('filter_links') else '❌'}
• Keyword Filters: {len(settings.get('keyword_filters', []))} keywords

**Content Modification:**
• Remove Links: {'✅' if settings.get('remove_links') else '❌'}
• Remove Mentions: {'✅' if settings.get('remove_mentions') else '❌'}
• Text Replacements: {len(settings.get('replace_text', {}))} rules

**Performance:**
• Min Delay: {settings.get('delay_min', 0)}s
• Max Delay: {settings.get('delay_max', 5)}s
• Duplicate Check: {'✅' if settings.get('duplicate_check') else '❌'}
• Max Message Length: {settings.get('max_message_length', 4096)} chars
            """.strip()
            
        except Exception as e:
            logger.error(f"Error formatting task settings for {task_id}: {e}")
            return "❌ Error loading settings"
    
    async def clear_cache(self):
        """Clear settings cache"""
        self.system_settings_cache.clear()
        self.task_settings_cache.clear()
        logger.info("Settings cache cleared")
    
    async def validate_task_settings(self, settings: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate task settings and return errors"""
        errors = []
        
        try:
            # Validate forward mode
            if settings.get("forward_mode") not in ["copy", "forward", "quote"]:
                errors.append("Invalid forward mode")
            
            # Validate delays
            delay_min = settings.get("delay_min", 0)
            delay_max = settings.get("delay_max", 5)
            
            if delay_min < 0:
                errors.append("Minimum delay cannot be negative")
            
            if delay_max < delay_min:
                errors.append("Maximum delay must be greater than minimum delay")
            
            if delay_max > 300:  # 5 minutes max
                errors.append("Maximum delay cannot exceed 300 seconds")
            
            # Validate message length
            max_length = settings.get("max_message_length", 4096)
            if max_length < 1 or max_length > 4096:
                errors.append("Message length must be between 1 and 4096 characters")
            
            # Validate keyword filters
            keyword_filters = settings.get("keyword_filters", [])
            if not isinstance(keyword_filters, list):
                errors.append("Keyword filters must be a list")
            elif len(keyword_filters) > 100:
                errors.append("Maximum 100 keyword filters allowed")
            
            # Validate text replacements
            replace_text = settings.get("replace_text", {})
            if not isinstance(replace_text, dict):
                errors.append("Text replacements must be a dictionary")
            elif len(replace_text) > 50:
                errors.append("Maximum 50 text replacement rules allowed")
            
            # Validate custom caption
            custom_caption = settings.get("custom_caption")
            if custom_caption and len(custom_caption) > 1024:
                errors.append("Custom caption cannot exceed 1024 characters")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating task settings: {e}")
            return False, [f"Validation error: {e}"]
