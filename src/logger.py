"""
Action Audit Logger
===================
Logs all administrative operations performed by the AI to console (via structlog)
and optionally to a dedicated Discord audit logging channel.
"""

import discord
import structlog
from src.config import config

logger = structlog.get_logger("discord_ai_admin")

async def log_admin_action(
    bot: discord.Client,
    guild: discord.Guild,
    invoker: discord.Member,
    tool_name: str,
    tool_args: dict,
    result_message: str,
    success: bool = True
):
    """Log the action both locally and to Discord if configured."""
    logger.info(
        "admin_tool_executed",
        guild_id=guild.id,
        guild_name=guild.name,
        invoker_id=invoker.id,
        invoker_name=str(invoker),
        tool=tool_name,
        args=tool_args,
        success=success,
        result=result_message[:150]
    )

    if not config.log_channel_id:
        return

    channel = guild.get_channel(config.log_channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return

    try:
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"🛠️ Admin Action: `{tool_name}`",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Requested By", value=f"{invoker.mention} (`{invoker.name}`)", inline=True)
        embed.add_field(name="Status", value="✅ Success" if success else "❌ Failed", inline=True)
        
        args_str = str(tool_args)
        if len(args_str) > 1000:
            args_str = args_str[:997] + "..."
        embed.add_field(name="Parameters", value=f"```json\n{args_str}\n```", inline=False)
        
        res_str = result_message if len(result_message) <= 1000 else result_message[:997] + "..."
        embed.add_field(name="Result", value=res_str, inline=False)
        
        await channel.send(embed=embed)
    except Exception as err:
        logger.warning("failed_to_post_audit_embed", error=str(err))
