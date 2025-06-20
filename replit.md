# Telegram Forwarding Bot

## Overview

This is a sophisticated Telegram forwarding bot built with Python that supports both Bot API and Userbot (Telethon/Pyrogram) modes. The application enables automated forwarding of messages between Telegram channels with advanced filtering, transformation, and management capabilities. It features a comprehensive web interface, database persistence, and enterprise-grade security features.

## System Architecture

### Backend Architecture
- **Framework**: Python 3.11+ with asyncio for concurrent operations
- **Bot Framework**: aiogram 3.x for Telegram Bot API integration
- **Userbot Support**: Telethon and Pyrogram for enhanced channel access
- **Web Server**: aiohttp for webhook support and potential web interface
- **Database**: PostgreSQL with asyncpg for async operations
- **ORM**: SQLAlchemy 2.x with async support for database modeling
- **Migrations**: Alembic for database schema versioning

### Key Components

1. **Bot Controller** (`bot_controller.py`)
   - Central orchestrator for bot operations
   - Manages FSM states and user interactions
   - Coordinates between different handlers and engines

2. **Forwarding Engine** (`forwarding_engine.py`)
   - Core message processing and forwarding logic
   - Supports both Bot API and Userbot modes
   - Handles message filtering, transformation, and delivery

3. **Database Layer** (`database.py`, `models.py`)
   - Async PostgreSQL operations with connection pooling
   - Comprehensive data models for users, tasks, sources, targets
   - Advanced tracking for forwarding logs and statistics

4. **Security Manager** (`security.py`)
   - User authentication and authorization
   - Rate limiting and access control
   - Encryption for sensitive data storage

5. **Session Manager** (`session_manager.py`)
   - Secure encrypted session storage
   - Machine-specific key generation
   - Backup and recovery mechanisms

6. **Modular Handlers** (`handlers/`)
   - Admin functions (`admin.py`)
   - Task management (`tasks.py`)
   - Source channel management (`sources.py`)
   - Target channel management (`targets.py`)
   - Interactive session creation (`session.py`)

7. **Management Modules** (`modules/`)
   - Task lifecycle management (`task_manager.py`)
   - Channel monitoring (`channel_monitor.py`)
   - Statistics and analytics (`statistics.py`)
   - Settings management (`settings_manager.py`)
   - Performance monitoring (`performance_monitor.py`)

## Data Flow

1. **Message Reception**: Source channels are monitored via userbot or bot webhooks
2. **Processing Pipeline**: Messages pass through filtering, transformation, and validation
3. **Forwarding**: Processed messages are delivered to target channels
4. **Tracking**: All operations are logged for statistics and audit purposes
5. **User Interface**: Admin users interact through inline keyboards and FSM states

## External Dependencies

### Core Dependencies
- **aiogram**: Telegram Bot API framework
- **telethon**: Telegram userbot client
- **pyrogram**: Alternative userbot client with tgcrypto
- **asyncpg**: Async PostgreSQL driver
- **sqlalchemy**: ORM and database toolkit
- **alembic**: Database migration tool

### Utility Dependencies
- **loguru**: Advanced logging
- **cryptography**: Encryption and security
- **googletrans**: Message translation
- **psutil**: System monitoring
- **pytz**: Timezone handling
- **aiohttp**: HTTP client/server

### Development Tools
- **uv**: Modern Python package manager
- **cargo/rustc**: For compiled dependencies

## Deployment Strategy

### Environment Setup
- **Runtime**: Python 3.11 with Nix package management
- **Database**: PostgreSQL 16 with connection pooling
- **Session Storage**: Encrypted local files with machine-specific keys
- **Logging**: File-based logging with rotation

### Configuration Management
- Environment variables for sensitive data (API keys, tokens)
- Database connection via standard PostgreSQL environment variables
- Optional webhook mode for production deployments
- Google Cloud Engine deployment target configured

### Scaling Considerations
- Async architecture supports high concurrency
- Database connection pooling for efficient resource usage
- Modular design allows for horizontal scaling
- Performance monitoring for bottleneck identification

## Changelog

- June 20, 2025. Initial setup
- June 20, 2025. Enhanced Text Cleaner with comprehensive 12-function interface including emoji removal, links, mentions, emails, hashtags, numbers, punctuation, empty lines, extra lines, whitespace normalization, duplicate lines, and target word management with testing capabilities
- June 20, 2025. Fixed Text Cleaner interface by removing duplicate function definitions and ensuring comprehensive version with all 12 features is properly displayed in Arabic interface
- June 20, 2025. Enhanced Text Cleaner with dedicated toggle button for "remove lines with target words" feature and improved Arabic naming for better user experience
- June 20, 2025. Completed comprehensive UI reorganization: moved Forward Mode into Forward button, created dedicated Limits button for delays/limits/length, moved day filter into Filters section, reorganized all menus with two-button rows for better user experience
- June 20, 2025. Fixed missing day filter button functionality by adding callback handler for filter_days_ in task handlers module
- June 20, 2025. Resolved day filter button visibility issue by updating filter settings handler to use standardized keyboard layout from keyboards module
- June 20, 2025. Fixed advanced feature sub-buttons (working hours, translation, recurring posts) by correcting task ID extraction and removing duplicate handlers
- June 20, 2025. Resolved translation settings interface duplication issue by fixing callback loops and removing unnecessary buttons for cleaner user experience
- June 20, 2025. Implemented comprehensive webhook support with automatic fallback to polling mode, Docker containerization, and Northflank deployment configuration for production-ready bot deployment
- June 20, 2025. Fixed translation settings interface conflicts by removing duplicate _handle_set_target_language function and correcting callback handler routing to eliminate interface duplication issues
- June 20, 2025. Integrated automatic translation functionality into forwarding engine workflow by adding translation call between text replacements and cleaning operations, and fixed text replacement error handling for both dict and list formats
- June 20, 2025. Fixed text replacement functionality by updating forwarding engine to check both "replace_text" and "text_replacements" field names, and added support for multiple replacement rule formats including "from/to" and "old/new" structures
- June 20, 2025. Fixed working hours and recurring posts advanced settings button responsiveness by adding missing callback handlers and implemented comprehensive User Filter functionality with verified users, bot filtering, whitelist/blacklist management, and message length filtering options

## User Preferences

Preferred communication style: Simple, everyday language.