import asyncio
import re
from re import Match
from typing import Type

from aiogram import types
from aiogram.dispatcher.filters import RegexpCommandsFilter

from .. import GlobalState, dp, on9bot
from ..constants import GameSettings, GameState, VIP, VIP_GROUP
from ..models import ClassicGame, EliminationGame, GAME_MODES, MixedEliminationGame
from ..utils import amt_donated, send_groups_only_message




@send_groups_only_message
async def start_game(message: types.Message, game_type: Type[ClassicGame]) -> None:
    group_id = message.chat.id
    
    # Debug log
    print(f"Starting game in group {group_id}")
    print(f"Current games in GlobalState: {GlobalState.games.keys()}")
    
    if group_id in GlobalState.games:
        print(f"Game already exists in group {group_id}")
        # There is already a game running in the group
        await GlobalState.games[group_id].join(message)
        return

    if GlobalState.maint_mode:
        # Only stop people from starting games, not joining
        await message.reply(
            (
                "Maintenance mode is on. Games are temporarily disabled.\n"
                "This is likely due to a pending bot update."
            ),
            allow_sending_without_reply=True
        )
        return

    await message.chat.update_chat()
    if message.chat.slow_mode_delay:
        await message.reply(
            (
                "Slow mode is enabled in this group, so the bot cannot function properly.\n"
                "If you are a group admin, please disable slow mode to start games."
            ),
            allow_sending_without_reply=True
        )
        return

    if (
        game_type is MixedEliminationGame and message.chat.id not in VIP_GROUP
        and message.from_user.id not in VIP and await amt_donated(message.from_user.id) < 30
    ):
        await message.reply(
            (
                "This game mode is a donation reward.\n"
                "You can try this game mode at the [official group](https://t.me/+T30aTNo-2Xx2kc52)."
            ),
            allow_sending_without_reply=True
        )
        return

    async with GlobalState.games_lock:  # Avoid duplicate game creation
        if group_id in GlobalState.games:
            asyncio.create_task(GlobalState.games[group_id].join(message))
        else:
            game = game_type(message.chat.id)
            GlobalState.games[group_id] = game
            asyncio.create_task(game.main_loop(message))


@dp.message_handler(RegexpCommandsFilter([r"^/(start[a-z]+)"]))
async def cmd_startgame(message: types.Message, regexp_command: Match) -> None:
    command = regexp_command.groups()[0].lower()
    if command == "startgame":
        await start_game(message, ClassicGame)
        return

    for mode in GAME_MODES:
        if mode.command == command:
            await start_game(message, mode)
            return


@dp.message_handler(commands="join")
@send_groups_only_message
async def cmd_join(message: types.Message) -> None:
    group_id = message.chat.id
    if group_id in GlobalState.games:
        await GlobalState.games[group_id].join(message)


@dp.message_handler(is_owner=True, game_running=True, commands="forcejoin")
async def cmd_forcejoin(message: types.Message) -> None:
    group_id = message.chat.id
    rmsg = message.reply_to_message
    if rmsg and rmsg.from_user.is_bot:  # On9Bot only
        if rmsg.from_user.id == on9bot.id:
            await cmd_addvp(message)
        return
    await GlobalState.games[group_id].forcejoin(message)


@dp.message_handler(game_running=True, commands="extend")
async def cmd_extend(message: types.Message) -> None:
    await GlobalState.games[message.chat.id].extend(message)






@dp.message_handler(is_owner=True, game_running=True, commands="forceflee")
async def cmd_forceflee(message: types.Message) -> None:
    await GlobalState.games[message.chat.id].forceflee(message)


