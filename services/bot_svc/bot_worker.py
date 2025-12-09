"""
Telegram Bot Worker - Handles bot polling and webhook modes.
Provides core bot functionality and message routing.
"""
import os
import asyncio
import logging
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import ParseMode, BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web


class BotWorker:
    """Telegram bot worker with polling and webhook support."""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
        self.webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        self.webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "webhook_secret")
        
        if self.bot_token == "YOUR_BOT_TOKEN":
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable must be set")
        
        self.bot = Bot(token=self.bot_token, parse_mode=ParseMode.HTML)
        self.dp = Dispatcher()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup bot command and message handlers."""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: types.Message):
            """Handle /start command."""
            welcome_text = (
                "🤖 <b>RSS Bot Platform</b>\n\n"
                "Welcome to the modular RSS Bot! This bot is part of a microservice "
                "architecture that can manage RSS feeds, channels, and user subscriptions.\n\n"
                "Available commands:\n"
                "/ping - Check if bot is responsive\n"
                "/help - Show this help message\n"
                "/status - Show bot status\n\n"
                "<i>More features coming soon...</i>"
            )
            await message.answer(welcome_text)
        
        @self.dp.message(Command("ping"))
        async def ping_handler(message: types.Message):
            """Handle /ping command - simple responsiveness test."""
            await message.answer("🏓 Pong! Bot is working correctly.")
        
        @self.dp.message(Command("help"))
        async def help_handler(message: types.Message):
            """Handle /help command."""
            help_text = (
                "🔧 <b>RSS Bot Help</b>\n\n"
                "This is a modular RSS Bot platform with the following services:\n"
                "• Database service for data management\n"
                "• Bot service for Telegram interactions\n"
                "• Formatting service for content processing\n"
                "• Payment service for subscriptions\n"
                "• User service for profile management\n"
                "• Controller service for orchestration\n\n"
                "The bot is currently in development mode. Full functionality "
                "will be available once all services are properly configured."
            )
            await message.answer(help_text)
        
        @self.dp.message(Command("status"))
        async def status_handler(message: types.Message):
            """Handle /status command - show bot and system status."""
            # TODO: Check service health via controller service
            status_text = (
                "📊 <b>Bot Status</b>\n\n"
                "• Bot: ✅ Online\n"
                "• Mode: Polling (Development)\n"
                "• Services: Checking...\n\n"
                "<i>Service health checks will be implemented when "
                "controller service is fully operational.</i>"
            )
            await message.answer(status_text)
        
        @self.dp.message()
        async def echo_handler(message: types.Message):
            """Handle all other messages - echo for development."""
            response_text = (
                f"🔄 Echo: {message.text}\n\n"
                "<i>This is development mode. The bot will process RSS feeds "
                "and manage subscriptions once the platform is fully configured.</i>"
            )
            await message.answer(response_text)
    
    async def setup_bot_commands(self):
        """Setup bot command menu."""
        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="ping", description="Check bot responsiveness"),
            BotCommand(command="help", description="Show help message"),
            BotCommand(command="status", description="Show bot status"),
        ]
        await self.bot.set_my_commands(commands)
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message to a chat.
        Used by other services via the HTTP API.
        """
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                **kwargs
            )
            return {
                "success": True,
                "message_id": message.message_id,
                "chat_id": message.chat.id
            }
        except Exception as e:
            logging.error(f"Failed to send message to {chat_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "chat_id": chat_id
            }
    
    async def send_formatted_message(self, chat_id: int, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a formatted message with enhanced content.
        Handles different message types and formatting.
        """
        try:
            message_type = content.get("type", "text")
            
            if message_type == "text":
                return await self.send_message(
                    chat_id=chat_id,
                    text=content["text"],
                    parse_mode=content.get("parse_mode", ParseMode.HTML)
                )
            
            # TODO: Implement other message types (photo, document, etc.)
            elif message_type == "photo":
                # Placeholder for photo messages
                pass
            elif message_type == "document":
                # Placeholder for document messages
                pass
            
            return {"success": False, "error": f"Unsupported message type: {message_type}"}
        
        except Exception as e:
            logging.error(f"Failed to send formatted message to {chat_id}: {e}")
            return {"success": False, "error": str(e), "chat_id": chat_id}
    
    async def start_polling(self):
        """Start bot in polling mode (development)."""
        print("Starting bot in polling mode...")
        await self.setup_bot_commands()
        await self.dp.start_polling(self.bot)
    
    async def start_webhook(self, app: web.Application, path: str = "/webhook"):
        """Setup bot in webhook mode (production)."""
        if not self.webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL must be set for webhook mode")
        
        # Setup webhook
        await self.bot.set_webhook(
            url=f"{self.webhook_url}{path}",
            secret_token=self.webhook_secret
        )
        
        # Setup webhook handler
        SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot,
            secret_token=self.webhook_secret
        ).register(app, path=path)
        
        await self.setup_bot_commands()
        print(f"Webhook configured for {self.webhook_url}{path}")
        
        return app


# Global bot worker instance
bot_worker = BotWorker()


# Standalone function for running in polling mode
async def main():
    """Run bot in polling mode."""
    try:
        await bot_worker.start_polling()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        await bot_worker.bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())