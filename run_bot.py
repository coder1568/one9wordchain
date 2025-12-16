import asyncio
import logging
from on9wordchainbot import start_bot

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start the bot
    try:
        start_bot()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Error running bot: {e}", exc_info=True)
    finally:
        # Ensure all asyncio tasks are properly closed
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()
