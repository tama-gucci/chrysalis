#!/usr/bin/env python3
"""
Chrysalis Golem Deployment Packager
Bundles core mdbase v0.3 schemas, contracts, workflows, setup scripts, and templates
into a single deployable zip archive for frictionless seeding on Golem (Surface Pro X).

Usage:
    python3 System/scripts/package_golem_bundle.py [--output chrysalis-golem-seed.zip]
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path


def create_golem_bundle(output_path: Path):
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Inventory of items to include in the bundle
    bundle_files = [
        "mdbase.yaml",
        "System/Life-Roadmap.md",
        "docs/golem-deployment-and-spark-test-guide.md",
        "docs/spark-agent-system-prompt.md",
        "System/scripts/setup_golem.ps1",
    ]

    bundle_dirs = [
        "_types",
        "contracts",
        "_contracts",
        "_templates",
        "chrysalis/Workflows",
        "System/_templates",
        "tests/harness",
    ]

    print(f"[package] Packaging Chrysalis Golem Seed Bundle to: {output_path}")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add discrete files
        for rel_file in bundle_files:
            file_path = repo_root / rel_file
            if file_path.exists() and file_path.is_file():
                zf.write(file_path, arcname=rel_file)
                print(f"  + Added: {rel_file}")
            else:
                print(f"  ! Warning: {rel_file} not found, skipping.")

        # Add directories recursively
        for rel_dir in bundle_dirs:
            dir_path = repo_root / rel_dir
            if dir_path.exists() and dir_path.is_dir():
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith((".pyc", ".lock")) or file.startswith("."):
                            continue
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(repo_root).as_posix()
                        zf.write(full_path, arcname=arcname)
                        print(f"  + Added: {arcname}")

    print(f"[package] Bundle successfully created: {output_path} ({output_path.stat().st_size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Package Chrysalis for Golem deployment.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("chrysalis-golem-seed.zip"),
        help="Destination zip archive path",
    )
    args = parser.parse_args()
    create_golem_bundle(args.output.resolve())


if __name__ == "__main__":
    main()
