# Verification

Create Python/pytest environments outside source. Point `TMP`, `TEMP`, `TMPDIR` and
pytest's basetemp to external scratch. Set `PYTHONDONTWRITEBYTECODE=1`. Run:

```text
python -B -m pytest -q -p no:cacheprovider --basetemp <external-scratch>/pytest
python -B Development/scripts/check.py
python -B Development/scripts/agent_context.py show
```

The retained suite checks exact approval, raw revisions, editor conflicts, missing validation
in a fresh process, plugin/Calendar preservation, planning, learning, pauses, checkpoints,
horizons, reconciliation, knowledge links, ingestion, originals/relocation, provider policies
and package failure recovery.

The checker scans all non-Git working-tree files, including ignored/untracked content. It rejects
private/generated locations and redirects, parses Python/YAML, checks local Markdown links and
skill references. Review prose and findings too: automated scans cannot prove that arbitrary
prose contains no personal fact.

Native acceptance uses external isolated profiles and the shipped package. Verify actual loading,
registered tool calls and denied bypasses. A synthetic assistant call through the real pipeline
tests transport/policy without asserting model behavior. Preserve pinned versions and logs privately.

Authenticated integrations, TaskNotes rendering/sync, OCR/vision, streamed storage, mobile and
model learning each need separate acceptance. See `STATUS.md`.
