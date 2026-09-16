# Testing

Run checks from `vault-git/`. All fixtures must be synthetic and temporary; never use the personal runtime as a test fixture.

## One local check command

From the source checkout, run:

```bash
python3 Development/scripts/check.py
```

This runs candidate privacy checks, pinned dependency checks, the complete framework and gateway suites, Flutter analysis/tests, and the standalone storage regression. Every check has a named PASS/FAIL result and a separate log. The final result is nonzero if any required check fails, times out, cannot start, or the candidate changes during the run. Privacy/preflight failures stop before candidate test execution. Application test failures do not suppress the remaining check results.

A private temporary directory holds `report.json` and logs. The command prints its location. The report includes working/index fingerprints, the starting commit, results and explicit local-offset timestamps. Logs can contain local paths; do not commit them. There are no skip-check flags. A passing local report is validation evidence, not permission to merge, publish or deploy.

### Set up a fresh development checkout

The verified environment is Linux x86_64, Python 3.14 (tested 3.14.7), Flutter 3.47.2 with bundled Dart 3.13.2, and the native dependencies in [the workstation guide](WORKSTATION-SETUP.md). Keep the existing mobile `pubspec.lock`; setup enforces it. `Development/requirements.lock` pins the complete tested Python environment, including transitive packages. Refresh dependency pins through a reviewed change and fresh validation, not an automatic upgrade during checks.

Install the OS tools and Flutter SDK first. Then, in each independent checkout:

```bash
bash Development/scripts/setup-dev.sh --mobile
python3 Development/scripts/check.py
```

Setup resolves Flutter from `FLUTTER_ROOT`, PATH, or that checkout's ignored Android `local.properties`. If discovery fails, set `FLUTTER_ROOT` to your installed SDK directory; do not commit it. The setup command creates this checkout's `.venv`, installs the pinned packages and resolves the locked mobile dependencies. Internet access/package caches and Flutter cache write access may be needed. It never initializes a personal vault. Checks reject personal runtime environment overrides.

The existing Android toolchain remains necessary for APK/device checks, which are separate from this local command. Hosted GitHub checks have not been implemented or exercised and remain pending.

### Trusted checks before integration

For future integration, keep a separate checkout of an explicitly reviewed checker revision outside the candidate working folder. Run its controller, passing the candidate directory:

```bash
python3 trusted-source/Development/scripts/check.py --candidate candidate-source
```

Both paths above are examples relative to the workspace. The controller's required check list and privacy implementation come from `trusted-source`, regardless of candidate instruction edits. Changes to its protected checker/setup/audit/lock files are refused in the candidate until the trusted policy is separately reviewed and updated. Removing a baseline test file also fails. The checker never commits or integrates anything. B02 must bind its integration decision to this external controller's result and exact candidate identity; it must not execute a candidate-provided replacement checker or accept a candidate's claimed PASS.

Use the local command while developing the checker itself, then independently review the policy change before selecting it as a trusted revision. This boundary prevents a candidate from quietly removing required checks; it is not an OS security sandbox against hostile programs running under the same account. Review remains required for test changes and generated artifacts.

### Candidate privacy contract

`bash Development/scripts/pii-scanner.sh` is the compatibility entry point for the Python candidate audit. It inspects both the actual staged blobs and tracked/eligible-untracked working files without modifying the Git index. Partial staging cannot hide a staged secret behind a clean working file. Unresolved Git entries and symlinks fail closed. Quarantined paths, Unix/Windows user paths, token patterns, private calendar/task references and non-placeholder emails fail with a file/line diagnostic that does not echo the offending value.

Reserved example domains are allowed. Exact preserved upstream plugin artifacts (including public author attribution) are bound to their path and SHA-256; any change requires new provenance review. New JS/CSS files are scanned, not blanket-exempted. Recognized PNG/ICO assets are excluded from text scans, and other unknown binaries fail. Mobile asset scale filenames and the updater's SSH transport string have narrowly scoped non-email exceptions. Ignore rules are evaluated separately for each candidate view, without global Git excludes, with representative private-path probes. Human inspection supplements these finite pattern checks.

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

A lightweight local-storage regression check can run without Flutter native test assets. From `apps/mobile/`:

```powershell
dart --packages=.dart_tool/package_config.json test/data/local_vault_initialization_check.dart
```

See [mobile USB testing](../apps/mobile/README.md#test-the-gateway-over-usb) for physical-device gateway tests. A successful command round trip does not establish task synchronization or working agent execution.

## Before publishing

Run `/audit-dev`, including `bash Development/scripts/pii-scanner.sh`, and review the staged diff and newly added files. Plugin settings, private notes, caches, and deployment history must remain untracked.

Record dated results and limitations in [STATUS.md](../STATUS.md). Generated reports and caches are disposable; source tests and private rollback snapshots are retained.
