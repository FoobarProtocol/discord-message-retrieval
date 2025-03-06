"""Database schema definitions for Discord message storage."""

# Schema for PostgreSQL

MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    channel_name TEXT NOT NULL,
    guild_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    author_name TEXT NOT NULL,
    content TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    has_attachments BOOLEAN DEFAULT FALSE,
    reference_message_id BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

ATTACHMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id BIGINT PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    url TEXT NOT NULL,
    content_type TEXT,
    width INTEGER,
    height INTEGER,
    size INTEGER,
    proxy_url TEXT,
    description TEXT,
    data BYTEA,
    CONSTRAINT fk_message
        FOREIGN KEY(message_id)
        REFERENCES messages(message_id)
        ON DELETE CASCADE
);
"""

# Create indices for faster searching
INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_messages_guild_id ON messages(guild_id);",
    "CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);",
    "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_messages_author_id ON messages(author_id);",
    "CREATE INDEX IF NOT EXISTS idx_attachments_message_id ON attachments(message_id);",
    # Full text search index for content
    """
    CREATE INDEX IF NOT EXISTS idx_messages_content_tsvector ON messages 
    USING GIN (to_tsvector('english', content));
    """
]

# Views for common queries
VIEWS = [
    """
    CREATE OR REPLACE VIEW messages_with_attachments AS
    SELECT m.message_id, m.channel_id, m.channel_name, m.guild_id, 
           m.author_id, m.author_name, m.content, m.timestamp,
           m.is_pinned, m.has_attachments, m.reference_message_id,
           a.attachment_id, a.filename, a.url, a.content_type, 
           a.width, a.height
    FROM messages m
    LEFT JOIN attachments a ON m.message_id = a.message_id
    WHERE m.has_attachments = TRUE;
    """
]

# Function to generate the database schema
def get_schema_creation_commands():
    """Return a list of SQL commands to create the database schema."""
    return [
        MESSAGES_TABLE,
        ATTACHMENTS_TABLE,
        *INDICES,
        *VIEWS
    ]
