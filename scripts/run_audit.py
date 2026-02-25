#!/usr/bin/env python3
"""Run the detective graph against a target repo URL (and optional PDF path). Uses rubric.json."""

import json
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    rubric_path = root / "rubric.json"
    if not rubric_path.is_file():
        print("rubric.json not found", file=sys.stderr)
        sys.exit(1)
    dimensions = json.loads(rubric_path.read_text(encoding="utf-8")).get("dimensions", [])
    if not dimensions:
        print("rubric.json has no dimensions", file=sys.stderr)
        sys.exit(1)

    repo_url = sys.argv[1] if len(sys.argv) > 1 else ""
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else ""
    if not repo_url and not pdf_path:
        print("Usage: uv run python scripts/run_audit.py <repo_url> [pdf_path]")
        print("Example: uv run python scripts/run_audit.py https://github.com/owner/repo")
        sys.exit(1)

    from src.graph import build_detective_graph

    graph = build_detective_graph()
    state = graph.invoke({
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": dimensions,
    })
    evidences = state.get("evidences") or {}
    out = {}
    for k, v in evidences.items():
        out[k] = [e.model_dump() if hasattr(e, "model_dump") else (e if isinstance(e, dict) else {}) for e in v]
    print(json.dumps({"evidences": out}, indent=2))


if __name__ == "__main__":
    main()
