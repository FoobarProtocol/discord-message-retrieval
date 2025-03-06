from discord import app_commands
import discord
from discord.ext import commands
import logging
from typing import Optional
import asyncio

from ..utils.config import get_config
from ..rag.retriever import MessageRetriever
from ..rag.processor import ContextProcessor
from ..rag.generator import ResponseGenerator
from ..rag.conversation import ConversationManager

logger = logging.getLogger('discord_bot.slash_commands')

async def setup_slash_commands(bot: commands.Bot):
    """Set up slash commands for the bot."""
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

def register_slash_commands(bot: commands.Bot) -> None:
    """Register slash commands to the bot."""
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
    
    @bot.tree.command(name="ask", description="Ask a question and get an answer based on server message history")
    async def ask_slash_command(interaction: discord.Interaction, question: str):
        """Ask a question using server context."""
        await interaction.response.defer(thinking=True)
        
        try:
            user_id = interaction.user.id
            guild_id = interaction.guild.id if interaction.guild else None
            
            # Get conversation history
            conversation = conversation_manager.get_conversation(user_id)
            
            # Add user message to conversation
            conversation.add_user_message(question)
            
            # Get relevant messages using RAG
            messages = await retriever.retrieve(guild_id, question)
            
            # Process messages into a context
            context = processor.process(messages, question)
            
            # Generate a response
            response = await generator.generate(question, context, conversation)
            
            # Add assistant response to conversation
            conversation.add_assistant_message(response)
            
            # Send the response
            await interaction.followup.send(response)
            
        except Exception as e:
            logger.error(f"Error processing ask command: {str(e)}")
            await interaction.followup.send(f"Sorry, I encountered an error while processing your question. Please try again later.")
    
    @bot.tree.command(name="help", description="Show the bot's help information")
    async def help_slash_command(interaction: discord.Interaction):
        """Display help information."""
        embed = discord.Embed(
            title="Discord RAG Bot Help",
            description="Here are the commands you can use:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="/ask [question]",
            value="Ask a question and get an answer based on server message history",
            inline=False
        )
        
        embed.add_field(
            name="/help",
            value="Show this help message",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
