#!/usr/bin/env python3
\"\"\"Small helper to update an existing project using copier.

Usage:
  # update a project that was created from this template:
  python scripts/sync-template.py /path/to/target --trust
\"\"\"
import sys
import subprocess
from pathlib import Path

def run_update(target: Path, trust: bool = False):
    args = ["copier", "update", str(Path(__file__).resolve().parents[1])]
    if trust:
        args.append("--trust")
    args += ["--data", f'project_path={target}']
    subprocess.run(args, check=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sync-template.py <project_path> [--trust]")
        sys.exit(2)
    target = Path(sys.argv[1])
    trust = "--trust" in sys.argv[2:]
    run_update(target, trust)