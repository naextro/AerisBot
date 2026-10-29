"""
Channel Management Tools
========================
Handles creation, deletion, editing, listing, and permission overrides for channels.
"""

from typing import Any
import discord

async def create_channel(guild: discord.Guild, **kwargs: Any) -> str:
    """Creates a text, voice, category, stage, or forum channel."""
    name = kwargs.get("name")
    if not name:
        return "Error: 'name' is required to create a channel."

    channel_type = kwargs.get("channel_type", "text").lower()
    category_name = kwargs.get("category")
    topic = kwargs.get("topic")

    category = None
    if category_name:
        category = discord.utils.find(lambda c: c.name.lower() == category_name.lower(), guild.categories)
        if not category and category_name.isdigit():
            category = guild.get_channel(int(category_name))

    try:
        if channel_type == "text":
            ch = await guild.create_text_channel(name=name, category=category, topic=topic)
            return f"Successfully created text channel #{ch.name} (ID: {ch.id})."
        elif channel_type == "voice":
            ch = await guild.create_voice_channel(name=name, category=category)
            return f"Successfully created voice channel 🔊 {ch.name} (ID: {ch.id})."
        elif channel_type == "category":
            ch = await guild.create_category(name=name)
            return f"Successfully created category 📁 {ch.name} (ID: {ch.id})."
        elif channel_type == "stage":
            ch = await guild.create_stage_channel(name=name, category=category)
            return f"Successfully created stage channel 🎭 {ch.name} (ID: {ch.id})."
        elif channel_type == "forum":
            ch = await guild.create_forum_channel(name=name, category=category, topic=topic)
            return f"Successfully created forum channel 💬 {ch.name} (ID: {ch.id})."
        else:
            return f"Unsupported channel_type '{channel_type}'. Choose text, voice, category, stage, or forum."
    except discord.Forbidden:
        return "Error: Missing permissions to create channel. Ensure bot has 'Manage Channels' permission."
    except Exception as e:
        return f"Error creating channel: {str(e)}"

async def delete_channel(guild: discord.Guild, **kwargs: Any) -> str:
    """Deletes an existing channel or category by name or ID."""
    identifier = str(kwargs.get("channel_identifier", "")).strip()
    if not identifier:
        return "Error: 'channel_identifier' (name or ID) is required."

    target = None
    if identifier.isdigit():
        target = guild.get_channel(int(identifier))
    if not target:
        cleaned = identifier.lstrip("#").lower()
        target = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.channels)

    if not target:
        return f"Error: Could not find channel matching '{identifier}'."

    try:
        channel_name = target.name
        await target.delete(reason=kwargs.get("reason", "Deleted via AI Admin"))
        return f"Successfully deleted channel #{channel_name}."
    except discord.Forbidden:
        return "Error: Forbidden. Bot lacks 'Manage Channels' permission."
    except Exception as e:
        return f"Error deleting channel: {str(e)}"

async def edit_channel(guild: discord.Guild, **kwargs: Any) -> str:
    """Edits channel attributes like name, topic, slowmode, or category."""
    identifier = str(kwargs.get("channel_identifier", "")).strip()
    target = None
    if identifier.isdigit():
        target = guild.get_channel(int(identifier))
    if not target:
        cleaned = identifier.lstrip("#").lower()
        target = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.channels)

    if not target:
        return f"Error: Could not find channel '{identifier}'."

    edit_kwargs = {}
    if "new_name" in kwargs:
        edit_kwargs["name"] = kwargs["new_name"]
    if "topic" in kwargs and hasattr(target, "topic"):
        edit_kwargs["topic"] = kwargs["topic"]
    if "slowmode_delay" in kwargs and hasattr(target, "slowmode_delay"):
        edit_kwargs["slowmode_delay"] = int(kwargs["slowmode_delay"])
    if "nsfw" in kwargs and hasattr(target, "nsfw"):
        edit_kwargs["nsfw"] = bool(kwargs["nsfw"])

    try:
        await target.edit(**edit_kwargs)
        return f"Successfully updated channel #{target.name} with settings {edit_kwargs}."
    except discord.Forbidden:
        return "Error: Forbidden to edit channel."
    except Exception as e:
        return f"Error editing channel: {str(e)}"

