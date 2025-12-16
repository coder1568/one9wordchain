from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from .. import GlobalState
from ..bot_instance import dp, bot

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    """Send a welcome message when the command /start or /help is issued."""
    await message.reply(
        "👋 Hello! I'm the Word Chain Bot.\n"
        "I can help you play word chain games in your group!\n\n"
        "Available commands:\n"
        "/start - Show this help message\n"
        "/stats - Show your statistics\n"
        "/groupstats - Show group statistics\n"
        "\nAdd me to a group and make me an admin to start playing!"
    )

@dp.message_handler(commands=["maint"], is_owner=True)
async def cmd_maint(message: types.Message):
    """Toggle maintenance mode (owner only)."""
    from .. import GlobalState
    GlobalState.maint_mode = not GlobalState.maint_mode
    status = "enabled" if GlobalState.maint_mode else "disabled"
    await message.reply(f"🚧 Maintenance mode {status}.")

@dp.message_handler(commands=["addvp"], is_chat_admin=True)
async def cmd_add_vp(message: types.Message):
    """Add a virtual player to the game (admin only)."""
    chat_id = message.chat.id
    if chat_id not in GlobalState.games:
        await message.reply("No active game in this chat!")
        return
    
    game = GlobalState.games[chat_id]
    if hasattr(game, 'addvp'):
        await game.addvp(message)
    else:
        await message.reply("This game mode doesn't support virtual players.")

@dp.message_handler(commands=["remvp"], is_chat_admin=True)
async def cmd_remove_vp(message: types.Message):
    """Remove a virtual player from the game (admin only)."""
    if not message.reply_to_message:
        await message.reply("Please reply to a message from the virtual player you want to remove.")
        return
        
    chat_id = message.chat.id
    if chat_id not in GlobalState.games:
        await message.reply("No active game in this chat!")
        return
    
    game = GlobalState.games[chat_id]
    if hasattr(game, 'remvp'):
        await game.remvp(message)
    else:
        await message.reply("This game mode doesn't support virtual players.")

@dp.message_handler(commands=["extend"], is_chat_admin=True)
async def cmd_extend(message: types.Message):
    """Extend the joining time (admin only)."""
    chat_id = message.chat.id
    if chat_id not in GlobalState.games:
        await message.reply("No active game in this chat!")
        return
    
    game = GlobalState.games[chat_id]
    if hasattr(game, 'extend'):
        await game.extend(message)
    else:
        await message.reply("This game mode doesn't support extending time.")
