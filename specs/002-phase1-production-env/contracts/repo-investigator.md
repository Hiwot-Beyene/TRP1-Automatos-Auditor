# RepoInvestigator tool contract

**Detective:** RepoInvestigator (AST / code detective)  
**Target artifact:** GitHub repository (`target_artifact: github_repo`)

## Capabilities

| Function | Input | Output | Constraints |
|----------|--------|--------|-------------|
| Sandboxed clone | repo_url: str | local path: str (in temp dir) | Use `tempfile.TemporaryDirectory()`; subprocess with timeout; capture stderr/stdout; no `os.system`; sanitize URL |
| extract_git_history | path: str (clone root) | List of {commit, message, timestamp} or equivalent | `git log --oneline --reverse`; parse output; no regex for structured fields where avoidable |
| analyze_graph_structure | path: str (clone root) | Structured description of StateGraph usage | Python `ast` or tree-sitter; detect `add_edge`, `add_conditional_edges`, node names; no regex for code structure |

## Evidence mapping (rubric dimensions)

- **git_forensic_analysis:** extract_git_history → commit count, progression, timestamps.
- **state_management_rigor:** AST scan for `src/state.py` / state usage in `src/graph.py`; BaseModel/TypedDict, reducers (Annotated with operator.ior/operator.add).
- **graph_orchestration:** AST on graph builder: fan-out, fan-in, conditional edges.
- **safe_tool_engineering:** AST/code inspection of `src/tools/`: tempfile, subprocess, no os.system, error handling.
- **structured_output_enforcement:** AST on `src/nodes/judges.py`: `.with_structured_output()` or `.bind_tools()` and retry/validation.

## Error handling

- Clone failure (auth, network, invalid URL): return Evidence with found=False, rationale describing error; do not raise uncaught into graph.
- Missing path / not a git repo: return Evidence with found=False.

## Contract summary

- **Inputs:** repo_url from state; path = result of sandboxed clone.
- **Outputs:** List[Evidence] or updates to state.evidences keyed by dimension id.
- **No:** Regex for AST/code structure; cloning into cwd; os.system; unsanitized URL in shell.
