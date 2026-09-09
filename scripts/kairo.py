#!/usr/bin/env python3
"""Unified Kairo CLI launcher delegating to specific subsystems (Evaluation, Release, Tools)."""

import os
import sys
from pathlib import Path

# Ensure backend is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: kairo <command> [options]")
        print("Available commands:")
        print("  eval    Run evaluations, benchmarks, and baseline comparisons")
        sys.exit(1)

    subcommand = sys.argv[1]
    # Re-slice argv so sub-parsers see the remaining flags
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand == "eval":
        from app.evaluation.cli import main as eval_main
        eval_main()
    else:
        print(f"Unknown command: '{subcommand}'. Available: eval")
        sys.exit(1)


if __name__ == "__main__":
    main()
