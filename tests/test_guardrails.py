import pytest
from unittest.mock import MagicMock
from src.guardrails import is_authorized, is_destructive_action
from src.config import config

def test_admin_authorized(mock_admin_member):
    assert is_authorized(mock_admin_member) is True

def test_regular_user_unauthorized(mock_regular_member):
    assert is_authorized(mock_regular_member) is False

def test_destructive_action_check():
    assert is_destructive_action("delete_channel") is True
    assert is_destructive_action("ban_member") is True
    assert is_destructive_action("kick_member") is True
    assert is_destructive_action("create_channel") is False
    assert is_destructive_action("list_roles") is False

def test_role_whitelist_authorization(mock_regular_member):
    # Set allowed roles to role ID 777
    config.allowed_role_ids = [777]
    role = MagicMock()
    role.id = 777
    mock_regular_member.roles = [role]
    assert is_authorized(mock_regular_member) is True
    # Reset
    config.allowed_role_ids = []
