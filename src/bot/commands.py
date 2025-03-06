"""Discord bot commands for message retrieval and database management."""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import List, Optional
import datetime

# Configure logging
logger = logging.getLogger('discord_bot.commands')

async def fetch_historical_messages(channels: List[discord.TextChannel], 
                                   fetch_limit: int = 10000,
                                   fetch_delay: float = 1.0,
                                   after_date: Optional[datetime.datetime] = None) -> int:
    """
    Fetch historical messages from a list of channels and store them in the database.
    
    Args:
        channels (List[discord.TextChannel]): List of channels to fetch messages from
        fetch_limit (int, optional): Maximum number of messages to fetch per channel
        fetch_delay (float, optional): Delay between batches to avoid rate limits
        after_date (datetime, optional): Only fetch messages after this date
    
    Returns:
        int: Total number of messages fetched
    """
    # Import here to avoid circular imports
    from ..database.operations import store_message
    
    total_messages = 0
    
    for channel in channels:
        if not isinstance(channel, discord.TextChannel):
            continue  # Skip non-text channels
            
        logger.info(f"Fetching messages from #{channel.name} (ID: {channel.id})")
        message_count = 0
        
        try:
            # Create history parameters
            history_params = {"limit": fetch_limit}
            if after_date:
                history_params["after"] = after_date
                
            async for message in channel.history(**history_params):
                await store_message(message)
                message_count += 1
                
                # Process images and other attachments
                if message.attachments:
                    logger.debug(f"Message {message.id} has {len(message.attachments)} attachment(s)")
                
                # Add a small delay every 100 messages to avoid rate limiting
                if message_count % 100 == 0:
                    logger.info(f"Fetched {message_count} messages from #{channel.name}")
                    await asyncio.sleep(fetch_delay)
            
            total_messages += message_count
            logger.info(f"Completed fetching {message_count} messages from #{channel.name}")
            
        except discord.errors.Forbidden:
            logger.warning(f"No permission to read history in #{channel.name}")
        except Exception as e:
            logger.error(f"Error fetching messages from #{channel.name}: {str(e)}")
    
    logger.info(f"Historical message fetch complete. Total messages: {total_messages}")
    return total_messages

def register_commands(bot: commands.Bot) -> None:
    """
    Register all commands to the Discord bot.
    
    Args:
        bot (commands.Bot): The bot to register commands to
    """
    @bot.command(name='fetch_history')
    @commands.has_permissions(administrator=True)  # Only server admins can run this
    async def fetch_history_command(ctx: commands.Context, 
                                   limit: Optional[int] = None,
                                   days: Optional[int] = None):
        """
        Command to fetch and store the server's message history.
        
        Usage:
            !fetch_history [limit] [days]
            
        Args:
            limit: Maximum messages per channel (default: 10000)
            days: Only fetch messages from the last X days
        """
        # Calculate after_date if days is provided
        after_date = None
        if days:
            after_date = datetime.datetime.now() - datetime.timedelta(days=days)
            await ctx.send(f"Starting to fetch messages from the last {days} days. This may take a while...")
        else:
            await ctx.send("Starting to fetch all historical messages. This may take a while...")
        
        # Get all visible text channels
        channels = [channel for channel in ctx.guild.text_channels 
                   if channel.permissions_for(ctx.guild.me).read_messages]
        
        # Send status update
        await ctx.send(f"Will fetch messages from {len(channels)} channels. Please wait...")
        
        # Set limit if provided
        fetch_limit = limit if limit is not None else 10000
        
        # Fetch messages
        count = await fetch_historical_messages(
            channels, 
            fetch_limit=fetch_limit,
            after_date=after_date
        )
        
        # Send completion message
        await ctx.send(f"Historical message fetch complete! Stored {count} messages in the database.")

    @bot.command(name='db_status')
    @commands.has_permissions(administrator=True)
    async def db_status_command(ctx: commands.Context):
        """
        Check the status of the message database.
        
        Usage:
            !db_status
        """
        # Import here to avoid circular imports
        from ..database.operations import get_database_stats
        
        await ctx.send("Fetching database statistics...")
        
        try:
            # Get database statistics
            stats = await get_database_stats()
            
            # Create status message
            status = f"**Database Status**\n"
            status += f"Total messages stored: {stats['total_messages']}\n"
            
            if stats['date_range']:
                status += f"Date range: {stats['date_range'][0]} to {stats['date_range'][1]}\n\n"
            else:
                status += "No messages stored yet.\n\n"
            
            if stats['channel_stats']:
                status += "**Messages per channel:**\n"
                for channel_name, count in stats['channel_stats']:
                    status += f"#{channel_name}: {count} messages\n"
                    
            if stats['attachment_count'] > 0:
                status += f"\n**Attachments:** {stats['attachment_count']} stored"
            
            await ctx.send(status)
        except Exception as e:
            logger.error(f"Error fetching database stats: {str(e)}")
            await ctx.send(f"Error fetching database statistics: {str(e)}")

    @bot.command(name='fetch_channel')
    @commands.has_permissions(administrator=True)
    async def fetch_channel_command(ctx: commands.Context, 
                                  channel: discord.TextChannel,
                                  limit: Optional[int] = None,
                                  days: Optional[int] = None):
        """
        Fetch message history from a specific channel.
        
        Usage:
            !fetch_channel #channel-name [limit] [days]
            
        Args:
            channel: The channel to fetch messages from
            limit: Maximum messages to fetch (default: 10000)
            days: Only fetch messages from the last X days
        """
        # Calculate after_date if days is provided
        after_date = None
        if days:
            after_date = datetime.datetime.now() - datetime.timedelta(days=days)
            await ctx.send(f"Fetching messages from #{channel.name} for the last {days} days...")
        else:
            await ctx.send(f"Fetching all messages from #{channel.name}...")
        
        # Set limit if provided
        fetch_limit = limit if limit is not None else 10000
        
        # Fetch messages
        count = await fetch_historical_messages(
            [channel], 
            fetch_limit=fetch_limit,
            after_date=after_date
        )
        
        # Send completion message
        await ctx.send(f"Complete! Stored {count} messages from #{channel.name}.")
    
    logger.info("Bot commands registered")
