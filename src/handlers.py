# ============================================================
# src/handlers.py — FULL FILE
# ============================================================
"""
Agentic Execution Loop
======================
Handles incoming natural language commands from Discord users, coordinates
with the AI model (Gemma 4 31B), checks authorization, triggers interactive
confirmation buttons if needed, executes the corresponding tools, and loops
until the AI completes the task.
"""

import json
import re
from typing import Any
import discord
from discord.ext import commands
import structlog

from src.config import config
from src.ai_client import request_ai_decision
from src.tools import get_tool_schemas_for_prompt, get_tool_handler
from src.guardrails import is_authorized, is_destructive_action, ConfirmationView
from src.logger import log_admin_action

logger = structlog.get_logger("agentic_loop")

def _repair_tool_arguments(raw_args: Any) -> dict[str, Any]:
    """
    Small/local fallback models occasionally emit tool-call arguments with
    trailing garbage after the JSON object (e.g. 'BadRequestError' /
    'trailing characters at line 1 column 74'). Try a straight parse first,
    then fall back to regex-extracting the outermost balanced {...} block.
    """
    if not isinstance(raw_args, str):
        return raw_args or {}

    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_args, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Walk brace depth to find where the FIRST complete object ends,
            # and cut off whatever trailing junk comes after it.
            depth = 0
            end_idx = None
            for i, ch in enumerate(candidate):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx is not None:
                try:
                    return json.loads(candidate[:end_idx + 1])
                except json.JSONDecodeError:
                    pass

    logger.warning("tool_args_json_repair_failed", raw_args=raw_args)
    return {}

async def build_conversation_context(channel: discord.TextChannel, bot_user: discord.ClientUser) -> list[dict[str, Any]]:
    """Fetches recent channel messages to provide conversational history."""
    history_messages = []
    try:
        async for msg in channel.history(limit=config.context_window_size):
            # Skip messages from other bots
            if msg.author.bot and msg.author.id != bot_user.id:
                continue

            role = "assistant" if msg.author.id == bot_user.id else "user"
            content = msg.clean_content
            if content:
                # Truncate individual older messages to 300 chars to conserve TPM budget
                truncated = content if len(content) <= 300 else content[:297] + "..."
                history_messages.append({
                    "role": role,
                    "content": f"{msg.author.display_name}: {truncated}"
                })
    except Exception as e:
        logger.warning("failed_to_fetch_history", error=str(e))

    # Oldest first
    history_messages.reverse()
    return history_messages

async def execute_agentic_request(
    bot: commands.Bot,
    origin_message: discord.Message,
    user_prompt: str
):
    """
    Main loop executing an AI request with tool calling capabilities.
    """
    invoker = origin_message.author
    guild = origin_message.guild
    channel = origin_message.channel

    if not guild or not isinstance(invoker, discord.Member):
        await channel.send("❌ Admin actions can only be performed inside a Discord server.")
        return

    # Strictly silent in auto-nickname channel (never reply or process)
    if config.auto_nickname_channel_id and channel.id == config.auto_nickname_channel_id:
        return

    # 1. Authorization check
    if not is_authorized(invoker):
        await origin_message.reply("⛔ **Access Denied:** You need Discord Administrator privileges to issue admin commands.")
        return

    # 2. Build context
    messages = await build_conversation_context(channel, bot.user)
    # Append current explicit instruction
    messages.append({
        "role": "user",
        "content": f"{invoker.display_name} requested: {user_prompt}"
    })

    tool_schemas = get_tool_schemas_for_prompt(user_prompt)
    max_turns = 10 # Prevent infinite loops

    # 3. Agentic Loop
    for turn in range(max_turns):
        async with channel.typing():
            try:
                ai_response = await request_ai_decision(messages=messages, tools=tool_schemas)
            except Exception as e:
                logger.error("llm_api_call_failed", error=str(e))
                await origin_message.reply(f"⚠️ **AI API Error:** Failed communicating with Gemini/Gemma endpoint: `{str(e)}`")
                return

        if not ai_response or not getattr(ai_response, "choices", None):
            await origin_message.reply("⚠️ Received empty response from AI model.")
            return

        choice = ai_response.choices[0]
        assistant_msg = getattr(choice, "message", None)
        if assistant_msg is None:
            await origin_message.reply("⚠️ Received invalid message structure from AI model.")
            return

        # Check if the AI decided to call any tools
        tool_calls = getattr(assistant_msg, "tool_calls", None)
        if tool_calls:
            # Cleanly format assistant tool_calls message (exclude None fields that trigger Gemini 400 'Value is not a struct: null')
            formatted_tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ]
            clean_assistant_entry = {
                "role": "assistant",
                "tool_calls": formatted_tool_calls,
            }
            messages.append(clean_assistant_entry)

            for tool_call in assistant_msg.tool_calls:
                tool_name = tool_call.function.name
                raw_args = tool_call.function.arguments

                parsed_args = _repair_tool_arguments(raw_args)

                # Check if this tool is dangerous and requires interactive user confirmation
                if is_destructive_action(tool_name):
                    view = ConfirmationView(
                        requester=invoker,
                        action_summary=f"{tool_name} with args {parsed_args}"
                    )
                    prompt_msg = await origin_message.reply(
                        f"⚠️ **High-Impact Action Request**\nThe AI wants to execute: `{tool_name}` with parameters: ```json\n{json.dumps(parsed_args, indent=2)}\n```\nClick below to proceed or abort.",
                        view=view
                    )
                    await view.wait()

                    if not view.confirmed:
                        tool_result = f"Action '{tool_name}' was CANCELLED by the user."
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                        continue

                # Execute the tool
                handler = get_tool_handler(tool_name)
                success = True
                if handler:
                    try:
                        logger.info("executing_tool", tool=tool_name, args=parsed_args)
                        tool_result = await handler(guild=guild, bot=bot, **parsed_args)
                    except Exception as exc:
                        success = False
                        tool_result = f"Exception executing tool '{tool_name}': {str(exc)}"
                else:
                    success = False
                    tool_result = f"Tool '{tool_name}' does not exist in registry."

                # Log the action (Discord audit channel + console)
                await log_admin_action(
                    bot=bot,
                    guild=guild,
                    invoker=invoker,
                    tool_name=tool_name,
                    tool_args=parsed_args,
                    result_message=tool_result,
                    success=success
                )

                # Feed the tool execution result back to the AI (no truncation on any tool)
                res_str = str(tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": res_str
                })

            # Continue the loop so the model can inspect results and provide final response or next step
            continue

        else:
            # Model generated a final response
            raw_reply = assistant_msg.content or "Task finished."
            # Strip internal <thought>...</thought> reasoning tags so user only sees the clean response
            final_reply = re.sub(r"<thought>.*?</thought>", "", raw_reply, flags=re.DOTALL).strip()
            if not final_reply:
                final_reply = "Task completed successfully."

            # Discord has a 2000 character limit per message
            chunks = [final_reply[i:i + 1950] for i in range(0, len(final_reply), 1950)]
            for chunk in chunks:
                await origin_message.reply(chunk)
            return

    await origin_message.reply("⚠️ Reached maximum automated tool iteration limit.")