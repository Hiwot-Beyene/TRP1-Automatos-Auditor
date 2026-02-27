#!/usr/bin/env python3
"""Run the full auditor graph (detectives → report_accuracy → judges → chief_justice). Uses rubric.json."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


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

    parser = argparse.ArgumentParser(description="Run Automaton Auditor against repo URL and optional PDF.")
    parser.add_argument("repo_url", nargs="?", default="", help="GitHub repository URL")
    parser.add_argument("pdf_path", nargs="?", default="", help="Path to PDF report")
    parser.add_argument("--mode", choices=("self", "peer"), default="self", help="Audit mode: self (report_onself_generated) or peer (report_onpeer_generated)")
    args = parser.parse_args()
    repo_url = args.repo_url or ""
    pdf_path = args.pdf_path or ""

    if not repo_url and not pdf_path:
        print("Usage: uv run python scripts/run_audit.py [repo_url] [pdf_path] [--mode self|peer]")
        print("Example: uv run python scripts/run_audit.py https://github.com/owner/repo /path/to/report.pdf --mode self")
        sys.exit(1)

    audit_dir = root / "audit" / ("report_onself_generated" if args.mode == "self" else "report_onpeer_generated")
    audit_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    trace_id = str(uuid.uuid4())
    from src.graph import build_detective_graph

    graph = build_detective_graph()
    state = graph.invoke(
        {
            "repo_url": repo_url,
            "pdf_path": pdf_path,
            "rubric_dimensions": dimensions,
            "report_type": args.mode,
            "audit_output_dir": str(audit_dir),
        },
        config={
            "run_name": "LangGraph",
            "thread_id": trace_id,
            "project_name": "week2-automato-auditor",
            "tags": ["audit", "cli", args.mode],
            "metadata": {
                "repo_url": (repo_url or "")[:80],
                "has_pdf": bool(pdf_path),
                "mode": args.mode,
                "trace_id": trace_id,
            },
        },
    )
    evidences = state.get("evidences") or {}
    final_report = state.get("final_report")

    out = {}
    for k, v in evidences.items():
        out[k] = [e.model_dump() if hasattr(e, "model_dump") else (e if isinstance(e, dict) else {}) for e in v]
    result = {"evidences": out}
    if final_report:
        result["final_report_path"] = str(audit_dir / "audit_report.md")
        result["overall_score"] = getattr(final_report, "overall_score", None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
