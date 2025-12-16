from aiogram import types
from on9wordchainbot.bot_instance import dp
from on9wordchainbot import GlobalState

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def debug_message_handler(message: types.Message):
    print("\n=== DEBUG MESSAGE HANDLER ===")
    print(f"Message received: {message.text}")
    print(f"Chat ID: {message.chat.id}")
    print(f"From User ID: {message.from_user.id if message.from_user else 'No user'}")
    print(f"Chat type: {message.chat.type}")
    print(f"Command: {message.get_command()}")
    print(f"Command with args: {message.get_command(True)}")
    print(f"Full message: {message}")
    print("===========================\n")

    # Check if this is a command we're having issues with
    if message.text and any(cmd in message.text.lower() for cmd in ['/flee', '/forcestart', '/killgame']):
        print("\n=== TROUBLESHOOTING COMMAND DETECTED ===")
        print(f"Command: {message.text}")
        print(f"Chat ID: {message.chat.id}")
        print(f"User ID: {message.from_user.id if message.from_user else 'No user'}")
        print(f"Games in GlobalState: {list(GlobalState.games.keys())}")
        if message.chat.id in GlobalState.games:
            game = GlobalState.games[message.chat.id]
            print(f"Game state: {game.state}")
            print(f"Players: {[p.user_id for p in game.players]}")
        print("===================================\n")
