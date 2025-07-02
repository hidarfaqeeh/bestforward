"""
MemoryManager - Advanced memory management and cleanup system

This module addresses memory leaks and accumulation issues in the bot,
particularly in session management and request tracking.
"""

import gc
import time
import asyncio
import os
import resource
from typing import Dict, Any, Set, List, Optional
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
from dataclasses import dataclass, field


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_memory: float = 0.0
    used_memory: float = 0.0
    available_memory: float = 0.0
    memory_percent: float = 0.0
    active_sessions: int = 0
    cached_objects: int = 0
    gc_collections: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class MemoryManager:
    """
    Advanced memory management system that prevents memory leaks
    and optimizes memory usage across the bot.
    """
    
    def __init__(self, 
                 cleanup_interval: int = 300,  # 5 minutes
                 max_session_age: int = 3600,  # 1 hour
                 max_cache_size: int = 1000,
                 memory_threshold: float = 80.0):  # 80% memory usage threshold
        
        self.cleanup_interval = cleanup_interval
        self.max_session_age = max_session_age
        self.max_cache_size = max_cache_size
        self.memory_threshold = memory_threshold
        
        # Memory tracking
        self.memory_stats: List[MemoryStats] = []
        self.max_stats_history = 100
        
        # Cleanup counters
        self.cleanup_stats = {
            'sessions_cleaned': 0,
            'caches_cleaned': 0,
            'objects_collected': 0,
            'memory_freed_mb': 0.0,
            'last_cleanup': None,
            'total_cleanups': 0
        }
        
        # References to objects that need cleanup
        self._session_managers: Set[Any] = set()
        self._cache_managers: Set[Any] = set()
        self._callback_routers: Set[Any] = set()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Emergency cleanup thresholds
        self.emergency_memory_threshold = 90.0  # 90%
        self.emergency_cleanup_enabled = True
        
        self._start_background_tasks()
        
    def _start_background_tasks(self):
        """Start background memory management tasks"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("MemoryManager background tasks started")
        
    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.perform_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    async def _monitoring_loop(self):
        """Memory monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                await self._update_memory_stats()
                await self._check_memory_pressure()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                
    async def _update_memory_stats(self):
        """Update memory usage statistics"""
        try:
            # Get process memory info using resource module
            usage = resource.getrusage(resource.RUSAGE_SELF)
            max_memory = usage.ru_maxrss  # Peak memory usage in KB (Linux) or bytes (macOS)
            
            # Convert to MB for consistency
            if os.name == 'posix':
                max_memory_mb = max_memory / 1024  # KB to MB on Linux
            else:
                max_memory_mb = max_memory / (1024 * 1024)  # bytes to MB on other systems
            
            # Get current memory from /proc/meminfo if available (Linux)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    total_kb = int([line for line in meminfo.split('\n') if 'MemTotal:' in line][0].split()[1])
                    available_kb = int([line for line in meminfo.split('\n') if 'MemAvailable:' in line][0].split()[1])
                    total_gb = total_kb / (1024 * 1024)
                    available_gb = available_kb / (1024 * 1024)
                    used_gb = total_gb - available_gb
                    memory_percent = (used_gb / total_gb) * 100
            except:
                # Fallback values if /proc/meminfo is not available
                total_gb = 8.0  # Default assumption
                used_gb = max_memory_mb / 1024
                available_gb = total_gb - used_gb
                memory_percent = (used_gb / total_gb) * 100
            
            stats = MemoryStats(
                total_memory=total_gb,
                used_memory=used_gb,
                available_memory=available_gb,
                memory_percent=memory_percent,
                active_sessions=sum(len(sm.user_sessions) for sm in self._session_managers if hasattr(sm, 'user_sessions')),
                cached_objects=sum(len(cm._cache) for cm in self._cache_managers if hasattr(cm, '_cache')),
                gc_collections=len(gc.get_objects())
            )
            
            self.memory_stats.append(stats)
            
            # Keep only recent stats
            if len(self.memory_stats) > self.max_stats_history:
                self.memory_stats = self.memory_stats[-self.max_stats_history//2:]
                
            # Log high memory usage
            if stats.memory_percent > self.memory_threshold:
                logger.warning(f"High memory usage detected: {stats.memory_percent:.1f}%")
                
        except Exception as e:
            logger.error(f"Error updating memory stats: {e}")
            
    async def _check_memory_pressure(self):
        """Check for memory pressure and trigger emergency cleanup if needed"""
        if not self.memory_stats:
            return
            
        current_stats = self.memory_stats[-1]
        
        if current_stats.memory_percent > self.emergency_memory_threshold:
            logger.warning(f"Emergency memory cleanup triggered at {current_stats.memory_percent:.1f}%")
            await self.emergency_cleanup()
            
    async def perform_cleanup(self):
        """Perform regular memory cleanup"""
        start_time = time.time()
        initial_memory = self._get_memory_usage()
        
        try:
            # Clean up expired sessions
            sessions_cleaned = await self._cleanup_expired_sessions()
            
            # Clean up cache overflows
            caches_cleaned = await self._cleanup_cache_overflow()
            
            # Clean up callback router caches
            routers_cleaned = await self._cleanup_router_caches()
            
            # Force garbage collection
            objects_before = len(gc.get_objects())
            gc.collect()
            objects_after = len(gc.get_objects())
            objects_collected = objects_before - objects_after
            
            # Update cleanup stats
            final_memory = self._get_memory_usage()
            memory_freed = max(0, initial_memory - final_memory)
            
            self.cleanup_stats.update({
                'sessions_cleaned': self.cleanup_stats['sessions_cleaned'] + sessions_cleaned,
                'caches_cleaned': self.cleanup_stats['caches_cleaned'] + caches_cleaned,
                'objects_collected': self.cleanup_stats['objects_collected'] + objects_collected,
                'memory_freed_mb': self.cleanup_stats['memory_freed_mb'] + memory_freed,
                'last_cleanup': datetime.now(),
                'total_cleanups': self.cleanup_stats['total_cleanups'] + 1
            })
            
            cleanup_time = time.time() - start_time
            
            if sessions_cleaned > 0 or caches_cleaned > 0 or objects_collected > 0:
                logger.info(f"Cleanup completed in {cleanup_time:.2f}s: "
                          f"{sessions_cleaned} sessions, {caches_cleaned} caches, "
                          f"{objects_collected} objects, {memory_freed:.1f}MB freed")
                          
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            
    async def emergency_cleanup(self):
        """Emergency cleanup for high memory pressure"""
        if not self.emergency_cleanup_enabled:
            return
            
        logger.warning("Performing emergency memory cleanup")
        
        try:
            # Clear all router caches
            for router in self._callback_routers:
                if hasattr(router, 'clear_cache'):
                    router.clear_cache()
                    
            # Clear all database caches
            for cache in self._cache_managers:
                if hasattr(cache, 'clear_cache'):
                    await cache.clear_cache()
                    
            # Expire old sessions aggressively
            for session_manager in self._session_managers:
                if hasattr(session_manager, 'user_sessions'):
                    current_time = time.time()
                    expired_sessions = []
                    
                    for user_id, session in session_manager.user_sessions.items():
                        # Emergency cleanup: expire sessions older than 15 minutes
                        if current_time - session.get('last_activity', 0) > 900:
                            expired_sessions.append(user_id)
                            
                    for user_id in expired_sessions:
                        del session_manager.user_sessions[user_id]
                        
            # Force aggressive garbage collection
            for i in range(3):
                gc.collect()
                
            logger.warning("Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
            
    async def _cleanup_expired_sessions(self) -> int:
        """Clean up expired user sessions"""
        total_cleaned = 0
        current_time = time.time()
        
        for session_manager in self._session_managers:
            if not hasattr(session_manager, 'user_sessions'):
                continue
                
            expired_sessions = []
            for user_id, session in session_manager.user_sessions.items():
                last_activity = session.get('last_activity', 0)
                if current_time - last_activity > self.max_session_age:
                    expired_sessions.append(user_id)
                    
            for user_id in expired_sessions:
                del session_manager.user_sessions[user_id]
                total_cleaned += 1
                
        return total_cleaned
        
    async def _cleanup_cache_overflow(self) -> int:
        """Clean up cache overflows"""
        total_cleaned = 0
        
        for cache_manager in self._cache_managers:
            if not hasattr(cache_manager, '_cache'):
                continue
                
            cache_size = len(cache_manager._cache)
            if cache_size > self.max_cache_size:
                # Remove LRU entries
                if hasattr(cache_manager, '_evict_lru'):
                    cache_manager._evict_lru()
                    total_cleaned += cache_size - len(cache_manager._cache)
                    
        return total_cleaned
        
    async def _cleanup_router_caches(self) -> int:
        """Clean up callback router caches"""
        total_cleaned = 0
        
        for router in self._callback_routers:
            if hasattr(router, '_route_cache'):
                cache_size = len(router._route_cache)
                if cache_size > 100:  # Keep only 100 most recent routes
                    # Clear cache if too large
                    router.clear_cache()
                    total_cleaned += cache_size
                    
        return total_cleaned
        
    def register_session_manager(self, session_manager):
        """Register a session manager for cleanup"""
        self._session_managers.add(session_manager)
        logger.debug(f"Registered session manager: {type(session_manager).__name__}")
        
    def register_cache_manager(self, cache_manager):
        """Register a cache manager for cleanup"""
        self._cache_managers.add(cache_manager)
        logger.debug(f"Registered cache manager: {type(cache_manager).__name__}")
        
    def register_callback_router(self, router):
        """Register a callback router for cleanup"""
        self._callback_routers.add(router)
        logger.debug(f"Registered callback router: {type(router).__name__}")
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            max_memory = usage.ru_maxrss  # Peak memory usage in KB (Linux) or bytes (macOS)
            
            # Convert to MB for consistency
            if os.name == 'posix':
                return max_memory / 1024  # KB to MB on Linux
            else:
                return max_memory / (1024 * 1024)  # bytes to MB on other systems
        except:
            return 0.0
            
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        current_stats = self.memory_stats[-1] if self.memory_stats else MemoryStats()
        
        return {
            'current_memory_usage': {
                'total_gb': current_stats.total_memory,
                'used_gb': current_stats.used_memory,
                'available_gb': current_stats.available_memory,
                'usage_percent': current_stats.memory_percent,
            },
            'managed_objects': {
                'active_sessions': current_stats.active_sessions,
                'cached_objects': current_stats.cached_objects,
                'registered_session_managers': len(self._session_managers),
                'registered_cache_managers': len(self._cache_managers),
                'registered_routers': len(self._callback_routers),
            },
            'cleanup_stats': self.cleanup_stats.copy(),
            'thresholds': {
                'cleanup_interval': self.cleanup_interval,
                'max_session_age': self.max_session_age,
                'memory_threshold': self.memory_threshold,
                'emergency_threshold': self.emergency_memory_threshold,
            },
            'memory_history_size': len(self.memory_stats),
        }
        
    async def get_memory_trend(self, minutes: int = 30) -> Dict[str, Any]:
        """Get memory usage trend over specified minutes"""
        if not self.memory_stats:
            return {}
            
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_stats = [s for s in self.memory_stats if s.timestamp > cutoff_time]
        
        if len(recent_stats) < 2:
            return {'error': 'Insufficient data for trend analysis'}
            
        start_memory = recent_stats[0].memory_percent
        end_memory = recent_stats[-1].memory_percent
        trend = end_memory - start_memory
        
        avg_memory = sum(s.memory_percent for s in recent_stats) / len(recent_stats)
        max_memory = max(s.memory_percent for s in recent_stats)
        min_memory = min(s.memory_percent for s in recent_stats)
        
        return {
            'trend_percent': trend,
            'trend_direction': 'increasing' if trend > 1 else 'decreasing' if trend < -1 else 'stable',
            'average_usage': avg_memory,
            'max_usage': max_memory,
            'min_usage': min_memory,
            'data_points': len(recent_stats),
            'time_span_minutes': minutes,
        }
        
    async def force_cleanup(self):
        """Force immediate cleanup"""
        await self.perform_cleanup()
        
    async def shutdown(self):
        """Shutdown memory manager and cleanup tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        if self._monitoring_task:
            self._monitoring_task.cancel()
            
        # Final cleanup
        await self.perform_cleanup()
        
        logger.info("MemoryManager shut down successfully")
        
    def __del__(self):
        """Cleanup when memory manager is destroyed"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()


# Global memory manager instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

def reset_memory_manager():
    """Reset global memory manager (useful for testing)"""
    global _memory_manager
    if _memory_manager:
        asyncio.create_task(_memory_manager.shutdown())
    _memory_manager = None