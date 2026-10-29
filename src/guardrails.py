"""
Guardrails and Authorization Module
====================================
Ensures only authorized server members can invoke AI Admin actions,
and provides interactive Discord UI views (Buttons) for destructive operations.
"""

import discord
from src.config import config

def is_authorized(member: discord.Member) -> bool:
    """
    Check if a member is authorized to run admin commands.
    - If ALLOWED_ROLE_IDS is populated, requires at least one of those roles.
    - Otherwise, falls back to requiring server 'administrator' permission or guild ownership.
    """
    if not isinstance(member, discord.Member):
        return False

    if member.guild.owner_id == member.id:
        return True

    if config.allowed_role_ids:
        member_role_ids = {r.id for r in member.roles}
        if any(role_id in member_role_ids for role_id in config.allowed_role_ids):
            return True

    return member.guild_permissions.administrator

def is_destructive_action(tool_name: str) -> bool:
    """Returns True if the specified tool requires interactive user confirmation."""
    if not config.require_confirmation_for_destructive:
        return False
    return tool_name in config.dangerous_actions

class ConfirmationView(discord.ui.View):
    """Interactive Discord Button View to confirm or cancel high-impact destructive actions."""

    def __init__(self, requester: discord.Member, action_summary: str, timeout: float = 45.0):
        super().__init__(timeout=timeout)
        self.requester = requester
        self.action_summary = action_summary
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "❌ You did not initiate this command.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm Action", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(
            content=f"⏳ **Confirmed:** Proceeding with `{self.action_summary}`...",
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(
            content=f"🚫 **Cancelled:** Action `{self.action_summary}` was aborted.",
            view=None
        )
