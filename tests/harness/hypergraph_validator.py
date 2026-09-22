"""
tests/harness/hypergraph_validator.py
Layer 3 Hypergraph Link Integrity & Cross-Reference Validation Engine.
"""
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .models import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    LinkEdge,
    RecoveryAction,
    ValidationLayer,
)

WIKILINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")


class HypergraphValidator:
    def __init__(self, collection_dir: Union[str, Path]):
        self.collection_dir = Path(collection_dir)
        self.records_by_path: Dict[str, Dict[str, Any]] = {}
        self.records_by_id: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self.sources_by_sha256: Dict[str, Tuple[str, Dict[str, Any]]] = {}

    def index_records(self, records: List[Tuple[str, Dict[str, Any]]]) -> None:
        """Indexes all valid records in the collection for hypergraph link traversal."""
        self.records_by_path.clear()
        self.records_by_id.clear()
        self.sources_by_sha256.clear()

        for rel_path, fm in records:
            norm_path = rel_path.replace("\\", "/")
            self.records_by_path[norm_path] = fm

            # Index by project_id or id
            rid = fm.get("project_id") or fm.get("id")
            if rid:
                self.records_by_id[str(rid)] = (norm_path, fm)

            # Index sources by sha256
            rec_type = fm.get("type")
            if rec_type == "source" and "sha256" in fm and fm["sha256"]:
                self.sources_by_sha256[str(fm["sha256"]).lower()] = (norm_path, fm)

    def extract_links(self, rel_path: str, fm: Dict[str, Any]) -> List[LinkEdge]:
        """Extracts declared hypergraph link edges from record frontmatter."""
        edges: List[LinkEdge] = []
        rec_type = fm.get("type", "unknown")
        if rec_type == "project_roadmap":
            rec_type = "project"

        # 1. Task links
        if rec_type == "task":
            if fm.get("project_ref"):
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="task",
                    target_ref=str(fm["project_ref"]),
                    expected_target_type="project",
                    link_property="project_ref"
                ))
            for z_ref in fm.get("linked_zettels", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="task",
                    target_ref=str(z_ref),
                    expected_target_type="zettel",
                    link_property="linked_zettels"
                ))

        # 2. Project Roadmap links
        elif rec_type == "project":
            if fm.get("source_ref"):
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="project",
                    target_ref=str(fm["source_ref"]),
                    expected_target_type="source",
                    link_property="source_ref"
                ))
            for z_ref in fm.get("linked_zettels", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="project",
                    target_ref=str(z_ref),
                    expected_target_type="zettel",
                    link_property="linked_zettels"
                ))
            for d in fm.get("deliverables", []) or []:
                if isinstance(d, dict) and d.get("task_ref"):
                    edges.append(LinkEdge(
                        source_path=rel_path,
                        source_type="project",
                        target_ref=str(d["task_ref"]),
                        expected_target_type="task",
                        link_property=f"deliverables[{d.get('id', '')}].task_ref"
                    ))

        # 3. Zettel links
        elif rec_type == "zettel":
            if fm.get("project_ref"):
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="zettel",
                    target_ref=str(fm["project_ref"]),
                    expected_target_type="project",
                    link_property="project_ref"
                ))
            if fm.get("source_ref"):
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="zettel",
                    target_ref=str(fm["source_ref"]),
                    expected_target_type="source",
                    link_property="source_ref"
                ))
            for z_ref in fm.get("linked_zettels", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="zettel",
                    target_ref=str(z_ref),
                    expected_target_type="zettel",
                    link_property="linked_zettels"
                ))

        # 4. Source links
        elif rec_type == "source":
            if fm.get("supersedes"):
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="source",
                    target_ref=str(fm["supersedes"]),
                    expected_target_type="source",
                    link_property="supersedes"
                ))
            for p_ref in fm.get("extracted_projects", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="source",
                    target_ref=str(p_ref),
                    expected_target_type="project",
                    link_property="extracted_projects"
                ))
            for z_ref in fm.get("extracted_zettels", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="source",
                    target_ref=str(z_ref),
                    expected_target_type="zettel",
                    link_property="extracted_zettels"
                ))
            for t_ref in fm.get("extracted_tasks", []) or []:
                edges.append(LinkEdge(
                    source_path=rel_path,
                    source_type="source",
                    target_ref=str(t_ref),
                    expected_target_type="task",
                    link_property="extracted_tasks"
                ))

        return edges

    def resolve_target(self, raw_ref: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Resolves raw [[WikiLink]] string to (canonical_path, frontmatter)."""
        clean = raw_ref.strip()
        if clean.startswith("[[") and clean.endswith("]]"):
            clean = clean[2:-2]
        clean = clean.split("#")[0].split("|")[0].strip()

        # 1. Direct path check
        path_candidates = [clean, f"{clean}.md"]
        for cand in path_candidates:
            norm = cand.replace("\\", "/").lstrip("/")
            if norm in self.records_by_path:
                return (norm, self.records_by_path[norm])

        # 2. Match declared ID (project_id or id)
        if clean in self.records_by_id:
            return self.records_by_id[clean]

        # 3. Match filename stem across all indexed paths
        for path_key, fm in self.records_by_path.items():
            stem = Path(path_key).stem
            if stem == clean or stem == clean.split("/")[-1]:
                return (path_key, fm)

        return None

    def validate_links(
        self,
        records: List[Tuple[str, Dict[str, Any]]],
        strict_existence: bool = False
    ) -> List[Diagnostic]:
        """Validates all link edges for existence, target type match, and checksum integrity."""
        diagnostics: List[Diagnostic] = []
        self.index_records(records)

        for rel_path, fm in records:
            edges = self.extract_links(rel_path, fm)
            for edge in edges:
                resolved = self.resolve_target(edge.target_ref)
                if not resolved:
                    severity = DiagnosticSeverity.ERROR if strict_existence else DiagnosticSeverity.WARNING
                    diagnostics.append(Diagnostic(
                        code=DiagnosticCode.LINK_BROKEN,
                        severity=severity,
                        layer=ValidationLayer.LAYER_3_FRAMEWORK,
                        message=f"Dangling link reference '{edge.target_ref}' in {edge.link_property}",
                        field=edge.link_property,
                        path=rel_path,
                        recovery_action=RecoveryAction.FIX_REQUEST
                    ))
                    continue

                target_path, target_fm = resolved
                target_type = target_fm.get("type")
                if target_type == "project_roadmap":
                    target_type = "project"

                # Check expected target type
                if edge.expected_target_type and target_type and target_type != edge.expected_target_type:
                    diagnostics.append(Diagnostic(
                        code=DiagnosticCode.LINK_TARGET_TYPE_MISMATCH,
                        severity=DiagnosticSeverity.ERROR,
                        layer=ValidationLayer.LAYER_3_FRAMEWORK,
                        message=(
                            f"Link '{edge.target_ref}' targets type '{target_type}', "
                            f"but '{edge.expected_target_type}' is required by {edge.link_property}"
                        ),
                        field=edge.link_property,
                        path=rel_path,
                        recovery_action=RecoveryAction.FIX_REQUEST
                    ))

                # Cryptographic Grounding Check: Zettel -> Source SHA-256 Checksum
                if edge.source_type == "zettel" and edge.link_property == "source_ref":
                    zettel_checksum = fm.get("source_checksum")
                    target_sha256 = target_fm.get("sha256")
                    if zettel_checksum and target_sha256:
                        if str(zettel_checksum).lower() != str(target_sha256).lower():
                            diagnostics.append(Diagnostic(
                                code=DiagnosticCode.PROVENANCE_CHECKSUM_MISMATCH,
                                severity=DiagnosticSeverity.ERROR,
                                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                                message=(
                                    f"Cryptographic grounding failure: source_checksum '{zettel_checksum}' "
                                    f"does not match actual source SHA-256 '{target_sha256}' in {target_path}"
                                ),
                                field="source_checksum",
                                path=rel_path,
                                recovery_action=RecoveryAction.REFRESH
                            ))

                # Cryptographic Grounding Check: Project -> Source SHA-256 Checksum
                if edge.source_type == "project" and edge.link_property == "source_ref":
                    project_checksum = fm.get("source_checksum")
                    target_sha256 = target_fm.get("sha256")
                    if project_checksum and target_sha256:
                        if str(project_checksum).lower() != str(target_sha256).lower():
                            diagnostics.append(Diagnostic(
                                code=DiagnosticCode.PROVENANCE_CHECKSUM_MISMATCH,
                                severity=DiagnosticSeverity.ERROR,
                                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                                message=(
                                    f"Cryptographic grounding failure: source_checksum '{project_checksum}' "
                                    f"does not match actual source SHA-256 '{target_sha256}' in {target_path}"
                                ),
                                field="source_checksum",
                                path=rel_path,
                                recovery_action=RecoveryAction.REFRESH
                            ))

        return diagnostics


# Backward compatibility alias
LinkIntegrityValidator = HypergraphValidator