async def set_channel_permissions(guild: discord.Guild, **kwargs: Any) -> str:
    """Sets channel permission overwrites for a role or member."""
    channel_id = str(kwargs.get("channel_identifier", "")).strip()
    target_channel = None
    if channel_id.isdigit():
        target_channel = guild.get_channel(int(channel_id))
    if not target_channel:
        cleaned = channel_id.lstrip("#").lower()
        target_channel = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.channels)

    if not target_channel:
        return f"Error: Channel '{channel_id}' not found."

    target_name = str(kwargs.get("target_role_or_user", "")).strip()
    target_entity = None
    if target_name.lower() in ("@everyone", "everyone"):
        target_entity = guild.default_role
    elif target_name.isdigit():
        target_entity = guild.get_role(int(target_name)) or guild.get_member(int(target_name))
    if not target_entity:
        target_entity = discord.utils.find(lambda r: r.name.lower() == target_name.lstrip("@").lower(), guild.roles)
    if not target_entity:
        target_entity = discord.utils.find(lambda m: m.name.lower() == target_name.lstrip("@").lower(), guild.members)

    if not target_entity:
        return f"Error: Role or member '{target_name}' not found."

    # Parse permissions to allow/deny
    # Examples: send_messages=False, view_channel=True, read_message_history=True
    perms_kwargs = {}
    for perm_name in ["view_channel", "send_messages", "read_message_history", "manage_messages", "connect", "speak"]:
        if perm_name in kwargs:
            val = kwargs[perm_name]
            perms_kwargs[perm_name] = True if val in (True, "true", "True") else False if val in (False, "false", "False") else None

    try:
        overwrite = target_channel.overwrites_for(target_entity)
        for k, v in perms_kwargs.items():
            setattr(overwrite, k, v)
        await target_channel.set_permissions(target_entity, overwrite=overwrite)
        return f"Successfully updated permissions on #{target_channel.name} for '{target_name}' with {perms_kwargs}."
    except discord.Forbidden:
        return "Error: Missing permission to set channel permissions."
    except Exception as e:
        return f"Error setting permissions: {str(e)}"

async def list_channels(guild: discord.Guild, **kwargs: Any) -> str:
    """Lists channels in the server grouped by category."""
    lines = [f"Channels in {guild.name}:"]
    uncategorized = [c for c in guild.channels if c.category is None and not isinstance(c, discord.CategoryChannel)]
    if uncategorized:
        lines.append("📁 [Uncategorized]")
        for c in uncategorized:
            lines.append(f"  - #{c.name} (type: {c.type}, id: {c.id})")

    for cat in guild.categories:
        lines.append(f"📁 {cat.name} (id: {cat.id})")
        for c in cat.channels:
            lines.append(f"  - #{c.name} (type: {c.type}, id: {c.id})")

    return "\n".join(lines)

# JSON Schemas for AI Function Calling
CHANNEL_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "create_channel",
                "description": "Create a text, voice, stage, forum, or category channel in the Discord server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the new channel"},
                        "channel_type": {
                            "type": "string",
                            "enum": ["text", "voice", "category", "stage", "forum"],
                            "description": "Type of channel to create"
                        },
                        "category": {"type": "string", "description": "Optional category name or ID to put channel under"},
                        "topic": {"type": "string", "description": "Optional topic for text/forum channel"}
                    },
                    "required": ["name", "channel_type"]
                }
            }
        },
        create_channel
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "delete_channel",
                "description": "Delete a channel or category by name or ID. Use with care.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Name or ID of channel to delete"},
                        "reason": {"type": "string", "description": "Reason for deletion"}
                    },
                    "required": ["channel_identifier"]
                }
            }
        },
        delete_channel
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "edit_channel",
                "description": "Modify settings of an existing channel (name, topic, slowmode, nsfw).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Name or ID of channel to edit"},
                        "new_name": {"type": "string", "description": "New name for the channel"},
                        "topic": {"type": "string", "description": "New topic for the channel"},
                        "slowmode_delay": {"type": "integer", "description": "Slowmode delay in seconds (0 to disable)"},
                        "nsfw": {"type": "boolean", "description": "Whether channel is NSFW"}
                    },
                    "required": ["channel_identifier"]
                }
            }
        },
        edit_channel
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "set_channel_permissions",
                "description": "Configure channel permissions (e.g. make read-only, hide from @everyone, allow specific role).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Name or ID of the channel"},
                        "target_role_or_user": {"type": "string", "description": "Role name, '@everyone', or username/ID"},
                        "view_channel": {"type": "boolean", "description": "Allow or deny viewing the channel"},
                        "send_messages": {"type": "boolean", "description": "Allow or deny sending messages in channel"},
                        "read_message_history": {"type": "boolean", "description": "Allow reading history"},
                        "manage_messages": {"type": "boolean", "description": "Allow managing messages"}
                    },
                    "required": ["channel_identifier", "target_role_or_user"]
                }
            }
        },
        set_channel_permissions
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "list_channels",
                "description": "Get a structured list of all channels and categories currently in the server.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        list_channels
    )
]
