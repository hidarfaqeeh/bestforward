"""
CallbackRouter - Performance-critical router to replace 365 elif statements

This module addresses the critical performance issue where every callback
was processed through 365+ elif statements in handlers/tasks.py
"""

import time
from typing import Dict, Callable, Optional, Any, List
import logging
logger = logging.getLogger(__name__)
# Import aiogram types only when available
try:
    from aiogram.types import CallbackQuery
    from aiogram.fsm.context import FSMContext
except ImportError:
    # Fallback types for testing without aiogram
    CallbackQuery = object
    FSMContext = object


class CallbackRouter:
    """
    High-performance callback router that replaces the 365+ elif statements
    in tasks handler with O(1) lookup time.
    """
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.prefix_handlers: Dict[str, Callable] = {}
        self.pattern_handlers: List[tuple] = []  # (pattern, handler)
        self.stats = {
            'total_routes': 0,
            'routing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self._route_cache: Dict[str, Callable] = {}
        
    def register_exact(self, callback_data: str, handler: Callable):
        """Register exact callback match handler"""
        self.handlers[callback_data] = handler
        self.stats['total_routes'] += 1
        logger.debug(f"Registered exact route: {callback_data}")
        
    def register_prefix(self, prefix: str, handler: Callable):
        """Register prefix-based handler"""
        self.prefix_handlers[prefix] = handler
        self.stats['total_routes'] += 1
        logger.debug(f"Registered prefix route: {prefix}")
        
    def register_pattern(self, pattern: str, handler: Callable):
        """Register pattern-based handler"""
        self.pattern_handlers.append((pattern, handler))
        self.stats['total_routes'] += 1
        logger.debug(f"Registered pattern route: {pattern}")
        
    async def route(self, callback: CallbackQuery, state: FSMContext) -> bool:
        """
        Route callback to appropriate handler
        
        Returns:
            bool: True if handled, False if no handler found
        """
        start_time = time.time()
        callback_data = callback.data
        
        if not callback_data:
            logger.warning("Empty callback data received")
            return False
            
        try:
            # Check cache first for performance
            if callback_data in self._route_cache:
                handler = self._route_cache[callback_data]
                self.stats['cache_hits'] += 1
                await handler(callback, state)
                return True
                
            # Find handler
            handler = self._find_handler(callback_data)
            
            if handler:
                # Cache the route for future use
                self._route_cache[callback_data] = handler
                self.stats['cache_misses'] += 1
                
                # Execute handler
                await handler(callback, state)
                return True
            else:
                logger.warning(f"No handler found for callback: {callback_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing callback '{callback_data}': {e}")
            return False
        finally:
            routing_time = time.time() - start_time
            self.stats['routing_time'] += routing_time
            
            # Log slow routes for performance monitoring
            if routing_time > 0.1:  # 100ms threshold
                logger.warning(f"Slow routing detected: {callback_data} took {routing_time:.3f}s")
                
    def _find_handler(self, callback_data: str) -> Optional[Callable]:
        """Find appropriate handler for callback data"""
        
        # 1. Exact match (fastest)
        if callback_data in self.handlers:
            return self.handlers[callback_data]
            
        # 2. Prefix match
        for prefix, handler in self.prefix_handlers.items():
            if callback_data.startswith(prefix):
                return handler
                
        # 3. Pattern match (slowest but most flexible)
        for pattern, handler in self.pattern_handlers:
            import re
            if re.match(pattern, callback_data):
                return handler
                
        return None
        
    def get_stats(self) -> Dict[str, Any]:
        """Get routing performance statistics"""
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        
        return {
            'total_routes_registered': self.stats['total_routes'],
            'total_requests': total_requests,
            'cache_hit_rate': (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0,
            'average_routing_time': (self.stats['routing_time'] / total_requests) if total_requests > 0 else 0,
            'cache_size': len(self._route_cache)
        }
        
    def clear_cache(self):
        """Clear routing cache"""
        self._route_cache.clear()
        logger.info("Routing cache cleared")
        
    def preload_common_routes(self, common_routes: List[str]):
        """Preload common routes into cache"""
        for route in common_routes:
            handler = self._find_handler(route)
            if handler:
                self._route_cache[route] = handler
        logger.info(f"Preloaded {len(common_routes)} common routes")


class TaskCallbackRouter(CallbackRouter):
    """
    Specialized callback router for task-related callbacks
    This replaces the massive elif chain in handlers/tasks.py
    """
    
    def __init__(self, task_handler):
        super().__init__()
        self.task_handler = task_handler
        self._register_all_task_routes()
        
    def _register_all_task_routes(self):
        """Register all task-related routes"""
        
        # === EXACT MATCHES ===
        exact_routes = {
            "task_create": self.task_handler._handle_task_creation_start,
            "task_list": self.task_handler._handle_task_list,
            "task_refresh": self.task_handler._handle_task_refresh,
            "task_stats": self.task_handler._handle_task_statistics_overview,
        }
        
        for route, handler in exact_routes.items():
            self.register_exact(route, handler)
            
        # === PREFIX MATCHES ===
        prefix_routes = {
            "task_create_": self.task_handler._handle_task_type_selection,
            "task_view_": self.task_handler._handle_task_view,
            "task_edit_": self.task_handler._handle_task_edit,
            "task_toggle_": self.task_handler._handle_task_toggle,
            "task_mode_toggle_": self.task_handler._handle_task_mode_toggle,
            "task_delete_": self.task_handler._handle_task_delete,
            "task_statistics_": self.task_handler._handle_task_statistics,
            "task_settings_": self.task_handler._handle_task_settings,
            "task_info_": self.task_handler._handle_task_info,
            "task_edit_name_": self.task_handler._handle_task_edit_name,
            "task_edit_desc_": self.task_handler._handle_task_edit_description,
            "task_edit_type_": self.task_handler._handle_task_change_type,
            "task_list_page_": self.task_handler._handle_task_list_pagination,
            
            # Settings routes
            "setting_forward_mode_": self.task_handler._handle_forward_mode_setting,
            "setting_delays_": self.task_handler._handle_delay_setting,
            "setting_limits_": self.task_handler._handle_limits_setting,
            "setting_filters_": self.task_handler._handle_filters_setting,
            "setting_content_": self.task_handler._handle_content_setting,
            "setting_forward_": self.task_handler._handle_forward_setting,
            "setting_advanced_": self.task_handler._handle_advanced_setting,
            
            # Advanced features
            "advanced_translation_": self.task_handler._handle_advanced_translation,
            "advanced_working_hours_": self.task_handler._handle_advanced_working_hours,
            "advanced_recurring_": self.task_handler._handle_advanced_recurring,
            
            # Content routes
            "content_prefix_": self.task_handler._handle_prefix_suffix_setting,
            "content_replace_": self.task_handler._handle_text_replace_setting,
            "content_formatting_": self.task_handler._handle_formatting_setting,
            "content_links_": self.task_handler._handle_links_setting,
            "content_cleaner_": self.task_handler._handle_text_cleaner_setting,
            "content_inline_buttons_": self.task_handler._handle_inline_buttons_setting,
            
            # Filter routes
            "filter_keywords_": self.task_handler._handle_keyword_filter,
            "filter_media_": self.task_handler._handle_media_filter,
            "filter_length_": self.task_handler._handle_length_filter,
            "filter_languages_": self.task_handler._handle_language_filter_management,
            
            # Toggle routes
            "toggle_filter_forwarded_": self.task_handler._toggle_forwarded_filter,
            "toggle_filter_links_": self.task_handler._toggle_links_filter,
            "toggle_filter_buttons_": self.task_handler._toggle_buttons_filter,
            "toggle_filter_duplicates_": self.task_handler._toggle_duplicates_filter,
            "toggle_filter_language_": self.task_handler._toggle_language_filter,
            "toggle_manual_mode_": self.task_handler._handle_toggle_manual_mode,
            "toggle_link_preview_": self.task_handler._handle_toggle_link_preview,
            "toggle_pin_messages_": self.task_handler._handle_toggle_pin_messages,
            "toggle_silent_mode_": self.task_handler._handle_toggle_silent_mode,
            "toggle_sync_edits_": self.task_handler._handle_toggle_sync_edits,
            "toggle_sync_deletes_": self.task_handler._handle_toggle_sync_deletes,
            "toggle_preserve_replies_": self.task_handler._handle_toggle_preserve_replies,
        }
        
        for prefix, handler in prefix_routes.items():
            self.register_prefix(prefix, handler)
            
        # === PATTERN MATCHES ===
        pattern_routes = [
            (r"^confirm_delete_task\d+$", self.task_handler._handle_confirm_task_delete),
            (r"^cancel_delete_task\d+$", self.task_handler._handle_cancel_task_delete),
            (r"^len_\d+_\d+$", self.task_handler._handle_length_setting),
            (r"^set_min_\d+_\d+$", self.task_handler._handle_length_value_setting),
            (r"^set_max_\d+_\d+$", self.task_handler._handle_length_value_setting),
            (r"^set_action_\w+_\d+$", self.task_handler._handle_action_mode_setting),
        ]
        
        for pattern, handler in pattern_routes:
            self.register_pattern(pattern, handler)
            
        # Preload common routes for better performance
        common_routes = [
            "task_list", "task_create", "task_refresh",
            "task_view_1", "task_settings_1", "task_edit_1"
        ]
        self.preload_common_routes(common_routes)
        
        logger.success(f"TaskCallbackRouter initialized with {self.stats['total_routes']} routes")


# Global router instance
_task_router = None

def get_task_router(task_handler=None) -> TaskCallbackRouter:
    """Get or create global task router instance"""
    global _task_router
    if _task_router is None and task_handler is not None:
        _task_router = TaskCallbackRouter(task_handler)
    return _task_router

def reset_task_router():
    """Reset global task router (useful for testing)"""
    global _task_router
    _task_router = None