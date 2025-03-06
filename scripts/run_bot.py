#!/usr/bin/env python3

import asyncio
import argparse
import sys
import os
import logging
import signal
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logging import setup_logging
from src.utils.config import load_config
from src.database.connection import setup_database
from src.bot.client import create_bot, run_bot
from src.bot.commands import register_commands
from src.bot.events import register_events

def signal_handler(sig, frame):
    """Handle signals to gracefully shut down the bot."""
    logger = logging.getLogger('bot_runner')
    logger.info(f"Received signal {sig}. Shutting down...")
    sys.exit(0)

def main():
    """Main function to run the Discord bot."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run the Discord RAG Bot')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--token', type=str, help='Discord bot token (overrides config/env)')
    parser.add_argument('--no-db-setup', action='store_true', help='Skip database setup')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override log level if debug flag is set
    if args.debug:
        config['logging']['level'] = 'DEBUG'
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Discord RAG Bot")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set up database schema if needed
    if not args.no_db_setup:
        try:
            logger.info("Setting up database...")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(setup_database())
            logger.info("Database setup complete")
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            return 1
    
    try:
        # Create Discord bot
        bot = create_bot()
        
        # Register commands and events
        register_commands(bot)
        register_events(bot)
        
        # Get bot token from arguments, config, or environment
        token = args.token or os.getenv('DISCORD_BOT_TOKEN')
        
        # Run the bot
        logger.info("Running bot...")
        run_bot(bot, token)
        
        return 0
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        return 1

if __name__ == "__main__":
    # Run the main function and exit with its return code
    sys.exit(main())
