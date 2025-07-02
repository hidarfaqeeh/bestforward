"""
Database management for Telegram Forwarding Bot
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg
from loguru import logger
from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class Database:
    """Database management class"""

    def __init__(self, database_url: str):
        # Store original URL
        self.original_url = database_url
        
        # Handle SSL parameters properly for Northflank/production environments
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)

        # Keep SSL parameters but handle them properly
        self.database_url = database_url
        
        # Handle different database types
        if self.database_url.startswith("sqlite"):
            self.async_database_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
            self.is_postgresql = False
        elif self.database_url.startswith("postgresql"):
            self.async_database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            self.is_postgresql = True
        else:
            self.async_database_url = self.database_url
            self.is_postgresql = "postgresql" in self.database_url
            
        self.engine = None
        self.async_session_factory = None
        self.pool = None

    async def initialize(self):
        """Initialize database connections and create tables"""
        try:
            # Create async engine with different settings for SQLite vs PostgreSQL
            if self.is_postgresql:
                # Configure engine with SSL support for production environments
                engine_args = {
                    "echo": False,
                    "pool_size": 20,
                    "max_overflow": 30,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                }
                
                # Handle SSL configuration properly for asyncpg
                import urllib.parse
                parsed = urllib.parse.urlparse(self.original_url)
                query_params = urllib.parse.parse_qs(parsed.query)
                
                if 'sslmode' in query_params:
                    ssl_mode = query_params['sslmode'][0]
                    # Remove sslmode from the async URL to prevent it being passed to asyncpg
                    filtered_params = {k: v for k, v in query_params.items() if k != 'sslmode'}
                    
                    # Rebuild the async URL without sslmode
                    if filtered_params:
                        new_query = urllib.parse.urlencode(filtered_params, doseq=True)
                        parsed_async = urllib.parse.urlparse(self.async_database_url)
                        self.async_database_url = urllib.parse.urlunparse((
                            parsed_async.scheme,
                            parsed_async.netloc,
                            parsed_async.path,
                            parsed_async.params,
                            new_query,
                            parsed_async.fragment
                        ))
                    else:
                        # Remove query entirely if only sslmode was present
                        parsed_async = urllib.parse.urlparse(self.async_database_url)
                        self.async_database_url = urllib.parse.urlunparse((
                            parsed_async.scheme,
                            parsed_async.netloc,
                            parsed_async.path,
                            parsed_async.params,
                            '',
                            parsed_async.fragment
                        ))
                    
                    # Configure SSL for SQLAlchemy engine
                    if ssl_mode == 'require':
                        engine_args["connect_args"] = {"ssl": "require"}
                    elif ssl_mode == 'prefer':
                        engine_args["connect_args"] = {"ssl": "prefer"}
                    elif ssl_mode == 'disable':
                        engine_args["connect_args"] = {"ssl": "disable"}
                
                self.engine = create_async_engine(
                    self.async_database_url,
                    **engine_args
                )
            else:
                # SQLite configuration
                self.engine = create_async_engine(
                    self.async_database_url,
                    echo=False,
                    pool_pre_ping=True,
                )

            # Create session factory
            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create connection pool only for PostgreSQL
            if self.is_postgresql:
                import urllib.parse
                parsed_url = urllib.parse.urlparse(self.original_url)

                # Extract SSL mode from query parameters and remove it from parsed URL
                query_params = urllib.parse.parse_qs(parsed_url.query)
                ssl_mode = query_params.get('sslmode', ['prefer'])[0]
                
                # Remove sslmode from query params to avoid passing it to asyncpg
                filtered_params = {k: v for k, v in query_params.items() if k != 'sslmode'}
                
                # Configure SSL context for production environments
                ssl_context = None
                if ssl_mode == 'require':
                    import ssl
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                elif ssl_mode == 'prefer':
                    ssl_context = True  # Let asyncpg handle SSL automatically
                elif ssl_mode == 'disable':
                    ssl_context = False  # Disable SSL
                else:
                    ssl_context = None  # Use asyncpg default

                # Create connection pool with proper SSL configuration
                try:
                    self.pool = await asyncpg.create_pool(
                        host=parsed_url.hostname,
                        port=parsed_url.port or 5432,
                        user=parsed_url.username,
                        password=parsed_url.password,
                        database=parsed_url.path.lstrip('/'),
                        ssl=ssl_context,
                        min_size=5,
                        max_size=20,
                        command_timeout=60
                    )
                except Exception as pool_error:
                    logger.warning(f"Failed to create connection pool with SSL context: {pool_error}")
                    # Try without SSL context as fallback
                    try:
                        self.pool = await asyncpg.create_pool(
                            host=parsed_url.hostname,
                            port=parsed_url.port or 5432,
                            user=parsed_url.username,
                            password=parsed_url.password,
                            database=parsed_url.path.lstrip('/'),
                            min_size=5,
                            max_size=20,
                            command_timeout=60
                        )
                        logger.info("Connection pool created without SSL context")
                    except Exception as fallback_error:
                        logger.error(f"Failed to create connection pool even without SSL: {fallback_error}")
                        raise
            else:
                # For SQLite, we'll use the SQLAlchemy session directly
                self.pool = None

            # Import models to ensure they're registered
            from models import (
                User, Task, Source, Target, TaskSettings, 
                ForwardingLog, TaskStatistics, UserSession,
                SystemSettings, MessageDuplicate
            )

            # First ensure users table exists before creating other tables
            await self.ensure_users_table_structure()

            # Now create all tables (this will create user_sessions with proper foreign key)
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Create additional tables for advanced features
            await self.create_advanced_tables()

            # Ensure critical columns exist before other migrations
            await self._ensure_critical_columns()

            # Add new columns if they don't exist
            await self.migrate_columns()

            # Add language column to users table if not exists
            await self.execute_command("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'ar'
            """)

            # Create additional tables for advanced features
            await self.create_advanced_tables()

            # Add missing indexes for performance
            await self.create_performance_indexes()

            logger.success("Database initialized successfully")

        except Exception as e:
            error_msg = str(e)
            if "Name or service not known" in error_msg:
                logger.error(f"Database connection failed: Cannot resolve hostname. Check network connectivity and DATABASE_URL")
                logger.error(f"Database URL: {self.original_url}")
            elif "Connection refused" in error_msg:
                logger.error(f"Database connection refused: Check if database server is running and accessible")
            elif "SSL" in error_msg or "certificate" in error_msg:
                logger.error(f"SSL/TLS connection error: {error_msg}")
                logger.error("Try adjusting SSL settings in DATABASE_URL")
            elif "sslmode" in error_msg.lower():
                logger.error(f"SSL mode parameter error: {error_msg}")
                logger.error("The sslmode parameter should be handled by the connection logic, not passed directly to asyncpg")
            else:
                logger.error(f"Failed to initialize database: {e}")
            raise

    async def ensure_users_table_structure(self):
        """Ensure users table has proper structure"""
        try:
            # First, try to drop and recreate the users table if it has issues
            try:
                # Check if the table exists and has the right structure
                result = await self.execute_query("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'id'
                """)
                
                if not result:
                    # users table doesn't have id column, need to recreate
                    logger.info("Users table missing id column, recreating...")
                    await self.execute_command("DROP TABLE IF EXISTS users CASCADE")
                    
            except Exception:
                # Table doesn't exist or query failed, that's fine
                pass
            
            # Create users table with proper structure
            await self.execute_command("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Ensured users table structure")
        except Exception as e:
            logger.warning(f"Could not ensure users table structure: {e}")

    async def _ensure_critical_columns(self):
        """Ensure critical columns exist in tables"""
        try:
            # Ensure task_type column exists in tasks table
            await self.execute_command("""
                ALTER TABLE tasks 
                ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) DEFAULT 'bot' NOT NULL
            """)
            logger.info("Ensured task_type column exists in tasks table")
        except Exception as e:
            logger.warning(f"Could not ensure task_type column in tasks table: {e}")

        # Remove invalid columns from tasks table that shouldn't be there
        try:
            # Check if source_chat column exists and remove it
            check_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' AND column_name = 'source_chat'
            """
            result = await self.execute_query(check_query)
            
            if result:
                logger.info("Found invalid 'source_chat' column in tasks table, removing it...")
                await self.execute_command("ALTER TABLE tasks DROP COLUMN IF EXISTS source_chat")
                logger.info("Removed invalid 'source_chat' column from tasks table")
                
        except Exception as e:
            logger.warning(f"Could not remove invalid source_chat column: {e}")

        # Check for other invalid columns that might exist
        try:
            # Get all columns in tasks table
            columns_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks'
            """
            existing_columns = await self.execute_query(columns_query)
            existing_column_names = [col['column_name'] for col in existing_columns] if existing_columns else []
            
            # Expected columns according to the Task model
            expected_columns = {
                'id', 'user_id', 'name', 'description', 'task_type', 
                'is_active', 'created_at', 'updated_at'
            }
            
            # Find unexpected columns
            unexpected_columns = set(existing_column_names) - expected_columns
            
            if unexpected_columns:
                logger.warning(f"Found unexpected columns in tasks table: {unexpected_columns}")
                for col in unexpected_columns:
                    try:
                        await self.execute_command(f"ALTER TABLE tasks DROP COLUMN IF EXISTS {col}")
                        logger.info(f"Removed unexpected column '{col}' from tasks table")
                    except Exception as col_error:
                        logger.warning(f"Could not remove column '{col}': {col_error}")
                        
        except Exception as e:
            logger.warning(f"Could not check for unexpected columns: {e}")

    async def migrate_columns(self):
        """Add new columns if they don't exist"""
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS length_filter_settings JSONB DEFAULT NULL
            """)
            logger.info("Added length_filter_settings column")
        except Exception as e:
            logger.warning(f"Could not add length_filter_settings column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS hashtag_settings JSONB DEFAULT NULL
            """)
            logger.info("Added hashtag_settings column")
        except Exception as e:
            logger.warning(f"Could not add hashtag_settings column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS text_cleaner_settings JSONB DEFAULT NULL
            """)
            logger.info("Added text_cleaner_settings column")
        except Exception as e:
            logger.warning(f"Could not add text_cleaner_settings column: {e}")

        # Add new filter columns
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS filter_inline_buttons BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added filter_inline_buttons column")
        except Exception as e:
            logger.warning(f"Could not add filter_inline_buttons column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS filter_duplicates BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added filter_duplicates column")
        except Exception as e:
            logger.warning(f"Could not add filter_duplicates column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS filter_language BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added filter_language column")
        except Exception as e:
            logger.warning(f"Could not add filter_language column: {e}")

        # filter_bots column removed - not implemented

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS language_filter_mode VARCHAR(50) DEFAULT 'blacklist'
            """)
            logger.info("Added language_filter_mode column")
        except Exception as e:
            logger.warning(f"Could not add language_filter_mode column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS allowed_languages JSONB DEFAULT NULL
            """)
            logger.info("Added allowed_languages column")
        except Exception as e:
            logger.warning(f"Could not add allowed_languages column: {e}")

        # filter_bots column removed - not needed

        # Add advanced forwarding options
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS manual_mode BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added manual_mode column")
        except Exception as e:
            logger.warning(f"Could not add manual_mode column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS link_preview BOOLEAN DEFAULT TRUE
            """)
            logger.info("Added link_preview column")
        except Exception as e:
            logger.warning(f"Could not add link_preview column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS pin_messages BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added pin_messages column")
        except Exception as e:
            logger.warning(f"Could not add pin_messages column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS silent_mode BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added silent_mode column")
        except Exception as e:
            logger.warning(f"Could not add silent_mode column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS sync_edits BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added sync_edits column")
        except Exception as e:
            logger.warning(f"Could not add sync_edits column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS sync_deletes BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added sync_deletes column")
        except Exception as e:
            logger.warning(f"Could not add sync_deletes column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS preserve_replies BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added preserve_replies column")
        except Exception as e:
            logger.warning(f"Could not add preserve_replies column: {e}")

        # Add advanced features columns
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS auto_translate BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added auto_translate column")
        except Exception as e:
            logger.warning(f"Could not add auto_translate column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS target_language VARCHAR(10) DEFAULT 'ar'
            """)
            logger.info("Added target_language column")
        except Exception as e:
            logger.warning(f"Could not add target_language column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS working_hours_enabled BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added working_hours_enabled column")
        except Exception as e:
            logger.warning(f"Could not add working_hours_enabled column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS start_hour INTEGER DEFAULT 0
            """)
            logger.info("Added start_hour column")
        except Exception as e:
            logger.warning(f"Could not add start_hour column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS end_hour INTEGER DEFAULT 23
            """)
            logger.info("Added end_hour column")
        except Exception as e:
            logger.warning(f"Could not add end_hour column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC'
            """)
            logger.info("Added timezone column")
        except Exception as e:
            logger.warning(f"Could not add timezone column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS recurring_post_enabled BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added recurring_post_enabled column")
        except Exception as e:
            logger.warning(f"Could not add recurring_post_enabled column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS recurring_post_content TEXT
            """)
            logger.info("Added recurring_post_content column")
        except Exception as e:
            logger.warning(f"Could not add recurring_post_content column: {e}")

        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS recurring_interval_hours INTEGER DEFAULT 24
            """)
            logger.info("Added recurring_interval_hours column")
        except Exception as e:
            logger.warning(f"Could not add recurring_interval_hours column: {e}")

        # Add formatting settings column
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS format_settings JSONB DEFAULT '{}'::jsonb
            """)
            logger.info("Added format_settings column")
        except Exception as e:
            logger.warning(f"Could not add format_settings column: {e}")

        # Add text cleaner settings column  
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS text_cleaner_settings JSONB DEFAULT '{}'::jsonb
            """)
            logger.info("Added text_cleaner_settings column")
        except Exception as e:
            logger.warning(f"Could not add text_cleaner_settings column: {e}")

        # Add replace text settings column
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS replace_text JSONB DEFAULT '{}'::jsonb
            """)
            logger.info("Added replace_text column")
        except Exception as e:
            logger.warning(f"Could not add replace_text column: {e}")

        # Add prefix/suffix settings columns
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS custom_prefix TEXT,
                ADD COLUMN IF NOT EXISTS custom_suffix TEXT
            """)
            logger.info("Added prefix/suffix columns")
        except Exception as e:
            logger.warning(f"Could not add prefix/suffix columns: {e}")

        # Add inline buttons settings columns
        try:
            await self.execute_command("""
                ALTER TABLE task_settings 
                ADD COLUMN IF NOT EXISTS inline_buttons_enabled BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS inline_buttons_config JSONB DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS inline_button_settings JSONB DEFAULT '{}'::jsonb
            """)
            logger.info("Added inline buttons columns")
        except Exception as e:
            logger.warning(f"Could not add inline buttons columns: {e}")

    async def create_advanced_tables(self):
        """Create additional tables for advanced forwarding features"""
        try:
            # Ensure tasks table exists first
            await self.execute_command("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    task_type VARCHAR(50) DEFAULT 'bot' NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Create manual_approvals table for manual forwarding mode
            await self.execute_command("""
                CREATE TABLE IF NOT EXISTS manual_approvals (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    source_chat_id BIGINT NOT NULL,
                    message_text TEXT,
                    message_type VARCHAR(50),
                    media_caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    approved_by BIGINT,
                    approved_at TIMESTAMP,
                    forwarded_message_ids JSONB DEFAULT '{}',
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """)
            logger.info("Created manual_approvals table")
        except Exception as e:
            logger.warning(f"Could not create manual_approvals table: {e}")

        try:
            # Create message_tracking table for edit/delete sync
            await self.execute_command("""
                CREATE TABLE IF NOT EXISTS message_tracking (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    source_chat_id BIGINT NOT NULL,
                    target_message_ids JSONB NOT NULL,
                    reply_to_message_id INTEGER,
                    message_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """)
            logger.info("Created message_tracking table")
        except Exception as e:
            logger.warning(f"Could not create message_tracking table: {e}")

        try:
            # Create recurring_posts table
            await self.execute_command("""
                CREATE TABLE IF NOT EXISTS recurring_posts (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    media_type VARCHAR(50),
                    media_file_id TEXT,
                    interval_hours INTEGER DEFAULT 24,
                    next_post_time TIMESTAMP,
                    last_post_time TIMESTAMP,
                    previous_message_ids JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """)
            logger.info("Created recurring_posts table")
        except Exception as e:
            logger.warning(f"Could not create recurring_posts table: {e}")

    async def create_performance_indexes(self):
        """Create performance indexes for better query speed"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_forwarding_logs_task_date ON forwarding_logs(task_id, processed_at)",
                "CREATE INDEX IF NOT EXISTS idx_message_tracking_hash ON message_tracking(message_hash)",
                "CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_active ON tasks(user_id, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_sources_task_active ON sources(task_id, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_targets_task_active ON targets(task_id, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_task_settings_task_id ON task_settings(task_id)",
                "CREATE INDEX IF NOT EXISTS idx_message_duplicates_task_hash ON message_duplicates(task_id, message_hash)",
                "CREATE INDEX IF NOT EXISTS idx_manual_approvals_status ON manual_approvals(status, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_task_statistics_task ON task_statistics(task_id)",
                "CREATE INDEX IF NOT EXISTS idx_forwarding_logs_status ON forwarding_logs(status, processed_at)"
            ]
            
            for index_sql in indexes:
                try:
                    await self.execute_command(index_sql)
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")
            
            logger.info("Performance indexes created")
            
        except Exception as e:
            logger.error(f"Error creating performance indexes: {e}")

    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute raw SQL query"""
        if self.is_postgresql and self.pool:
            async with self.pool.acquire() as conn:
                try:
                    rows = await conn.fetch(query, *args)
                    return [dict(row) for row in rows]
                except Exception as e:
                    logger.error(f"Query execution failed: {e}")
                    raise
        else:
            # Use SQLAlchemy for SQLite or when no pool available
            async with self.get_session() as session:
                try:
                    from sqlalchemy import text
                    result = await session.execute(text(query), dict(enumerate(args, 1)))
                    rows = result.fetchall()
                    return [dict(row._mapping) for row in rows]
                except Exception as e:
                    logger.error(f"Query execution failed: {e}")
                    raise

    async def execute_command(self, command: str, *args) -> str:
        """Execute SQL command (INSERT, UPDATE, DELETE)"""
        if self.is_postgresql and self.pool:
            async with self.pool.acquire() as conn:
                try:
                    result = await conn.execute(command, *args)
                    return result
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    raise
        else:
            # Use SQLAlchemy for SQLite or when no pool available
            async with self.get_session() as session:
                try:
                    from sqlalchemy import text
                    result = await session.execute(text(command), dict(enumerate(args, 1)))
                    return str(result.rowcount)
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    raise

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        query = """
            SELECT * FROM users WHERE telegram_id = $1
        """
        result = await self.execute_query(query, user_id)
        return result[0] if result else None

    async def create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user"""
        query = """
            INSERT INTO users (telegram_id, username, first_name, last_name, language, is_admin, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
            ON CONFLICT (telegram_id) 
            DO UPDATE SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language = EXCLUDED.language,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
            RETURNING *
        """
        result = await self.execute_query(
            query,
            user_data["telegram_id"],
            user_data.get("username"),
            user_data.get("first_name"),
            user_data.get("last_name"),
            user_data.get("language", "ar"),
            user_data.get("is_admin", False),
            user_data.get("is_active", True)
        )
        return result[0] if result else None

    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active forwarding tasks with sources and targets"""
        try:
            # Get active tasks
            tasks_query = """
                SELECT * FROM tasks WHERE is_active = true ORDER BY created_at DESC
            """
            tasks = await self.execute_query(tasks_query)

            # For each task, get sources and targets
            for task in tasks:
                task_id = task['id']

                # Get sources
                sources_query = "SELECT * FROM sources WHERE task_id = $1"
                sources = await self.execute_query(sources_query, task_id)
                task['sources'] = sources

                # Get targets
                targets_query = "SELECT * FROM targets WHERE task_id = $1"
                targets = await self.execute_query(targets_query, task_id)
                task['targets'] = targets

            return tasks

        except Exception as e:
            logger.error(f"Failed to get active tasks with sources/targets: {e}")
            return []

    async def get_task_sources(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all sources for a task"""
        query = """
            SELECT * FROM sources 
            WHERE task_id = $1 
            ORDER BY created_at DESC
        """
        return await self.execute_query(query, task_id)

    async def get_task_targets(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all targets for a task"""
        query = """
            SELECT * FROM targets 
            WHERE task_id = $1 
            ORDER BY created_at DESC
        """
        return await self.execute_query(query, task_id)

    async def get_task_settings(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task settings including all media type columns"""
        query = """
            SELECT task_id, forward_mode, preserve_sender, add_caption, custom_caption,
                   filter_media, filter_text, filter_forwarded, filter_links, keyword_filters,
                   keyword_filter_mode,
                   allow_text, allow_photos, allow_videos, allow_documents, allow_audio, allow_voice,
                   allow_video_notes, allow_stickers, allow_animations, allow_contacts,
                   allow_locations, allow_venues, allow_polls, allow_dice,
                   delay_min, delay_max, remove_links, remove_mentions, replace_text,
                   duplicate_check, max_message_length, length_filter_settings, created_at, updated_at,
                   hashtag_settings, text_cleaner_settings, filter_inline_buttons, filter_duplicates,
                   filter_language, language_filter_mode, allowed_languages, manual_mode, link_preview,
                   pin_messages, silent_mode, sync_edits, preserve_replies, auto_translate, target_language,
                   working_hours_enabled, start_hour, end_hour, timezone, recurring_post_enabled,
                   recurring_post_content, recurring_interval_hours, format_settings,
                   sync_deletes, prefix_text, suffix_text, header_enabled, footer_enabled,
                   inline_buttons_enabled, inline_buttons_config, inline_button_settings
            FROM task_settings WHERE task_id = $1
        """
        result = await self.execute_query(query, task_id)
        return result[0] if result else None

    async def log_forwarding(self, log_data: Dict[str, Any]) -> bool:
        """Log forwarding operation"""
        try:
            query = """
                INSERT INTO forwarding_logs 
                (task_id, source_chat_id, target_chat_id, message_id, 
                 forwarded_message_id, status, error_message, processed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """
            await self.execute_command(
                query,
                log_data["task_id"],
                log_data["source_chat_id"],
                log_data["target_chat_id"],
                log_data["message_id"],
                log_data.get("forwarded_message_id"),
                log_data["status"],
                log_data.get("error_message")
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log forwarding: {e}")
            return False

    async def update_task_statistics(self, task_id: int, status: str) -> bool:
        """Update task statistics"""
        try:
            if status == "success":
                query = """
                    INSERT INTO task_statistics (
                        task_id, messages_processed, messages_forwarded, messages_failed, 
                        last_activity, created_at
                    ) VALUES ($1, 1, 1, 0, NOW(), NOW())
                    ON CONFLICT (task_id)
                    DO UPDATE SET 
                        messages_processed = COALESCE(task_statistics.messages_processed, 0) + 1,
                        messages_forwarded = COALESCE(task_statistics.messages_forwarded, 0) + 1,
                        last_activity = NOW()
                """
            else:
                query = """
                    INSERT INTO task_statistics (
                        task_id, messages_processed, messages_forwarded, messages_failed, 
                        last_activity, created_at
                    ) VALUES ($1, 1, 0, 1, NOW(), NOW())
                    ON CONFLICT (task_id)
                    DO UPDATE SET 
                        messages_processed = COALESCE(task_statistics.messages_processed, 0) + 1,
                        messages_failed = COALESCE(task_statistics.messages_failed, 0) + 1,
                        last_activity = NOW()
                """

            await self.execute_command(query, task_id)
            return True
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            return False

    async def get_task_statistics(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task statistics"""
        query = """
            SELECT * FROM task_statistics WHERE task_id = $1
        """
        result = await self.execute_query(query, task_id)
        return result[0] if result else None

    async def cleanup_old_logs(self, days: int = 30) -> int:
        """Clean up old forwarding logs"""
        try:
            query = """
                DELETE FROM forwarding_logs 
                WHERE processed_at < NOW() - INTERVAL '%s days'
            """
            result = await self.execute_command(query % days)
            logger.info(f"Cleaned up old logs: {result}")
            return int(result.split()[-1]) if result else 0
        except Exception as e:
            logger.error(f"Failed to cleanup logs: {e}")
            return 0

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            queries = {
                "total_users": "SELECT COUNT(*) as count FROM users",
                "total_tasks": "SELECT COUNT(*) as count FROM tasks",
                "active_tasks": "SELECT COUNT(*) as count FROM tasks WHERE is_active = true",
                "total_sources": "SELECT COUNT(*) as count FROM sources",
                "total_targets": "SELECT COUNT(*) as count FROM targets",
                "total_logs": "SELECT COUNT(*) as count FROM forwarding_logs",
                "logs_today": """
                    SELECT COUNT(*) as count FROM forwarding_logs 
                    WHERE DATE(processed_at) = CURRENT_DATE
                """
            }

            stats = {}
            for key, query in queries.items():
                result = await self.execute_query(query)
                stats[key] = result[0]["count"] if result else 0

            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def close(self):
        """Close database connections"""
        try:
            if self.pool:
                await self.pool.close()
                logger.info("Connection pool closed")

            if self.engine:
                await self.engine.dispose()
                logger.info("Database engine disposed")

        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

    async def health_check(self) -> bool:
        """Check database health"""
        try:
            result = await self.execute_query("SELECT 1 as health")
            return len(result) > 0 and result[0]["health"] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Placeholder for language menu callback handler.
async def lang_menu(update, context):
    """Handles the language menu callback."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Language change functionality not yet implemented.")