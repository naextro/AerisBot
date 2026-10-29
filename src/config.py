import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load local .env if available
load_dotenv()

@dataclass
class Config:
    # Discord credentials
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", ""))
    bot_prefix: str = field(default_factory=lambda: os.getenv("BOT_PREFIX", "!"))

    # Gemini OpenAI-compatible settings
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "gemma-4-31b-it"))
    ai_base_url: str = field(default_factory=lambda: os.getenv("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"))
    ai_temperature: float = field(default_factory=lambda: float(os.getenv("AI_TEMPERATURE", "0.2")))
    max_requests_per_minute: int = field(default_factory=lambda: int(os.getenv("MAX_REQUESTS_PER_MINUTE", "20")))
    max_tokens_per_minute: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS_PER_MINUTE", "14000")))

    # Backup model #1: same Gemini API/key, different (smaller) model
    ai_model_backup: str = field(default_factory=lambda: os.getenv("AI_MODEL_BACKUP", "gemma-4-26b-a4b-it"))

    # Backup tier: Gemma 4 A6B (A4B) served via Google's Gemini endpoint —
    # same family as the Cloudflare-hosted one, different host, sits between
    # Cloudflare and the 31B tier in the fallback chain.
    ai_model_a6b: str = field(default_factory=lambda: os.getenv("AI_MODEL_A6B", "gemma-4-26b-a4b-it"))

    # Backup model #2: Cloudflare Workers AI, OpenAI-compatible endpoint
    cloudflare_account_id: str = field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
    cloudflare_api_token: str = field(default_factory=lambda: os.getenv("CLOUDFLARE_API_TOKEN", ""))
    cloudflare_ai_model: str = field(default_factory=lambda: os.getenv("CLOUDFLARE_AI_MODEL", "@cf/google/gemma-4-26b-a4b-it"))
    cloudflare_base_url: str = field(default_factory=lambda: os.getenv(
        "CLOUDFLARE_BASE_URL",
        f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID', '')}/ai/v1"
    ))

    # Backup model #3: OpenRouter, OpenAI-compatible endpoint
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_ai_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_AI_MODEL", "openrouter/free"))
    openrouter_base_url: str = field(default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))

    # Backup model #4 (last resort - low credit): Groq, OpenAI-compatible endpoint
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_ai_model: str = field(default_factory=lambda: os.getenv("GROQ_AI_MODEL", "openai/gpt-oss-120b"))
    groq_base_url: str = field(default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))

    # Permissions and safety
    allowed_role_ids: list[int] = field(default_factory=list)
    log_channel_id: int | None = None
    auto_nickname_channel_id: int | None = None
    context_window_size: int = 10
    require_confirmation_for_destructive: bool = True

    # High-impact dangerous actions that trigger interactive confirmation
    dangerous_actions: set[str] = field(default_factory=lambda: {
        "delete_channel",
        "delete_role",
        "ban_member",
        "kick_member",
        "delete_messages_bulk",
        "prune_members"
    })

    def __post_init__(self):
        raw_roles = os.getenv("ALLOWED_ROLE_IDS", "").strip()
        if raw_roles:
            self.allowed_role_ids = [int(r.strip()) for r in raw_roles.split(",") if r.strip().isdigit()]

        raw_log = os.getenv("LOG_CHANNEL_ID", "").strip()
        if raw_log and raw_log.isdigit():
            self.log_channel_id = int(raw_log)

        raw_nick_ch = os.getenv("AUTO_NICKNAME_CHANNEL_ID", "").strip()
        if raw_nick_ch and raw_nick_ch.isdigit():
            self.auto_nickname_channel_id = int(raw_nick_ch)

        raw_ctx = os.getenv("CONTEXT_WINDOW_SIZE", "10").strip()
        if raw_ctx.isdigit():
            self.context_window_size = int(raw_ctx)

        req_confirm = os.getenv("REQUIRE_CONFIRMATION_FOR_DESTRUCTIVE", "true").strip().lower()
        self.require_confirmation_for_destructive = req_confirm in ("true", "1", "yes")

config = Config()