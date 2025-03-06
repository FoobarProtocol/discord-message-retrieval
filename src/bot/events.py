import discord
from discord.ext import commands
import logging
from typing import Callable, Any

# Configure logging
logger = logging.getLogger('discord_bot.events')

def register_events(bot: commands.Bot) -> None:
    """
    Register all event handlers to the Discord bot.

    Args:
        bot (commands.Bot): The bot to register events to
    """
    @bot.event
    async def on_ready():
        """Event handler for when the bot is ready and connected to Discord."""
        logger.info(f'Bot connected as {bot.user.name}')
        logger.info(f'Bot ID: {bot.user.id}')
        logger.info(f'Connected to {len(bot.guilds)} guilds')

        # Log the servers the bot is connected to
        for guild in bot.guilds:
            logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')
            logger.info(f'Guild has {len(guild.text_channels)} text channels and {guild.member_count} members')

    @bot.event
    async def on_message(message):
        """Event handler for when a new message is received."""
        # Ignore messages from the bot itself
        if message.author == bot.user:
            return

        try:
            # Import here to avoid circular imports
            from ..database.operations import store_message

            # Store the message in the database
            await store_message(message)

            # Log message information
            channel_name = getattr(message.channel, 'name', 'DM')
            logger.debug(f"Stored message from {message.author.name} in #{channel_name}")

            # If the message has attachments (images, files, etc.)
            if message.attachments:
                logger.debug(f"Message has {len(message.attachments)} attachment(s)")

            # If this is a direct mention of the bot, treat it as a question
            if bot.user in message.mentions and message.content:
                # Remove the bot mention
                content = message.content.replace(f'<@{bot.user.id}>', '').strip()
                if content:
                    # Create a synthetic context object to reuse the ask command logic
                    ctx = await bot.get_context(message)
                    # Get the ask command
                    ask_command = bot.get_command('ask')
                    if ask_command:
                        await ctx.invoke(ask_command, question=content)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

        # Process commands
        await bot.process_commands(message)

    @bot.event
    async def on_guild_join(guild):
        """Event handler for when the bot joins a new guild."""
        logger.info(f'Bot joined guild: {guild.name} (ID: {guild.id})')
        logger.info(f'Guild has {len(guild.text_channels)} text channels and {guild.member_count} members')

    @bot.event
    async def on_message_edit(before, after):
        """Event handler for when a message is edited."""
        if before.author == bot.user:
            return

        try:
            # Import here to avoid circular imports
            from ..database.operations import update_message

            # Update the message in the database
            await update_message(after)

            logger.debug(f"Updated edited message from {after.author.name}")
        except Exception as e:
            logger.error(f"Error processing edited message: {str(e)}")

    logger.info("Bot events registered")
