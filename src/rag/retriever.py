import logging
import datetime
from typing import List, Dict, Any, Optional

from ..database.operations import get_messages_by_content, get_messages_for_rag

logger = logging.getLogger('discord_bot.rag.retriever')

class MessageRetriever:
    """Retrieves relevant messages from the database based on user queries."""
    
    def __init__(self, max_results: int = 20, max_days: Optional[int] = 30):
        """
        Initialize the message retriever.
        
        Args:
            max_results (int): Maximum number of messages to retrieve
            max_days (int, optional): Only consider messages from the last X days
        """
        self.max_results = max_results
        self.max_days = max_days
    
    async def retrieve(self, guild_id: int, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant messages for the given query.
        
        Args:
            guild_id (int): Discord server ID
            query (str): User's question or query
            
        Returns:
            List[Dict[str, Any]]: List of relevant messages
        """
        logger.info(f"Retrieving context for query: {query}")
        
        try:
            # Use the specialized RAG query function
            messages = await get_messages_for_rag(
                guild_id=guild_id,
                query=query,
                max_results=self.max_results,
                max_days=self.max_days
            )
            
            logger.info(f"Retrieved {len(messages)} messages as context")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving messages for RAG: {str(e)}")
            return []
    
    def filter_by_relevance(self, messages: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Further filter messages by relevance to the query.
        
        Args:
            messages (List[Dict[str, Any]]): Retrieved messages
            query (str): User's question or query
            
        Returns:
            List[Dict[str, Any]]: Filtered list of messages
        """
        # If we already have ranking from the database, we can just use that
        if messages and 'rank' in messages[0]:
            return sorted(messages, key=lambda m: m['rank'], reverse=True)
        
        # Otherwise, perform basic keyword filtering
        # This is a simple implementation - you might want to use better NLP techniques
        query_terms = set(query.lower().split())
        
        # Calculate a simple relevance score based on term overlap
        for message in messages:
            content = message['content'].lower() if message['content'] else ""
            content_terms = set(content.split())
            
            # Calculate term overlap as a simple relevance score
            overlap = len(query_terms.intersection(content_terms))
            message['relevance_score'] = overlap / len(query_terms) if query_terms else 0
        
        # Sort by relevance score
        return sorted(messages, key=lambda m: m.get('relevance_score', 0), reverse=True)
