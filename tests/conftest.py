import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 999999999
    guild.name = "Test Admin Guild"
    guild.owner_id = 111111111

    # Channel mocks
    guild.create_text_channel = AsyncMock()
    guild.create_voice_channel = AsyncMock()
    guild.create_category = AsyncMock()
    guild.create_stage_channel = AsyncMock()
    guild.create_forum_channel = AsyncMock()
    guild.get_channel = MagicMock(return_value=None)
    guild.channels = []
    guild.categories = []
    guild.text_channels = []
    guild.voice_channels = []

    # Role mocks
    guild.create_role = AsyncMock()
    guild.get_role = MagicMock(return_value=None)
    guild.roles = []

    # Member mocks
    guild.get_member = MagicMock(return_value=None)
    guild.members = []
    guild.kick = AsyncMock()
    guild.ban = AsyncMock()
    guild.unban = AsyncMock()

    # Guild edit
    guild.edit = AsyncMock()

    return guild

@pytest.fixture
def mock_admin_member(mock_guild):
    member = MagicMock(spec=discord.Member)
    member.id = 12345
    member.name = "ServerAdmin"
    member.display_name = "ServerAdmin"
    member.discriminator = "0001"
    member.guild = mock_guild
    member.roles = []
    member.guild_permissions = MagicMock()
    member.guild_permissions.administrator = True
    return member

@pytest.fixture
def mock_regular_member(mock_guild):
    member = MagicMock(spec=discord.Member)
    member.id = 54321
    member.name = "RegularUser"
    member.display_name = "RegularUser"
    member.discriminator = "0002"
    member.guild = mock_guild
    member.roles = []
    member.guild_permissions = MagicMock()
    member.guild_permissions.administrator = False
    return member
