#!/usr/bin/env python3

import asyncio
import argparse
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logging import setup_logging
from src.utils.config import load_config
from src.database.connection import setup_database, get_db_pool
import asyncpg

async def create_database_if_not_exists(host, port, user, password, database):
    """Create the database if it doesn't exist."""
    logger = logging.getLogger('db_setup')
    
    # Connect to PostgreSQL server with default database
    try:
        # Connect to the default 'postgres' database to check if our DB exists
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        
        # Check if our database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database
        )
        
        if not exists:
            logger.info(f"Creating database '{database}'...")
            # Create the database
            await conn.execute(f'CREATE DATABASE "{database}"')
            logger.info(f"Database '{database}' created successfully")
        else:
            logger.info(f"Database '{database}' already exists")
            
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL or creating database: {str(e)}")
        return False

async def main():
    """Main function to set up the database."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Set up the Discord RAG Bot database')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--recreate', action='store_true', help='Recreate database if it exists')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting database setup")
    
    # Get database config
    db_config = config['database']
    host = db_config['host']
    port = db_config['port']
    user = db_config['user']
    password = db_config['password']
    database = db_config['database']
    
    if args.recreate:
        try:
            # Connect to PostgreSQL server with default database
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database='postgres'
            )
            
            # Terminate existing connections and drop database
            logger.warning(f"Recreating database '{database}'...")
            await conn.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{database}'
                  AND pid <> pg_backend_pid()
            """)
            await conn.execute(f'DROP DATABASE IF EXISTS "{database}"')
            await conn.execute(f'CREATE DATABASE "{database}"')
            await conn.close()
            logger.info(f"Database '{database}' recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating database: {str(e)}")
            return
    else:
        # Create database if it doesn't exist
        db_created = await create_database_if_not_exists(host, port, user, password, database)
        if not db_created:
            logger.error("Failed to create database. Exiting.")
            return
    
    # Set up database schema
    try:
        logger.info("Setting up database schema...")
        await setup_database()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up database schema: {str(e)}")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
