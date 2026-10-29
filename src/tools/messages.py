"""
Message Management Tools
========================
Handles bulk deletion (purging), pinning, unpinning, and broadcasting messages/embeds.
"""

from typing import Any
import discord

async def delete_messages_bulk(guild: discord.Guild, **kwargs: Any) -> str:
    """Bulk purges the last N messages in a channel."""
    channel_id = str(kwargs.get("channel_identifier", "")).strip()
    limit = int(kwargs.get("limit", 10))
    limit = max(1, min(limit, 100)) # Discord bulk delete limit is 100

    target_channel = None
    if channel_id.isdigit():
        target_channel = guild.get_channel(int(channel_id))
    if not target_channel:
        cleaned = channel_id.lstrip("#").lower()
        target_channel = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.text_channels)

    if not target_channel or not isinstance(target_channel, discord.TextChannel):
        return f"Error: Text channel '{channel_id}' not found."

    try:
        deleted = await target_channel.purge(limit=limit)
        return f"Successfully purged {len(deleted)} messages from #{target_channel.name}."
    except discord.Forbidden:
        return "Error: Missing 'Manage Messages' permission."
    except Exception as e:
        return f"Error purging messages: {str(e)}"

async def pin_message(guild: discord.Guild, **kwargs: Any) -> str:
    """Pins a message in a channel by message ID."""
    channel_id = str(kwargs.get("channel_identifier", "")).strip()
    message_id = str(kwargs.get("message_id", "")).strip()

    if not message_id.isdigit():
        return "Error: Valid integer 'message_id' is required."

    target_channel = None
    if channel_id.isdigit():
        target_channel = guild.get_channel(int(channel_id))
    if not target_channel:
        cleaned = channel_id.lstrip("#").lower()
        target_channel = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.text_channels)

    if not target_channel or not isinstance(target_channel, discord.TextChannel):
        return f"Error: Text channel '{channel_id}' not found."

    try:
        msg = await target_channel.fetch_message(int(message_id))
        await msg.pin(reason=kwargs.get("reason", "Pinned by AI Admin"))
        return f"Successfully pinned message {message_id} in #{target_channel.name}."
    except discord.NotFound:
        return f"Error: Message {message_id} not found."
    except discord.Forbidden:
        return "Error: Missing permission to pin messages."
    except Exception as e:
        return f"Error pinning message: {str(e)}"

async def send_channel_message(guild: discord.Guild, **kwargs: Any) -> str:
    """Sends a direct or announcement message into a target channel."""
    channel_id = str(kwargs.get("channel_identifier", "")).strip()
    content = kwargs.get("content", "")

    if not content:
        return "Error: 'content' is required."

    target_channel = None
    if channel_id.isdigit():
        target_channel = guild.get_channel(int(channel_id))
    if not target_channel:
        cleaned = channel_id.lstrip("#").lower()
        target_channel = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.text_channels)

    if not target_channel or not isinstance(target_channel, discord.TextChannel):
        return f"Error: Text channel '{channel_id}' not found."

    try:
        sent = await target_channel.send(content)
        return f"Message dispatched to #{target_channel.name} (ID: {sent.id})."
    except discord.Forbidden:
        return f"Error: Forbidden to send message to #{target_channel.name}."
    except Exception as e:
        return f"Error sending message: {str(e)}"

MESSAGE_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "delete_messages_bulk",
                "description": "Purge / bulk delete the last N messages from a channel (max 100).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Channel name or ID"},
                        "limit": {"type": "integer", "description": "Number of messages to delete (1-100)"}
                    },
                    "required": ["channel_identifier", "limit"]
                }
            }
        },
        delete_messages_bulk
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "pin_message",
                "description": "Pin a specific message in a channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Channel name or ID"},
                        "message_id": {"type": "string", "description": "Message ID to pin"}
                    },
                    "required": ["channel_identifier", "message_id"]
                }
            }
        },
        pin_message
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "send_channel_message",
                "description": "Send an announcement or message to any specific channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Channel name or ID"},
                        "content": {"type": "string", "description": "Text content of message"}
                    },
                    "required": ["channel_identifier", "content"]
                }
            }
        },
        send_channel_message
    )
]
