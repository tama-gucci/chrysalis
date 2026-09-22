"""
tests/harness/workflow_validator.py
Layer 3 Agent Runtime State Machine & Invariant Validator.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .models import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    RecoveryAction,
    ValidationLayer,
)

VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "INITIALIZE": {"CONTEXT_ASSEMBLY"},
    "CONTEXT_ASSEMBLY": {"MEMORY_RETRIEVAL", "CONTINUATION"},
    "MEMORY_RETRIEVAL": {"PLAN_PROPOSAL"},
    "PLAN_PROPOSAL": {"APPROVAL_GATE", "CONTINUATION"},
    "APPROVAL_GATE": {"ACT", "PLAN_PROPOSAL", "CONTINUATION"},
    "ACT": {"OUTCOME_RECORDING", "PLAN_PROPOSAL"},
    "OUTCOME_RECORDING": {"CONTINUATION"},
    "CONTINUATION": set(),
}

READ_ONLY_ACTIONS: Set[str] = {
    "read_record",
    "query_records",
    "propose_plan",
    "get_schema",
    "inspect_provenance",
}


class WorkflowValidator:
    def validate_transition(self, current_state: str, next_state: str) -> Optional[Diagnostic]:
        """Validates state machine transitions against agent-runtime.contract.md Section 2."""
        c_state = current_state.upper()
        n_state = next_state.upper()

        if c_state not in VALID_TRANSITIONS:
            return Diagnostic(
                code=DiagnosticCode.WORKFLOW_INVALID_STATE,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                message=f"Unknown lifecycle state '{current_state}'",
                recovery_action=RecoveryAction.FIX_REQUEST
            )

        if n_state not in VALID_TRANSITIONS[c_state]:
            return Diagnostic(
                code=DiagnosticCode.WORKFLOW_ILLEGAL_TRANSITION,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                message=f"Illegal state transition from '{current_state}' to '{next_state}'",
                recovery_action=RecoveryAction.FIX_REQUEST
            )

        return None

    def validate_approval_gate(
        self,
        proposal_id: str,
        approval_token: Optional[str],
        action: str
    ) -> Optional[Diagnostic]:
        """Enforces Human Approval Gate invariant before physical disk mutation."""
        if action in READ_ONLY_ACTIONS:
            return None

        if not approval_token or approval_token != proposal_id:
            return Diagnostic(
                code=DiagnosticCode.APPROVAL_REQUIRED,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                message=(
                    f"Action '{action}' requires user approval. Expected token '{proposal_id}', "
                    f"received '{approval_token}'. Zero bytes written to disk."
                ),
                field="context.approval_token",
                recovery_action=RecoveryAction.FIX_REQUEST
            )
        return None

    def validate_anti_simulation(
        self,
        claimed_path: Union[str, Path],
        expected_bytes: Optional[bytes] = None
    ) -> Optional[Diagnostic]:
        """Verifies that claimed mutations physically exist on disk (Anti-Simulation Law)."""
        target = Path(claimed_path)
        if not target.is_file():
            return Diagnostic(
                code=DiagnosticCode.ANTI_SIMULATION_VIOLATION,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                message=f"Anti-simulation breach: Claimed file '{claimed_path}' does not exist on physical disk.",
                path=str(claimed_path),
                recovery_action=RecoveryAction.FIX_REQUEST
            )

        if expected_bytes is not None:
            actual_bytes = target.read_bytes()
            if actual_bytes != expected_bytes:
                return Diagnostic(
                    code=DiagnosticCode.ANTI_SIMULATION_VIOLATION,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_3_FRAMEWORK,
                    message=f"Anti-simulation breach: File bytes on disk do not match claimed content in '{claimed_path}'.",
                    path=str(claimed_path),
                    recovery_action=RecoveryAction.REFRESH
                )

        return None

    def validate_passive_text_quarantine(self, body_text: str, source_id: str = "") -> List[Diagnostic]:
        """Verifies that untrusted external payloads are quarantined and delimited."""
        diagnostics: List[Diagnostic] = []
        if "<untrusted_document_payload" not in body_text:
            diagnostics.append(Diagnostic(
                code=DiagnosticCode.UNTRUSTED_PAYLOAD_UNQUARANTINED,
                severity=DiagnosticSeverity.ERROR,
                layer=ValidationLayer.LAYER_3_FRAMEWORK,
                message=f"Untrusted payload in source '{source_id}' is not wrapped in <untrusted_document_payload>",
                recovery_action=RecoveryAction.FIX_REQUEST
            ))

        # Check for unescaped closing tags inside the payload body
        if "<untrusted_document_payload" in body_text:
            inner_segment = body_text.split("<untrusted_document_payload", 1)[1]
            # If there is a genuine closing tag, count closing tags
            tag_count = inner_segment.count("</untrusted_document_payload>")
            if tag_count > 1:
                diagnostics.append(Diagnostic(
                    code=DiagnosticCode.UNTRUSTED_PAYLOAD_DELIMITER_ESCAPE,
                    severity=DiagnosticSeverity.ERROR,
                    layer=ValidationLayer.LAYER_3_FRAMEWORK,
                    message="Unescaped closing </untrusted_document_payload> found in body text",
                    recovery_action=RecoveryAction.FIX_REQUEST
                ))

        return diagnostics
