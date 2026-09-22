"""
tests/harness/validation_harness.py
Standalone local Python validation test harness and CLI runner for mdbase v0.3.
Conforms to Python 3.10+ standard library, PyYAML, and jsonschema.
"""
import argparse
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

try:
    from .engine_validator import EngineValidator
    from .hypergraph_validator import HypergraphValidator
    from .models import (
        CollectionSummary,
        Diagnostic,
        DiagnosticCode,
        DiagnosticSeverity,
        RecoveryAction,
        ValidationLayer,
        ValidationReport,
    )
    from .reporters import get_reporter
    from .syntax_validator import SyntaxValidator
    from .workflow_validator import WorkflowValidator
except (ImportError, ValueError):
    # Support direct execution: python tests/harness/validation_harness.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tests.harness.engine_validator import EngineValidator
    from tests.harness.hypergraph_validator import HypergraphValidator
    from tests.harness.models import (
        CollectionSummary,
        Diagnostic,
        DiagnosticCode,
        DiagnosticSeverity,
        RecoveryAction,
        ValidationLayer,
        ValidationReport,
    )
    from tests.harness.reporters import get_reporter
    from tests.harness.syntax_validator import SyntaxValidator
    from tests.harness.workflow_validator import WorkflowValidator


class ValidationHarness:
    def __init__(self, collection_dir: Union[str, Path]):
        self.collection_dir = Path(collection_dir).resolve()
        self.syntax_validator = SyntaxValidator()
        self.engine_validator = EngineValidator(self.collection_dir)
        self.hypergraph_validator = HypergraphValidator(self.collection_dir)
        self.workflow_validator = WorkflowValidator()

    def validate_manifest(self) -> ValidationReport:
        """Validates mdbase.yaml and loads type schemas."""
        start_time = time.time()
        report = ValidationReport(collection_dir=self.collection_dir)

        manifest_diags = self.engine_validator.load_and_validate_manifest()
        for d in manifest_diags:
            report.add_diagnostic(d)

        if not report.is_valid:
            report.duration_seconds = time.time() - start_time
            return report

        type_diags = self.engine_validator.load_types()
        for d in type_diags:
            report.add_diagnostic(d)

        report.duration_seconds = time.time() - start_time
        return report

    def discover_records(
        self,
        target_path: Optional[Path] = None,
        type_filter: Optional[str] = None
    ) -> List[Tuple[Path, str]]:
        """
        Discovers all Markdown record files within the collection or target_path,
        honoring exclusions declared in mdbase.yaml.
        Returns a list of (absolute_path, relative_to_collection_path).
        """
        scan_root = target_path if target_path else self.collection_dir
        if not scan_root.exists():
            return []

        if scan_root.is_file():
            rel_path = str(scan_root.relative_to(self.collection_dir)).replace("\\", "/")
            return [(scan_root, rel_path)]

        # Get exclusions from manifest or defaults
        default_excludes = {
            ".git", ".venv", "venv", ".chrysalis", "node_modules",
            "System", "Development", "tests", "fixtures", "docs",
            "_types", "_contracts", "_templates", "apps", "contracts",
            "Workflows", "Views", ".agent", ".agents"
        }
        manifest_excludes = set(self.engine_validator.config.get("settings", {}).get("exclude", []) or self.engine_validator.config.get("exclude", []))
        excluded_dirs = default_excludes.union(manifest_excludes)

        records: List[Tuple[Path, str]] = []
        for root, dirs, files in os.walk(scan_root):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith(".")]

            for file in files:
                if not file.endswith(".md"):
                    continue
                # Skip templates or root doc/dashboard files
                if file.endswith(".template.md") or file in (
                    "Dashboard.md", "README.md", "STATUS.md", "AGENTS.md", "ARCHITECTURE.md"
                ):
                    continue

                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.collection_dir)).replace("\\", "/")

                # Skip files inside excluded paths if scan_root was collection_dir
                parts = Path(rel_path).parts
                if any(p in excluded_dirs for p in parts[:-1]):
                    continue

                records.append((full_path, rel_path))

        return sorted(records, key=lambda x: str(x[1]))

    def run_full_validation(
        self,
        target_path: Optional[Path] = None,
        layers: Optional[Sequence[int]] = None,
        type_filter: Optional[str] = None,
        check_links: bool = True,
        strict_links: bool = False
    ) -> ValidationReport:
        """
        Executes a comprehensive validation pass across Layer 1 (syntax/schema),
        Layer 2 (collection/engine), and Layer 3 (hypergraph/workflows).
        """
        start_time = time.time()
        active_layers = set(layers) if layers else {1, 2, 3}

        # Step 1: Validate manifest and types
        report = self.validate_manifest()
        if not report.is_valid:
            report.duration_seconds = time.time() - start_time
            return report

        # Step 2: Discover records
        discovered = self.discover_records(target_path, type_filter)
        report.total_files_scanned = len(discovered)

        parsed_records: List[Tuple[str, Dict[str, Any]]] = []

        # Step 3: Validate each record
        for full_path, rel_path in discovered:
            raw_text = full_path.read_text(encoding="utf-8")

            # Layer 1: Syntax & Delimiter Check
            parsed_ok, fm, body, l1_diags = self.syntax_validator.parse_frontmatter(raw_text, rel_path)
            for d in l1_diags:
                report.add_diagnostic(d)

            if not parsed_ok:
                continue

            # Layer 2: Resolve Type
            rec_type = self.engine_validator.resolve_type_for_path(rel_path, fm)
            if type_filter and rec_type != type_filter:
                continue

            if rec_type:
                report.records_by_type[rec_type] = report.records_by_type.get(rec_type, 0) + 1
            else:
                report.records_by_type["unknown"] = report.records_by_type.get("unknown", 0) + 1
                if 2 in active_layers:
                    report.add_diagnostic(Diagnostic(
                        code=DiagnosticCode.TYPE_UNKNOWN,
                        severity=DiagnosticSeverity.WARNING,
                        layer=ValidationLayer.LAYER_2_ENGINE,
                        message=f"Record path '{rel_path}' does not match any registered type in _types/",
                        path=rel_path,
                        recovery_action=RecoveryAction.FIX_REQUEST
                    ))

            # Layer 1: JSON Schema Draft 2020-12 Validation
            if 1 in active_layers and rec_type and rec_type in self.engine_validator.type_schemas:
                schema_dict = self.engine_validator.type_schemas[rec_type]
                schema_valid, _, _, schema_diags = self.syntax_validator.validate_syntax_and_schema(
                    raw_text,
                    rel_path,
                    schema_dict
                )
                for d in schema_diags:
                    report.add_diagnostic(d)

            # Store record for collection uniqueness and link analysis
            # Ensure type is populated for link traversal
            record_fm = dict(fm)
            if "type" not in record_fm and rec_type:
                record_fm["type"] = rec_type
            parsed_records.append((rel_path, record_fm))

        # Step 4: Layer 2 Collection Uniqueness
        if 2 in active_layers:
            unique_diags = self.engine_validator.validate_collection_uniqueness(parsed_records)
            for d in unique_diags:
                report.add_diagnostic(d)

        # Step 5: Layer 3 Hypergraph Link Traversal
        if 3 in active_layers and check_links:
            link_diags = self.hypergraph_validator.validate_links(
                parsed_records,
                strict_existence=strict_links
            )
            for d in link_diags:
                report.add_diagnostic(d)

        report.duration_seconds = time.time() - start_time
        return report

    def validate_all_records(
        self,
        path: Optional[Path] = None,
        layers: Optional[Sequence[int]] = None,
        type_filter: Optional[str] = None,
        check_links: bool = True,
        strict_links: bool = False
    ) -> ValidationReport:
        """Alias for run_full_validation."""
        return self.run_full_validation(
            target_path=path,
            layers=layers,
            type_filter=type_filter,
            check_links=check_links,
            strict_links=strict_links
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chrysalis mdbase v0.3 Local Validation Test Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c", "--collection",
        default=".",
        help="Path to mdbase collection root directory."
    )
    parser.add_argument(
        "-p", "--path",
        default=None,
        help="Subdirectory or file path to validate within the collection."
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "json", "tap", "markdown", "md"],
        default="terminal",
        help="Output report formatting format."
    )
    parser.add_argument(
        "--layer",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Specific validation layer to evaluate (1: syntax, 2: engine, 3: framework, all: full pass)."
    )
    parser.add_argument(
        "--type",
        choices=["task", "project", "zettel", "source"],
        default=None,
        help="Filter validation to specific record type."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: treat broken link warnings as errors."
    )
    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Disable Layer 3 hypergraph link integrity checks."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write report output to specified file instead of stdout."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output."
    )

    args = parser.parse_args(argv)

    collection_root = Path(args.collection).resolve()
    target_path = Path(args.path).resolve() if args.path else None

    # Layer selection
    if args.layer == "1":
        layers = [1]
    elif args.layer == "2":
        layers = [2]
    elif args.layer == "3":
        layers = [3]
    else:
        layers = [1, 2, 3]

    try:
        harness = ValidationHarness(collection_root)
        # Check manifest existence early for exit code 2
        manifest_path = collection_root / "mdbase.yaml"
        if not manifest_path.is_file():
            sys.stderr.write(f"Configuration error: Missing {manifest_path}\n")
            return 2

        report = harness.run_full_validation(
            target_path=target_path,
            layers=layers,
            type_filter=args.type,
            check_links=not args.no_links,
            strict_links=args.strict
        )

        reporter = get_reporter(args.format)
        output_str = reporter.format_report(report, use_color=(args.output is None))

        if args.output:
            Path(args.output).write_text(output_str, encoding="utf-8")
        else:
            print(output_str)

        # Exit code determination
        if not report.is_valid:
            # Check if failure is configuration-level (manifest missing/corrupt)
            for d in report.diagnostics:
                if d.code in (
                    DiagnosticCode.COLLECTION_MANIFEST_MISSING,
                    DiagnosticCode.COLLECTION_MANIFEST_CORRUPT,
                    DiagnosticCode.COLLECTION_VERSION_UNSUPPORTED,
                    DiagnosticCode.TYPES_FOLDER_MISSING,
                ):
                    return 2
            return 1

        # Clean success
        return 0

    except Exception as exc:
        sys.stderr.write(f"Fatal harness error: {exc}\n")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
