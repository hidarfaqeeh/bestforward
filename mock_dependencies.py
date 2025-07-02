"""
Mock dependencies for testing without full installation
"""

import sys
from typing import Any, Dict, List, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone


class MockAsyncSession:
    """Mock SQLAlchemy AsyncSession"""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def execute(self, query, *args, **kwargs):
        return MockResult()
    
    async def commit(self):
        pass
    
    async def rollback(self):
        pass
    
    def close(self):
        pass


class MockResult:
    """Mock SQLAlchemy Result"""
    
    def fetchall(self):
        return []
    
    def fetchone(self):
        return None
    
    def first(self):
        return None
    
    def scalars(self):
        return MockScalars()
    
    def scalar_one_or_none(self):
        return None
    
    def mappings(self):
        return MockMappings()


class MockScalars:
    """Mock SQLAlchemy Scalars"""
    
    def all(self):
        return []
    
    def first(self):
        return None


class MockMappings:
    """Mock SQLAlchemy Mappings"""
    
    def all(self):
        return []
    
    def first(self):
        return None


class MockEngine:
    """Mock SQLAlchemy Engine"""
    
    def __init__(self, *args, **kwargs):
        pass
    
    def dispose(self):
        pass


class MockAsyncEngine(MockEngine):
    """Mock SQLAlchemy AsyncEngine"""
    pass


def mock_async_sessionmaker(*args, **kwargs):
    """Mock async_sessionmaker"""
    return lambda: MockAsyncSession()


def mock_create_async_engine(*args, **kwargs):
    """Mock create_async_engine"""
    return MockAsyncEngine()


def mock_create_engine(*args, **kwargs):
    """Mock create_engine"""
    return MockEngine()


def mock_text(query: str):
    """Mock text function"""
    return query


class MockDeclarativeBase:
    """Mock SQLAlchemy DeclarativeBase"""
    
    def __init__(self):
        pass
    
    metadata = Mock()
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()


def mock_declarative_base():
    """Mock declarative_base function"""
    return MockDeclarativeBase


# Mock SQLAlchemy module
class MockSQLAlchemy:
    """Mock SQLAlchemy module"""
    
    class ext:
        class asyncio:
            AsyncSession = MockAsyncSession
            async_sessionmaker = staticmethod(mock_async_sessionmaker)
            create_async_engine = staticmethod(mock_create_async_engine)
    
    class orm:
        declarative_base = staticmethod(mock_declarative_base)
        sessionmaker = Mock
        Session = Mock
        DeclarativeBase = MockDeclarativeBase  # This is what we need!
    
    text = staticmethod(mock_text)
    create_engine = staticmethod(mock_create_engine)
    Integer = Mock
    String = Mock  
    Text = Mock
    Boolean = Mock
    DateTime = Mock
    JSON = Mock
    MetaData = Mock
    Table = Mock
    Column = Mock


# Mock aiogram classes
class MockBot:
    """Mock aiogram Bot"""
    
    def __init__(self, token: str, **kwargs):
        self.token = token
    
    async def get_me(self):
        return {"id": 123, "username": "test_bot", "first_name": "Test"}
    
    async def send_message(self, chat_id, text, **kwargs):
        return {"message_id": 1, "text": text}
    
    async def close(self):
        pass


class MockDispatcher:
    """Mock aiogram Dispatcher"""
    
    def __init__(self):
        self.message = Mock()
        self.callback_query = Mock()
    
    async def start_polling(self, bot):
        print("Mock polling started...")


class MockCallbackQuery:
    """Mock aiogram CallbackQuery"""
    
    def __init__(self, data="test"):
        self.data = data
        self.message = Mock()
        self.from_user = Mock()
    
    async def answer(self, text="", **kwargs):
        pass


class MockMessage:
    """Mock aiogram Message"""
    
    def __init__(self, text="test", chat_id=123):
        self.text = text
        self.chat = Mock()
        self.chat.id = chat_id
        self.from_user = Mock()
    
    async def answer(self, text, **kwargs):
        pass


class MockWebhookInfo:
    """Mock aiogram WebhookInfo"""
    
    def __init__(self):
        self.url = ""
        self.has_custom_certificate = False


