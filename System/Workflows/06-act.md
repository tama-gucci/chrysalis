---
type: agent_workflow
id: workflow-06-act
version: "1.0.0"
stage: act
lifecycle_state_ref: ACT
requires_approval: true
inputs:
  - proposal_id
  - approval_token
  - mutations_list
outputs:
  - mutations_result
  - resulting_revisions
---

# Workflow 06: Approval Gate & Compare-And-Swap Mutation

## Objective
Enforce human authorization barrier, verify CAS concurrency hashes, and atomically commit mutations to physical disk.

## Protocol Steps
1. **Approval Verification**:
   - Verify `context.approval_token == proposal_id`.
   - If token is missing or mismatched: abort write immediately with `approval_required`. Zero bytes written to disk.
2. **CAS Precondition Verification**:
   - For each target file being updated or deleted:
     - Read disk bytes: `bytes_on_disk = file_path.read_bytes()`.
     - Calculate `disk_revision = sha256(bytes_on_disk)`.
     - Assert `if_revision.lower() == disk_revision.lower()`.
     - On mismatch: Abort immediately with `concurrent_modification` and `recovery_action: "Refresh"`.
3. **Write Execution**:
   - Apply write-time lifecycle hooks (`lifecycle.on_create`, `lifecycle.on_update`).
   - Validate frontmatter against JSON Schema 2020-12 dialect (`additionalProperties: false`).
   - Execute atomic write via sibling temporary file:
     ```python
     temp_path = target_path.with_suffix(f".tmp.{uuid4().hex}")
     temp_path.write_text(content, encoding="utf-8")
     os.replace(temp_path, target_path)
     ```
4. **State Transition**: Transition to `07-record-outcomes.md`.
