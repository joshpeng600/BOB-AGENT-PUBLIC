#!/usr/bin/env python3
"""Require B's canonical prediction-contract test before CI can pass."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STARTER_SUBMIT = ROOT / "starter" / "submit.py"
CONTRACT_TEST = ROOT / "tests" / "test_submission.py"


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in (STARTER_SUBMIT, CONTRACT_TEST) if not path.is_file()]
    if missing:
        print("Prediction-contract validation is not bootstrapped; B must provide/verify:", file=sys.stderr)
        for path in missing:
            print(f"- {path}", file=sys.stderr)
        return 1
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            CONTRACT_TEST.name,
            "-v",
        ],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
