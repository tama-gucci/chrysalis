"""
tests/harness/syntax_validator.py
Layer 1 Validator: Syntax & JSON Schema Draft 2020-12 Conformance.
"""
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
try:
    from jsonschema import Draft202012Validator, FormatChecker
    HAS_JSONSCHEMA = True
except ImportError:
    Draft202012Validator = None
    FormatChecker = None
    HAS_JSONSCHEMA = False

from .models import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    RecoveryAction,
    ValidationLayer,
    ValidationResult,
)

TIMEZONE_OFFSET_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?[+\-][0-9]{2}:[0-9]{2}$"
)
RAW_UTC_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)
DATE_ONLY_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class _MockValidationError:
    def __init__(self, validator: str, message: str, path: Sequence[Union[str, int]] = ()):
        self.validator = validator
        self.message = message
        self.path = list(path)


class _FallbackValidator:
    def __init__(self, schema_dict: Dict[str, Any]):
        self.schema = schema_dict

    def iter_errors(self, instance: Any):
        if not isinstance(instance, dict):
            return
        req = self.schema.get("required", [])
        for r in req:
            if r not in instance:
                yield _MockValidationError("required", f"'{r}' is a required property", [r])
        if self.schema.get("additionalProperties") is False:
            allowed = set(self.schema.get("properties", {}).keys())
            for k in instance.keys():
                if k not in allowed:
                    yield _MockValidationError("additionalProperties", f"Additional properties are not allowed ('{k}' was unexpected)", [k])
        props = self.schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                pdef = props[k]
                if "enum" in pdef and v is not None and v not in pdef["enum"]:
                    yield _MockValidationError("enum", f"'{v}' is not one of {pdef['enum']}", [k])


