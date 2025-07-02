"""
Temporary asyncpg compatibility module

This provides a minimal interface to prevent import errors.
This is a temporary solution until proper dependencies can be installed.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union


class MockConnection:
    """Mock connection for asyncpg compatibility"""
    
    async def execute(self, query: str, *args) -> str:
        return "Mock execute"
    
    async def fetch(self, query: str, *args) -> List[Dict]:
        return []
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict]:
        return None
    
    async def fetchval(self, query: str, *args) -> Any:
        return None
    
    async def executemany(self, query: str, args_list: List) -> None:
        pass
    
    async def close(self):
        pass


class MockPool:
    """Mock connection pool for asyncpg compatibility"""
    
    async def acquire(self) -> MockConnection:
        return MockConnection()
    
    async def release(self, connection: MockConnection):
        pass
    
    async def close(self):
        pass
    
    def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def connect(dsn: str = None, **kwargs) -> MockConnection:
    """Mock connect function"""
    return MockConnection()


async def create_pool(dsn: str = None, **kwargs) -> MockPool:
    """Mock create_pool function"""
    return MockPool()


# Exception classes for compatibility
class PostgresError(Exception):
    pass

class UniqueViolationError(PostgresError):
    pass

class DataError(PostgresError):
    pass

class IntegrityError(PostgresError):
    pass