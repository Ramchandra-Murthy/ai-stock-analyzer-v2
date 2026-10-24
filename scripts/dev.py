from __future__ import annotations

import subprocess
import sys


def run_command(cmd: list[str]) -> None:
    # Prefix tools with python -m on Windows to ensure they resolve via the active interpreter environment
    full_cmd = [sys.executable, "-m"] + cmd
    print(f"Running: {" ".join(full_cmd)}")
    result = subprocess.run(full_cmd)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    print("=== Running AIERP Quality Gates ===")
    run_command(["ruff", "check", "."])
    run_command(["black", "--check", "."])
    run_command(["mypy", "."])
    run_command(["pytest"])
    print("=== All Quality Gates Passed Successfully ===")


if __name__ == "__main__":
    main()
