from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from ..bot_instance import dp
from ..models.game import (
    classic,
    banned_letters,
    chaos,
    chosen_first_letter,
    elimination,
    hard_mode,
    mixed_elimination,
    required_letter,
    random_first_letter
)

@dp.message_handler(commands=["startclassic"])
async def cmd_start_classic(message: types.Message):
    """Start a classic word chain game"""
    await classic.start_game(message)

@dp.message_handler(commands=["startbanned"])
async def cmd_start_banned_letters(message: types.Message):
    """Start a banned letters word chain game"""
    await banned_letters.start_game(message)

@dp.message_handler(commands=["startchaos"])
async def cmd_start_chaos(message: types.Message):
    """Start a chaos mode word chain game"""
    await chaos.start_game(message)

@dp.message_handler(commands=["startelimination"])
async def cmd_start_elimination(message: types.Message):
    """Start an elimination word chain game"""
    await elimination.start_game(message)

@dp.message_handler(commands=["starthard"])
async def cmd_start_hard_mode(message: types.Message):
    """Start a hard mode word chain game"""
    await hard_mode.start_game(message)

@dp.message_handler(commands=["startmixed"])
async def cmd_start_mixed_elimination(message: types.Message):
    """Start a mixed elimination word chain game"""
    await mixed_elimination.start_game(message)

@dp.message_handler(commands=["startrequired"])
async def cmd_start_required_letter(message: types.Message):
    """Start a required letter word chain game"""
    await required_letter.start_game(message)

@dp.message_handler(commands=["startrandom"])
async def cmd_start_random_letter(message: types.Message):
    """Start a random first letter word chain game"""
    await random_first_letter.start_game(message)


@dp.message_handler(commands=["flee"])
async def cmd_flee(message: types.Message):
    """Player leaves the game"""
    from .. import GlobalState
    
    group_id = message.chat.id
    if group_id not in GlobalState.games:
        await message.reply("❌ No active game in this chat.")
        return
    
    game = GlobalState.games[group_id]
    try:
        await game.flee(message)
    except Exception as e:
        print(f"Error in flee: {e}")
        await message.reply("❌ An error occurred while trying to flee.")


@dp.message_handler(commands=["forcestart"])
async def cmd_forcestart(message: types.Message):
    """Admin forces game to start"""
    from .. import GlobalState
    from ..constants import GameState
    
    group_id = message.chat.id
    if group_id not in GlobalState.games:
        await message.reply("❌ No active game in this chat.")
        return
    
    game = GlobalState.games[group_id]
    
    # Check if user is admin
    try:
        is_admin = await game.is_admin(message.from_user.id)
    except:
        is_admin = False
    
    if not is_admin:
        await message.reply("❌ Only admins can use this command.")
        return
    
    if game.state != GameState.JOINING:
        await message.reply("❌ Game has already started!")
        return
    
    if len(game.players) < 2:
        await message.reply("❌ At least 2 players are required to start the game.")
        return
    
    try:
        import random
        game.state = GameState.RUNNING
        game.players_in_game = game.players[:]
        random.shuffle(game.players_in_game)
        
        await game.running_initialization()
        await game.send_turn_message()
        await message.reply("🚀 Game has been force started!")
    except Exception as e:
        print(f"Error in forcestart: {e}")
        await message.reply("❌ An error occurred while starting the game.")