class MockLogger:
    """Mock loguru logger"""
    
    def info(self, msg, *args, **kwargs):
        print(f"INFO: {msg}")
    
    def error(self, msg, *args, **kwargs):
        print(f"ERROR: {msg}")
    
    def warning(self, msg, *args, **kwargs):
        print(f"WARNING: {msg}")
    
    def success(self, msg, *args, **kwargs):
        print(f"SUCCESS: {msg}")
    
    def debug(self, msg, *args, **kwargs):
        print(f"DEBUG: {msg}")


class MockTimezone:
    """Mock pytz timezone"""
    
    def __init__(self, name):
        self.name = name
    
    def localize(self, dt):
        return dt.replace(tzinfo=timezone.utc)
    
    def normalize(self, dt):
        return dt


def install_mocks():
    """Install all mock modules"""
    
    # Mock SQLAlchemy
    sqlalchemy_mock = MockSQLAlchemy()
    sys.modules['sqlalchemy'] = sqlalchemy_mock
    sys.modules['sqlalchemy.ext'] = MockSQLAlchemy.ext
    sys.modules['sqlalchemy.ext.asyncio'] = MockSQLAlchemy.ext.asyncio
    sys.modules['sqlalchemy.orm'] = MockSQLAlchemy.orm
    
    # Mock aiogram and its submodules
    aiogram_mock = Mock()
    aiogram_mock.Bot = MockBot
    aiogram_mock.Dispatcher = MockDispatcher
    aiogram_mock.Router = Mock
    aiogram_mock.F = Mock()
    
    # Mock aiogram submodules
    sys.modules['aiogram'] = aiogram_mock
    sys.modules['aiogram.client'] = Mock()
    sys.modules['aiogram.client.session'] = Mock()
    sys.modules['aiogram.client.default'] = Mock()
    sys.modules['aiogram.filters'] = Mock()
    sys.modules['aiogram.types'] = Mock()
    sys.modules['aiogram.exceptions'] = Mock()
    sys.modules['aiogram.webhook'] = Mock()
    sys.modules['aiogram.webhook.aiohttp_server'] = Mock()
    sys.modules['aiogram.utils'] = Mock()
    sys.modules['aiogram.utils.keyboard'] = Mock()
    sys.modules['aiogram.fsm'] = Mock()
    sys.modules['aiogram.fsm.context'] = Mock()
    sys.modules['aiogram.fsm.state'] = Mock()
    sys.modules['aiogram.enums'] = Mock()
    
    # Mock loguru
    loguru_mock = Mock()
    loguru_mock.logger = MockLogger()
    sys.modules['loguru'] = loguru_mock
    
    # Mock timezone
    pytz_mock = Mock()
    pytz_mock.timezone = MockTimezone
    pytz_mock.UTC = MockTimezone('UTC')
    sys.modules['pytz'] = pytz_mock
    
    # Mock cryptography and submodules
    cryptography_mock = Mock()
    cryptography_mock.fernet = Mock()
    cryptography_mock.fernet.Fernet = Mock
    sys.modules['cryptography'] = cryptography_mock
    sys.modules['cryptography.fernet'] = cryptography_mock.fernet
    
    # Mock telethon and submodules
    telethon_mock = Mock()
    telethon_mock.sessions = Mock()
    telethon_mock.sessions.StringSession = Mock
    telethon_mock.TelegramClient = Mock
    sys.modules['telethon'] = telethon_mock
    sys.modules['telethon.sessions'] = telethon_mock.sessions
    
    # Mock pyrogram and submodules
    pyrogram_mock = Mock()
    pyrogram_mock.errors = Mock()
    pyrogram_mock.types = Mock()
    pyrogram_mock.Client = Mock
    sys.modules['pyrogram'] = pyrogram_mock
    sys.modules['pyrogram.errors'] = pyrogram_mock.errors
    sys.modules['pyrogram.types'] = pyrogram_mock.types
    
    # Mock other dependencies
    sys.modules['psutil'] = Mock()
    sys.modules['asyncpg'] = Mock()
    sys.modules['aiohttp'] = Mock()
    sys.modules['aiohttp.web'] = Mock()
    sys.modules['googletrans'] = Mock()
    sys.modules['dotenv'] = Mock()  # python-dotenv
    
    print("✅ Complete mock dependencies installed successfully!")


if __name__ == "__main__":
    install_mocks()
    print("Complete mock dependencies ready for testing")