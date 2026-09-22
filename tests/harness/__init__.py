"""
tests/harness/__init__.py
Chrysalis mdbase v0.3 Validation Test Harness Package.
"""
from .engine_validator import EngineValidator
from .hypergraph_validator import (
    HypergraphValidator,
    LinkIntegrityValidator,
    WIKILINK_PATTERN,
)
from .models import (
    CollectionSummary,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    LinkEdge,
    RecordContext,
    RecoveryAction,
    RuleSeverity,
    ValidationLayer,
    ValidationReport,
    ValidationResult,
)
from .reporters import (
    BaseReporter,
    JSONReporter,
    MarkdownReporter,
    TAPReporter,
    TerminalReporter,
    get_reporter,
)
from .syntax_validator import SyntaxValidator
from .validation_harness import ValidationHarness, main
from .workflow_validator import WorkflowValidator

__all__ = [
    # Models & Enums
    "CollectionSummary",
    "Diagnostic",
    "DiagnosticCode",
    "DiagnosticSeverity",
    "LinkEdge",
    "RecordContext",
    "RecoveryAction",
    "RuleSeverity",
    "ValidationLayer",
    "ValidationReport",
    "ValidationResult",
    # Validators
    "SyntaxValidator",
    "EngineValidator",
    "HypergraphValidator",
    "LinkIntegrityValidator",
    "WorkflowValidator",
    "WIKILINK_PATTERN",
    # Reporters
    "BaseReporter",
    "TerminalReporter",
    "JSONReporter",
    "TAPReporter",
    "MarkdownReporter",
    "get_reporter",
    # Master Harness & CLI
    "ValidationHarness",
    "main",
]
