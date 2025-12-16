import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List

import aiohttp
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from . import filters
from .database import Database
from .bot_instance import bot, on9bot, dp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

try:
    import uvloop  # pip install uvloop
except ImportError:
    logger.info(r"uvloop unavailable ¯\_(ツ)_/¯")
else:
    uvloop.install()

# Initialize global variables
loop = asyncio.get_event_loop()
session = aiohttp.ClientSession()

# Initialize filters
from .filters import OwnerFilter, VIPFilter, AdminFilter, GameRunningFilter

# Register filters with the dispatcher
dp.filters_factory.bind(OwnerFilter)
dp.filters_factory.bind(VIPFilter)
dp.filters_factory.bind(AdminFilter)
dp.filters_factory.bind(GameRunningFilter)

class GlobalState:
    build_time = datetime.now().replace(microsecond=0)
    maint_mode = False
    games: Dict[int, "ClassicGame"] = {}
    games_lock: asyncio.Lock = asyncio.Lock()

# Initialize database connection
async def init_database(dispatcher):
    """Initialize database connection"""
    logger.info("Initializing database")
    await db.connect()
    logger.info("Database initialized")

# Import handlers after all globals are defined
def setup_handlers():
    """Initialize all handlers after the bot is fully set up"""
    from .handlers import admin, game
    return dp

async def on_shutdown(dispatcher):
    """Shutdown handler"""
    logger.info("Shutting down...")
    await db.close()
    await session.close()
    await bot.close()
    await on9bot.close()
    logger.info("Shutdown complete")

async def set_bot_commands():
    from aiogram import types
    commands = [
        # Basic commands
        types.BotCommand("start", "Start the bot and show help"),
        types.BotCommand("help", "Show help message"),
        types.BotCommand("maint", "Toggle maintenance mode (owner only)"),
        
        # Game start commands
        types.BotCommand("startclassic", "Start a classic word chain game"),
        types.BotCommand("startbanned", "Start a banned letters game"),
        types.BotCommand("startchaos", "Start a chaos mode game"),
        types.BotCommand("startelimination", "Start an elimination game"),
        types.BotCommand("starthard", "Start a hard mode game"),
        types.BotCommand("startmixed", "Start a mixed elimination game"),
        types.BotCommand("startrequired", "Start a required letter game"),
        types.BotCommand("startrandom", "Start a random first letter game"),
        
        # Game control commands
        types.BotCommand("join", "Join the current game"),
        types.BotCommand("flee", "Leave the current game"),
        
        # Admin commands
        types.BotCommand("forcestart", "Force start the game (admin only)"),
        types.BotCommand("killgame", "End the current game (admin only)"),
        types.BotCommand("addvp", "Add a virtual player"),
        types.BotCommand("remvp", "Remove a virtual player"),
        types.BotCommand("extend", "Extend joining time"),
        types.BotCommand("forceskip", "Skip current player's turn (admin only)")
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands have been set successfully!")

async def on_startup(dp):
    """Run this when bot starts."""
    await set_bot_commands()
    logger.info("Bot has been started!")

def start_bot():
    """Start the bot."""
    from aiogram import executor
    import asyncio

    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Initialize database
        loop.run_until_complete(init_database(dp))

        # Setup handlers
        setup_handlers()

        # Start the bot
        executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True, loop=loop)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Close the event loop when done
        if loop.is_running():
            loop.close()

if __name__ == "__main__":
    start_bot()
