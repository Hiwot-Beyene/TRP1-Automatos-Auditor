"""Centralized LLM clients: judge (Ollama/Groq/Gemini), RepoInvestigator, VisionInspector, DocAnalyst."""

import os
from typing import Any

DEFAULT_GROQ_JUDGE_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_REPO_MODEL = "llama-3.1-8b-instant"
DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

_judge_llm_ollama: Any = None
_judge_llm_groq: Any = None
_judge_llm_google: Any = None
_repo_llm: Any = None
_vision_llm: Any = None
_doc_llm: Any = None


def get_judge_llm_ollama() -> Any:
    """Ollama LLM for judges (local). Cached. Uses OLLAMA_MODEL and OLLAMA_BASE_URL."""
    global _judge_llm_ollama
    if _judge_llm_ollama is None:
        try:
            from langchain_ollama import ChatOllama
            model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
            base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
            _judge_llm_ollama = ChatOllama(model=model, base_url=base_url, temperature=0.6)
        except Exception:
            return None
    return _judge_llm_ollama


def get_judge_llm() -> Any:
    """Primary judge LLM. JUDGE_PROVIDER=ollama uses local Ollama (llama3.2); groq | google use APIs."""
    provider = (os.environ.get("JUDGE_PROVIDER") or "ollama").strip().lower()
    if provider == "ollama":
        return get_judge_llm_ollama()
    if provider == "google":
        return get_judge_llm_google()
    if os.environ.get("GROQ_API_KEY"):
        return get_judge_llm_groq()
    return get_judge_llm_google()


def get_judge_llm_groq() -> Any:
    """Groq LLM for judges. Cached. Returns None if GROQ_API_KEY unset."""
    global _judge_llm_groq
    if not os.environ.get("GROQ_API_KEY"):
        return None
    if _judge_llm_groq is None:
        from langchain_groq import ChatGroq
        model = os.environ.get("GROQ_JUDGE_MODEL") or DEFAULT_GROQ_JUDGE_MODEL
        _judge_llm_groq = ChatGroq(model=model, temperature=0.6)
    return _judge_llm_groq


def get_judge_llm_google() -> Any:
    """Gemini LLM for judges (fallback). Cached. Returns None if GOOGLE_API_KEY unset."""
    global _judge_llm_google
    if not os.environ.get("GOOGLE_API_KEY"):
        return None
    if _judge_llm_google is None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = os.environ.get("GOOGLE_GEMINI_MODEL", DEFAULT_GOOGLE_MODEL)
            _judge_llm_google = ChatGoogleGenerativeAI(model=model, temperature=0.6)
        except Exception:
            return None
    return _judge_llm_google


def get_repo_investigator_llm() -> Any:
    """Optional LLM for RepoInvestigator summary. Uses Ollama when JUDGE_PROVIDER=ollama; else Groq if API key set. Skip if AUDITOR_FAST_REPO."""
    global _repo_llm
    if os.environ.get("AUDITOR_FAST_REPO"):
        return None
    provider = (os.environ.get("JUDGE_PROVIDER") or "ollama").strip().lower()
    if provider == "ollama":
        if _repo_llm is None:
            try:
                from langchain_ollama import ChatOllama
                model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
                base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
                _repo_llm = ChatOllama(model=model, base_url=base_url, temperature=0.2)
            except Exception:
                return None
        return _repo_llm
    if not os.environ.get("GROQ_API_KEY"):
        return None
    if _repo_llm is None:
        from langchain_groq import ChatGroq
        model = os.environ.get("GROQ_REPO_MODEL", DEFAULT_GROQ_REPO_MODEL)
        _repo_llm = ChatGroq(model=model, temperature=0.2)
    return _repo_llm


def get_vision_llm() -> Any:
    """Gemini LLM for VisionInspector (multimodal). Cached. Returns None if GOOGLE_API_KEY unset."""
    global _vision_llm
    if not os.environ.get("GOOGLE_API_KEY"):
        return None
    if _vision_llm is None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = os.environ.get("GOOGLE_GEMINI_MODEL", DEFAULT_GOOGLE_MODEL)
            _vision_llm = ChatGoogleGenerativeAI(model=model)
        except Exception:
            return None
    return _vision_llm


def get_doc_llm() -> Any:
    """Gemini LLM for DocAnalyst (theoretical depth, RAG). Cached. Returns None if GOOGLE_API_KEY unset."""
    global _doc_llm
    if not os.environ.get("GOOGLE_API_KEY"):
        return None
    if _doc_llm is None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = os.environ.get("GOOGLE_GEMINI_MODEL", DEFAULT_GOOGLE_MODEL)
            _doc_llm = ChatGoogleGenerativeAI(model=model)
        except Exception:
            return None
    return _doc_llm
