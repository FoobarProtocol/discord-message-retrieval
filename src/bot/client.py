"""Discord bot client setup and core functionality."""

import discord
from discord.ext import commands
import logging
import os
from typing import Optional

# Configure logging
logger = logging.getLogger('discord_bot.client')

def create_bot() -> commands.Bot:
    """
    Create and configure the Discord bot with all necessary permissions.
    
    Returns:
        commands.Bot: Configured bot instance ready for event/command registration
    """
    # Set up intents (permissions)
    intents = discord.Intents.default()
    intents.message_content = True  # Required to read message content and attachments
    intents.messages = True         # Required to read messages
    intents.guilds = True           # Required for server information
    intents.members = True          # For user information
    
    # Initialize bot with command prefix
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    return bot

def run_bot(bot: commands.Bot, token: Optional[str] = None) -> None:
    """
    Run the Discord bot with the provided token.
    
    Args:
        bot (commands.Bot): The configured bot instance
        token (str, optional): Discord bot token. If None, uses DISCORD_BOT_TOKEN environment variable
    
    Raises:
        ValueError: If no token is provided and DISCORD_BOT_TOKEN is not set
        discord.errors.LoginFailure: If the token is invalid
    """
    # Use provided token or get from environment
    bot_token = token or os.getenv('DISCORD_BOT_TOKEN')
    
    if not bot_token:
        error_msg = "No Discord bot token provided. Set DISCORD_BOT_TOKEN environment variable or pass token parameter."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info("Starting Discord bot...")
        bot.run(bot_token)
    except discord.errors.LoginFailure:
        error_msg = "Invalid Discord bot token. Please check your token."
        logger.error(error_msg)
        raise
    except Exception as e:
        logger.error(f"Failed to start the bot: {str(e)}")
        raise
