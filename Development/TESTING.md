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

This runs candidate privacy checks, pinned dependency checks, the framework suite, and mdbase Layer 1-3 validation. Every check has a named PASS/FAIL result and a separate log in `/tmp/chrysalis-check-*/`.

---

## 4. Retired Historical Prototypes (`archive/deprecated-apps`)

The bespoke Flutter mobile application (`apps/mobile/`) and FastAPI daemon (`apps/gateway/`) have been **formally retired and archived** to the `archive/deprecated-apps` git branch. The `main` branch contains strictly what is required to run the redesigned mdbase v0.3 Chrysalis AI agent framework.

The core framework operates directly on local Markdown files without daemon processes or custom mobile clients. Mobile and desktop interaction is provided natively by Obsidian with the community TaskNotes plugin, Google Calendar synchronization, and candidate AI runtime agents (Gemini Spark, Google Antigravity, local LLMs).

If historical inspection of the retired Flutter or FastAPI prototypes is ever needed, check out the remote branch:
```bash
git fetch origin archive/deprecated-apps
git checkout archive/deprecated-apps
```

---

## 5. Before Publishing or Handing Off

Before committing changes or concluding an engineering session:
1. Run `.venv/bin/pytest tests/` and verify all tests pass.
2. Run `python3 tests/harness/validation_harness.py -c .` and verify Layer 1-3 pass.
3. Run `python3 Development/scripts/candidate_audit.py` and `bash Development/scripts/pii-scanner.sh` and verify 0 findings.
4. Update `Development/HANDOFF.md` with dated receipts, exact diff summary, and concrete next steps.
