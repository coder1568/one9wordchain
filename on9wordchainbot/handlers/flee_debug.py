"""
Debug version of the flee command.
Replace the existing cmd_flee function in gameplay.py with the one below.
"""

@dp.message_handler(commands=["flee"], commands_ignore_mention=True, chat_type=["group", "supergroup"])
@send_groups_only_message
async def cmd_flee_debug(message: types.Message) -> None:
    print("\n=== FLEE COMMAND TRIGGERED ===")
    print(f"Message: {message.text}")
    print(f"Chat ID: {message.chat.id}")
    print(f"From User ID: {message.from_user.id}")
    print(f"Current games in GlobalState: {GlobalState.games.keys()}")
    
    group_id = message.chat.id
    if group_id not in GlobalState.games:
        print("❌ No active game in this chat")
        await message.reply("❌ No active game in this chat.")
        return
        
    game = GlobalState.games[group_id]
    print(f"Game state: {game.state}")
    print(f"Players in game: {[f'{p.user_id} ({p.name})' for p in game.players]}")
    
    # Check if user is in the game
    user_id = message.from_user.id
    player_in_game = any(p.user_id == user_id for p in game.players)
    print(f"Is user {user_id} in game? {player_in_game}")
    
    if not player_in_game:
        print(f"❌ User {user_id} not in game")
        await message.reply("❌ You're not in the current game!")
        return
    
    print("Calling game.flee()...")
    try:
        await game.flee(message)
        print("game.flee() completed successfully")
        print(f"Players after flee: {[f'{p.user_id} ({p.name})' for p in game.players]}")
        print(f"Game state after flee: {game.state}")
        await message.reply("✅ Successfully left the game!")
    except Exception as e:
        import traceback
        print(f"❌ Error in game.flee(): {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        await message.reply("❌ An error occurred while trying to flee. Please try again.")
    
    print("=== FLEE COMMAND COMPLETED ===\n")
