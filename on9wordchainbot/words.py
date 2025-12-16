import logging
from typing import Set, List
import aiofiles
import os

logger = logging.getLogger(__name__)

class Words:
    # Simple set to store words
    words: Set[str] = set()
    count: int = 0

    @classmethod
    async def update(cls) -> None:
        """Update the word list from the word.txt file."""
        logger.info("Loading word list from words.txt")
        try:
            # Get the directory of the current script (on9wordchainbot/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Path to words.txt in the same directory
            word_file = os.path.join(script_dir, 'words.txt')
            
            # Read words from the file
            async with aiofiles.open(word_file, 'r', encoding='utf-8') as f:
                words = await f.read()
                cls.words = {word.strip().lower() for word in words.split('\n') if word.strip()}
                cls.count = len(cls.words)
                
            logger.info(f"Successfully loaded {cls.count} words from words.txt")
        except Exception as e:
            logger.error(f"Error loading word list: {e}")
            cls.words = set()
            cls.count = 0

    @classmethod
    def __contains__(cls, word: str) -> bool:
        """Check if a word exists in the word list."""
        return word.lower() in cls.words

    @classmethod
    def starts_with(cls, prefix: str) -> List[str]:
        """Find all words that start with the given prefix."""
        prefix = prefix.lower()
        return [word for word in cls.words if word.startswith(prefix)]

# Initialize words on import
if __name__ != "__main__":
    import asyncio
    
    async def initialize():
        await Words.update()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(Words.update())
        else:
            loop.run_until_complete(Words.update())
    except RuntimeError:
        asyncio.run(Words.update())