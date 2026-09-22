"""
tests/harness/models.py
Core data structures, diagnostics, enums, and result envelopes for mdbase validation.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class ValidationLayer(str, Enum):
    LAYER_1_SYNTAX = "Layer 1: Artifact Syntax & Schema"
    LAYER_2_ENGINE = "Layer 2: mdbase Engine Capabilities"
    LAYER_3_FRAMEWORK = "Layer 3: Chrysalis Framework Behavior"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Alias RuleSeverity for backwards-compatibility with various specifications
RuleSeverity = DiagnosticSeverity


class RecoveryAction(str, Enum):
    FIX_REQUEST = "FixRequest"
    REFRESH = "Refresh"
    RESOLVE_CONFLICT = "ResolveConflict"
    REPAIR_COLLECTION = "RepairCollection"
    RETRY = "Retry"


class DiagnosticCode(str, Enum):
    # Layer 1 Syntax & Schema
    SYNTAX_MISSING_DELIMITER = "syntax_missing_delimiter"
    SYNTAX_UNCLOSED_DELIMITER = "syntax_unclosed_delimiter"
    SYNTAX_YAML_PARSE_ERROR = "syntax_yaml_parse_error"
    FORMAT_INVALID = "format_invalid"
    SCHEMA_REQUIRED = "schema_required"
    SCHEMA_ADDITIONAL_PROPERTIES = "schema_additional_properties"
    SCHEMA_FORMAT = "schema_format"
    SCHEMA_ENUM = "schema_enum"
    SCHEMA_PATTERN = "schema_pattern"
    SCHEMA_MINIMUM = "schema_minimum"
    SCHEMA_TYPE = "schema_type"
    SCHEMA_VIOLATION = "schema_violation"

    # Layer 2 mdbase Engine
    COLLECTION_MANIFEST_MISSING = "collection_manifest_missing"
    COLLECTION_MANIFEST_CORRUPT = "collection_manifest_corrupt"
    COLLECTION_VERSION_UNSUPPORTED = "collection_version_unsupported"
    TYPES_FOLDER_MISSING = "types_folder_missing"
    TYPE_DEFINITION_CORRUPT = "type_definition_corrupt"
    REQUIRED_TYPE_MISSING = "required_type_missing"
    TYPE_UNKNOWN = "type_unknown"
    UNIQUE_CONSTRAINT_VIOLATION = "unique_constraint_violation"
    DUPLICATE_SOURCE_DETECTED = "duplicate_source_detected"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    RECORD_NOT_FOUND = "record_not_found"

    # Layer 3 Chrysalis Framework
    LINK_BROKEN = "link_broken"
    LINK_TARGET_TYPE_MISMATCH = "link_target_type_mismatch"
    PROVENANCE_CHECKSUM_MISMATCH = "provenance_checksum_mismatch"
    WORKFLOW_INVALID_STATE = "workflow_invalid_state"
    WORKFLOW_ILLEGAL_TRANSITION = "workflow_illegal_transition"
    APPROVAL_REQUIRED = "approval_required"
    UNTRUSTED_PAYLOAD_UNQUARANTINED = "untrusted_payload_unquarantined"
    UNTRUSTED_PAYLOAD_DELIMITER_ESCAPE = "untrusted_payload_delimiter_escape"
    ANTI_SIMULATION_VIOLATION = "anti_simulation_violation"


@dataclass
class Diagnostic:
    code: Union[str, DiagnosticCode]
    severity: Union[str, DiagnosticSeverity]
    message: str
    layer: Union[str, ValidationLayer] = ValidationLayer.LAYER_1_SYNTAX
    field: Optional[str] = None
    path: Optional[str] = None
    recovery_action: Optional[Union[str, RecoveryAction]] = None

    def __post_init__(self):
        if isinstance(self.code, DiagnosticCode):
            self.code = self.code.value
        if isinstance(self.severity, DiagnosticSeverity):
            self.severity = self.severity.value
        if isinstance(self.layer, ValidationLayer):
            self.layer = self.layer.value
        if isinstance(self.recovery_action, RecoveryAction):
            self.recovery_action = self.recovery_action.value

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "code": str(self.code),
            "severity": str(self.severity),
            "layer": str(self.layer),
            "message": self.message,
        }
        if self.field is not None:
            res["field"] = self.field
        if self.path is not None:
            res["path"] = str(self.path)
        if self.recovery_action is not None:
            res["recovery_action"] = str(self.recovery_action)
        return res


@dataclass
class ValidationResult:
    valid: bool
    diagnostics: List[Diagnostic] = field(default_factory=list)
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    path: Optional[Path] = None

    @property
    def success(self) -> bool:
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "valid": self.valid,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "frontmatter": self.frontmatter,
            "body": self.body,
        }
        if self.path is not None:
            res["path"] = str(self.path)
        return res


@dataclass
class RecordContext:
    path: Path
    rel_path: str
    raw_text: str
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    resolved_type: Optional[str] = None
    revision: str = ""
    layer1_passed: bool = False
    layer2_passed: bool = False
    layer3_passed: bool = False


@dataclass
class LinkEdge:
    source_path: str
    source_type: str
    target_ref: str
    expected_target_type: Optional[str]
    link_property: str
    resolved_target_path: Optional[str] = None
    is_broken: bool = False
    checksum_verified: Optional[bool] = None


@dataclass
class CollectionSummary:
    collection_dir: str
    is_valid: bool
    total_files: int = 0
    records_by_type: Dict[str, int] = field(default_factory=dict)
    errors_total: int = 0
    layer1_syntax_errors: int = 0
    layer2_engine_errors: int = 0
    layer3_framework_errors: int = 0
    warnings: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_dir": self.collection_dir,
            "is_valid": self.is_valid,
            "total_files": self.total_files,
            "records_by_type": self.records_by_type,
            "errors_total": self.errors_total,
            "layer1_syntax_errors": self.layer1_syntax_errors,
            "layer2_engine_errors": self.layer2_engine_errors,
            "layer3_framework_errors": self.layer3_framework_errors,
            "warnings": self.warnings,
            "duration_seconds": round(self.duration_seconds, 4),
        }


@dataclass
class ValidationReport:
    collection_dir: Path
    total_files_scanned: int = 0
    records_by_type: Dict[str, int] = field(default_factory=dict)
    diagnostics: List[Diagnostic] = field(default_factory=list)
    duration_seconds: float = 0.0
    layer1_errors: int = 0
    layer2_errors: int = 0
    layer3_errors: int = 0
    warnings: int = 0

    @property
    def is_valid(self) -> bool:
        return (self.layer1_errors + self.layer2_errors + self.layer3_errors) == 0

    def add_diagnostic(self, diag: Diagnostic) -> None:
        self.diagnostics.append(diag)
        sev = str(diag.severity).lower()
        layer = str(diag.layer)
        if sev == "error":
            if ValidationLayer.LAYER_1_SYNTAX.value in layer:
                self.layer1_errors += 1
            elif ValidationLayer.LAYER_2_ENGINE.value in layer:
                self.layer2_errors += 1
            elif ValidationLayer.LAYER_3_FRAMEWORK.value in layer:
                self.layer3_errors += 1
            else:
                self.layer1_errors += 1
        elif sev == "warning":
            self.warnings += 1

    def to_summary(self) -> CollectionSummary:
        return CollectionSummary(
            collection_dir=str(self.collection_dir),
            is_valid=self.is_valid,
            total_files=self.total_files_scanned,
            records_by_type=dict(self.records_by_type),
            errors_total=self.layer1_errors + self.layer2_errors + self.layer3_errors,
            layer1_syntax_errors=self.layer1_errors,
            layer2_engine_errors=self.layer2_errors,
            layer3_framework_errors=self.layer3_errors,
            warnings=self.warnings,
            duration_seconds=self.duration_seconds,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.to_summary().to_dict(),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
