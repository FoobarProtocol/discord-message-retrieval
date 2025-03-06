import logging
from typing import List, Dict, Any, Optional
import datetime

logger = logging.getLogger('discord_bot.rag.processor')

class ContextProcessor:
    """Process retrieved messages into a suitable context format for the LLM."""
    
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize the context processor.
        
        Args:
            max_context_length (int): Maximum token length for the context
        """
        self.max_context_length = max_context_length
    
    def process_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Process retrieved messages into a context string.
        
        Args:
            messages (List[Dict[str, Any]]): List of message records
            
        Returns:
            str: Formatted context string
        """
        if not messages:
            return "No relevant message history found."
        
        # Sort messages by timestamp (oldest first)
        sorted_messages = sorted(messages, key=lambda m: m['timestamp'])
        
        # Format messages into context
        context_parts = []
        
        for message in sorted_messages:
            # Format timestamp
            timestamp = message['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if message['timestamp'] else "Unknown time"
            
            # Format message
            author = message['author_name']
            channel = message['channel_name']
            content = message['content'] or "[No text content]"
            
            # Create formatted message entry
            formatted_message = f"[{timestamp}] {author} in #{channel}: {content}"
            context_parts.append(formatted_message)
        
        # Join messages and truncate if needed
        context = "\n".join(context_parts)
        
        # Simple truncation strategy - in a production system, you'd want
        # to use a proper tokenizer to ensure you don't exceed token limits
        if len(context) > self.max_context_length:
            # Truncate and add indicator
            context = context[:self.max_context_length - 100] + "\n[Context truncated due to length...]"
        
        return context
    
    def create_prompt_with_context(self, query: str, context: str) -> str:
        """
        Create a prompt for the LLM with the user query and retrieved context.
        
        Args:
            query (str): User's question
            context (str): Retrieved context
            
        Returns:
            str: Complete prompt for the LLM
        """
        prompt = f"""
Based on the following message history from the Discord server, please answer this question:

QUESTION: {query}

RELEVANT MESSAGE HISTORY:
{context}

Answer the question based only on the information provided in the message history. If the information needed isn't in the message history, acknowledge that and provide what's known. Be conversational and helpful.
"""
        return prompt
