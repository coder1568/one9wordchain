from aiogram import Dispatcher
from .. import GlobalState
from ..bot_instance import dp, bot

# Import all handlers to register them with the dispatcher
from . import admin
from . import game_handler
from . import gameplay  # Import gameplay handlers

# This will be populated by individual handler modules
handlers = []

__all__ = ["dp", "handlers"]

# Initialize any required handlers
def init_handlers():
    """Initialize all handlers and return the dispatcher"""
    # Import handlers to register them
    from . import gameplay
    return dp
