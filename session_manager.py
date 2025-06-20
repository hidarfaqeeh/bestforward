#!/usr/bin/env python3
"""
Session Manager - Secure encrypted session storage and management
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger

class SessionManager:
    """Secure session storage and management"""
    
    def __init__(self, session_file: str = "secure_session.enc"):
        self.session_file = Path(session_file)
        self.backup_file = Path("session_backup.enc")
        self._fernet = None
        self._master_key = None
        
    def _generate_key_from_machine(self) -> bytes:
        """Generate encryption key based on machine characteristics"""
        try:
            # Use bot token and machine info to create unique key
            bot_token = os.environ.get('BOT_TOKEN', 'default_fallback')
            
            # Get machine-specific info
            import platform
            import psutil
            
            machine_info = f"{platform.node()}{platform.machine()}{bot_token}"
            
            # Add system info if available
            try:
                machine_info += f"{psutil.boot_time()}"
            except:
                pass
                
            # Create salt from machine info
            salt = hashlib.sha256(machine_info.encode()).digest()[:16]
            
            # Generate key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(machine_info.encode()))
            return key
            
        except Exception as e:
            logger.warning(f"Could not generate machine-specific key: {e}")
            # Fallback to bot token based key
            fallback_key = hashlib.sha256(bot_token.encode()).digest()
            return base64.urlsafe_b64encode(fallback_key)
    
    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher"""
        if self._fernet is None:
            key = self._generate_key_from_machine()
            self._fernet = Fernet(key)
        return self._fernet
    
    def save_session(self, session_string: str, user_id: int = None, metadata: Dict[str, Any] = None) -> bool:
        """Save encrypted session to file"""
        try:
            from datetime import datetime
            
            session_data = {
                'session': session_string,
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Encrypt data
            cipher = self._get_cipher()
            json_data = json.dumps(session_data)
            encrypted_data = cipher.encrypt(json_data.encode())
            
            # Save to main file
            with open(self.session_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Create backup
            try:
                with open(self.backup_file, 'wb') as f:
                    f.write(encrypted_data)
            except Exception as e:
                logger.warning(f"Could not create session backup: {e}")
            
            logger.success(f"Session saved securely to {self.session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self) -> Optional[str]:
        """Load and decrypt session from file"""
        for session_file in [self.session_file, self.backup_file]:
            try:
                if session_file.exists():
                    with open(session_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    # Decrypt data
                    cipher = self._get_cipher()
                    decrypted_data = cipher.decrypt(encrypted_data)
                    session_data = json.loads(decrypted_data.decode())
                    
                    session_string = session_data.get('session')
                    if session_string:
                        logger.success(f"Session loaded from {session_file}")
                        return session_string
                        
            except Exception as e:
                logger.warning(f"Could not load session from {session_file}: {e}")
                continue
        
        logger.warning("No valid encrypted session found")
        return None
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get session metadata without exposing the actual session"""
        for session_file in [self.session_file, self.backup_file]:
            try:
                if session_file.exists():
                    with open(session_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    cipher = self._get_cipher()
                    decrypted_data = cipher.decrypt(encrypted_data)
                    session_data = json.loads(decrypted_data.decode())
                    
                    # Return metadata without session string
                    info = {
                        'user_id': session_data.get('user_id'),
                        'created_at': session_data.get('created_at'),
                        'metadata': session_data.get('metadata', {}),
                        'file_size': session_file.stat().st_size,
                        'source_file': str(session_file)
                    }
                    
                    return info
                    
            except Exception as e:
                logger.warning(f"Could not get session info from {session_file}: {e}")
                continue
        
        return None
    
    def delete_session(self) -> bool:
        """Securely delete session files"""
        deleted = False
        
        for session_file in [self.session_file, self.backup_file]:
            try:
                if session_file.exists():
                    # Overwrite with random data before deletion
                    file_size = session_file.stat().st_size
                    with open(session_file, 'wb') as f:
                        f.write(os.urandom(file_size))
                    
                    session_file.unlink()
                    logger.info(f"Session file {session_file} securely deleted")
                    deleted = True
                    
            except Exception as e:
                logger.error(f"Could not delete {session_file}: {e}")
        
        return deleted
    
    def verify_session_integrity(self) -> bool:
        """Verify session file integrity"""
        try:
            session = self.load_session()
            return session is not None and len(session) > 100
        except:
            return False
    
    def get_unified_session(self) -> str:
        """Get session from unified storage - single source of truth"""
        
        # Always try encrypted file first (our single source of truth)
        file_session = self.load_session()
        if file_session:
            logger.info("Using session from unified encrypted storage")
            return file_session
        
        # If no encrypted file, migrate from any available source
        logger.info("No unified session found, checking for migration sources...")
        
        # Check environment variable
        env_session = os.environ.get('STRING_SESSION')
        if env_session and len(env_session) > 100:
            logger.info("Migrating session from environment variable to unified storage")
            if self.save_session(env_session, metadata={'migrated_from': 'environment_variable'}):
                logger.success("Session migrated from environment variable")
                return env_session
        
        # Check plain text files
        for txt_file in ['new_session.txt', 'userbot_session.txt']:
            try:
                txt_path = Path(txt_file)
                if txt_path.exists():
                    session = txt_path.read_text().strip()
                    if session and len(session) > 100:
                        logger.info(f"Migrating session from {txt_file} to unified storage")
                        if self.save_session(session, metadata={'migrated_from': txt_file}):
                            logger.success(f"Session migrated from {txt_file}")
                            # Remove the text file after successful migration
                            try:
                                txt_path.unlink()
                                logger.info(f"Removed {txt_file} after migration to unified storage")
                            except:
                                logger.warning(f"Could not remove {txt_file}")
                            return session
            except Exception as e:
                logger.warning(f"Could not migrate from {txt_file}: {e}")
        
        logger.error("No valid session found from any source")
        return None
    
    def update_from_new_session(self, new_session: str, user_id: int = None) -> bool:
        """Update stored session with new one"""
        try:
            # Update encrypted file
            if self.save_session(new_session, user_id):
                # Also update environment variable for current process
                os.environ['STRING_SESSION'] = new_session
                logger.success("Session updated in both encrypted file and environment")
                return True
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
        
        return False

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    if not hasattr(get_session_manager, '_instance'):
        get_session_manager._instance = SessionManager()
    return get_session_manager._instance

# Test function
def test_session_manager():
    """Test session manager functionality"""
    manager = SessionManager("test_session.enc")
    
    # Test data
    test_session = "1BJWap1wBuyr2V1ADIRVkiQfMCPwjEYbqtxP0d06_o2QqYAjZr_YKSPQ8ITQZbVOT9K03mQ"
    
    print("Testing Session Manager...")
    
    # Test save
    if manager.save_session(test_session, user_id=12345):
        print("✅ Save test passed")
    else:
        print("❌ Save test failed")
    
    # Test load
    loaded = manager.load_session()
    if loaded == test_session:
        print("✅ Load test passed")
    else:
        print("❌ Load test failed")
    
    # Test info
    info = manager.get_session_info()
    if info:
        print(f"✅ Info test passed: {info}")
    else:
        print("❌ Info test failed")
    
    # Cleanup
    manager.delete_session()
    print("🧹 Test cleanup completed")

if __name__ == "__main__":
    test_session_manager()