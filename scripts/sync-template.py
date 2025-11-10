#!/usr/bin/env python3
"""Small helper to update an existing project using copier.

Usage:
  # update a project that was created from this template:
  python scripts/sync-template.py /path/to/target --trust
"""

import subprocess
import sys
from pathlib import Path


def run_update(target: Path, trust: bool = False) -> None:
    if not target.exists():
        raise FileNotFoundError(f"Target directory does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target is not a directory: {target}")

    args = ["copier", "update", str(Path(__file__).resolve().parents[1])]
    if trust:
        args.append("--trust")
    subprocess.run(args, cwd=str(target), check=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sync-template.py <project_path> [--trust]")
        sys.exit(2)
    target = Path(sys.argv[1])
    trust = "--trust" in sys.argv[2:]
    run_update(target, trust)
