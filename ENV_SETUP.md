# Environment Variables Setup

This document describes the required and optional environment variables for the Automaton Auditor.

## Required Setup

### 1. Ollama Configuration

All LLM nodes use local Ollama. No API keys required.

**IMPORTANT:** The model is hardcoded to `llama3.2:3b` in the code. Environment variables like `OLLAMA_MODEL` or `OLLAMA_VISION_MODEL` are **ignored** to prevent model name conflicts.

```bash
# Ollama base URL (default: http://localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434
```

**Before first run:** Pull the model:
```bash
ollama pull llama3.2:3b
```

**Note:** If you previously had `OLLAMA_VISION_MODEL=llava` or similar set, you may need to:
1. Restart your Python application completely
2. Clear any cached environment variables
3. The code will now always use `llama3.2:3b` regardless of environment variables

## Optional Configuration

### 2. LangSmith Observability

Enable tracing for debugging and monitoring:

```bash
# Enable LangSmith tracing
LANGCHAIN_TRACING_V2=true

# LangSmith API key (get from https://smith.langchain.com/)
LANGCHAIN_API_KEY=your_langsmith_api_key_here

# LangSmith project name (optional, defaults to "week2-automato-auditor" in code)
# LANGCHAIN_PROJECT=week2-automato-auditor
```

### 3. Performance Tuning

Control parallelism and rate limiting:

```bash
# Parallel workers for detective nodes (RepoInvestigator, DocAnalyst, VisionInspector)
# Default: 3, Range: 1-8
AUDITOR_DETECTIVE_WORKERS=3

# Parallel workers for judge panel (Prosecutor, Defense, TechLead)
# Default: 3, Range: 1-8
AUDITOR_JUDGE_WORKERS=3

# Maximum concurrent graph runs (rate limiting)
# Default: 2, Range: 1-32
# Lower values prevent overwhelming local Ollama instance
AUDITOR_MAX_CONCURRENT_RUNS=2

# Skip LLM for RepoInvestigator (tool-only mode for faster execution)
# Set to any value to disable LLM summarization
# AUDITOR_FAST_REPO=true
```

## Complete .env.example Template

Create a `.env` file in the project root with:

```bash
# Ollama Configuration (Required)
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# LangSmith Observability (Optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here

# Performance Tuning (Optional)
AUDITOR_DETECTIVE_WORKERS=3
AUDITOR_JUDGE_WORKERS=3
AUDITOR_MAX_CONCURRENT_RUNS=2
# AUDITOR_FAST_REPO=true
```

## Notes

- **No API keys required:** All nodes use local Ollama, so no external API keys are needed.
- **Model selection:** You can use any Ollama model. Popular alternatives:
  - `llama3.2:3b` - Very fast, smaller model
  - `qwen2.5:14b` - Better quality, slower
  - `mistral:7b` - Good balance
- **LangSmith:** Optional but recommended for debugging complex graph executions.
