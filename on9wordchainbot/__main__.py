import asyncio
import random
import time
from decimal import ROUND_HALF_UP, getcontext

from aiogram import executor
from periodic import Periodic

from on9wordchainbot import dp, loop, session
from on9wordchainbot.utils import send_admin_group
from on9wordchainbot.words import Words

# Import all handlers to register them
from on9wordchainbot.handlers import game_handler, gameplay, info, stats, wordlist

random.seed(time.time())
getcontext().rounding = ROUND_HALF_UP


async def on_startup(_) -> None:
    # Notify admin group
    await send_admin_group("Bot starting.")

    await Words.update()

    # Update word list every 3 hours
    task = Periodic(3 * 60 * 60, Words.update)
    await task.start()


async def on_shutdown(_) -> None:
    # Notify admin group
    await send_admin_group("Bot shutting down...")
    # Close database connection
    if 'session' in globals():
        await session.close()


def main() -> None:
    executor.start_polling(
        dp, loop=loop, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True
    )


if __name__ == "__main__":
    main()