@dp.message_handler(commands=["killgame", "killgaym"])
async def cmd_killgame(message: types.Message) -> None:
    from ..constants import GameState
    
    try:
        group_id = message.chat.id
        
        # Check if there's a game in this chat
        if group_id not in GlobalState.games:
            await message.reply("❌ No active game in this chat.")
            return
            
        game = GlobalState.games[group_id]
        
        # Check if user is admin
        if not await game.is_admin(message.from_user.id) and message.from_user.id not in VIP:
            await message.reply("❌ Only admins can use this command.")
            return
        
        # Store game info for the message
        game_info = f"Game ended by admin. "
        if hasattr(game, 'turns'):
            game_info += f"Total words: {game.turns}"
        
        # Set game state to KILLGAME to signal the game to end
        game.state = GameState.KILLGAME
        
        # Send game end message
        await message.reply(f"🛑 Game has been forcefully ended.\n{game_info}")
        
        # Clean up the game
        if group_id in GlobalState.games:
            # Remove the game from global state first to prevent race conditions
            game = GlobalState.games.pop(group_id, None)
            if game:
                # Call cleanup if it exists
                if hasattr(game, 'cleanup'):
                    try:
                        await game.cleanup()
                    except Exception as e:
                        logger.error(f"Error during game cleanup: {e}")
                
                # Clear any remaining tasks
                for task in asyncio.all_tasks():
                    if task.get_name() == f"game_loop_{group_id}":
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Error cancelling game task: {e}")
            
    except Exception as e:
        logger.error(f"Error in killgame command: {e}", exc_info=True)
        await message.reply("❌ An error occurred while trying to end the game.")


@dp.message_handler(is_owner=True, game_running=True, commands="forceskip")
async def cmd_forceskip(message: types.Message) -> None:
    group_id = message.chat.id
    if GlobalState.games[group_id].state == GameState.RUNNING and not GlobalState.games[group_id].answered:
        GlobalState.games[group_id].time_left = 0


@dp.message_handler(game_running=True, commands="addvp")
async def cmd_addvp(message: types.Message) -> None:
    group_id = message.chat.id
    if isinstance(GlobalState.games[group_id], EliminationGame):
        await message.reply(
            (
                f"Sorry, [{(await on9bot.me).full_name}](https://t.me/{(await on9bot.me).username}) "
                "can't play elimination games."
            ),
            allow_sending_without_reply=True
        )
        return
    await GlobalState.games[group_id].addvp(message)


@dp.message_handler(game_running=True, commands="remvp")
async def cmd_remvp(message: types.Message) -> None:
    await GlobalState.games[message.chat.id].remvp(message)


@dp.message_handler(is_owner=True, game_running=True, commands="incmaxp")
async def cmd_incmaxp(message: types.Message) -> None:
    # Thought this could be useful when I implemented this
    # It is not
    group_id = message.chat.id
    if (
        GlobalState.games[group_id].state != GameState.JOINING
        or GlobalState.games[group_id].max_players == GameSettings.INCREASED_MAX_PLAYERS
    ):
        await message.reply("smh")
        return

    if isinstance(GlobalState.games[group_id], EliminationGame):
        GlobalState.games[group_id].max_players = GameSettings.ELIM_INCREASED_MAX_PLAYERS
    else:
        GlobalState.games[group_id].max_players = GameSettings.INCREASED_MAX_PLAYERS
    await message.reply(
        f"This game can now accommodate {GlobalState.games[group_id].max_players} players.",
        allow_sending_without_reply=True
    )


# Word answer handler - MUST BE LAST to have lowest priority
@dp.message_handler(
    lambda m: bool(re.fullmatch(r"^[a-zA-Z]{1,100}$", m.text)) and not m.text.startswith('/'),
    chat_type=["group", "supergroup"]
)
@dp.edited_message_handler(
    lambda m: bool(re.fullmatch(r"^[a-zA-Z]{1,100}$", m.text)) and not m.text.startswith('/'),
    chat_type=["group", "supergroup"]
)
async def answer_handler(message: types.Message) -> None:
    """Handle word answers during game.
    
    This handler only processes messages that:
    - Match the word pattern (1-100 letters)
    - Don't start with '/'
    - Are in a group or supergroup chat
    """
    group_id = message.chat.id
    
    # Check if game exists
    if group_id not in GlobalState.games:
        return
    
    game = GlobalState.games[group_id]
    
    # Only handle if game is running and player is current turn
    if (
        game.players_in_game
        and message.from_user.id == game.players_in_game[0].user_id
        and not game.answered
        and game.accepting_answers
    ):
        await game.handle_answer(message)
