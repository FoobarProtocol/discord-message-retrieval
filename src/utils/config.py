import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Default configuration
DEFAULT_CONFIG = {
    # Bot settings
    'bot': {
        'command_prefix': '!',
        'description': 'Discord bot with RAG capabilities',
        'message_fetch_limit': 10000,
        'fetch_delay': 1.0,  # seconds between batch fetches
    },
    
    # Database settings
    'database': {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'discord_rag',
        'min_pool_size': 5,
        'max_pool_size': 20,
    },
    
    # RAG settings
    'rag': {
        'max_context_messages': 20,
        'max_context_days': 30,  # How far back to look for context by default
        'search_similarity_threshold': 0.7,
        'max_context_length': 12000,
        'conversation_history_limit': 25
    },
    
    # Logging settings
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'discord_rag_bot.log',
        'max_file_size': 10 * 1024 * 1024,  # 10 MB
        'backup_count': 5,
    },
    
    # AI model settings
    'ai': {
        'model': 'o3-mini',
        'api_key_env_var': 'OPENAI_API_KEY',
        'temperature': 0.7,
        'max_tokens': 16384,
    }
}

# Global config singleton
_CONFIG = None

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the configuration from a JSON file and environment variables.
    
    Args:
        config_path (str, optional): Path to the JSON config file
        
    Returns:
        Dict[str, Any]: The loaded configuration
    """
    global _CONFIG
    
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Load config from file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Merge with default config
                _merge_configs(config, file_config)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
    
    # Override with environment variables
    _override_config_from_env(config)
    
    # Store config
    _CONFIG = config
    
    return config

def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    
    Returns:
        Dict[str, Any]: The current configuration
    """
    global _CONFIG
    
    if _CONFIG is None:
        return load_config()
    
    return _CONFIG

def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """
    Recursively merge override dict into base dict.
    
    Args:
        base (Dict[str, Any]): Base configuration
        override (Dict[str, Any]): Override configuration
    """
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _merge_configs(base[key], value)
        else:
            base[key] = value

def _override_config_from_env(config: Dict[str, Any], prefix: str = "") -> None:
    """
    Override configuration values from environment variables.
    
    Args:
        config (Dict[str, Any]): Configuration to override
        prefix (str, optional): Current prefix for nested keys
    """
    for key, value in config.items():
        env_key = f"{prefix}_{key}".upper().strip('_')
        
        if isinstance(value, dict):
            _override_config_from_env(value, env_key)
        else:
            env_value = os.getenv(env_key)
            if env_value is not None:
                # Convert to appropriate type
                if isinstance(value, bool):
                    config[key] = env_value.lower() in ('true', 'yes', '1', 'y')
                elif isinstance(value, int):
                    config[key] = int(env_value)
                elif isinstance(value, float):
                    config[key] = float(env_value)
                else:
                    config[key] = env_value

def create_default_config_file(path: str = "config.json") -> None:
    """
    Create a default configuration file.
    
    Args:
        path (str, optional): Path to save the config file
    """
    try:
        with open(path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"Default configuration saved to {path}")
    except Exception as e:
        print(f"Error creating default config file: {str(e)}")
