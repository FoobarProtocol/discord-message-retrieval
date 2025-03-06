import logging
import os
from typing import Dict, Any, Optional
import json
import aiohttp

logger = logging.getLogger('discord_bot.rag.generator')

class ResponseGenerator:
    """Generate responses using an LLM with retrieved context."""
    
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
        """
        Initialize the response generator.
        
        Args:
            model (str): The LLM model to use
            api_key (str, optional): API key for the LLM service
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Response generation will fail.")
    
    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt (str): The prompt for the LLM
            temperature (float): Creativity parameter
            
        Returns:
            str: Generated response
        """
        if not self.api_key:
            return "I'm unable to generate a response because the AI service is not configured properly."
        
        logger.info("Generating response with LLM")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on Discord message history."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 1000
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error from OpenAI API: {error_text}")
                        return "I encountered an error while generating a response. Please try again later."
                    
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I encountered an error while generating a response. Please try again later."
