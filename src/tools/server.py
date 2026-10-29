"""
Server Information and Settings Tools
======================================
Tools for server details, member prunes, and server name updates.
"""

from typing import Any
import discord

async def get_server_info(guild: discord.Guild, **kwargs: Any) -> str:
    """Retrieves server statistics, member counts, channel counts, and boost levels."""
    text_count = len(guild.text_channels)
    voice_count = len(guild.voice_channels)
    category_count = len(guild.categories)
    role_count = len(guild.roles)
    member_count = guild.member_count or len(guild.members)
    boost_count = guild.premium_subscription_count or 0
    tier = guild.premium_tier

    owner = guild.owner
    owner_str = f"{owner.name}#{owner.discriminator}" if owner else f"ID {guild.owner_id}"

    info = [
        f"**Server Info for {guild.name}**",
        f"- **Server ID:** `{guild.id}`",
        f"- **Owner:** {owner_str}",
        f"- **Total Members:** {member_count}",
        f"- **Channels:** {text_count} Text | {voice_count} Voice | {category_count} Categories",
        f"- **Total Roles:** {role_count}",
        f"- **Nitro Boost Level:** Level {tier} ({boost_count} boosts)",
        f"- **Created At:** {guild.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    ]
    return "\n".join(info)

async def set_server_name(guild: discord.Guild, **kwargs: Any) -> str:
    """Updates the server name."""
    new_name = str(kwargs.get("new_name", "")).strip()
    if not new_name:
        return "Error: 'new_name' is required."

    try:
        old_name = guild.name
        await guild.edit(name=new_name, reason=kwargs.get("reason", "Name updated by AI Admin"))
        return f"Successfully renamed server from '{old_name}' to '{new_name}'."
    except discord.Forbidden:
        return "Error: Bot lacks 'Manage Server' permission."
    except Exception as e:
        return f"Error changing server name: {str(e)}"

SERVER_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "get_server_info",
                "description": "Fetch overall server statistics, member counts, channels, and boost details.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        get_server_info
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "set_server_name",
                "description": "Rename the Discord server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "new_name": {"type": "string", "description": "The new server name"}
                    },
                    "required": ["new_name"]
                }
            }
        },
        set_server_name
    )
]
