"""
DatabaseCache - High-performance caching system for database operations

This module addresses the critical performance issue where 223 database
queries were executed in handlers/tasks.py, many of them repetitive.
"""

import time
import json
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    ttl: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl
        
    def touch(self):
        """Update access metadata"""
        self.access_count += 1
        self.last_access = time.time()


class DatabaseCache:
    """
    High-performance database cache that reduces repetitive queries
    from 223 to a minimal number by caching frequently accessed data.
    """
    
    def __init__(self, database, default_ttl: int = 300, max_cache_size: int = 1000):
        self.database = database
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._dirty_keys: Set[str] = set()  # Keys that need DB sync
        
        # Performance metrics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'database_queries_saved': 0,
            'cache_evictions': 0,
            'dirty_writes': 0
        }
        
        # Auto-cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
    def _start_cleanup_task(self):
        """Start automatic cache cleanup task"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
                
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        
    async def _cleanup_expired(self):
        """Remove expired cache entries"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
                
        for key in expired_keys:
            del self._cache[key]
            self.stats['cache_evictions'] += 1
            
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
    def _evict_lru(self):
        """Evict least recently used entries if cache is full"""
        if len(self._cache) <= self.max_cache_size:
            return
            
        # Sort by last access time and remove oldest
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_access
        )
        
        to_evict = len(self._cache) - self.max_cache_size + 10  # Evict extra for buffer
        for i in range(to_evict):
            key = sorted_entries[i][0]
            del self._cache[key]
            self.stats['cache_evictions'] += 1
            
    def _get_cache_key(self, operation: str, *args) -> str:
        """Generate cache key for operation and arguments"""
        args_str = "_".join(str(arg) for arg in args)
        return f"{operation}:{args_str}"
        
    async def get_task_settings(self, task_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get task settings with caching"""
        cache_key = self._get_cache_key("task_settings", task_id)
        
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                entry.touch()
                self.stats['cache_hits'] += 1
                self.stats['total_requests'] += 1
                return entry.data
                
        # Cache miss - fetch from database
        self.stats['cache_misses'] += 1
        self.stats['total_requests'] += 1
        self.stats['database_queries_saved'] += 1
        
        try:
            settings = await self.database.get_task_settings(task_id)
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                data=settings,
                timestamp=time.time(),
                ttl=self.default_ttl
            )
            
            self._evict_lru()
            return settings
            
        except Exception as e:
            logger.error(f"Error fetching task settings for task {task_id}: {e}")
            return None
            
    async def update_task_settings(self, task_id: int, settings: Dict[str, Any]) -> bool:
        """Update task settings and invalidate cache"""
        try:
            # Update database
            success = await self.database.update_task_settings(task_id, settings)
            
            if success:
                # Update cache immediately for consistency
                cache_key = self._get_cache_key("task_settings", task_id)
                self._cache[cache_key] = CacheEntry(
                    data=settings,
                    timestamp=time.time(),
                    ttl=self.default_ttl
                )
                
                # Mark as dirty for tracking
                self._dirty_keys.add(cache_key)
                self.stats['dirty_writes'] += 1
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating task settings for task {task_id}: {e}")
            return False
            
    async def get_task_data(self, task_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get task data with caching"""
        cache_key = self._get_cache_key("task_data", task_id)
        
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                entry.touch()
                self.stats['cache_hits'] += 1
                self.stats['total_requests'] += 1
                return entry.data
                
        # Cache miss - fetch from database
        self.stats['cache_misses'] += 1
        self.stats['total_requests'] += 1
        
        try:
            query = "SELECT * FROM tasks WHERE id = $1"
            result = await self.database.execute_query(query, task_id)
            task_data = result[0] if result else None
            
            # Cache the result
            if task_data:
                self._cache[cache_key] = CacheEntry(
                    data=task_data,
                    timestamp=time.time(),
                    ttl=600  # Tasks change less frequently, cache longer
                )
                
            self._evict_lru()
            return task_data
            
        except Exception as e:
            logger.error(f"Error fetching task data for task {task_id}: {e}")
            return None
            
    async def get_user_tasks(self, user_id: int, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get user tasks with caching"""
        cache_key = self._get_cache_key("user_tasks", user_id)
        
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                entry.touch()
                self.stats['cache_hits'] += 1
                self.stats['total_requests'] += 1
                return entry.data
                
        # Cache miss - fetch from database
        self.stats['cache_misses'] += 1
        self.stats['total_requests'] += 1
        
        try:
            query = """
            SELECT t.*, 
                   COUNT(s.id) as source_count,
                   COUNT(tg.id) as target_count
            FROM tasks t
            LEFT JOIN sources s ON t.id = s.task_id
            LEFT JOIN targets tg ON t.id = tg.task_id
            WHERE t.user_id = $1
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
            tasks = await self.database.execute_query(query, user_id)
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                data=tasks,
                timestamp=time.time(),
                ttl=180  # Task lists change more frequently
            )
            
            self._evict_lru()
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching user tasks for user {user_id}: {e}")
            return []
            
    async def invalidate_task_cache(self, task_id: int):
        """Invalidate all cache entries related to a task"""
        keys_to_remove = []
        for key in self._cache.keys():
            if f"task_{task_id}" in key or f":{task_id}" in key:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self._cache[key]
            
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for task {task_id}")
        
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries related to a user"""
        keys_to_remove = []
        for key in self._cache.keys():
            if f"user_{user_id}" in key or f":{user_id}" in key:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self._cache[key]
            
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
        
    async def batch_get_task_settings(self, task_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get multiple task settings in a single optimized query"""
        cache_results = {}
        missing_ids = []
        
        # Check cache first
        for task_id in task_ids:
            cache_key = self._get_cache_key("task_settings", task_id)
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if not entry.is_expired():
                    entry.touch()
                    cache_results[task_id] = entry.data
                    self.stats['cache_hits'] += 1
                else:
                    missing_ids.append(task_id)
            else:
                missing_ids.append(task_id)
                
        # Fetch missing data in batch
        if missing_ids:
            try:
                placeholders = ",".join(f"${i+1}" for i in range(len(missing_ids)))
                query = f"""
                SELECT ts.*, t.id as task_id
                FROM task_settings ts
                JOIN tasks t ON ts.task_id = t.id
                WHERE t.id IN ({placeholders})
                """
                
                results = await self.database.execute_query(query, *missing_ids)
                
                for row in results:
                    task_id = row['task_id']
                    settings_data = {k: v for k, v in row.items() if k != 'task_id'}
                    
                    # Cache the result
                    cache_key = self._get_cache_key("task_settings", task_id)
                    self._cache[cache_key] = CacheEntry(
                        data=settings_data,
                        timestamp=time.time(),
                        ttl=self.default_ttl
                    )
                    
                    cache_results[task_id] = settings_data
                    self.stats['cache_misses'] += 1
                    
                self.stats['database_queries_saved'] += len(missing_ids) - 1  # Saved N-1 queries
                
            except Exception as e:
                logger.error(f"Error batch fetching task settings: {e}")
                
        self.stats['total_requests'] += len(task_ids)
        self._evict_lru()
        return cache_results
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats['total_requests']
        
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self.max_cache_size,
            'total_requests': total_requests,
            'cache_hit_rate': (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0,
            'cache_miss_rate': (self.stats['cache_misses'] / total_requests * 100) if total_requests > 0 else 0,
            'database_queries_saved': self.stats['database_queries_saved'],
            'cache_evictions': self.stats['cache_evictions'],
            'dirty_entries': len(self._dirty_keys),
            'memory_usage_estimate': len(self._cache) * 1024,  # Rough estimate in bytes
        }
        
    async def clear_cache(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._dirty_keys.clear()
        logger.info("Database cache cleared")
        
    async def warm_up_cache(self, user_id: int):
        """Pre-load frequently accessed data for a user"""
        try:
            # Pre-load user tasks
            await self.get_user_tasks(user_id)
            
            # Pre-load task settings for user's tasks
            tasks = await self.get_user_tasks(user_id)
            if tasks:
                task_ids = [task['id'] for task in tasks]
                await self.batch_get_task_settings(task_ids)
                
            logger.info(f"Cache warmed up for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error warming up cache for user {user_id}: {e}")
            
    def __del__(self):
        """Cleanup when cache is destroyed"""
        if self._cleanup_task:
            self._cleanup_task.cancel()


# Global cache instance
_database_cache = None

def get_database_cache(database=None) -> DatabaseCache:
    """Get or create global database cache instance"""
    global _database_cache
    if _database_cache is None and database is not None:
        _database_cache = DatabaseCache(database)
    return _database_cache

def reset_database_cache():
    """Reset global database cache (useful for testing)"""
    global _database_cache
    if _database_cache:
        _database_cache._cleanup_task.cancel()
    _database_cache = None