class SyntaxValidator:
    def __init__(self):
        self.format_checker = FormatChecker() if FormatChecker else None
        if self.format_checker:
            self._register_custom_formats()
        self._validator_cache: Dict[int, Any] = {}

    def _register_custom_formats(self) -> None:
        @self.format_checker.checks("date")
        def _check_date(val: Any) -> bool:
            if not isinstance(val, str):
                return True
            if not DATE_ONLY_PATTERN.match(val):
                return False
            try:
                datetime.strptime(val, "%Y-%m-%d")
                return True
            except ValueError:
                return False

        @self.format_checker.checks("date-time")
        def _check_datetime(val: Any) -> bool:
            if not isinstance(val, str):
                return True
            if RAW_UTC_PATTERN.match(val):
                return False  # Prohibited UTC 'Z'
            if not TIMEZONE_OFFSET_PATTERN.match(val):
                return False
            try:
                datetime.fromisoformat(val)
                return True
            except ValueError:
                return False

    def parse_frontmatter(self, raw_text: str, path_str: str = "") -> Tuple[bool, Dict[str, Any], str, List[Diagnostic]]:
        """Parses YAML frontmatter delimited by --- at start and end."""
        diagnostics: List[Diagnostic] = []
        if not raw_text.startswith("---"):
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.SYNTAX_MISSING_DELIMITER,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_1_SYNTAX,
                message="File must start with YAML frontmatter delimiter '---'",
                path=path_str,
                recovery_action=RecoveryAction.FIX_REQUEST
            ))
            return False, {}, raw_text, diagnostics

        parts = raw_text.split("---", 2)
        if len(parts) < 3:
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.SYNTAX_UNCLOSED_DELIMITER,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_1_SYNTAX,
                message="Unclosed YAML frontmatter delimiter. Expected terminating '---'",
                path=path_str,
                recovery_action=RecoveryAction.FIX_REQUEST
            ))
            return False, {}, raw_text, diagnostics

        try:
            frontmatter = yaml.safe_load(parts[1])
            if frontmatter is None:
                frontmatter = {}
            elif not isinstance(frontmatter, dict):
                diagnostics.append(Diagnostic(
                    code=DiagnosticCode.SYNTAX_YAML_PARSE_ERROR,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_1_SYNTAX,
                    message=f"YAML frontmatter must deserialize to a mapping/dict, got {type(frontmatter).__name__}",
                    path=path_str,
                    recovery_action=RecoveryAction.FIX_REQUEST
                ))
                return False, {}, parts[2], diagnostics
        except Exception as e:
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.SYNTAX_YAML_PARSE_ERROR,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_1_SYNTAX,
                message=f"YAML parsing error: {e}",
                path=path_str,
                recovery_action=RecoveryAction.FIX_REQUEST
            ))
            return False, {}, parts[2], diagnostics

        body = parts[2].lstrip("\r\n")
        return True, frontmatter, body, diagnostics

    def get_validator(self, schema_dict: Dict[str, Any]) -> Any:
        schema_id = id(schema_dict)
        if schema_id not in self._validator_cache:
            if Draft202012Validator is not None:
                self._validator_cache[schema_id] = Draft202012Validator(
                    schema_dict,
                    format_checker=self.format_checker
                )
            else:
                self._validator_cache[schema_id] = _FallbackValidator(schema_dict)
        return self._validator_cache[schema_id]

    def validate_syntax_and_schema(
        self,
        raw_text: str,
        path_str: str,
        schema_dict: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any], str, List[Diagnostic]]:
        """Parses delimiter/YAML and validates against Draft 2020-12 schema."""
        parsed_ok, frontmatter, body, diagnostics = self.parse_frontmatter(raw_text, path_str)
        if not parsed_ok:
            return False, frontmatter, body, diagnostics

        # Check explicit local timezone on any string fields
        def _check_tz_in_obj(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    current_path = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, str):
                        if RAW_UTC_PATTERN.match(v):
                            diagnostics.append(Diagnostic(
                                code=DiagnosticCode.FORMAT_INVALID,
                                severity=DiagnosticSeverity.ERROR,
                                layer=ValidationLayer.LAYER_1_SYNTAX,
                                message=f"Field '{current_path}' contains raw UTC 'Z' string '{v}'. Explicit local offset required (e.g. -05:00).",
                                field=current_path,
                                path=path_str,
                                recovery_action=RecoveryAction.FIX_REQUEST
                            ))
                    elif isinstance(v, (dict, list)):
                        _check_tz_in_obj(v, current_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    current_path = f"{prefix}[{idx}]"
                    _check_tz_in_obj(item, current_path)

        _check_tz_in_obj(frontmatter)

        # Validate against JSON Schema Draft 2020-12 if schema provided
        if schema_dict:
            validator = self.get_validator(schema_dict)
            for err in validator.iter_errors(frontmatter):
                val_name = err.validator or "violation"
                # Snake case translation: e.g. additionalProperties -> schema_additional_properties
                snake_code = f"schema_{re.sub(r'(?<!^)(?=[A-Z])', '_', val_name).lower()}"
                
                # Format specific code
                if val_name == "format":
                    snake_code = DiagnosticCode.SCHEMA_FORMAT.value
                elif val_name == "required":
                    snake_code = DiagnosticCode.SCHEMA_REQUIRED.value
                elif val_name == "additionalProperties":
                    snake_code = DiagnosticCode.SCHEMA_ADDITIONAL_PROPERTIES.value
                elif val_name == "enum":
                    snake_code = DiagnosticCode.SCHEMA_ENUM.value

                field_name = ".".join([str(p) for p in err.path]) if err.path else None
                if val_name == "additionalProperties":
                    # Extract the extra property name from error message or context
                    match = re.search(r"Additional properties are not allowed \('([^']+)'", err.message)
                    if match:
                        extra_prop = match.group(1)
                        field_name = f"{field_name}.{extra_prop}" if field_name else extra_prop
                    elif not field_name and err.validator_value is False and len(err.path) == 0:
                        # Find which property wasn't in schema properties
                        schema_props = set(schema_dict.get("properties", {}).keys())
                        for k in frontmatter.keys():
                            if k not in schema_props:
                                field_name = k
                                break

                diagnostics.append(Diagnostic(
                    code=snake_code,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_1_SYNTAX,
                    message=err.message,
                    field=field_name,
                    path=path_str,
                    recovery_action=RecoveryAction.FIX_REQUEST
                ))

        is_valid = len([d for d in diagnostics if str(d.severity).lower() == "error"]) == 0
        return is_valid, frontmatter, body, diagnostics

    def validate_record(
        self,
        path: Union[str, Path],
        record_text: str,
        schema_dict: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        path_str = str(path)
        valid, fm, body, diags = self.validate_syntax_and_schema(record_text, path_str, schema_dict)
        return ValidationResult(
            valid=valid,
            diagnostics=diags,
            frontmatter=fm,
            body=body,
            path=Path(path) if path else None
        )
