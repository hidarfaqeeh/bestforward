"""
Security Manager - Authentication and access control
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from cryptography.fernet import Fernet
from loguru import logger

from database import Database


class SecurityManager:
    """Security manager for user authentication and access control"""
    
    def __init__(self, database: Database, encryption_key: str = None):
        self.database = database
        self.encryption_key = encryption_key or "your-32-char-encryption-key-here"
        self.cipher_suite = Fernet(self._prepare_key(self.encryption_key))
        
        # Access control
        self.admin_users: Set[int] = set()
        self.authorized_users: Set[int] = set()
        self.banned_users: Set[int] = set()
        
        # Rate limiting
        self.user_requests: Dict[int, List[float]] = {}
        self.rate_limit_window = 60  # 1 minute
        self.max_requests_per_window = 30
        
        # Session management
        self.user_sessions: Dict[int, Dict[str, any]] = {}
        self.session_timeout = 3600  # 1 hour
        
        # Security events tracking
        self.security_events: List[Dict[str, any]] = []
        self.max_security_events = 1000
        
    async def initialize(self):
        """Initialize security manager"""
        try:
            await self._load_user_permissions()
            await self._sync_admin_users_from_config()
            logger.success("Security manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {e}")
            raise
    
    def _prepare_key(self, key: str) -> bytes:
        """Prepare encryption key"""
        if len(key) < 32:
            key = key.ljust(32, '0')
        elif len(key) > 32:
            key = key[:32]
        
        # Generate Fernet key from the provided key
        key_hash = hashlib.sha256(key.encode()).digest()
        import base64
        return base64.urlsafe_b64encode(key_hash)
    
    async def _sync_admin_users_from_config(self):
        """Sync admin users from environment variables"""
        try:
            # Get admin user IDs from config
            import os
            admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
            
            if not admin_ids_str:
                logger.warning("No ADMIN_USER_IDS configured in environment")
                return
            
            # Parse admin IDs
            try:
                admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
            except ValueError as e:
                logger.error(f"Invalid ADMIN_USER_IDS format: {e}")
                return
            
            # Add each admin user to the system
            for user_id in admin_ids:
                try:
                    # Check if user exists in database
                    existing_user = await self.database.get_user_by_id(user_id)
                    
                    if existing_user:
                        # Update existing user to admin
                        if not existing_user.get('is_admin', False):
                            await self.database.execute_command(
                                "UPDATE users SET is_admin = true WHERE telegram_id = $1",
                                user_id
                            )
                            logger.info(f"Updated existing user {user_id} to admin")
                        
                        # Update cache
                        self.authorized_users.add(user_id)
                        self.admin_users.add(user_id)
                    else:
                        # Create new admin user
                        user_data = {
                            "telegram_id": user_id,
                            "username": None,
                            "first_name": f"Admin_{user_id}",
                            "last_name": None,
                            "is_admin": True,
                            "is_active": True,
                            "language": "ar"
                        }
                        
                        await self.database.create_or_update_user(user_data)
                        
                        # Update cache
                        self.authorized_users.add(user_id)
                        self.admin_users.add(user_id)
                        
                        logger.info(f"Created new admin user: {user_id}")
                        
                except Exception as user_error:
                    logger.error(f"Failed to sync admin user {user_id}: {user_error}")
                    # Add to cache anyway for immediate access
                    self.authorized_users.add(user_id)
                    self.admin_users.add(user_id)
            
            logger.success(f"Synced {len(admin_ids)} admin users from environment config")
            
        except Exception as e:
            logger.error(f"Failed to sync admin users from config: {e}")
    
    async def _load_user_permissions(self):
        """Load user permissions from database"""
        try:
            users = await self.database.execute_query(
                "SELECT telegram_id, is_admin FROM users WHERE is_active = true"
            )
            
            for user in users:
                user_id = user["telegram_id"]
                self.authorized_users.add(user_id)
                
                if user["is_admin"]:
                    self.admin_users.add(user_id)
            
            logger.info(f"Loaded permissions for {len(self.authorized_users)} users "
                       f"({len(self.admin_users)} admins)")
            
        except Exception as e:
            logger.error(f"Failed to load user permissions: {e}")
    
    async def verify_user_access(self, user_id: int) -> bool:
        """Verify if user has access to the bot"""
        try:
            # Check if user is banned
            if user_id in self.banned_users:
                await self._log_security_event(user_id, "access_denied", "User is banned")
                return False

            # Check rate limiting
            if not await self._check_rate_limit(user_id):
                await self._log_security_event(user_id, "rate_limit_exceeded", 
                                             "User exceeded rate limit")
                return False

            # Check if user is in ADMIN_USER_IDS environment variable (immediate access)
            import os
            admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
            if admin_ids_str:
                try:
                    admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
                    if user_id in admin_ids:
                        # Add to cache if not already there
                        self.authorized_users.add(user_id)
                        self.admin_users.add(user_id)
                        return True
                except ValueError:
                    pass  # Invalid format, continue with normal checks

            # Check if user is authorized in cache
            if user_id not in self.authorized_users:
                # Check database for new users
                user = await self.database.get_user_by_id(user_id)
                if user and user["is_active"]:
                    self.authorized_users.add(user_id)
                    if user["is_admin"]:
                        self.admin_users.add(user_id)
                    return True
                
                await self._log_security_event(user_id, "unauthorized_access", 
                                             "User not authorized")
                return False

            return True

        except Exception as e:
            logger.error(f"Error verifying user access for {user_id}: {e}")
            return False
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admin_users
    
    async def add_admin(self, user_id: int) -> bool:
        """Add user as admin"""
        try:
            # Update database
            await self.database.execute_command(
                "UPDATE users SET is_admin = true WHERE telegram_id = $1",
                user_id
            )
            
            # Update cache
            self.admin_users.add(user_id)
            self.authorized_users.add(user_id)
            
            await self._log_security_event(user_id, "admin_added", "User promoted to admin")
            logger.info(f"Added admin user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add admin {user_id}: {e}")
            return False
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove user from admin"""
        try:
            # Update database
            await self.database.execute_command(
                "UPDATE users SET is_admin = false WHERE telegram_id = $1",
                user_id
            )
            
            # Update cache
            self.admin_users.discard(user_id)
            
            await self._log_security_event(user_id, "admin_removed", "User demoted from admin")
            logger.info(f"Removed admin user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove admin {user_id}: {e}")
            return False
    
    async def ban_user(self, user_id: int, reason: str = "") -> bool:
        """Ban user from using the bot"""
        try:
            # Update database
            await self.database.execute_command(
                "UPDATE users SET is_active = false WHERE telegram_id = $1",
                user_id
            )
            
            # Update cache
            self.banned_users.add(user_id)
            self.authorized_users.discard(user_id)
            self.admin_users.discard(user_id)
            
            await self._log_security_event(user_id, "user_banned", f"User banned: {reason}")
            logger.warning(f"Banned user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
            return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban user"""
        try:
            # Update database
            await self.database.execute_command(
                "UPDATE users SET is_active = true WHERE telegram_id = $1",
                user_id
            )
            
            # Update cache
            self.banned_users.discard(user_id)
            self.authorized_users.add(user_id)
            
            await self._log_security_event(user_id, "user_unbanned", "User unbanned")
            logger.info(f"Unbanned user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
            return False
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        try:
            current_time = time.time()
            
            # Get user's request history
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            
            user_requests = self.user_requests[user_id]
            
            # Remove old requests outside the window
            cutoff_time = current_time - self.rate_limit_window
            user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
            
            # Check if user exceeded rate limit
            if len(user_requests) >= self.max_requests_per_window:
                return False
            
            # Add current request
            user_requests.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {user_id}: {e}")
            return True  # Allow on error
    
    async def create_user_session(self, user_id: int, session_data: Dict[str, any] = None) -> str:
        """Create user session"""
        try:
            session_id = self._generate_session_id(user_id)
            session = {
                "user_id": user_id,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=self.session_timeout),
                "data": session_data or {}
            }
            
            self.user_sessions[user_id] = session
            
            await self._log_security_event(user_id, "session_created", "User session created")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session for {user_id}: {e}")
            return ""
    
    async def validate_user_session(self, user_id: int) -> bool:
        """Validate user session"""
        try:
            if user_id not in self.user_sessions:
                return False
            
            session = self.user_sessions[user_id]
            
            # Check if session expired
            if datetime.now() > session["expires_at"]:
                del self.user_sessions[user_id]
                await self._log_security_event(user_id, "session_expired", "User session expired")
                return False
            
            # Extend session
            session["expires_at"] = datetime.now() + timedelta(seconds=self.session_timeout)
            return True
            
        except Exception as e:
            logger.error(f"Error validating session for {user_id}: {e}")
            return False
    
    async def destroy_user_session(self, user_id: int):
        """Destroy user session"""
        try:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
                await self._log_security_event(user_id, "session_destroyed", "User session destroyed")
                
        except Exception as e:
            logger.error(f"Error destroying session for {user_id}: {e}")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return encrypted_data
    
    def _generate_session_id(self, user_id: int) -> str:
        """Generate session ID"""
        data = f"{user_id}_{time.time()}_{self.encryption_key}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _log_security_event(self, user_id: int, event_type: str, description: str):
        """Log security event"""
        try:
            event = {
                "user_id": user_id,
                "event_type": event_type,
                "description": description,
                "timestamp": datetime.now(),
                "ip_address": None  # Could be added if available
            }
            
            self.security_events.append(event)
            
            # Keep only recent events
            if len(self.security_events) > self.max_security_events:
                self.security_events = self.security_events[-self.max_security_events//2:]
            
            # Log critical events
            if event_type in ["unauthorized_access", "user_banned", "rate_limit_exceeded"]:
                logger.warning(f"Security event - {event_type}: {description} (User: {user_id})")
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    async def get_security_stats(self) -> Dict[str, any]:
        """Get security statistics"""
        try:
            # Count events by type in last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_events = [e for e in self.security_events if e["timestamp"] > cutoff_time]
            
            event_counts = {}
            for event in recent_events:
                event_type = event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "total_authorized_users": len(self.authorized_users),
                "total_admin_users": len(self.admin_users),
                "total_banned_users": len(self.banned_users),
                "active_sessions": len(self.user_sessions),
                "security_events_24h": len(recent_events),
                "event_types_24h": event_counts,
                "rate_limited_users": len([uid for uid, reqs in self.user_requests.items() 
                                         if len(reqs) >= self.max_requests_per_window])
            }
            
        except Exception as e:
            logger.error(f"Error getting security stats: {e}")
            return {}
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            current_time = datetime.now()
            expired_users = []
            
            for user_id, session in self.user_sessions.items():
                if current_time > session["expires_at"]:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.user_sessions[user_id]
                await self._log_security_event(user_id, "session_cleanup", "Expired session cleaned up")
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """Get user permissions"""
        return {
            "is_authorized": user_id in self.authorized_users,
            "is_admin": user_id in self.admin_users,
            "is_banned": user_id in self.banned_users,
            "has_session": user_id in self.user_sessions
        }
    
    async def verify_admin_action(self, admin_id: int, action: str, target_id: int = None) -> bool:
        """Verify admin action authorization"""
        try:
            # Check if user is admin
            if not await self.is_admin(admin_id):
                await self._log_security_event(admin_id, "unauthorized_admin_action", 
                                             f"Non-admin attempted: {action}")
                return False
            
            # Log admin action
            description = f"Admin action: {action}"
            if target_id:
                description += f" (Target: {target_id})"
            
            await self._log_security_event(admin_id, "admin_action", description)
            return True
            
        except Exception as e:
            logger.error(f"Error verifying admin action: {e}")
            return False
