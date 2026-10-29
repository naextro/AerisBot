import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.handlers import execute_agentic_request

@pytest.mark.asyncio
async def test_unauthorized_user_blocked(mock_guild, mock_regular_member):
    bot = MagicMock()
    msg = MagicMock(spec=discord.Message)
    msg.author = mock_regular_member
    msg.guild = mock_guild
    msg.channel = MagicMock()
    msg.reply = AsyncMock()

    await execute_agentic_request(bot, msg, "delete all channels")
    msg.reply.assert_called_once()
    assert "Access Denied" in msg.reply.call_args[0][0]

@pytest.mark.asyncio
async def test_agentic_tool_dispatch(mock_guild, mock_admin_member):
    bot = MagicMock()
    msg = MagicMock(spec=discord.Message)
    msg.author = mock_admin_member
    msg.guild = mock_guild
    channel = MagicMock(spec=discord.TextChannel)
    channel.typing = MagicMock()
    channel.typing.return_value.__aenter__ = AsyncMock()
    channel.typing.return_value.__aexit__ = AsyncMock()

    async def mock_history(limit=10):
        return
        yield

    channel.history = mock_history
    msg.channel = channel
    msg.reply = AsyncMock()

    # Create mock tool call response from LLM
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc123"
    mock_tool_call.function.name = "create_channel"
    mock_tool_call.function.arguments = json.dumps({"name": "bot-testing", "channel_type": "text"})

    first_response = MagicMock()
    first_choice = MagicMock()
    first_msg = MagicMock()
    first_msg.tool_calls = [mock_tool_call]
    first_msg.model_dump.return_value = {"role": "assistant", "content": None}
    first_choice.message = first_msg
    first_response.choices = [first_choice]

    # Second response terminates with final text
    second_response = MagicMock()
    second_choice = MagicMock()
    second_msg = MagicMock()
    second_msg.tool_calls = None
    second_msg.content = "Created the channel #bot-testing as requested!"
    second_choice.message = second_msg
    second_response.choices = [second_choice]

    created_chan = MagicMock()
    created_chan.name = "bot-testing"
    created_chan.id = 55555
    mock_guild.create_text_channel = AsyncMock(return_value=created_chan)

    with patch("src.handlers.request_ai_decision", AsyncMock(side_effect=[first_response, second_response])):
        await execute_agentic_request(bot, msg, "please make a channel called bot-testing")

    mock_guild.create_text_channel.assert_called_once()
    msg.reply.assert_called_with("Created the channel #bot-testing as requested!")
