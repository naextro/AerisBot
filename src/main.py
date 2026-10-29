"""
Bot Main Entrypoint
===================
Initializes discord.py client, registers commands, sync handlers, and starts bot.
"""

import os
import sys
from pathlib import Path

# Ensure project root is always in sys.path regardless of execution method
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Support Pterodactyl container local prefix installation
LOCAL_PACKAGES = PROJECT_ROOT / ".local" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.insert(0, str(LOCAL_PACKAGES))

import discord
from discord import app_commands
from discord.ext import commands
import structlog

from src.config import config
from src.handlers import execute_agentic_request
from src.badword_filter import BadWordFilter, handle_bad_message
from src.tools.wordlist import add_words, delete_words
from src.ai_client import runtime_state, current_chain_status, PROVIDER_DISPLAY_NAMES, DEFAULT_CHAIN_ORDER

# Loaded once at startup — frozenset lives in memory, zero disk I/O per message
_bad_filter = BadWordFilter(PROJECT_ROOT / "badwords.txt")

logger = structlog.get_logger("bot_entrypoint")

# Enable privileged intents required for admin bots
intents = discord.Intents.default()
intents.message_content = True  # Required to read instructions in channels
intents.members = True          # Required to manage roles, kick, ban, list members
intents.guilds = True           # Required for channel/guild management

bot = commands.Bot(command_prefix=config.bot_prefix, intents=intents)
bot.bad_filter = _bad_filter  # exposed so wordlist tools can hot-reload it

def _is_admin(interaction: discord.Interaction) -> bool:
    return isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator

def _is_admin_ctx(ctx: commands.Context) -> bool:
    return isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator

@bot.event
async def on_ready():
    logger.info("bot_online", user=str(bot.user), user_id=bot.user.id, guilds_count=len(bot.guilds))
    print(f"🤖 Bot logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🌐 Serving in {len(bot.guilds)} server(s)")
    print(f"🧠 AI Model: {config.ai_model}")
    print(f"🔗 AI Endpoint: {config.ai_base_url}")
    print("Ready to receive natural language admin requests!")

@bot.hybrid_command(name="admin", description="Give an AI admin instruction (e.g. 'create a channel', 'make #rules read-only')")
async def admin(ctx: commands.Context, *, instruction: str):
    """Slash/hybrid command entrypoint."""
    await execute_agentic_request(bot=bot, origin_message=ctx.message, user_prompt=instruction)

_PROVIDER_CHOICES = [
    app_commands.Choice(name=display, value=label)
    for label, display in PROVIDER_DISPLAY_NAMES.items()
]

@bot.tree.command(name="ai-set-provider", description="[Admin] Force which AI provider is tried first in the fallback chain")
@app_commands.choices(provider=_PROVIDER_CHOICES)
async def ai_set_provider(interaction: discord.Interaction, provider: app_commands.Choice[str]):
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ You need Administrator permission to use this.", ephemeral=True)
        return
    runtime_state.primary_override = provider.value
    logger.info("ai_provider_override_set", by=interaction.user.id, provider=provider.value)
    await interaction.response.send_message(
        f"✅ **{provider.name}** now goes first. Current chain:\n{current_chain_status()}"
    )

@bot.tree.command(name="ai-set-model", description="[Admin] Override the model string used for a specific AI provider")
@app_commands.choices(provider=_PROVIDER_CHOICES)
@app_commands.describe(model="Exact model string to use for this provider, e.g. gemma-4-31b-it")
async def ai_set_model(interaction: discord.Interaction, provider: app_commands.Choice[str], model: str):
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ You need Administrator permission to use this.", ephemeral=True)
        return
    runtime_state.model_overrides[provider.value] = model
    logger.info("ai_model_override_set", by=interaction.user.id, provider=provider.value, model=model)
    await interaction.response.send_message(
        f"✅ **{provider.name}** now uses `{model}`. Current chain:\n{current_chain_status()}"
    )

