# 🛰️ Ambient Chrysalis Gateway

> **Status:** 🟡 **Functional Prototype** | **Port:** 8765 | **Architecture:** Windows 11 ARM64/x64  
> The **Ambient Chrysalis Gateway** is a lightweight, asynchronous Python FastAPI daemon engineered to operate 24/7 on your dedicated home hub ("golem" — Microsoft Surface Pro X on Windows 11 ARM64). It exposes high-throughput, low-latency REST and bidirectional WebSocket interfaces bridging the Chrysalis Mobile and Wear OS clients to autonomous agent orchestrators via a **Pluggable Orchestrator Bridge**.

---

## 🏛️ Architecture & Port Separation Invariant

### 1. The Port Separation Invariant (Port 8765 vs Port 8080)
To ensure seamless, collision-free coexistence with the desktop Obsidian environment:
* **Port `8080`:** Reserved exclusively for the **`chrysalis-obsidian` plugin Local REST API & MCP server**.
* **Port `8765`:** Dedicated to the **Ambient Chrysalis Gateway daemon**.
* *Both services run side-by-side on golem with zero port collisions.*

### 2. The Single-Install Invariant (Zero-Phone-Config)
> *The Chrysalis Android app and Wear OS smartwatch must be the ONLY software installed on client devices. No secondary VPN apps (WireGuard/Tailscale), no third-party sync daemons, and no mobile terminal emulators.*

To achieve secure global remote access with zero open inbound router ports:
1. **At-Home Daemon:** The FastAPI gateway runs locally on `0.0.0.0:8765`.
2. **Cloudflare Zero-Trust Tunnel:** An outbound-only tunnel (`cloudflared`) securely exposes the gateway to an encrypted endpoint (e.g. `https://gateway.example.com`).
3. **Client Access:** Chrysalis Mobile and Wear OS make standard HTTPS and WSS requests over TLS using Bearer token authentication.

```
┌───────────────────────────┐       HTTPS / WSS        ┌───────────────────────┐
│ Chrysalis Mobile & Watch  │ ───────────────────────> │ Cloudflare Edge       │
│ (Flutter / Wear OS OLED)  │  Bearer Token Auth       │ (Zero Open Ports)     │
└───────────────────────────┘                          └──────────┬────────────┘
                                                                  │ Outbound Tunnel
                                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ "golem" Home Server (Surface Pro X - Windows 11 on ARM64 - 16GB Total RAM)  │
│                                                                             │
│  ┌───────────────────────────────┐      ┌────────────────────────────────┐  │
│  │ Hyper-V: Home Assistant (4GB) │      │ chrysalis-obsidian (Port 8080) │  │
│  └───────────────────────────────┘      └────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────┐      ┌────────────────────────────────┐  │
│  │ cloudflared Tunnel Service    │ ───> │ Ambient Gateway (Port 8765)   │  │
│  └───────────────────────────────┘      └───────────────┬────────────────┘  │
│                                                         │                   │
│                                                         ▼                   │
│                                         ┌────────────────────────────────┐  │
│                                         │ Pluggable Orchestrator Bridge  │  │
│                                         │ (BaseOrchestratorBridge)       │  │
│                                         └───────┬───────────┬────────────┘  │
│                                                 │           │               │
│                      ┌──────────────────────────┘           └────────┐      │
│                      ▼                                               ▼      │
│     ┌───────────────────────────────────┐               ┌────────────────┐  │
│     │ Antigravity Language Server (Ref) │               │ OpenClaw /     │  │
│     │ (language_server.exe / agentapi)  │               │ Hermes OS / LLM│  │
│     └───────────────────────────────────┘               └────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Pluggable Orchestrator Bridge Architecture

The gateway decouples network transport from agent orchestration through the `BaseOrchestratorBridge` adapter interface ([`orchestrator_bridge.py`](orchestrator_bridge.py)):

* **`AntigravityBridge` (Reference Implementation):** Connects to the local Google Antigravity language server via `language_server.exe agentapi` or `agentapi.bat` on Windows (`~/.gemini/antigravity/bin/agentapi` on POSIX). Dispatches slash commands (`/morning`, `/evening`, `/plan`, `/task`, `/project`, `/zettel`, `/doctor`, `/audit`, `/pause`) and streams markdown responses.
* **`OpenClawBridge` (Pluggable Slot):** Direct bridge for OpenClaw-based autonomous agent execution.
* **`HermesOSBridge` (Pluggable Slot):** Direct bridge for Hermes OS / local LLM inference engines.

---

## 📡 API Specification

### 1. `POST /api/orchestrator/command`
Dispatches a Chrysalis slash command or conversational prompt to the active orchestrator.

**Request:**
```json
{
  "command": "/morning",
  "args": {
    "wake": "07:45",
    "energy": 4
  },
  "conversation_id": "optional-existing-conversation-id",
  "model": "gemini-3.8-flash"
}
```

**Response:**
```json
{
  "success": true,
  "command": "/morning",
  "output": "🌅 Morning Calibration Completed\n- Wake time locked: 07:45...",
  "conversation_id": "auto-created-or-passed-id",
  "execution_time_ms": 240,
  "timestamp": "2026-09-10T07:45:00-05:00"
}
```

### 2. `GET /api/orchestrator/status`
Returns real-time health, uptime, active profile, and availability of the orchestrator bridge.

**Response:**
```json
{
  "status": "healthy",
  "active_bridge": "antigravity",
  "bridge_connected": true,
  "vault_path": "vault/chrysalis",
  "version": "5.0.0",
  "port": 8765
}
```

### 3. `WebSocket /ws/orchestrator`
Provides real-time bidirectional streaming for conversational chat, active sprint telemetry, and rapid task creation.

---

## 📦 Windows Packaging & Installer Roadmap (`.exe`)

To transition from manual virtual environment execution to an autonomous, 1-click Windows installer:

1. **Frozen Subprocess Protection:** Add `multiprocessing.freeze_support()` at the entrypoint of [`main.py`](main.py). When frozen via PyInstaller, subprocess calls to `language_server.exe` / `agentapi` on Windows will recursively spawn duplicate processes without freeze support.
2. **Direct Uvicorn Application Passing:** Transition `uvicorn.run("main:app", ...)` to pass the application object directly (`uvicorn.run(app, ...)`), avoiding module import string failures inside PyInstaller bundles.
3. **User-Session Execution Invariant (No Session 0 Services):** The Chrysalis vault substrate often lives on a per-user mapped virtual drive (e.g. `G:\My Drive`). Windows Services run in **Session 0** and cannot access user mapped drives or `%LOCALAPPDATA%`. The installer will register the gateway daemon in the user's **Windows Startup folder** or `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
4. **Persistent JSON Configuration:** Read configuration from `%LOCALAPPDATA%\Chrysalis\gateway.json` with automatic fallback to environment variables.
5. **Inno Setup (`setup.iss`):** Compile an unprivileged user installer that unpacks the PyInstaller single-file binary, provisions the default configuration, and registers user auto-start.

---

## 🚀 Setup & Execution (Manual Prototype)

```powershell
# Navigate to gateway directory
cd apps\gateway

# Set up Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure environment variables
$env:CHRYSALIS_GATEWAY_PORT = "8765"
$env:CHRYSALIS_GATEWAY_TOKEN = "your-secure-bearer-token"
$env:CHRYSALIS_VAULT_PATH = "vault/chrysalis"

# Launch daemon
python main.py
```
