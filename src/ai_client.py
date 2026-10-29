"""
AI Client Module
================
This dedicated file handles all interactions with the LLM, with an automatic
fallback chain so a single provider hiccup doesn't take the bot down:

  1. primary_cloudflare -> config.cloudflare_ai_model (default
                           @cf/google/gemma-4-26b-a4b-it) via Cloudflare Workers AI's
                           OpenAI-compatible endpoint
  2. gemma_a6b          -> config.ai_model_a6b (default gemma-4-26b-a4b-it) via
                           Gemini's OpenAI-compatible endpoint
  3. gemma_31b          -> config.ai_model (default gemma-4-31b-it) via Gemini's
                           OpenAI-compatible endpoint
  4. backup_openrouter  -> config.openrouter_ai_model (default openrouter/free)
                           via OpenRouter's OpenAI-compatible endpoint
  5. backup_groq        -> config.groq_ai_model (default openai/gpt-oss-120b)
                           via Groq's OpenAI-compatible endpoint. Kept last since
                           this account has less API credit on Groq.

Admins can override the chain at runtime via the /ai-set-provider and
/ai-set-model slash commands (see main.py) — no restart needed. Runtime
state lives in `runtime_state` below and /ai-reset puts it back to default.

You can modify prompts, model parameters, or swap API endpoints directly in this file
without touching any Discord or Tool logic!
"""

import asyncio
import time
from collections import deque
from typing import Any
from openai import AsyncOpenAI
import structlog
from src.config import config

logger = structlog.get_logger("ai_client")

def estimate_payload_tokens(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> int:
    """
    Fast, conservative token estimation (~3.5 chars per token)
    covering messages history, system prompts, and tool JSON schemas.
    """
    total_chars = 0
    for m in messages:
        content = m.get("content") or ""
        total_chars += len(str(content))
        tool_calls = m.get("tool_calls")
        if tool_calls:
            total_chars += len(str(tool_calls))
    if tools:
        import json
        total_chars += len(json.dumps(tools))

    # ~3.5 chars per token + reserve 500 tokens for output/safety
    return int(total_chars / 3.5) + 500

class AsyncRateLimiter:
    """
    Sliding-window rate limiter ensuring the Gemini API never exceeds
    EITHER the configured requests per minute (RPM) OR tokens per minute (TPM).
    """
    def __init__(self, max_requests: int = 20, max_tokens: int = 14000, time_window: float = 60.0):
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.time_window = time_window
        # Deque of (timestamp, token_count)
        self.history: deque[tuple[float, int]] = deque()
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 2000):
        """Wait until both a request slot and sufficient token budget are available."""
        async with self.lock:
            while True:
                now = time.monotonic()
                # Discard entries older than the sliding window
                while self.history and now - self.history[0][0] >= self.time_window:
                    self.history.popleft()

                current_requests = len(self.history)
                current_tokens = sum(t[1] for t in self.history)

                need_to_wait = False
                wait_time = 0.0

                # Check RPM limit
                if current_requests >= self.max_requests:
                    need_to_wait = True
                    wait_time = max(wait_time, self.time_window - (now - self.history[0][0]))

                # Check TPM limit
                if current_tokens + estimated_tokens > self.max_tokens:
                    need_to_wait = True
                    # Find how long until enough tokens fall out of the sliding window
                    accumulated = 0
                    for ts, tok in self.history:
                        accumulated += tok
                        if (current_tokens - accumulated) + estimated_tokens <= self.max_tokens:
                            wait_time = max(wait_time, self.time_window - (now - ts))
                            break
                    if wait_time <= 0:
                        wait_time = self.time_window - (now - self.history[0][0])

                if not need_to_wait:
                    self.history.append((now, estimated_tokens))
                    break

                # Sleep and check again
                wait_time = min(max(wait_time + 0.1, 0.5), self.time_window)
                logger.warning(
                    "gemini_rate_limit_throttle",
                    current_tokens=current_tokens,
                    incoming_tokens=estimated_tokens,
                    max_tokens=self.max_tokens,
                    current_rpm=current_requests,
                    waiting_seconds=round(wait_time, 2)
                )
                await asyncio.sleep(wait_time)

# Global rate limiter instance (20 RPM, 14,000 TPM to stay comfortably under 16K)
rate_limiter = AsyncRateLimiter(
    max_requests=config.max_requests_per_minute,
    max_tokens=config.max_tokens_per_minute,
    time_window=60.0
)

