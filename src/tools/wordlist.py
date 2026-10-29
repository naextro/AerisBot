"""
Word List Management Tools
===========================
Lets the AI admin add/remove entries from badwords.txt at runtime and
hot-reloads the in-memory BadWordFilter so changes apply immediately
(no bot restart needed).
"""

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BADWORDS_PATH = PROJECT_ROOT / "badwords.txt"


def _read_words() -> list[str]:
    if not BADWORDS_PATH.exists():
        return []
    with open(BADWORDS_PATH, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _write_words(words: list[str]) -> None:
    with open(BADWORDS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(words) + "\n")


def _reload_filter(bot: Any) -> None:
    """Hot-reload the shared BadWordFilter instance if the bot exposes one."""
    bad_filter = getattr(bot, "bad_filter", None)
    if bad_filter is not None:
        bad_filter.reload()


async def add_word(bot: Any = None, **kwargs: Any) -> str:
    """Adds a single word/phrase to the bad word list."""
    word = str(kwargs.get("word", "")).strip().lower()
    if not word:
        return "Error: No word provided."

    words = _read_words()
    if word in [w.lower() for w in words]:
        return f"'{word}' is already in the list."

    words.append(word)
    _write_words(words)
    _reload_filter(bot)
    return f"Successfully added '{word}' to the bad word list."


async def add_words(bot: Any = None, **kwargs: Any) -> str:
    """Adds multiple comma-separated words/phrases to the bad word list."""
    raw = str(kwargs.get("words", ""))
    new_words = [w.strip().lower() for w in raw.split(",") if w.strip()]
    if not new_words:
        return "Error: No words provided."

    words = _read_words()
    existing_lower = {w.lower() for w in words}

    added = []
    skipped = []
    for w in new_words:
        if w in existing_lower:
            skipped.append(w)
            continue
        words.append(w)
        existing_lower.add(w)
        added.append(w)

    _write_words(words)
    _reload_filter(bot)

    msg = f"Added {len(added)} word(s): {', '.join(added) if added else 'none'}."
    if skipped:
        msg += f" Skipped {len(skipped)} already present: {', '.join(skipped)}."
    return msg


async def delete_word(bot: Any = None, **kwargs: Any) -> str:
    """Removes a single word/phrase from the bad word list."""
    word = str(kwargs.get("word", "")).strip().lower()
    if not word:
        return "Error: No word provided."

    words = _read_words()
    filtered = [w for w in words if w.lower() != word]

    if len(filtered) == len(words):
        return f"'{word}' was not found in the list."

    _write_words(filtered)
    _reload_filter(bot)
    return f"Successfully removed '{word}' from the bad word list."


async def delete_words(bot: Any = None, **kwargs: Any) -> str:
    """Removes multiple comma-separated words/phrases from the bad word list."""
    raw = str(kwargs.get("words", ""))
    to_remove = {w.strip().lower() for w in raw.split(",") if w.strip()}
    if not to_remove:
        return "Error: No words provided."

    words = _read_words()
    filtered = [w for w in words if w.lower() not in to_remove]
    removed_count = len(words) - len(filtered)
    not_found = to_remove - {w.lower() for w in words}

    _write_words(filtered)
    _reload_filter(bot)

    msg = f"Removed {removed_count} word(s)."
    if not_found:
        msg += f" Not found: {', '.join(not_found)}."
    return msg


async def list_words(bot: Any = None, **kwargs: Any) -> str:
    """Lists all words/phrases currently in the bad word filter."""
    words = _read_words()
    if not words:
        return "The bad word list is currently empty."
    return f"Bad word list ({len(words)} entries):\n" + ", ".join(words)


WORDLIST_TOOLS_CONFIG = [
    (
        {
            "type": "function",
            "function": {
                "name": "list_words",
                "description": "List all words/phrases currently in the bad word filter list.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        list_words
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "add_word",
                "description": "Add a single word or phrase to the bad word filter list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string", "description": "The word or phrase to add"}
                    },
                    "required": ["word"]
                }
            }
        },
        add_word
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "add_words",
                "description": "Add multiple words or phrases to the bad word filter list at once, separated by commas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "words": {"type": "string", "description": "Comma-separated list of words/phrases to add, e.g. 'word1, word2, word3'"}
                    },
                    "required": ["words"]
                }
            }
        },
        add_words
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "delete_word",
                "description": "Remove a single word or phrase from the bad word filter list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string", "description": "The word or phrase to remove"}
                    },
                    "required": ["word"]
                }
            }
        },
        delete_word
    ),
    (
        {
            "type": "function",
            "function": {
                "name": "delete_words",
                "description": "Remove multiple words or phrases from the bad word filter list at once, separated by commas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "words": {"type": "string", "description": "Comma-separated list of words/phrases to remove, e.g. 'word1, word2, word3'"}
                    },
                    "required": ["words"]
                }
            }
        },
        delete_words
    )
]
