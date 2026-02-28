"""
Configurable LLM layer: provider and role selected from env.

Single default: LLM_PROVIDER=ollama (local llama3.2:3b); or openai | openrouter | groq | gemini.
Role overrides: JUDICIAL_PROVIDER, DETECTIVE_PROVIDER, FORENSIC_PROVIDER, VISION_PROVIDER.
Vision: use VISION_PROVIDER=gemini (or openai/ollama with vision model) for image-capable nodes.

Add a new provider by implementing a builder in _PROVIDER_BUILDERS and setting the env var.
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
    if role == "judicial":
        return (_env("JUDICIAL_PROVIDER") or _env("LLM_PROVIDER") or "ollama").lower()
    if role == "detective":
        return (_env("DETECTIVE_PROVIDER") or _env("VISION_PROVIDER") or _env("LLM_PROVIDER") or "ollama").lower()
    if role == "forensic":
        return (_env("FORENSIC_PROVIDER") or _env("LLM_PROVIDER") or "ollama").lower()
    if role == "vision":
        return (_env("VISION_PROVIDER") or _env("LLM_PROVIDER") or "ollama").lower()
    return (_env("LLM_PROVIDER") or "ollama").lower()


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


def _build_llm(provider_id: str, role: str, temperature: float) -> BaseChatModel | None:
    builder = _PROVIDER_BUILDERS.get(provider_id)
    if not builder:
        return None
    return builder(role, temperature)


def get_llm(role: str | None = None, temperature: float = 0.3, required: bool = True) -> BaseChatModel | None:
    """
    Return the chat model. Provider from LLM_PROVIDER (or role override).
    role: None (default), "judicial", "detective", "forensic", "vision".
    If required=False, returns None when no API key / provider is configured.
    """
    prov = _provider(role)
    cache_key = (role, temperature)
    
    if prov == "ollama":
        clear_llm_cache()
        if cache_key in _llm_cache:
            del _llm_cache[cache_key]
    
    if cache_key in _llm_cache:
        out = _llm_cache[cache_key]
        if out is not None:
            if prov == "ollama":
                model_name = getattr(out, "model", None)
                if model_name != "llama3.2:3b":
                    logger.warning(f"Clearing cache: cached model '{model_name}' != 'llama3.2:3b'")
                    clear_llm_cache()
                    if cache_key in _llm_cache:
                        del _llm_cache[cache_key]
                else:
                    return out
            else:
                return out
    
    out = _build_llm(prov, role or "default", temperature)
    if out is None and prov != "ollama":
        out = _build_ollama(role or "default", temperature)
    if out is None:
        out = _build_ollama(role or "default", temperature)
    if out is None and not required:
        return None
    if out is None:
        logger.warning("No LLM available for provider=%s; no model specified.", prov)
        raise NoModelProvidedError()
    
    if prov == "ollama":
        model_name = getattr(out, "model", None)
        if model_name and model_name != "llama3.2:3b":
            logger.warning(f"Model name mismatch: expected 'llama3.2:3b', got '{model_name}'. Rebuilding...")
            out = _build_ollama(role or "default", temperature)
    
    _llm_cache[cache_key] = out
    return out


def get_vision_provider() -> str:
    """Provider used for vision (image) tasks; influences message format (e.g. Gemini image block)."""
    return _provider("vision")


def get_judicial_llm() -> BaseChatModel | None:
    """Judges (Prosecutor, Defense, Tech Lead). Uses JUDICIAL_PROVIDER or LLM_PROVIDER."""
    return get_llm(role="judicial", temperature=0.3, required=False)


def get_judge_llm() -> Any:
    """Alias for get_judicial_llm(); Judges node expects this name."""
    return get_judicial_llm()


def get_vision_llm() -> BaseChatModel | None:
    """Vision-capable model for VisionInspector. Uses VISION_PROVIDER or LLM_PROVIDER."""
    return get_llm(role="vision", temperature=0.2, required=False)


def get_detective_llm() -> BaseChatModel | None:
    """Doc/vision detectives. Uses DETECTIVE_PROVIDER or VISION_PROVIDER or LLM_PROVIDER."""
    return get_llm(role="detective", temperature=0.2, required=False)


def get_forensic_llm() -> BaseChatModel | None:
    """Repo investigator. Uses FORENSIC_PROVIDER or LLM_PROVIDER."""
    return get_llm(role="forensic", temperature=0.2, required=False)


def get_doc_llm() -> Any:
    """DocAnalyst / theoretical depth. Same as detective LLM."""
    return get_detective_llm() or get_llm(temperature=0.2, required=False)


def get_repo_investigator_llm() -> Any:
    """RepoInvestigator. None if AUDITOR_FAST_REPO=1 (skip LLM summary)."""
    if _env("AUDITOR_FAST_REPO"):
        return None
    return get_forensic_llm() or get_llm(temperature=0.2, required=False)
