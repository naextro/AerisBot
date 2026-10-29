"""
Moderation Tools
================
Handles kicking, banning, unbanning, timing out (muting), and removing timeouts.
"""

from datetime import timedelta
import re
from typing import Any
import discord

def parse_duration(duration_str: str) -> timedelta:
    """Parses strings like '10m', '1h', '2d', '30s' into timedelta."""
    match = re.match(r"^(\d+)\s*(s|m|h|d|w)?$", duration_str.strip().lower())
    if not match:
        return timedelta(minutes=10) # default fallback
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    elif unit == "w":
        return timedelta(weeks=val)
    return timedelta(minutes=val)

async def kick_member(guild: discord.Guild, **kwargs: Any) -> str:
    """Kicks a member from the server."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    reason = kwargs.get("reason", "Kicked by AI Admin")

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned or (m.nick and m.nick.lower() == cleaned), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    try:
        await member.kick(reason=reason)
        return f"Successfully kicked {member.name}#{member.discriminator} (Reason: {reason})."
    except discord.Forbidden:
        return f"Error: Forbidden. Cannot kick {member.name}. Their role may be higher than the bot's."
    except Exception as e:
        return f"Error kicking member: {str(e)}"

async def ban_member(guild: discord.Guild, **kwargs: Any) -> str:
    """Bans a member or user ID from the server."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    reason = kwargs.get("reason", "Banned by AI Admin")
    delete_days = int(kwargs.get("delete_message_days", 0))

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned or (m.nick and m.nick.lower() == cleaned), guild.members)

    try:
        if member:
            await member.ban(reason=reason, delete_message_days=min(delete_days, 7))
            return f"Successfully banned {member.name}#{member.discriminator} (Reason: {reason})."
        elif member_id.isdigit():
            user = await guild.ban(discord.Object(id=int(member_id)), reason=reason)
            return f"Successfully banned user ID {member_id}."
        else:
            return f"Error: Member or User ID '{member_id}' not found."
    except discord.Forbidden:
        return "Error: Cannot ban user. The bot lacks permission or user has higher hierarchy."
    except Exception as e:
        return f"Error banning member: {str(e)}"

async def unban_member(guild: discord.Guild, **kwargs: Any) -> str:
    """Unbans a user by username or ID."""
    user_id = str(kwargs.get("user_identifier", "")).strip()
    reason = kwargs.get("reason", "Unbanned by AI Admin")

    try:
        async for ban_entry in guild.bans():
            user = ban_entry.user
            if str(user.id) == user_id or user.name.lower() == user_id.lower():
                await guild.unban(user, reason=reason)
                return f"Successfully unbanned {user.name}#{user.discriminator}."
        return f"Error: No ban entry found matching '{user_id}'."
    except discord.Forbidden:
        return "Error: Bot lacks permission to unban."
    except Exception as e:
        return f"Error unbanning user: {str(e)}"

async def timeout_member(guild: discord.Guild, **kwargs: Any) -> str:
    """Mutes/timeouts a member for a duration (e.g. '10m', '1h', '24h')."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    duration_str = str(kwargs.get("duration", "10m"))
    reason = kwargs.get("reason", "Timed out by AI Admin")

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned or (m.nick and m.nick.lower() == cleaned), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    delta = parse_duration(duration_str)
    # Discord maximum timeout is 28 days
    if delta > timedelta(days=28):
        delta = timedelta(days=28)

    try:
        await member.timeout(delta, reason=reason)
        return f"Successfully timed out {member.name} for {duration_str} (Reason: {reason})."
    except discord.Forbidden:
        return f"Error: Cannot timeout {member.name}. Member has higher hierarchy or bot lacks permission."
    except Exception as e:
        return f"Error applying timeout: {str(e)}"

async def remove_timeout(guild: discord.Guild, **kwargs: Any) -> str:
    """Removes timeout (unmutes) from a member."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned or (m.nick and m.nick.lower() == cleaned), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    try:
        await member.timeout(None, reason=kwargs.get("reason", "Timeout removed by AI Admin"))
        return f"Successfully removed timeout for {member.name}."
    except discord.Forbidden:
        return "Error: Cannot remove timeout from member."
    except Exception as e:
        return f"Error removing timeout: {str(e)}"

async def set_member_nickname(guild: discord.Guild, **kwargs: Any) -> str:
    """Changes or resets the nickname of any server member."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    nickname = kwargs.get("nickname")  # None or empty string resets to original username
    if nickname is not None:
        nickname = str(nickname).strip()
        if len(nickname) > 32:
            nickname = nickname[:32]
        if not nickname:
            nickname = None  # Reset to default username

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned or (m.nick and m.nick.lower() == cleaned), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    reason = kwargs.get("reason", "Nickname changed via AI Admin")
    try:
        old_display = member.display_name
        await member.edit(nick=nickname, reason=reason)
        if nickname:
            return f"Successfully changed {old_display}'s nickname to '{nickname}'."
        else:
            return f"Successfully reset {old_display}'s nickname to default ({member.name})."
    except discord.Forbidden:
        return f"Error: Cannot change nickname for {member.name}. Member has higher or equal role hierarchy, or bot lacks 'Manage Nicknames' permission."
    except Exception as e:
        return f"Error changing nickname: {str(e)}"

MODERATION_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "kick_member",
                "description": "Kick a member out of the Discord server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Username, mention, or ID of member to kick"},
                        "reason": {"type": "string", "description": "Reason for kick"}
                    },
                    "required": ["member_identifier"]
                }
            }
        },
        kick_member
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "ban_member",
                "description": "Ban a member or user ID from the Discord server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Username, mention, or ID of member to ban"},
                        "reason": {"type": "string", "description": "Reason for ban"},
                        "delete_message_days": {"type": "integer", "description": "Days of messages to purge (0-7)"}
                    },
                    "required": ["member_identifier"]
                }
            }
        },
        ban_member
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "unban_member",
                "description": "Unban a previously banned user by username or ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_identifier": {"type": "string", "description": "Username or ID of the banned user"},
                        "reason": {"type": "string", "description": "Reason for unban"}
                    },
                    "required": ["user_identifier"]
                }
            }
        },
        unban_member
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "timeout_member",
                "description": "Mute or timeout a user so they cannot chat or speak in voice (e.g. 10m, 1h, 1d).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Username, mention, or ID of member"},
                        "duration": {"type": "string", "description": "Duration string (e.g. '30m', '2h', '1d')"},
                        "reason": {"type": "string", "description": "Reason for timeout"}
                    },
                    "required": ["member_identifier", "duration"]
                }
            }
        },
        timeout_member
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "remove_timeout",
                "description": "Remove an active timeout from a member (unmute).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Username, mention, or ID of member"},
                        "reason": {"type": "string", "description": "Reason for removing timeout"}
                    },
                    "required": ["member_identifier"]
                }
            }
        },
        remove_timeout
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "set_member_nickname",
                "description": "Change or reset a member's server nickname. Can rename any user or bot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Username, mention, or ID of member"},
                        "nickname": {"type": "string", "description": "New nickname (leave empty or omit to reset to original username)"},
                        "reason": {"type": "string", "description": "Reason for nickname change"}
                    },
                    "required": ["member_identifier"]
                }
            }
        },
        set_member_nickname
    )
]
