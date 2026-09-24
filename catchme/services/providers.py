"""
Supported LLM providers and their default API URLs.

This is a simple lookup table — when ``llm.api_url`` is omitted in
``config.json``, the default URL for the chosen provider is used.
"""

from __future__ import annotations

# (provider_name, display_name, default_api_url, get_key_url)
PROVIDERS: tuple[tuple[str, str, str, str], ...] = (
    # Gateways (route any model from any vendor)
    ("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "https://openrouter.ai/keys"),
    ("requesty", "Requesty", "https://router.requesty.ai/v1", "https://app.requesty.ai/api-keys"),
    ("aihubmix", "AiHubMix", "https://aihubmix.com/v1", "https://aihubmix.com"),
    ("siliconflow", "SiliconFlow", "https://api.siliconflow.cn/v1", "https://cloud.siliconflow.cn"),
    # Cloud providers
    ("openai", "OpenAI", "https://api.openai.com/v1", "https://platform.openai.com/api-keys"),
    ("anthropic", "Anthropic", "https://api.anthropic.com/v1", "https://console.anthropic.com"),
    (
        "deepseek",
        "DeepSeek",
        "https://api.deepseek.com/v1",
        "https://platform.deepseek.com/api_keys",
    ),
    (
        "gemini",
        "Gemini",
        "https://generativelanguage.googleapis.com/v1beta",
        "https://aistudio.google.com/apikey",
    ),
    ("groq", "Groq", "https://api.groq.com/openai/v1", "https://console.groq.com/keys"),
    ("mistral", "Mistral", "https://api.mistral.ai/v1", "https://console.mistral.ai"),
    ("moonshot", "Moonshot / Kimi", "https://api.moonshot.ai/v1", "https://platform.moonshot.cn"),
    ("minimax", "MiniMax", "https://api.minimax.io/v1", "https://platform.minimaxi.com"),
    ("zhipu", "Zhipu AI (GLM)", "https://open.bigmodel.cn/api/paas/v4", "https://open.bigmodel.cn"),
    (
        "dashscope",
        "DashScope (Qwen)",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "https://dashscope.console.aliyun.com",
    ),
    # VolcEngine / BytePlus
    (
        "volcengine",
        "VolcEngine",
        "https://ark.cn-beijing.volces.com/api/v3",
        "https://console.volcengine.com",
    ),
    (
        "volcengine_coding_plan",
        "VolcEngine Coding Plan",
        "https://ark.cn-beijing.volces.com/api/coding/v3",
        "https://console.volcengine.com",
    ),
    (
        "byteplus",
        "BytePlus",
        "https://ark.ap-southeast.bytepluses.com/api/v3",
        "https://console.byteplus.com",
    ),
    (
        "byteplus_coding_plan",
        "BytePlus Coding Plan",
        "https://ark.ap-southeast.bytepluses.com/api/coding/v3",
        "https://console.byteplus.com",
    ),
    # Local deployment
    ("ollama", "Ollama", "http://localhost:11434/v1", ""),
    ("vllm", "vLLM / Local", "http://localhost:8000/v1", ""),
    ("lmstudio", "LM Studio", "http://localhost:1234/v1", ""),
)


def get_default_api_url(provider: str) -> str | None:
    """Return the default API URL for a provider name, or None."""
    for name, _, url, _ in PROVIDERS:
        if name == provider:
            return url
    return None
