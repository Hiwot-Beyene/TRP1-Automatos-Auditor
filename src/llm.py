"""
LLM layer: Always uses Ollama with llama3.2:3b for all nodes.

All LLM instances (judicial, detective, forensic, vision) use Ollama llama3.2:3b.
Environment variables for provider selection are ignored - always uses Ollama.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel

from src.llm_errors import NoModelProvidedError

logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


def _provider(role: str | None) -> str:
    return "ollama"


def _build_openai(role: str, temperature: float) -> BaseChatModel | None:
    key = _env("OPENAI_API_KEY")
    if not key:
        if role == "default":
            raise ValueError(
            "OPENAI_API_KEY is not set. Set it in .env or use LLM_PROVIDER=openrouter (with OPENROUTER_API_KEY). Default is Ollama (llama3.2:3b)."
            )
        return None
    from langchain_openai import ChatOpenAI
    model = _env("OPENAI_MODEL") or "gpt-4o-mini"
    if role == "vision":
        model = _env("OPENAI_VISION_MODEL") or model
    return ChatOpenAI(model=model, temperature=temperature, api_key=key)


def _build_openrouter(role: str, temperature: float) -> BaseChatModel | None:
    key = _env("OPENROUTER_API_KEY")
    if not key:
        return None
    from langchain_openai import ChatOpenAI
    model = _env("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
    if role == "vision":
        model = _env("OPENROUTER_VISION_MODEL") or model
    base = _env("OPENROUTER_API_BASE") or "https://openrouter.ai/api/v1"
    return ChatOpenAI(model=model, temperature=temperature, api_key=key, base_url=base)


def _build_ollama(role: str, temperature: float) -> BaseChatModel | None:
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        return None
    model = "llama3.2:3b"
    base = _env("OLLAMA_BASE_URL") or "http://localhost:11434"
    logger.info(f"Building Ollama model: {model} for role: {role}")
    return ChatOllama(model=model, base_url=base, temperature=temperature)


def _build_groq(role: str, temperature: float) -> BaseChatModel | None:
    key = _env("GROQ_API_KEY")
    if not key:
        return None
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        return None
    model = _env("GROQ_MODEL") or "llama-3.3-70b-versatile"
    return ChatGroq(model=model, temperature=temperature, groq_api_key=key)


def _build_gemini(role: str, temperature: float) -> BaseChatModel | None:
    key = _env("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        return None
    model = _env("GOOGLE_MODEL") or "gemini-2.0-flash"
    if role in ("detective", "vision"):
        model = _env("GOOGLE_VISION_MODEL") or _env("GOOGLE_DETECTIVE_MODEL") or model
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=key)


def _build_anthropic(role: str, temperature: float) -> BaseChatModel | None:
    key = _env("ANTHROPIC_API_KEY")
    if not key:
        return None
    from langchain_anthropic import ChatAnthropic
    model = _env("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022"
    return ChatAnthropic(model=model, temperature=temperature, api_key=key)


def _build_openai_compatible(role: str, temperature: float) -> BaseChatModel | None:
    """Any OpenAI-compatible API (e.g. local vLLM, LiteLLM). Set OPENAI_BASE_URL + OPENAI_API_KEY + OPENAI_MODEL."""
    base = _env("OPENAI_BASE_URL")
    key = _env("OPENAI_API_KEY")
    if not base or not key:
        return None
    from langchain_openai import ChatOpenAI
    model = _env("OPENAI_MODEL") or "gpt-4o-mini"
    return ChatOpenAI(model=model, temperature=temperature, api_key=key, base_url=base)


_PROVIDER_BUILDERS: dict[str, Callable[[str, float], BaseChatModel | None]] = {
    "openai": _build_openai,
    "openrouter": _build_openrouter,
    "ollama": _build_ollama,
    "groq": _build_groq,
    "gemini": _build_gemini,
    "anthropic": _build_anthropic,
    "openai_compatible": _build_openai_compatible,
}

_llm_cache: dict[tuple[str | None, float], BaseChatModel | None] = {}


def clear_llm_cache():
    """Clear the LLM cache to force fresh model instances."""
    global _llm_cache
    _llm_cache.clear()


clear_llm_cache()


def _build_llm(provider_id: str, role: str, temperature: float) -> BaseChatModel | None:
    builder = _PROVIDER_BUILDERS.get(provider_id)
    if not builder:
        return None
    return builder(role, temperature)


def get_llm(role: str | None = None, temperature: float = 0.3, required: bool = True) -> BaseChatModel | None:
    """
    Return the chat model. Always uses Ollama with llama3.2:3b.
    role: None (default), "judicial", "detective", "forensic", "vision".
    If required=False, returns None when Ollama is unavailable.
    """
    cache_key = (role, temperature)
    
    if cache_key in _llm_cache:
        out = _llm_cache[cache_key]
        if out is not None:
            model_name = getattr(out, "model", None)
            if model_name != "llama3.2:3b":
                logger.warning(f"Clearing cache: cached model '{model_name}' != 'llama3.2:3b'")
                clear_llm_cache()
            else:
                return out
    
    out = _build_ollama(role or "default", temperature)
    if out is None and not required:
        return None
    if out is None:
        logger.warning("Ollama is not available. Make sure Ollama is running and llama3.2:3b is installed.")
        raise NoModelProvidedError()
    
    model_name = getattr(out, "model", None)
    if model_name and model_name != "llama3.2:3b":
        logger.error(f"Model name mismatch: expected 'llama3.2:3b', got '{model_name}'. Rebuilding...")
        out = _build_ollama(role or "default", temperature)
        model_name = getattr(out, "model", None)
        if model_name and model_name != "llama3.2:3b":
            raise ValueError(f"Failed to create Ollama model with 'llama3.2:3b'. Got '{model_name}' instead.")
    
    _llm_cache[cache_key] = out
    return out


def get_vision_provider() -> str:
    """Provider used for vision (image) tasks. Always returns 'ollama'."""
    return "ollama"


def get_judicial_llm() -> BaseChatModel | None:
    """Judges (Prosecutor, Defense, Tech Lead). Always uses Ollama llama3.2:3b."""
    return get_llm(role="judicial", temperature=0.3, required=False)


def get_judge_llm() -> Any:
    """Alias for get_judicial_llm(); Judges node expects this name."""
    return get_judicial_llm()


def get_vision_llm() -> BaseChatModel | None:
    """Vision-capable model for VisionInspector. Always uses Ollama llama3.2:3b."""
    return get_llm(role="vision", temperature=0.2, required=False)


def get_detective_llm() -> BaseChatModel | None:
    """Doc/vision detectives. Always uses Ollama llama3.2:3b."""
    return get_llm(role="detective", temperature=0.2, required=False)


def get_forensic_llm() -> BaseChatModel | None:
    """Repo investigator. Always uses Ollama llama3.2:3b."""
    return get_llm(role="forensic", temperature=0.2, required=False)


def get_doc_llm() -> Any:
    """DocAnalyst / theoretical depth. Same as detective LLM."""
    return get_detective_llm() or get_llm(temperature=0.2, required=False)


def get_repo_investigator_llm() -> Any:
    """RepoInvestigator. None if AUDITOR_FAST_REPO=1 (skip LLM summary)."""
    if _env("AUDITOR_FAST_REPO"):
        return None
    return get_forensic_llm() or get_llm(temperature=0.2, required=False)
