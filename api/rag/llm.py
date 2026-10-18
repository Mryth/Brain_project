"""Pluggable LLM client. Speaks the OpenAI chat-completions API, so it works with:
  - a LOCAL Ollama server (default: LLM_BASE_URL=http://ollama:11434/v1)
  - vLLM / LM Studio / any OpenAI-compatible server
  - OpenAI / Groq (set LLM_BASE_URL + LLM_API_KEY + LLM_MODEL)
Swapping providers is pure configuration — no code change."""
import logging
from functools import lru_cache
import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


def chat(messages, temperature=None, max_tokens=1024) -> str:
    """messages: [{'role':'system'|'user'|'assistant','content':str}] -> str."""
    resp = _client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=config.LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def complete(system: str, user: str, **kw) -> str:
    return chat([{"role": "system", "content": system},
                 {"role": "user", "content": user}], **kw)


def available() -> bool:
    try:
        _client().models.list()
        return True
    except Exception as e:
        logger.warning(f"LLM backend not reachable: {e}")
        return False
