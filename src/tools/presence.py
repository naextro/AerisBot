"""
Bot Presence Tools
==================
Change the bot's presence / status (online, idle, dnd, invisible)
and activity (playing, watching, listening, streaming, competing).
"""

from typing import Any
import discord
from discord.ext import commands


# Map user-friendly strings to discord.py enums
_STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "do_not_disturb": discord.Status.dnd,
    "invisible": discord.Status.invisible,
    "offline": discord.Status.invisible,
}

_ACTIVITY_TYPE_MAP = {
    "playing": discord.ActivityType.playing,
    "streaming": discord.ActivityType.streaming,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching,
    "competing": discord.ActivityType.competing,
}


async def change_bot_presence(guild: discord.Guild, **kwargs: Any) -> str:
    """Change the bot's displayed presence (status + activity)."""
    bot: commands.Bot | None = kwargs.get("bot")
    if bot is None:
        return "Error: Bot instance not available — cannot change presence."

    status_str = str(kwargs.get("status", "online")).strip().lower()
    activity_type_str = str(kwargs.get("activity_type", "")).strip().lower()
    activity_text = str(kwargs.get("activity_text", "")).strip()
    streaming_url = str(kwargs.get("streaming_url", "")).strip() or None

    # Resolve status
    new_status = _STATUS_MAP.get(status_str, discord.Status.online)

    # Resolve activity (optional)
    new_activity: discord.Activity | discord.Streaming | None = None
    if activity_type_str and activity_text:
        if activity_type_str == "streaming":
            new_activity = discord.Streaming(
                name=activity_text,
                url=streaming_url or "https://twitch.tv/placeholder",
            )
        else:
            act_type = _ACTIVITY_TYPE_MAP.get(activity_type_str, discord.ActivityType.playing)
            new_activity = discord.Activity(type=act_type, name=activity_text)

    try:
        await bot.change_presence(status=new_status, activity=new_activity)
        parts = [f"Status set to **{new_status.value}**"]
        if new_activity:
            parts.append(f"Activity set to **{activity_type_str} {activity_text}**")
        return "Presence updated! " + ", ".join(parts) + "."
    except Exception as e:
        return f"Error changing presence: {str(e)}"


PRESENCE_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "change_bot_presence",
                "description": (
                    "Change the bot's presence. Can set status (online/idle/dnd/invisible) "
                    "and an activity like 'Playing Minecraft', 'Listening to Spotify', "
                    "'Watching YouTube', 'Streaming on Twitch', or 'Competing in ranked'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Bot status: online, idle, dnd, or invisible",
                            "enum": ["online", "idle", "dnd", "invisible"],
                        },
                        "activity_type": {
                            "type": "string",
                            "description": "Type of activity to display",
                            "enum": ["playing", "streaming", "listening", "watching", "competing"],
                        },
                        "activity_text": {
                            "type": "string",
                            "description": "The text to display for the activity (e.g. 'Minecraft', 'Lo-fi beats')",
                        },
                        "streaming_url": {
                            "type": "string",
                            "description": "Twitch/YouTube URL (only used when activity_type is 'streaming')",
                        },
                    },
                },
            },
        },
        change_bot_presence,
    ),
]
