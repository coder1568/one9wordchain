from aiogram import types
from aiogram.dispatcher.filters import Command
import asyncio

from .. import GlobalState
from ..bot_instance import dp, bot
from ..models.game import (
    ClassicGame,
    BannedLettersGame,
    ChaosGame,
    ChosenFirstLetterGame,
    EliminationGame,
    HardModeGame,
    MixedEliminationGame,
    RequiredLetterGame,
    RandomFirstLetterGame
)

async def start_game(message: types.Message, game_class):
    """Helper function to start a game"""
    async with GlobalState.games_lock:
        if message.chat.id in GlobalState.games:
            await message.reply("A game is already running in this chat!")
            return
        
        try:
            # Create new game instance
            game = game_class(message.chat.id)
            GlobalState.games[message.chat.id] = game
            
            # Start the game loop in the background with the message
            asyncio.create_task(game.main_loop(message))
            
        except Exception as e:
            error_msg = f"Failed to start game: {str(e)}"
            print(error_msg)  # Log the error
            await message.reply(error_msg)
            if message.chat.id in GlobalState.games:
                del GlobalState.games[message.chat.id]

@dp.message_handler(commands=["startclassic"])
async def cmd_start_classic(message: types.Message):
    """Start a classic word chain game"""
    await start_game(message, ClassicGame)

@dp.message_handler(commands=["startbanned"])
async def cmd_start_banned_letters(message: types.Message):
    """Start a banned letters word chain game"""
    await start_game(message, BannedLettersGame)

@dp.message_handler(commands=["startchaos"])
async def cmd_start_chaos(message: types.Message):
    """Start a chaos mode word chain game"""
    await start_game(message, ChaosGame)

@dp.message_handler(commands=["startelimination"])
async def cmd_start_elimination(message: types.Message):
    """Start an elimination word chain game"""
    await start_game(message, EliminationGame)

@dp.message_handler(commands=["starthard"])
async def cmd_start_hard_mode(message: types.Message):
    """Start a hard mode word chain game"""
    await start_game(message, HardModeGame)

@dp.message_handler(commands=["startmixed"])
async def cmd_start_mixed_elimination(message: types.Message):
    """Start a mixed elimination word chain game"""
    await start_game(message, MixedEliminationGame)

@dp.message_handler(commands=["startrequired"])
async def cmd_start_required_letter(message: types.Message):
    """Start a required letter word chain game"""
    await start_game(message, RequiredLetterGame)

@dp.message_handler(commands=["startrandom"])
async def cmd_start_random_letter(message: types.Message):
    """Start a random first letter word chain game"""
    await start_game(message, RandomFirstLetterGame)

# Add word handler for all game types
@dp.message_handler(lambda message: message.chat.id in GlobalState.games and not message.text.startswith('/'))
async def handle_game_message(message: types.Message):
    """Handle messages during an active game"""
    from ..constants import GameState
    
    game = GlobalState.games.get(message.chat.id)
    if not game:
        return
        
    # Check if the message is from a player in the game
    player = next((p for p in game.players if p.user_id == message.from_user.id), None)
    if not player:
        return
        
    # Process the message if it's the player's turn
    if game.state == GameState.RUNNING and game.players_in_game and game.players_in_game[0].user_id == message.from_user.id:
        word = message.text.strip().lower()
        await game.handle_answer(message)
