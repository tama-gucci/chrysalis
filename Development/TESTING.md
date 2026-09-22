# Testing

Run checks from the selected local source repository root. All fixtures must be synthetic and temporary; never use the personal runtime vault as a test fixture.

## 1. Primary Framework Test Suite (mdbase v0.3)

The Chrysalis AI Agent Framework is validated through an extensive, multi-tier automated test suite:

### A. Full Pytest Suite (Authoritative)
Runs all unit, contract, integration, and scenario tests:

```bash
.venv/bin/pytest tests/
```

This suite covers:
- **Layer 1 (Syntax & Schemas)**: `_types/*.md` conformance to JSON Schema Draft 2020-12, RFC 3339 timestamp offsets (`"-05:00"`), and rejection of unknown fields.
- **Layer 2 (mdbase v0.3 Engine)**: Collection indexing, `mdbase.yaml` manifests, atomic CAS concurrency (`if_revision`), advisory locking (`fcntl.flock`), temporary file replacement (`os.replace`), and semantic deduplication.
- **Layer 3 (Framework Workflows & Security)**: Provider-independent 8-stage agent lifecycle (`contracts/agent-runtime.contract.md`), 14-day cognitive planning horizon, passive untrusted text defense (`<untrusted_document_payload>` quarantine and delimiter escaping), tripartite hypergraph linking (`Slipbox/` $\leftrightarrow$ `Projects/` $\leftrightarrow$ `chrysalis/TaskNotes/Tasks/`), worked end-to-end scenario (`tests/test_worked_scenario.py`), and 6 critical failure mode tests (`tests/test_failure_modes.py`).

### B. Standalone 3-Layer Validation Harness
A zero-cloud-dependency validation harness verifying the collection and hypergraph:

```bash
python3 tests/harness/validation_harness.py -c .
```

Returns exit code 0 when all Layer 1, Layer 2, and Layer 3 constraints pass.

### C. Zero-Leak PII Privacy Audits
Enforces the constitutional Zero-Leak PII Law:

```bash
python3 Development/scripts/candidate_audit.py
bash Development/scripts/pii-scanner.sh
```

Inspects both staged Git index blobs and untracked/working files. Fails closed if any quarantined paths, personal usernames, machine-bound paths, private tasks, or non-synthetic emails are detected.

---

## 2. Setting Up a Development Checkout

The verified environment is Linux x86_64, Python 3.14 (tested 3.14.7), Git, Bash, and ripgrep. `Development/requirements.lock` pins the complete tested Python environment.

In each independent checkout or worktree:

```bash
bash Development/scripts/setup-dev.sh
.venv/bin/pytest tests/
```

Setup creates this checkout's `.venv` and installs declared dependencies. It never touches or initializes a personal vault.

---

## 3. Local Check Controller (`check.py`)

From the source checkout, you can run the unified multi-check runner:

```bash
python3 Development/scripts/check.py
```

This runs candidate privacy checks, pinned dependency checks, the framework suite, and historical baseline regression tests. Every check has a named PASS/FAIL result and a separate log in `/tmp/chrysalis-check-*/`.

---

## 4. Retired Historical Prototypes (`apps/gateway/` & `apps/mobile/`)

The bespoke Flutter mobile application (`apps/mobile/`) and FastAPI daemon (`apps/gateway/`) have been **formally retired**. The core framework operates directly on local Markdown files without daemon processes or custom mobile clients.

Their code and tests remain in `apps/` solely for historical regression verification:
- Gateway test suite: `.venv/bin/pytest apps/gateway/tests/test_gateway.py -q`
- Mobile test suite: `cd apps/mobile && flutter test` (requires optional Flutter SDK toolchain)

These legacy components are not required for framework development, runtime agent execution, or vault deployment.

---

## 5. Before Publishing or Handing Off

Before committing changes or concluding an engineering session:
1. Run `.venv/bin/pytest tests/` and verify all tests pass.
2. Run `python3 tests/harness/validation_harness.py -c .` and verify Layer 1-3 pass.
3. Run `python3 Development/scripts/candidate_audit.py` and `bash Development/scripts/pii-scanner.sh` and verify 0 findings.
4. Update `Development/HANDOFF.md` with dated receipts, exact diff summary, and concrete next steps.
