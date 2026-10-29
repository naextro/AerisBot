"""
Bad Word Filter
===============
O(1) hashset-based filter. Loads badwords.txt once at startup.
Handles leet speak normalization. Zero regex overhead per message.
"""

import re
import asyncio
from datetime import timedelta
from pathlib import Path
import structlog
import discord

logger = structlog.get_logger("badword_filter")

# Leet speak normalization — applied before lookup
_LEET: dict[int, str] = str.maketrans({
    '@': 'a', '4': 'a',
    '3': 'e',
    '1': 'i', '!': 'i',
    '0': 'o',
    '5': 's', '$': 's',
    '7': 't', '+': 't',
    '9': 'g',
    '|': 'l',
    '2': 'z',
})

# Regex to split message into tokens (reused, compiled once)
_SPLIT = re.compile(r'[\W_]+')

def _load(path: Path) -> tuple[frozenset[str], list[str]]:
    """
    Loads badwords.txt into:
      - single_words: frozenset for O(1) per-token lookup
      - phrases: list of multi-word entries for substring search
    """
    single: set[str] = set()
    phrases: list[str] = []

    if not path.exists():
        logger.warning("badwords_file_missing", path=str(path))
        return frozenset(), []

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            word = raw.strip().lower()
            if not word or word.startswith("#"):
                continue
            # normalize leet in the list itself too
            word = word.translate(_LEET)
            if " " in word:
                phrases.append(word)
            else:
                single.add(word)

    logger.info("badwords_loaded", single=len(single), phrases=len(phrases))
    return frozenset(single), phrases


def _normalize(text: str) -> str:
    return text.lower().translate(_LEET)


class BadWordFilter:
    def __init__(self, badwords_path: Path):
        self._path = badwords_path
        self._single, self._phrases = _load(badwords_path)

    def reload(self):
        """Hot-reload the word list without restarting."""
        self._single, self._phrases = _load(self._path)

    def contains(self, content: str) -> bool:
        """
        Returns True if content contains a bad word.
        Step 1: normalize + tokenize → O(n) where n = token count
        Step 2: each token lookup → O(1) via frozenset
        Step 3: phrase check only if phrases list is non-empty
        """
        normalized = _normalize(content)

        # Token check — O(n) total, O(1) per token
        for token in _SPLIT.split(normalized):
            if token and token in self._single:
                return True

        # Phrase check — only runs if you have multi-word entries
        for phrase in self._phrases:
            if phrase in normalized:
                return True

        return False


async def handle_bad_message(message: discord.Message) -> None:
    """
    Delete the message. No timeout/mute is applied to the sender.
    """
    member = message.author
    if not isinstance(member, discord.Member):
        return

    try:
        await message.delete()
    except discord.NotFound:
        pass  # already gone
    except discord.Forbidden:
        logger.warning("badword_delete_forbidden", channel_id=message.channel.id)
