import unittest
import asyncio
import discord
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bot.client import create_bot
from src.bot.commands import register_commands
from src.bot.events import register_events

class TestBotClient(unittest.TestCase):
    """Test cases for the bot client functionality."""
    
    def setUp(self):
        """Set up tests."""
        # Mock the commands.Bot to avoid actual Discord connections
        self.bot_patcher = patch('discord.ext.commands.Bot')
        self.mock_bot_class = self.bot_patcher.start()
        self.mock_bot = MagicMock()
        self.mock_bot_class.return_value = self.mock_bot
        
        # Mock discord.Intents
        self.intents_patcher = patch('discord.Intents')
        self.mock_intents = self.intents_patcher.start()
        self.mock_intents.default.return_value = MagicMock()
    
    def tearDown(self):
        """Clean up after tests."""
        self.bot_patcher.stop()
        self.intents_patcher.stop()
    
    def test_create_bot(self):
        """Test bot creation."""
        bot = create_bot()
        
        # Verify bot was created with expected parameters
        self.mock_bot_class.assert_called_once()
        
        # Verify intents were set correctly
        intents = self.mock_intents.default.return_value
        self.assertEqual(intents.message_content, True)
        self.assertEqual(intents.messages, True)
        self.assertEqual(intents.guilds, True)
        self.assertEqual(intents.members, True)
    
    @patch('os.getenv')
    def test_run_bot_with_token(self, mock_getenv):
        """Test running the bot with a provided token."""
        from src.bot.client import run_bot
        
        # Setup mock
        mock_getenv.return_value = 'mock_token'
        bot = MagicMock()
        
        # Run the function
        run_bot(bot, 'test_token')
        
        # Verify bot.run was called with the token
        bot.run.assert_called_once_with('test_token')
    
    @patch('os.getenv')
    def test_run_bot_with_env_token(self, mock_getenv):
        """Test running the bot with an environment token."""
        from src.bot.client import run_bot
        
        # Setup mock
        mock_getenv.return_value = 'env_token'
        bot = MagicMock()
        
        # Run the function
        run_bot(bot)
        
        # Verify bot.run was called with the environment token
        bot.run.assert_called_once_with('env_token')
    
    @patch('os.getenv')
    def test_run_bot_no_token(self, mock_getenv):
        """Test running the bot with no token."""
        from src.bot.client import run_bot
        
        # Setup mock
        mock_getenv.return_value = None
        bot = MagicMock()
        
        # Verify exception is raised
        with self.assertRaises(ValueError):
            run_bot(bot)

class TestBotCommands(unittest.TestCase):
    """Test cases for bot commands."""
    
    def setUp(self):
        """Set up tests."""
        self.bot = MagicMock()
        # Mock the command decorator
        self.bot.command.return_value = lambda func: func
    
    def test_register_commands(self):
        """Test command registration."""
        register_commands(self.bot)
        
        # Verify command registration
        self.assertTrue(self.bot.command.called)
        
        # Check specific commands were registered
        command_names = [call.args[0] for call in self.bot.command.call_args_list]
        self.assertIn('fetch_history', str(command_names))
        self.assertIn('db_status', str(command_names))
        self.assertIn('fetch_channel', str(command_names))

class TestBotEvents(unittest.IsolatedAsyncioTestCase):
    """Test cases for bot events."""
    
    def setUp(self):
        """Set up tests."""
        self.bot = MagicMock()
        # Dictionary to store event handlers
        self.event_handlers = {}
        
        # Mock the event decorator
        def event_decorator(func):
            event_name = func.__name__
            self.event_handlers[event_name] = func
            return func
        
        self.bot.event = event_decorator
    
    def test_register_events(self):
        """Test event registration."""
        register_events(self.bot)
        
        # Verify event registration
        self.assertIn('on_ready', self.event_handlers)
        self.assertIn('on_message', self.event_handlers)
        self.assertIn('on_guild_join', self.event_handlers)
        self.assertIn('on_message_edit', self.event_handlers)
    
    @patch('src.database.operations.store_message')
    async def test_on_message_event(self, mock_store_message):
        """Test on_message event handler."""
        register_events(self.bot)
        
        # Create a mock message
        mock_message = AsyncMock()
        mock_message.author = MagicMock(spec=discord.User)
        mock_message.author.bot = False
        mock_message.content = "Test message"
        mock_message.attachments = []
        
        # Set up mock for store_message
        mock_store_message.return_value = True
        
        # Call the event handler
        await self.event_handlers['on_message'](mock_message)
        
        # Verify store_message was called
        mock_store_message.assert_called_once_with(mock_message)
        
        # Verify process_commands was called
        self.bot.process_commands.assert_called_once_with(mock_message)

if __name__ == '__main__':
    unittest.main()
