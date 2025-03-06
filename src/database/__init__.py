"""Database module for storing and retrieving Discord messages with PostgreSQL."""

from .connection import get_db_pool, setup_database
from .operations import (
    store_message,
    update_message,
    get_messages_by_date,
    get_messages_by_content,
    get_database_stats,
    store_attachment
)

__all__ = [
    'get_db_pool',
    'setup_database',
    'store_message',
    'update_message',
    'get_messages_by_date',
    'get_messages_by_content',
    'get_database_stats',
    'store_attachment'
]