# Default fallback order (labels must match _PROVIDER_DEFAULTS keys below)
DEFAULT_CHAIN_ORDER = ["primary_cloudflare", "gemma_a6b", "gemma_31b", "backup_openrouter", "backup_groq"]

# Human-friendly display names, used in /ai-set-provider, /ai-set-model choices, and logs
PROVIDER_DISPLAY_NAMES = {
    "primary_cloudflare": "Cloudflare",
    "gemma_a6b": "Gemma 4 A6B",
    "gemma_31b": "Gemma 4 31B",
    "backup_openrouter": "OpenRouter",
    "backup_groq": "Groq",
}

class _RuntimeState:
    """
    Holds admin-configurable overrides for the fallback chain. Nothing here
    touches config.py / the .env file — it's in-memory only and resets to
    the defaults above on bot restart or via /ai-reset.
    """
    def __init__(self):
        self.primary_override: str | None = None       # provider label to try first
        self.model_overrides: dict[str, str] = {}       # label -> model string override

    def reset(self):
        self.primary_override = None
        self.model_overrides.clear()

    def order(self) -> list[str]:
        """Chain order, with the override (if any) moved to the front."""
        if self.primary_override and self.primary_override in DEFAULT_CHAIN_ORDER:
            rest = [p for p in DEFAULT_CHAIN_ORDER if p != self.primary_override]
            return [self.primary_override] + rest
        return list(DEFAULT_CHAIN_ORDER)

    def model_for(self, label: str, default_model: str) -> str:
        return self.model_overrides.get(label, default_model)

runtime_state = _RuntimeState()

# System prompt giving explicit role instructions to Gemma 4 31B
SYSTEM_PROMPT = """You are an expert AI Discord Server Administrator with full administrative access.
Your role is to understand user requests and autonomously manage the Discord server using the provided tools.

TONE & PERSONALITY GUIDELINES:
- Address the user as twin/Homie/bud/brody.
- Be casual and chill like you're texting a friend who's into tech.
- No corporate speak, no excessive bullet points, no "certainly!" or "great question!" type openers.
- Match my energy — if I'm informal, be informal.
- Swear occasionally if it fits, more swearing is extremely encouraged and appreciated.
- Keep responses concise unless the topic actually needs depth.
- Just talk like a normal person.
- Never use the word "lol", use "lmao" instead. Don't use lmao on every sentence use it only when it's funny

CRITICAL INSTRUCTIONS:
1. When asked to perform administrative tasks (e.g. creating/modifying/deleting channels, managing roles, moderating users, changing/resetting user nicknames, purging messages), call the appropriate tool with the exact parameters.
2. If multiple actions are requested, you can call multiple tools or call them sequentially.
3. If an action is missing required details (e.g. asking to timeout someone without specifying duration or user), ask for clarification or use sensible safe defaults.
4. Channel permissions: To make a channel read-only for @everyone, set 'send_messages' to false for the role '@everyone'.
5. Once tool calls have executed and returned results, confirm what was accomplished in your chill, casual voice.
6. Never make assumptions about IDs; you can look up channels/roles/members by name or mention.
"""

def get_openai_client() -> AsyncOpenAI:
    """Instantiate and return the asynchronous OpenAI-compatible client (Gemini)."""
    return AsyncOpenAI(
        api_key=config.gemini_api_key or "placeholder_key",
        base_url=config.ai_base_url,
    )

def get_cloudflare_client() -> AsyncOpenAI:
    """
    Instantiate the OpenAI-compatible client pointed at Cloudflare Workers AI.
    Docs: https://developers.cloudflare.com/ai-gateway/usage/rest-api/#ai-v1-chat-completions--openai-compatible
    Base URL shape: https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1
    """
    return AsyncOpenAI(
        api_key=config.cloudflare_api_token or "placeholder_key",
        base_url=config.cloudflare_base_url,
    )

def get_openrouter_client() -> AsyncOpenAI:
    """Instantiate the OpenAI-compatible client pointed at OpenRouter."""
    return AsyncOpenAI(
        api_key=config.openrouter_api_key or "placeholder_key",
        base_url=config.openrouter_base_url,
    )

def get_groq_client() -> AsyncOpenAI:
    """Instantiate the OpenAI-compatible client pointed at Groq."""
    return AsyncOpenAI(
        api_key=config.groq_api_key or "placeholder_key",
        base_url=config.groq_base_url,
    )

