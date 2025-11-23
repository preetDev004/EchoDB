"""Configuration constants for EchoDB application."""

# Database query limits
MAX_ROWS = 100

# Chat limits
MAX_MESSAGES = 10

# Provider and model configurations
PROVIDER_MODELS = {
    "OpenAI": ["gpt-5.1", "gpt-5-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini"],
    "Google": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
    "Anthropic": ["claude-4.5-sonnet", "claude-3.7-sonnet", "claude-3.5-sonnet", "claude-haiku-4.5"],
    "X-AI": ["grok-4.1-fast", "grok-4-fast", "grok-3", "grok-3-mini"]
}