@bot.tree.command(name="ai-reset", description="[Admin] Reset the AI fallback chain to default order and models")
async def ai_reset(interaction: discord.Interaction):
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ You need Administrator permission to use this.", ephemeral=True)
        return
    runtime_state.reset()
    logger.info("ai_chain_reset", by=interaction.user.id)
    await interaction.response.send_message(
        f"🔄 Reset to default chain:\n{current_chain_status()}"
    )

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots
    if message.author.bot:
        return

    # Resolve context once — reused for both the filter exemption check and dispatch below
    ctx = await bot.get_context(message)

    # --- Bad word filter (runs before anything else) ---
    # Only in guild channels, not DMs. Skip for !add/!remove — their entire
    # purpose is to contain bad words, so filtering them would break the commands.
    if message.guild:
        is_wordlist_cmd = ctx.command is not None and ctx.command.name in ("add", "remove")
        if not is_wordlist_cmd and _bad_filter.contains(message.content):
            await handle_bad_message(message)
            return  # stop processing — don't run commands or AI on a deleted message
    # ---------------------------------------------------

    # Check for auto-nickname channel
    if config.auto_nickname_channel_id and message.channel.id == config.auto_nickname_channel_id:
        if isinstance(message.author, discord.Member) and message.guild:
            raw_text = message.clean_content.strip()
            if raw_text:
                try:
                    if raw_text.lower() == ".reset":
                        await message.author.edit(nick=None, reason="Auto-nickname channel — reset")
                        logger.info("auto_nickname_reset", user_id=message.author.id)
                    else:
                        new_nick = raw_text[:32]  # Discord nickname limit
                        await message.author.edit(nick=new_nick, reason="Auto-nickname channel")
                        logger.info("auto_nickname_applied", user_id=message.author.id, nickname=new_nick)
                    await message.add_reaction("✅")
                except discord.Forbidden:
                    logger.warning("auto_nickname_forbidden", user_id=message.author.id, error="Hierarchy or missing permissions")
                    await message.add_reaction("❌")
                    await message.reply("idk what happend but i cant do it, u prolly did sum blackmagic or smthn")
                except Exception as e:
                    logger.warning("auto_nickname_error", user_id=message.author.id, error=str(e))
                    await message.add_reaction("❌")
                    await message.reply("idk what happend but i cant do it, u prolly did sum blackmagic or smthn")
        # Never process bot commands in the auto-nickname channel
        return

    # Process standard commands first (e.g. !sync, !admin, !add, !remove)
    await bot.invoke(ctx)

    # If the bot is directly @mentioned in a server channel
    if bot.user in message.mentions:
        # Strip the mention tag from text
        clean_prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if clean_prompt:
            await execute_agentic_request(bot=bot, origin_message=message, user_prompt=clean_prompt)

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context):
    """Syncs slash commands to Discord globally or to this server."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Successfully synced {len(synced)} application command(s) globally.")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {str(e)}")

@bot.command(name="add")
async def add_badwords(ctx: commands.Context, *, words: str):
    """Adds one or more comma-separated words/phrases to badwords.txt and hot-reloads."""
    if not _is_admin_ctx(ctx):
        await ctx.reply("⛔ You need Administrator permission to use this.")
        return

    result = await add_words(bot=bot, words=words)
    logger.info("badwords_added", by=ctx.author.id, result=result)
    await ctx.reply(f"✅ {result}")

@bot.command(name="remove")
async def remove_badwords(ctx: commands.Context, *, words: str):
    """Removes one or more comma-separated words/phrases from badwords.txt and hot-reloads."""
    if not _is_admin_ctx(ctx):
        await ctx.reply("⛔ You need Administrator permission to use this.")
        return

    result = await delete_words(bot=bot, words=words)
    logger.info("badwords_removed", by=ctx.author.id, result=result)
    await ctx.reply(f"✅ {result}")

def start():
    if not config.discord_token:
        print("❌ ERROR: DISCORD_BOT_TOKEN is not set in environment or .env!")
        print("Please configure your .env file before starting the bot.")
        sys.exit(1)
    
    bot.run(config.discord_token)

if __name__ == "__main__":
    start()