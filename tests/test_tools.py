import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.channels import create_channel, delete_channel, set_channel_permissions
from src.tools.roles import create_role, assign_role
from src.tools.moderation import timeout_member, kick_member
from src.tools.messages import delete_messages_bulk
from src.tools.server import get_server_info

@pytest.mark.asyncio
async def test_create_text_channel(mock_guild):
    mock_chan = MagicMock()
    mock_chan.name = "general-ai"
    mock_chan.id = 10101
    mock_guild.create_text_channel = AsyncMock(return_value=mock_chan)

    res = await create_channel(mock_guild, name="general-ai", channel_type="text")
    assert "Successfully created text channel #general-ai" in res
    mock_guild.create_text_channel.assert_called_once()

@pytest.mark.asyncio
async def test_delete_channel(mock_guild):
    mock_chan = MagicMock()
    mock_chan.name = "junk-chat"
    mock_chan.delete = AsyncMock()
    mock_guild.channels = [mock_chan]

    res = await delete_channel(mock_guild, channel_identifier="junk-chat")
    assert "Successfully deleted channel #junk-chat" in res
    mock_chan.delete.assert_called_once()

@pytest.mark.asyncio
async def test_create_role(mock_guild):
    mock_role = MagicMock()
    mock_role.name = "Moderator"
    mock_role.id = 20202
    mock_guild.create_role = AsyncMock(return_value=mock_role)

    res = await create_role(mock_guild, name="Moderator", color="blue", permissions=["kick_members", "manage_messages"])
    assert "Successfully created role 'Moderator'" in res
    mock_guild.create_role.assert_called_once()

@pytest.mark.asyncio
async def test_assign_role(mock_guild):
    mock_member = MagicMock()
    mock_member.name = "JohnDoe"
    mock_member.display_name = "John"
    mock_member.add_roles = AsyncMock()
    mock_guild.members = [mock_member]

    mock_role = MagicMock()
    mock_role.name = "VIP"
    mock_guild.roles = [mock_role]

    res = await assign_role(mock_guild, member_identifier="JohnDoe", role_identifier="VIP")
    assert "Assigned role 'VIP' to John" in res
    mock_member.add_roles.assert_called_once_with(mock_role, reason="Assigned via AI Admin")

@pytest.mark.asyncio
async def test_timeout_member(mock_guild):
    mock_member = MagicMock()
    mock_member.name = "TrollUser"
    mock_member.timeout = AsyncMock()
    mock_guild.members = [mock_member]

    res = await timeout_member(mock_guild, member_identifier="TrollUser", duration="30m", reason="Spamming")
    assert "Successfully timed out TrollUser for 30m" in res
    mock_member.timeout.assert_called_once()

@pytest.mark.asyncio
async def test_bulk_delete_messages(mock_guild):
    import discord
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.name = "announcements"
    mock_channel.purge = AsyncMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    mock_guild.text_channels = [mock_channel]

    res = await delete_messages_bulk(mock_guild, channel_identifier="announcements", limit=3)
    assert "Successfully purged 3 messages from #announcements" in res
    mock_channel.purge.assert_called_once_with(limit=3)

@pytest.mark.asyncio
async def test_get_server_info(mock_guild):
    from datetime import datetime, timezone
    mock_guild.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    mock_guild.member_count = 42
    mock_guild.premium_tier = 1
    mock_guild.premium_subscription_count = 2

    res = await get_server_info(mock_guild)
    assert "Server Info for Test Admin Guild" in res
    assert "**Total Members:** 42" in res
