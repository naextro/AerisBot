# ============================================================
# src/tools/__init__.py — FULL FILE
# ============================================================
"""
Tools Registry
==============
Aggregates all tool definitions (JSON schemas) and their execution handlers.
"""

from typing import Callable, Any
from src.tools.channels import CHANNEL_TOOLS_CONFIG
from src.tools.roles import ROLE_TOOLS_CONFIG
from src.tools.moderation import MODERATION_TOOLS_CONFIG
from src.tools.messages import MESSAGE_TOOLS_CONFIG
from src.tools.server import SERVER_TOOLS_CONFIG
from src.tools.misc import MISC_TOOLS_CONFIG
from src.tools.presence import PRESENCE_TOOLS_CONFIG
from src.tools.wordlist import WORDLIST_TOOLS_CONFIG

# Global tool registry: tool_name -> (schema_dict, handler_callable)
_REGISTRY: dict[str, tuple[dict[str, Any], Callable]] = {}

ALL_CONFIGS = [
    CHANNEL_TOOLS_CONFIG,
    ROLE_TOOLS_CONFIG,
    MODERATION_TOOLS_CONFIG,
    MESSAGE_TOOLS_CONFIG,
    SERVER_TOOLS_CONFIG,
    MISC_TOOLS_CONFIG,
    PRESENCE_TOOLS_CONFIG,
    WORDLIST_TOOLS_CONFIG,
]

for config_group in ALL_CONFIGS:
    for schema, handler in config_group:
        tool_name = schema["function"]["name"]
        _REGISTRY[tool_name] = (schema, handler)

def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Return JSON schemas for all registered tools to send to the LLM."""
    return [schema for schema, _ in _REGISTRY.values()]

# Names of tools that manage channels/categories (create_channel also handles
# categories via channel_type="category", so no separate category config exists)
_CHANNEL_TOOL_NAMES = {schema["function"]["name"] for schema, _ in CHANNEL_TOOLS_CONFIG}

def get_tool_schemas_for_prompt(user_prompt: str) -> list[dict[str, Any]]:
    """
    Keyword-routes which tool schemas get sent to the LLM.
    If the user's message mentions "channel" (case-insensitive), only expose
    channel/category management tools — keeps the tool list small for the
    weaker fallback models instead of always sending all ~29 tools.
    """
    if "channel" in user_prompt.lower():
        return [schema for schema, _ in CHANNEL_TOOLS_CONFIG]
    return get_all_tool_schemas()

def get_tool_handler(tool_name: str) -> Callable | None:
    """Return the executable async function for the specified tool name."""
    entry = _REGISTRY.get(tool_name)
    return entry[1] if entry else None

def list_registered_tool_names() -> list[str]:
    """Return a list of all registered tool names."""
    return list(_REGISTRY.keys())