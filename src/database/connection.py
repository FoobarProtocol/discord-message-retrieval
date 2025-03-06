import asyncpg
import os
import logging
from typing import Optional, Dict, Any, List
import asyncio

# Configure logging
logger = logging.getLogger('discord_bot.database')

# Default connection parameters
DEFAULT_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'discord_rag',
    'min_size': 5,
    'max_size': 20
}

# Connection pool singleton
_pool = None

async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create the database connection pool.

    Returns:
        asyncpg.Pool: PostgreSQL connection pool
    """
    global _pool

    if _pool is not None and not _pool._closed:
        return _pool

    # Get database configuration from environment variables or use defaults
    db_config = {
        'host': os.getenv('DB_HOST', DEFAULT_DB_CONFIG['host']),
        'port': int(os.getenv('DB_PORT', DEFAULT_DB_CONFIG['port'])),
        'user': os.getenv('DB_USER', DEFAULT_DB_CONFIG['user']),
        'password': os.getenv('DB_PASSWORD', DEFAULT_DB_CONFIG['password']),
        'database': os.getenv('DB_NAME', DEFAULT_DB_CONFIG['database']),
        'min_size': int(os.getenv('DB_MIN_POOL_SIZE', DEFAULT_DB_CONFIG['min_size'])),
        'max_size': int(os.getenv('DB_MAX_POOL_SIZE', DEFAULT_DB_CONFIG['max_size']))
    }

    # Add retry logic
    max_retries = 5
    retry_delay = 3  # seconds
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create connection pool
            logger.info(f"Creating database connection pool to {db_config['host']}:{db_config['port']}/{db_config['database']} (attempt {retry_count + 1}/{max_retries})")
            _pool = await asyncpg.create_pool(**db_config)

            if _pool is None:
                raise Exception("Failed to create database connection pool")

            logger.info("Successfully connected to the database")
            return _pool
        except asyncpg.PostgresError as e:
            retry_count += 1
            logger.warning(f"Database connection attempt {retry_count} failed: {str(e)}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise

    try:
        # Create connection pool
        logger.info(f"Creating database connection pool to {db_config['host']}:{db_config['port']}/{db_config['database']}")
        _pool = await asyncpg.create_pool(**db_config)

        if _pool is None:
            raise Exception("Failed to create database connection pool")

        logger.info("Successfully connected to the database")
        return _pool
    except asyncpg.PostgresError as e:
        logger.error(f"Error connecting to PostgreSQL: {str(e)}")
        raise

async def execute_query(query: str, *args, fetch: bool = False,
                        fetch_one: bool = False, fetch_val: bool = False) -> Any:
    """
    Execute an SQL query on the database.

    Args:
        query (str): SQL query to execute
        *args: Query parameters
        fetch (bool): Whether to fetch all results
        fetch_one (bool): Whether to fetch a single row
        fetch_val (bool): Whether to fetch a single value

    Returns:
        Any: Query results if fetch=True, otherwise None
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            logger.info(f"Executing query: {query} with args: {args}")
            if fetch:
                result = await conn.fetch(query, *args)
                logger.info(f"Query result: {result}")
                return result
            elif fetch_one:
                result = await conn.fetchrow(query, *args)
                logger.info(f"Query result: {result}")
                return result
            elif fetch_val:
                result = await conn.fetchval(query, *args)
                logger.info(f"Query result: {result}")
                return result
            else:
                result = await conn.execute(query, *args)
                logger.info(f"Query executed successfully")
                return result
    except asyncpg.PostgresError as e:
        logger.error(f"Database query error: {str(e)}")
        logger.error(f"Query: {query}")
        raise

async def setup_database() -> None:
    """
    Set up the database schema if it doesn't exist.
    """
    from .models import get_schema_creation_commands

    pool = await get_db_pool()

    # Create schema in a transaction
    async with pool.acquire() as conn:
        async with conn.transaction():
            for command in get_schema_creation_commands():
                await conn.execute(command)

    logger.info("Database schema setup complete")
