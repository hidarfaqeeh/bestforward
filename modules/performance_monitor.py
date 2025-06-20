"""
Performance Monitor - Advanced system monitoring and analytics
"""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from loguru import logger

from database import Database


class PerformanceMonitor:
    """Advanced performance monitoring and analytics system"""
    
    def __init__(self, database: Database):
        self.database = database
        self.running = False
        
        # Performance metrics
        self.message_stats = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.channel_activity = defaultdict(lambda: defaultdict(int))
        
        # System metrics
        self.cpu_usage_history = deque(maxlen=60)  # Last 60 readings
        self.memory_usage_history = deque(maxlen=60)
        self.network_stats = defaultdict(int)
        
        # Task performance tracking
        self.task_performance = defaultdict(lambda: {
            'total_messages': 0,
            'successful_forwards': 0,
            'failed_forwards': 0,
            'avg_processing_time': 0,
            'last_activity': None
        })
        
        logger.info("Performance monitor initialized")
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting performance monitoring")
        
        # Start background monitoring tasks
        asyncio.create_task(self._system_metrics_collector())
        asyncio.create_task(self._database_stats_collector())
        asyncio.create_task(self._cleanup_old_data())
        
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        logger.info("Performance monitoring stopped")
    
    def record_message_processed(self, task_id: int, processing_time: float, success: bool):
        """Record message processing metrics"""
        self.message_stats['total_processed'] += 1
        self.response_times.append(processing_time)
        
        # Update task-specific metrics
        task_perf = self.task_performance[task_id]
        task_perf['total_messages'] += 1
        task_perf['last_activity'] = datetime.now()
        
        if success:
            self.message_stats['successful'] += 1
            task_perf['successful_forwards'] += 1
        else:
            self.message_stats['failed'] += 1
            task_perf['failed_forwards'] += 1
            
        # Update average processing time
        if task_perf['total_messages'] > 0:
            current_avg = task_perf['avg_processing_time']
            new_avg = (current_avg * (task_perf['total_messages'] - 1) + processing_time) / task_perf['total_messages']
            task_perf['avg_processing_time'] = new_avg
    
    def record_error(self, error_type: str, task_id: Optional[int] = None):
        """Record error occurrence"""
        self.error_counts[error_type] += 1
        self.message_stats['errors'] += 1
        
        if task_id:
            self.task_performance[task_id]['failed_forwards'] += 1
    
    def record_channel_activity(self, channel_id: int, activity_type: str):
        """Record channel-specific activity"""
        self.channel_activity[channel_id][activity_type] += 1
        self.channel_activity[channel_id]['last_activity'] = datetime.now().isoformat()
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            # Calculate success rate
            total = self.message_stats['total_processed']
            success_rate = (self.message_stats['successful'] / total * 100) if total > 0 else 0
            
            # Calculate response time statistics
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                max_response_time = max(self.response_times)
                min_response_time = min(self.response_times)
            else:
                avg_response_time = max_response_time = min_response_time = 0
            
            # Get current system metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database statistics
            db_stats = await self._get_database_statistics()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'message_processing': {
                    'total_processed': total,
                    'successful': self.message_stats['successful'],
                    'failed': self.message_stats['failed'],
                    'errors': self.message_stats['errors'],
                    'success_rate': round(success_rate, 2)
                },
                'performance_metrics': {
                    'avg_response_time_ms': round(avg_response_time * 1000, 2),
                    'max_response_time_ms': round(max_response_time * 1000, 2),
                    'min_response_time_ms': round(min_response_time * 1000, 2),
                    'total_response_samples': len(self.response_times)
                },
                'system_resources': {
                    'cpu_usage_percent': cpu_percent,
                    'memory_usage_percent': memory.percent,
                    'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                    'disk_usage_percent': disk.percent,
                    'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2)
                },
                'database': db_stats,
                'error_breakdown': dict(self.error_counts),
                'task_performance': self._format_task_performance(),
                'channel_activity': self._format_channel_activity()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Recent activity (last 5 minutes)
            recent_messages = sum(1 for t in self.response_times if time.time() - t < 300)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'recent_messages_5min': recent_messages,
                'active_tasks': len([t for t in self.task_performance.values() 
                                   if t['last_activity'] and 
                                   datetime.now() - datetime.fromisoformat(t['last_activity'].isoformat()) < timedelta(minutes=10)])
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {'error': str(e)}
    
    async def _system_metrics_collector(self):
        """Background task to collect system metrics"""
        while self.running:
            try:
                # Collect CPU and memory usage
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                self.cpu_usage_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'value': cpu_percent
                })
                
                self.memory_usage_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'value': memory.percent
                })
                
                # Network statistics
                net_io = psutil.net_io_counters()
                self.network_stats['bytes_sent'] = net_io.bytes_sent
                self.network_stats['bytes_recv'] = net_io.bytes_recv
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error in system metrics collector: {e}")
                await asyncio.sleep(60)
    
    async def _database_stats_collector(self):
        """Collect database performance statistics"""
        while self.running:
            try:
                await self._get_database_statistics()
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in database stats collector: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self):
        """Clean up old performance data"""
        while self.running:
            try:
                # Clean up old response times (keep only last 1000)
                if len(self.response_times) > 1000:
                    # Already handled by deque maxlen
                    pass
                
                # Clean up old system metrics (keep only last hour)
                cutoff_time = datetime.now() - timedelta(hours=1)
                
                # CPU usage cleanup is handled by deque maxlen
                # Memory usage cleanup is handled by deque maxlen
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def _get_database_statistics(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        try:
            # Get table sizes
            table_stats = {}
            tables = ['forwarding_tasks', 'task_sources', 'task_targets', 'forwarding_logs', 'message_tracking']
            
            for table in tables:
                try:
                    result = await self.database.execute_query(
                        f"SELECT COUNT(*) as count FROM {table}"
                    )
                    table_stats[table] = result[0]['count'] if result else 0
                except:
                    table_stats[table] = 0
            
            # Get recent activity
            recent_logs = await self.database.execute_query(
                "SELECT COUNT(*) as count FROM forwarding_logs WHERE created_at > NOW() - INTERVAL '1 hour'"
            )
            
            return {
                'table_sizes': table_stats,
                'recent_activity_1h': recent_logs[0]['count'] if recent_logs else 0,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'error': str(e)}
    
    def _format_task_performance(self) -> Dict[str, Any]:
        """Format task performance data for reporting"""
        formatted = {}
        for task_id, perf in self.task_performance.items():
            success_rate = 0
            if perf['total_messages'] > 0:
                success_rate = (perf['successful_forwards'] / perf['total_messages']) * 100
                
            formatted[str(task_id)] = {
                'total_messages': perf['total_messages'],
                'successful_forwards': perf['successful_forwards'],
                'failed_forwards': perf['failed_forwards'],
                'success_rate': round(success_rate, 2),
                'avg_processing_time_ms': round(perf['avg_processing_time'] * 1000, 2),
                'last_activity': perf['last_activity'].isoformat() if perf['last_activity'] else None
            }
        return formatted
    
    def _format_channel_activity(self) -> Dict[str, Any]:
        """Format channel activity data for reporting"""
        formatted = {}
        for channel_id, activity in self.channel_activity.items():
            formatted[str(channel_id)] = dict(activity)
        return formatted
    
    def get_system_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        try:
            # Component scores (0-100)
            scores = {}
            
            # Message processing health
            total = self.message_stats['total_processed']
            if total > 0:
                success_rate = (self.message_stats['successful'] / total) * 100
                scores['message_processing'] = min(success_rate, 100)
            else:
                scores['message_processing'] = 100  # No failures if no messages
            
            # System resource health
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            scores['cpu_health'] = max(100 - cpu_percent, 0)
            scores['memory_health'] = max(100 - memory.percent, 0)
            
            # Response time health (lower is better)
            if self.response_times:
                avg_response = sum(self.response_times) / len(self.response_times)
                # Score based on response time (100 = 0ms, 0 = 5s+)
                scores['response_time'] = max(100 - (avg_response * 20), 0)
            else:
                scores['response_time'] = 100
            
            # Error rate health
            error_rate = (self.message_stats['errors'] / max(total, 1)) * 100
            scores['error_rate'] = max(100 - error_rate * 10, 0)
            
            # Calculate overall health
            overall_health = sum(scores.values()) / len(scores)
            
            # Determine health status
            if overall_health >= 90:
                status = "excellent"
            elif overall_health >= 75:
                status = "good"
            elif overall_health >= 60:
                status = "fair"
            elif overall_health >= 40:
                status = "poor"
            else:
                status = "critical"
            
            return {
                'overall_score': round(overall_health, 2),
                'status': status,
                'component_scores': {k: round(v, 2) for k, v in scores.items()},
                'recommendations': self._get_health_recommendations(scores)
            }
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return {'error': str(e)}
    
    def _get_health_recommendations(self, scores: Dict[str, float]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        if scores['cpu_health'] < 70:
            recommendations.append("نصيحة: استخدام المعالج مرتفع - راقب العمليات الجارية")
        
        if scores['memory_health'] < 70:
            recommendations.append("نصيحة: استخدام الذاكرة مرتفع - فكر في إعادة تشغيل البوت")
        
        if scores['response_time'] < 70:
            recommendations.append("نصيحة: أوقات الاستجابة بطيئة - تحقق من الشبكة وقاعدة البيانات")
        
        if scores['error_rate'] < 80:
            recommendations.append("نصيحة: معدل الأخطاء مرتفع - راجع سجلات الأخطاء")
        
        if scores['message_processing'] < 90:
            recommendations.append("نصيحة: معدل نجاح معالجة الرسائل منخفض - تحقق من إعدادات المهام")
        
        if not recommendations:
            recommendations.append("النظام يعمل بشكل ممتاز!")
        
        return recommendations