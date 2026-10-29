# Discord AI Server Admin Bot

An autonomous Discord AI server administrator powered by **Gemma 4 31B** (via Google Gemini's OpenAI-compatible endpoint) and **discord.py 2.x**.

Users with administrator privileges can converse in natural language (via `/admin <prompt>` or `@bot <prompt>`), and the bot dynamically selects and executes server admin tools autonomously.

---

## 🚀 Key Features

- **Isolated AI Client (`src/ai_client.py`):** The LLM logic is cleanly decoupled. You can change prompts, system parameters, or switch models in this single file.
- **Admin Capabilities:**
  - **Channels:** Create (text, voice, category, stage, forum), delete, rename, change slowmode/NSFW, configure permission overwrites (e.g. make read-only, hide from `@everyone`).
  - **Roles:** Create with specific permissions & hex/color presets, delete, assign, remove, and list roles.
  - **Moderation:** Timeout (mute) users with flexible time durations (`10m`, `2h`, `1d`), remove timeouts, kick, ban (with message deletion days), and unban.
  - **Messages:** Purge/bulk delete messages, pin, and send announcements.
  - **Server & Misc:** Server stats, rename server, member search, create instant invites.
- **Safety & Guardrails:**
  - Strict authorization checks (`Administrator` permission or whitelist role IDs).
  - High-impact destructive action confirmation buttons (Discord UI View).
  - Comprehensive audit logging via console and dedicated Discord logging channel.

---

## 📁 Project Structure

```
discord-ai-bot/
├── .env.example           # Environment variables template
├── pyproject.toml         # UV project configuration & dependencies
├── README.md
├── src/
│   ├── config.py          # Central configuration
│   ├── ai_client.py       # [EDIT THIS] Gemini / Gemma 4 31B API calling file
│   ├── guardrails.py      # Authorization & interactive confirmation views
│   ├── logger.py          # Structlog & Discord audit channel logger
│   ├── handlers.py        # Agentic loop (Message -> AI -> Tool -> AI -> Reply)
│   ├── main.py            # Discord bot entrypoint
│   └── tools/             # Tool implementations & JSON schemas
│       ├── __init__.py    # Unified registry
│       ├── channels.py    # Channel management tools
│       ├── roles.py       # Role management tools
│       ├── moderation.py  # Moderation tools (kick/ban/timeout)
│       ├── messages.py    # Purge & message management tools
│       ├── server.py      # Server stats & rename tools
│       └── misc.py        # Invites & member tools
└── tests/                 # Automated Pytest suite
    ├── conftest.py
    ├── test_guardrails.py
    ├── test_tools.py
    └── test_agentic_loop.py
```

---

## ⚙️ Quick Start

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_google_gemini_api_key_here

# Pre-configured to Gemma 4 31B:
AI_MODEL=gemma-4-31b-it
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

### 2. Run the Bot
Using `uv`:
```bash
uv run python -m src.main
```

### 3. Sync Slash Commands
Inside Discord, run `!sync` as the bot owner to register the `/admin` slash command.

---

## 🧪 Testing

Run the automated test suite anytime:
```bash
uv run pytest tests/ -v
```
