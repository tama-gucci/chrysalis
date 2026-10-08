"""Isolated entry point: python -I -B /package/run.py <command>."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrysalis.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