# Default (label -> (default_model, client_factory)). Order here doesn't matter —
# actual try-order comes from runtime_state.order(), which defaults to
# DEFAULT_CHAIN_ORDER but can be reshuffled via /ai-set-provider.
_PROVIDER_DEFAULTS: dict[str, tuple[str, Any]] = {
    "primary_cloudflare": (config.cloudflare_ai_model, get_cloudflare_client),
    "gemma_a6b": (config.ai_model_a6b, get_openai_client),
    "gemma_31b": (config.ai_model, get_openai_client),
    "backup_openrouter": (config.openrouter_ai_model, get_openrouter_client),
    "backup_groq": (config.groq_ai_model, get_groq_client),
}

def _build_fallback_chain() -> list[tuple[str, str, Any]]:
    """
    Ordered fallback chain: (label, model, client_factory).
    Default order: Cloudflare -> Gemma 4 A6B -> Gemma 4 31B -> OpenRouter -> Groq.
    Respects any admin-set /ai-set-provider / /ai-set-model overrides.
    """
    chain = []
    for label in runtime_state.order():
        default_model, client_factory = _PROVIDER_DEFAULTS[label]
        model = runtime_state.model_for(label, default_model)
        chain.append((label, model, client_factory))
    return chain

async def request_ai_decision(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
    """
    Send messages and available tool definitions to the LLM.
    Tries, in order: Cloudflare Workers AI, then Google/Gemini, then OpenRouter,
    then Groq as a last resort (kept last due to limited API credit there).
    Guaranteed to never exceed the configured RPM/TPM on the Google/Gemini leg
    via the internal rate limiter (the other providers aren't throttled by it,
    since they're separate providers/quotas).
    """
    # Ensure system prompt is at the start
    full_messages = []
    has_system = any(m.get("role") == "system" for m in messages)
    if not has_system:
        full_messages.append({"role": "system", "content": SYSTEM_PROMPT})
    full_messages.extend(messages)

    base_kwargs: dict[str, Any] = {
        "messages": full_messages,
        "temperature": config.ai_temperature,
    }
    if tools:
        base_kwargs["tools"] = tools
        base_kwargs["tool_choice"] = "auto"

    chain = _build_fallback_chain()
    last_error: Exception | None = None

    for label, model, client_factory in chain:
        try:
            if label in ("gemma_a6b", "gemma_31b"):
                # Both of these hit the Gemini API, so both count against the
                # Gemini RPM/TPM budget
                estimated_tokens = estimate_payload_tokens(messages, tools)
                await rate_limiter.acquire(estimated_tokens=estimated_tokens)

            client = client_factory()

            estimated_tokens = estimate_payload_tokens(messages, tools)
            logger.info(
                "llm_request_sent",
                backend=label,
                model=model,
                base_url=str(client.base_url),
                message_count=len(full_messages),
                tool_count=len(tools) if tools else 0,
                estimated_prompt_tokens=estimated_tokens,
            )

            # Use with_raw_response so we can log the actual HTTP status code
            # alongside the parsed completion.
            raw_response = await client.chat.completions.with_raw_response.create(
                model=model, **base_kwargs
            )
            status_code = raw_response.status_code
            response = raw_response.parse()

            usage = getattr(response, "usage", None)
            finish_reason = None
            if getattr(response, "choices", None):
                finish_reason = response.choices[0].finish_reason

            logger.info(
                "llm_response_received",
                backend=label,
                model=model,
                actual_model=getattr(response, "model", None),
                status_code=status_code,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                finish_reason=finish_reason,
            )

            if label != runtime_state.order()[0]:
                logger.warning("llm_fallback_used", used=label, model=model)

            return response
        except Exception as e:
            last_error = e
            status_code = getattr(e, "status_code", None)
            logger.error(
                "llm_backend_failed",
                backend=label,
                model=model,
                status_code=status_code,
                error=str(e),
            )
            continue

    # Every backend in the chain failed
    raise last_error

def current_chain_status() -> str:
    """Human-readable summary of the current fallback chain, for the admin commands."""
    lines = []
    for i, (label, model, _factory) in enumerate(_build_fallback_chain(), start=1):
        lines.append(f"{i}. {PROVIDER_DISPLAY_NAMES.get(label, label)} — `{model}`")
    return "\n".join(lines)