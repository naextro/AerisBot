"""
Miscellaneous Administrative Tools
==================================
Invites, webhooks, emoji lookup, member listing.
"""

from typing import Any
import discord

async def create_channel_invite(guild: discord.Guild, **kwargs: Any) -> str:
    """Generates an instant invite for a channel."""
    channel_id = str(kwargs.get("channel_identifier", "")).strip()
    max_age = int(kwargs.get("max_age_seconds", 86400)) # 24h default
    max_uses = int(kwargs.get("max_uses", 0))

    target = None
    if channel_id.isdigit():
        target = guild.get_channel(int(channel_id))
    if not target:
        cleaned = channel_id.lstrip("#").lower()
        target = discord.utils.find(lambda c: c.name.lower() == cleaned, guild.text_channels)

    if not target or not isinstance(target, (discord.TextChannel, discord.VoiceChannel)):
        # Default to first text channel
        target = guild.text_channels[0] if guild.text_channels else None

    if not target:
        return "Error: No suitable channel found to create invite."

    try:
        invite = await target.create_invite(
            max_age=max_age,
            max_uses=max_uses,
            unique=True,
            reason=kwargs.get("reason", "Invite created by AI Admin")
        )
        return f"Invite link generated for #{target.name}: {invite.url}"
    except discord.Forbidden:
        return "Error: Lacking 'Create Instant Invite' permission."
    except Exception as e:
        return f"Error generating invite: {str(e)}"

async def list_members(guild: discord.Guild, **kwargs: Any) -> str:
    """List server members with optional role filter."""
    role_filter = str(kwargs.get("role_filter", "")).strip()
    members = guild.members

    if role_filter:
        target_role = discord.utils.find(lambda r: r.name.lower() == role_filter.lstrip("@").lower(), guild.roles)
        if target_role:
            members = [m for m in members if target_role in m.roles]
        else:
            return f"Error: Role filter '{role_filter}' does not exist."

    sample = members[:30]
    lines = [f"Found {len(members)} member(s) (showing up to 30):"]
    for m in sample:
        top_role = m.top_role.name if m.top_role else "None"
        lines.append(f"- {m.name} (Nick: {m.nick or 'None'}, ID: {m.id}, Top Role: {top_role})")

    return "\n".join(lines)

MISC_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "create_channel_invite",
                "description": "Create an invite URL for the server or a specific channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_identifier": {"type": "string", "description": "Channel name or ID"},
                        "max_age_seconds": {"type": "integer", "description": "Expiration in seconds (0 = never)"},
                        "max_uses": {"type": "integer", "description": "Max number of uses (0 = unlimited)"}
                    }
                }
            }
        },
        create_channel_invite
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "list_members",
                "description": "List members in the server, optionally filtered by a specific role.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role_filter": {"type": "string", "description": "Optional role name to filter by"}
                    }
                }
            }
        },
        list_members
    )
]
