"""Logging configuration for the Discord RAG bot."""

import logging
import os
from logging.handlers import RotatingFileHandler
import sys
from typing import Optional, Dict, Any

# Default logger
_LOGGER = None

def setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        config (Dict[str, Any], optional): Logging configuration

    Returns:
        logging.Logger: Configured root logger
    """
    global _LOGGER

    if _LOGGER is not None:
        return _LOGGER

    # Get config (either provided or from config module)
    if config is None:
        from .config import get_config
        config = get_config()['logging']

    # Get configuration values
    log_level_name = config.get('level', 'INFO')
    log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('file')
    max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10 MB default
    backup_count = config.get('backup_count', 5)

    # Convert log level name to logging level
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Create a logger for our application
    logger = logging.getLogger('discord_rag_bot')
    handler = RotatingFileHandler('/app/logs/discord_rag_bot.log', maxBytes=5*1024*1024, backupCount=2)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    # Store logger
    _LOGGER = logger

    logger.info("Logging configured")
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name (str, optional): Logger name, appended to 'discord_rag_bot'

    Returns:
        logging.Logger: Configured logger
    """
    global _LOGGER

    # Set up logging if not already done
    if _LOGGER is None:
        setup_logging()

    # Return named logger
    if name:
        return logging.getLogger(f'discord_rag_bot.{name}')
    else:
        return _LOGGER

class DiscordHandler(logging.Handler):
    """
    Custom logging handler that sends log messages to a Discord channel.
    Useful for remote monitoring of the bot.
    """

    def __init__(self, bot, channel_id: int, level: int = logging.ERROR):
        """
        Initialize the Discord logging handler.

        Args:
            bot: Discord bot instance
            channel_id (int): ID of the channel to send logs to
            level (int, optional): Minimum log level to send to Discord
        """
        super().__init__(level)
        self.bot = bot
