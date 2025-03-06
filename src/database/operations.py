import discord
import asyncpg
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
import io

from .connection import execute_query, get_db_pool

# Configure logging
logger = logging.getLogger('discord_bot.database.operations')

async def store_message(message: discord.Message) -> bool:
    """
    Store a Discord message in the database.
    
    Args:
        message (discord.Message): The Discord message to store
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract basic message data
        message_id = message.id
        channel_id = message.channel.id
        channel_name = getattr(message.channel, 'name', 'DM')
        guild_id = getattr(message.guild, 'id', 0)
        author_id = message.author.id
        author_name = message.author.name
        content = message.content
        timestamp = message.created_at
        is_pinned = message.pinned
        has_attachments = len(message.attachments) > 0
        reference_id = message.reference.message_id if message.reference else None
        
        # Insert message into database, updating if it already exists
        query = """
        INSERT INTO messages (
            message_id, channel_id, channel_name, guild_id, author_id, author_name,
            content, timestamp, is_pinned, has_attachments, reference_message_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (message_id) 
        DO UPDATE SET
            content = EXCLUDED.content,
            is_pinned = EXCLUDED.is_pinned,
            has_attachments = EXCLUDED.has_attachments,
            last_updated = CURRENT_TIMESTAMP
        RETURNING message_id
        """
        
        result = await execute_query(
            query,
            message_id, channel_id, channel_name, guild_id,
            author_id, author_name, content, timestamp,
            is_pinned, has_attachments, reference_id,
            fetch_val=True
        )
        
        # Process attachments if any
        if message.attachments:
            for attachment in message.attachments:
                await store_attachment(attachment, message_id)
        
        return True
    except Exception as e:
        logger.error(f"Error storing message {message.id}: {str(e)}")
        return False

async def update_message(message: discord.Message) -> bool:
    """
    Update an existing message in the database.
    
    Args:
        message (discord.Message): The updated Discord message
        
    Returns:
        bool: True if successful, False otherwise
    """
    # This function is similar to store_message but is used specifically for updates
    # The ON CONFLICT clause in store_message handles the update logic
    return await store_message(message)

async def store_attachment(attachment: discord.Attachment, message_id: int) -> bool:
    """
    Store a Discord attachment in the database.
    
    Args:
        attachment (discord.Attachment): The Discord attachment to store
        message_id (int): ID of the message this attachment belongs to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract attachment data
        attachment_id = attachment.id
        filename = attachment.filename
        url = attachment.url
        content_type = attachment.content_type
        width = getattr(attachment, 'width', None)
        height = getattr(attachment, 'height', None)
        size = attachment.size
        proxy_url = attachment.proxy_url
        description = getattr(attachment, 'description', None)
        
        # We don't store the actual attachment data by default to save space
        # But we could fetch and store it if needed:
        # data = await attachment.read() if attachment.size <= MAX_ATTACHMENT_SIZE else None
        data = None
        
        # Insert attachment into database
        query = """
        INSERT INTO attachments (
            attachment_id, message_id, filename, url, content_type,
            width, height, size, proxy_url, description, data
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (attachment_id) 
        DO UPDATE SET
            url = EXCLUDED.url,
            proxy_url = EXCLUDED.proxy_url,
            data = EXCLUDED.data
        """
        
        await execute_query(
            query,
            attachment_id, message_id, filename, url, content_type,
            width, height, size, proxy_url, description, data
        )
        
        return True
    except Exception as e:
        logger.error(f"Error storing attachment {attachment.id}: {str(e)}")
        return False

async def get_messages_by_date(
    guild_id: int,
    start_date: datetime.datetime,
    end_date: Optional[datetime.datetime] = None,
    channel_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Retrieve messages from a specific date range.
    
    Args:
        guild_id (int): The Discord server ID
        start_date (datetime.datetime): Start of date range
        end_date (datetime.datetime, optional): End of date range, defaults to current time
        channel_id (int, optional): Specific channel to query, or None for all channels
        limit (int, optional): Maximum number of messages to return
        
    Returns:
        List[Dict[str, Any]]: List of message records
    """
    try:
        # Default end_date to current time if not provided
        if end_date is None:
            end_date = datetime.datetime.now(datetime.timezone.utc)
        
        # Build query based on whether channel_id is provided
        if channel_id:
            query = """
            SELECT * FROM messages
            WHERE guild_id = $1 AND channel_id = $2
            AND timestamp BETWEEN $3 AND $4
            ORDER BY timestamp DESC
            LIMIT $5
            """
            params = [guild_id, channel_id, start_date, end_date, limit]
        else:
            query = """
            SELECT * FROM messages
            WHERE guild_id = $1
            AND timestamp BETWEEN $2 AND $3
            ORDER BY timestamp DESC
            LIMIT $4
            """
            params = [guild_id, start_date, end_date, limit]
        
        # Execute query and return results
        results = await execute_query(query, *params, fetch=True)
        
        # Convert results to dictionaries
        messages = []
        for record in results:
            messages.append(dict(record))
        
        return messages
    except Exception as e:
        logger.error(f"Error retrieving messages by date: {str(e)}")
        return []

async def get_messages_by_content(
    guild_id: int,
    search_text: str,
    channel_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search for messages containing specific text using full-text search.
    
    Args:
        guild_id (int): The Discord server ID
        search_text (str): Text to search for
        channel_id (int, optional): Specific channel to query, or None for all channels
        limit (int, optional): Maximum number of messages to return
        
    Returns:
        List[Dict[str, Any]]: List of message records
    """
    try:
        # Convert search text to tsquery format
        search_terms = ' & '.join(search_text.split())
        
        # Build query based on whether channel_id is provided
        if channel_id:
            query = """
            SELECT * FROM messages
            WHERE guild_id = $1 AND channel_id = $2
            AND to_tsvector('english', content) @@ to_tsquery('english', $3)
            ORDER BY timestamp DESC
            LIMIT $4
            """
            params = [guild_id, channel_id, search_terms, limit]
        else:
            query = """
            SELECT * FROM messages
            WHERE guild_id = $1
            AND to_tsvector('english', content) @@ to_tsquery('english', $2)
            ORDER BY timestamp DESC
            LIMIT $3
            """
            params = [guild_id, search_terms, limit]
        
        # Execute query and return results
        results = await execute_query(query, *params, fetch=True)
        
        # Convert results to dictionaries
        messages = []
        for record in results:
            messages.append(dict(record))
        
        return messages
    except Exception as e:
        logger.error(f"Error searching messages by content: {str(e)}")
        return []

async def get_messages_for_rag(
    guild_id: int,
    query: str,
    max_results: int = 20,
    max_days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve messages that are relevant for RAG-based question answering.
    
    Args:
        guild_id (int): The Discord server ID
        query (str): The user's question or query
        max_results (int, optional): Maximum number of messages to return
        max_days (int, optional): Only consider messages from the last X days
        
    Returns:
        List[Dict[str, Any]]: List of relevant message records
    """
    try:
        # Extract key terms from the query
        # This is a simplified version - in production, use better NLP
        search_terms = ' | '.join(term for term in query.split() if len(term) > 3)
        
        # Add date constraint if max_days is provided
        date_constraint = ""
        params = [guild_id, search_terms, max_results]
        
        if max_days:
            date_constraint = "AND timestamp > NOW() - INTERVAL '$3 days'"
            params = [guild_id, search_terms, max_days, max_results]
        
        # Use full-text search with ranking to find relevant messages
        query = f"""
        SELECT *, ts_rank(to_tsvector('english', content), to_tsquery('english', $2)) AS rank
        FROM messages
        WHERE guild_id = $1
        AND to_tsvector('english', content) @@ to_tsquery('english', $2)
        {date_constraint}
        ORDER BY rank DESC
        LIMIT ${len(params)}
        """
        
        # Execute query and return results
        results = await execute_query(query, *params, fetch=True)
        
        # Convert results to dictionaries
        messages = []
        for record in results:
            messages.append(dict(record))
        
        return messages
    except Exception as e:
        logger.error(f"Error retrieving messages for RAG: {str(e)}")
        return []

async def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the database.
    
    Returns:
        Dict[str, Any]: Statistics about the database
    """
    try:
        stats = {}
        
        # Get total message count
        query_total = "SELECT COUNT(*) FROM messages"
        stats['total_messages'] = await execute_query(query_total, fetch_val=True)
        
        # Get date range
        query_dates = "SELECT MIN(timestamp), MAX(timestamp) FROM messages"
        date_range = await execute_query(query_dates, fetch_one=True)
        stats['date_range'] = date_range
        
        # Get message count by channel
        query_channels = """
        SELECT channel_name, COUNT(*) 
        FROM messages 
        GROUP BY channel_id, channel_name 
        ORDER BY COUNT(*) DESC
        """
        channel_stats = await execute_query(query_channels, fetch=True)
        stats['channel_stats'] = [(record['channel_name'], record['count']) for record in channel_stats]
        
        # Get attachment count
        query_attachments = "SELECT COUNT(*) FROM attachments"
        stats['attachment_count'] = await execute_query(query_attachments, fetch_val=True)
        
        return stats
    except Exception as e:
        logger.error(f"Error fetching database stats: {str(e)}")
        return {
            'total_messages': 0,
            'date_range': None,
            'channel_stats': [],
            'attachment_count': 0
        }

async def get_messages_for_rag(
    guild_id: int,
    query: str,
    max_results: int = 20,
    max_days: Optional[int] = 30
) -> List[Dict[str, Any]]:
    """
    Get messages for RAG processing based on query relevance.
    
    Args:
        guild_id (int): The Discord server ID
        query (str): The user's query text
        max_results (int): Maximum number of messages to retrieve
        max_days (int, optional): Only consider messages from the last X days
        
    Returns:
        List[Dict[str, Any]]: List of relevant message records with ranking
    """
    try:
        # Create a date cutoff if max_days is specified
        date_clause = ""
        params = [guild_id]
        
        if max_days is not None:
            date_cutoff = datetime.datetime.now() - datetime.timedelta(days=max_days)
            date_clause = "AND timestamp > $2"
            params.append(date_cutoff)
        
        # Convert search text to TSQuery format (add:ed for fuzzy matching)
        search_terms = ' | '.join(query.split())
        params.append(search_terms)
        params.append(max_results)
        
        # Build query using PostgreSQL's full-text search capabilities with ranking
        query_sql = f"""
        SELECT m.*, 
               ts_rank_cd(to_tsvector('english', m.content), to_tsquery('english', $3)) AS rank
        FROM messages m
        WHERE m.guild_id = $1
        {date_clause}
        AND to_tsvector('english', m.content) @@ to_tsquery('english', $3)
        ORDER BY rank DESC
        LIMIT ${len(params)}
        """
        
        # Execute query and return results
        results = await execute_query(query_sql, *params, fetch=True)
        
        # Convert results to dictionaries
        messages = []
        for record in results:
            messages.append(dict(record))
        
        return messages
    except Exception as e:
        logger.error(f"Error retrieving messages for RAG: {str(e)}")
        return []

async def store_message(message_id: int, content: str, author_id: int, channel_id: int) -> None:
    """
    Store a message in the database.

    Args:
        message_id (int): ID of the message
        content (str): Content of the message
        author_id (int): ID of the author
        channel_id (int): ID of the channel
    """
    query = """
    INSERT INTO messages (message_id, content, author_id, channel_id)
    VALUES ($1, $2, $3, $4)
    """
    await execute_query(query, message_id, content, author_id, channel_id)

