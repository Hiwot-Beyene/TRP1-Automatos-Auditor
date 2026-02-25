# Test-Driven Development (TRP1 Challenge)

This project follows **Test-Driven Development (TDD)** per the implementation plan and TRP1 Challenge: write tests from contracts first, then implement to pass.

## Approach

1. **Red:** Write a failing test that encodes the contract or requirement (from `specs/002-phase1-production-env/contracts/` or plan).
2. **Green:** Implement the minimum code so the test passes.
3. **Refactor:** Improve implementation without breaking tests.

## Test layout

| Layer        | Path                    | Purpose |
|-------------|--------------------------|--------|
| **Unit**    | `tests/unit/`            | State models, node functions with mock state, pure logic. No network or graph compile. |
| **Contract**| `tests/contract/`        | Graph topology and behaviour from detective-graph contract; tool contracts. |
| **Integration** | `tests/integration/` | End-to-end: build graph, invoke with real/minimal state, assert outputs. |

## Running tests

```bash
uv sync --all-extras   # install pytest
uv run pytest tests/ -v
uv run pytest tests/unit/ -v
uv run pytest tests/contract/ -v
uv run pytest tests/integration/ -v
```

## Contracts as spec

- **Detective graph:** `contracts/detective-graph.md` → `tests/contract/test_detective_graph_parallelism.py` (fan-out, fan-in, evidence merge).
- **RepoInvestigator:** `contracts/repo-investigator.md` → contract tests for clone/history/graph structure when adding or changing repo_tools.
- **DocAnalyst / VisionInspector:** contracts under `contracts/` define expected inputs/outputs; unit tests for nodes use mock state and assert return shape (`evidences` dict, Evidence fields).

New behaviour: add or extend a test in the appropriate layer first, run pytest (see it fail), then implement.
