#!/usr/bin/env python3
"""
Telegram Forwarding Bot - Main Application Entry Point
Supports both Bot API and Userbot modes with webhook/polling toggle
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession

from bot_controller import BotController
from config import Config
from database import Database
from forwarding_engine import ForwardingEngine
from security import SecurityManager
from modules.statistics import StatisticsManager
from modules.settings_manager import SettingsManager


class TelegramForwardingBot:
    """Main application class for the Telegram Forwarding Bot"""

    def __init__(self):
        self.config = Config()
        self.database = None
        self.bot = None
        self.dispatcher = None
        self.userbot = None
        self.forwarding_engine = None
        self.bot_controller = None
        self.security_manager = None
        self.webhook_app = None
        self.running = False

    async def initialize(self):
        """Initialize all components of the bot"""
        try:
            logger.info("Initializing Telegram Forwarding Bot...")

            # Initialize database
            self.database = Database(self.config.database_url)
            await self.database.initialize()
            logger.success("Database initialized successfully")

            # Initialize security manager
            self.security_manager = SecurityManager(self.database)
            await self.security_manager.initialize()
            logger.success("Security manager initialized")

            # Initialize bot
            self.bot = Bot(
                token=self.config.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Initialize dispatcher
            self.dispatcher = Dispatcher()

            # Initialize Telethon userbot with secure session management
            self.userbot = None
            if self.config.api_id and self.config.api_hash:
                try:
                    # Use the unified session manager to get session
                    from session_manager import SessionManager
                    session_manager = SessionManager()
                    session_string = session_manager.get_unified_session()
                    
                    if session_string and len(session_string) > 50:
                        try:
                            # Initialize Telethon client with StringSession
                            self.userbot = TelegramClient(
                                StringSession(session_string),
                                api_id=int(self.config.api_id),
                                api_hash=self.config.api_hash
                            )
                            logger.success("Telethon userbot initialized with unified session manager")
                        except Exception as session_error:
                            logger.warning(f"Telethon session error: {session_error}")
                            self.userbot = None
                    else:
                        logger.warning("No valid session string found in unified storage - userbot disabled")
                        self.userbot = None
                except Exception as e:
                    logger.error(f"Failed to initialize Telethon userbot: {e}")
                    self.userbot = None
            else:
                logger.info("Userbot disabled - API credentials not available")

            # Initialize forwarding engine
            self.forwarding_engine = ForwardingEngine(
                database=self.database,
                bot=self.bot,
                userbot=self.userbot,
                security_manager=self.security_manager
            )
            await self.forwarding_engine.initialize()
            logger.success("Forwarding engine initialized")

            # Initialize bot controller
            self.bot_controller = BotController(
                bot=self.bot,
                dispatcher=self.dispatcher,
                database=self.database,
                forwarding_engine=self.forwarding_engine,
                security_manager=self.security_manager,
                userbot=self.userbot
            )
            await self.bot_controller.initialize()
            logger.success("Bot controller initialized")

            logger.success("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    async def start_polling(self):
        """Start the bot in polling mode"""
        try:
            logger.info("Starting bot in polling mode...")
            await self.bot.delete_webhook(drop_pending_updates=True)

            # Start Telethon userbot with session handling
            if self.userbot:
                try:
                    if not self.userbot.is_connected():
                        await self.userbot.connect()
                    logger.success("Telethon userbot started successfully - hybrid mode active")
                    # Test userbot connectivity
                    try:
                        me = await self.userbot.get_me()
                        logger.info(f"Userbot authenticated as: {me.first_name} (@{me.username or 'N/A'})")
                    except Exception:
                        logger.warning("Userbot started but couldn't verify identity")
                except Exception as userbot_error:
                    logger.error(f"Telethon userbot startup failed: {userbot_error}")
                    logger.warning("Continuing with Bot API only mode")
                    self.userbot = None
                    # Update forwarding engine
                    if hasattr(self.forwarding_engine, 'userbot'):
                        self.forwarding_engine.userbot = None

            # Start forwarding engine
            await self.forwarding_engine.start()
            logger.success("Forwarding engine started")

            # Start polling with allowed updates
            allowed_updates = [
                "message", "edited_message", "channel_post", "edited_channel_post",
                "inline_query", "chosen_inline_result", "callback_query"
            ]
            await self.dispatcher.start_polling(self.bot, allowed_updates=allowed_updates)

        except Exception as e:
            logger.error(f"Error in polling mode: {e}")
            raise

    async def start_webhook(self):
        """Start the bot in webhook mode with automatic fallback to polling"""
        try:
            logger.info("Starting bot in webhook mode...")

            # Start userbot if available
            if self.userbot:
                try:
                    if not self.userbot.is_connected():
                        await self.userbot.connect()
                    logger.success("Userbot started successfully - hybrid mode active")
                    # Test userbot connectivity
                    try:
                        me = await self.userbot.get_me()
                        logger.info(f"Userbot authenticated as: {me.first_name} (@{me.username or 'N/A'})")
                    except Exception:
                        logger.warning("Userbot started but couldn't verify identity")
                except Exception as userbot_error:
                    logger.error(f"Userbot startup failed: {userbot_error}")
                    logger.warning("Continuing with Bot API only mode")
                    self.userbot = None
                    if hasattr(self.forwarding_engine, 'userbot'):
                        self.forwarding_engine.userbot = None

            # Start forwarding engine
            await self.forwarding_engine.start()
            logger.success("Forwarding engine started")

            # Build webhook URL
            webhook_url = f"{self.config.webhook_host}/webhook"
            if not webhook_url.startswith('http'):
                webhook_url = f"https://{webhook_url}"

            # Try to set webhook
            try:
                # Delete any existing webhook first
                await self.bot.delete_webhook(drop_pending_updates=True)
                await asyncio.sleep(1)  # Give Telegram a moment

                # Set new webhook
                await self.bot.set_webhook(
                    url=webhook_url,
                    secret_token=self.config.webhook_secret,
                    allowed_updates=["message", "edited_message", "channel_post", "edited_channel_post", "callback_query"],
                    max_connections=40,
                    drop_pending_updates=True
                )
                logger.success(f"Webhook set successfully to: {webhook_url}")

                # Verify webhook was set
                webhook_info = await self.bot.get_webhook_info()
                if webhook_info.url != webhook_url:
                    raise Exception(f"Webhook verification failed. Expected: {webhook_url}, Got: {webhook_info.url}")
                
                logger.info(f"Webhook verified - pending updates: {webhook_info.pending_update_count}")

            except Exception as webhook_error:
                logger.error(f"Failed to set webhook: {webhook_error}")
                logger.warning("Webhook setup failed, falling back to polling mode...")
                return await self.start_polling()

            # Create webhook application
            self.webhook_app = web.Application()

            # Setup webhook handler
            webhook_handler = SimpleRequestHandler(
                dispatcher=self.dispatcher,
                bot=self.bot,
                secret_token=self.config.webhook_secret
            )
            webhook_handler.register(self.webhook_app, path="/webhook")

            # Setup application
            setup_application(self.webhook_app, self.dispatcher, bot=self.bot)

            # Add health check endpoint
            async def health_check(request):
                try:
                    # Check bot connection
                    await self.bot.get_me()
                    return web.Response(
                        text="Bot is running and healthy", 
                        status=200,
                        headers={"Content-Type": "text/plain"}
                    )
                except Exception as e:
                    return web.Response(
                        text=f"Bot health check failed: {e}", 
                        status=503,
                        headers={"Content-Type": "text/plain"}
                    )

            # Add webhook info endpoint
            async def webhook_info(request):
                try:
                    info = await self.bot.get_webhook_info()
                    return web.json_response({
                        "url": info.url,
                        "has_custom_certificate": info.has_custom_certificate,
                        "pending_update_count": info.pending_update_count,
                        "last_error_date": info.last_error_date.isoformat() if info.last_error_date else None,
                        "last_error_message": info.last_error_message,
                        "max_connections": info.max_connections,
                        "allowed_updates": info.allowed_updates
                    })
                except Exception as e:
                    return web.json_response({"error": str(e)}, status=500)

            self.webhook_app.router.add_get("/health", health_check)
            self.webhook_app.router.add_get("/webhook-info", webhook_info)
            self.webhook_app.router.add_get("/", lambda r: web.Response(text="Telegram Forwarding Bot", status=200))

            # Start web server
            try:
                runner = web.AppRunner(self.webhook_app)
                await runner.setup()

                site = web.TCPSite(
                    runner,
                    host="0.0.0.0",
                    port=self.config.webhook_port
                )
                await site.start()

                logger.success(f"Webhook server started on port {self.config.webhook_port}")
                logger.info(f"Health check available at: http://0.0.0.0:{self.config.webhook_port}/health")
                logger.info(f"Webhook info available at: http://0.0.0.0:{self.config.webhook_port}/webhook-info")

            except Exception as server_error:
                logger.error(f"Failed to start webhook server: {server_error}")
                logger.warning("Server startup failed, falling back to polling mode...")
                return await self.start_polling()

            # Keep running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Critical error in webhook mode: {e}")
            logger.warning("Falling back to polling mode...")
            return await self.start_polling()

    async def start(self):
        """Start the bot with automatic webhook/polling detection"""
        self.running = True

        try:
            await self.initialize()

            # Try webhook mode first if webhook host is configured
            if self.config.webhook_host and not self.config.webhook_host.startswith("localhost"):
                logger.info("Webhook host detected, attempting webhook mode...")
                try:
                    await self.start_webhook()
                except Exception as webhook_error:
                    logger.error(f"Webhook mode failed: {webhook_error}")
                    logger.info("Falling back to polling mode...")
                    await self.start_polling()
            else:
                logger.info("No webhook host configured or localhost detected, using polling mode...")
                await self.start_polling()

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Gracefully shutdown the bot"""
        logger.info("Shutting down bot...")
        self.running = False

        try:
            # Stop forwarding engine
            if self.forwarding_engine:
                await self.forwarding_engine.stop()
                logger.success("Forwarding engine stopped")

            # Stop userbot
            if self.userbot and self.userbot.is_connected():
                await self.userbot.disconnect()
                logger.success("Telethon userbot disconnected")

            # Close bot session
            if self.bot:
                await self.bot.session.close()
                logger.success("Bot session closed")

            # Close database connections
            if self.database:
                await self.database.close()
                logger.success("Database connections closed")

            logger.success("Bot shutdown completed")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def signal_handler(app: TelegramForwardingBot, sig: int):
    """Handle shutdown signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    await app.shutdown()
    sys.exit(0)


async def main():
    """Main application entry point"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create bot instance
    app = TelegramForwardingBot()

    # Setup signal handlers
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, lambda s, f: asyncio.create_task(signal_handler(app, s)))

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await app.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await app.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    # Ensure event loop is properly configured
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())