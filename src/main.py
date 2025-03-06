import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure import paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot import create_bot, register_commands, register_events, run_bot
from src.database import setup_database
from src.utils import setup_logging, load_config

async def setup():
    """Set up the database and prepare the environment."""
    logger = logging.getLogger('discord_bot')
    logger.info("Setting up Discord RAG Bot...")
    
    # Set up the database schema
    try:
        logger.info("Setting up database...")
        await setup_database()
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        raise

def main():
    """Main function to run the Discord bot."""
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Discord RAG Bot")
    
    # Load configuration
    config = load_config()
    
    # Run database setup
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(setup())
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        return 1
    
    try:
        # Create Discord bot
        bot = create_bot()
        
        # Register commands and events
        register_commands(bot)
        register_events(bot)
        
        # Get bot token from environment
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("DISCORD_BOT_TOKEN not found in environment variables")
            return 1
        
        # Run the bot
        logger.info("Running bot...")
        run_bot(bot, token)
        
        return 0
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
