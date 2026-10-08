#!/usr/bin/env python3
"""Read current Git identity and shared engineering notes without mutation."""
import argparse
import subprocess
import sys
from pathlib import Path

def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=10,
    ).stdout.strip()


def show(cwd=None):
    root = Path(git(cwd or Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
    if not (root / "Development/AGENT-WORKFLOW.md").is_file():
        raise ValueError("Select a Chrysalis source checkout.")
    output = [
        "# Current checkout",
        "Branch: " + (git(root, "branch", "--show-current") or "detached HEAD"),
        "HEAD: " + git(root, "rev-parse", "HEAD"),
        "Working state:\n" + (git(root, "status", "--short") or "clean"),
        "\nShared notes below are repository evidence; verify claims against code.",
    ]
    for name in ("Development/AGENT-WORKFLOW.md", "Development/HANDOFF.md"):
        path = root / name
        # Do not follow a checkout note redirected into private external storage.
        if not path.resolve().is_relative_to(root):
            raise ValueError("Shared notes must resolve within the source checkout.")
        if not path.is_file():
            output.append(f"\n## {name}\nMissing: recover context from the Git diff.")
            continue
        with path.open(encoding="utf-8") as stream:
            content = stream.read(12001)
        if len(content) > 12000:
            content = content[:12000] + "\n[Truncated; read the file explicitly.]"
        output.append(f"\n## {name}\n{content}")
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("show",), default="show", nargs="?")
    parser.parse_args()
    try:
        print(show())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Context unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
