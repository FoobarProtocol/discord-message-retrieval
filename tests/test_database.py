import unittest
import asyncio
import discord
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import datetime
from pathlib import Path
import asyncpg

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import setup_database, get_db_pool, execute_query
from src.database.operations import (
    store_message, 
    update_message,
    get_messages_by_date,
    get_messages_by_content,
    get_database_stats
)

class TestDatabaseConnection(unittest.IsolatedAsyncioTestCase):
    """Test cases for database connection functionality."""
    
    def setUp(self):
        """Set up tests."""
        # Mock asyncpg.create_pool
        self.pool_patcher = patch('asyncpg.create_pool')
        self.mock_create_pool = self.pool_patcher.start()
        self.mock_pool = AsyncMock()
        self.mock_create_pool.return_value = self.mock_pool
        
        # Mock os.getenv to return test database config
        self.getenv_patcher = patch('os.getenv')
        self.mock_getenv = self.getenv_patcher.start()
        self.mock_getenv.side_effect = lambda key, default=None: {
            'DB_HOST': 'test_host',
            'DB_PORT': '5432',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password',
            'DB_NAME': 'test_db',
            'DB_MIN_POOL_SIZE': '1',
            'DB_MAX_POOL_SIZE': '5'
        }.get(key, default)
    
    def tearDown(self):
        """Clean up after tests."""
        self.pool_patcher.stop()
        self.getenv_patcher.stop()
    
    async def test_get_db_pool(self):
        """Test getting the database connection pool."""
        # Get the pool
        pool = await get_db_pool()
        
        # Verify the pool is the mock pool
        self.assertEqual(pool, self.mock_pool)
        
        # Verify create_pool was called with the right parameters
        self.mock_create_pool.assert_called_once_with(
            host='test_host',
            port=5432,
            user='test_user',
            password='test_password',
            database='test_db',
            min_size=1,
            max_size=5
        )
    
    async def test_setup_database(self):
        """Test database schema setup."""
        # Mock asyncpg transaction and connection
        mock_conn = AsyncMock()
        self.mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        
        # Call setup_database
        await setup_database()
        
        # Verify transaction was created
        mock_conn.transaction.assert_called_once()
        
        # Verify execute was called for schema creation
        self.assertTrue(mock_conn.execute.called)
        
        # Number of calls should match the number of schema commands
        from src.database.models import get_schema_creation_commands
        expected_calls = len(get_schema_creation_commands())
        self.assertGreaterEqual(mock_conn.execute.call_count, expected_calls)

class TestDatabaseOperations(unittest.IsolatedAsyncioTestCase):
    """Test cases for database operations."""
    
    def setUp(self):
        """Set up tests."""
        # Mock the execute_query function
        self.execute_query_patcher = patch('src.database.operations.execute_query')
        self.mock_execute_query = self.execute_query_patcher.start()
        
        # Create a mock Discord message
        self.mock_message = MagicMock(spec=discord.Message)
        self.mock_message.id = 123456789
        self.mock_message.channel = MagicMock(spec=discord.TextChannel)
        self.mock_message.channel.id = 987654321
        self.mock_message.channel.name = 'test-channel'
        self.mock_message.guild = MagicMock(spec=discord.Guild)
        self.mock_message.guild.id = 111222333
        self.mock_message.author = MagicMock(spec=discord.Member)
        self.mock_message.author.id = 444555666
        self.mock_message.author.name = 'Test User'
        self.mock_message.content = 'This is a test message'
        self.mock_message.created_at = datetime.datetime.now()
        self.mock_message.pinned = False
        self.mock_message.attachments = []
        self.mock_message.reference = None
    
    def tearDown(self):
        """Clean up after tests."""
        self.execute_query_patcher.stop()
    
    async def test_store_message(self):
        """Test storing a message."""
        # Set up mock return value
        self.mock_execute_query.return_value = self.mock_message.id
        
        # Call store_message
        result = await store_message(self.mock_message)
        
        # Verify execute_query was called
        self.mock_execute_query.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
        
        # Check query contains expected values
        query_args = self.mock_execute_query.call_args.args
        self.assertIn('INSERT INTO messages', query_args[0])
        self.assertEqual(query_args[1], self.mock_message.id)
        self.assertEqual(query_args[2], self.mock_message.channel.id)
    
    async def test_update_message(self):
        """Test updating a message."""
        # Set up mock return value
        self.mock_execute_query.return_value = self.mock_message.id
        
        # Call update_message
        result = await update_message(self.mock_message)
        
        # Verify execute_query was called
        self.mock_execute_query.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
    
    async def test_get_messages_by_date(self):
        """Test retrieving messages by date."""
        # Set up mock return value - list of record-like dictionaries
        mock_records = [
            {'message_id': 1, 'content': 'Test 1'},
            {'message_id': 2, 'content': 'Test 2'}
        ]
        self.mock_execute_query.return_value = [
            MagicMock(**record) for record in mock_records
        ]
        
        # Call get_messages_by_date
        start_date = datetime.datetime.now() - datetime.timedelta(days=1)
        result = await get_messages_by_date(
            guild_id=111222333,
            start_date=start_date
        )
        
        # Verify execute_query was called
        self.mock_execute_query.assert_called_once()
        
        # Verify result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['message_id'], 1)
        self.assertEqual(result[1]['content'], 'Test 2')
    
    async def test_get_messages_by_content(self):
        """Test searching messages by content."""
        # Set up mock return value
        mock_records = [
            {'message_id': 1, 'content': 'Test search term'},
            {'message_id': 2, 'content': 'Another test with search term'}
        ]
        self.mock_execute_query.return_value = [
            MagicMock(**record) for record in mock_records
        ]
        
        # Call get_messages_by_content
        result = await get_messages_by_content(
            guild_id=111222333,
            search_text='search term'
        )
        
        # Verify execute_query was called
        self.mock_execute_query.assert_called_once()
        
        # Verify result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['message_id'], 1)
        self.assertEqual(result[1]['content'], 'Another test with search term')
    
    async def test_get_database_stats(self):
        """Test getting database statistics."""
        # Set up mock return values for different queries
        self.mock_execute_query.side_effect = [
            100,  # Total messages
            (datetime.datetime(2023, 1, 1), datetime.datetime(2023, 12, 31)),  # Date range
            [  # Channel stats
                MagicMock(channel_name='channel1', count=50),
                MagicMock(channel_name='channel2', count=30),
                MagicMock(channel_name='channel3', count=20)
            ],
            10  # Attachment count
        ]
        
        # Call get_database_stats
        result = await get_database_stats()
        
        # Verify execute_query was called multiple times
        self.assertEqual(self.mock_execute_query.call_count, 4)
        
        # Verify result
        self.assertEqual(result['total_messages'], 100)
        self.assertEqual(result['date_range'][0], datetime.datetime(2023, 1, 1))
        self.assertEqual(result['date_range'][1], datetime.datetime(2023, 12, 31))
        self.assertEqual(len(result['channel_stats']), 3)
        self.assertEqual(result['channel_stats'][0], ('channel1', 50))
        self.assertEqual(result['attachment_count'], 10)

if __name__ == '__main__':
    unittest.main()

