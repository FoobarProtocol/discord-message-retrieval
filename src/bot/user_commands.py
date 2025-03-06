import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional
import datetime

from ..rag.retriever import MessageRetriever
from ..rag.processor import ContextProcessor
from ..rag.generator import ResponseGenerator
from ..utils.config import get_config

# Configure logging
logger = logging.getLogger('discord_bot.user_commands')

class ConversationManager:
    """Manages conversation history for users."""
    
    def __init__(self, history_limit: int = 5):
        """
        Initialize the conversation manager.
        
        Args:
            history_limit (int): Maximum number of messages to keep in history
        """
        self.user_history = {}
        self.history_limit = history_limit
    
    def add_message(self, user_id: int, message: str, is_bot: bool = False):
        """
        Add a message to a user's conversation history.
        
        Args:
            user_id (int): Discord user ID
            message (str): Message content
            is_bot (bool): Whether this is a bot message
        """
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        self.user_history[user_id].append({
            'content': message,
            'is_bot': is_bot,
            'timestamp': datetime.datetime.now()
        })
        
        # Trim history if needed
        if len(self.user_history[user_id]) > self.history_limit:
            self.user_history[user_id] = self.user_history[user_id][-self.history_limit:]
    
    def get_history(self, user_id: int) -> str:
        """
        Get a formatted history for a user.
        
        Args:
            user_id (int): Discord user ID
            
        Returns:
            str: Formatted conversation history
        """
        if user_id not in self.user_history:
            return ""
        
        history = []
        for msg in self.user_history[user_id]:
            speaker = "Bot" if msg['is_bot'] else "User"
            history.append(f"{speaker}: {msg['content']}")
        
        return "\n".join(history)
    
    def clear_history(self, user_id: int):
        """
        Clear a user's conversation history.
        
        Args:
            user_id (int): Discord user ID
        """
        if user_id in self.user_history:
            del self.user_history[user_id]

def register_user_commands(bot: commands.Bot) -> None:
    """
    Register user-facing commands to the Discord bot.
    
    Args:
        bot (commands.Bot): The bot to register commands to
    """
    # Load configuration
    config = get_config()
    rag_config = config.get('rag', {})
    ai_config = config.get('ai', {})
    
    # Initialize components
    retriever = MessageRetriever(
        max_results=rag_config.get('max_context_messages', 20),
        max_days=rag_config.get('max_context_days', 30)
    )
    processor = ContextProcessor()
    generator = ResponseGenerator(
        model=ai_config.get('model', 'gpt-3.5-turbo')
    )
    conversation_manager = ConversationManager()
    
    @bot.command(name='ask')
    async def ask_command(ctx: commands.Context, *, question: str):
        """
        Ask a question and get an answer based on server message history.
        
        Usage:
            !ask What was discussed about the project deadline yesterday?
        """
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Add typing indicator to show the bot is working
        async with ctx.typing():
            # Store user question in conversation history
            conversation_manager.add_message(user_id, question)
            
            # Retrieve relevant messages
            messages = await retriever.retrieve(guild_id, question)
            
            # If no messages found, give a simple response
            if not messages:
                response = "I couldn't find any relevant information in the server's message history to answer your question."
                await ctx.reply(response)
                conversation_manager.add_message(user_id, response, is_bot=True)
                return
            
            # Process retrieved messages into context
            context = processor.process_messages(messages)
            
            # Get conversation history for additional context
            conv_history = conversation_manager.get_history(user_id)
            
            # Create the full prompt with both message
            prompt = processor.create_prompt_with_context(question, context)
            if conv_history:
                prompt += f"\n\nRecent conversation history:\n{conv_history}"
            
            # Generate response
            response = await generator.generate_response(prompt)
            
            # Store bot response in conversation history
            conversation_manager.add_message(user_id, response, is_bot=True)
        
        # Send the response
        # Split long responses if they exceed Discord's character limit
        if len(response) > 2000:
            chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await ctx.reply(chunk)
                else:
                    await ctx.send(chunk)
        else:
            await ctx.reply(response)
    
    @bot.command(name='clear')
    async def clear_history_command(ctx: commands.Context):
        """
        Clear your conversation history with the bot.
        
        Usage:
            !clear
        """
        user_id = ctx.author.id
        conversation_manager.clear_history(user_id)
        await ctx.reply("Your conversation history has been cleared.")
    
    @bot.command(name='search')
    async def search_messages_command(ctx: commands.Context, *, search_term: str):
        """
        Search for specific messages in the server's history.
        
        Usage:
            !search project deadline
        """
        guild_id = ctx.guild.id
        
        # Add typing indicator
        async with ctx.typing():
            # Import here to avoid circular imports
            from ..database.operations import get_messages_by_content
            
            # Retrieve messages matching search term
            messages = await get_messages_by_content(guild_id, search_term, limit=10)
            
            if not messages:
                await ctx.reply(f"No messages found containing '{search_term}'.")
                return
            
            # Create an embed to display the results
            embed = discord.Embed(
                title=f"Search Results for '{search_term}'",
                description=f"Found {len(messages)} messages:",
                color=discord.Color.blue()
            )
            
            # Add each message to the embed
            for i, msg in enumerate(messages[:10]):  # Limit to 10 messages for display
                timestamp = msg['timestamp'].strftime("%Y-%m-%d %H:%M")
                author = msg['author_name']
                content = msg['content'][:200] + ("..." if len(msg['content']) > 200 else "")
                channel = msg['channel_name']
                
                embed.add_field(
                    name=f"{i+1}. {author} in #{channel} ({timestamp})",
                    value=content,
                    inline=False
                )
            
            await ctx.reply(embed=embed)
    
    @bot.command(name='help_rag')
    async def help_command(ctx: commands.Context):
        """Show help information about the bot's RAG capabilities."""
        embed = discord.Embed(
            title="Discord RAG Bot Help",
            description="I can answer questions based on the server's message history. Here are the commands you can use:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="!ask [question]",
            value="Ask a question and I'll search the server's message history to provide an answer.",
            inline=False
        )
        
        embed.add_field(
            name="!search [term]",
            value="Search for specific messages in the server's history containing the given term.",
            inline=False
        )
        
        embed.add_field(
            name="!clear",
            value="Clear your conversation history with me.",
            inline=False
        )
        
        embed.add_field(
            name="Example",
            value="!ask What was decided about the project timeline yesterday?",
            inline=False
        )
        
        await ctx.reply(embed=embed)
    
    logger.info("User commands registered")
