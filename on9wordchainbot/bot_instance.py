import json
import os
from pathlib import Path
from aiogram import Bot, Dispatcher, types

# Load configuration from JSON file
config_path = Path(__file__).parent.parent / 'config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Initialize bot instances
bot = Bot(
    token=config['TOKEN'],
    parse_mode=types.ParseMode.MARKDOWN,
    disable_web_page_preview=True
)
on9bot = Bot(token=config['ON9BOT_TOKEN'])

# Create dispatcher instance
dp = Dispatcher(bot)

# Make config available to other modules
config = config
