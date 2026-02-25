"""Interactive CLI: prompt for repo URL and doc URL, then run the detective graph."""

import json
from pathlib import Path

from src.graph import build_detective_graph

DEFAULT_RUBRIC = [
    {"id": "git_forensic_analysis", "name": "Git history", "target_artifact": "github_repo"},
    {"id": "graph_orchestration", "name": "Graph orchestration", "target_artifact": "github_repo"},
    {"id": "theoretical_depth", "name": "Theoretical depth", "target_artifact": "pdf_report"},
    {"id": "swarm_visual", "name": "Swarm visual", "target_artifact": "pdf_images"},
]


def load_rubric() -> list[dict]:
    path = Path("rubric.json")
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "dimensions" in data:
                return data["dimensions"]
        except Exception:
            pass
    return DEFAULT_RUBRIC


def main() -> None:
    print("Automaton Auditor — Detective graph\n")
    repo_url = input("Enter Repo URL: ").strip()
    doc_url = input("Enter doc URL: ").strip()
    rubric_dimensions = load_rubric()

    graph = build_detective_graph()
    state = graph.invoke({
        "repo_url": repo_url or "",
        "pdf_path": doc_url or "",
        "rubric_dimensions": rubric_dimensions,
    })

    evidences = state.get("evidences") or {}
    print("\nEvidences by dimension:", list(evidences.keys()))
    for dim_id, evs in evidences.items():
        print(f"  {dim_id}: {len(evs)} item(s)")


if __name__ == "__main__":
    main()
