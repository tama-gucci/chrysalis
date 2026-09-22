"""
tests/harness/engine_validator.py
Layer 2 Validator: mdbase v0.3 Collection Engine Capabilities & Conformance.
"""
import contextlib
from fnmatch import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import yaml

from .models import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    RecoveryAction,
    ValidationLayer,
)


class EngineValidator:
    def __init__(self, collection_dir: Union[str, Path]):
        self.collection_dir = Path(collection_dir)
        self.config: Dict[str, Any] = {}
        self.types: Dict[str, Dict[str, Any]] = {}
        self.type_schemas: Dict[str, Dict[str, Any]] = {}

    def load_and_validate_manifest(self) -> List[Diagnostic]:
        """Loads and validates mdbase.yaml against mdbase v0.3 collection spec."""
        diagnostics: List[Diagnostic] = []
        manifest_path = self.collection_dir / "mdbase.yaml"
        if not manifest_path.is_file():
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.COLLECTION_MANIFEST_MISSING,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_2_ENGINE,
                message=f"Missing collection root manifest: {manifest_path}",
                path=str(manifest_path),
                recovery_action=RecoveryAction.REPAIR_COLLECTION
            ))
            return diagnostics

        try:
            raw_text = manifest_path.read_text(encoding="utf-8")
            self.config = yaml.safe_load(raw_text) or {}
        except Exception as e:
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.COLLECTION_MANIFEST_CORRUPT,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_2_ENGINE,
                message=f"Failed to parse mdbase.yaml: {e}",
                path=str(manifest_path),
                recovery_action=RecoveryAction.REPAIR_COLLECTION
            ))
            return diagnostics

        if self.config.get("spec_version") != "0.3.0":
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.COLLECTION_VERSION_UNSUPPORTED,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_2_ENGINE,
                message=f"Unsupported spec_version: '{self.config.get('spec_version')}'. Expected '0.3.0'.",
                field="spec_version",
                path=str(manifest_path),
                recovery_action=RecoveryAction.REPAIR_COLLECTION
            ))

        return diagnostics

    def load_types(self) -> List[Diagnostic]:
        """Discovers and parses type definitions in _types/ folder."""
        diagnostics: List[Diagnostic] = []
        types_rel = self.config.get("settings", {}).get("types_folder", "_types")
        types_dir = self.collection_dir / types_rel
        if not types_dir.is_dir():
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.TYPES_FOLDER_MISSING,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_2_ENGINE,
                message=f"Types folder not found at {types_dir}",
                path=str(types_dir),
                recovery_action=RecoveryAction.REPAIR_COLLECTION
            ))
            return diagnostics

        for f in sorted(types_dir.glob("*.md")):
            try:
                parts = f.read_text(encoding="utf-8").split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1]) or {}
                    if fm.get("kind") == "mdbase.type" and "name" in fm:
                        name = fm["name"]
                        self.types[name] = fm
                        schema_val = fm.get("schema", {}).get("value", {})
                        self.type_schemas[name] = schema_val
            except Exception as e:
                diagnostics.append(Diagnostic(
                    code=DiagnosticCode.TYPE_DEFINITION_CORRUPT,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_2_ENGINE,
                    message=f"Error reading type definition {f}: {e}",
                    path=str(f),
                    recovery_action=RecoveryAction.REPAIR_COLLECTION
                ))

        for required_type in ["task", "project", "zettel", "source"]:
            if required_type not in self.types:
                diagnostics.append(Diagnostic(
                    code=DiagnosticCode.REQUIRED_TYPE_MISSING,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_2_ENGINE,
                    message=f"Authoritative type '{required_type}' is missing from _types/",
                    path=str(types_dir),
                    recovery_action=RecoveryAction.REPAIR_COLLECTION
                ))

        return diagnostics

    def resolve_type_for_path(self, rel_path: str, frontmatter: Dict[str, Any]) -> Optional[str]:
        """Resolves record type based on explicit frontmatter tag or path glob match."""
        explicit_type = frontmatter.get("type")
        if explicit_type == "project_roadmap":
            explicit_type = "project"
        if explicit_type in self.types:
            return explicit_type

        norm_path = rel_path.replace("\\", "/")
        # Match against type path_globs
        for name, t_def in self.types.items():
            glob_pattern = t_def.get("match", {}).get("path_glob")
            if glob_pattern:
                if fnmatch(norm_path, glob_pattern) or fnmatch(norm_path, f"*/{glob_pattern}"):
                    return name

        # Well-known path heuristics
        if "TaskNotes/Tasks" in norm_path or "chrysalis/Tasks" in norm_path or "chrysalis/TaskNotes/Tasks" in norm_path or "Tasks/" in norm_path or norm_path.startswith("Tasks/"):
            return "task"
        if "Projects" in norm_path and norm_path.endswith("Roadmap.md"):
            return "project"
        if "Slipbox" in norm_path:
            return "zettel"
        if "Sources" in norm_path:
            return "source"

        return None

    def validate_collection_uniqueness(
        self,
        records: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Diagnostic]:
        """Validates collection uniqueness constraints (project_id, id, sha256)."""
        diagnostics: List[Diagnostic] = []
        seen_projects: Dict[str, str] = {}
        seen_zettels: Dict[str, str] = {}
        seen_sources: Dict[str, str] = {}
        seen_checksums: Dict[str, str] = {}

        for rel_path, fm in records:
            norm_path = rel_path.replace("\\", "/")
            t = fm.get("type")
            if t == "project_roadmap":
                t = "project"

            # 1. Project ID uniqueness
            if t == "project":
                pid = fm.get("project_id")
                if pid:
                    if pid in seen_projects:
                        diagnostics.append(Diagnostic(
                            code=DiagnosticCode.UNIQUE_CONSTRAINT_VIOLATION,
                            severity=DiagnosticSeverity.ERROR,
                            layer=ValidationLayer.LAYER_2_ENGINE,
                            message=f"Duplicate project_id '{pid}' in {norm_path} (already declared in {seen_projects[pid]})",
                            field="project_id",
                            path=norm_path,
                            recovery_action=RecoveryAction.RESOLVE_CONFLICT
                        ))
                    else:
                        seen_projects[pid] = norm_path

            # 2. Zettel ID uniqueness
            elif t == "zettel":
                zid = fm.get("id")
                if zid:
                    if zid in seen_zettels:
                        diagnostics.append(Diagnostic(
                            code=DiagnosticCode.UNIQUE_CONSTRAINT_VIOLATION,
                            severity=DiagnosticSeverity.ERROR,
                            layer=ValidationLayer.LAYER_2_ENGINE,
                            message=f"Duplicate zettel id '{zid}' in {norm_path} (already declared in {seen_zettels[zid]})",
                            field="id",
                            path=norm_path,
                            recovery_action=RecoveryAction.RESOLVE_CONFLICT
                        ))
                    else:
                        seen_zettels[zid] = norm_path

            # 3. Source ID and SHA-256 uniqueness
            elif t == "source":
                sid = fm.get("id")
                if sid:
                    if sid in seen_sources:
                        diagnostics.append(Diagnostic(
                            code=DiagnosticCode.UNIQUE_CONSTRAINT_VIOLATION,
                            severity=DiagnosticSeverity.ERROR,
                            layer=ValidationLayer.LAYER_2_ENGINE,
                            message=f"Duplicate source id '{sid}' in {norm_path} (already declared in {seen_sources[sid]})",
                            field="id",
                            path=norm_path,
                            recovery_action=RecoveryAction.RESOLVE_CONFLICT
                        ))
                    else:
                        seen_sources[sid] = norm_path

                sha = fm.get("sha256")
                if sha:
                    sha_lower = sha.lower()
                    if sha_lower in seen_checksums:
                        diagnostics.append(Diagnostic(
                            code=DiagnosticCode.DUPLICATE_SOURCE_DETECTED,
                            severity=DiagnosticSeverity.ERROR,
                            layer=ValidationLayer.LAYER_2_ENGINE,
                            message=f"Duplicate source sha256 checksum '{sha}' in {norm_path} (matches {seen_checksums[sha_lower]})",
                            field="sha256",
                            path=norm_path,
                            recovery_action=RecoveryAction.RESOLVE_CONFLICT
                        ))
                    else:
                        seen_checksums[sha_lower] = norm_path

        return diagnostics

    @staticmethod
    def compute_revision(document_bytes: bytes) -> str:
        """Computes exact-document v1 revision: 64 lowercase hex sha256."""
        return hashlib.sha256(document_bytes).hexdigest().lower()
