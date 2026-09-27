#!/usr/bin/env python3
"""
Chrysalis Golem Deployment Packager
Bundles core mdbase v0.3 schemas, contracts, workflows, setup scripts, and templates
into a single deployable zip archive for frictionless seeding on Golem (Surface Pro X).

Usage:
    python3 System/scripts/package_golem_bundle.py [--output chrysalis-golem-seed.zip]
"""

import argparse
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from update import distribution_files


def create_golem_bundle(output_path: Path):
    """Export the updater's public inventory, plus the experimental setup guides."""
    selected = set(distribution_files(REPO_ROOT))
    selected.update(("docs/data-ingestion-guide.md",
                     "docs/golem-deployment-and-spark-test-guide.md",
                     "docs/spark-agent-system-prompt.md",
                     "docs/staged-migration-plan.md"))
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        for relative in sorted(selected):
            bundle.write(REPO_ROOT / relative, arcname=relative)
    print(f"[package] Exported {len(selected)} public framework files to {output_path}")


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
