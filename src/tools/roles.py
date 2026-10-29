"""
Role Management Tools
=====================
Handles creation, deletion, editing, assigning, removing, and listing roles.
"""

from typing import Any
import discord

async def create_role(guild: discord.Guild, **kwargs: Any) -> str:
    """Creates a new role with customizable color, permissions, and settings."""
    name = kwargs.get("name")
    if not name:
        return "Error: Role 'name' is required."

    color_val = discord.Color.default()
    color_input = kwargs.get("color")
    if color_input:
        if isinstance(color_input, str) and color_input.startswith("#"):
            try:
                color_val = discord.Color(int(color_input.lstrip("#"), 16))
            except ValueError:
                pass
        elif hasattr(discord.Color, str(color_input).lower()):
            color_val = getattr(discord.Color, str(color_input).lower())()

    hoist = bool(kwargs.get("hoist", False))
    mentionable = bool(kwargs.get("mentionable", False))

    perms = discord.Permissions.none()
    requested_perms = kwargs.get("permissions", [])
    if isinstance(requested_perms, list):
        for p in requested_perms:
            p_clean = p.strip().lower().replace(" ", "_")
            if hasattr(perms, p_clean):
                setattr(perms, p_clean, True)

    try:
        new_role = await guild.create_role(
            name=name,
            color=color_val,
            permissions=perms,
            hoist=hoist,
            mentionable=mentionable,
            reason=kwargs.get("reason", "Created via AI Admin")
        )
        return f"Successfully created role '{new_role.name}' (ID: {new_role.id}) with color {color_val}."
    except discord.Forbidden:
        return "Error: Missing 'Manage Roles' permission or role hierarchy is too low."
    except Exception as e:
        return f"Error creating role: {str(e)}"

async def delete_role(guild: discord.Guild, **kwargs: Any) -> str:
    """Deletes a role by name or ID."""
    role_identifier = str(kwargs.get("role_identifier", "")).strip()
    target_role = None
    if role_identifier.isdigit():
        target_role = guild.get_role(int(role_identifier))
    if not target_role:
        target_role = discord.utils.find(lambda r: r.name.lower() == role_identifier.lower(), guild.roles)

    if not target_role:
        return f"Error: Role '{role_identifier}' not found."

    try:
        role_name = target_role.name
        await target_role.delete(reason=kwargs.get("reason", "Deleted via AI Admin"))
        return f"Successfully deleted role '{role_name}'."
    except discord.Forbidden:
        return "Error: Role cannot be deleted. The bot's role is likely lower than this role in the hierarchy."
    except Exception as e:
        return f"Error deleting role: {str(e)}"

async def assign_role(guild: discord.Guild, **kwargs: Any) -> str:
    """Assigns an existing role to a member."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    role_id = str(kwargs.get("role_identifier", "")).strip()

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned_m = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned_m or (m.nick and m.nick.lower() == cleaned_m), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    role = None
    if role_id.isdigit():
        role = guild.get_role(int(role_id))
    if not role:
        role = discord.utils.find(lambda r: r.name.lower() == role_id.lstrip("@").lower(), guild.roles)

    if not role:
        return f"Error: Role '{role_id}' not found."

    try:
        await member.add_roles(role, reason=kwargs.get("reason", "Assigned via AI Admin"))
        return f"Assigned role '{role.name}' to {member.display_name}."
    except discord.Forbidden:
        return "Error: Role hierarchy prevents assigning this role."
    except Exception as e:
        return f"Error assigning role: {str(e)}"

async def remove_role(guild: discord.Guild, **kwargs: Any) -> str:
    """Removes a role from a member."""
    member_id = str(kwargs.get("member_identifier", "")).strip()
    role_id = str(kwargs.get("role_identifier", "")).strip()

    member = None
    if member_id.isdigit():
        member = guild.get_member(int(member_id))
    if not member:
        cleaned_m = member_id.lstrip("@").lower()
        member = discord.utils.find(lambda m: m.name.lower() == cleaned_m or (m.nick and m.nick.lower() == cleaned_m), guild.members)

    if not member:
        return f"Error: Member '{member_id}' not found."

    role = None
    if role_id.isdigit():
        role = guild.get_role(int(role_id))
    if not role:
        role = discord.utils.find(lambda r: r.name.lower() == role_id.lstrip("@").lower(), guild.roles)

    if not role:
        return f"Error: Role '{role_id}' not found."

    try:
        await member.remove_roles(role, reason=kwargs.get("reason", "Removed via AI Admin"))
        return f"Removed role '{role.name}' from {member.display_name}."
    except discord.Forbidden:
        return "Error: Role hierarchy prevents removing this role."
    except Exception as e:
        return f"Error removing role: {str(e)}"

async def list_roles(guild: discord.Guild, **kwargs: Any) -> str:
    """Lists all roles in the server along with member counts."""
    sorted_roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
    lines = [f"Roles in {guild.name} (from highest to lowest):"]
    for r in sorted_roles:
        lines.append(f"- {r.name} (id: {r.id}, members: {len(r.members)}, color: {r.color})")
    return "\n".join(lines)

ROLE_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "create_role",
                "description": "Create a new role with specified name, color, and permissions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the role"},
                        "color": {"type": "string", "description": "Color name (e.g. blue, red, gold) or hex code (e.g. #FF5733)"},
                        "permissions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of permission names, e.g. ['manage_messages', 'kick_members', 'ban_members', 'view_audit_log']"
                        },
                        "hoist": {"type": "boolean", "description": "Display role separately in member list"},
                        "mentionable": {"type": "boolean", "description": "Allow anyone to mention this role"}
                    },
                    "required": ["name"]
                }
            }
        },
        create_role
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "delete_role",
                "description": "Delete an existing role by name or ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role_identifier": {"type": "string", "description": "Role name or ID to delete"},
                        "reason": {"type": "string", "description": "Reason for deletion"}
                    },
                    "required": ["role_identifier"]
                }
            }
        },
        delete_role
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "assign_role",
                "description": "Assign a role to a server member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Member username, mention, or ID"},
                        "role_identifier": {"type": "string", "description": "Role name or ID"}
                    },
                    "required": ["member_identifier", "role_identifier"]
                }
            }
        },
        assign_role
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "remove_role",
                "description": "Remove a role from a server member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_identifier": {"type": "string", "description": "Member username, mention, or ID"},
                        "role_identifier": {"type": "string", "description": "Role name or ID"}
                    },
                    "required": ["member_identifier", "role_identifier"]
                }
            }
        },
        remove_role
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "list_roles",
                "description": "List all roles in the server ordered by hierarchy.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        list_roles
    )
]
