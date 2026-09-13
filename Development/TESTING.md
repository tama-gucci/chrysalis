# Testing

Run checks from `vault-git/`. All fixtures must be synthetic and temporary; never use the personal runtime as a test fixture.

## Framework

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -t . -s tests
```

The suite covers calendar parsing, migration, linking, deployment preservation and rollback, and four legacy integration tiers: features, boundaries, interactions, and scenarios. Older test identifiers F1–F9 refer to historical requirements; current contracts are [ARCHITECTURE.md](../ARCHITECTURE.md), [STATUS.md](../STATUS.md), and the constitutions.

## Gateway and mobile

Install `apps/gateway/requirements.txt` in an isolated environment, then run:

```powershell
python -m pytest apps/gateway/tests -q
```

From `apps/mobile/`, run `flutter analyze` and `flutter test`. Native dependencies require a supported local compiler toolchain. Tests and builds do not establish physical-device integration; capture, synchronization, permissions, and calendar lifecycle still need device rehearsal.

## Before publishing

Run `/audit-dev`, including `bash Development/scripts/pii-scanner.sh`, and review the staged diff and newly added files. Plugin settings, private notes, caches, and deployment history must remain untracked.

Record dated results and limitations in [STATUS.md](../STATUS.md). Generated reports and caches are disposable; source tests and private rollback snapshots are retained.
