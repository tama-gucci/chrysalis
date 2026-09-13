# Development roadmap

Implementation status lives in [STATUS.md](../STATUS.md). This roadmap describes outstanding work in dependency order.

## 1. Near-term: Prove the personal daily-use workflow

- Exercise capture on a physical phone and verify the destination file.
- Establish an explicit supported route from phone-local files to the shared vault.
- Enable the dashboard dependencies and rehearse offline Obsidian use.
- Prove one complete input → useful note/task → plan → completion cycle.
- Add document/transcript ingestion with deduplication and reviewable output.

## 2. Mid-term: Finish integrations

- Configure authenticated mobile Drive sync and conflict handling.
- Implement the Android calendar handler; connect it to task changes and verify event lifecycle on a device.
- Validate real gateway execution against the installed orchestrator CLI and selected vault.
- Implement a mailbox consumer with acknowledgments and duplicate-execution protection.
- Finish user-controlled Health Connect permission onboarding and verify real telemetry.

## 3. Package the usable core

- Establish maintainable standalone Obsidian plugin source, license/provenance records, and release builds.
- Package the gateway for Windows with explicit local configuration and service lifecycle controls.
- Add release/version manifests, APK signing, reproducible builds, and upgrade rehearsal.

## 4. Long-term: Expand only after the core workflow is proven

- Direct cloud or on-device intelligence adapters.
- Wear OS interface and voice capture.
- Secure pairing and multi-device profiles.
- Evening triage interface and richer knowledge previews.
- Semantic linking and carefully reviewed self-improvement.

## Capability horizons

| Horizon | Planned capability | Dependency |
| --- | --- | --- |
| Near-term | Task micro-chunking / Starter Wedge refinement | Real daily-use feedback |
| Mid-term | Cross-agent telemetry and chronotype calibration | Verified execution and permission-based telemetry |
| Mid-term | Multi-workstation synchronization | Authenticated storage and conflict handling |
| Long-term | Semantic synthesis and self-improvement | Stable data and reviewable proposals |
