import logging
import random
from functools import wraps
from string import ascii_lowercase
from typing import Any, Callable, List, Optional, Set

logger = logging.getLogger(__name__)

from aiocache import cached
from aiogram import types

from . import bot, on9bot, db
from .constants import ADMIN_GROUP_ID, VIP
from .words import Words


def is_word(s: str) -> bool:
    return all(c in ascii_lowercase for c in s)


def check_word_existence(word: str) -> bool:
    """Check if a word exists in the dictionary (case-insensitive)"""
    if not word or not isinstance(word, str):
        return False
    word = word.strip().lower()
    return word in Words.words or word.capitalize() in Words.words


def filter_words(
    min_len: int = 1,
    prefix: Optional[str] = None,
    required_letter: Optional[str] = None,
    banned_letters: Optional[List[str]] = None,
    exclude_words: Optional[Set[str]] = None
) -> List[str]:
    """Filter words based on given criteria"""
    try:
        # Get words with prefix if specified
        if prefix:
            prefix = prefix.lower()
            words = Words.starts_with(prefix)
        else:
            words = list(Words.words)
        
        # Apply filters
        filtered_words = []
        exclude_set = {w.lower() for w in (exclude_words or [])}
        
        for word in words:
            word_lower = word.lower()
            
            # Skip if word is too short
            if len(word) < min_len:
                continue
                
            # Check required letter
            if required_letter and required_letter.lower() not in word_lower:
                continue
                
            # Check banned letters
            if banned_letters and any(letter.lower() in word_lower for letter in banned_letters):
                continue
                
            # Check excluded words (case-insensitive)
            if word_lower in exclude_set:
                continue
                
            filtered_words.append(word)
            
        return filtered_words
        
    except Exception as e:
        logger.error(f"Error in filter_words: {e}")
        return []


def get_random_word(
    min_len: int = 1,
    prefix: Optional[str] = None,
    required_letter: Optional[str] = None,
    banned_letters: Optional[List[str]] = None,
    exclude_words: Optional[Set[str]] = None
) -> Optional[str]:
    words = filter_words(min_len, prefix, required_letter, banned_letters, exclude_words)
    return random.choice(words) if words else None


async def send_admin_group(*args: Any, **kwargs: Any) -> Optional[types.Message]:
    try:
        if not ADMIN_GROUP_ID:
            return None
        return await bot.send_message(ADMIN_GROUP_ID, *args, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message to admin group: {e}")
        return None


@cached(ttl=3600)
async def amt_donated(user_id: int) -> int:
    result = await db.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM donation WHERE user_id = ?",
        user_id
    )
    return float(result) if result else 0.0


@cached(ttl=15)
async def has_star(user_id: int) -> bool:
    return user_id in VIP or user_id == on9bot.id or (await amt_donated(user_id)) > 0


def inline_keyboard_from_button(button: types.InlineKeyboardButton) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


ADD_TO_GROUP_KEYBOARD = inline_keyboard_from_button(
    types.InlineKeyboardButton("Add to group", url="https://t.me/on9wordchainbot?startgroup=_")
)
ADD_ON9BOT_TO_GROUP_KEYBOARD = inline_keyboard_from_button(
    types.InlineKeyboardButton("Add On9Bot to group", url="https://t.me/On9Bot?startgroup=_")
)


def send_private_only_message(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    async def inner(message: types.Message, *args: Any, **kwargs: Any) -> None:
        if message.chat.id < 0:
            await message.reply("Please use this command in private.", allow_sending_without_reply=True)
            return
        await f(message, *args, **kwargs)

    return inner


def send_groups_only_message(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    async def inner(message: types.Message, *args: Any, **kwargs: Any) -> None:
        if message.chat.id > 0:
            await message.reply(
                "This command can only be used in groups.",
                allow_sending_without_reply=True, reply_markup=ADD_TO_GROUP_KEYBOARD
            )
            return
        await f(message, *args, **kwargs)

    return inner
