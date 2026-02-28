"""Centralized LLM clients: judge (Groq/Gemini), RepoInvestigator, VisionInspector, DocAnalyst."""

import os
from typing import Any

DEFAULT_GROQ_JUDGE_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_REPO_MODEL = "llama-3.1-8b-instant"
DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"

_judge_llm_groq: Any = None
_judge_llm_google: Any = None
_repo_llm: Any = None
_vision_llm: Any = None
_doc_llm: Any = None


def get_judge_llm() -> Any:
    """Primary judge LLM. Prefer Groq; if JUDGE_PROVIDER=google or Groq unavailable, use Gemini."""
    provider = (os.environ.get("JUDGE_PROVIDER") or "groq").strip().lower()
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
    """Optional Groq LLM for RepoInvestigator summary. Cached. Returns None if GROQ_API_KEY unset or AUDITOR_FAST_REPO set."""
    global _repo_llm
    if not os.environ.get("GROQ_API_KEY") or os.environ.get("AUDITOR_FAST_REPO"):
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
