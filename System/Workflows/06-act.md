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
Enforce human authorization barrier, verify CAS concurrency hashes via the A2 access layer (`helpers/mdbase_helper.py`), and atomically commit mutations to the resolved local runtime vault (`<vault>`).

## Protocol Steps
1. **Approval Verification**:
   - Verify `context.approval_token == proposal_id`.
   - If token is missing or mismatched: abort write immediately with `approval_required`. Zero bytes written to disk.
2. **CAS Precondition Verification (`helpers/mdbase_helper.py`)**:
   - For each target file being updated or deleted in `<vault>`:
     - Compute `disk_revision` via `python helpers/mdbase_helper.py --vault "<vault>" revision <path>` (`sha256(file_path.read_bytes())`).
     - Assert `if_revision.lower() == disk_revision.lower()`.
     - On mismatch: Abort immediately with `concurrent_modification` and `recovery_action: "Refresh"`.
3. **Write Execution & Schema Validation (A2 Access Layer)**:
   - Apply write-time lifecycle hooks (`lifecycle.on_create`, `lifecycle.on_update`).
   - Validate frontmatter against JSON Schema 2020-12 dialect (`additionalProperties: false`) using `python helpers/mdbase_helper.py --vault "<vault>" validate <path>` or `helpers.mdbase_helper.apply_cas_mutation()`.
   - Execute physical disk mutation via `helpers.mdbase_helper.apply_cas_mutation()` or the active local agent's native file tools (`replace_file_content` / `write_to_file` / `apply_patch`), followed by `python helpers/mdbase_helper.py --vault "<vault>" validate <path>`:
     ```python
     temp_path = target_path.with_suffix(f".tmp.{uuid4().hex}")
     temp_path.write_text(content, encoding="utf-8")
     os.replace(temp_path, target_path)
     ```
4. **State Transition**: Transition to `07-record-outcomes.md`.
