# Phase 2: Advanced Tool Engineering (The Detective Layer)

**Source**: TRP1 Challenge Week 2 — The Automaton Auditor (Implementation Curriculum)  
**Folder**: `specs/phase2-detective-layer/`

## Objective

Build forensic tools that don't just "read text" but "understand structure." Implement RepoInvestigator, DocAnalyst, and VisionInspector capabilities.

## Scope

- **RepoInvestigator (AST Detective):** Do not rely on Regex. Use Python `ast` or robust parser; sandboxed clone (tempfile), git log; `analyze_graph_structure(path)`, `extract_git_history(path)`.
- **DocAnalyst (Context Detective):** RAG-lite PDF ingestion; `ingest_pdf(path)`; chunked query; cross-reference with repo evidence.
- **VisionInspector (Multimodal Detective):** `extract_images_from_pdf(path)`; vision model for diagram analysis. Implementation required; execution optional.

## Branches and commits

| Branch | Commits |
|--------|---------|
| `003-phase2-repo-tools` | 1. Add sandboxed git clone and extract_git_history in src/tools/repo_tools.py 2. Add analyze_graph_structure (AST-based) in src/tools/repo_tools.py |
| `004-phase2-doc-tools` | 1. Add ingest_pdf and chunked query (RAG-lite) in src/tools/doc_tools.py |
| `005-phase2-detective-nodes` | 1. Add RepoInvestigator node in src/nodes/detectives.py 2. Add DocAnalyst node in src/nodes/detectives.py 3. Add VisionInspector node and extract_images_from_pdf (execution optional) |

## Key files

- `src/tools/repo_tools.py`
- `src/tools/doc_tools.py`
- `src/nodes/detectives.py`

## References

- Master spec: [../spec.md](../spec.md)
- Functional: [../functional-spec.md](../functional-spec.md)
- Technical: [../technical-spec.md](../technical-spec.md)
- Challenge: `TRP1 Challenge Week 2_ The Automaton Auditor.md`
