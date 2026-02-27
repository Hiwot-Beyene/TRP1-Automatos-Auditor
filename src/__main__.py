"""Entrypoint: run audits and parallelism tests via the Web UI at http://localhost:3000."""

import sys

def main() -> None:
    print("Automaton Auditor — use the Web UI to run audits and parallelism tests.")
    print("  API:    uv run uvicorn src.api:app --reload --port 8000")
    print("  Frontend: cd frontend && npm run dev")
    print("  Open:   http://localhost:3000")
    sys.exit(0)

if __name__ == "__main__":
    main()
